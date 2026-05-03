// frontend/lib/api.ts
import { QueryResponse, DocumentListResponse, UploadResponse, StatusResponse } from "@/types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// Keys stored in sessionStorage — never sent to any server except as headers
// to YOUR backend, which uses them for API calls then discards them.
export function getStoredKeys(): { openaiKey: string; groqKey: string } {
  if (typeof window === "undefined") return { openaiKey: "", groqKey: "" }
  return {
    openaiKey: sessionStorage.getItem("openai_key") || "",
    groqKey:   sessionStorage.getItem("groq_key")   || "",
  }
}

export function setStoredKeys(openaiKey: string, groqKey: string) {
  sessionStorage.setItem("openai_key", openaiKey)
  sessionStorage.setItem("groq_key", groqKey)
}

export function clearStoredKeys() {
  sessionStorage.removeItem("openai_key")
  sessionStorage.removeItem("groq_key")
}

export function hasKeys(): boolean {
  const { openaiKey, groqKey } = getStoredKeys()
  return !!openaiKey && !!groqKey
}

function authHeaders(): Record<string, string> {
  const { openaiKey, groqKey } = getStoredKeys()
  const headers: Record<string, string> = {}
  if (openaiKey) headers["X-OpenAI-Key"] = openaiKey
  if (groqKey)   headers["X-Groq-Key"]   = groqKey
  return headers
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append("file", file)
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Upload failed") }
  return res.json()
}

export async function getIngestionStatus(docId: string): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/status/${encodeURIComponent(docId)}`,
    { headers: authHeaders() })
  if (!res.ok) throw new Error("Status check failed")
  return res.json()
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const res = await fetch(`${API_BASE}/documents`, { headers: authHeaders() })
  if (!res.ok) throw new Error("Failed to list documents")
  return res.json()
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(docId)}`,
    { method: "DELETE", headers: authHeaders() })
  if (!res.ok) throw new Error("Delete failed")
}

export async function queryStream(
  question: string,
  onToken: (token: string) => void,
  onDone: (response: QueryResponse) => void,
  onError: (error: string) => void,
  docId?: string,
  k: number = 8
): Promise<void> {
  const params = new URLSearchParams({
    question, k: String(k),
    ...(docId ? { doc_id: docId } : {}),
  })

  let res: Response
  try {
    res = await fetch(`${API_BASE}/query/stream?${params}`, { headers: authHeaders() })
  } catch {
    onError("Could not connect to backend"); return
  }
  if (!res.ok || !res.body) { onError(`Stream failed: ${res.status}`); return }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let raw = ""
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    raw += decoder.decode(value, { stream: true })
  }

  for (const event of raw.split(/\n\n/)) {
    const lines = event.split("\n").map((l) => l.trim()).filter(Boolean)
    if (!lines.length) continue
    const eventLine = lines.find((l) => l.startsWith("event:"))
    const dataLine  = lines.find((l) => l.startsWith("data:"))
    if (!dataLine) continue
    const data = dataLine.slice(5).trim()
    if (eventLine === "event: done") {
      try { onDone(JSON.parse(data) as QueryResponse) } catch { onError("Failed to parse response") }
      return
    } else if (eventLine === "event: error") {
      onError(data || "Server error"); return
    } else {
      onToken(data.replace(/\\n/g, "\n"))
    }
  }
}
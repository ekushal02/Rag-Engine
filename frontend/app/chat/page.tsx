// frontend/app/chat/page.tsx
"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Send, Loader2, KeyRound, Menu, Library, X } from "lucide-react"
import AnswerDisplay from "@/components/AnswerDisplay"
import SourcesPanel from "@/components/SourcesPanel"
import DocumentList from "@/components/DocumentList"
import UploadZone from "@/components/UploadZone"
import { queryStream, listDocuments, hasKeys, clearStoredKeys } from "@/lib/api"
import KeySetup from "@/components/KeySetup"
import { Citation, DocumentInfo, QueryResponse, UploadResponse } from "@/types"

interface Message {
  id: string
  question: string
  answer: string
  citations: Citation[]
  routeTaken: string
  latencyMs: number
  model: string
  streaming: boolean
}

export default function ChatPage() {
  const [question, setQuestion]           = useState("")
  const [messages, setMessages]           = useState<Message[]>([])
  const [loading, setLoading]             = useState(false)
  const [documents, setDocuments]         = useState<DocumentInfo[]>([])
  const [docsLoading, setDocsLoading]     = useState(true)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [highlightedCitation, setHighlightedCitation] = useState<string | null>(null)
  const [activeMsgId, setActiveMsgId]     = useState<string | null>(null)
  const [keysReady, setKeysReady]         = useState(false)
  const [docsDrawerOpen, setDocsDrawerOpen]       = useState(false)
  const [sourcesDrawerOpen, setSourcesDrawerOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const refreshDocuments = useCallback(async () => {
    try {
      const res = await listDocuments()
      setDocuments(res.documents)
    } catch { /* silently fail */ }
    finally { setDocsLoading(false) }
  }, [])

  useEffect(() => { setKeysReady(hasKeys()) }, [])
  useEffect(() => { refreshDocuments() }, [refreshDocuments])
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  function handleUploadSuccess(_result: UploadResponse) { refreshDocuments() }

  async function handleSubmit() {
    const q = question.trim()
    if (!q || loading) return

    const msgId = Date.now().toString()
    setQuestion("")
    setLoading(true)
    setHighlightedCitation(null)

    setMessages((prev) => [...prev, {
      id: msgId, question: q, answer: "",
      citations: [], routeTaken: "", latencyMs: 0, model: "", streaming: true,
    }])

    await queryStream(
      q,
      (token) => setMessages((prev) =>
        prev.map((m) => m.id === msgId ? { ...m, answer: m.answer + token } : m)
      ),
      (response: QueryResponse) => {
        setMessages((prev) => prev.map((m) =>
          m.id === msgId ? {
            ...m,
            answer: response.answer,
            citations: response.citations,
            routeTaken: response.route_taken,
            latencyMs: response.latency_ms,
            model: response.model,
            streaming: false,
          } : m
        ))
        setActiveMsgId(msgId)
        setLoading(false)
      },
      (error) => {
        setMessages((prev) => prev.map((m) =>
          m.id === msgId ? { ...m, answer: `Error: ${error}`, streaming: false } : m
        ))
        setActiveMsgId(msgId)
        setLoading(false)
      },
      selectedDocId || undefined
    )
  }

  const sourceMessage =
    messages.find((m) => m.id === activeMsgId && !m.streaming) ??
    [...messages].reverse().find((m) => !m.streaming) ??
    null

  if (!keysReady) {
    return <KeySetup onKeysSet={() => setKeysReady(true)} />
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">

      {/* ── Header ── */}
      <header className="bg-white border-b border-gray-200 px-3 sm:px-6 py-3 flex-shrink-0">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between gap-2">

          {/* Left: hamburger (mobile/tablet) + logo + title */}
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <button
              onClick={() => setDocsDrawerOpen(true)}
              className="lg:hidden p-2 -ml-1 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
              aria-label="Open documents panel"
            >
              <Menu size={20} />
            </button>
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
              <span className="text-white text-sm font-bold">R</span>
            </div>
            <div className="min-w-0">
              <h1 className="text-sm sm:text-base font-semibold text-gray-900 leading-none truncate">
                RAG Document Intelligence
              </h1>
              <p className="hidden sm:block text-xs text-gray-500 mt-0.5">
                Upload PDFs · Ask questions · Get cited answers
              </p>
            </div>
          </div>

          {/* Right: status chips + sources toggle + change keys */}
          <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
            <div className="hidden xl:flex items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-green-50 border border-green-200 text-green-700 rounded-full font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                Groq LLaMA 3.3 70B
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 border border-blue-200 text-blue-700 rounded-full font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                OpenAI Embeddings
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-purple-50 border border-purple-200 text-purple-700 rounded-full font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                ChromaDB
              </span>
            </div>

            {/* Change keys button — clearly visible */}
            <button
              onClick={() => { clearStoredKeys(); setKeysReady(false) }}
              className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 border border-gray-200 rounded-lg transition-colors"
            >
              <KeyRound size={12} />
              <span className="hidden sm:inline">Change keys</span>
            </button>

            {/* Sources toggle (mobile/tablet) */}
            <button
              onClick={() => setSourcesDrawerOpen(true)}
              className="lg:hidden relative p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
              aria-label="Open sources panel"
            >
              <Library size={20} />
              {sourceMessage && sourceMessage.citations.length > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 flex items-center justify-center text-[10px] font-bold text-white bg-blue-600 rounded-full">
                  {sourceMessage.citations.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* ── Three-column body ── */}
      <div className="flex flex-1 min-h-0 overflow-hidden max-w-[1400px] mx-auto w-full relative">

        {/* Backdrop for mobile/tablet drawers */}
        {(docsDrawerOpen || sourcesDrawerOpen) && (
          <div
            className="fixed inset-0 bg-black/30 z-30 lg:hidden"
            onClick={() => { setDocsDrawerOpen(false); setSourcesDrawerOpen(false) }}
          />
        )}

        {/* ── Left sidebar ── */}
        <aside
          className={`
            fixed inset-y-0 left-0 z-40 w-72 sm:w-80
            border-r border-gray-200 bg-white flex flex-col
            transform transition-transform duration-200 ease-in-out
            ${docsDrawerOpen ? "translate-x-0" : "-translate-x-full"}
            lg:static lg:z-auto lg:translate-x-0 lg:w-72 lg:flex-shrink-0
          `}
        >
          {/* Mobile/tablet drawer header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-100 lg:hidden">
            <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
              Documents
            </h2>
            <button
              onClick={() => setDocsDrawerOpen(false)}
              className="p-1 text-gray-400 hover:text-gray-700 rounded"
              aria-label="Close documents panel"
            >
              <X size={18} />
            </button>
          </div>

          {/* Upload zone */}
          <div className="p-4 border-b border-gray-100">
            <h2 className="hidden lg:block text-xs font-bold text-gray-700 uppercase tracking-wider mb-3">
              Documents
            </h2>
            <UploadZone onSuccess={handleUploadSuccess} />
          </div>

          {/* Document list */}
          <div className="flex-1 overflow-y-auto p-4">
            {docsLoading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : (
              <DocumentList
                documents={documents}
                selectedDocId={selectedDocId}
                onSelect={(id) => { setSelectedDocId(id); setDocsDrawerOpen(false) }}
                onDeleted={(id) => {
                  setDocuments((prev) => prev.filter((d) => d.doc_id !== id))
                  if (selectedDocId === id) setSelectedDocId(null)
                }}
              />
            )}
          </div>

          {/* Pipeline info */}
          <div className="p-4 border-t border-gray-100 bg-gray-50">
            <p className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              Pipeline
            </p>
            <p className="text-xs text-gray-600 leading-relaxed">
              Simple → direct retrieval (k=8).<br />
              Complex → HyDE + cross-encoder reranking.
            </p>
          </div>
        </aside>

        {/* ── Center: Conversation ── */}
        <main className="flex-1 flex flex-col min-w-0 w-full">

          <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center max-w-lg mx-auto">
                <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center mb-4">
                  <span className="text-3xl">🔍</span>
                </div>
                <h2 className="text-xl font-semibold text-gray-800 mb-2">
                  Ask anything about your documents
                </h2>
                <p className="text-sm text-gray-500 max-w-sm">
                  Upload a PDF on the left, then type your question below.
                  Every claim links directly to its source chunk.
                </p>
                {documents.length === 0 && (
                  <div className="mt-6 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
                    No documents yet — upload a PDF to get started.
                  </div>
                )}
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                onClick={() => {
                  if (!msg.streaming) {
                    setActiveMsgId(msg.id)
                    setHighlightedCitation(null)
                  }
                }}
                className={`bg-white rounded-xl border p-3 sm:p-5 transition-all ${
                  msg.streaming
                    ? "border-blue-200 shadow-sm"
                    : activeMsgId === msg.id
                    ? "border-blue-300 shadow-sm cursor-pointer"
                    : "border-gray-200 hover:border-gray-300 cursor-pointer"
                }`}
              >
                {/* Question */}
                <div className="flex items-start gap-2.5 mb-3">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-blue-600">Q</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">{msg.question}</p>
                </div>

                {/* Streaming dots */}
                {msg.streaming && msg.answer === "" && (
                  <div className="flex items-center gap-2 ml-8 mb-3">
                    <div className="flex gap-1">
                      {[0, 150, 300].map((delay) => (
                        <span
                          key={delay}
                          className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
                          style={{ animationDelay: `${delay}ms` }}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-gray-500">Thinking...</span>
                  </div>
                )}

                {/* Answer */}
                {msg.answer !== "" && (
                  <div className="ml-8">
                    <AnswerDisplay
                      answer={msg.answer}
                      citations={msg.citations}
                      streaming={msg.streaming}
                      onCitationClick={(label) => {
                        setActiveMsgId(msg.id)
                        setHighlightedCitation(label)
                        setSourcesDrawerOpen(true)
                      }}
                    />
                  </div>
                )}

                {/* Metadata bar */}
                {!msg.streaming && msg.routeTaken && (
                  <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100 ml-8 flex-wrap items-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                      msg.routeTaken === "complex"
                        ? "bg-purple-100 text-purple-700"
                        : "bg-green-100 text-green-700"
                    }`}>
                      {msg.routeTaken === "complex" ? "HyDE + Rerank" : "Direct retrieval"}
                    </span>
                    <span className="text-xs text-gray-500">{msg.latencyMs}ms</span>
                    <span className="text-xs text-gray-500">
                      {msg.citations.length} citation{msg.citations.length !== 1 ? "s" : ""}
                    </span>
                    <span className="text-xs text-gray-400">{msg.model}</span>
                  </div>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div className="border-t border-gray-200 bg-white p-3 sm:p-4 flex-shrink-0">
            {selectedDocId && (
              <div className="flex items-center gap-1.5 mb-2 text-xs">
                <span className="text-gray-600 font-medium">Searching in:</span>
                <span className="font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                  {selectedDocId}
                </span>
                <button
                  onClick={() => setSelectedDocId(null)}
                  className="text-gray-400 hover:text-gray-700 ml-1 font-medium"
                >
                  ✕
                </button>
              </div>
            )}
            <div className="flex gap-3">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") handleSubmit()
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit() }
                }}
                placeholder={
                  documents.length === 0
                    ? "Upload a document first..."
                    : selectedDocId
                    ? `Ask about ${selectedDocId}... (Enter to send)`
                    : "Ask a question about your documents... (Enter to send)"
                }
                disabled={loading || documents.length === 0}
                rows={2}
                className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-shadow"
              />
              <button
                onClick={handleSubmit}
                disabled={loading || !question.trim() || documents.length === 0}
                className="px-3 sm:px-5 py-3 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors self-end flex items-center gap-2"
              >
                {loading
                  ? <><Loader2 size={14} className="animate-spin" /> <span className="hidden sm:inline">Generating</span></>
                  : <><Send size={14} /> <span className="hidden sm:inline">Ask</span></>
                }
              </button>
            </div>
          </div>
        </main>

        {/* ── Right sidebar: Sources ── */}
        <aside
          className={`
            fixed inset-y-0 right-0 z-40 w-80 max-w-[85vw]
            border-l border-gray-200 bg-white flex flex-col
            transform transition-transform duration-200 ease-in-out
            ${sourcesDrawerOpen ? "translate-x-0" : "translate-x-full"}
            lg:static lg:z-auto lg:translate-x-0 lg:max-w-none lg:flex-shrink-0
          `}
        >
          <div className="flex items-center justify-between p-4 border-b border-gray-100">
            <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
              Sources
              {sourceMessage && sourceMessage.citations.length > 0 && (
                <span className="ml-2 text-xs font-semibold text-blue-600 normal-case">
                  {sourceMessage.citations.length} cited
                </span>
              )}
            </h2>
            <button
              onClick={() => setSourcesDrawerOpen(false)}
              className="p-1 text-gray-400 hover:text-gray-700 rounded lg:hidden"
              aria-label="Close sources panel"
            >
              <X size={18} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <SourcesPanel
              citations={sourceMessage?.citations ?? []}
              highlightedLabel={highlightedCitation}
            />
          </div>
        </aside>
      </div>
    </div>
  )
}
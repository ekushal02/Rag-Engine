// frontend/components/UploadZone.tsx
"use client"

import { useState, useRef } from "react"
import { uploadDocument } from "@/lib/api"
import { UploadResponse } from "@/types"

interface Props {
  onSuccess: (result: UploadResponse) => void
}

const MAX_FILE_SIZE_MB = 50

export default function UploadZone({ onSuccess }: Props) {
  const [dragging,  setDragging]  = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress,  setProgress]  = useState<string | null>(null)
  const [error,     setError]     = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    // validate type
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.")
      return
    }

    // validate size
    const sizeMB = file.size / (1024 * 1024)
    if (sizeMB > MAX_FILE_SIZE_MB) {
      setError(`File too large (${sizeMB.toFixed(1)} MB). Maximum is ${MAX_FILE_SIZE_MB} MB.`)
      return
    }

    setError(null)
    setUploading(true)
    setProgress("Uploading...")

    // Show realistic progress messages as ingestion runs server-side
    const messages = [
      { delay: 800,  text: "Extracting text..." },
      { delay: 2000, text: "Chunking document..." },
      { delay: 3500, text: "Generating embeddings..." },
      { delay: 5500, text: "Storing in ChromaDB..." },
    ]
    const timers: ReturnType<typeof setTimeout>[] = []
    messages.forEach(({ delay, text }) => {
      timers.push(setTimeout(() => setProgress(text), delay))
    })

    try {
      const result = await uploadDocument(file)
      timers.forEach(clearTimeout)
      setProgress(`Done! ${result.chunk_count} chunks from ${result.pages} pages.`)
      setTimeout(() => {
        setProgress(null)
        setUploading(false)
      }, 2000)
      onSuccess(result)
    } catch (e: any) {
      timers.forEach(clearTimeout)
      setError(e.message || "Upload failed. Check that the backend is running.")
      setProgress(null)
      setUploading(false)
    }
  }

  return (
    <div
      onClick={() => !uploading && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        const file = e.dataTransfer.files[0]
        if (file) handleFile(file)
      }}
      className={`
        border-2 border-dashed rounded-xl p-6 text-center
        transition-colors duration-150
        ${uploading
          ? "border-blue-300 bg-blue-50 cursor-default"
          : dragging
            ? "border-blue-500 bg-blue-50 cursor-copy"
            : "border-gray-300 hover:border-blue-400 hover:bg-gray-50 cursor-pointer"}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFile(file)
          // reset input so same file can be re-uploaded after deletion
          e.target.value = ""
        }}
      />

      <div className="text-3xl mb-2">
        {uploading ? "⚙️" : dragging ? "📂" : "📄"}
      </div>

      {uploading ? (
        <div>
          <p className="text-sm font-medium text-blue-700">{progress}</p>
          <div className="mt-2 h-1 bg-blue-100 rounded-full overflow-hidden">
            <div className="h-full bg-blue-400 rounded-full animate-pulse w-3/4" />
          </div>
        </div>
      ) : (
        <>
          <p className="font-medium text-gray-700 text-sm">
            Drop a PDF here or click to browse
          </p>
          <p className="text-xs text-gray-400 mt-1">
            PDF only · max {MAX_FILE_SIZE_MB} MB
          </p>
        </>
      )}

      {error && (
        <p className="text-red-500 text-xs mt-3 leading-snug">{error}</p>
      )}
    </div>
  )
}

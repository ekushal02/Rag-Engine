// frontend/components/DocumentList.tsx
"use client"

import { useState } from "react"
import { DocumentInfo } from "@/types"
import { deleteDocument } from "@/lib/api"
import { Trash2, Loader2 } from "lucide-react"

interface Props {
  documents: DocumentInfo[]
  selectedDocId: string | null
  onSelect: (docId: string | null) => void
  onDeleted: (docId: string) => void
}

export default function DocumentList({ documents, selectedDocId, onSelect, onDeleted }: Props) {
  // track which doc is being deleted (shows spinner + prevents double-click)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(e: React.MouseEvent, docId: string) {
    e.stopPropagation()

    // Confirm before deleting — prevents accidental data loss
    const confirmed = window.confirm(
      `Delete "${docId}" and all its chunks from the index?\n\nThis cannot be undone.`
    )
    if (!confirmed) return

    setDeletingId(docId)
    try {
      await deleteDocument(docId)
      onDeleted(docId)
    } catch (err) {
      alert(`Failed to delete "${docId}". Try again.`)
    } finally {
      setDeletingId(null)
    }
  }

  if (documents.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-6">
        No documents ingested yet.
      </p>
    )
  }

  return (
    <ul className="space-y-2">
      {documents.map((doc) => {
        const isSelected  = selectedDocId === doc.doc_id
        const isDeleting  = deletingId === doc.doc_id

        return (
          <li
            key={doc.doc_id}
            onClick={() => !isDeleting && onSelect(isSelected ? null : doc.doc_id)}
            className={`
              flex items-center justify-between px-3 py-2 rounded-lg
              border text-sm transition-colors
              ${isDeleting
                ? "opacity-50 cursor-not-allowed border-gray-200"
                : isSelected
                  ? "border-blue-500 bg-blue-50 text-blue-700 cursor-pointer"
                  : "border-gray-200 hover:border-gray-300 text-gray-700 cursor-pointer"}
            `}
          >
            {/* document info */}
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate" title={doc.doc_id}>
                {doc.doc_id}
              </p>
              <p className="text-xs text-gray-400">
                {doc.chunk_count} chunks ·{" "}
                <span className={
                  doc.status === "done"    ? "text-green-500" :
                  doc.status === "error"   ? "text-red-500"   :
                  "text-amber-500"
                }>
                  {doc.status}
                </span>
              </p>
            </div>

            {/* delete button */}
            <button
              onClick={(e) => handleDelete(e, doc.doc_id)}
              disabled={isDeleting}
              className="ml-2 p-1 text-gray-400 hover:text-red-500 transition-colors rounded disabled:cursor-not-allowed"
              title="Delete document"
            >
              {isDeleting
                ? <Loader2 size={14} className="animate-spin" />
                : <Trash2 size={14} />}
            </button>
          </li>
        )
      })}

      {/* clear filter hint */}
      {selectedDocId && (
        <p
          className="text-xs text-blue-500 text-center pt-1 cursor-pointer hover:text-blue-700"
          onClick={() => onSelect(null)}
        >
          ✕ Clear filter — search all documents
        </p>
      )}
    </ul>
  )
}

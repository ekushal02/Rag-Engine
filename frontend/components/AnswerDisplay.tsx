// frontend/components/AnswerDisplay.tsx
"use client"

import { useState } from "react"
import { Citation } from "@/types"
import { Copy, Check } from "lucide-react"

interface Props {
  answer: string
  citations: Citation[]
  onCitationClick: (label: string) => void
  streaming?: boolean
}

/**
 * Splits the answer text into alternating plain-text and citation-tag segments,
 * rendering [C1], [C2] etc. as interactive buttons.
 */
function renderAnswerWithCitations(
  answer: string,
  citations: Citation[],
  onClick: (label: string) => void,
) {
  const parts = answer.split(/(\[C\d+\])/g)

  return parts.map((part, i) => {
    const match = part.match(/^\[C(\d+)\]$/)
    if (match) {
      const label    = `C${match[1]}`
      const citation = citations.find((c) => c.label === label)
      return (
        <button
          key={i}
          onClick={() => onClick(label)}
          title={citation ? `${citation.source} · page ${citation.page}` : label}
          className="
            inline-flex items-center mx-0.5 px-1.5 py-0 rounded
            text-xs font-semibold bg-blue-100 text-blue-700
            hover:bg-blue-200 active:bg-blue-300
            transition-colors cursor-pointer align-middle
          "
        >
          {label}
        </button>
      )
    }
    return <span key={i}>{part}</span>
  })
}

export default function AnswerDisplay({ answer, citations, onCitationClick, streaming }: Props) {
  const [copied, setCopied] = useState(false)

  // Detect the fallback refusal phrase written by the system prompt
  const isRefusal = answer
    .toLowerCase()
    .includes("i cannot answer this question based on the provided documents")

  async function handleCopy() {
    // Strip inline citation tags before copying so the text is clean
    const plainText = answer.replace(/\[C\d+\]/g, "").trim()
    await navigator.clipboard.writeText(plainText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!answer) return null

  return (
    <div className="relative group">

      {/* copy button — appears on hover when answer is present and not streaming */}
      {answer && !streaming && !isRefusal && (
        <button
          onClick={handleCopy}
          title="Copy answer"
          className="
            absolute top-0 right-0
            opacity-0 group-hover:opacity-100
            transition-opacity p-1.5 rounded-lg
            text-gray-400 hover:text-gray-600 hover:bg-gray-100
          "
        >
          {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
        </button>
      )}

      <div className="prose prose-sm max-w-none pr-8">
        {isRefusal ? (
          <div className="text-gray-500 text-sm">
            <p>No relevant information found in the ingested documents.</p>
            <p className="mt-1 text-xs text-gray-400">
              Try asking about document contents, grading criteria, research findings,
              or course requirements.
            </p>
          </div>
        ) : (
          <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
            {renderAnswerWithCitations(answer, citations, onCitationClick)}
            {/* streaming cursor */}
            {streaming && (
              <span className="inline-block w-0.5 h-4 bg-gray-400 ml-0.5 animate-pulse align-middle" />
            )}
          </p>
        )}
      </div>
    </div>
  )
}

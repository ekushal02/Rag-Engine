// frontend/components/SourcesPanel.tsx
"use client"

import { useEffect, useRef } from "react"
import { Citation } from "@/types"

interface Props {
  citations: Citation[]
  highlightedLabel: string | null
}

/**
 * Sidebar panel that shows the source chunks behind each citation.
 * Clicking a [C1] badge in AnswerDisplay scrolls this panel to that citation.
 */
export default function SourcesPanel({ citations, highlightedLabel }: Props) {
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({})

  // Scroll to highlighted citation when user clicks a citation badge
  useEffect(() => {
    if (highlightedLabel && cardRefs.current[highlightedLabel]) {
      cardRefs.current[highlightedLabel]?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      })
    }
  }, [highlightedLabel])

  if (citations.length === 0) {
    return (
      <div className="text-sm text-gray-400 text-center py-8 px-2">
        <p>Citations will appear here after you ask a question.</p>
        <p className="text-xs mt-2">
          Click any <span className="font-mono bg-blue-100 text-blue-600 px-1 rounded">[C1]</span>{" "}
          badge in the answer to jump to its source.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {citations.map((c) => {
        const isHighlighted = c.label === highlightedLabel
        const text = (c.chunk_text || "").trim()

        // Add leading ellipsis for chunks that begin mid-sentence
        const displayText = /^[a-z]/.test(text) ? "…" + text : text

        // Flag chunks where the cross-encoder found weak relevance.
        // The LLM may still have found the right answer in the chunk, but
        // the match was weak — worth surfacing to the user.
        const lowConfidence =
          c.rerank_score !== null &&
          c.rerank_score !== undefined &&
          c.rerank_score < -3

        // Similarity score color (cosine similarity 0–1)
        const simColor =
          c.relevance_score === null || c.relevance_score === undefined
            ? "text-gray-400"
            : c.relevance_score > 0.7
              ? "text-green-600"
              : c.relevance_score > 0.5
                ? "text-amber-600"
                : "text-red-400"

        return (
          <div
            key={c.label}
            ref={(el) => { cardRefs.current[c.label] = el }}
            className={`
              rounded-lg border p-3 transition-all duration-200
              ${isHighlighted
                ? "border-blue-400 bg-blue-50 shadow-sm ring-1 ring-blue-200"
                : lowConfidence
                  ? "border-amber-200 bg-amber-50"
                  : "border-gray-200 bg-white hover:border-gray-300"}
            `}
          >
            {/* Header: label + source */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">
                {c.label}
              </span>
              <span
                className="text-xs text-gray-500 truncate ml-2 max-w-[140px]"
                title={`${c.source} · page ${c.page}`}
              >
                {c.source} · p.{c.page}
              </span>
            </div>

            {/* Low-confidence warning */}
            {lowConfidence && (
              <div className="text-xs text-amber-700 bg-amber-100 rounded px-2 py-1 mb-2">
                ⚠️ Weak relevance score — answer may still be correct
              </div>
            )}

            {/* Scores */}
            <div className="flex gap-3 mb-2">
              {c.relevance_score !== null && c.relevance_score !== undefined && (
                <div className="text-xs">
                  <span className="text-gray-400">similarity </span>
                  <span className={`font-medium ${simColor}`}>
                    {c.relevance_score.toFixed(3)}
                  </span>
                </div>
              )}
              {c.rerank_score !== null && c.rerank_score !== undefined && (
                <div className="text-xs">
                  <span className="text-gray-400">rerank </span>
                  <span className={`font-medium ${c.rerank_score > 0 ? "text-green-600" : "text-red-400"}`}>
                    {c.rerank_score.toFixed(2)}
                  </span>
                </div>
              )}
            </div>

            {/* Chunk text preview */}
            <p className="text-xs text-gray-600 leading-relaxed line-clamp-6">
              {displayText}
            </p>
          </div>
        )
      })}
    </div>
  )
}

// frontend/components/KeySetup.tsx
"use client"

import { useState } from "react"
import { setStoredKeys } from "@/lib/api"
import { Key, Eye, EyeOff } from "lucide-react"

interface Props {
  onKeysSet: () => void
}

export default function KeySetup({ onKeysSet }: Props) {
  const [openaiKey, setOpenaiKey] = useState("")
  const [groqKey,   setGroqKey]   = useState("")
  const [showKeys,  setShowKeys]  = useState(false)
  const [error,     setError]     = useState("")

  function handleSubmit() {
    if (!openaiKey.startsWith("sk-")) {
      setError("OpenAI key should start with sk-"); return
    }
    if (!groqKey.startsWith("gsk_")) {
      setError("Groq key should start with gsk_"); return
    }
    setStoredKeys(openaiKey.trim(), groqKey.trim())
    onKeysSet()
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 w-full max-w-md">

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center flex-shrink-0">
            <Key size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">RAG Document Intelligence</h1>
            <p className="text-xs text-gray-500 mt-0.5">Enter your API keys to get started</p>
          </div>
        </div>

        <div className="space-y-4">

          {/* OpenAI key */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">
              OpenAI API Key
              <span className="ml-1.5 text-xs text-gray-500 font-normal">for embeddings</span>
            </label>
            <input
              type={showKeys ? "text" : "password"}
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              placeholder="sk-..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Groq key */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">
              Groq API Key
              <span className="ml-1.5 text-xs text-gray-500 font-normal">for LLaMA 3.3 70B — free</span>
            </label>
            <input
              type={showKeys ? "text" : "password"}
              value={groqKey}
              onChange={(e) => setGroqKey(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              placeholder="gsk_..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Show/hide toggle */}
          <button
            onClick={() => setShowKeys(!showKeys)}
            className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
          >
            {showKeys ? <EyeOff size={13} /> : <Eye size={13} />}
            {showKeys ? "Hide keys" : "Show keys"}
          </button>

          {error && (
            <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-xs font-medium text-red-600">{error}</p>
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={!openaiKey || !groqKey}
            className="w-full bg-blue-600 text-white rounded-xl py-3 text-sm font-semibold hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Continue →
          </button>
        </div>

        {/* Footer */}
        <div className="mt-6 pt-5 border-t border-gray-100 space-y-3">
          <p className="text-xs text-gray-600 leading-relaxed">
            🔒 Keys are stored only in your browser session and sent as request headers.
            They are <span className="font-semibold text-gray-700">never stored on the server</span>.
            Session clears on tab close.
          </p>
          <div className="flex gap-4">
            <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noreferrer"
                className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
            >
                Get OpenAI key →
            </a>

            <a
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noreferrer"
                className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
            >
                Get Groq key (free) →
            </a>
            </div>
        </div>
      </div>
    </div>
  )
}
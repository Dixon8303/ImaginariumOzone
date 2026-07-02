import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { api } from './api/client'

const MODES = [
  { id: 'ASSISTED', label: 'Assisted', desc: 'Pause at script, assets, and video review' },
  { id: 'SEMI_AUTO', label: 'Semi-Auto', desc: 'Pause only before upload' },
  { id: 'FULL_AUTO', label: 'Full Auto', desc: 'End-to-end, pause only before upload' },
]

export default function EpisodeManager() {
  const navigate = useNavigate()
  const location = useLocation()
  const [topic, setTopic] = useState(location.state?.topic || '')
  const [mode, setMode] = useState('ASSISTED')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!topic.trim()) return
    setLoading(true)
    setError(null)
    try {
      const ep = await api.createEpisode(topic.trim(), mode)
      await api.startPipeline(ep.id)
      navigate(`/episodes/${ep.id}/pipeline`)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-16 px-6">
      <div className="mb-10">
        <p className="text-xs tracking-widest text-amber-600 uppercase mb-3">§ New Episode</p>
        <h1 className="font-display text-5xl text-amber-100 tracking-wide mb-3">
          NEW PRODUCTION
        </h1>
        <p className="text-amber-200/60 italic font-serif text-lg">
          Enter a topic and the system begins immediately.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Topic */}
        <div>
          <label className="block text-xs tracking-widest text-amber-600 uppercase mb-3">
            Episode Topic
          </label>
          <textarea
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="e.g. Garrett Morgan and the invention of the traffic signal — and how he was written out of history"
            rows={4}
            className="w-full bg-stone-900 border border-amber-900/40 text-amber-100 rounded-sm p-4
                       font-serif text-base leading-relaxed resize-none
                       focus:outline-none focus:border-amber-600 placeholder:text-stone-600"
          />
        </div>

        {/* Production Notes */}
        <div>
          <label className="block text-xs tracking-widest text-amber-600 uppercase mb-3">
            Production Notes <span className="text-stone-600 normal-case">(optional)</span>
          </label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="e.g. Focus on the 1920s–1940s era. Emphasize the commercial scale of his inventions."
            rows={2}
            className="w-full bg-stone-900 border border-amber-900/40 text-amber-100 rounded-sm p-4
                       font-serif text-sm leading-relaxed resize-none
                       focus:outline-none focus:border-amber-600 placeholder:text-stone-600"
          />
        </div>

        {/* Mode */}
        <div>
          <label className="block text-xs tracking-widest text-amber-600 uppercase mb-3">
            Operating Mode
          </label>
          <div className="grid grid-cols-3 gap-3">
            {MODES.map(m => (
              <button
                key={m.id}
                type="button"
                onClick={() => setMode(m.id)}
                className={`p-4 border text-left transition-colors duration-200 rounded-sm
                  ${mode === m.id
                    ? 'border-amber-600 bg-amber-950/40'
                    : 'border-stone-700 bg-stone-900 hover:border-amber-800'}`}
              >
                <div className={`text-sm font-bold tracking-wide mb-1
                  ${mode === m.id ? 'text-amber-400' : 'text-amber-100'}`}>
                  {m.label}
                </div>
                <div className="text-xs text-stone-500 leading-relaxed">{m.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="border border-red-800 bg-red-950/30 text-red-400 p-4 text-sm font-mono">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !topic.trim()}
          className="w-full py-4 bg-amber-700 hover:bg-amber-600 disabled:bg-stone-700
                     disabled:text-stone-500 text-black font-bold tracking-widest text-sm
                     uppercase transition-colors duration-200"
        >
          {loading ? 'INITIATING PRODUCTION…' : 'BEGIN PRODUCTION'}
        </button>
      </form>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from './api/client'

function formatViews(n) {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`
  return String(n)
}

export default function DiscoveryFeed() {
  const navigate = useNavigate()
  const [feed, setFeed] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getDiscoveryFeed()
      .then(setFeed)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function startEpisode(topic) {
    navigate('/new', { state: { topic } })
  }

  if (loading) return (
    <div className="max-w-4xl mx-auto py-16 px-6 text-center text-amber-800 font-mono text-sm">
      Scanning the content space…
    </div>
  )

  if (error) return (
    <div className="max-w-4xl mx-auto py-16 px-6 text-center text-red-400 font-mono text-sm">
      {error}
    </div>
  )

  const candidates = feed?.candidates || []
  const outliers = feed?.outliers || []

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      {/* Header */}
      <div className="mb-10 border-b border-amber-900/30 pb-6">
        <p className="text-xs tracking-widest text-amber-600 uppercase mb-2">§ Discovery</p>
        <h1 className="font-display text-5xl text-amber-100 tracking-wide">WHAT TO MAKE NEXT</h1>
        <p className="text-stone-500 font-serif italic text-sm mt-2">
          Audience demand, mapped before a frame is generated.
        </p>
      </div>

      {/* Topic candidates from Haiku */}
      <section className="mb-12">
        <h2 className="font-display text-2xl text-amber-200 tracking-wide mb-1">
          TOPIC CANDIDATES
        </h2>
        <p className="text-stone-600 font-mono text-xs mb-5">
          Generated against the BGF editorial doctrine — named institutions, systems framing
        </p>
        {candidates.length === 0 ? (
          <p className="text-stone-600 font-serif italic py-6">
            No candidates generated. Check the ANTHROPIC_API_KEY.
          </p>
        ) : (
          <div className="grid gap-3">
            {candidates.map((c, i) => (
              <div key={i}
                   className="border border-amber-900/30 bg-stone-950 p-5 flex items-start gap-5
                              hover:border-amber-700/60 transition-colors group">
                <div className="flex-1 min-w-0">
                  <p className="text-amber-100 font-serif text-base leading-snug">{c.topic}</p>
                  <p className="text-stone-500 font-serif italic text-sm mt-1.5">{c.hook}</p>
                  <div className="flex items-center gap-4 mt-2.5">
                    {c.era && (
                      <span className="text-xs font-mono text-stone-600">{c.era}</span>
                    )}
                    {c.primary_keyword && (
                      <span className="text-xs font-mono text-amber-800">
                        kw: {c.primary_keyword}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => startEpisode(c.topic)}
                  className="shrink-0 px-4 py-2 border border-amber-800/50 text-amber-600
                             text-[10px] font-mono tracking-widest uppercase
                             hover:bg-amber-700 hover:text-black hover:border-transparent
                             transition-colors"
                >
                  Produce →
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* vidIQ outliers */}
      <section>
        <h2 className="font-display text-2xl text-amber-200 tracking-wide mb-1">
          BREAKOUT SIGNALS
        </h2>
        <p className="text-stone-600 font-mono text-xs mb-5">
          Small channels over-performing on BGF-adjacent topics — proof of audience demand
        </p>
        {!feed?.vidiq_configured ? (
          <div className="border border-stone-800 bg-stone-950 p-6 text-center">
            <p className="text-stone-500 font-serif italic mb-2">
              vidIQ is not connected.
            </p>
            <p className="text-stone-600 font-mono text-xs">
              Add VIDIQ_API_KEY to backend/.env to see breakout videos in the BGF content space.
            </p>
          </div>
        ) : outliers.length === 0 ? (
          <p className="text-stone-600 font-serif italic py-6">
            No outliers found for the current seed queries.
          </p>
        ) : (
          <div className="border border-amber-900/30 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-amber-900/30 bg-stone-900/40">
                  {['Video', 'Channel', 'Views', 'Subs', 'Multiplier'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-ui tracking-widest text-stone-500 uppercase">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {outliers.map((o, i) => (
                  <tr key={i} className="border-b border-amber-900/10 hover:bg-stone-900/30 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-amber-100 text-sm font-serif truncate max-w-sm">{o.title}</p>
                      <p className="text-stone-600 font-mono text-[10px] mt-0.5">{o.seed_query}</p>
                    </td>
                    <td className="px-4 py-3 text-stone-400 text-sm truncate max-w-[10rem]">{o.channel}</td>
                    <td className="px-4 py-3 font-mono text-sm text-amber-400">{formatViews(o.views)}</td>
                    <td className="px-4 py-3 font-mono text-sm text-stone-500">{formatViews(o.subscriber_count)}</td>
                    <td className="px-4 py-3 font-mono text-sm">
                      <span className={o.outlier_score >= 10 ? 'text-emerald-400' : 'text-stone-400'}>
                        {o.outlier_score ? `${Number(o.outlier_score).toFixed(1)}×` : '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

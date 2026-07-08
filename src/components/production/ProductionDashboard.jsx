import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from './api/client'

const STATUS_CONFIG = {
  draft:              { color: 'text-stone-500',  border: 'border-stone-700',  label: 'Draft' },
  running:            { color: 'text-amber-400',  border: 'border-amber-700',  label: 'Running' },
  script_review:      { color: 'text-amber-400',  border: 'border-amber-600',  label: 'Script Review' },
  generation_review:  { color: 'text-amber-400',  border: 'border-amber-600',  label: 'Asset Review' },
  assembly_review:    { color: 'text-amber-400',  border: 'border-amber-600',  label: 'Video Review' },
  review:             { color: 'text-amber-300',  border: 'border-amber-500',  label: 'Ready to Upload' },
  done:               { color: 'text-emerald-500', border: 'border-emerald-800', label: 'Published' },
  failed:             { color: 'text-red-400',    border: 'border-red-800',    label: 'Failed' },
}

const REVIEW_ROUTES = {
  script_review:      'script',
  generation_review:  'assets',
  assembly_review:    'preview',
  review:             'upload',
}

export default function ProductionDashboard() {
  const navigate = useNavigate()
  const [episodes, setEpisodes] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listEpisodes().then(eps => { setEpisodes(eps); setLoading(false) })
  }, [])

  async function handleDelete(id, e) {
    e.stopPropagation()
    if (!confirm('Delete this episode and all its assets?')) return
    await api.deleteEpisode(id)
    setEpisodes(prev => prev.filter(ep => ep.id !== id))
  }

  function getActionRoute(ep) {
    return REVIEW_ROUTES[ep.status] || 'pipeline'
  }

  return (
    <div className="max-w-5xl mx-auto py-16 px-6">
      {/* Header */}
      <div className="flex items-end justify-between mb-12 border-b border-amber-900/30 pb-8">
        <div>
          <p className="text-xs tracking-widest text-amber-600 uppercase mb-3">
            E.A.T. Media · Spinoff 03
          </p>
          <h1 className="font-display text-6xl text-amber-100 tracking-wide leading-none">
            THE BLACK
          </h1>
          <h1 className="font-display text-6xl text-amber-600 tracking-wide leading-none">
            GENIUS FILES
          </h1>
          <p className="text-stone-500 font-serif italic text-base mt-3">
            Narrative Production Operating System · v1.0
          </p>
        </div>
        <div className="flex flex-col gap-3 items-end">
          <button
            onClick={() => navigate('/new')}
            className="px-6 py-3 bg-amber-700 hover:bg-amber-600 text-black font-bold
                       text-xs tracking-widest uppercase transition-colors"
          >
            + New Episode
          </button>
          <Link
            to="/war-room"
            className="text-xs font-mono text-stone-500 hover:text-amber-600 tracking-widest
                       uppercase border-none transition-colors"
          >
            War Room →
          </Link>
        </div>
      </div>

      {/* Episodes */}
      {loading ? (
        <div className="text-center py-20 text-amber-800 font-mono text-sm">
          Loading episodes…
        </div>
      ) : episodes.length === 0 ? (
        <div className="text-center py-24">
          <p className="font-display text-3xl text-stone-700 tracking-wide mb-4">
            NO PRODUCTIONS YET
          </p>
          <p className="text-stone-600 font-serif italic mb-8">
            Begin with a topic. The system does the rest.
          </p>
          <button
            onClick={() => navigate('/new')}
            className="px-8 py-3 border border-amber-800/50 text-amber-700 text-xs tracking-widest
                       uppercase hover:border-amber-600 hover:text-amber-500 transition-colors"
          >
            Create First Episode
          </button>
        </div>
      ) : (
        <div className="space-y-px bg-amber-900/10">
          {episodes.map(ep => {
            const cfg = STATUS_CONFIG[ep.status] || STATUS_CONFIG.draft
            const isReview = Object.keys(REVIEW_ROUTES).includes(ep.status)
            const actionRoute = getActionRoute(ep)
            return (
              <div
                key={ep.id}
                className="bg-stone-950 hover:bg-stone-900/60 transition-colors
                           flex items-center gap-6 px-6 py-5 cursor-pointer group"
                onClick={() => navigate(`/episodes/${ep.id}/${actionRoute}`)}
              >
                {/* Status indicator */}
                <div className={`w-2 h-2 rounded-full flex-shrink-0
                  ${ep.status === 'running' ? 'bg-amber-500 animate-pulse' :
                    ep.status === 'done' ? 'bg-emerald-500' :
                    ep.status === 'failed' ? 'bg-red-500' :
                    isReview ? 'bg-amber-400' : 'bg-stone-600'}`}
                />

                {/* Topic */}
                <div className="flex-1 min-w-0">
                  <p className="text-amber-100 font-serif text-base truncate group-hover:text-amber-200 transition-colors">
                    {ep.topic}
                  </p>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="text-stone-600 font-mono text-xs">
                      {new Date(ep.created_at).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric'
                      })}
                    </span>
                    {ep.keyword && (
                      <span className="text-stone-600 font-mono text-xs">
                        {ep.keyword}
                      </span>
                    )}
                    {ep.score && (
                      <span className={`font-mono text-xs ${ep.score >= 70 ? 'text-emerald-700' : 'text-red-700'}`}>
                        Score: {ep.score}/100
                      </span>
                    )}
                  </div>
                </div>

                {/* Mode badge */}
                <span className="text-xs font-mono text-stone-600 flex-shrink-0 hidden md:block">
                  {ep.mode}
                </span>

                {/* Status badge */}
                <span className={`text-xs font-mono px-3 py-1 border flex-shrink-0 ${cfg.border} ${cfg.color}`}>
                  {cfg.label}
                </span>

                {/* Review indicator */}
                {isReview && (
                  <span className="text-xs text-amber-600 font-mono flex-shrink-0 animate-pulse">
                    REVIEW NEEDED
                  </span>
                )}

                {/* Delete */}
                <button
                  onClick={(e) => handleDelete(ep.id, e)}
                  className="text-stone-700 hover:text-red-500 text-lg opacity-0 group-hover:opacity-100
                             transition-all flex-shrink-0"
                >
                  ×
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Footer doctrine */}
      <div className="mt-16 pt-8 border-t border-amber-900/20 text-center">
        <p className="text-stone-700 font-serif italic text-sm">
          Truth · Tension · Transmission · Transformation
        </p>
      </div>
    </div>
  )
}

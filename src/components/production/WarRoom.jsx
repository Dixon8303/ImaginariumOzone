import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from './api/client'

const PRIORITY_COLOR = {
  immediate:  'text-red-400 border-red-800/50',
  structural: 'text-amber-400 border-amber-800/50',
  monitor:    'text-emerald-400 border-emerald-800/50',
}

const STATUS_PILL = {
  draft:       'border-stone-700 text-stone-500',
  running:     'border-amber-700 text-amber-400',
  review:      'border-amber-600 text-amber-400',
  done:        'border-emerald-800 text-emerald-500',
  failed:      'border-red-800 text-red-400',
}

export default function WarRoom() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [episodes, setEpisodes] = useState([])
  const [interventions, setInterventions] = useState({})
  const [loading, setLoading] = useState(true)
  const [selectedEp, setSelectedEp] = useState(null)
  const [metrics, setMetrics] = useState({ ctr_24h: '', ctr_48h: '', retention_30: '', retention_70: '', watch_time_sec: '', session_depth: '', shorts_views: '' })
  const [submitting, setSubmitting] = useState(false)
  const [pulling, setPulling] = useState(false)
  const [pullStatus, setPullStatus] = useState(null)

  async function handlePullVidiq() {
    setPulling(true)
    setPullStatus(null)
    try {
      const res = await api.getChannelAnalytics()
      if (!res.configured) {
        setPullStatus('vidIQ not connected — add VIDIQ_API_KEY to backend/.env')
      } else if (!res.data) {
        setPullStatus('vidIQ returned no data for this channel')
      } else {
        const d = res.data
        setMetrics(prev => ({
          ...prev,
          ctr_48h: d.ctr ?? prev.ctr_48h,
          retention_30: d.retention_pct ?? prev.retention_30,
          watch_time_sec: d.avg_view_duration ?? prev.watch_time_sec,
        }))
        setPullStatus('Pulled live channel data — review and run the decision engine')
      }
    } catch (e) {
      setPullStatus(e.message)
    } finally {
      setPulling(false)
    }
  }

  useEffect(() => {
    Promise.all([api.getWarRoom(), api.listEpisodes()]).then(([wr, eps]) => {
      setData(wr)
      setEpisodes(eps)
      setLoading(false)
    })
  }, [])

  async function loadInterventions(epId) {
    const ivs = await api.getInterventions(epId)
    setInterventions(prev => ({ ...prev, [epId]: ivs }))
  }

  async function handleSubmitMetrics(epId) {
    setSubmitting(true)
    const m = {}
    for (const [k, v] of Object.entries(metrics)) m[k] = parseFloat(v) || 0
    const result = await api.recordPerformance(epId, m)
    setInterventions(prev => ({ ...prev, [epId]: result.interventions }))
    setSubmitting(false)
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-amber-800 font-mono text-sm">
      Loading war room…
    </div>
  )

  const avgs = data?.averages || {}

  return (
    <div className="max-w-6xl mx-auto py-12 px-6">
      {/* Header */}
      <div className="mb-10 flex items-end justify-between border-b border-amber-900/30 pb-6">
        <div>
          <p className="text-xs tracking-widest text-amber-600 uppercase mb-2">§ Analytics</p>
          <h1 className="font-display text-5xl text-amber-100 tracking-wide">WAR ROOM</h1>
          <p className="text-stone-500 font-serif italic text-sm mt-2">
            Data becomes decision.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-emerald-600">
          <span className="w-2 h-2 rounded-full bg-emerald-600" />
          SYSTEM NOMINAL
        </div>
      </div>

      {/* 4 metric cards */}
      <div className="grid grid-cols-4 gap-px bg-amber-900/20 border border-amber-900/20 mb-10">
        {[
          { label: 'CTR · Avg', value: avgs.avg_ctr ? `${avgs.avg_ctr}%` : '—', good: avgs.avg_ctr >= 6 },
          { label: 'Retention · Avg', value: avgs.avg_retention ? `${avgs.avg_retention}%` : '—', good: avgs.avg_retention >= 35 },
          { label: 'Session Depth', value: avgs.avg_session_depth ? avgs.avg_session_depth.toFixed(2) : '—', good: avgs.avg_session_depth >= 1.5 },
          { label: 'Episodes Total', value: episodes.length, good: true },
        ].map((m, i) => (
          <div key={i} className="bg-stone-950 p-6">
            <p className="text-xs tracking-widest text-stone-500 uppercase mb-3">{m.label}</p>
            <p className={`font-display text-5xl tracking-wide ${m.good ? 'text-amber-400' : 'text-red-400'}`}>
              {m.value}
            </p>
          </div>
        ))}
      </div>

      {/* Episode table */}
      <div className="mb-10">
        <h2 className="font-display text-2xl text-amber-200 tracking-wide mb-4">ACTIVE EPISODES</h2>
        <div className="border border-amber-900/30 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-amber-900/30 bg-stone-900/40">
                {['Episode', 'Status', 'CTR', 'Retention', 'Action'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-ui tracking-widest text-stone-500 uppercase">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {episodes.slice(0, 10).map(ep => {
                const perf = (data?.episodes || []).find(e => e.id === ep.id)
                const pillStyle = STATUS_PILL[ep.status] || STATUS_PILL.draft
                return (
                  <tr key={ep.id}
                      className="border-b border-amber-900/10 hover:bg-stone-900/30 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-amber-100 text-sm font-serif truncate max-w-xs">{ep.topic}</p>
                      <p className="text-stone-600 font-mono text-xs mt-0.5">
                        {new Date(ep.created_at).toLocaleDateString()}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-mono px-2 py-0.5 border ${pillStyle}`}>
                        {ep.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-sm">
                      <span className={perf?.ctr_48h >= 6 ? 'text-emerald-500' : perf?.ctr_48h ? 'text-red-400' : 'text-stone-600'}>
                        {perf?.ctr_48h ? `${perf.ctr_48h}%` : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-sm">
                      <span className={perf?.retention_pct >= 35 ? 'text-emerald-500' : perf?.retention_pct ? 'text-amber-500' : 'text-stone-600'}>
                        {perf?.retention_pct ? `${perf.retention_pct}%` : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => navigate(`/episodes/${ep.id}/pipeline`)}
                          className="text-xs text-amber-700 hover:text-amber-500 font-mono transition-colors"
                        >
                          Pipeline →
                        </button>
                        <button
                          onClick={() => {
                            setSelectedEp(selectedEp === ep.id ? null : ep.id)
                            loadInterventions(ep.id)
                          }}
                          className="text-xs text-stone-600 hover:text-stone-400 font-mono transition-colors"
                        >
                          Metrics
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {episodes.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-stone-600 font-serif italic">
                    No episodes yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Metrics input panel */}
      {selectedEp && (
        <div className="mb-10 border border-amber-900/30 bg-stone-950 p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="font-display text-xl text-amber-200 tracking-wide">
              LOG PERFORMANCE METRICS
            </h3>
            <button
              disabled={pulling}
              onClick={handlePullVidiq}
              className="px-4 py-2 border border-violet-800/60 text-violet-400 text-[10px]
                         font-mono tracking-widest uppercase hover:border-violet-500
                         hover:text-violet-300 transition-colors disabled:opacity-50"
            >
              {pulling ? 'Pulling…' : '⇣ Pull from vidIQ'}
            </button>
          </div>
          {pullStatus && (
            <p className="text-xs font-mono text-stone-500 mb-4 -mt-2">{pullStatus}</p>
          )}
          <div className="grid grid-cols-4 gap-4 mb-5">
            {[
              { key: 'ctr_24h', label: 'CTR 24h %' },
              { key: 'ctr_48h', label: 'CTR 48h %' },
              { key: 'retention_30', label: 'Retention 30% mark %' },
              { key: 'retention_70', label: 'Retention 70% mark %' },
              { key: 'watch_time_sec', label: 'Avg Watch Time (sec)' },
              { key: 'session_depth', label: 'Session Depth' },
              { key: 'shorts_views', label: 'Shorts Views (best)' },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-xs tracking-widest text-stone-500 uppercase mb-1">
                  {f.label}
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={metrics[f.key]}
                  onChange={e => setMetrics(prev => ({ ...prev, [f.key]: e.target.value }))}
                  className="w-full bg-stone-900 border border-stone-700 text-amber-100 px-3 py-2
                             font-mono text-sm focus:outline-none focus:border-amber-700"
                />
              </div>
            ))}
          </div>
          <button
            disabled={submitting}
            onClick={() => handleSubmitMetrics(selectedEp)}
            className="px-6 py-2 bg-amber-800 hover:bg-amber-700 text-black font-bold text-xs
                       tracking-widest uppercase transition-colors disabled:opacity-50"
          >
            {submitting ? 'Analyzing…' : 'Run Decision Engine'}
          </button>

          {/* Interventions */}
          {interventions[selectedEp]?.length > 0 && (
            <div className="mt-6 space-y-3">
              <p className="text-xs tracking-widest text-amber-700 uppercase mb-3">
                Decision Engine Output
              </p>
              {interventions[selectedEp].map((iv, i) => {
                const colors = PRIORITY_COLOR[iv.priority] || PRIORITY_COLOR.monitor
                return (
                  <div key={i} className={`border-l-2 pl-4 py-2 ${colors}`}>
                    <p className="text-xs font-mono uppercase tracking-widest mb-1 opacity-60">
                      {iv.priority}
                    </p>
                    <p className="text-sm text-stone-400 font-serif italic mb-1">{iv.issue}</p>
                    <p className="text-sm text-amber-200 font-serif">{iv.action}</p>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { api } from './api/client'

const TIER_META = {
  'claude-fable-5':          { label: 'Fable 5',   color: 'text-violet-400', bg: 'bg-violet-950/60 border-violet-700/40', dot: 'bg-violet-400' },
  'claude-opus-4-8':         { label: 'Opus 4.8',  color: 'text-amber-400',  bg: 'bg-amber-950/60 border-amber-700/40',   dot: 'bg-amber-400'  },
  'claude-sonnet-4-6':       { label: 'Sonnet 4.6',color: 'text-sky-400',    bg: 'bg-sky-950/60 border-sky-700/40',       dot: 'bg-sky-400'    },
  'claude-haiku-4-5-20251001':{ label: 'Haiku 4.5', color: 'text-emerald-400',bg: 'bg-emerald-950/60 border-emerald-700/40',dot: 'bg-emerald-400'},
  'comfyui':                 { label: 'ComfyUI',   color: 'text-rose-400',   bg: 'bg-rose-950/60 border-rose-700/40',     dot: 'bg-rose-400'   },
  'ffmpeg':                  { label: 'ffmpeg',    color: 'text-stone-400',  bg: 'bg-stone-900/60 border-stone-700/40',   dot: 'bg-stone-400'  },
  'ollama':                  { label: 'Ollama',    color: 'text-lime-400',   bg: 'bg-lime-950/60 border-lime-700/40',     dot: 'bg-lime-400'   },
}

const GATE_META = {
  G1: { label: 'Editorial Perspective', desc: 'Named institution? Systems frame? Reconstructable?' },
  G2: { label: '100-pt Score',          desc: '≥70 produce · 60-69 revise · <60 kill' },
  G3: { label: 'Hook Diagnostic',       desc: '/50 score · B1≤4 = auto-fail' },
  G4: { label: 'Predictive',            desc: 'CTR + retention vs. benchmarks' },
  G5: { label: 'Monetization / Ethics', desc: 'Advertiser safety ≥36/50' },
}

function TierBadge({ tier }) {
  const m = TIER_META[tier] || { label: tier, color: 'text-stone-400', bg: 'bg-stone-900/60 border-stone-700/40', dot: 'bg-stone-400' }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-mono tracking-widest uppercase border rounded ${m.bg} ${m.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${m.dot}`} />
      {m.label}
    </span>
  )
}

function GateBadge({ result }) {
  if (!result) return <span className="text-stone-600 text-xs font-mono">—</span>
  const pass = result === 'PASS'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono tracking-widest uppercase border rounded
      ${pass ? 'bg-emerald-950/60 border-emerald-700/40 text-emerald-400' : 'bg-red-950/60 border-red-700/40 text-red-400'}`}>
      {pass ? '✓' : '✗'} {result}
    </span>
  )
}

function StageStatusDot({ status }) {
  const map = {
    COMPLETED: 'bg-emerald-400',
    RUNNING:   'bg-amber-400 animate-pulse',
    FAILED:    'bg-red-400',
    HALTED:    'bg-orange-400',
    NOT_STARTED: 'bg-stone-700',
  }
  return <span className={`w-2 h-2 rounded-full ${map[status] || 'bg-stone-700'}`} />
}

function AutonomyTag({ autonomy }) {
  const map = {
    AUTO:         'text-emerald-500',
    AUTO_REVIEW:  'text-sky-400',
    CHECKPOINT:   'text-amber-400',
    HARD_HALT:    'text-red-400',
  }
  return <span className={`text-[10px] font-mono tracking-widest uppercase ${map[autonomy] || 'text-stone-500'}`}>{autonomy}</span>
}

function GatePanel({ gates, remediations, episodeId, onOverride }) {
  const [overrideGate, setOverrideGate] = useState(null)
  const [rationale, setRationale] = useState('')
  const [advancing, setAdvancing] = useState(false)

  const handleOverride = async (gateId, result, advanceTo) => {
    if (!rationale.trim()) return
    setAdvancing(true)
    try {
      await onOverride(gateId, result, rationale, advanceTo)
      setOverrideGate(null)
      setRationale('')
    } finally {
      setAdvancing(false)
    }
  }

  return (
    <div className="space-y-3">
      {Object.entries(GATE_META).map(([gateId, meta]) => {
        const decision = gates.find(g => g.gate_id === gateId)
        const rem = remediations.find(r => r.gate_id === gateId && r.status === 'open')
        return (
          <div key={gateId} className="border border-stone-800 rounded p-3 space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-stone-500 uppercase tracking-widest">{gateId}</span>
                  <span className="text-sm text-[var(--ink-cream)] font-ui">{meta.label}</span>
                </div>
                <p className="text-[11px] text-stone-500 mt-0.5">{meta.desc}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {decision?.score != null && (
                  <span className="text-xs font-mono text-stone-400">
                    {decision.score}{decision.max_score ? `/${decision.max_score}` : ''}
                  </span>
                )}
                <GateBadge result={decision?.result} />
              </div>
            </div>
            {decision?.rationale && (
              <p className="text-[11px] text-stone-400 border-l-2 border-stone-700 pl-2 italic">
                {decision.rationale}
              </p>
            )}
            {rem && (
              <div className="bg-red-950/40 border border-red-800/40 rounded p-2 text-[11px] text-red-300">
                <span className="font-mono text-red-500 uppercase tracking-widest text-[10px]">Remediation open · </span>
                {rem.description}
              </div>
            )}
            {decision?.result === 'FAIL' && (
              overrideGate === gateId ? (
                <div className="space-y-2 pt-1">
                  <textarea
                    rows={2}
                    placeholder="Operator rationale for override..."
                    value={rationale}
                    onChange={e => setRationale(e.target.value)}
                    className="w-full bg-stone-900 border border-stone-700 rounded px-3 py-2 text-xs text-stone-200
                               placeholder:text-stone-600 focus:outline-none focus:border-amber-600 resize-none"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleOverride(gateId, 'PASS', null)}
                      disabled={advancing || !rationale.trim()}
                      className="px-3 py-1.5 text-[10px] font-mono tracking-widest uppercase
                                 bg-amber-700 hover:bg-amber-600 text-black rounded disabled:opacity-40 transition-colors"
                    >
                      Override → Pass
                    </button>
                    <button
                      onClick={() => { setOverrideGate(null); setRationale('') }}
                      className="px-3 py-1.5 text-[10px] font-mono tracking-widest uppercase
                                 border border-stone-700 text-stone-400 hover:text-stone-200 rounded transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setOverrideGate(gateId)}
                  className="text-[10px] font-mono tracking-widest uppercase text-amber-600
                             hover:text-amber-400 transition-colors"
                >
                  Operator Override →
                </button>
              )
            )}
          </div>
        )
      })}
    </div>
  )
}

function StageRunsTable({ runs }) {
  if (!runs.length) {
    return <p className="text-stone-600 text-sm text-center py-8">No stage runs yet.</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-stone-800">
            <th className="text-left font-mono text-stone-500 tracking-widest uppercase text-[10px] pb-2 pr-4">Stage</th>
            <th className="text-left font-mono text-stone-500 tracking-widest uppercase text-[10px] pb-2 pr-4">Tier</th>
            <th className="text-left font-mono text-stone-500 tracking-widest uppercase text-[10px] pb-2 pr-4">Autonomy</th>
            <th className="text-left font-mono text-stone-500 tracking-widest uppercase text-[10px] pb-2 pr-4">Status</th>
            <th className="text-left font-mono text-stone-500 tracking-widest uppercase text-[10px] pb-2">Duration</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-900">
          {runs.map(run => {
            const dur = run.started_at && run.completed_at
              ? Math.round((new Date(run.completed_at) - new Date(run.started_at)) / 1000)
              : null
            return (
              <tr key={run.id} className="hover:bg-stone-900/30 transition-colors">
                <td className="py-2 pr-4 font-mono text-[var(--ink-cream)]">{run.stage}</td>
                <td className="py-2 pr-4"><TierBadge tier={run.tier} /></td>
                <td className="py-2 pr-4"><AutonomyTag autonomy={run.autonomy} /></td>
                <td className="py-2 pr-4">
                  <div className="flex items-center gap-2">
                    <StageStatusDot status={run.status} />
                    <span className="text-stone-400">{run.status}</span>
                  </div>
                </td>
                <td className="py-2 text-stone-500">{dur != null ? `${dur}s` : '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function MutationLog({ mutations }) {
  if (!mutations.length) {
    return <p className="text-stone-600 text-sm text-center py-6">No mutations logged.</p>
  }
  return (
    <div className="space-y-1 max-h-64 overflow-y-auto pr-1">
      {mutations.map(m => (
        <div key={m.id} className="flex items-start gap-3 text-[11px] font-mono py-1
                                    border-b border-stone-900 last:border-0">
          <span className="text-stone-600 shrink-0 w-20 truncate">{m.stage || '—'}</span>
          <span className="text-amber-700 shrink-0 w-28 truncate">{m.table_name}</span>
          <span className={`shrink-0 w-28 ${
            m.mutation_type.includes('FAIL') ? 'text-red-400' :
            m.mutation_type.includes('COMPLETE') ? 'text-emerald-400' : 'text-stone-400'
          }`}>{m.mutation_type}</span>
          <span className="text-stone-600 truncate">{m.logged_at?.slice(11, 19)}</span>
        </div>
      ))}
    </div>
  )
}

function TitleVariantsList({ variants }) {
  if (!variants.length) return null
  const ollama = variants.filter(v => v.source === 'ollama')
  const opus   = variants.filter(v => v.source === 'opus')
  const selected = variants.find(v => v.selected)
  return (
    <div className="space-y-3">
      {selected && (
        <div className="bg-amber-950/30 border border-amber-700/40 rounded p-2">
          <span className="text-[10px] font-mono text-amber-600 tracking-widest uppercase">Selected · </span>
          <span className="text-sm text-amber-200">{selected.title}</span>
        </div>
      )}
      {opus.length > 0 && (
        <div>
          <p className="text-[10px] font-mono text-stone-500 tracking-widest uppercase mb-1.5">Opus — scored variants</p>
          <ul className="space-y-1">
            {opus.map(v => (
              <li key={v.id} className="text-xs text-[var(--ink-cream)] border-l-2 border-amber-800/50 pl-2 py-0.5">{v.title}</li>
            ))}
          </ul>
        </div>
      )}
      {ollama.length > 0 && (
        <div>
          <p className="text-[10px] font-mono text-stone-500 tracking-widest uppercase mb-1.5">Ollama — candidate pool ({ollama.length})</p>
          <ul className="space-y-1">
            {ollama.map(v => (
              <li key={v.id} className="text-xs text-stone-500 border-l border-stone-800 pl-2 py-0.5">{v.title}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function ControlRoom() {
  const { id: episodeId } = useParams()
  const [tab, setTab] = useState('gates')
  const [gates, setGates] = useState([])
  const [remediations, setRemediations] = useState([])
  const [stageRuns, setStageRuns] = useState([])
  const [routing, setRouting] = useState({})
  const [mutations, setMutations] = useState([])
  const [titleVariants, setTitleVariants] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      const [g, sr, ml, tv] = await Promise.all([
        api.getGates(episodeId),
        api.getStageRuns(episodeId),
        api.getMutationLog(episodeId),
        api.getTitleVariants(episodeId),
      ])
      setGates(g.gates || [])
      setRemediations(g.remediations || [])
      setStageRuns(sr.stage_runs || [])
      setRouting(sr.routing || {})
      setMutations(ml.mutations || [])
      setTitleVariants(tv.variants || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [episodeId])

  useEffect(() => { load() }, [load])

  const handleOverride = async (gateId, result, rationale, advanceTo) => {
    await api.gateOverride(episodeId, gateId, result, rationale, advanceTo)
    await load()
  }

  const TABS = [
    { id: 'gates',    label: 'Gates G1–G5' },
    { id: 'stages',   label: 'Stage Runs' },
    { id: 'titles',   label: 'Title Variants' },
    { id: 'log',      label: 'Mutation Log' },
  ]

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div>
        <p className="eyebrow mb-1">Episode {episodeId?.slice(0, 8)}</p>
        <h1 className="font-display text-3xl tracking-widest text-[var(--gold)]">
          CONTROL ROOM
        </h1>
        <p className="text-[var(--ink-muted)] text-sm mt-1 font-ui">
          Gate decisions · Stage routing · Mutation audit
        </p>
      </div>

      {/* Routing legend */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {[
          ['claude-fable-5',           'Research · Evidence · Forensics'],
          ['claude-opus-4-8',          'Judgment · Gates · Script'],
          ['claude-sonnet-4-6',        'SSML · Storyboard · Shorts'],
          ['claude-haiku-4-5-20251001','SEO · Tags · Volume'],
        ].map(([tier, role]) => (
          <div key={tier} className={`p-2 rounded border text-[10px] ${TIER_META[tier]?.bg || ''}`}>
            <TierBadge tier={tier} />
            <p className={`mt-1 font-ui ${TIER_META[tier]?.color || ''} opacity-70`}>{role}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-stone-800 pb-0">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-xs font-ui tracking-widest uppercase transition-colors border-b-2
              ${tab === t.id
                ? 'border-[var(--gold)] text-[var(--gold)]'
                : 'border-transparent text-stone-500 hover:text-stone-300'}`}
          >
            {t.label}
          </button>
        ))}
        <button onClick={load} className="ml-auto text-[10px] font-mono text-stone-600 hover:text-stone-400 pb-2 transition-colors">
          ↻ refresh
        </button>
      </div>

      {loading ? (
        <p className="text-stone-600 text-sm text-center py-12">Loading…</p>
      ) : error ? (
        <p className="text-red-400 text-sm text-center py-8">{error}</p>
      ) : (
        <div>
          {tab === 'gates' && (
            <GatePanel
              gates={gates}
              remediations={remediations}
              episodeId={episodeId}
              onOverride={handleOverride}
            />
          )}
          {tab === 'stages' && <StageRunsTable runs={stageRuns} />}
          {tab === 'titles' && <TitleVariantsList variants={titleVariants} />}
          {tab === 'log' && <MutationLog mutations={mutations} />}
        </div>
      )}
    </div>
  )
}

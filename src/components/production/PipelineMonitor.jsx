import { useParams, useNavigate } from 'react-router-dom'
import { usePipeline } from './hooks/usePipeline'
import { api } from './api/client'
import { useState } from 'react'

const STATUS_COLORS = {
  pending:  { dot: 'bg-stone-600',  text: 'text-stone-500',  label: 'Pending' },
  running:  { dot: 'bg-amber-500 animate-pulse', text: 'text-amber-400', label: 'Running…' },
  done:     { dot: 'bg-emerald-500', text: 'text-emerald-400', label: 'Done' },
  failed:   { dot: 'bg-red-500',    text: 'text-red-400',    label: 'Failed' },
}

const GATE_LABELS = {
  script_review:     { label: 'Script Ready for Review', next: 'Approve & Continue', stage: 'seo' },
  generation_review: { label: 'Assets Ready for Review', next: 'Assets Approved', stage: 'ken_burns', link: 'assets' },
  assembly_review:   { label: 'Video Ready for Review', next: 'Proof & Continue', stage: 'shorts', link: 'preview' },
  review:            { label: 'Ready to Upload', next: 'Go to Upload', link: 'upload' },
}

export default function PipelineMonitor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { stageList, connected, episode, lastEvent } = usePipeline(id)
  const [resuming, setResuming] = useState(false)

  const status = episode?.status || 'running'
  const gate = GATE_LABELS[status]

  async function handleResume(fromStage) {
    setResuming(true)
    await api.resumePipeline(id, fromStage)
  }

  return (
    <div className="max-w-2xl mx-auto py-16 px-6">
      <div className="mb-10 flex items-start justify-between">
        <div>
          <p className="text-xs tracking-widest text-amber-600 uppercase mb-2">§ Pipeline</p>
          <h1 className="font-display text-4xl text-amber-100 tracking-wide">
            PRODUCTION STATUS
          </h1>
          <p className="text-stone-500 font-mono text-xs mt-2 truncate max-w-xs">
            {episode?.topic || id}
          </p>
        </div>
        <div className={`flex items-center gap-2 text-xs font-mono ${connected ? 'text-emerald-500' : 'text-stone-600'}`}>
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-stone-600'}`} />
          {connected ? 'LIVE' : 'OFFLINE'}
        </div>
      </div>

      {/* Stage list */}
      <div className="space-y-0 border border-amber-900/30">
        {stageList.map((stage, i) => {
          const colors = STATUS_COLORS[stage.status] || STATUS_COLORS.pending
          return (
            <div key={stage.name}
                 className="flex items-center gap-5 px-5 py-4 border-b border-amber-900/20 last:border-b-0">
              <span className="font-mono text-xs text-amber-900/60 w-8 text-right">
                {String(i + 1).padStart(2, '0')}
              </span>
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${colors.dot}`} />
              <span className="flex-1 text-amber-100 font-ui text-sm tracking-wide">
                {stage.label}
              </span>
              <span className={`text-xs font-mono ${colors.text}`}>
                {colors.label}
              </span>
            </div>
          )
        })}
      </div>

      {/* Gate / action panel */}
      {gate && (
        <div className="mt-8 border border-amber-700/50 bg-amber-950/20 p-6">
          <p className="text-xs tracking-widest text-amber-600 uppercase mb-2">
            ⏸ Human Gate Required
          </p>
          <p className="text-amber-100 font-serif italic text-lg mb-5">
            {gate.label}
          </p>
          <div className="flex gap-3">
            {gate.link && (
              <button
                onClick={() => navigate(`/episodes/${id}/${gate.link}`)}
                className="px-6 py-3 border border-amber-600 text-amber-400 text-xs tracking-widest
                           uppercase hover:bg-amber-950/40 transition-colors"
              >
                {gate.next}
              </button>
            )}
            {gate.stage && !gate.link && (
              <button
                disabled={resuming}
                onClick={() => handleResume(gate.stage)}
                className="px-6 py-3 bg-amber-700 hover:bg-amber-600 text-black font-bold
                           text-xs tracking-widest uppercase transition-colors disabled:opacity-50"
              >
                {resuming ? 'Resuming…' : gate.next}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Failed state */}
      {status === 'failed' && (
        <div className="mt-8 border border-red-800/50 bg-red-950/20 p-6">
          <p className="text-xs tracking-widest text-red-500 uppercase mb-2">Pipeline Failed</p>
          <p className="text-stone-400 font-mono text-sm mb-5">
            {lastEvent?.error || 'Check stage output for details.'}
          </p>
          <button
            disabled={resuming}
            onClick={() => handleResume(null)}
            className="px-6 py-3 border border-red-700 text-red-400 text-xs tracking-widest
                       uppercase hover:bg-red-950/40 transition-colors"
          >
            Retry from Failed Stage
          </button>
        </div>
      )}
    </div>
  )
}

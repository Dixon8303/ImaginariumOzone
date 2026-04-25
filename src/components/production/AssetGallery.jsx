import { useParams, useNavigate } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import { api } from './api/client'

const STATUS_STYLE = {
  pending:     { badge: 'bg-stone-800 text-stone-400',    label: 'Pending' },
  generating:  { badge: 'bg-amber-900/60 text-amber-400', label: 'Generating…' },
  done:        { badge: 'bg-stone-800 text-stone-400',    label: 'Ready' },
  approved:    { badge: 'bg-emerald-900/60 text-emerald-400', label: 'Approved' },
  rejected:    { badge: 'bg-red-900/40 text-red-400',     label: 'Rejected' },
  failed:      { badge: 'bg-red-900/40 text-red-400',     label: 'Failed' },
}

export default function AssetGallery() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(true)
  const [proceeding, setProceeding] = useState(false)

  const load = useCallback(() => {
    api.listAssets(id).then(a => { setAssets(a); setLoading(false) })
  }, [id])

  useEffect(() => {
    load()
    const interval = setInterval(load, 8000)
    return () => clearInterval(interval)
  }, [load])

  async function handleApprove(assetId) {
    await api.approveAsset(assetId)
    setAssets(prev => prev.map(a => a.id === assetId ? { ...a, status: 'approved' } : a))
  }

  async function handleReject(assetId) {
    await api.rejectAsset(assetId)
    setAssets(prev => prev.map(a => a.id === assetId ? { ...a, status: 'rejected' } : a))
  }

  async function handleRegenerate(assetId) {
    await api.regenerateAsset(assetId)
    setAssets(prev => prev.map(a => a.id === assetId ? { ...a, status: 'generating' } : a))
  }

  async function handleProceed() {
    setProceeding(true)
    await api.resumePipeline(id, 'ken_burns')
    navigate(`/episodes/${id}/pipeline`)
  }

  const total = assets.length
  const approved = assets.filter(a => a.status === 'approved').length
  const done = assets.filter(a => ['done', 'approved'].includes(a.status)).length
  const canProceed = total > 0 && assets.every(a => ['approved', 'done'].includes(a.status))

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-amber-800 font-mono text-sm">
      Loading assets…
    </div>
  )

  return (
    <div className="max-w-6xl mx-auto py-12 px-6">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <p className="text-xs tracking-widest text-amber-600 uppercase mb-2">§ Asset Review</p>
          <h1 className="font-display text-4xl text-amber-100 tracking-wide">ASSET GALLERY</h1>
          <p className="text-stone-500 font-mono text-xs mt-2">
            {done}/{total} generated · {approved}/{total} approved
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => assets.forEach(a => a.status === 'done' && handleApprove(a.id))}
            className="px-4 py-2 border border-amber-800/60 text-amber-600 text-xs tracking-widest
                       uppercase hover:border-amber-600 transition-colors"
          >
            Approve All Ready
          </button>
          <button
            disabled={!canProceed || proceeding}
            onClick={handleProceed}
            className="px-5 py-2 bg-amber-700 hover:bg-amber-600 text-black font-bold text-xs
                       tracking-widest uppercase transition-colors disabled:opacity-40"
          >
            {proceeding ? 'Starting Assembly…' : 'Proceed to Assembly'}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-stone-800 mb-8">
        <div
          className="h-full bg-amber-700 transition-all duration-500"
          style={{ width: `${total ? (done / total) * 100 : 0}%` }}
        />
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {assets.map(asset => {
          const style = STATUS_STYLE[asset.status] || STATUS_STYLE.pending
          const isImage = asset.asset_type === 'ai_image'
          const hasFile = asset.status === 'done' || asset.status === 'approved'
          return (
            <div
              key={asset.id}
              className={`border flex flex-col overflow-hidden transition-colors
                ${asset.status === 'approved' ? 'border-emerald-800/60' :
                  asset.status === 'rejected' ? 'border-red-900/40 opacity-50' :
                  'border-amber-900/30'}`}
            >
              {/* Preview */}
              <div className="aspect-video bg-stone-900 flex items-center justify-center relative">
                {hasFile && isImage && (
                  <img
                    src={api.assetFileUrl(asset.id)}
                    alt={`Scene ${asset.scene_index}`}
                    className="w-full h-full object-cover"
                    onError={e => { e.target.style.display = 'none' }}
                  />
                )}
                {hasFile && !isImage && (
                  <video
                    src={api.assetFileUrl(asset.id)}
                    className="w-full h-full object-cover"
                    muted loop
                    onMouseEnter={e => e.target.play()}
                    onMouseLeave={e => e.target.pause()}
                  />
                )}
                {!hasFile && (
                  <div className="text-stone-700 font-mono text-xs text-center px-3">
                    {asset.status === 'generating' ? (
                      <span className="text-amber-700 animate-pulse">Generating…</span>
                    ) : (
                      <span>Scene {asset.scene_index + 1}</span>
                    )}
                  </div>
                )}
                <div className="absolute top-2 left-2">
                  <span className="font-mono text-xs text-stone-600 bg-black/60 px-1.5 py-0.5">
                    {asset.asset_type === 'ai_video' ? '▶ VIDEO' : '◼ IMAGE'}
                  </span>
                </div>
              </div>

              {/* Info */}
              <div className="p-3 flex-1 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-amber-800">
                    Scene {asset.scene_index + 1}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-sm font-mono ${style.badge}`}>
                    {style.label}
                  </span>
                </div>
                <p className="text-stone-500 text-xs leading-relaxed line-clamp-2 font-serif italic">
                  {asset.prompt?.slice(0, 100)}…
                </p>

                {/* Actions */}
                {['done', 'approved', 'rejected', 'failed'].includes(asset.status) && (
                  <div className="flex gap-2 mt-auto pt-2">
                    {asset.status !== 'approved' && (
                      <button
                        onClick={() => handleApprove(asset.id)}
                        className="flex-1 py-1.5 text-xs bg-emerald-900/30 border border-emerald-800/40
                                   text-emerald-400 hover:bg-emerald-900/60 transition-colors"
                      >
                        ✓ Approve
                      </button>
                    )}
                    {asset.status === 'approved' && (
                      <button
                        onClick={() => handleReject(asset.id)}
                        className="flex-1 py-1.5 text-xs bg-transparent border border-stone-700
                                   text-stone-500 hover:border-red-800 hover:text-red-400 transition-colors"
                      >
                        Reject
                      </button>
                    )}
                    <button
                      onClick={() => handleRegenerate(asset.id)}
                      className="px-3 py-1.5 text-xs border border-amber-900/40 text-amber-700
                                 hover:border-amber-600 hover:text-amber-500 transition-colors"
                    >
                      ↺
                    </button>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {assets.length === 0 && (
        <div className="text-center py-20 text-stone-600 font-serif italic">
          No assets generated yet. Return to the pipeline.
        </div>
      )}
    </div>
  )
}

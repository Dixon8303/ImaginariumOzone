import { useParams, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { api } from './api/client'

export default function VideoPreview() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [seo, setSeo] = useState(null)
  const [videoReady, setVideoReady] = useState(false)
  const [loading, setLoading] = useState(true)
  const [proceeding, setProceeding] = useState(false)

  useEffect(() => {
    api.getEpisode(id).then(ep => {
      const seoStage = (ep.stages || []).find(s => s.stage_name === 'seo')
      if (seoStage?.output_json) {
        try { setSeo(JSON.parse(seoStage.output_json)) } catch {}
      }
      setLoading(false)
    })
    // Check if video exists
    fetch(api.finalVideoUrl(id), { method: 'HEAD' })
      .then(r => setVideoReady(r.ok))
      .catch(() => setVideoReady(false))
  }, [id])

  async function handleApprove() {
    setProceeding(true)
    await api.resumePipeline(id, 'shorts')
    navigate(`/episodes/${id}/upload`)
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-amber-800 font-mono text-sm">
      Loading…
    </div>
  )

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <div className="mb-8">
        <p className="text-xs tracking-widest text-amber-600 uppercase mb-2">§ Final Review</p>
        <h1 className="font-display text-4xl text-amber-100 tracking-wide">VIDEO PROOF</h1>
        <p className="text-stone-500 font-serif italic text-sm mt-2">
          Review the assembled episode before upload.
        </p>
      </div>

      {/* Video player */}
      <div className="aspect-video bg-stone-900 border border-amber-900/30 mb-6">
        {videoReady ? (
          <video
            src={api.finalVideoUrl(id)}
            controls
            className="w-full h-full"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-stone-600 font-mono text-sm mb-2">Video not ready</p>
              <p className="text-stone-700 text-xs">Assembly stage may still be running.</p>
            </div>
          </div>
        )}
      </div>

      {/* Thumbnail */}
      <div className="mb-8 flex gap-6 items-start">
        <div className="w-48 flex-shrink-0">
          <p className="text-xs tracking-widest text-amber-800 uppercase mb-2">Thumbnail</p>
          <img
            src={api.thumbnailUrl(id)}
            alt="Thumbnail"
            className="w-full border border-amber-900/30"
            onError={e => { e.target.parentElement.style.display = 'none' }}
          />
        </div>

        {seo && (
          <div className="flex-1 space-y-3">
            <div>
              <p className="text-xs tracking-widest text-amber-800 uppercase mb-1">Title</p>
              <p className="text-amber-100 font-serif text-lg">{seo.title}</p>
              <p className="text-stone-600 font-mono text-xs mt-1">
                {seo.title?.length || 0}/70 chars
              </p>
            </div>
            <div>
              <p className="text-xs tracking-widest text-amber-800 uppercase mb-1">Tags</p>
              <div className="flex flex-wrap gap-1">
                {(seo.tags || []).slice(0, 10).map((tag, i) => (
                  <span key={i}
                        className="text-xs font-mono px-2 py-0.5 border border-stone-700 text-stone-500">
                    {tag}
                  </span>
                ))}
                {(seo.tags || []).length > 10 && (
                  <span className="text-xs text-stone-600">
                    +{(seo.tags || []).length - 10} more
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-4 pt-6 border-t border-amber-900/20">
        <button
          onClick={() => navigate(`/episodes/${id}/assets`)}
          className="px-5 py-3 border border-stone-700 text-stone-400 text-xs tracking-widest
                     uppercase hover:border-amber-800 hover:text-amber-600 transition-colors"
        >
          ← Back to Assets
        </button>
        <button
          disabled={!videoReady || proceeding}
          onClick={handleApprove}
          className="px-8 py-3 bg-amber-700 hover:bg-amber-600 text-black font-bold text-xs
                     tracking-widest uppercase transition-colors disabled:opacity-40 ml-auto"
        >
          {proceeding ? 'Preparing…' : 'Approve — Prepare Upload'}
        </button>
      </div>
    </div>
  )
}

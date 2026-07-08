import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from './api/client'

const PRIVACY_OPTIONS = [
  { id: 'private',   label: 'Private',   desc: 'Only you can see it' },
  { id: 'unlisted',  label: 'Unlisted',  desc: 'Anyone with the link' },
  { id: 'public',    label: 'Public',    desc: 'Live on your channel' },
]

export default function UploadPanel() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [seo, setSeo] = useState(null)
  const [privacy, setPrivacy] = useState('private')
  const [uploading, setUploading] = useState(false)
  const [uploadDone, setUploadDone] = useState(false)
  const [youtubeUrl, setYoutubeUrl] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getEpisode(id).then(ep => {
      const seoStage = (ep.stages || []).find(s => s.stage_name === 'seo')
      if (seoStage?.output_json) {
        try { setSeo(JSON.parse(seoStage.output_json)) } catch {}
      }
      setLoading(false)
    })
    // Listen for upload completion via SSE
    const es = new EventSource(`/api/pipeline/status/${id}`)
    es.onmessage = (e) => {
      const ev = JSON.parse(e.data)
      if (ev.type === 'upload_done') {
        setUploadDone(true)
        setYoutubeUrl(ev.url)
        setUploading(false)
        es.close()
      }
      if (ev.type === 'upload_failed') {
        setError(ev.error || 'Upload failed')
        setUploading(false)
        es.close()
      }
    }
    return () => es.close()
  }, [id])

  function updateSeo(field, value) {
    setSeo(prev => ({ ...prev, [field]: value }))
  }

  function updateTag(i, value) {
    const tags = [...(seo.tags || [])]
    tags[i] = value
    updateSeo('tags', tags)
  }

  function removeTag(i) {
    const tags = (seo.tags || []).filter((_, idx) => idx !== i)
    updateSeo('tags', tags)
  }

  function addTag() {
    updateSeo('tags', [...(seo.tags || []), ''])
  }

  async function handleUpload() {
    setUploading(true)
    setError(null)
    try {
      await api.triggerUpload(id, privacy)
    } catch (e) {
      setError(e.message)
      setUploading(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-amber-800 font-mono text-sm">
      Loading…
    </div>
  )

  if (uploadDone) return (
    <div className="max-w-2xl mx-auto py-20 px-6 text-center">
      <div className="text-amber-600 font-display text-6xl mb-6">⁂</div>
      <h1 className="font-display text-4xl text-amber-100 tracking-wide mb-4">UPLOADED</h1>
      <p className="text-stone-400 font-serif italic text-lg mb-8">
        The episode is live on YouTube.
      </p>
      {youtubeUrl && (
        <a href={youtubeUrl} target="_blank" rel="noreferrer"
           className="text-amber-600 font-mono text-sm border-b border-amber-800 hover:text-amber-400">
          {youtubeUrl}
        </a>
      )}
      <div className="mt-10">
        <button
          onClick={() => navigate('/')}
          className="px-6 py-3 border border-amber-800/60 text-amber-600 text-xs tracking-widest
                     uppercase hover:border-amber-600 transition-colors"
        >
          Back to Dashboard
        </button>
      </div>
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
      <div className="mb-10">
        <p className="text-xs tracking-widest text-amber-600 uppercase mb-2">§ Upload</p>
        <h1 className="font-display text-4xl text-amber-100 tracking-wide">UPLOAD TO YOUTUBE</h1>
        <p className="text-stone-500 font-serif italic text-sm mt-2">
          Review the SEO package, set privacy, then upload.
        </p>
      </div>

      {seo ? (
        <div className="space-y-8">
          {/* Title */}
          <div>
            <label className="block text-xs tracking-widest text-amber-700 uppercase mb-2">
              Title
              <span className="ml-3 text-stone-600 normal-case font-mono">
                {seo.title?.length || 0}/70
              </span>
            </label>
            <input
              value={seo.title || ''}
              onChange={e => updateSeo('title', e.target.value)}
              maxLength={100}
              className="w-full bg-stone-900 border border-amber-900/40 text-amber-100 p-3
                         font-serif text-base focus:outline-none focus:border-amber-600"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs tracking-widest text-amber-700 uppercase mb-2">
              Description
            </label>
            <textarea
              value={seo.description || ''}
              onChange={e => updateSeo('description', e.target.value)}
              rows={10}
              className="w-full bg-stone-900 border border-amber-900/40 text-amber-100 p-3
                         font-serif text-sm leading-relaxed resize-none
                         focus:outline-none focus:border-amber-600"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-xs tracking-widest text-amber-700 uppercase mb-3">
              Tags <span className="text-stone-600 normal-case font-mono">({(seo.tags || []).length}/30)</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {(seo.tags || []).map((tag, i) => (
                <div key={i} className="flex items-center group">
                  <input
                    value={tag}
                    onChange={e => updateTag(i, e.target.value)}
                    className="bg-stone-900 border border-stone-700 text-stone-300 font-mono text-xs
                               px-2 py-1 focus:outline-none focus:border-amber-700 w-auto"
                    style={{ width: `${Math.max(tag.length + 2, 8)}ch` }}
                  />
                  <button
                    onClick={() => removeTag(i)}
                    className="ml-1 text-stone-700 hover:text-red-500 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                onClick={addTag}
                className="px-3 py-1 border border-dashed border-stone-700 text-stone-600
                           text-xs font-mono hover:border-amber-700 hover:text-amber-700 transition-colors"
              >
                + tag
              </button>
            </div>
          </div>

          {/* Pinned comments */}
          {seo.pinned_comments?.length > 0 && (
            <div>
              <label className="block text-xs tracking-widest text-amber-700 uppercase mb-3">
                Pinned Comment Options
              </label>
              <div className="space-y-2">
                {seo.pinned_comments.map((comment, i) => (
                  <div key={i}
                       className="p-3 border border-stone-800 bg-stone-900/40 text-stone-400
                                  font-serif text-sm italic">
                    {comment}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Privacy */}
          <div>
            <label className="block text-xs tracking-widest text-amber-700 uppercase mb-3">
              Privacy
            </label>
            <div className="flex gap-3">
              {PRIVACY_OPTIONS.map(opt => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setPrivacy(opt.id)}
                  className={`flex-1 p-3 border text-left transition-colors rounded-sm
                    ${privacy === opt.id
                      ? 'border-amber-600 bg-amber-950/30'
                      : 'border-stone-700 hover:border-amber-900'}`}
                >
                  <div className={`text-sm font-bold mb-1 ${privacy === opt.id ? 'text-amber-400' : 'text-amber-100'}`}>
                    {opt.label}
                  </div>
                  <div className="text-xs text-stone-500">{opt.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="border border-red-800 bg-red-950/20 text-red-400 p-4 font-mono text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-4 pt-4 border-t border-amber-900/20">
            <button
              onClick={() => navigate(`/episodes/${id}/preview`)}
              className="px-5 py-3 border border-stone-700 text-stone-400 text-xs tracking-widest
                         uppercase hover:border-amber-800 transition-colors"
            >
              ← Back to Preview
            </button>
            <button
              disabled={uploading}
              onClick={handleUpload}
              className="flex-1 py-3 bg-amber-700 hover:bg-amber-600 text-black font-bold text-sm
                         tracking-widest uppercase transition-colors disabled:opacity-50"
            >
              {uploading ? 'UPLOADING TO YOUTUBE…' : 'UPLOAD TO YOUTUBE'}
            </button>
          </div>
        </div>
      ) : (
        <div className="text-stone-600 font-serif italic py-12 text-center">
          SEO package not yet generated. Run the pipeline first.
        </div>
      )}
    </div>
  )
}

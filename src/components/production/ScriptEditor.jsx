import { useParams, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { api } from './api/client'

export default function ScriptEditor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [scenes, setScenes] = useState([])
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [continuing, setContinuing] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getEpisode(id).then(ep => {
      const stages = ep.stages || []
      const scriptStage = stages.find(s => s.stage_name === 'script')
      if (scriptStage?.output_json) {
        try {
          const data = JSON.parse(scriptStage.output_json)
          setTitle(data.title || ep.topic)
          setScenes(data.scenes || [])
        } catch {}
      }
      setLoading(false)
    }).catch(e => { setError(e.message); setLoading(false) })
  }, [id])

  function updateScene(i, field, value) {
    setScenes(prev => prev.map((s, idx) => idx === i ? { ...s, [field]: value } : s))
  }

  async function handleSave() {
    setSaving(true)
    try {
      await api.updateEpisode(id, { script_json: JSON.stringify({ title, scenes }) })
    } catch (e) { setError(e.message) }
    setSaving(false)
  }

  async function handleContinue() {
    setContinuing(true)
    await handleSave()
    await api.resumePipeline(id, 'seo')
    navigate(`/episodes/${id}/pipeline`)
  }

  const moodColors = {
    intense: 'text-red-400', reverent: 'text-amber-400', somber: 'text-blue-400',
    triumphant: 'text-emerald-400', ominous: 'text-purple-400', reflective: 'text-stone-400',
  }

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} />

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <div className="mb-10 flex items-start justify-between">
        <div>
          <p className="text-xs tracking-widest text-amber-600 uppercase mb-2">§ Script Review</p>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="bg-transparent text-amber-100 font-display text-3xl tracking-wide
                       border-b border-amber-900/40 focus:border-amber-600 focus:outline-none
                       pb-1 w-full max-w-2xl"
          />
        </div>
        <div className="flex gap-3 flex-shrink-0 ml-6">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 border border-amber-800/60 text-amber-600 text-xs tracking-widest
                       uppercase hover:border-amber-600 transition-colors disabled:opacity-40"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button
            onClick={handleContinue}
            disabled={continuing}
            className="px-5 py-2 bg-amber-700 hover:bg-amber-600 text-black font-bold text-xs
                       tracking-widest uppercase transition-colors disabled:opacity-50"
          >
            {continuing ? 'Starting…' : 'Approve & Generate'}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {scenes.map((scene, i) => (
          <div key={i} className="border border-amber-900/30 bg-stone-950">
            {/* Scene header */}
            <div className="flex items-center gap-4 px-4 py-3 border-b border-amber-900/20 bg-stone-900/40">
              <span className="font-mono text-xs text-amber-700">
                {String(scene.scene_number || i + 1).padStart(2, '0')}
              </span>
              <span className="font-mono text-xs text-stone-500">
                {scene.timecode_start || '—'}
              </span>
              <span className={`font-mono text-xs ml-auto ${moodColors[scene.mood] || 'text-stone-500'}`}>
                {scene.mood || '—'}
              </span>
              <span className="font-mono text-xs text-stone-600">
                {scene.duration_seconds || '—'}s
              </span>
              {scene.shorts_clip && (
                <span className="text-xs px-2 py-0.5 border border-amber-700/40 text-amber-600 font-mono">
                  SHORT
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-0 divide-x divide-amber-900/20">
              {/* Narration */}
              <div className="p-4">
                <label className="block text-xs text-amber-800 uppercase tracking-widest mb-2">
                  Narration
                </label>
                <textarea
                  value={scene.narration || ''}
                  onChange={e => updateScene(i, 'narration', e.target.value)}
                  rows={5}
                  className="w-full bg-transparent text-amber-100 font-serif text-sm leading-relaxed
                             resize-none focus:outline-none placeholder:text-stone-700"
                  placeholder="Narration text…"
                />
              </div>

              {/* Visual */}
              <div className="p-4">
                <label className="block text-xs text-amber-800 uppercase tracking-widest mb-2">
                  Visual Description
                </label>
                <textarea
                  value={scene.visual_description || ''}
                  onChange={e => updateScene(i, 'visual_description', e.target.value)}
                  rows={5}
                  className="w-full bg-transparent text-stone-400 font-serif text-sm leading-relaxed
                             resize-none focus:outline-none italic placeholder:text-stone-700"
                  placeholder="What is shown on screen…"
                />
              </div>
            </div>

            {scene.music_note && (
              <div className="px-4 py-2 border-t border-amber-900/20 bg-stone-900/20">
                <span className="text-xs text-stone-600 font-mono">♪ {scene.music_note}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {scenes.length === 0 && (
        <div className="text-center py-20 text-stone-600 font-serif italic">
          Script not yet generated. Return to the pipeline monitor.
        </div>
      )}
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-64 text-amber-800 font-mono text-sm">
      Loading script…
    </div>
  )
}

function ErrorState({ message }) {
  return (
    <div className="max-w-xl mx-auto mt-20 p-6 border border-red-800 text-red-400 font-mono text-sm">
      {message}
    </div>
  )
}

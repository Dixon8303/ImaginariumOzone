import { useState, useEffect, useCallback } from 'react'

export function usePipeline(episodeId) {
  const [stages, setStages] = useState({})
  const [connected, setConnected] = useState(false)
  const [episode, setEpisode] = useState(null)
  const [lastEvent, setLastEvent] = useState(null)

  const STAGE_ORDER = [
    'topic_scoring', 'research', 'script', 'seo', 'voice_ssml',
    'asset_planning', 'generation', 'ken_burns', 'assembly', 'shorts'
  ]

  useEffect(() => {
    if (!episodeId) return
    const es = new EventSource(`/api/pipeline/status/${episodeId}`)

    es.onopen = () => setConnected(true)
    es.onerror = () => setConnected(false)

    es.onmessage = (e) => {
      const event = JSON.parse(e.data)
      setLastEvent(event)

      if (event.type === 'current_state' && event.episode) {
        setEpisode(event.episode)
        const stageMap = {}
        for (const s of event.episode.stages || []) {
          stageMap[s.stage_name] = s
        }
        setStages(stageMap)
        return
      }

      if (event.type === 'stage_start' || event.type === 'stage_done' || event.type === 'stage_failed') {
        setStages(prev => ({
          ...prev,
          [event.stage]: { stage_name: event.stage, status: stageStatusFromEvent(event.type) }
        }))
      }

      if (event.type === 'gate') {
        setEpisode(prev => prev ? { ...prev, status: `${event.stage}_review` } : prev)
      }
    }

    return () => es.close()
  }, [episodeId])

  const stageList = STAGE_ORDER.map(name => ({
    name,
    label: stageLabel(name),
    status: stages[name]?.status || 'pending'
  }))

  return { stageList, connected, episode, lastEvent }
}

function stageStatusFromEvent(type) {
  if (type === 'stage_start') return 'running'
  if (type === 'stage_done') return 'done'
  if (type === 'stage_failed') return 'failed'
  return 'pending'
}

function stageLabel(name) {
  const labels = {
    topic_scoring: 'Topic Scoring',
    research: 'Research',
    script: 'Script Generation',
    seo: 'SEO Package',
    voice_ssml: 'Voice & SSML',
    asset_planning: 'Asset Planning',
    generation: 'Generation',
    ken_burns: 'Ken Burns Effects',
    assembly: 'Video Assembly',
    shorts: 'Shorts Extraction',
  }
  return labels[name] || name
}

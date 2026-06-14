import { useState, useEffect } from 'react'

export function usePipeline(episodeId) {
  const [stages, setStages] = useState({})
  const [connected, setConnected] = useState(false)
  const [episode, setEpisode] = useState(null)
  const [lastEvent, setLastEvent] = useState(null)

  const STAGE_ORDER = [
    'topic_scoring', 'research', 'outline', 'script', 'seo',
    'voice_ssml', 'asset_planning', 'generation',
    'ken_burns', 'assembly', 'shorts', 'qa_gates',
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

      if (['stage_start', 'stage_done', 'stage_failed'].includes(event.type)) {
        setStages(prev => ({
          ...prev,
          [event.stage]: {
            stage_name: event.stage,
            status: stageStatusFromEvent(event.type),
            tier: event.tier || null,
            autonomy: event.autonomy || null,
          }
        }))
      }

      if (event.type === 'gate') {
        setEpisode(prev => prev ? { ...prev, status: `${event.stage}_review` } : prev)
      }

      if (event.type === 'hard_halt') {
        setEpisode(prev => prev ? { ...prev, status: 'halted' } : prev)
      }
    }

    return () => es.close()
  }, [episodeId])

  const stageList = STAGE_ORDER.map(name => ({
    name,
    label: stageLabel(name),
    status: stages[name]?.status || 'pending',
    tier: stages[name]?.tier || null,
    autonomy: stages[name]?.autonomy || null,
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
    topic_scoring:  'P1 · Topic Score + G1/G2',
    research:       'P2 · Research (Fable)',
    outline:        'P3 · Outline',
    script:         'P4 · Script (Opus)',
    seo:            'P8 · SEO Metadata',
    voice_ssml:     'P5 · Voice & SSML',
    asset_planning: 'P6 · Storyboard',
    generation:     'P6 · Asset Generation',
    ken_burns:      'Ken Burns Effects',
    assembly:       'Episode Assembly',
    shorts:         'P9 · Shorts',
    qa_gates:       'P10 · QA Gates G3–G5',
  }
  return labels[name] || name
}

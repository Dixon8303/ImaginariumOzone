const BASE = '/api'

async function req(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Episodes
  listEpisodes: () => req('GET', '/episodes'),
  createEpisode: (topic, mode) => req('POST', '/episodes', { topic, mode }),
  getEpisode: (id) => req('GET', `/episodes/${id}`),
  updateEpisode: (id, data) => req('PATCH', `/episodes/${id}`, data),
  deleteEpisode: (id) => req('DELETE', `/episodes/${id}`),

  // Pipeline
  startPipeline: (id) => req('POST', `/pipeline/start/${id}`),
  resumePipeline: (id, fromStage) =>
    req('POST', `/pipeline/resume/${id}${fromStage ? `?from_stage=${fromStage}` : ''}`),
  triggerUpload: (id, privacy = 'private') =>
    req('POST', `/pipeline/upload/${id}`, { privacy }),

  // Assets
  listAssets: (episodeId) => req('GET', `/assets/episode/${episodeId}`),
  approveAsset: (id) => req('PATCH', `/assets/${id}`, { status: 'approved' }),
  rejectAsset: (id) => req('PATCH', `/assets/${id}`, { status: 'rejected' }),
  regenerateAsset: (id) => req('POST', `/assets/${id}/regenerate`),
  assetFileUrl: (id) => `${BASE}/assets/${id}/file`,
  finalVideoUrl: (episodeId) => `${BASE}/assets/episode/${episodeId}/final`,
  thumbnailUrl: (episodeId) => `${BASE}/assets/episode/${episodeId}/thumbnail`,

  // Orchestration: gates, stage runs, mutation log, title variants
  getGates: (id) => req('GET', `/pipeline/gates/${id}`),
  getStageRuns: (id) => req('GET', `/pipeline/stage-runs/${id}`),
  getMutationLog: (id, limit = 50) => req('GET', `/pipeline/mutation-log/${id}?limit=${limit}`),
  getTitleVariants: (id) => req('GET', `/pipeline/title-variants/${id}`),
  gateOverride: (id, gateId, result, rationale, advanceTo) =>
    req('POST', `/pipeline/gate-override/${id}/${gateId}`,
        { result, rationale, advance_to: advanceTo }),

  // Analytics
  recordPerformance: (episodeId, metrics) =>
    req('POST', `/analytics/performance/${episodeId}`, metrics),
  getPerformance: (episodeId) => req('GET', `/analytics/performance/${episodeId}`),
  getInterventions: (episodeId) => req('GET', `/analytics/interventions/${episodeId}`),
  getWarRoom: () => req('GET', '/analytics/war-room'),
}

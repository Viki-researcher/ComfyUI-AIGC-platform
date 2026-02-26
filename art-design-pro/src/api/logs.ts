import request from '@/utils/http'

export function fetchCreateLog(params: Api.DataGen.LogCreateParams) {
  return request.post<any>({
    url: '/api/logs',
    params,
    showSuccessMessage: true
  })
}

export function fetchGetLogs(params: Partial<Api.DataGen.LogList> & Record<string, any>) {
  return request.get<Api.DataGen.LogList>({
    url: '/api/logs',
    params
  })
}

export function fetchExportLogs(params: {
  user_id?: number
  project_id?: number
  status?: string
  start?: string
  end?: string
}) {
  const query = new URLSearchParams()
  if (params.user_id) query.set('user_id', String(params.user_id))
  if (params.project_id) query.set('project_id', String(params.project_id))
  if (params.status) query.set('status', params.status)
  if (params.start) query.set('start', params.start)
  if (params.end) query.set('end', params.end)

  const url = `/api/logs/export?${query.toString()}`
  window.open(url, '_blank')
}

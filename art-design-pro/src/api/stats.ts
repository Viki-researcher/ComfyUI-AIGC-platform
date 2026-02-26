import request from '@/utils/http'

export function fetchGetStats(params: {
  dimension: Api.DataGen.StatsDimension
  start_date?: string
  end_date?: string
}) {
  return request.get<any[]>({
    url: '/api/stats',
    params
  })
}

export function fetchGetStatsTrend(params: {
  group_by: string
  start_date?: string
  end_date?: string
}) {
  return request.get<{ dates: string[]; series: { name: string; data: number[] }[] }>({
    url: '/api/stats/trend',
    params
  })
}

export function fetchExportStats(params: {
  dimension: Api.DataGen.StatsDimension
  start_date?: string
  end_date?: string
}) {
  return request.get<any>({
    url: '/api/export',
    params
  })
}

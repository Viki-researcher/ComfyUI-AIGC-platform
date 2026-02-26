import axios from 'axios'
import { useUserStore } from '@/store/modules/user'
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

export async function fetchExportLogs(params: {
  user_id?: number
  project_id?: number
  status?: string
  start?: string
  end?: string
}) {
  const query: Record<string, string> = {}
  if (params.user_id) query.user_id = String(params.user_id)
  if (params.project_id) query.project_id = String(params.project_id)
  if (params.status) query.status = params.status
  if (params.start) query.start = params.start
  if (params.end) query.end = params.end

  const { VITE_API_URL } = import.meta.env
  const { accessToken } = useUserStore()

  const res = await axios.get(`${VITE_API_URL}/api/logs/export`, {
    params: query,
    responseType: 'blob',
    headers: { Authorization: accessToken || '' }
  })

  const blob = new Blob([res.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  })
  const disposition = res.headers['content-disposition'] || ''
  const match = disposition.match(/filename="?([^";\s]+)"?/)
  const filename = match ? match[1] : `generation_logs_export.xlsx`

  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

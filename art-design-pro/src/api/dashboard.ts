import request from '@/utils/http'

export function fetchDashboard() {
  return request.get<Api.DataGen.DashboardOverview>({
    url: '/api/dashboard'
  })
}

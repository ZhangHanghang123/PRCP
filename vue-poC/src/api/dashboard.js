import request from './request'

export const dashboardApi = {
  overview: () => request.get('/dashboard/overview'),
  kpiTrend: (days = 14) => request.get('/dashboard/kpi-trend', { params: { days } }),
  schemeDistribution: () => request.get('/dashboard/scheme-distribution'),
  topKpis: () => request.get('/dashboard/top-kpis')
}
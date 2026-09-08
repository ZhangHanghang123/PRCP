import axios, { AxiosInstance } from 'axios'
import { message } from 'antd'

const TOKEN_KEY = 'prcp_token'
export const getToken = () => localStorage.getItem(TOKEN_KEY) || ''
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

const http: AxiosInstance = axios.create({ baseURL: '/prcp/api', timeout: 30000 })
http.interceptors.request.use((c) => {
  const t = getToken(); if (t) c.headers.Authorization = `Bearer ${t}`; return c
})
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      clearToken()
      if (!location.pathname.includes('/login')) location.href = '/prcp/login'
    } else if (err.response?.data?.detail) {
      const d = err.response.data.detail
      message.error(typeof d === 'string' ? d : JSON.stringify(d))
    } else if (err.message) message.error(err.message)
    return Promise.reject(err)
  }
)

export const authApi = {
  login: (username: string, password: string) => {
    const fd = new FormData(); fd.append('username', username); fd.append('password', password)
    return http.post('/auth/login', fd).then((r) => r.data)
  },
  me: () => http.get('/auth/me').then((r) => r.data),
}
export const dashboardApi = {
  overview: () => http.get('/dashboard/overview').then((r) => r.data),
  taskTrend: (days = 14) => http.get('/dashboard/task-trend', { params: { days } }).then((r) => r.data),
  currencyDistribution: () => http.get('/dashboard/currency-distribution').then((r) => r.data),
}
export const groupsApi = {
  list: (params: any = {}) => http.get('/groups', { params }).then((r) => r.data),
  create: (data: any) => http.post('/groups', data).then((r) => r.data),
  update: (id: number, data: any) => http.put(`/groups/${id}`, data).then((r) => r.data),
  delete: (id: number) => http.delete(`/groups/${id}`).then((r) => r.data),
}
export const positionsApi = {
  list: (params: any = {}) => http.get('/positions', { params }).then((r) => r.data),
  create: (data: any) => http.post('/positions', data).then((r) => r.data),
  update: (id: number, data: any) => http.put(`/positions/${id}`, data).then((r) => r.data),
  delete: (id: number) => http.delete(`/positions/${id}`).then((r) => r.data),
  gap: (params: any = {}) => http.get('/positions/gap', { params }).then((r) => r.data),
}
export const rulesApi = {
  list: (params: any = {}) => http.get('/rules', { params }).then((r) => r.data),
  create: (data: any) => http.post('/rules', data).then((r) => r.data),
  update: (id: number, data: any) => http.put(`/rules/${id}`, data).then((r) => r.data),
  delete: (id: number) => http.delete(`/rules/${id}`).then((r) => r.data),
}
export const tasksApi = {
  list: (params: any = {}) => http.get('/tasks', { params }).then((r) => r.data),
  create: (data: any) => http.post('/tasks', data).then((r) => r.data),
  run: (id: number) => http.post(`/tasks/${id}/run`).then((r) => r.data),
  log: (id: number) => http.get(`/tasks/${id}/log`).then((r) => r.data),
}
// metricItemsApi 已废弃：193 条数据已迁移到 prcp_rpt_item，请使用 reportsApi

// 账户册
export const coaApi = {
  listSchemes: (params: any = {}) => http.get('/coa/schemes', { params }).then((r) => r.data),
  createScheme: (data: any) => http.post('/coa/schemes', data).then((r) => r.data),
  updateScheme: (id: number, data: any) => http.put(`/coa/schemes/${id}`, data).then((r) => r.data),
  deleteScheme: (id: number) => http.delete(`/coa/schemes/${id}`).then((r) => r.data),
  listNodes: (schemeId: number) => http.get('/coa/nodes', { params: { scheme_id: schemeId } }).then((r) => r.data),
  treeNodes: (schemeId: number) => http.get('/coa/nodes/tree', { params: { scheme_id: schemeId } }).then((r) => r.data),
  createNode: (data: any) => http.post('/coa/nodes', data).then((r) => r.data),
  updateNode: (id: number, data: any) => http.put(`/coa/nodes/${id}`, data).then((r) => r.data),
  deleteNode: (id: number) => http.delete(`/coa/nodes/${id}`).then((r) => r.data),
}

// 报表
export const reportsApi = {
  list: (params: any = {}) => http.get('/reports/', { params }).then((r) => r.data),
  create: (data: any) => http.post('/reports/', data).then((r) => r.data),
  update: (id: number, data: any) => http.put(`/reports/${id}`, data).then((r) => r.data),
  delete: (id: number) => http.delete(`/reports/${id}`).then((r) => r.data),
  listItems: (reportId: number) => http.get('/reports/items', { params: { report_id: reportId } }).then((r) => r.data),
  treeItems: (reportId: number) => http.get('/reports/items/tree', { params: { report_id: reportId } }).then((r) => r.data),
  createItem: (data: any) => http.post('/reports/items', data).then((r) => r.data),
  updateItem: (id: number, data: any) => http.put(`/reports/items/${id}`, data).then((r) => r.data),
  deleteItem: (id: number) => http.delete(`/reports/items/${id}`).then((r) => r.data),
  batchItems: (reportId: number, payload: any) => http.post('/reports/items/batch', payload, { params: { report_id: reportId } }).then((r) => r.data),
}

// 资产负债表
export const balanceApi = {
  list: (params: any = {}) => http.get('/balance/', { params }).then((r) => r.data),
  upsert: (data: any) => http.post('/balance/', data).then((r) => r.data),
  delete: (id: number) => http.delete(`/balance/${id}`).then((r) => r.data),
  gapSummary: (dataDate: string) => http.get('/balance/gap-summary', { params: { data_date: dataDate } }).then((r) => r.data),
}

// 指标（v2：方案 + 定义 + 维护）
export const kpiApi = {
  // 方案
  listSchemes: (params: any = {}) => http.get('/kpi/schemes', { params }).then((r) => r.data),
  createScheme: (data: any) => http.post('/kpi/schemes', data).then((r) => r.data),
  updateScheme: (id: number, data: any) => http.put(`/kpi/schemes/${id}`, data).then((r) => r.data),
  deleteScheme: (id: number) => http.delete(`/kpi/schemes/${id}`).then((r) => r.data),
  // 报表表项（供定义公式引用）
  listRptItems: (params: any = {}) => http.get('/kpi/rpt-items', { params }).then((r) => r.data),
  // 定义
  listDefs: (params: any = {}) => http.get('/kpi/definitions', { params }).then((r) => r.data),
  createDef: (data: any) => http.post('/kpi/definitions', data).then((r) => r.data),
  updateDef: (id: number, data: any) => http.put(`/kpi/definitions/${id}`, data).then((r) => r.data),
  deleteDef: (id: number) => http.delete(`/kpi/definitions/${id}`).then((r) => r.data),
  // 值
  listValues: (params: any = {}) => http.get('/kpi/values', { params }).then((r) => r.data),
  upsertValue: (data: any) => http.post('/kpi/values', data).then((r) => r.data),
  deleteValue: (id: number) => http.delete(`/kpi/values/${id}`).then((r) => r.data),
  // 公式引擎
  formulaEval: (formula: string, ctx: any = {}) => http.post('/kpi/formula/eval', { formula, ctx }).then((r) => r.data),
  formulaValidate: (formula: string) => http.post('/kpi/formula/validate', { formula }).then((r) => r.data),
  recalc: (kpiId: number, dataDate: string) =>
    http.post('/kpi/recalc', null, { params: { kpi_id: kpiId, data_date: dataDate } }).then((r) => r.data),
}
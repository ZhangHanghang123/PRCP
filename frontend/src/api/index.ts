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
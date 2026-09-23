import request from './request'

export const reportsApi = {
  list: (params = {}) => request.get('/reports/', { params }),
  create: (data: any) => request.post('/reports/', data),
  update: (id: number, data: any) => request.put(`/reports/${id}`, data),
  delete: (id: number) => request.delete(`/reports/${id}`),
  listItems: (reportId: number) => request.get('/reports/items', { params: { report_id: reportId } }),
  createItem: (data: any) => request.post('/reports/items', data),
  updateItem: (id: number, data: any) => request.put(`/reports/items/${id}`, data),
  deleteItem: (id: number) => request.delete(`/reports/items/${id}`)
}
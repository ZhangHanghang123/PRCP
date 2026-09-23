import request from './request'

export const reportsApi = {
  list: (params = {}) => request.get('/reports/', { params }),
  create: (data) => request.post('/reports/', data),
  update: (id, data) => request.put(`/reports/${id}`, data),
  delete: (id) => request.delete(`/reports/${id}`),
  listItems: (reportId) => request.get('/reports/items', { params: { report_id: reportId } }),
  createItem: (data) => request.post('/reports/items', data),
  updateItem: (id, data) => request.put(`/reports/items/${id}`, data),
  deleteItem: (id) => request.delete(`/reports/items/${id}`)
}
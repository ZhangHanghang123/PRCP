import request from './request'

export const coaApi = {
  // 方案
  listSchemes: () => request.get('/coa/schemes'),
  getScheme: (id) => request.get(`/coa/scheme/${id}`),
  createScheme: (data) => request.post('/coa/scheme', data),
  updateScheme: (id, data) => request.put(`/coa/scheme/${id}`, data),
  deleteScheme: (id) => request.delete(`/coa/scheme/${id}`),

  // 节点
  listNodes: (schemeId) => request.get('/coa/nodes', { params: { scheme_id: schemeId } }),
  listTree: (schemeId) => request.get('/coa/nodes/tree', { params: { scheme_id: schemeId } }),
  createNode: (data) => request.post('/coa/node', data),
  updateNode: (id, data) => request.put(`/coa/node/${id}`, data),
  deleteNode: (id) => request.delete(`/coa/node/${id}`)
}

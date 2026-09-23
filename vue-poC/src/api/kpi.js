import request from './request'

export const kpiApi = {
  listSchemes: () => request.get('/kpi/schemes'),
  listSchemesAll: () => request.get('/kpi/schemes/all'),
  createScheme: (data) => request.post('/kpi/schemes', data),
  updateScheme: (id, data) => request.put(`/kpi/schemes/${id}`, data),
  deleteScheme: (id) => request.delete(`/kpi/schemes/${id}`),
  listDefs: (params = {}) => request.get('/kpi/definitions', { params }),
  createDef: (data) => request.post('/kpi/definitions', data),
  updateDef: (id, data) => request.put(`/kpi/definitions/${id}`, data),
  deleteDef: (id) => request.delete(`/kpi/definitions/${id}`),
  listValues: (params = {}) => request.get('/kpi/values', { params }),
  createValue: (data) => request.post('/kpi/values', data),
  deleteValue: (id) => request.delete(`/kpi/values/${id}`),
  recalc: (kpiId, dataDate) =>
    request.post('/kpi/recalc', null, { params: { kpi_id: kpiId, data_date: dataDate } }),
  listScoreRules: (params = {}) => request.get('/kpi/score-rules', { params }),
  createScoreRule: (data) => request.post('/kpi/score-rules', data),
  deleteScoreRule: (id) => request.delete(`/kpi/score-rules/${id}`),
  listRptItems: (rptId) => request.get('/kpi/rpt-items', { params: { rpt_id: rptId } })
}
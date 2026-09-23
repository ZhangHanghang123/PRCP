import request from './request'

export const kpiApi = {
  listSchemes: () => request.get('/kpi/schemes'),
  listDefs: (params: any = {}) => request.get('/kpi/definitions', { params }),
  createDef: (data: any) => request.post('/kpi/definitions', data),
  updateDef: (id: number, data: any) => request.put(`/kpi/definitions/${id}`, data),
  deleteDef: (id: number) => request.delete(`/kpi/definitions/${id}`),
  listValues: (params: any = {}) => request.get('/kpi/values', { params }),
  createValue: (data: any) => request.post('/kpi/values', data),
  deleteValue: (id: number) => request.delete(`/kpi/values/${id}`),
  recalc: (kpiId: number, dataDate: string) =>
    request.post('/kpi/recalc', null, { params: { kpi_id: kpiId, data_date: dataDate } }),
  listScoreRules: (params: any = {}) => request.get('/kpi/score-rules', { params }),
  createScoreRule: (data: any) => request.post('/kpi/score-rules', data),
  deleteScoreRule: (id: number) => request.delete(`/kpi/score-rules/${id}`),
  listRptItems: (rptId: number) => request.get('/kpi/rpt-items', { params: { rpt_id: rptId } })
}
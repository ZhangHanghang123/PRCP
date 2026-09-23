import request from './request'

export const metricApi = {
  list: (params) => request.get('/metric-coefficient', { params }),
  options: (schemeId) => request.get('/metric-coefficient/options', { params: { schemeId } }),
  create: (data) => request.post('/metric-coefficient', data),
  update: (id, data) => request.put('/metric-coefficient/' + id, data),
  remove: (id) => request.delete('/metric-coefficient/' + id)
}

export const reverseMetricTableApi = {
  query: (params) => request.get('/reverse-metric-table', { params }),
  options: () => request.get('/reverse-metric-table/options')
}
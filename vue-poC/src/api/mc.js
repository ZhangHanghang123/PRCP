import request from './request'

export const metricApi = {
  list: (params) => request.get('/metric-coefficient', { params }),
  options: (schemeId) => {
    // schemeId 为 null 时不传参数，避免 axios 把 null 序列化成 "null" 字符串触发 Spring 转换失败
    const cfg = schemeId == null ? {} : { params: { schemeId } }
    return request.get('/metric-coefficient/options', cfg)
  },
  create: (data) => request.post('/metric-coefficient', data),
  update: (id, data) => request.put('/metric-coefficient/' + id, data),
  remove: (id) => request.delete('/metric-coefficient/' + id)
}

export const reverseMetricTableApi = {
  query: (params) => request.get('/reverse-metric-table', { params }),
  options: () => request.get('/reverse-metric-table/options')
}
import request from './request'

export const basicDataApi = {
  dates: (schemeId) => request.get('/basic-data/dates', { params: schemeId == null ? {} : { schemeId } }),
  list: (params = {}) => request.get('/basic-data/list', { params }),
  matrix: (params = {}) => request.get('/basic-data/matrix', { params }),
  upsert: (data) => request.post('/basic-data/upsert', data),
  remove: (id) => request.delete('/basic-data/' + id)
}

export const reverseDataApi = {
  dates: () => request.get('/reverse-data/dates'),
  list: (params = {}) => request.get('/reverse-data/list', { params }),
  matrix: (params = {}) => request.get('/reverse-data/matrix', { params }),
  upsert: (data) => request.post('/reverse-data/upsert', data),
  remove: (id) => request.delete('/reverse-data/' + id)
}
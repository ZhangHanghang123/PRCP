import request from './request'

// 用户
export const adminApi = {
  listUsers: (keyword) => request.get('/admin/users', { params: { keyword } }),
  createUser: (data) => request.post('/admin/users', data),
  updateUser: (id, data) => request.put('/admin/users/' + id, data),
  deleteUser: (id) => request.delete('/admin/users/' + id),
  resetPassword: (id, password) => request.post('/admin/users/' + id + '/reset-password', { password })
}

// 角色
export const roleApi = {
  list: () => request.get('/admin/roles'),
  create: (data) => request.post('/admin/roles', data),
  update: (id, data) => request.put('/admin/roles/' + id, data),
  remove: (id) => request.delete('/admin/roles/' + id)
}

// 字典
export const dictApi = {
  list: (keyword) => request.get('/dict/all', { params: { keyword } }),
  listByType: (type, keyword) => request.get('/dict/' + type, { params: { keyword } }),
  listTypes: () => request.get('/dict/types'),
  listTypesSummary: () => request.get('/dict/types/summary'),
  create: (data) => request.post('/dict', data),
  update: (id, data) => request.put('/dict/' + id, data),
  remove: (id) => request.delete('/dict/' + id),
  listItems: (dictId) => request.get('/dict/' + dictId + '/items'),
  createItem: (dictId, data) => request.post('/dict/' + dictId + '/items', data),
  deleteItem: (itemId) => request.delete('/dict/items/' + itemId)
}
import request from './request'

export const authApi = {
  login: (data) => request.post('/auth/login', data),
  health: () => request.post('/auth/health')
}

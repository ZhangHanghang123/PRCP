/**
 * Token 工具
 */
const TOKEN_KEY = 'prcp-java-token'
const USER_KEY = 'prcp-java-user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getUser() {
  const s = localStorage.getItem(USER_KEY)
  return s ? JSON.parse(s) : null
}

export function setUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function removeUser() {
  localStorage.removeItem(USER_KEY)
}

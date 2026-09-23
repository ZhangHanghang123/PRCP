import { getToken, setToken, removeToken, getUser, setUser, removeUser } from '@/utils/auth'

const state = {
  token: getToken(),
  user: getUser()
}

const mutations = {
  SET_TOKEN(state, token) {
    state.token = token
    setToken(token)
  },
  SET_USER(state, user) {
    state.user = user
    setUser(user)
  },
  CLEAR(state) {
    state.token = null
    state.user = null
    removeToken()
    removeUser()
  }
}

const actions = {
  login({ commit }, payload) {
    return new Promise((resolve, reject) => {
      import('@/api/auth').then(({ authApi }) => {
        authApi.login(payload).then(res => {
          commit('SET_TOKEN', res.access_token)
          commit('SET_USER', { id: res.user_id, username: res.username, real_name: res.real_name })
          resolve(res)
        }).catch(reject)
      })
    })
  },
  logout({ commit }) {
    commit('CLEAR')
  }
}

const getters = {
  token: state => state.token,
  user: state => state.user,
  isLoggedIn: state => !!state.token
}

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters
}

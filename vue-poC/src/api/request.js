import axios from 'axios'
import { Message, MessageBox } from 'element-ui'
import router from '@/router'
import { getToken, removeToken, removeUser } from '@/utils/auth'

const service = axios.create({
  baseURL: process.env.VUE_APP_BASE_API,
  timeout: 30000
})

service.interceptors.request.use(
  config => {
    const token = getToken()
    if (token) config.headers['Authorization'] = `Bearer ${token}`
    return config
  },
  error => Promise.reject(error)
)

service.interceptors.response.use(
  response => {
    const res = response.data
    // Java 端 R<T> 格式：{code, msg, data}
    if (res.code !== 0 && res.code !== 200) {
      Message.error(res.msg || '请求失败')
      if (res.code === 401) {
        MessageBox.confirm('登录已过期，请重新登录', '提示', { confirmButtonText: '重新登录' })
          .then(() => {
            removeToken()
            removeUser()
            router.push('/login')
          })
          .catch(() => {})
      }
      return Promise.reject(new Error(res.msg || 'Error'))
    }
    return res.data
  },
  error => {
    console.error('[Request Error]', error)
    Message.error(error.message || '网络异常')
    return Promise.reject(error)
  }
)

export default service

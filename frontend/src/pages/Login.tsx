import React from 'react'
import { Form, Input, Button, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { authApi, setToken } from '../api'

const Login: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = React.useState(false)

  const onFinish = async (v: { username: string; password: string }) => {
    setLoading(true)
    try {
      const r = await authApi.login(v.username, v.password)
      if (r?.access_token) {
        setToken(r.access_token)
        message.success('登录成功')
        navigate('/dashboard')
      } else {
        message.error('登录失败: 未获取到 token')
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo-icon">组算</div>
          <div className="login-title">PRCP · 组算平台</div>
          <div className="login-subtitle">Portfolio Resource Coordination Platform</div>
        </div>
        <Form name="login" onFinish={onFinish} autoComplete="off">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" size="large" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" size="large" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large"
              className="login-btn-gradient">
              登录
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: 'center', color: '#999', fontSize: 13, marginTop: -8 }}>
          默认账号：admin / admin123
        </div>
      </div>
    </div>
  )
}

export default Login
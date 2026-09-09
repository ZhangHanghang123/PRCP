import React from 'react'
import { Layout, Menu, Dropdown, Avatar } from 'antd'
import {
  DashboardOutlined,
  TeamOutlined,
  BankOutlined,
  ApartmentOutlined,
  ExperimentOutlined,
  PartitionOutlined,
  FileDoneOutlined,
  LineChartOutlined,
  FunctionOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { clearToken } from '../api'

const { Header, Sider, Content, Footer } = Layout

const MainLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const selectedKey = location.pathname

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: 'Dashboard' },
    { key: '/coa', icon: <PartitionOutlined />, label: '账户册维护' },
    { key: '/reports', icon: <FileDoneOutlined />, label: '报表表项管理' },
    { key: '/balance', icon: <LineChartOutlined />, label: '资产负债表' },
    { key: '/kpi', icon: <FunctionOutlined />, label: '指标管理' },
    { key: '/groups', icon: <TeamOutlined />, label: '资金组管理' },
    { key: '/positions', icon: <BankOutlined />, label: '头寸管理' },
    { key: '/rules', icon: <ApartmentOutlined />, label: '组算规则' },
    { key: '/tasks', icon: <ExperimentOutlined />, label: '组算任务' },
    { key: '/system', icon: <SettingOutlined />, label: '系统管理' },
  ]

  const handleLogout = () => {
    clearToken()
    window.location.href = '/prcp/login'
  }

  const userMenu = {
    items: [
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
    ],
  }

  return (
    <Layout className="app-layout">
      <Sider className="app-sider" theme="light" breakpoint="lg" collapsedWidth="0" width={220}>
        <div className="app-sider-logo">PRCP · 组算平台</div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <h2>组算平台 · Portfolio Resource Coordination</h2>
          <Dropdown menu={userMenu} placement="bottomRight">
            <div className="app-header-right" style={{ cursor: 'pointer' }}>
              <Avatar size="small" icon={<UserOutlined />} style={{ background: 'rgba(255,255,255,0.2)' }} />
              <span>管理员</span>
            </div>
          </Dropdown>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
        <Footer className="app-footer">
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span>
              <svg viewBox="0 0 16 16" width="12" height="12" style={{ verticalAlign: '-2px', marginRight: 4 }} fill="currentColor">
                <path d="M8 1l6 2v4c0 4.418-2.866 8.418-6 9-3.134-.582-6-4.582-6-9V3l6-2zm0 2.236L4 4.618V7c0 3.314 2.068 6.34 4 7.022 1.932-.682 4-3.708 4-7.022V4.618L8 3.236zM7 9V7h2v2H7zm0 3v-1h2v1H7z"/>
              </svg>
              <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">京ICP备2026054150号-1</a>
            </span>
            <span style={{ color: '#ddd' }}>|</span>
            <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">京ICP备2026054150号</a>
          </div>
        </Footer>
      </Layout>
    </Layout>
  )
}

export default MainLayout
import React, { useEffect, useState } from 'react'
import {
  Card, Row, Col, Form, Input, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, Tabs, Popconfirm, Statistic, Alert,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  UserOutlined, TeamOutlined, BookOutlined, KeyOutlined,
  LockOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { adminApi } from '../api'

const System: React.FC = () => {
  const [tab, setTab] = useState<'users' | 'roles' | 'dicts'>('users')
  const [loading, setLoading] = useState(false)

  // Users
  const [users, setUsers] = useState<any[]>([])
  const [userKw, setUserKw] = useState('')
  const [userModal, setUserModal] = useState(false)
  const [editingUser, setEditingUser] = useState<any>(null)
  const [userForm] = Form.useForm()
  const [pwdModal, setPwdModal] = useState(false)
  const [pwdUserId, setPwdUserId] = useState<number | null>(null)
  const [pwdForm] = Form.useForm()

  // Roles
  const [roles, setRoles] = useState<any[]>([])
  const [roleKw, setRoleKw] = useState('')
  const [roleModal, setRoleModal] = useState(false)
  const [editingRole, setEditingRole] = useState<any>(null)
  const [roleForm] = Form.useForm()

  // Dicts
  const [dicts, setDicts] = useState<any[]>([])
  const [dictKw, setDictKw] = useState('')
  const [dictModal, setDictModal] = useState(false)
  const [editingDict, setEditingDict] = useState<any>(null)
  const [dictForm] = Form.useForm()
  const [selectedDict, setSelectedDict] = useState<any>(null)
  const [dictItems, setDictItems] = useState<any[]>([])
  const [itemModal, setItemModal] = useState(false)
  const [editingItem, setEditingItem] = useState<any>(null)
  const [itemForm] = Form.useForm()

  // ========== 用户 ==========
  const loadUsers = async () => {
    setLoading(true)
    try {
      const r = await adminApi.listUsers({ keyword: userKw })
      setUsers(r.items || [])
    } finally { setLoading(false) }
  }
  useEffect(() => { if (tab === 'users') loadUsers() }, [tab, userKw])

  const onCreateUser = () => {
    setEditingUser(null)
    userForm.resetFields()
    userForm.setFieldsValue({ role: 'user', status: 1, role_ids: [] })
    setUserModal(true)
  }
  const onEditUser = (u: any) => {
    setEditingUser(u)
    userForm.setFieldsValue({
      username: u.username, display_name: u.display_name,
      role: u.role, status: u.status,
      role_ids: (u.roles || []).map((r: any) => r.id),
    })
    setUserModal(true)
  }
  const onSaveUser = async () => {
    const v = await userForm.validateFields()
    try {
      if (editingUser) {
        // 编辑时不传 password（用重置密码功能）
        const { password, ...rest } = v
        await adminApi.updateUser(editingUser.id, rest)
      } else {
        await adminApi.createUser(v)
      }
      message.success('已保存')
      setUserModal(false)
      loadUsers()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onDeleteUser = async (uid: number) => {
    try {
      await adminApi.deleteUser(uid)
      message.success('已删除')
      loadUsers()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }
  const onResetPwd = async () => {
    const v = await pwdForm.validateFields()
    try {
      await adminApi.resetPassword(pwdUserId!, v.new_password)
      message.success('密码已重置')
      setPwdModal(false)
      pwdForm.resetFields()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '重置失败')
    }
  }

  // ========== 角色 ==========
  const loadRoles = async () => {
    setLoading(true)
    try {
      const r = await adminApi.listRoles({ keyword: roleKw })
      setRoles(r.items || [])
    } finally { setLoading(false) }
  }
  useEffect(() => { if (tab === 'roles') loadRoles() }, [tab, roleKw])

  const onCreateRole = () => {
    setEditingRole(null)
    roleForm.resetFields()
    roleForm.setFieldsValue({ status: 1 })
    setRoleModal(true)
  }
  const onEditRole = (r: any) => {
    setEditingRole(r)
    roleForm.setFieldsValue(r)
    setRoleModal(true)
  }
  const onSaveRole = async () => {
    const v = await roleForm.validateFields()
    try {
      if (editingRole) await adminApi.updateRole(editingRole.id, v)
      else await adminApi.createRole(v)
      message.success('已保存')
      setRoleModal(false)
      loadRoles()
      // 如果在 users Tab，可能需要刷新用户的 roles
      if (tab === 'users') loadUsers()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onDeleteRole = async (rid: number) => {
    try {
      await adminApi.deleteRole(rid)
      message.success('已删除')
      loadRoles()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }

  // ========== 字典 ==========
  const loadDicts = async () => {
    setLoading(true)
    try {
      const r = await adminApi.listDicts({ keyword: dictKw })
      setDicts(r.items || [])
      // 默认选第一个
      if (!selectedDict && r.items?.length) {
        setSelectedDict(r.items[0])
      }
    } finally { setLoading(false) }
  }
  const loadDictItems = async (dictId: number) => {
    try {
      const r = await adminApi.listDictItems(dictId)
      setDictItems(r.items || [])
    } catch { setDictItems([]) }
  }
  useEffect(() => { if (tab === 'dicts') loadDicts() }, [tab, dictKw])
  useEffect(() => { if (selectedDict) loadDictItems(selectedDict.id) }, [selectedDict])

  const onCreateDict = () => {
    setEditingDict(null)
    dictForm.resetFields()
    dictForm.setFieldsValue({ status: 1 })
    setDictModal(true)
  }
  const onEditDict = (d: any) => {
    setEditingDict(d)
    dictForm.setFieldsValue(d)
    setDictModal(true)
  }
  const onSaveDict = async () => {
    const v = await dictForm.validateFields()
    try {
      if (editingDict) await adminApi.updateDict(editingDict.id, v)
      else await adminApi.createDict(v)
      message.success('已保存')
      setDictModal(false)
      loadDicts()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onDeleteDict = async (did: number) => {
    try {
      await adminApi.deleteDict(did)
      message.success('已删除')
      if (selectedDict?.id === did) {
        setSelectedDict(null); setDictItems([])
      }
      loadDicts()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }

  // 字典项
  const onCreateItem = () => {
    if (!selectedDict) { message.warning('请先选择字典'); return }
    setEditingItem(null)
    itemForm.resetFields()
    itemForm.setFieldsValue({ sort_order: 0, status: 1 })
    setItemModal(true)
  }
  const onEditItem = (it: any) => {
    setEditingItem(it)
    itemForm.setFieldsValue(it)
    setItemModal(true)
  }
  const onSaveItem = async () => {
    const v = await itemForm.validateFields()
    try {
      if (editingItem) await adminApi.updateDictItem(editingItem.id, v)
      else await adminApi.createDictItem(selectedDict.id, v)
      message.success('已保存')
      setItemModal(false)
      loadDictItems(selectedDict.id)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onDeleteItem = async (iid: number) => {
    try {
      await adminApi.deleteDictItem(iid)
      message.success('已删除')
      loadDictItems(selectedDict.id)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }

  // ========== 列定义 ==========
  const userCols: ColumnsType<any> = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '用户名', dataIndex: 'username', width: 130, render: (c) => <code>{c}</code> },
    { title: '显示名', dataIndex: 'display_name', width: 150 },
    { title: '角色', dataIndex: 'roles', width: 200,
      render: (roles: any[]) => roles?.length ? roles.map((r) => (
        <Tag key={r.id} color="purple">{r.role_name}</Tag>
      )) : <span style={{ color: '#ccc' }}>无</span> },
    { title: '内置', dataIndex: 'role', width: 100,
      render: (r) => <Tag color={r === 'admin' ? 'red' : 'default'}>{r}</Tag> },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (s) => <Tag color={s === 1 ? 'green' : 'default'}>{s === 1 ? '启用' : '禁用'}</Tag> },
    { title: '创建时间', dataIndex: 'created_at', width: 170 },
    {
      title: '操作', width: 220, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditUser(r)}>编辑</Button>
          <Button size="small" icon={<KeyOutlined />} onClick={() => { setPwdUserId(r.id); setPwdModal(true) }}>重置密码</Button>
          {r.id !== 1 && (
            <Popconfirm title="确认删除？" onConfirm={() => onDeleteUser(r.id)}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const roleCols: ColumnsType<any> = [
    { title: '角色编码', dataIndex: 'role_code', width: 130, render: (c) => <code>{c}</code> },
    { title: '角色名称', dataIndex: 'role_name', width: 150 },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '关联用户', dataIndex: 'user_count', width: 100,
      render: (n) => <Tag color="blue">{n || 0}</Tag> },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (s) => <Tag color={s === 1 ? 'green' : 'default'}>{s === 1 ? '启用' : '禁用'}</Tag> },
    {
      title: '操作', width: 150, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditRole(r)}>编辑</Button>
          <Popconfirm title="确认删除？" description="将解除所有用户的此角色关联" onConfirm={() => onDeleteRole(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const dictCols: ColumnsType<any> = [
    { title: '字典编码', dataIndex: 'dict_code', width: 150, render: (c) => <code>{c}</code> },
    { title: '字典名称', dataIndex: 'dict_name', width: 150 },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '项数', dataIndex: 'item_count', width: 80, render: (n) => <Tag color="blue">{n || 0}</Tag> },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (s) => <Tag color={s === 1 ? 'green' : 'default'}>{s === 1 ? '启用' : '禁用'}</Tag> },
    {
      title: '操作', width: 150, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" type={r.id === selectedDict?.id ? 'primary' : 'default'}
            onClick={() => { setSelectedDict(r); loadDictItems(r.id) }}>
            查看项
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditDict(r)}>编辑</Button>
          <Popconfirm title="确认删除？" description="将同时软删所有字典项" onConfirm={() => onDeleteDict(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const itemCols: ColumnsType<any> = [
    { title: '项编码', dataIndex: 'item_code', width: 130, render: (c) => <code>{c}</code> },
    { title: '项名称', dataIndex: 'item_name', width: 150 },
    { title: '项值', dataIndex: 'item_value', width: 150 },
    { title: '排序', dataIndex: 'sort_order', width: 80 },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (s) => <Tag color={s === 1 ? 'green' : 'default'}>{s === 1 ? '启用' : '禁用'}</Tag> },
    {
      title: '操作', width: 120, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditItem(r)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => onDeleteItem(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // ========== 渲染 ==========
  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>系统管理 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>· 用户 · 角色 · 字典</span></span>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic title="用户总数" value={users.length} prefix={<UserOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="角色总数" value={roles.length} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="字典分类" value={dicts.length} prefix={<BookOutlined />} />
          </Card>
        </Col>
      </Row>

      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Tabs
          activeKey={tab} onChange={(k) => setTab(k as any)}
          items={[
            // ========== 用户管理 ==========
            { key: 'users', label: <span><UserOutlined /> 用户管理</span>, children: (
              <div style={{ padding: 16 }}>
                <Space style={{ marginBottom: 12 }}>
                  <Input.Search
                    placeholder="搜索用户名 / 显示名"
                    value={userKw}
                    onChange={(e) => setUserKw(e.target.value)}
                    style={{ width: 240 }}
                    allowClear
                  />
                  <Button icon={<ReloadOutlined />} onClick={loadUsers}>刷新</Button>
                  <Button type="primary" icon={<PlusOutlined />} onClick={onCreateUser}>新增用户</Button>
                </Space>
                <Table size="small" rowKey="id" dataSource={users} columns={userCols}
                  scroll={{ x: 1100 }} pagination={{ pageSize: 20 }} />
              </div>
            ) },

            // ========== 角色管理 ==========
            { key: 'roles', label: <span><TeamOutlined /> 角色管理</span>, children: (
              <div style={{ padding: 16 }}>
                <Alert
                  type="info" showIcon style={{ marginBottom: 12 }}
                  message="RBAC 权限模型"
                  description="角色可关联多个用户；用户可拥有多个角色。在【用户管理】Tab中可调整用户与角色的关联。"
                />
                <Space style={{ marginBottom: 12 }}>
                  <Input.Search
                    placeholder="搜索编码 / 名称"
                    value={roleKw}
                    onChange={(e) => setRoleKw(e.target.value)}
                    style={{ width: 240 }}
                    allowClear
                  />
                  <Button icon={<ReloadOutlined />} onClick={loadRoles}>刷新</Button>
                  <Button type="primary" icon={<PlusOutlined />} onClick={onCreateRole}>新增角色</Button>
                </Space>
                <Table size="small" rowKey="id" dataSource={roles} columns={roleCols}
                  pagination={{ pageSize: 20 }} />
              </div>
            ) },

            // ========== 字典管理 ==========
            { key: 'dicts', label: <span><BookOutlined /> 字典管理</span>, children: (
              <div style={{ padding: 16 }}>
                <Row gutter={16}>
                  <Col span={10}>
                    <Space style={{ marginBottom: 12 }}>
                      <Input.Search
                        placeholder="搜索编码 / 名称"
                        value={dictKw}
                        onChange={(e) => setDictKw(e.target.value)}
                        style={{ width: 200 }}
                        allowClear
                      />
                      <Button icon={<ReloadOutlined />} onClick={loadDicts}>刷新</Button>
                      <Button type="primary" icon={<PlusOutlined />} onClick={onCreateDict}>新增字典</Button>
                    </Space>
                    <Table size="small" rowKey="id" dataSource={dicts} columns={dictCols}
                      pagination={{ pageSize: 10 }}
                      onRow={(r) => ({ onClick: () => { setSelectedDict(r); loadDictItems(r.id) }, style: { cursor: 'pointer', background: r.id === selectedDict?.id ? '#e6f4ff' : undefined } })}
                    />
                  </Col>
                  <Col span={14}>
                    <Space style={{ marginBottom: 12 }}>
                      {selectedDict ? (
                        <>
                          <Tag color="purple">当前字典：{selectedDict.dict_code} · {selectedDict.dict_name}</Tag>
                          <Tag>{dictItems.length} 项</Tag>
                        </>
                      ) : (
                        <Tag>请选择左侧字典</Tag>
                      )}
                      <Button type="primary" icon={<PlusOutlined />} onClick={onCreateItem}
                        disabled={!selectedDict}>新增字典项</Button>
                    </Space>
                    {!selectedDict ? (
                      <Empty description="请在左侧选择一个字典" />
                    ) : (
                      <Table size="small" rowKey="id" dataSource={dictItems} columns={itemCols}
                        pagination={{ pageSize: 20 }} />
                    )}
                  </Col>
                </Row>
              </div>
            ) },
          ]}
        />
      </Card>

      {/* 用户编辑 */}
      <Modal title={editingUser ? '编辑用户' : '新增用户'} open={userModal}
        onCancel={() => setUserModal(false)} onOk={onSaveUser} width={560}>
        <Form form={userForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="username" label="用户名" rules={[{ required: true }, { min: 3 }]}>
                <Input disabled={!!editingUser} placeholder="登录名（不可修改）" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="display_name" label="显示名">
                <Input placeholder="如：李四 / 分析员甲" />
              </Form.Item>
            </Col>
          </Row>
          {!editingUser && (
            <Form.Item name="password" label="初始密码" rules={[{ required: true }, { min: 6 }]}>
              <Input.Password placeholder="至少6 位" />
            </Form.Item>
          )}
          {editingUser && (
            <Alert type="info" message="如需修改密码，请使用【重置密码】按钮" showIcon style={{ marginBottom: 12 }} />
          )}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="role" label="内置角色" rules={[{ required: true }]}>
                <Select options={[
                  { value: 'admin', label: 'admin（超级管理员）' },
                  { value: 'user', label: 'user（普通用户）' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="状态">
                <Select options={[
                  { value: 1, label: '启用' },
                  { value: 0, label: '禁用' },
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="role_ids" label="关联角色（多选）">
            <Select mode="multiple" allowClear placeholder="可关联多个自定义角色"
              options={roles.map((r) => ({ value: r.id, label: `${r.role_code} · ${r.role_name}` }))} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 重置密码 */}
      <Modal title="重置密码" open={pwdModal}
        onCancel={() => { setPwdModal(false); pwdForm.resetFields() }} onOk={onResetPwd}>
        <Form form={pwdForm} layout="vertical">
          <Form.Item name="new_password" label="新密码" rules={[{ required: true }, { min: 6 }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="至少 6 位" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 角色编辑 */}
      <Modal title={editingRole ? '编辑角色' : '新增角色'} open={roleModal}
        onCancel={() => setRoleModal(false)} onOk={onSaveRole} width={520}>
        <Form form={roleForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="role_code" label="角色编码" rules={[{ required: true }]}>
                <Input disabled={!!editingRole} placeholder="如 ADMIN/ANALYST" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="role_name" label="角色名称" rules={[{ required: true }]}>
                <Input placeholder="如：系统管理员" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="角色职责说明" />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue={1}>
            <Select options={[
              { value: 1, label: '启用' },
              { value: 0, label: '禁用' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 字典编辑 */}
      <Modal title={editingDict ? '编辑字典' : '新增字典'} open={dictModal}
        onCancel={() => setDictModal(false)} onOk={onSaveDict} width={520}>
        <Form form={dictForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="dict_code" label="字典编码" rules={[{ required: true }]}>
                <Input disabled={!!editingDict} placeholder="如 CURRENCY" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="dict_name" label="字典名称" rules={[{ required: true }]}>
                <Input placeholder="如：币种" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue={1}>
            <Select options={[
              { value: 1, label: '启用' },
              { value: 0, label: '禁用' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 字典项编辑 */}
      <Modal title={editingItem ? '编辑字典项' : '新增字典项'} open={itemModal}
        onCancel={() => setItemModal(false)} onOk={onSaveItem} width={520}>
        <Form form={itemForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="item_code" label="项编码" rules={[{ required: true }]}>
                <Input placeholder="如 CNY" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="item_name" label="项名称" rules={[{ required: true }]}>
                <Input placeholder="如：人民币" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="item_value" label="项值">
                <Input placeholder="可选：关联业务值" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sort_order" label="排序" initialValue={0}>
                <Input type="number" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="status" label="状态" initialValue={1}>
                <Select options={[{ value: 1, label: '启用' }, { value: 0, label: '禁用' }]} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </Spin>
  )
}

export default System
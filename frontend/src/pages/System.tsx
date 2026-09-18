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
import { dictApi } from '../api/dict'
import { DictTag } from '../components'

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

  // Dicts（基于 sys_dict 平铺表）
  const [dicts, setDicts] = useState<any[]>([])           // 字典类别列表（含 count）
  const [dictKw, setDictKw] = useState('')
  const [selectedDictType, setSelectedDictType] = useState<string | null>(null)
  const [dictItems, setDictItems] = useState<any[]>([])   // 当前选中类型的字典项
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

  // ========== 字典（基于 sys_dict 平铺表） ==========
  const loadDictTypes = async () => {
    setLoading(true)
    try {
      const r = await dictApi.listTypes()
      setDicts(r.items || [])
      // 默认选第一个类型
      if (!selectedDictType && r.items?.length) {
        setSelectedDictType(r.items[0].dict_type)
      }
    } finally { setLoading(false) }
  }
  const loadDictItems = async (type: string) => {
    try {
      const r = await dictApi.listByType(type, dictKw)
      setDictItems(r.items || [])
    } catch { setDictItems([]) }
  }
  useEffect(() => { if (tab === 'dicts') loadDictTypes() }, [tab])
  useEffect(() => { if (tab === 'dicts' && selectedDictType) loadDictItems(selectedDictType) }, [tab, selectedDictType, dictKw])

  const onCreateItem = () => {
    if (!selectedDictType) { message.warning('请先选择字典类型'); return }
    setEditingItem(null)
    itemForm.resetFields()
    itemForm.setFieldsValue({
      dict_type: selectedDictType,
      sort_order: 0,
      status: 'ACTIVE',
    })
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
      // 把空字符串字段转为 null
      const payload = {
        ...v,
        dict_type: v.dict_type || selectedDictType,
        color: v.color || null,
        description: v.description || null,
      }
      if (editingItem) await dictApi.update(editingItem.id, payload)
      else await dictApi.create(payload)
      message.success('已保存')
      setItemModal(false)
      loadDictItems(selectedDictType)
      loadDictTypes()  // 刷新类别计数
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onDeleteItem = async (iid: number) => {
    try {
      await dictApi.remove(iid)
      message.success('已删除')
      loadDictItems(selectedDictType)
      loadDictTypes()
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

  const dictTypeCols: ColumnsType<any> = [
    { title: '字典类别', dataIndex: 'dict_type', width: 220,
      render: (t: string) => <code style={{ background: '#f0f4ff', padding: '2px 8px', borderRadius: 3 }}>{t}</code> },
    { title: '项数', dataIndex: 'count', width: 80,
      render: (n: number) => <Tag color="blue">{n || 0}</Tag> },
  ]

  const dictItemCols: ColumnsType<any> = [
    { title: '字典值', dataIndex: 'dict_key', width: 160,
      render: (c: string) => <code style={{ background: '#f0f4ff', padding: '2px 8px', borderRadius: 3 }}>{c}</code> },
    { title: '显示标签', dataIndex: 'dict_label', width: 160 },
    { title: '颜色', dataIndex: 'color', width: 90,
      render: (c: string) => c ? <Tag color={c}>{c}</Tag> : '-' },
    { title: '排序', dataIndex: 'sort_order', width: 80 },
    { title: '状态', dataIndex: 'status', width: 100,
      render: (s: string) => <DictTag dictType="PRCP_STATUS" value={s} /> },
    {
      title: '操作', width: 140, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditItem(r)}>编辑</Button>
          <Popconfirm title="确认删除字典项？" description="软删除后可由字典管理恢复" onConfirm={() => onDeleteItem(r.id)}>
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
                <Alert type="info" showIcon style={{ marginBottom: 12 }}
                  message="PRCP 通用字典（sys_dict）"
                  description="所有字典共用一张表，按 dict_type 分类。前端下拉 / Tag 颜色都从此表动态加载。新增字典项后刷新业务页面即生效。" />
                <Row gutter={16}>
                  <Col span={8}>
                    <Space style={{ marginBottom: 12 }}>
                      <Button icon={<ReloadOutlined />} onClick={loadDictTypes}>刷新</Button>
                    </Space>
                    <Table size="small" rowKey="dict_type" dataSource={dicts} columns={dictTypeCols}
                      pagination={false}
                      onRow={(r) => ({ onClick: () => setSelectedDictType(r.dict_type), style: { cursor: 'pointer', background: r.dict_type === selectedDictType ? '#e6f4ff' : undefined } })}
                    />
                  </Col>
                  <Col span={16}>
                    <Space style={{ marginBottom: 12 }}>
                      {selectedDictType ? (
                        <>
                          <Tag color="purple">当前字典：{selectedDictType}</Tag>
                          <Tag>{dictItems.length} 项</Tag>
                        </>
                      ) : (
                        <Tag>请选择左侧字典类型</Tag>
                      )}
                      <Input.Search
                        placeholder="搜索 dict_key / dict_label"
                        value={dictKw}
                        onChange={(e) => setDictKw(e.target.value)}
                        style={{ width: 200 }}
                        allowClear
                      />
                      <Button type="primary" icon={<PlusOutlined />} onClick={onCreateItem}
                        disabled={!selectedDictType}>新增字典项</Button>
                    </Space>
                    {!selectedDictType ? (
                      <Empty description="请在左侧选择一个字典类型" />
                    ) : (
                      <Table size="small" rowKey="id" dataSource={dictItems} columns={dictItemCols}
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

      {/* 字典项编辑（sys_dict 平铺表） */}
      <Modal title={editingItem ? '编辑字典项' : '新增字典项'} open={itemModal}
        onCancel={() => setItemModal(false)} onOk={onSaveItem} width={560}>
        <Form form={itemForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="dict_type" label="字典类别" rules={[{ required: true }]}>
                <Input disabled={!!editingItem} placeholder="如 PRCP_ALGO" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="dict_key" label="字典值（代码）" rules={[{ required: true }]}>
                <Input disabled={!!editingItem} placeholder="如 LINEAR_REGRESSION" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="dict_label" label="显示标签（中文）" rules={[{ required: true }]}>
            <Input placeholder="如：线性回归" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="color" label="AntD 颜色">
                <Select allowClear placeholder="如 blue / red">
                  <Select.Option value="blue">blue</Select.Option>
                  <Select.Option value="purple">purple</Select.Option>
                  <Select.Option value="cyan">cyan</Select.Option>
                  <Select.Option value="green">green</Select.Option>
                  <Select.Option value="gold">gold</Select.Option>
                  <Select.Option value="orange">orange</Select.Option>
                  <Select.Option value="red">red</Select.Option>
                  <Select.Option value="magenta">magenta</Select.Option>
                  <Select.Option value="volcano">volcano</Select.Option>
                  <Select.Option value="geekblue">geekblue</Select.Option>
                  <Select.Option value="default">default</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sort_order" label="排序" initialValue={0}>
                <Input type="number" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="status" label="状态" initialValue="ACTIVE">
                <Select options={[
                  { value: 'ACTIVE', label: 'ACTIVE（启用）' },
                  { value: 'DEPRECATED', label: 'DEPRECATED（停用）' },
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="字典项说明（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </Spin>
  )
}

export default System
import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Tree, Form, Input, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, Tabs, InputNumber, Drawer, Popconfirm, Tooltip,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  ApartmentOutlined, FolderOutlined, FileTextOutlined,
} from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import type { ColumnsType } from 'antd/es/table'
import { coaApi } from '../api'

const NODE_TYPES = [
  { value: 'ASSET', label: '资产', color: 'blue' },
  { value: 'LIABILITY', label: '负债', color: 'orange' },
  { value: 'EQUITY', label: '权益', color: 'green' },
  { value: 'INCOME', label: '收入', color: 'cyan' },
  { value: 'EXPENSE', label: '支出', color: 'magenta' },
]

const COA: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [activeScheme, setActiveScheme] = useState<number | null>(null)
  const [tree, setTree] = useState<any[]>([])
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [schemeModalOpen, setSchemeModalOpen] = useState(false)
  const [editingScheme, setEditingScheme] = useState<any>(null)
  const [schemeForm] = Form.useForm()
  const [nodeForm] = Form.useForm()
  const [nodeModalOpen, setNodeModalOpen] = useState(false)
  const [editingNode, setEditingNode] = useState<any>(null)

  // 加载方案列表
  const loadSchemes = async () => {
    setLoading(true)
    try {
      const r = await coaApi.listSchemes()
      setSchemes(r.items || [])
      if (!activeScheme && r.items?.length) setActiveScheme(r.items[0].id)
    } catch (e: any) { message.error('方案加载失败') }
    finally { setLoading(false) }
  }
  useEffect(() => { loadSchemes() }, [])

  // 加载树
  useEffect(() => {
    if (!activeScheme) return
    setLoading(true)
    coaApi.treeNodes(activeScheme).then((r) => {
      setTree(r.items || [])
      setSelectedKey(null); setSelectedNode(null)
    }).catch(() => message.error('树加载失败'))
      .finally(() => setLoading(false))
  }, [activeScheme])

  // 选中节点
  const onSelect = (keys: React.Key[]) => {
    if (!keys.length) { setSelectedKey(null); setSelectedNode(null); return }
    const k = String(keys[0])
    setSelectedKey(k)
    // 找节点详情
    const find = (nodes: any[]): any => {
      for (const n of nodes) {
        if (n.key === k) return n
        if (n.children?.length) { const c = find(n.children); if (c) return c }
      }
      return null
    }
    setSelectedNode(find(tree))
  }

  // 新增方案
  const onCreateScheme = () => {
    setEditingScheme(null)
    schemeForm.resetFields()
    setSchemeModalOpen(true)
  }
  const onEditScheme = (s: any) => {
    setEditingScheme(s)
    schemeForm.setFieldsValue(s)
    setSchemeModalOpen(true)
  }
  const onSaveScheme = async () => {
    const v = await schemeForm.validateFields()
    try {
      if (editingScheme) {
        await coaApi.updateScheme(editingScheme.id, v)
        message.success('方案已更新')
      } else {
        const r = await coaApi.createScheme(v)
        message.success(`方案已创建 id=${r.id}`)
        setActiveScheme(r.id)
      }
      setSchemeModalOpen(false)
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  // 新增节点
  const onCreateNode = (parent?: any) => {
    setEditingNode(null)
    nodeForm.resetFields()
    nodeForm.setFieldsValue({
      scheme_id: activeScheme,
      parent_id: parent?.id || null,
      node_level: parent ? (parent.level || 1) + 1 : 1,
      sort_order: 0,
      status: 'ACTIVE',
    })
    setNodeModalOpen(true)
  }
  const onEditNode = (n: any) => {
    setEditingNode(n)
    nodeForm.setFieldsValue({
      scheme_id: activeScheme,
      node_code: n.code,
      node_name: n.name,
      parent_id: n.parent_id || null,
      node_level: n.level,
      node_type: n.type,
      sort_order: n.sort_order,
      status: n.status,
      description: '',
    })
    setNodeModalOpen(true)
  }
  const onSaveNode = async () => {
    const v = await nodeForm.validateFields()
    try {
      if (editingNode) {
        await coaApi.updateNode(editingNode.id, v)
        message.success('节点已更新')
      } else {
        await coaApi.createNode(v)
        message.success('节点已创建')
      }
      setNodeModalOpen(false)
      coaApi.treeNodes(activeScheme!).then((r) => setTree(r.items || []))
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  // 树
  const treeData: DataNode[] = useMemo(() => {
    const toNode = (n: any): DataNode => {
      const typeMeta = NODE_TYPES.find((t) => t.value === n.type)
      return {
        key: n.key,
        title: (
          <span>
            <Tag color={typeMeta?.color || 'default'} style={{ marginRight: 4 }}>{n.level}</Tag>
            <span style={{ fontWeight: n.level === 1 ? 600 : 400 }}>{n.title}</span>
          </span>
        ),
        children: n.children?.length ? n.children.map(toNode) : undefined,
      }
    }
    return tree.map(toNode)
  }, [tree])

  // 方案表
  const schemeCols: ColumnsType<any> = [
    { title: '方案编码', dataIndex: 'scheme_code', width: 140, render: (c) => <code>{c}</code> },
    { title: '方案名称', dataIndex: 'scheme_name', ellipsis: true },
    { title: '节点数', dataIndex: 'node_count', width: 90, render: (n) => <Tag color="blue">{n || 0}</Tag> },
    { title: '状态', dataIndex: 'status', width: 90, render: (s) => <Tag color={s === 'ACTIVE' ? 'green' : 'default'}>{s}</Tag> },
    {
      title: '操作', width: 140, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditScheme(r)}>编辑</Button>
          <Popconfirm
            title="确认删除此方案及其所有节点？"
            onConfirm={async () => {
              await coaApi.deleteScheme(r.id)
              message.success('已删除')
              if (activeScheme === r.id) setActiveScheme(null)
              loadSchemes()
            }}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>账户册维护 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>· COA · 树形结构</span></span>
      </div>

      <Card
        bordered={false}
        bodyStyle={{ padding: 0 }}
        title={
          <Tabs
            activeKey={activeScheme ? String(activeScheme) : ''}
            onChange={(k) => setActiveScheme(Number(k))}
            items={schemes.map((s) => ({
              key: String(s.id),
              label: <span>{s.scheme_name} <Tag color="blue">{s.node_count}</Tag></span>,
            }))}
            tabBarExtraContent={
              <Space>
                <Button size="small" icon={<PlusOutlined />} type="primary" onClick={onCreateScheme}>新增方案</Button>
                <Button size="small" icon={<ReloadOutlined />} onClick={loadSchemes} />
              </Space>
            }
          />
        }
      >
        <Row style={{ minHeight: 520 }}>
          {/* 左：方案列表 */}
          <Col span={9} style={{ borderRight: '1px solid #f0f0f0', padding: 12 }}>
            <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>
              <FolderOutlined style={{ marginRight: 6 }} /> 方案列表（{schemes.length}）
            </div>
            <Table
              size="small" rowKey="id" dataSource={schemes} columns={schemeCols}
              pagination={false} scroll={{ y: 460 }}
              onRow={(r) => ({ onClick: () => setActiveScheme(r.id), style: { cursor: 'pointer', background: r.id === activeScheme ? '#e6f4ff' : undefined } })}
            />
          </Col>

          {/* 中：树形 */}
          <Col span={6} style={{ borderRight: '1px solid #f0f0f0', padding: 12, background: '#fafafa' }}>
            <div style={{ marginBottom: 8, color: '#666', fontSize: 13, display: 'flex', justifyContent: 'space-between' }}>
              <span><ApartmentOutlined style={{ marginRight: 6 }} />节点树</span>
              <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => onCreateNode()}>新增根节点</Button>
            </div>
            {treeData.length ? (
              <Tree treeData={treeData} defaultExpandAll showLine blockNode
                selectedKeys={selectedKey ? [selectedKey] : []}
                onSelect={onSelect}
              />
            ) : <Empty description="请先选择方案" />}
          </Col>

          {/* 右：节点详情 */}
          <Col span={9} style={{ padding: 16 }}>
            {selectedNode ? (
              <div>
                <div style={{ marginBottom: 12, color: '#666' }}>
                  <FileTextOutlined style={{ marginRight: 6 }} />节点详情
                </div>
                <Form layout="vertical">
                  <Form.Item label="节点编码"><Input value={selectedNode.code} disabled /></Form.Item>
                  <Form.Item label="节点名称"><Input value={selectedNode.name} disabled /></Form.Item>
                  <Row gutter={16}>
                    <Col span={12}><Form.Item label="节点层级"><Input value={selectedNode.level} disabled /></Form.Item></Col>
                    <Col span={12}><Form.Item label="节点类型">
                      <Tag color={NODE_TYPES.find((t) => t.value === selectedNode.type)?.color}>
                        {NODE_TYPES.find((t) => t.value === selectedNode.type)?.label || selectedNode.type || '未设置'}
                      </Tag>
                    </Form.Item></Col>
                  </Row>
                  <Form.Item label="物化路径">
                    <Input.TextArea value={selectedNode.path} disabled rows={2} />
                  </Form.Item>
                  <Space>
                    <Button type="primary" icon={<EditOutlined />} onClick={() => onEditNode(selectedNode)}>编辑</Button>
                    <Button icon={<PlusOutlined />} onClick={() => onCreateNode(selectedNode)}>新增子节点</Button>
                    <Popconfirm
                      title="删除该节点及其所有子孙？"
                      onConfirm={async () => {
                        await coaApi.deleteNode(selectedNode.id)
                        message.success('已删除')
                        coaApi.treeNodes(activeScheme!).then((r) => setTree(r.items || []))
                        loadSchemes()
                        setSelectedKey(null); setSelectedNode(null)
                      }}
                    >
                      <Button danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>
                  </Space>
                </Form>
              </div>
            ) : <Empty description="请选择树中节点" />}
          </Col>
        </Row>
      </Card>

      {/* 方案编辑 */}
      <Modal title={editingScheme ? '编辑方案' : '新增方案'} open={schemeModalOpen}
        onCancel={() => setSchemeModalOpen(false)} onOk={onSaveScheme} width={520}>
        <Form form={schemeForm} layout="vertical">
          <Form.Item name="scheme_code" label="方案编码" rules={[{ required: true, message: '必填' }]}>
            <Input placeholder="如 BS_2026" />
          </Form.Item>
          <Form.Item name="scheme_name" label="方案名称" rules={[{ required: true }]}>
            <Input placeholder="如 资负表方案" />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="ACTIVE">
            <Select options={[{ value: 'ACTIVE', label: 'ACTIVE' }, { value: 'INACTIVE', label: 'INACTIVE' }]} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 节点编辑 */}
      <Modal title={editingNode ? '编辑节点' : '新增节点'} open={nodeModalOpen}
        onCancel={() => setNodeModalOpen(false)} onOk={onSaveNode} width={520}>
        <Form form={nodeForm} layout="vertical">
          <Form.Item name="scheme_id" hidden><Input /></Form.Item>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="node_code" label="节点编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="node_name" label="节点名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="parent_id" label="父节点 ID"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="node_level" label="层级"><InputNumber style={{ width: '100%' }} disabled /></Form.Item></Col>
            <Col span={8}><Form.Item name="sort_order" label="排序"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item name="node_type" label="节点类型">
            <Select options={NODE_TYPES.map((t) => ({ value: t.value, label: t.label }))} allowClear />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="ACTIVE">
            <Select options={[{ value: 'ACTIVE', label: 'ACTIVE' }, { value: 'INACTIVE', label: 'INACTIVE' }]} />
          </Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </Spin>
  )
}

export default COA

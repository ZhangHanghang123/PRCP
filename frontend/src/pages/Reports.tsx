import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Tree, Form, Input, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, Tabs, InputNumber, Popconfirm,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  ApartmentOutlined, FolderOutlined, FileTextOutlined,
} from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import type { ColumnsType } from 'antd/es/table'
import { reportsApi, coaApi } from '../api'

const REPORT_TYPES = [
  { value: 'BALANCE', label: '资产负债表', color: 'blue' },
  { value: 'INCOME', label: '损益表', color: 'green' },
  { value: 'CASHFLOW', label: '现金流量表', color: 'cyan' },
  { value: 'INDICATOR', label: '关键指标表', color: 'purple' },
  { value: 'RISK', label: 'RWA 报表', color: 'red' },
  { value: 'LIQUIDITY', label: '流动性报表', color: 'orange' },
]

const Reports: React.FC = () => {
  const [reports, setReports] = useState<any[]>([])
  const [schemes, setSchemes] = useState<any[]>([])
  const [activeReport, setActiveReport] = useState<number | null>(null)
  const [tree, setTree] = useState<any[]>([])
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [selectedItem, setSelectedItem] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [rptModalOpen, setRptModalOpen] = useState(false)
  const [editingRpt, setEditingRpt] = useState<any>(null)
  const [itemModalOpen, setItemModalOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<any>(null)
  const [rptForm] = Form.useForm()
  const [itemForm] = Form.useForm()

  const loadReports = async () => {
    setLoading(true)
    try {
      const [r, s] = await Promise.all([reportsApi.list({}), coaApi.listSchemes()])
      setReports(r.items || [])
      setSchemes(s.items || [])
      if (!activeReport && r.items?.length) setActiveReport(r.items[0].id)
    } catch { message.error('报表加载失败') }
    finally { setLoading(false) }
  }
  useEffect(() => { loadReports() }, [])

  useEffect(() => {
    if (!activeReport) return
    setLoading(true)
    reportsApi.treeItems(activeReport).then((r) => {
      setTree(r.items || [])
      setSelectedKey(null); setSelectedItem(null)
    }).catch(() => message.error('表项加载失败'))
      .finally(() => setLoading(false))
  }, [activeReport])

  const onSelect = (keys: React.Key[]) => {
    if (!keys.length) { setSelectedKey(null); setSelectedItem(null); return }
    const k = String(keys[0])
    setSelectedKey(k)
    const find = (nodes: any[]): any => {
      for (const n of nodes) {
        if (n.key === k) return n
        if (n.children?.length) { const c = find(n.children); if (c) return c }
      }
      return null
    }
    setSelectedItem(find(tree))
  }

  // 报表 CRUD
  const onCreateRpt = () => {
    setEditingRpt(null)
    rptForm.resetFields()
    rptForm.setFieldsValue({ status: 'ACTIVE' })
    setRptModalOpen(true)
  }
  const onEditRpt = (r: any) => {
    setEditingRpt(r)
    rptForm.setFieldsValue(r)
    setRptModalOpen(true)
  }
  const onSaveRpt = async () => {
    const v = await rptForm.validateFields()
    try {
      if (editingRpt) {
        await reportsApi.update(editingRpt.id, v)
        message.success('已更新')
      } else {
        const r = await reportsApi.create(v)
        message.success('已创建')
        setActiveReport(r.id)
      }
      setRptModalOpen(false)
      loadReports()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  // 表项 CRUD
  const onCreateItem = (parent?: any) => {
    setEditingItem(null)
    itemForm.resetFields()
    itemForm.setFieldsValue({
      report_id: activeReport,
      parent_id: parent?.id || null,
      data_type: 'DECIMAL',
      sort_order: 0,
      status: 'ACTIVE',
      coa_node_ids: [],
    })
    setItemModalOpen(true)
  }
  const onEditItem = (n: any) => {
    setEditingItem(n)
    itemForm.setFieldsValue({
      report_id: activeReport,
      item_code: n.code,
      item_name: n.name,
      parent_id: n.parent_id || null,
      data_type: n.data_type || 'DECIMAL',
      formula: n.formula,
      coa_node_ids: n.coa_node_ids || [],
      sort_order: n.sort_order,
      status: n.status,
    })
    setItemModalOpen(true)
  }
  const onSaveItem = async () => {
    const v = await itemForm.validateFields()
    try {
      if (editingItem) {
        await reportsApi.updateItem(editingItem.id, v)
        message.success('已更新')
      } else {
        await reportsApi.createItem(v)
        message.success('已创建')
      }
      setItemModalOpen(false)
      reportsApi.treeItems(activeReport!).then((r) => setTree(r.items || []))
      loadReports()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  const treeData: DataNode[] = useMemo(() => {
    const toNode = (n: any): DataNode => ({
      key: n.key,
      title: <span><Tag color="blue" style={{ marginRight: 4 }}>{n.level}</Tag>{n.title}</span>,
      children: n.children?.length ? n.children.map(toNode) : undefined,
    })
    return tree.map(toNode)
  }, [tree])

  const rptCols: ColumnsType<any> = [
    { title: '编码', dataIndex: 'report_code', width: 120, render: (c) => <code>{c}</code> },
    { title: '名称', dataIndex: 'report_name', ellipsis: true },
    { title: '类型', dataIndex: 'report_type', width: 110,
      render: (t) => <Tag color={REPORT_TYPES.find((x) => x.value === t)?.color}>{REPORT_TYPES.find((x) => x.value === t)?.label || t}</Tag> },
    { title: '关联账户册', dataIndex: 'scheme_name', width: 140 },
    { title: '表项数', dataIndex: 'item_count', width: 90, render: (n) => <Tag>{n || 0}</Tag> },
    { title: '状态', dataIndex: 'status', width: 80, render: (s) => <Tag color={s === 'ACTIVE' ? 'green' : 'default'}>{s}</Tag> },
    {
      title: '操作', width: 140, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditRpt(r)}>编辑</Button>
          <Popconfirm title="确认删除报表及其所有表项？" onConfirm={async () => {
            await reportsApi.delete(r.id)
            message.success('已删除')
            if (activeReport === r.id) setActiveReport(null)
            loadReports()
          }}><Button size="small" danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>报表表项管理 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>· 6 类报表 + 树形表项</span></span>
      </div>

      <Card
        bordered={false}
        bodyStyle={{ padding: 0 }}
        title={
          <Tabs
            activeKey={activeReport ? String(activeReport) : ''}
            onChange={(k) => setActiveReport(Number(k))}
            items={reports.map((r) => ({
              key: String(r.id),
              label: <span>{r.report_name} <Tag color="blue">{r.item_count}</Tag></span>,
            }))}
            tabBarExtraContent={
              <Space>
                <Button size="small" type="primary" icon={<PlusOutlined />} onClick={onCreateRpt}>新增报表</Button>
                <Button size="small" icon={<ReloadOutlined />} onClick={loadReports} />
              </Space>
            }
          />
        }
      >
        <Row style={{ minHeight: 520 }}>
          <Col span={9} style={{ borderRight: '1px solid #f0f0f0', padding: 12 }}>
            <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>
              <FolderOutlined style={{ marginRight: 6 }} /> 报表列表（{reports.length}）
            </div>
            <Table size="small" rowKey="id" dataSource={reports} columns={rptCols}
              pagination={false} scroll={{ y: 460 }}
              onRow={(r) => ({ onClick: () => setActiveReport(r.id), style: { cursor: 'pointer', background: r.id === activeReport ? '#e6f4ff' : undefined } })}
            />
          </Col>

          <Col span={6} style={{ borderRight: '1px solid #f0f0f0', padding: 12, background: '#fafafa' }}>
            <div style={{ marginBottom: 8, color: '#666', fontSize: 13, display: 'flex', justifyContent: 'space-between' }}>
              <span><ApartmentOutlined style={{ marginRight: 6 }} />表项树</span>
              <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => onCreateItem()}>新增根表项</Button>
            </div>
            {treeData.length ? (
              <Tree treeData={treeData} defaultExpandAll showLine blockNode
                selectedKeys={selectedKey ? [selectedKey] : []} onSelect={onSelect} />
            ) : <Empty description="请先选择报表" />}
          </Col>

          <Col span={9} style={{ padding: 16 }}>
            {selectedItem ? (
              <div>
                <div style={{ marginBottom: 12, color: '#666' }}><FileTextOutlined style={{ marginRight: 6 }} />表项详情</div>
                <Form layout="vertical">
                  <Form.Item label="表项编码"><Input value={selectedItem.code} disabled /></Form.Item>
                  <Form.Item label="表项名称"><Input value={selectedItem.name} disabled /></Form.Item>
                  <Row gutter={16}>
                    <Col span={12}><Form.Item label="层级"><Input value={selectedItem.level} disabled /></Form.Item></Col>
                    <Col span={12}><Form.Item label="数据类型"><Tag>{selectedItem.data_type}</Tag></Form.Item></Col>
                  </Row>
                  <Form.Item label="计算公式"><Input.TextArea value={selectedItem.formula || '（无）'} disabled rows={2} /></Form.Item>
                  <Form.Item label="关联账户册节点 ID">
                    <Input value={(selectedItem.coa_node_ids || []).join(', ') || '（无）'} disabled />
                  </Form.Item>
                  <Form.Item label="物化路径"><Input.TextArea value={selectedItem.path} disabled rows={2} /></Form.Item>
                  <Space>
                    <Button type="primary" icon={<EditOutlined />} onClick={() => onEditItem(selectedItem)}>编辑</Button>
                    <Button icon={<PlusOutlined />} onClick={() => onCreateItem(selectedItem)}>新增子表项</Button>
                    <Popconfirm title="删除该表项及其所有子孙？" onConfirm={async () => {
                      await reportsApi.deleteItem(selectedItem.id)
                      message.success('已删除')
                      reportsApi.treeItems(activeReport!).then((r) => setTree(r.items || []))
                      loadReports()
                      setSelectedKey(null); setSelectedItem(null)
                    }}><Button danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>
                  </Space>
                </Form>
              </div>
            ) : <Empty description="请选择树中表项" />}
          </Col>
        </Row>
      </Card>

      <Modal title={editingRpt ? '编辑报表' : '新增报表'} open={rptModalOpen}
        onCancel={() => setRptModalOpen(false)} onOk={onSaveRpt} width={520}>
        <Form form={rptForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="report_code" label="报表编码" rules={[{ required: true }]}><Input placeholder="RPT_BS" /></Form.Item></Col>
            <Col span={12}><Form.Item name="report_name" label="报表名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="report_type" label="报表类型" rules={[{ required: true }]}>
            <Select options={REPORT_TYPES.map((t) => ({ value: t.value, label: t.label }))} />
          </Form.Item>
          <Form.Item name="scheme_id" label="关联账户册方案" rules={[{ required: true }]}>
            <Select options={schemes.map((s) => ({ value: s.id, label: `${s.scheme_code} - ${s.scheme_name}` }))} />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="ACTIVE">
            <Select options={[{ value: 'ACTIVE', label: 'ACTIVE' }, { value: 'INACTIVE', label: 'INACTIVE' }]} />
          </Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal title={editingItem ? '编辑表项' : '新增表项'} open={itemModalOpen}
        onCancel={() => setItemModalOpen(false)} onOk={onSaveItem} width={560}>
        <Form form={itemForm} layout="vertical">
          <Form.Item name="report_id" hidden><Input /></Form.Item>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="item_code" label="表项编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="item_name" label="表项名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="parent_id" label="父表项 ID"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="data_type" label="数据类型"><Select options={[{ value: 'DECIMAL', label: 'DECIMAL' }, { value: 'INT', label: 'INT' }, { value: 'TEXT', label: 'TEXT' }]} /></Form.Item></Col>
            <Col span={8}><Form.Item name="sort_order" label="排序"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item name="formula" label="计算公式">
            <Input.TextArea rows={2} placeholder="如：rpt:001001 / rpt:001002" />
          </Form.Item>
          <Form.Item name="coa_node_ids" label="关联账户册节点 ID（多选，逗号分隔）">
            <Select mode="tags" placeholder="输入节点 ID 后回车" tokenSeparators={[',']} />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="ACTIVE">
            <Select options={[{ value: 'ACTIVE', label: 'ACTIVE' }, { value: 'INACTIVE', label: 'INACTIVE' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </Spin>
  )
}

export default Reports

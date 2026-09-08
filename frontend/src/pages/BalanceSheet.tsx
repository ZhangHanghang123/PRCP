import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, DatePicker, Popconfirm, Row, Col, Statistic,
} from 'antd'
import { DeleteOutlined, ReloadOutlined, PlusOutlined, LineChartOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { balanceApi, coaApi } from '../api'

const BalanceSheet: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [activeScheme, setActiveScheme] = useState<number | null>(null)
  const [nodes, setNodes] = useState<any[]>([])
  const [records, setRecords] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [dataDate, setDataDate] = useState<Dayjs>(dayjs('2026-08-31'))
  const [form] = Form.useForm()

  // 加载方案
  const loadSchemes = async () => {
    const r = await coaApi.listSchemes()
    setSchemes(r.items || [])
    if (!activeScheme && r.items?.length) setActiveScheme(r.items[0].id)
  }
  useEffect(() => { loadSchemes() }, [])

  // 加载节点（只顶层 + 叶子）
  useEffect(() => {
    if (!activeScheme) return
    coaApi.listNodes(activeScheme).then((r) => setNodes(r.items || []))
  }, [activeScheme])

  // 加载数据
  const loadRecords = async () => {
    if (!dataDate) return
    setLoading(true)
    try {
      const r = await balanceApi.list({ data_date: dataDate.format('YYYY-MM-DD') })
      setRecords(r.items || [])
    } finally { setLoading(false) }
  }
  useEffect(() => { loadRecords() }, [dataDate])

  // 新增
  const onCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      data_date: dataDate,
      current_amount: 0,
      gaps: Array(24).fill(0),
    })
    setModalOpen(true)
  }
  const onEdit = (r: any) => {
    setEditing(r)
    form.setFieldsValue({
      coa_node_id: r.coa_node_id,
      data_date: dayjs(r.data_date),
      current_amount: r.current_amount,
      gaps: r.gaps,
      calc_note: r.calc_note,
    })
    setModalOpen(true)
  }
  const onSave = async () => {
    const v = await form.validateFields()
    try {
      await balanceApi.upsert({
        coa_node_id: v.coa_node_id,
        data_date: v.data_date.format('YYYY-MM-DD'),
        current_amount: v.current_amount,
        gaps: v.gaps,
        calc_note: v.calc_note,
      })
      message.success(editing ? '已更新' : '已创建')
      setModalOpen(false)
      loadRecords()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  const cols: ColumnsType<any> = [
    { title: '节点编码', dataIndex: 'node_code', width: 120, render: (c) => <code>{c}</code> },
    { title: '节点名称', dataIndex: 'node_name', ellipsis: true },
    { title: '当前金额', dataIndex: 'current_amount', width: 140,
      render: (v) => v?.toLocaleString() },
    { title: 'M1 缺口', dataIndex: 'gaps', width: 110, render: (g) => <span style={{ color: g?.[0] > 0 ? '#cf1322' : '#3f8600' }}>{g?.[0]?.toLocaleString() || 0}</span> },
    { title: 'M3 缺口', dataIndex: 'gaps', width: 110, render: (g) => <span>{g?.[2]?.toLocaleString() || 0}</span> },
    { title: 'M6 缺口', dataIndex: 'gaps', width: 110, render: (g) => <span>{g?.[5]?.toLocaleString() || 0}</span> },
    { title: 'M12 缺口', dataIndex: 'gaps', width: 110, render: (g) => <span>{g?.[11]?.toLocaleString() || 0}</span> },
    { title: 'M24 缺口', dataIndex: 'gaps', width: 110, render: (g) => <span>{g?.[23]?.toLocaleString() || 0}</span> },
    { title: '24月合计', dataIndex: 'gaps', width: 120,
      render: (g) => {
        const s = (g || []).reduce((a: number, b: number) => a + (b || 0), 0)
        return <Tag color={s > 0 ? 'red' : s < 0 ? 'green' : 'default'}>{s.toLocaleString()}</Tag>
      },
    },
    {
      title: '操作', width: 110, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" onClick={() => onEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={async () => {
            await balanceApi.delete(r.id)
            message.success('已删除')
            loadRecords()
          }}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
        </Space>
      ),
    },
  ]

  // 汇总
  const summary = useMemo(() => {
    const total = records.length
    const totalAmt = records.reduce((s, r) => s + (r.current_amount || 0), 0)
    const totalGap24 = records.reduce((s, r) => s + (r.gaps || []).reduce((a: number, b: number) => a + (b || 0), 0), 0)
    return { total, totalAmt, totalGap24 }
  }, [records])

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>资产负债表 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>· 24 月现金流缺口</span></span>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card><Statistic title="记录数" value={summary.total} /></Card></Col>
        <Col span={6}><Card><Statistic title="当前金额合计" value={summary.totalAmt} precision={0} /></Card></Col>
        <Col span={6}><Card><Statistic title="24 月缺口合计" value={summary.totalGap24} precision={0} valueStyle={{ color: summary.totalGap24 > 0 ? '#cf1322' : '#3f8600' }} /></Card></Col>
        <Col span={6}><Card><Statistic title="数据日期" value={dataDate?.format('YYYY-MM-DD') || '—'} /></Card></Col>
      </Row>

      <Card
        bordered={false}
        title={
          <Space>
            <Select
              placeholder="选择账户册方案" style={{ width: 200 }}
              value={activeScheme || undefined}
              onChange={setActiveScheme}
              options={schemes.map((s) => ({ value: s.id, label: s.scheme_name }))}
            />
            <DatePicker value={dataDate} onChange={setDataDate} placeholder="数据日期" />
          </Space>
        }
        extra={
          <Space>
            <Button icon={<PlusOutlined />} type="primary" onClick={onCreate}>新增记录</Button>
            <Button icon={<ReloadOutlined />} onClick={loadRecords}>刷新</Button>
          </Space>
        }
      >
        <Table
          size="small" rowKey="id" dataSource={records} columns={cols}
          scroll={{ x: 1300 }}
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
        />
      </Card>

      <Modal title={editing ? '编辑记录' : '新增记录'} open={modalOpen}
        onCancel={() => setModalOpen(false)} onOk={onSave} width={720}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="coa_node_id" label="账户册节点" rules={[{ required: true }]}>
              <Select
                showSearch optionFilterProp="label"
                options={nodes.map((n) => ({ value: n.id, label: `${n.node_code} - ${n.node_name}` }))}
              />
            </Form.Item></Col>
            <Col span={12}><Form.Item name="data_date" label="数据日期" rules={[{ required: true }]}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item></Col>
          </Row>
          <Form.Item name="current_amount" label="当前余额">
            <InputNumber style={{ width: '100%' }} step={1000} />
          </Form.Item>
          <Form.Item label="未来 24 月缺口（每月一个数）">
            <Row gutter={6}>
              {Array.from({ length: 24 }, (_, i) => (
                <Col span={3} key={i} style={{ marginBottom: 6 }}>
                  <Form.Item name={['gaps', i]} noStyle>
                    <InputNumber placeholder={`M${i + 1}`} size="small" style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              ))}
            </Row>
          </Form.Item>
          <Form.Item name="calc_note" label="计算备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </Spin>
  )
}

export default BalanceSheet

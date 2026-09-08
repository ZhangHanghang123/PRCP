import React, { useEffect, useState } from 'react'
import { Table, Tag, Card, Button, Modal, Form, Input, Select, InputNumber, DatePicker, Space, message, Popconfirm, Row, Col, Statistic } from 'antd'
import { PlusOutlined, ReloadOutlined, AlertOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import { positionsApi } from '../api'

const Positions: React.FC = () => {
  const [data, setData] = useState<any>({ items: [], total: 0 })
  const [gap, setGap] = useState<any>({ by_currency_direction: [], net_gap: [] })
  const [filters, setFilters] = useState<any>({})
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  const load = async (over: any = {}) => {
    const f = { ...filters, ...over }
    setFilters(f)
    setLoading(true)
    try {
      const r = await positionsApi.list({ page_size: 50, ...f })
      setData(r)
      const g = await positionsApi.gap(f.group_id ? { group_id: f.group_id } : {})
      setGap(g)
    } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const onCreate = () => { setEditing(null); form.resetFields(); setOpen(true) }
  const onEdit = (r: any) => {
    setEditing(r); form.setFieldsValue({ ...r, trade_date: r.trade_date ? dayjs(r.trade_date) : null, settle_date: r.settle_date ? dayjs(r.settle_date) : null }); setOpen(true)
  }
  const onSubmit = async () => {
    const v = await form.validateFields()
    const payload = {
      ...v,
      trade_date: v.trade_date ? v.trade_date.format('YYYY-MM-DD') : null,
      settle_date: v.settle_date ? v.settle_date.format('YYYY-MM-DD') : null,
    }
    try {
      if (editing) await positionsApi.update(editing.id, payload)
      else await positionsApi.create(payload)
      message.success(editing ? '更新成功' : '创建成功')
      setOpen(false); load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '失败')
    }
  }

  const gapChartOpt = {
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: (gap.net_gap || []).map((g: any) => g.currency) },
    yAxis: { type: 'value', name: '净额' },
    series: [{
      data: (gap.net_gap || []).map((g: any) => g.net_amount),
      type: 'bar',
      itemStyle: {
        color: (p: any) => p.value >= 0 ? '#667eea' : '#764ba2',
        borderRadius: [6, 6, 0, 0],
      },
      label: { show: true, position: 'top', formatter: (p: any) => p.value.toLocaleString() },
    }],
  }

  const cols = [
    { title: '头寸编号', dataIndex: 'position_code', width: 130 },
    { title: '资金组', dataIndex: 'group_name', width: 150, ellipsis: true,
      render: (v: string, r: any) => v ? <Tag>#{r.group_id} {v}</Tag> : <Tag color="warning">未指定</Tag> },
    { title: '账户', dataIndex: 'account_code', width: 110 },
    { title: '币种', dataIndex: 'currency', width: 80 },
    { title: '方向', dataIndex: 'direction', width: 80,
      render: (v: string) => <Tag color={v === 'IN' ? 'green' : 'red'}>{v === 'IN' ? '调入' : '调出'}</Tag> },
    { title: '金额', dataIndex: 'amount', width: 150, render: (v: number) => v?.toLocaleString() },
    { title: '利率', dataIndex: 'rate', width: 90, render: (v: number) => (v * 100).toFixed(4) + '%' },
    { title: '交易日', dataIndex: 'trade_date', width: 110 },
    { title: '结算日', dataIndex: 'settle_date', width: 110 },
    { title: '对手方', dataIndex: 'counterparty', width: 130, ellipsis: true },
    { title: '状态', dataIndex: 'status', width: 90,
      render: (v: string) => <Tag color={v === 'SETTLED' ? 'green' : v === 'PENDING' ? 'gold' : 'default'}>{v}</Tag> },
    { title: '操作', width: 140, fixed: 'right' as const,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => onEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除？" okText="删除" cancelText="取消" okButtonProps={{ danger: true }}
            onConfirm={async () => { await positionsApi.delete(r.id); message.success('已删除'); load() }}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="page-title">
        <span className="page-title-icon" />
        头寸管理
        <Space style={{ marginLeft: 'auto' }}>
          <Button icon={<ReloadOutlined />} onClick={() => load()}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>新增头寸</Button>
        </Space>
      </div>

      {/* 缺口分析面板 */}
      <Card title={<><AlertOutlined /> 待调度缺口分析</>} size="small" style={{ marginBottom: 16 }}>
        {gap.net_gap?.length ? (
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <ReactECharts option={gapChartOpt} style={{ height: 240 }} />
            </Col>
            <Col xs={24} md={12}>
              <Row gutter={[12, 12]}>
                {gap.net_gap.map((g: any) => (
                  <Col span={12} key={g.currency}>
                    <Statistic
                      title={g.currency + ' 净缺口'}
                      value={g.net_amount}
                      valueStyle={{ color: g.net_amount >= 0 ? '#667eea' : '#764ba2', fontSize: 18 }}
                      suffix="元"
                    />
                  </Col>
                ))}
              </Row>
            </Col>
          </Row>
        ) : (
          <div style={{ color: '#999', padding: 20, textAlign: 'center' }}>暂无待调度头寸</div>
        )}
      </Card>

      {/* 过滤条件 */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Select allowClear placeholder="币种" style={{ width: 110 }}
            value={filters.currency}
            onChange={(v) => load({ currency: v })}
            options={['CNY', 'USD', 'EUR', 'JPY', 'HKD'].map(c => ({ label: c, value: c }))} />
          <Select allowClear placeholder="状态" style={{ width: 130 }}
            value={filters.status}
            onChange={(v) => load({ status: v })}
            options={[{ label: '待处理', value: 'PENDING' }, { label: '已结算', value: 'SETTLED' }, { label: '已取消', value: 'CANCELLED' }]} />
        </Space>
      </Card>

      <Card><Table rowKey="id" dataSource={data.items} columns={cols} loading={loading} pagination={{ pageSize: 20 }} scroll={{ x: 1500 }} /></Card>

      <Modal title={editing ? '编辑头寸' : '新增头寸'} open={open} onCancel={() => setOpen(false)} onOk={onSubmit} width={640}>
        <Form form={form} layout="vertical">
          <Form.Item label="头寸编号" name="position_code" rules={[{ required: true }]}><Input disabled={!!editing} /></Form.Item>
          <Row gutter={12}>
            <Col span={12}><Form.Item label="资金组 ID" name="group_id"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={12}><Form.Item label="账户代码" name="account_code"><Input /></Form.Item></Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}><Form.Item label="币种" name="currency" initialValue="CNY"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item label="方向" name="direction" initialValue="IN">
              <Select options={[{ label: '调入', value: 'IN' }, { label: '调出', value: 'OUT' }]} />
            </Form.Item></Col>
            <Col span={8}><Form.Item label="金额" name="amount"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}><Form.Item label="利率" name="rate"><InputNumber step={0.0001} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item label="交易日" name="trade_date"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item label="结算日" name="settle_date"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item label="对手方" name="counterparty"><Input /></Form.Item>
          <Form.Item label="状态" name="status" initialValue="PENDING">
            <Select options={[{ label: '待处理', value: 'PENDING' }, { label: '已结算', value: 'SETTLED' }, { label: '已取消', value: 'CANCELLED' }]} />
          </Form.Item>
          <Form.Item label="说明" name="description"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Positions
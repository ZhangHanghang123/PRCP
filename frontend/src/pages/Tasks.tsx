import React, { useEffect, useState } from 'react'
import { Table, Tag, Card, Button, Modal, Form, Input, DatePicker, Space, message, Popconfirm, Row, Col, Statistic, Empty } from 'antd'
import { PlusOutlined, ReloadOutlined, PlayCircleOutlined, FileTextOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { tasksApi } from '../api'

const Tasks: React.FC = () => {
  const [data, setData] = useState<any>({ items: [], total: 0 })
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [logOpen, setLogOpen] = useState(false)
  const [logItems, setLogItems] = useState<any[]>([])
  const [currentTask, setCurrentTask] = useState<any>(null)
  const [lastResult, setLastResult] = useState<any>(null)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try { setData(await tasksApi.list({ page_size: 50 })) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const onCreate = () => { form.resetFields(); form.setFieldsValue({ schedule_date: dayjs() }); setOpen(true) }
  const onSubmit = async () => {
    const v = await form.validateFields()
    try {
      await tasksApi.create({
        ...v,
        schedule_date: v.schedule_date ? v.schedule_date.format('YYYY-MM-DD') : null,
        total_amount: v.total_amount || 0,
      })
      message.success('任务已创建'); setOpen(false); load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '失败')
    }
  }

  const onRun = async (r: any) => {
    const hide = message.loading(`正在执行任务 ${r.task_code} ...`, 0)
    try {
      const result = await tasksApi.run(r.id)
      hide()
      setCurrentTask(r); setLastResult(result); load()
      message.success(`任务完成，撮合 ¥${result.matched_amount?.toLocaleString()}，缺口 ¥${result.gap_amount?.toLocaleString()}`)
    } catch (e: any) {
      hide()
      message.error(e?.response?.data?.detail || '执行失败')
    }
  }

  const onShowLog = async (r: any) => {
    setCurrentTask(r)
    try {
      const lg = await tasksApi.log(r.id)
      setLogItems(lg.items || []); setLogOpen(true)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载失败')
    }
  }

  const statusColor = (s: string) => s === 'DONE' ? 'green' : s === 'RUNNING' ? 'gold' : s === 'FAILED' ? 'red' : 'blue'
  const statusLabel = (s: string) => ({ DONE: '已完成', RUNNING: '运行中', PENDING: '待执行', FAILED: '失败' } as any)[s] || s

  const cols = [
    { title: '任务编码', dataIndex: 'task_code', width: 130 },
    { title: '任务名称', dataIndex: 'task_name', width: 180 },
    { title: '调度日期', dataIndex: 'schedule_date', width: 120 },
    { title: '总额', dataIndex: 'total_amount', width: 150, render: (v: number) => v?.toLocaleString() },
    { title: '撮合额', dataIndex: 'matched_amount', width: 150, render: (v: number) => v?.toLocaleString() },
    { title: '撮合笔数', dataIndex: 'matched_count', width: 100 },
    { title: '缺口', dataIndex: 'gap_amount', width: 150,
      render: (v: number) => <span style={{ color: v > 0 ? '#f5222d' : '#52c41a' }}>{v?.toLocaleString()}</span> },
    { title: '状态', dataIndex: 'status', width: 100,
      render: (v: string) => <Tag color={statusColor(v)}>{statusLabel(v)}</Tag> },
    { title: '开始', dataIndex: 'started_at', width: 170 },
    { title: '结束', dataIndex: 'finished_at', width: 170 },
    { title: '操作', width: 200, fixed: 'right' as const,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" size="small" icon={<PlayCircleOutlined />}
            disabled={r.status === 'RUNNING'}
            onClick={() => onRun(r)}>执行</Button>
          <Button type="link" size="small" icon={<FileTextOutlined />} onClick={() => onShowLog(r)}>流水</Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="page-title">
        <span className="page-title-icon" />
        组算任务
        <Space style={{ marginLeft: 'auto' }}>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>新建任务</Button>
        </Space>
      </div>

      {lastResult && (
        <Card title={`最近执行结果：${currentTask?.task_code || ''}`} size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={12} md={6}><Statistic title="撮合金额" value={lastResult.matched_amount} suffix="元" valueStyle={{ color: '#667eea' }} /></Col>
            <Col xs={12} md={6}><Statistic title="撮合笔数" value={lastResult.matched_count} suffix="笔" /></Col>
            <Col xs={12} md={6}><Statistic title="缺口金额" value={lastResult.gap_amount} suffix="元" valueStyle={{ color: '#764ba2' }} /></Col>
            <Col xs={12} md={6}><Statistic title="状态" value={statusLabel(lastResult.status)} valueStyle={{ color: '#52c41a' }} /></Col>
          </Row>
        </Card>
      )}

      <Card><Table rowKey="id" dataSource={data.items} columns={cols} loading={loading} pagination={{ pageSize: 20 }} scroll={{ x: 1500 }} /></Card>

      <Modal title="新建组算任务" open={open} onCancel={() => setOpen(false)} onOk={onSubmit} width={520}>
        <Form form={form} layout="vertical">
          <Form.Item label="任务编码" name="task_code" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="任务名称" name="task_name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="调度日期" name="schedule_date"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item label="预期总额（元）" name="total_amount"><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item label="说明" name="description"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal title={`任务流水：${currentTask?.task_code || ''}`} open={logOpen} onCancel={() => setLogOpen(false)} footer={null} width={720}>
        {logItems.length ? logItems.map((it: any) => (
          <Card size="small" key={it.id} style={{ marginBottom: 8 }} title={<><Tag color="purple">{it.log_type}</Tag> <span style={{ color: '#999', fontSize: 12 }}>{it.created_at}</span></>}>
            <pre style={{ background: '#fafafa', padding: 12, borderRadius: 6, margin: 0, fontSize: 12, overflow: 'auto' }}>
              {JSON.stringify(it.payload, null, 2)}
            </pre>
          </Card>
        )) : <Empty description="暂无流水" />}
      </Modal>
    </div>
  )
}

export default Tasks
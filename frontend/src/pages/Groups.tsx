import React, { useEffect, useState } from 'react'
import { Table, Tag, Card, Button, Modal, Form, Input, Select, InputNumber, Space, message, Popconfirm } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { groupsApi } from '../api'

const Groups: React.FC = () => {
  const [data, setData] = useState<any>({ items: [], total: 0 })
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try { setData(await groupsApi.list({ page_size: 50 })) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const onCreate = () => { setEditing(null); form.resetFields(); setOpen(true) }
  const onEdit = (r: any) => {
    setEditing(r); form.setFieldsValue(r); setOpen(true)
  }
  const onSubmit = async () => {
    const v = await form.validateFields()
    try {
      if (editing) await groupsApi.update(editing.id, v)
      else await groupsApi.create(v)
      message.success(editing ? '更新成功' : '创建成功')
      setOpen(false); load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '失败')
    }
  }

  const cols = [
    { title: '组编码', dataIndex: 'group_code', width: 130 },
    { title: '组名称', dataIndex: 'group_name', width: 180 },
    { title: '类型', dataIndex: 'group_type', width: 110,
      render: (v: string) => <Tag color="blue">{v || '-'}</Tag> },
    { title: '币种', dataIndex: 'currency', width: 80 },
    { title: '总额度', dataIndex: 'total_limit', width: 150,
      render: (v: number) => v?.toLocaleString() },
    { title: '已用', dataIndex: 'used_limit', width: 150,
      render: (v: number, r: any) => `${v?.toLocaleString()} (${r.total_limit ? (v / r.total_limit * 100).toFixed(1) : '0'}%)` },
    { title: '状态', dataIndex: 'status', width: 90,
      render: (v: string) => <Tag color={v === 'ACTIVE' ? 'green' : 'default'}>{v}</Tag> },
    { title: '说明', dataIndex: 'description', ellipsis: true },
    { title: '操作', width: 140, fixed: 'right' as const,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => onEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除？" okText="删除" cancelText="取消" okButtonProps={{ danger: true }}
            onConfirm={async () => { await groupsApi.delete(r.id); message.success('已删除'); load() }}>
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
        资金组管理
        <Space style={{ marginLeft: 'auto' }}>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>新增资金组</Button>
        </Space>
      </div>
      <Card><Table rowKey="id" dataSource={data.items} columns={cols} loading={loading} pagination={{ pageSize: 20 }} scroll={{ x: 1100 }} /></Card>

      <Modal title={editing ? '编辑资金组' : '新增资金组'} open={open} onCancel={() => setOpen(false)} onOk={onSubmit} width={560}>
        <Form form={form} layout="vertical">
          <Form.Item label="组编码" name="group_code" rules={[{ required: true }]}><Input disabled={!!editing} /></Form.Item>
          <Form.Item label="组名称" name="group_name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="类型" name="group_type">
            <Select options={[
              { label: '内部组', value: 'INTERNAL' },
              { label: '外部组', value: 'EXTERNAL' },
              { label: '跨境组', value: 'CROSS_BORDER' },
              { label: '同业组', value: 'INTERBANK' },
            ]} />
          </Form.Item>
          <Form.Item label="币种" name="currency" initialValue="CNY"><Input /></Form.Item>
          <Form.Item label="总额度" name="total_limit"><InputNumber style={{ width: '100%' }} step={10000} /></Form.Item>
          <Form.Item label="已用额度" name="used_limit"><InputNumber style={{ width: '100%' }} step={10000} /></Form.Item>
          <Form.Item label="状态" name="status" initialValue="ACTIVE">
            <Select options={[{ label: '启用', value: 'ACTIVE' }, { label: '停用', value: 'INACTIVE' }]} />
          </Form.Item>
          <Form.Item label="说明" name="description"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Groups
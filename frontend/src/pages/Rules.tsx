import React, { useEffect, useState } from 'react'
import { Table, Tag, Card, Button, Modal, Form, Input, Select, InputNumber, Space, message, Popconfirm } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { rulesApi } from '../api'

const Rules: React.FC = () => {
  const [data, setData] = useState<any>({ items: [], total: 0 })
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try { setData(await rulesApi.list({ page_size: 50 })) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const onCreate = () => { setEditing(null); form.resetFields(); setOpen(true) }
  const onEdit = (r: any) => { setEditing(r); form.setFieldsValue(r); setOpen(true) }
  const onSubmit = async () => {
    const v = await form.validateFields()
    try {
      if (editing) await rulesApi.update(editing.id, v)
      else await rulesApi.create(v)
      message.success(editing ? '更新成功' : '创建成功')
      setOpen(false); load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '失败')
    }
  }

  const cols = [
    { title: '规则编码', dataIndex: 'rule_code', width: 130 },
    { title: '规则名称', dataIndex: 'rule_name', width: 180 },
    { title: '类型', dataIndex: 'rule_type', width: 130,
      render: (v: string) => <Tag color="purple">{v || '-'}</Tag> },
    { title: '优先级', dataIndex: 'priority', width: 80,
      render: (v: number) => <Tag color={v >= 100 ? 'red' : v >= 50 ? 'gold' : 'blue'}>{v}</Tag> },
    { title: '币种', dataIndex: 'currency', width: 80 },
    { title: '阈值', dataIndex: 'threshold', width: 130, render: (v: number) => v?.toLocaleString() },
    { title: '动作', dataIndex: 'action', width: 130, render: (v: string) => <Tag>{v}</Tag> },
    { title: '状态', dataIndex: 'status', width: 90,
      render: (v: string) => <Tag color={v === 'ACTIVE' ? 'green' : 'default'}>{v}</Tag> },
    { title: '说明', dataIndex: 'description', ellipsis: true },
    { title: '操作', width: 140, fixed: 'right' as const,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => onEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除？" okText="删除" cancelText="取消" okButtonProps={{ danger: true }}
            onConfirm={async () => { await rulesApi.delete(r.id); message.success('已删除'); load() }}>
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
        组算规则
        <Space style={{ marginLeft: 'auto' }}>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>新增规则</Button>
        </Space>
      </div>
      <Card><Table rowKey="id" dataSource={data.items} columns={cols} loading={loading} pagination={{ pageSize: 20 }} scroll={{ x: 1300 }} /></Card>

      <Modal title={editing ? '编辑规则' : '新增规则'} open={open} onCancel={() => setOpen(false)} onOk={onSubmit} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item label="规则编码" name="rule_code" rules={[{ required: true }]}><Input disabled={!!editing} /></Form.Item>
          <Form.Item label="规则名称" name="rule_name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="类型" name="rule_type">
            <Select options={[
              { label: '内部调拨', value: 'INTERNAL_TRANSFER' },
              { label: '同业拆借', value: 'INTERBANK' },
              { label: '央行回购', value: 'REPO' },
              { label: '债券质押', value: 'BOND_PLEDGE' },
              { label: '额度分配', value: 'QUOTA_ALLOC' },
            ]} />
          </Form.Item>
          <Form.Item label="优先级（数字越大越优先）" name="priority" initialValue={50}><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item label="源组编码" name="source_group"><Input /></Form.Item>
          <Form.Item label="目标组编码" name="target_group"><Input /></Form.Item>
          <Form.Item label="币种" name="currency"><Input /></Form.Item>
          <Form.Item label="触发阈值" name="threshold"><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item label="动作" name="action">
            <Select options={[
              { label: '自动撮合', value: 'AUTO_MATCH' },
              { label: '手动审批', value: 'MANUAL_REVIEW' },
              { label: '告警', value: 'ALERT' },
              { label: '拒绝', value: 'REJECT' },
            ]} />
          </Form.Item>
          <Form.Item label="状态" name="status" initialValue="ACTIVE">
            <Select options={[{ label: '启用', value: 'ACTIVE' }, { label: '停用', value: 'INACTIVE' }]} />
          </Form.Item>
          <Form.Item label="说明" name="description"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Rules
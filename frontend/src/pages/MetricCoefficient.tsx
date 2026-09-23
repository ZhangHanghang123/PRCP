import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, DatePicker, Popconfirm, Tooltip, Upload, Alert, Statistic, Divider,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, DownloadOutlined, UploadOutlined,
  EditOutlined, DeleteOutlined,
  CalculatorOutlined, FileExcelOutlined, FilterOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { metricCoefficientApi, coaApi } from '../api'

interface OptionItem {
  dict_key: string
  dict_label: string
  color?: string
}

interface SchemeItem {
  id: number
  scheme_code: string
  scheme_name: string
}

interface NodeItem {
  id: number
  scheme_id: number
  node_code: string
  node_name: string
  node_level?: number
  label?: string
}

interface MCRecord {
  id: string
  scheme_id: number
  scheme_code: string
  node_id: number
  node_code: string
  metric_type: string
  metric_code: string
  data_date: string
  current_value: number
  y1_value: number
  y2_value: number
  y3_value: number
  y4_value: number
  y5_value: number
  unit: string
  description?: string
  status: string
  scheme_name?: string
  node_name?: string
  updated_at?: string
}

const MetricCoefficient: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [records, setRecords] = useState<MCRecord[]>([])
  const [schemes, setSchemes] = useState<SchemeItem[]>([])
  const [nodes, setNodes] = useState<NodeItem[]>([])
  const [metricTypes, setMetricTypes] = useState<OptionItem[]>([])
  const [units, setUnits] = useState<OptionItem[]>([])

  // 筛选条件
  const [filterSchemeId, setFilterSchemeId] = useState<number | undefined>(undefined)
  const [filterMetricType, setFilterMetricType] = useState<string | undefined>(undefined)
  const [filterDate, setFilterDate] = useState<Dayjs | null>(dayjs('2026-08-31'))
  const [keyword, setKeyword] = useState<string>('')

  // 新增/编辑
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editing, setEditing] = useState<MCRecord | null>(null)
  const [form] = Form.useForm()

  // 加载选项（一次性拉全：方案 / 节点 / 指标类型 / 单位）
  const loadOptions = async () => {
    try {
      const r = await metricCoefficientApi.options()
      setSchemes(r.schemes || [])
      setNodes(r.nodes || [])
      setMetricTypes(r.metric_types || [])
      setUnits(r.units || [])
    } catch (e) {
      message.error('选项加载失败')
    }
  }

  // 按方案筛选节点（供新增表单联动）
  const nodesOfScheme = useMemo(
    () => (filterSchemeId ? nodes.filter((n) => n.scheme_id === filterSchemeId) : nodes),
    [nodes, filterSchemeId],
  )

  // 加载列表
  const loadList = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (filterSchemeId) params.scheme_id = filterSchemeId
      if (filterMetricType) params.metric_type = filterMetricType
      if (filterDate) params.data_date = filterDate.format('YYYY-MM-DD')
      if (keyword) params.keyword = keyword
      const r = await metricCoefficientApi.list(params)
      setRecords(r.items || [])
    } catch (e) {
      message.error('列表加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadOptions() }, [])
  useEffect(() => { loadList() }, [filterSchemeId, filterMetricType, filterDate, keyword])

  // 打开新增
  const onAdd = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      data_date: filterDate || dayjs('2026-08-31'),
      unit: 'PERCENT',
      status: 'ACTIVE',
      scheme_id: filterSchemeId,
      metric_type: 'ROE',
    })
    setEditModalOpen(true)
  }

  // 打开编辑
  const onEdit = (rec: MCRecord) => {
    setEditing(rec)
    form.setFieldsValue({
      ...rec,
      data_date: dayjs(rec.data_date),
    })
    setEditModalOpen(true)
  }

  // 提交
  const onSubmit = async () => {
    try {
      const v = await form.validateFields()
      const dd: Dayjs = v.data_date
      const scheme = schemes.find((s) => s.id === v.scheme_id)
      const node = nodes.find((n) => n.id === v.node_id)
      if (!scheme || !node) { message.error('方案或节点不存在'); return }
      if (node.scheme_id !== v.scheme_id) { message.error('节点不属于该方案'); return }

      const payload = {
        scheme_id: v.scheme_id,
        scheme_code: scheme.scheme_code,
        node_id: v.node_id,
        node_code: node.node_code,
        metric_type: v.metric_type,
        metric_code: v.metric_type,
        data_date: dd.format('YYYY-MM-DD'),
        current_value: v.current_value ?? 0,
        y1_value: v.y1_value ?? 0,
        y2_value: v.y2_value ?? 0,
        y3_value: v.y3_value ?? 0,
        y4_value: v.y4_value ?? 0,
        y5_value: v.y5_value ?? 0,
        unit: v.unit || 'PERCENT',
        description: v.description,
        status: v.status || 'ACTIVE',
      }

      if (editing) {
        // 只更新可改字段
        await metricCoefficientApi.update(editing.id, {
          current_value: payload.current_value,
          y1_value: payload.y1_value, y2_value: payload.y2_value,
          y3_value: payload.y3_value, y4_value: payload.y4_value, y5_value: payload.y5_value,
          unit: payload.unit, description: payload.description, status: payload.status,
        })
        message.success('更新成功')
      } else {
        await metricCoefficientApi.create(payload)
        message.success('新增成功')
      }
      setEditModalOpen(false)
      loadList()
    } catch (e: any) {
      if (e?.errorFields) return // 表单校验失败
      message.error(e?.response?.data?.detail || '操作失败')
    }
  }

  // 删除
  const onRemove = async (rec: MCRecord) => {
    try {
      await metricCoefficientApi.remove(rec.id)
      message.success('删除成功')
      loadList()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }

  // 导入 Excel
  const onImport = async (file: File) => {
    try {
      const r = await metricCoefficientApi.importXlsx(file)
      Modal.info({
        title: '导入结果',
        width: 520,
        content: (
          <div>
            <p>新建：<b style={{ color: '#52c41a' }}>{r.created}</b> 条</p>
            <p>更新：<b style={{ color: '#1890ff' }}>{r.updated}</b> 条</p>
            <p>跳过：<b style={{ color: '#faad14' }}>{r.skipped}</b> 条</p>
            {r.errors?.length ? (
              <>
                <p>错误明细（最多 20 条）：</p>
                <pre style={{ maxHeight: 200, overflow: 'auto', background: '#fafafa', padding: 8, fontSize: 12 }}>
                  {r.errors.join('\n')}
                </pre>
              </>
            ) : null}
          </div>
        ),
      })
      loadList()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '导入失败')
    }
    return false // 阻止 Upload 默认上传
  }

  // 表格列
  const columns: ColumnsType<MCRecord> = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 280,
      fixed: 'left',
      render: (v: string) => (
        <Tooltip title={v}>
          <code style={{ fontSize: 11, color: '#666' }}>{v.length > 30 ? v.slice(0, 30) + '…' : v}</code>
        </Tooltip>
      ),
    },
    { title: '数据日期', dataIndex: 'data_date', width: 110 },
    {
      title: '账户册方案', dataIndex: 'scheme_code', width: 130,
      render: (v: string, r: MCRecord) => (
        <Tooltip title={r.scheme_name}>
          <Tag color="blue">{v}</Tag>
        </Tooltip>
      ),
    },
    {
      title: '账户册编码', dataIndex: 'node_code', width: 140,
      render: (v: string, r: MCRecord) => (
        <Tooltip title={r.node_name}>
          <Tag color="geekblue">{v}</Tag>
        </Tooltip>
      ),
    },
    {
      title: '指标类型', dataIndex: 'metric_type', width: 200,
      render: (v: string) => {
        const m = metricTypes.find((x) => x.dict_key === v)
        return <Tag color={m?.color || 'purple'}>{m?.dict_label || v}</Tag>
      },
    },
    { title: '当前值', dataIndex: 'current_value', width: 100, align: 'right' as const,
      render: (v: number) => <span style={{ fontWeight: 600 }}>{Number(v).toFixed(4)}</span> },
    { title: '未来一年', dataIndex: 'y1_value', width: 100, align: 'right' as const,
      render: (v: number) => Number(v).toFixed(4) },
    { title: '未来两年', dataIndex: 'y2_value', width: 100, align: 'right' as const,
      render: (v: number) => Number(v).toFixed(4) },
    { title: '未来三年', dataIndex: 'y3_value', width: 100, align: 'right' as const,
      render: (v: number) => Number(v).toFixed(4) },
    { title: '未来四年', dataIndex: 'y4_value', width: 100, align: 'right' as const,
      render: (v: number) => Number(v).toFixed(4) },
    { title: '未来五年', dataIndex: 'y5_value', width: 100, align: 'right' as const,
      render: (v: number) => Number(v).toFixed(4) },
    {
      title: '单位', dataIndex: 'unit', width: 80,
      render: (v: string) => {
        const u = units.find((x) => x.dict_key === v)
        return <Tag>{u?.dict_label || v}</Tag>
      },
    },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => <Tag color={v === 'ACTIVE' ? 'green' : 'default'}>{v}</Tag>,
    },
    {
      title: '操作', width: 130, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button size="small" icon={<EditOutlined />} onClick={() => onEdit(r)} />
          </Tooltip>
          <Popconfirm
            title="确认删除该条记录？"
            okType="danger"
            onConfirm={() => onRemove(r)}
          >
            <Tooltip title="删除">
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 统计
  const stats = useMemo(() => {
    const total = records.length
    const schemes = new Set(records.map((r) => r.scheme_code)).size
    const nodes = new Set(records.map((r) => `${r.scheme_code}/${r.node_code}`)).size
    const metrics = new Set(records.map((r) => r.metric_type)).size
    return { total, schemes, nodes, metrics }
  }, [records])

  return (
    <div style={{ padding: 16 }}>
      <Card
        title={
          <Space>
            <CalculatorOutlined style={{ color: '#722ed1' }} />
            <span>指标计量系数维护</span>
            <Tag color="purple">数据维护</Tag>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<DownloadOutlined />} onClick={() => {
              window.open(metricCoefficientApi.exportTemplateUrl(), '_blank')
            }}>
              下载模板
            </Button>
            <Upload accept=".xlsx,.xls" showUploadList={false} beforeUpload={onImport}>
              <Button icon={<UploadOutlined />}>导入 Excel</Button>
            </Upload>
            <Button type="primary" icon={<PlusOutlined />} onClick={onAdd}>
              新增记录
            </Button>
          </Space>
        }
      >
        {/* 顶部 KPI 统计 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic title="记录总数" value={stats.total} prefix={<FileExcelOutlined />} valueStyle={{ color: '#722ed1' }} />
          </Col>
          <Col span={6}>
            <Statistic title="覆盖方案数" value={stats.schemes} suffix="个" />
          </Col>
          <Col span={6}>
            <Statistic title="覆盖节点数" value={stats.nodes} suffix="个" />
          </Col>
          <Col span={6}>
            <Statistic title="覆盖指标类型" value={stats.metrics} suffix="种" valueStyle={{ color: '#1890ff' }} />
          </Col>
        </Row>

        {/* 筛选条 */}
        <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
          <Space size="middle" wrap>
            <span><FilterOutlined /> 筛选：</span>
            <Select
              allowClear
              placeholder="账户册方案"
              style={{ width: 200 }}
              options={schemes.map((s) => ({ value: s.id, label: `${s.scheme_code} | ${s.scheme_name}` }))}
              value={filterSchemeId}
              onChange={setFilterSchemeId}
            />
            <Select
              allowClear
              placeholder="指标类型"
              style={{ width: 200 }}
              options={metricTypes.map((m) => ({ value: m.dict_key, label: m.dict_label }))}
              value={filterMetricType}
              onChange={setFilterMetricType}
            />
            <DatePicker
              picker="month"
              placeholder="数据日期"
              value={filterDate}
              onChange={setFilterDate}
              format="YYYY-MM"
            />
            <Input.Search
              placeholder="搜索方案/节点/备注"
              style={{ width: 240 }}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onSearch={() => loadList()}
              allowClear
            />
            <Button icon={<ReloadOutlined />} onClick={() => {
              setKeyword('')
              loadList()
            }}>重置</Button>
          </Space>
        </Card>

        <Alert
          message="ID 生成规则"
          description={
            <span>
              每条记录的唯一 ID = <code>{'{scheme_code}_{node_code}_{metric_code}_{YYYYMMDD}'}</code>，
              例如 <code>COA_V6_ZX_A011_ROE_20260831</code>。修改方案/节点/指标/日期会生成新记录。
            </span>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Table<MCRecord>
          rowKey="id"
          columns={columns}
          dataSource={records}
          loading={loading}
          size="middle"
          scroll={{ x: 1500 }}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
          }}
          locale={{ emptyText: <Empty description="暂无指标计量系数记录，点击右上角【新增记录】开始维护" /> }}
        />
      </Card>

      {/* 新增/编辑 Modal */}
      <Modal
        title={editing ? `编辑指标计量系数 - ${editing.id}` : '新增指标计量系数'}
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={onSubmit}
        width={780}
        okText="保存"
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="账户册方案" name="scheme_id" rules={[{ required: true, message: '请选择账户册方案' }]}>
                <Select
                  placeholder="选择方案"
                  options={schemes.map((s) => ({ value: s.id, label: `${s.scheme_code} | ${s.scheme_name}` }))}
                  showSearch
                  optionFilterProp="label"
                  onChange={() => form.setFieldValue('node_id', undefined)}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="账户册节点"
                name="node_id"
                rules={[{ required: true, message: '请选择账户册节点' }]}
              >
                <Select
                  placeholder="选择节点（按方案过滤）"
                  options={nodesOfScheme.map((n) => ({ value: n.id, label: n.label }))}
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="指标类型" name="metric_type" rules={[{ required: true, message: '请选择指标类型' }]}>
                <Select
                  placeholder="选择指标类型（字典 METRIC_TYPE）"
                  options={metricTypes.map((m) => ({ value: m.dict_key, label: m.dict_label }))}
                  disabled={!!editing}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="数据日期" name="data_date" rules={[{ required: true, message: '请选择数据日期' }]}>
                <DatePicker picker="month" style={{ width: '100%' }} format="YYYY-MM" disabled={!!editing} />
              </Form.Item>
            </Col>
          </Row>
          <Divider style={{ margin: '8px 0' }}>计量数值（共 6 期）</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="当前值" name="current_value">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={4} placeholder="如 12.5" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="未来一年" name="y1_value">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={4} placeholder="如 13.0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="未来两年" name="y2_value">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={4} placeholder="如 13.5" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="未来三年" name="y3_value">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={4} placeholder="如 14.0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="未来四年" name="y4_value">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={4} placeholder="如 14.5" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="未来五年" name="y5_value">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={4} placeholder="如 15.0" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="计量单位" name="unit">
                <Select options={units.map((u) => ({ value: u.dict_key, label: u.dict_label }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="状态" name="status">
                <Select options={[{ value: 'ACTIVE', label: 'ACTIVE' }, { value: 'DISABLED', label: 'DISABLED' }]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="备注" name="description">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default MetricCoefficient
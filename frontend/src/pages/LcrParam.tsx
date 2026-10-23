import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Empty, DatePicker, Popconfirm, Tooltip, Alert, Statistic, Divider, Switch,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined,
  EditOutlined, DeleteOutlined,
  ExperimentOutlined, FileExcelOutlined, FilterOutlined, CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { lcrParamApi } from '../api'

interface OperatorItem {
  dict_key: string
  dict_label: string
  sort_order: number
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

interface LcrRecord {
  id: string
  scheme_id: number
  scheme_code: string
  node_id: number
  node_code: string
  node_name: string
  data_date: string
  is_numerator: number
  num_factor: number
  num_operator: string
  is_denominator: number
  den_factor: number
  den_operator: string
  current_balance: number
  rule_note?: string
  status: string
  scheme_name?: string
  updated_at?: string
}

const LcrParam: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [records, setRecords] = useState<LcrRecord[]>([])
  const [schemes, setSchemes] = useState<SchemeItem[]>([])
  const [nodes, setNodes] = useState<NodeItem[]>([])
  const [operators, setOperators] = useState<OperatorItem[]>([])
  const [availableDates, setAvailableDates] = useState<string[]>([])

  // 筛选（默认 ZX_COA + 2025-12-31）
  const [filterSchemeId, setFilterSchemeId] = useState<number | undefined>(undefined)
  const [filterDate, setFilterDate] = useState<Dayjs | null>(dayjs('2025-12-31'))
  const [keyword, setKeyword] = useState<string>('')

  // 新增/编辑
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editing, setEditing] = useState<LcrRecord | null>(null)
  const [form] = Form.useForm()

  // 加载选项
  const loadOptions = async () => {
    try {
      const r = await lcrParamApi.options()
      const schemeList = r.schemes || []
      setSchemes(schemeList)
      setNodes(r.nodes || [])
      setOperators(r.operators || [])
      setAvailableDates(r.data_dates || [])
      // 默认选 ZX_COA（演示数据所在方案）
      const zxcoa = schemeList.find((s: SchemeItem) => s.scheme_code === 'ZX_COA')
      if (zxcoa) setFilterSchemeId(zxcoa.id)
      else if (schemeList.length && !filterSchemeId) setFilterSchemeId(schemeList[0].id)
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
      if (filterDate) params.data_date = filterDate.format('YYYY-MM-DD')
      if (keyword) params.keyword = keyword
      const r = await lcrParamApi.list(params)
      setRecords(r.items || [])
    } catch (e) {
      message.error('列表加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadOptions() }, [])
  useEffect(() => { loadList() }, [filterSchemeId, filterDate])

  // ---------- 新增/编辑 ----------
  const onAdd = () => {
    setEditing(null)
    form.resetFields()
    if (filterSchemeId) {
      const sch = schemes.find((s) => s.id === filterSchemeId)
      form.setFieldsValue({
        scheme_id: filterSchemeId,
        scheme_code: sch?.scheme_code,
        data_date: filterDate || dayjs('2025-12-31'),
        is_numerator: false,
        num_factor: 0,
        num_operator: '+',
        is_denominator: false,
        den_factor: 0,
        den_operator: '+',
        current_balance: 0,
        status: 'ACTIVE',
      })
    }
    setEditModalOpen(true)
  }

  const onEdit = (r: LcrRecord) => {
    setEditing(r)
    form.setFieldsValue({
      scheme_id: r.scheme_id,
      scheme_code: r.scheme_code,
      node_id: r.node_id,
      node_code: r.node_code,
      node_name: r.node_name,
      data_date: dayjs(r.data_date),
      is_numerator: !!r.is_numerator,
      num_factor: r.num_factor,
      num_operator: r.num_operator,
      is_denominator: !!r.is_denominator,
      den_factor: r.den_factor,
      den_operator: r.den_operator,
      current_balance: r.current_balance,
      rule_note: r.rule_note,
      status: r.status,
    })
    setEditModalOpen(true)
  }

  const onSave = async () => {
    const v = await form.validateFields()
    try {
      const data_date = (v.data_date as Dayjs).format('YYYY-MM-DD')
      // 自动补 node_name（前端没传时）
      let node_name = v.node_name
      if (!node_name && v.node_id) {
        const nd = nodes.find((n) => n.id === v.node_id)
        node_name = nd?.node_name || ''
      }
      const payload = {
        scheme_id: v.scheme_id,
        scheme_code: v.scheme_code,
        node_id: v.node_id,
        node_code: v.node_code,
        node_name,
        data_date,
        is_numerator: v.is_numerator ? 1 : 0,
        num_factor: Number(v.num_factor || 0),
        num_operator: v.num_operator,
        is_denominator: v.is_denominator ? 1 : 0,
        den_factor: Number(v.den_factor || 0),
        den_operator: v.den_operator,
        rule_note: v.rule_note,
        status: v.status || 'ACTIVE',
      }
      if (editing) {
        await lcrParamApi.update(editing.id, payload)
        message.success('已更新')
      } else {
        await lcrParamApi.create(payload)
        message.success('已新增')
      }
      setEditModalOpen(false)
      loadList()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  const onRemove = async (r: LcrRecord) => {
    try {
      await lcrParamApi.remove(r.id)
      message.success('已删除')
      loadList()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }

  // 表格列
  const columns: ColumnsType<LcrRecord> = [
    {
      title: '数据日期', dataIndex: 'data_date', width: 110, fixed: 'left' as const,
      render: (v: string) => <Tag color="cyan">{v}</Tag>,
    },
    {
      title: '账户册编码', dataIndex: 'node_code', width: 160,
      render: (v: string, r: LcrRecord) => (
        <Tooltip title={`${v} · ${r.node_name || ''}`}>
          <span style={{ whiteSpace: 'nowrap', fontFamily: 'monospace' }}>
            <Tag color="geekblue">{v}</Tag>
          </span>
        </Tooltip>
      ),
    },
    {
      title: '账户册名称', dataIndex: 'node_name', width: 220,
      render: (v: string, r: LcrRecord) => (
        <Tooltip title={v}>
          <span style={{
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            display: 'inline-block', maxWidth: 210,
          }}>{v}</span>
        </Tooltip>
      ),
    },
    {
      title: '是否分子', dataIndex: 'is_numerator', width: 90, align: 'center' as const,
      render: (v: number) => v ? <Tag color="green" icon={<CheckCircleOutlined />}>是</Tag>
        : <Tag color="default" icon={<CloseCircleOutlined />}>否</Tag>,
    },
    {
      title: <Tooltip title="分子折算系数 = 项目计入 LCR 分子（HQLA）的权重比例。系数 = 0 表示该项目纳入分子计算口径但实际贡献为 0">
        <span>分子折算系数</span>
      </Tooltip>,
      dataIndex: 'num_factor', width: 130, align: 'right' as const,
      render: (v: number) => Number(v) === 0
        ? <span style={{ fontFamily: 'monospace', color: '#bfbfbf' }}>0.000000<small style={{ marginLeft: 4, color: '#999' }}>(贡献为0)</small></span>
        : <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{Number(v).toFixed(6)}</span>,
    },
    {
      title: '分子运算符', dataIndex: 'num_operator', width: 110, align: 'center' as const,
      render: (v: string) => {
        const op = operators.find((o) => o.dict_key === v)
        return <Tag color={v === '+' ? 'blue' : 'orange'} style={{ fontFamily: 'monospace', fontWeight: 600 }}>{op?.dict_label || v}</Tag>
      },
    },
    {
      title: '是否分母', dataIndex: 'is_denominator', width: 90, align: 'center' as const,
      render: (v: number) => v ? <Tag color="green" icon={<CheckCircleOutlined />}>是</Tag>
        : <Tag color="default" icon={<CloseCircleOutlined />}>否</Tag>,
    },
    {
      title: <Tooltip title="分母折算系数 = 项目计入 LCR 分母（30 天现金流出）的权重比例。系数 = 0 表示该项目纳入分母计算口径但实际贡献为 0">
        <span>分母折算系数</span>
      </Tooltip>,
      dataIndex: 'den_factor', width: 130, align: 'right' as const,
      render: (v: number) => Number(v) === 0
        ? <span style={{ fontFamily: 'monospace', color: '#bfbfbf' }}>0.000000<small style={{ marginLeft: 4, color: '#999' }}>(贡献为0)</small></span>
        : <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{Number(v).toFixed(6)}</span>,
    },
    {
      title: '分母运算符', dataIndex: 'den_operator', width: 110, align: 'center' as const,
      render: (v: string) => {
        const op = operators.find((o) => o.dict_key === v)
        return <Tag color={v === '+' ? 'blue' : 'orange'} style={{ fontFamily: 'monospace', fontWeight: 600 }}>{op?.dict_label || v}</Tag>
      },
    },
    {
      title: '规则说明', dataIndex: 'rule_note', width: 240,
      render: (v: string) => (
        <Tooltip title={v}>
          <span style={{
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            display: 'inline-block', maxWidth: 230, color: '#666',
          }}>{v}</span>
        </Tooltip>
      ),
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
    const numYes = records.filter((r) => r.is_numerator).length
    const denYes = records.filter((r) => r.is_denominator).length
    return { total, numYes, denYes }
  }, [records])

  return (
    <div style={{ padding: 16 }}>
      <Card
        title={
          <Space>
            <ExperimentOutlined style={{ color: '#13c2c2' }} />
            <span>LCR 参数补录</span>
            <Tag color="cyan">计量参数补录</Tag>
          </Space>
        }
        extra={
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={onAdd}>
              新增记录
            </Button>
          </Space>
        }
      >
        {/* KPI 统计 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Statistic title="记录总数" value={stats.total} prefix={<FileExcelOutlined />} valueStyle={{ color: '#13c2c2' }} />
          </Col>
          <Col span={8}>
            <Statistic title="分子节点数" value={stats.numYes} suffix="个" valueStyle={{ color: '#52c41a' }} />
          </Col>
          <Col span={8}>
            <Statistic title="分母节点数" value={stats.denYes} suffix="个" valueStyle={{ color: '#fa8c16' }} />
          </Col>
        </Row>

        {/* 筛选条 */}
        <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
          <Space size="middle" wrap>
            <span><FilterOutlined /> 筛选：</span>
            <Select
              allowClear
              placeholder="账户册方案"
              style={{ width: 240 }}
              options={schemes.map((s) => ({ value: s.id, label: `${s.scheme_code} | ${s.scheme_name}` }))}
              value={filterSchemeId}
              onChange={setFilterSchemeId}
            />
            <DatePicker
              placeholder="数据日期"
              value={filterDate}
              onChange={(d) => { setFilterDate(d); loadList() }}
              format="YYYY-MM-DD"
              allowClear
            />
            <Input.Search
              placeholder="搜索账户册编码 / 名称 / 规则说明"
              style={{ width: 260 }}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onSearch={() => loadList()}
              allowClear
            />
            <Button icon={<ReloadOutlined />} onClick={() => {
              const zxcoa = schemes.find((s) => s.scheme_code === 'ZX_COA')
              setFilterSchemeId(zxcoa ? zxcoa.id : (schemes[0]?.id))
              setFilterDate(dayjs('2025-12-31'))
              setKeyword('')
            }}>重置</Button>
          </Space>
        </Card>

        <Alert
          message="ID 生成规则与字段说明"
          description={
            <span>
              每条记录 ID = <code>{'{scheme_code}_{node_code}_{YYYYMMDD}'}</code>，
              例如 <code>ZX_COA_S010102010101_20251231</code>。
              <strong>分子</strong>：HQLA 折算（如国债 Level 1 折 100%、公司债 Level 2A 折 85%）。
              <strong>分母</strong>：30 天现金流出（如对公活期 48.5%、零售活期 8%、同业拆入 100%）。
              修改方案/节点/数据日期会生成新记录。
            </span>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Table<LcrRecord>
          rowKey="id"
          columns={columns}
          dataSource={records}
          loading={loading}
          size="middle"
          scroll={{ x: 1600 }}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
          }}
          locale={{ emptyText: <Empty description="暂无 LCR 参数记录，点击右上角【新增记录】开始维护" /> }}
        />
      </Card>

      {/* 新增/编辑 Modal */}
      <Modal
        title={editing ? `编辑 LCR 参数：${editing.node_code}` : '新增 LCR 参数'}
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={onSave}
        width={720}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="账户册方案" name="scheme_id" rules={[{ required: true }]}>
                <Select
                  placeholder="选择账户册方案"
                  options={schemes.map((s) => ({ value: s.id, label: `${s.scheme_code} | ${s.scheme_name}` }))}
                  onChange={(v) => {
                    const sch = schemes.find((s) => s.id === v)
                    if (sch) form.setFieldsValue({ scheme_code: sch.scheme_code })
                  }}
                  disabled={!!editing}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="数据日期" name="data_date" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" disabled={!!editing} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="账户册节点" name="node_id" rules={[{ required: true }]}>
            <Select
              showSearch
              placeholder="选择账户册节点"
              optionFilterProp="label"
              options={nodesOfScheme.map((n) => ({
                value: n.id,
                label: `${n.node_code} | ${n.node_name}`,
                node_code: n.node_code,
                node_name: n.node_name,
              }))}
              onChange={(v) => {
                const nd = nodesOfScheme.find((n) => n.id === v)
                if (nd) {
                  form.setFieldsValue({
                    node_code: nd.node_code,
                    node_name: nd.node_name,
                  })
                }
              }}
              disabled={!!editing}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="账户册编码" name="node_code">
                <Input disabled placeholder="选择节点后自动填充" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="账户册名称" name="node_name">
                <Input disabled placeholder="选择节点后自动填充" />
              </Form.Item>
            </Col>
          </Row>

          <Divider style={{ margin: '8px 0' }}>分子参数（HQLA 合格优质流动性资产）</Divider>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="是否分子" name="is_numerator" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={9}>
              <Form.Item label="分子折算系数" name="num_factor">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={6} min={0} max={1} />
              </Form.Item>
            </Col>
            <Col span={9}>
              <Form.Item label="分子运算符" name="num_operator">
                <Select
                  options={operators.map((o) => ({ value: o.dict_key, label: o.dict_label }))}
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider style={{ margin: '8px 0' }}>分母参数（30 天净流出）</Divider>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="是否分母" name="is_denominator" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={9}>
              <Form.Item label="分母折算系数" name="den_factor">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={6} min={0} />
              </Form.Item>
            </Col>
            <Col span={9}>
              <Form.Item label="分母运算符" name="den_operator">
                <Select
                  options={operators.map((o) => ({ value: o.dict_key, label: o.dict_label }))}
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider style={{ margin: '8px 0' }}>其他</Divider>
          <Form.Item label="LCR 规则说明" name="rule_note">
            <Input.TextArea rows={2} placeholder="如：对公一般贷款 流入 100%" />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select
              options={[
                { value: 'ACTIVE', label: 'ACTIVE 启用' },
                { value: 'INACTIVE', label: 'INACTIVE 停用' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default LcrParam
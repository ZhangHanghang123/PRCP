/** 新业务模拟方案 — 列表页
 *
 * 入口：左侧菜单「新业务模拟方案」
 * 功能：方案 CRUD（list / create / update / delete / toggle status）+ 跳转参数配置
 */
import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Form, Input, Select, Button, Table, Space, Tag, Modal, message,
  Popconfirm, Tooltip, Row, Col, InputNumber, Statistic, DatePicker, Progress, Alert,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined,
  SettingOutlined, PlayCircleOutlined, CheckCircleOutlined, StopOutlined,
  CalendarOutlined, RocketOutlined, ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { useNavigate } from 'react-router-dom'
import { simApi } from '../api'

const STATUS_OPTIONS = [
  { value: 'ACTIVE',   label: '启用',   color: 'green'  },
  { value: 'INACTIVE', label: '停用', color: 'default' },
]

const SimSchemeList: React.FC = () => {
  const navigate = useNavigate()
  const [schemes, setSchemes] = useState<any[]>([])
  const [coaSchemes, setCoaSchemes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [filterKw, setFilterKw] = useState('')
  const [filterStatus, setFilterStatus] = useState<string | undefined>(undefined)
  const [filterCoa, setFilterCoa] = useState<number | undefined>(undefined)

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  // ============== 数据加载 ==============
  const loadSchemes = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (filterKw) params.keyword = filterKw
      if (filterStatus) params.status = filterStatus
      if (filterCoa) params.coa_scheme_id = filterCoa
      const r = await simApi.listSchemes(params)
      setSchemes(r.items || [])
    } catch (e: any) {
      message.error('方案加载失败')
    } finally {
      setLoading(false)
    }
  }

  const loadCoaSchemes = async () => {
    try {
      const r = await simApi.listCoaSchemes()
      setCoaSchemes(r.items || [])
    } catch {
      // 静默
    }
  }

  useEffect(() => { loadCoaSchemes() }, [])
  useEffect(() => { loadSchemes() }, [filterStatus, filterCoa])

  const handleSearch = () => loadSchemes()
  const handleReset = () => {
    setFilterKw(''); setFilterStatus(undefined); setFilterCoa(undefined)
    setTimeout(loadSchemes, 0)
  }

  // ============== 方案 CRUD ==============
  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      status: 'ACTIVE',
      data_date: dayjs().startOf('month'),  // 默认本月第一天
    })
    setModalOpen(true)
  }

  const openEdit = (row: any) => {
    setEditing(row)
    form.setFieldsValue({
      scheme_code: row.scheme_code,
      scheme_name: row.scheme_name,
      coa_scheme_id: row.coa_scheme_id,
      data_date: row.data_date ? dayjs(row.data_date) : null,
      description: row.description,
      status: row.status,
    })
    setModalOpen(true)
  }

  const handleSave = async () => {
    const v = await form.validateFields()
    // 转 dayjs → 'YYYY-MM-DD'
    const payload = {
      ...v,
      data_date: v.data_date ? (v.data_date as Dayjs).format('YYYY-MM-DD') : null,
    }
    try {
      if (editing) {
        await simApi.updateScheme(editing.id, payload)
        message.success('方案已更新（coa_scheme_id / data_date 不可改）')
      } else {
        const r = await simApi.createScheme(payload)
        message.success(`方案已创建 id=${r.id}，起始月=${r.data_date}`)
      }
      setModalOpen(false)
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  const handleDelete = async (row: any) => {
    try {
      const r = await simApi.deleteScheme(row.id)
      message.success(`方案已删除（级联 ${r.deleted_configs || 0} 个配置）`)
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }

  const handleToggleStatus = async (row: any) => {
    const newStatus = row.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
    try {
      await simApi.toggleStatus(row.id, newStatus)
      message.success(`方案已${newStatus === 'ACTIVE' ? '启用' : '停用'}`)
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '状态切换失败')
    }
  }

  const goConfig = (row: any) => {
    navigate(`/sim/config/${row.id}`)
  }

  // ============== 引擎计量 ==============
  const [runModalOpen, setRunModalOpen] = useState(false)
  const [runningScheme, setRunningScheme] = useState<any>(null)
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState<any>(null)
  const [progress, setProgress] = useState(0)
  const [pollTimer, setPollTimer] = useState<any>(null)

  const openRun = (row: any) => {
    setRunningScheme(row)
    setRunResult(null)
    setProgress(0)
    setRunModalOpen(true)
  }

  const startRun = async (monthCount: number) => {
    if (!runningScheme) return
    setRunning(true)
    setProgress(0)
    setRunResult(null)
    try {
      const r = await simApi.runEngine(runningScheme.id, monthCount)
      message.success(`引擎执行成功 run_id=${r.run_id}`)
      setRunResult(r)
      setProgress(100)
      // 自动跳转结果页
      setTimeout(() => {
        setRunModalOpen(false)
        navigate(`/sim/results/${runningScheme.scheme_code}`)
      }, 1500)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '引擎执行失败')
      setRunResult({ status: 'FAILED', error_message: e?.response?.data?.detail || '未知错误' })
    } finally {
      setRunning(false)
      if (pollTimer) { clearInterval(pollTimer); setPollTimer(null) }
    }
  }

  // ============== 统计 KPI ==============
  const stats = useMemo(() => {
    const total = schemes.length
    const active = schemes.filter(s => s.status === 'ACTIVE').length
    const inactive = total - active
    const totalConfigs = schemes.reduce((a, s) => a + (s.config_node_count || 0), 0)
    return { total, active, inactive, totalConfigs }
  }, [schemes])

  // ============== 表格列 ==============
  const columns: ColumnsType<any> = [
    {
      title: '方案编码', dataIndex: 'scheme_code', width: 160,
      render: (v: string) => <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 3 }}>{v}</code>,
    },
    {
      title: '方案名称', dataIndex: 'scheme_name', width: 200,
      render: (v: string, r: any) => (
        <Space direction="vertical" size={0}>
          <strong>{v}</strong>
          {r.description && (
            <span style={{ fontSize: 12, color: '#999' }}>{r.description}</span>
          )}
        </Space>
      ),
    },
    {
      title: '关联账户册方案', width: 220,
      render: (_: any, r: any) => (
        <Space direction="vertical" size={0}>
          <code style={{ fontSize: 12 }}>{r.coa_scheme_code || '-'}</code>
          <span style={{ fontSize: 12, color: '#666' }}>{r.coa_scheme_name || '-'}</span>
        </Space>
      ),
    },
    {
      title: (
        <Space size={4}>
          <CalendarOutlined />
          数据日期
        </Space>
      ),
      dataIndex: 'data_date', width: 120,
      render: (v: string) => v ? <Tag color="cyan" style={{ fontFamily: 'monospace' }}>{v}</Tag> : <span style={{ color: '#999' }}>-</span>,
    },
    {
      title: '已配置节点', dataIndex: 'config_node_count', width: 110,
      align: 'center',
      render: (n: number) => (
        <Tag color={n > 0 ? 'blue' : 'default'}>{n ?? 0}</Tag>
      ),
    },
    {
      title: '状态', dataIndex: 'status', width: 90,
      filters: STATUS_OPTIONS.map(s => ({ text: s.label, value: s.value })),
      onFilter: (val, r) => r.status === val,
      render: (v: string) => {
        const opt = STATUS_OPTIONS.find(s => s.value === v)
        return <Tag color={opt?.color}>{opt?.label || v}</Tag>
      },
    },
    {
      title: '创建时间', dataIndex: 'created_at', width: 170,
      render: (v: string) => v ? <span style={{ fontSize: 12, color: '#666' }}>{v.replace('T', ' ').slice(0, 19)}</span> : '-',
    },
    {
      title: '操作', width: 340, fixed: 'right',
      render: (_: any, r: any) => (
        <Space size="small">
          <Tooltip title="参数配置（节点年化增长 + 期限占比）">
            <Button
              size="small" icon={<SettingOutlined />}
              onClick={() => goConfig(r)}
            >参数配置</Button>
          </Tooltip>
          <Tooltip title="触发引擎按月滚动生成 24 月快照">
            <Button
              type="primary" size="small" icon={<RocketOutlined />}
              onClick={() => openRun(r)}
              disabled={r.status !== 'ACTIVE' || r.config_node_count === 0}
            >引擎计量</Button>
          </Tooltip>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Tooltip title={r.status === 'ACTIVE' ? '停用' : '启用'}>
            <Button
              size="small"
              icon={r.status === 'ACTIVE' ? <StopOutlined /> : <CheckCircleOutlined />}
              onClick={() => handleToggleStatus(r)}
            >
              {r.status === 'ACTIVE' ? '停用' : '启用'}
            </Button>
          </Tooltip>
          <Popconfirm
            title="确认删除此方案？"
            description={
              <div>
                将级联软删该方案下 <strong>{r.config_node_count || 0}</strong> 个节点配置及其期限占比子表
              </div>
            }
            onConfirm={() => handleDelete(r)}
            okText="确认删除" cancelText="取消" okButtonProps={{ danger: true }}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="page-container">
      <Card
        title={
          <Space>
            <PlayCircleOutlined style={{ color: '#722ed1' }} />
            <span>新业务模拟方案</span>
            <span style={{ fontSize: 12, color: '#999', fontWeight: 'normal' }}>
              配置账户册节点的新业务年化增长 + 期限分布，作为反算驾驶舱的前置输入
            </span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadSchemes}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新增方案
            </Button>
          </Space>
        }
      >
        {/* 顶部 4 KPI 统计 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small" style={{ background: '#f0f5ff' }}>
              <Statistic title="方案总数" value={stats.total} prefix={<PlayCircleOutlined style={{ color: '#2f54eb' }} />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: '#f6ffed' }}>
              <Statistic title="启用中" value={stats.active} prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: '#fff7e6' }}>
              <Statistic title="已停用" value={stats.inactive} prefix={<StopOutlined style={{ color: '#fa8c16' }} />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: '#f9f0ff' }}>
              <Statistic title="累计节点配置数" value={stats.totalConfigs} prefix={<SettingOutlined style={{ color: '#722ed1' }} />} />
            </Card>
          </Col>
        </Row>

        {/* 筛选条 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Input.Search
              placeholder="搜索方案编码 / 方案名称"
              allowClear
              enterButton
              value={filterKw}
              onChange={(e) => setFilterKw(e.target.value)}
              onSearch={handleSearch}
            />
          </Col>
          <Col span={5}>
            <Select
              style={{ width: '100%' }}
              placeholder="状态筛选"
              allowClear
              value={filterStatus}
              onChange={setFilterStatus}
              options={STATUS_OPTIONS}
            />
          </Col>
          <Col span={7}>
            <Select
              style={{ width: '100%' }}
              placeholder="关联账户册方案筛选"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filterCoa}
              onChange={setFilterCoa}
              options={coaSchemes.map(c => ({
                value: c.id, label: `${c.scheme_code} | ${c.scheme_name}`,
              }))}
            />
          </Col>
          <Col span={4}>
            <Button onClick={handleReset} block>重置</Button>
          </Col>
        </Row>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={schemes}
          loading={loading}
          size="middle"
          scroll={{ x: 1300 }}
          pagination={{
            showSizeChanger: true, showQuickJumper: true,
            pageSize: 20, pageSizeOptions: ['10', '20', '50'],
            showTotal: (t) => `共 ${t} 条`,
          }}
        />
      </Card>

      {/* 新增/编辑 Modal */}
      <Modal
        title={editing ? `编辑方案 — ${editing.scheme_code}` : '新增新业务模拟方案'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        width={640}
        destroyOnClose
        okText="保存" cancelText="取消"
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="方案编码" name="scheme_code"
                rules={[
                  { required: true, message: '请输入方案编码' },
                  { max: 32, message: '最多 32 字符' },
                  { pattern: /^[A-Za-z0-9_]+$/, message: '仅允许字母、数字、下划线' },
                ]}
              >
                <Input placeholder="例如：SIM_BS_2026" disabled={!!editing} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="方案名称" name="scheme_name"
                rules={[{ required: true, message: '请输入方案名称' }, { max: 64 }]}
              >
                <Input placeholder="例如：资负表新业务模拟 2026" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label="关联账户册方案"
            name="coa_scheme_id"
            rules={[{ required: true, message: '请选择关联账户册方案' }]}
            extra={
              editing
                ? <span style={{ color: '#fa8c16' }}>⚠ 创建后不可修改</span>
                : '新业务模拟基于该账户册方案的节点结构进行配置'
            }
          >
            <Select
              placeholder="选择 ACTIVE 状态的账户册方案"
              showSearch
              optionFilterProp="label"
              disabled={!!editing}
              options={coaSchemes.map(c => ({
                value: c.id, label: `${c.scheme_code} | ${c.scheme_name}（${c.node_count || 0} 节点）`,
              }))}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="数据日期（模拟起始月）"
                name="data_date"
                rules={[{ required: true, message: '请选择基准数据日期' }]}
                extra={
                  editing
                    ? <span style={{ color: '#fa8c16' }}>⚠ 创建后不可修改</span>
                    : <span style={{ color: '#666' }}>引擎从该月开始按月滚动生成快照</span>
                }
              >
                <DatePicker
                  picker="month"
                  format="YYYY-MM"
                  placeholder="选择起始月"
                  disabled={!!editing}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="状态" name="status" rules={[{ required: true }]}>
                <Select options={STATUS_OPTIONS} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="方案的用途和说明" maxLength={500} showCount />
          </Form.Item>
        </Form>
      </Modal>

      {/* 引擎计量 Modal */}
      <Modal
        title={
          <Space>
            <RocketOutlined style={{ color: '#722ed1' }} />
            <span>引擎计量 — 按月滚动生成 24 月快照</span>
          </Space>
        }
        open={runModalOpen}
        onCancel={() => { if (!running) setRunModalOpen(false) }}
        footer={null}
        width={560}
        destroyOnClose
        maskClosable={false}
      >
        {runningScheme && (
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <Card size="small" style={{ background: '#f9f0ff' }}>
              <Space direction="vertical" size={4}>
                <span><strong>方案：</strong>
                  <Tag color="purple">{runningScheme.scheme_code}</Tag>
                  {runningScheme.scheme_name}
                </span>
                <span><strong>起始月：</strong>
                  <Tag color="cyan" style={{ fontFamily: 'monospace' }}>{runningScheme.data_date}</Tag>
                </span>
                <span><strong>已配置节点：</strong>
                  <Tag color="blue">{runningScheme.config_node_count || 0}</Tag>
                </span>
              </Space>
            </Card>

            {!runResult && !running && (
              <Form
                layout="inline"
                initialValues={{ month_count: 24 }}
                onFinish={(v) => startRun(v.month_count)}
              >
                <Form.Item label="生成月份数" name="month_count" rules={[{ required: true }]}>
                  <InputNumber min={1} max={60} style={{ width: 100 }} />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" icon={<ThunderboltOutlined />}>
                    开始执行
                  </Button>
                </Form.Item>
              </Form>
            )}

            {running && (
              <Card size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <span style={{ color: '#1890ff' }}>
                    <ThunderboltOutlined spin /> 引擎执行中…
                  </span>
                  <Progress percent={progress} status="active" />
                  <span style={{ fontSize: 12, color: '#999' }}>
                    正在为每个节点按月滚动计算 64+64 期限桶 + 4 主指标…
                  </span>
                </Space>
              </Card>
            )}

            {runResult && runResult.status === 'SUCCESS' && (
              <Alert
                type="success" showIcon
                message={`✅ 引擎执行成功 run_id=${runResult.run_id}`}
                description={
                  <div>
                    已生成 <strong>{runResult.month_count}</strong> 月快照，1.5 秒后跳转到结果查看页…
                  </div>
                }
              />
            )}

            {runResult && runResult.status === 'FAILED' && (
              <Alert
                type="error" showIcon
                message="❌ 引擎执行失败"
                description={<code>{runResult.error_message}</code>}
              />
            )}
          </Space>
        )}
      </Modal>
    </div>
  )
}

export default SimSchemeList

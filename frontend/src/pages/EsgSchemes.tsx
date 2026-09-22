/** PRCP ESG 场景工厂 · 方案管理列表页
 *
 * 入口：左侧菜单「ESG 场景工厂」/ 路由 /esg
 * 功能：方案 CRUD + 状态切换 + 一键演示 + 跳转方案详情
 */
import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Form, Input, Select, Button, Table, Space, Tag, Modal, message,
  Popconfirm, Row, Col, Statistic, Alert, Empty, DatePicker, Tooltip,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined,
  RocketOutlined, EyeOutlined, CopyOutlined, ThunderboltOutlined,
  AreaChartOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { useNavigate } from 'react-router-dom'
import {
  esgApi, yieldCurveApi,
  DEFAULT_MATURITIES_MONTHS, ESG_SOURCE_OPTIONS, ESG_STATUS_OPTIONS,
  EsgScheme,
} from '../api/esg'

const EsgSchemes: React.FC = () => {
  const navigate = useNavigate()
  const [schemes, setSchemes] = useState<EsgScheme[]>([])
  const [loading, setLoading] = useState(false)
  const [filterKw, setFilterKw] = useState('')
  const [filterStatus, setFilterStatus] = useState<string | undefined>(undefined)
  const [filterSource, setFilterSource] = useState<string | undefined>(undefined)

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<EsgScheme | null>(null)
  const [form] = Form.useForm()

  // 一键演示 loading
  const [oneClickLoading, setOneClickLoading] = useState(false)
  // 4 源曲线统计
  const [sourceStats, setSourceStats] = useState<{ source: string; count: number }[]>([])

  // ============== 数据加载 ==============

  const loadSchemes = async () => {
    setLoading(true)
    try {
      const params: any = { page_size: 100 }
      if (filterKw) params.keyword = filterKw
      if (filterStatus) params.status = filterStatus
      const r = await esgApi.listSchemes(params)
      setSchemes(r.items || [])
    } catch {
      message.error('方案加载失败')
    } finally {
      setLoading(false)
    }
  }

  const loadSourceStats = async () => {
    try {
      const r = await yieldCurveApi.sources()
      setSourceStats(r.items || [])
    } catch { /* 静默 */ }
  }

  useEffect(() => { loadSourceStats() }, [])
  useEffect(() => { loadSchemes() }, [filterStatus])

  const handleReset = () => {
    setFilterKw(''); setFilterStatus(undefined); setFilterSource(undefined)
    setTimeout(loadSchemes, 0)
  }

  // ============== 方案 CRUD ==============

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      status: 'DRAFT',
      data_source: 'ECB',
      n_factors: 3,
      maturities_months: DEFAULT_MATURITIES_MONTHS,
      n_scenarios: 1000,
      n_steps: 120,
      seed: 42,
    })
    setModalOpen(true)
  }

  const openEdit = (row: EsgScheme) => {
    setEditing(row)
    form.setFieldsValue({
      scheme_code: row.scheme_code,
      scheme_name: row.scheme_name,
      data_source: row.data_source,
      start_date: row.start_date ? dayjs(row.start_date) : null,
      end_date: row.end_date ? dayjs(row.end_date) : null,
      n_factors: row.n_factors,
      maturities_months: row.maturities_months,
      n_scenarios: row.n_scenarios,
      n_steps: row.n_steps,
      seed: row.seed,
      description: row.description,
      status: row.status,
    })
    setModalOpen(true)
  }

  const handleSave = async () => {
    const v = await form.validateFields()
    const payload = {
      ...v,
      start_date: v.start_date ? (v.start_date as Dayjs).format('YYYY-MM-DD') : null,
      end_date: v.end_date ? (v.end_date as Dayjs).format('YYYY-MM-DD') : null,
    }
    try {
      if (editing) {
        await esgApi.updateScheme(editing.id, payload)
        message.success(`方案已更新（缓存已清）`)
      } else {
        await esgApi.createScheme(payload)
        message.success('方案已创建')
      }
      setModalOpen(false)
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  const handleDelete = async (row: EsgScheme) => {
    try {
      await esgApi.deleteScheme(row.id)
      message.success(`已删除 ${row.scheme_code}`)
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }

  const handleClone = async (row: EsgScheme) => {
    const newCode = prompt(`克隆为新方案 code（建议 ${row.scheme_code}_COPY_N）：`)
    if (!newCode) return
    try {
      await esgApi.cloneScheme(row.id, newCode, `${row.scheme_name} (副本)`)
      message.success(`已克隆为 ${newCode}`)
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '克隆失败')
    }
  }

  const handleOneClick = async () => {
    setOneClickLoading(true)
    try {
      const r = await esgApi.runOneClickCase('ECB')
      message.success(
        `一键案例完成：scheme=${r.scheme_id} pca_run=${r.pca_run_id} hjm_run=${r.hjm_run_id} scenario=${r.scenario_code}`
      )
      navigate(`/esg/detail/${r.scheme_id}`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '一键案例失败')
    } finally {
      setOneClickLoading(false)
    }
  }

  // ============== 派生 ==============

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { DRAFT: 0, READY: 0, ARCHIVED: 0 }
    for (const s of schemes) counts[s.status] = (counts[s.status] || 0) + 1
    return counts
  }, [schemes])

  const totalRuns = useMemo(() => schemes.reduce((a, s) => a + (s.run_count || 0), 0), [schemes])

  const filteredSchemes = useMemo(() => {
    if (!filterSource) return schemes
    return schemes.filter((s) => s.data_source === filterSource)
  }, [schemes, filterSource])

  // ============== 表格列 ==============

  const columns: ColumnsType<EsgScheme> = [
    { title: '#', dataIndex: 'id', width: 60 },
    { title: 'Scheme Code', dataIndex: 'scheme_code', width: 180,
      render: (v: string, row: EsgScheme) => (
        <Space>
          <code style={{ fontSize: 12 }}>{v}</code>
          {row.scheme_code === 'PRCP_ESG_DEMO_001' && (
            <Tag color="cyan" style={{ marginLeft: 0 }}>演示</Tag>
          )}
        </Space>
      ),
    },
    { title: '方案名', dataIndex: 'scheme_name', width: 180 },
    { title: '数据源', dataIndex: 'data_source', width: 90,
      render: (v: string) => {
        const c = ESG_SOURCE_OPTIONS.find((x) => x.value === v)
        return <Tag color={c?.color}>{c?.label || v}</Tag>
      },
    },
    { title: '起止日期', width: 180,
      render: (_: any, row: EsgScheme) =>
        row.start_date && row.end_date ? `${row.start_date} ~ ${row.end_date}` : <span style={{ color: '#999' }}>未设</span>,
    },
    { title: '因子/情景/步数', width: 150,
      render: (_: any, row: EsgScheme) => (
        <Space size={4}>
          <Tag color="purple">{row.n_factors}F</Tag>
          <Tag color="orange">{row.n_scenarios}S</Tag>
          <Tag color="gold">{row.n_steps}T</Tag>
        </Space>
      ),
    },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => {
        const c = ESG_STATUS_OPTIONS.find((x) => x.value === v)
        return <Tag color={c?.color}>{c?.label || v}</Tag>
      },
    },
    { title: '运行', dataIndex: 'run_count', width: 70,
      render: (v: number) => v > 0 ? <Tag color="blue">{v}</Tag> : <span style={{ color: '#999' }}>-</span>,
    },
    { title: '最近运行', dataIndex: 'last_run_at', width: 160,
      render: (v: string | null) => v ? v.replace('T', ' ').slice(0, 16) : <span style={{ color: '#999' }}>-</span>,
    },
    {
      title: '操作', width: 180, fixed: 'right',
      render: (_: any, row: EsgScheme) => (
        <Space size={4}>
          <Tooltip title="详情/执行">
            <Button size="small" type="primary" icon={<EyeOutlined />}
                    onClick={() => navigate(`/esg/detail/${row.id}`)} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)} />
          </Tooltip>
          <Tooltip title="克隆">
            <Button size="small" icon={<CopyOutlined />} onClick={() => handleClone(row)} />
          </Tooltip>
          <Popconfirm title={`删除 ${row.scheme_code}?`} onConfirm={() => handleDelete(row)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // ============== 渲染 ==============

  return (
    <div className="page-container">
      {/* 顶部 4 KPI 卡 + 4 源曲线统计 */}
      <Card size="small" style={{ marginBottom: 12, background: 'linear-gradient(135deg, #f0f5ff 0%, #f9f0ff 100%)' }}>
        <Row gutter={16}>
          <Col span={5}>
            <Statistic title="方案总数" value={schemes.length}
              prefix={<AreaChartOutlined style={{ color: '#722ed1' }} />} />
          </Col>
          <Col span={5}>
            <Statistic title="READY 状态" value={statusCounts.READY || 0}
              valueStyle={{ color: '#52c41a' }} />
          </Col>
          <Col span={5}>
            <Statistic title="DRAFT 状态" value={statusCounts.DRAFT || 0}
              valueStyle={{ color: '#999' }} />
          </Col>
          <Col span={5}>
            <Statistic title="总运行次数" value={totalRuns}
              valueStyle={{ color: '#13c2c2' }} />
          </Col>
        </Row>
        <Row gutter={16} style={{ marginTop: 12 }}>
          <Col span={20}>
            <Space>
              <span style={{ fontSize: 12, color: '#666' }}>4 源曲线:</span>
              {sourceStats.length === 0 ? (
                <span style={{ fontSize: 12, color: '#999' }}>加载中...</span>
              ) : sourceStats.map((s) => {
                const c = ESG_SOURCE_OPTIONS.find((x) => x.value === s.source)
                return (
                  <Tag key={s.source} color={c?.color}>
                    {c?.label || s.source}: {s.count} 行
                  </Tag>
                )
              })}
            </Space>
          </Col>
          <Col span={4} style={{ textAlign: 'right' }}>
            <Button type="primary" icon={<RocketOutlined />}
                    loading={oneClickLoading} onClick={handleOneClick}>
              🚀 一键演示（ECB）
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 过滤栏 */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space>
          <Input.Search
            placeholder="搜索 scheme_code"
            value={filterKw}
            onChange={(e) => setFilterKw(e.target.value)}
            onSearch={loadSchemes}
            style={{ width: 220 }}
            allowClear
          />
          <Select
            placeholder="状态"
            value={filterStatus}
            onChange={setFilterStatus}
            allowClear
            style={{ width: 120 }}
            options={ESG_STATUS_OPTIONS.map((x) => ({ value: x.value, label: x.label }))}
          />
          <Select
            placeholder="数据源"
            value={filterSource}
            onChange={setFilterSource}
            allowClear
            style={{ width: 140 }}
            options={ESG_SOURCE_OPTIONS.map((x) => ({ value: x.value, label: x.label }))}
          />
          <Button icon={<ReloadOutlined />} onClick={loadSchemes}>刷新</Button>
          <Button onClick={handleReset}>重置</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建方案
          </Button>
        </Space>
      </Card>

      {/* 方案表 */}
      <Card size="small">
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={filteredSchemes}
          size="small"
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1280 }}
          locale={{
            emptyText: (
              <Empty
                description="暂无 ESG 方案。点击「🚀 一键演示」3 秒跑完 PCA + HJM + 情景集"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      </Card>

      {/* 创建/编辑 Modal */}
      <Modal
        title={editing ? `编辑方案 ${editing.scheme_code}` : '新建 ESG 方案'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        width={700}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Scheme Code" name="scheme_code"
                rules={[{ required: true, min: 3, max: 32, pattern: /^[A-Za-z0-9_]+$/ }]}>
                <Input placeholder="如 ESG_DEMO_001" disabled={!!editing} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Scheme Name" name="scheme_name"
                rules={[{ required: true, min: 2, max: 64 }]}>
                <Input placeholder="方案的展示名" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item label="数据源" name="data_source"
                rules={[{ required: true }]}>
                <Select options={ESG_SOURCE_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="起始日期" name="start_date">
                <DatePicker style={{ width: '100%' }} placeholder="选填" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="结束日期" name="end_date">
                <DatePicker style={{ width: '100%' }} placeholder="选填" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={6}>
              <Form.Item label="PCA 因子数" name="n_factors"
                rules={[{ required: true, type: 'number', min: 1, max: 6 }]}>
                <Input type="number" min={1} max={6} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="情景数" name="n_scenarios"
                rules={[{ required: true, type: 'number', min: 10, max: 10000 }]}>
                <Input type="number" min={10} max={10000} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="步数（月）" name="n_steps"
                rules={[{ required: true, type: 'number', min: 12, max: 360 }]}>
                <Input type="number" min={12} max={360} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="随机种子" name="seed">
                <Input type="number" min={0} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="期限数组（月）" name="maturities_months"
            tooltip="13 期限点 [1,3,6,12,24,36,48,60,84,120,180,240,360] 为默认">
            <Select mode="multiple" placeholder="选择期限（默认 13 点）"
              options={[1, 3, 6, 12, 24, 36, 48, 60, 84, 120, 180, 240, 360].map((m) => ({
                value: m, label: `${m} 月`,
              }))} />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="描述" name="description">
                <Input placeholder="方案的详细描述（选填）" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="状态" name="status"
                rules={[{ required: true }]}>
                <Select options={ESG_STATUS_OPTIONS} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}

export default EsgSchemes
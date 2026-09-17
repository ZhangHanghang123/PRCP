import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Select, Space, Button, Tag, Empty, Spin, Row, Col, Tooltip, Statistic,
  Modal, Form, Input, InputNumber, DatePicker, message, Tabs, Table,
} from 'antd'
import {
  ReloadOutlined, DownloadOutlined, LineChartOutlined, DatabaseOutlined,
  PlusOutlined, EditOutlined, DeleteOutlined, CopyOutlined,
} from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import { rateApi } from '../api'

// 13 个期限点
const TERM_KEYS = ['d1', 'd7', 'm1', 'm3', 'm6', 'y1', 'y2', 'y3', 'y5', 'y10', 'y15', 'y20', 'y30']
const TERM_NAMES: Record<string, string> = {
  d1: '1日', d7: '7日',
  m1: '1M', m3: '3M', m6: '6M',
  y1: '1Y', y2: '2Y', y3: '3Y', y5: '5Y',
  y10: '10Y', y15: '15Y', y20: '20Y', y30: '30Y',
}
const KEY_TERMS = ['y1', 'y5', 'y10']
const CURVE_TYPE_NAMES: Record<string, string> = {
  SOVEREIGN: '国债', POLICY: '政金', CD: '同业存单',
  LPR: 'LPR', FTP: 'FTP', CUSTOM: '自定义',
}
const CURVE_TYPE_COLORS: Record<string, string> = {
  SOVEREIGN: 'blue', POLICY: 'green', CD: 'orange',
  LPR: 'purple', FTP: 'magenta', CUSTOM: 'default',
}

const RateCurve: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [activeScheme, setActiveScheme] = useState<string | null>(null)
  const [points, setPoints] = useState<any[]>([])
  const [activeDate, setActiveDate] = useState<string | null>(null)
  const [compareData, setCompareData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [editingRates, setEditingRates] = useState<Record<string, number>>({})
  const [editingDirty, setEditingDirty] = useState(false)
  const [schemeModal, setSchemeModal] = useState(false)
  const [editingScheme, setEditingScheme] = useState<any>(null)
  const [form] = Form.useForm()

  // 1. 加载曲线方案
  const loadSchemes = async () => {
    const r = await rateApi.listSchemes()
    setSchemes(r.items || [])
    if (r.items?.length && !activeScheme) {
      // 默认选第一个 ACTIVE 的
      const active = r.items.find((s: any) => s.status === 'ACTIVE')
      setActiveScheme((active || r.items[0]).curve_code)
    }
  }
  useEffect(() => { loadSchemes() }, [])

  // 2. 加载利率点
  const loadPoints = async () => {
    if (!activeScheme) return
    setLoading(true)
    try {
      const r = await rateApi.listPoints({ curve_code: activeScheme })
      setPoints(r.items || [])
      if (r.items?.length) {
        setActiveDate((prev) => prev || r.items[0].data_date)
      } else {
        setActiveDate(null)
      }
    } finally { setLoading(false) }
  }
  useEffect(() => { loadPoints() }, [activeScheme])

  // 3. 切换数据日期时，加载 rates 到编辑状态
  const currentPoint = useMemo(
    () => points.find((p: any) => p.data_date === activeDate),
    [points, activeDate]
  )
  useEffect(() => {
    if (currentPoint) {
      setEditingRates(currentPoint.rates)
      setEditingDirty(false)
    } else {
      setEditingRates({})
      setEditingDirty(false)
    }
  }, [currentPoint])

  // 4. 加载历史对比数据
  const loadCompare = async () => {
    if (!activeScheme) return
    const r = await rateApi.compare(activeScheme)
    setCompareData(r.items || [])
  }
  useEffect(() => { loadCompare() }, [activeScheme])

  const onRateChange = (key: string, value: number | null) => {
    setEditingRates({ ...editingRates, [key]: value ?? 0 })
    setEditingDirty(true)
  }

  // 保存当前利率点
  const onSave = async () => {
    if (!activeScheme || !activeDate) {
      message.warning('请选择曲线和数据日期')
      return
    }
    try {
      await rateApi.upsertPoint({
        curve_code: activeScheme,
        data_date: activeDate,
        rates: editingRates,
        remark: '',
      })
      message.success('已保存')
      setEditingDirty(false)
      loadPoints()
      loadCompare()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  // 新增日期
  const onAddDate = () => {
    const newDate = dayjs().format('YYYY-MM-DD')
    setActiveDate(newDate)
    setEditingRates(TERM_KEYS.reduce((acc, k) => ({ ...acc, [k]: 0 }), {}))
    setEditingDirty(true)
  }

  // 导出
  const onExport = async () => {
    if (!activeScheme) return
    try {
      const url = rateApi.exportXlsxUrl(activeScheme)
      const token = localStorage.getItem('prcp_token') || ''
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `prcp_rate_${activeScheme}.xlsx`
      a.click()
      URL.revokeObjectURL(a.href)
      message.success('导出成功')
    } catch (e: any) {
      message.error(`导出失败：${e.message}`)
    }
  }

  // 曲线方案 CRUD
  const onSaveScheme = async () => {
    const v = await form.validateFields()
    try {
      if (editingScheme?.id) {
        await rateApi.updateScheme(editingScheme.id, v)
        message.success('已更新')
      } else {
        await rateApi.createScheme(v)
        message.success('已创建')
      }
      setSchemeModal(false)
      setEditingScheme(null)
      form.resetFields()
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  const onDeleteScheme = async (s: any) => {
    Modal.confirm({
      title: `确认删除 ${s.curve_code}？`,
      content: `该操作会同时删除该曲线下所有利率点（${s.point_count} 条）。`,
      onOk: async () => {
        try {
          await rateApi.deleteScheme(s.id)
          message.success('已删除')
          if (activeScheme === s.curve_code) {
            setActiveScheme(null)
            setPoints([])
          }
          loadSchemes()
        } catch (e: any) {
          message.error(e?.response?.data?.detail || '删除失败')
        }
      },
    })
  }

  const onDeletePoint = async (p: any) => {
    Modal.confirm({
      title: `确认删除 ${p.curve_code} @ ${p.data_date}？`,
      onOk: async () => {
        try {
          await rateApi.deletePoint(p.id)
          message.success('已删除')
          if (activeDate === p.data_date) setActiveDate(null)
          loadPoints()
          loadCompare()
        } catch (e: any) {
          message.error(e?.response?.data?.detail || '删除失败')
        }
      },
    })
  }

  // 度量计算
  const metrics = useMemo(() => {
    const y1 = editingRates.y1 || 0
    const y10 = editingRates.y10 || 0
    const slope = y10 - y1
    // 找前一个日期的 10Y
    const sortedPoints = [...points].sort((a, b) => b.data_date.localeCompare(a.data_date))
    const idx = sortedPoints.findIndex((p: any) => p.data_date === activeDate)
    const prev = idx >= 0 && idx + 1 < sortedPoints.length ? sortedPoints[idx + 1] : null
    const shiftBps = prev ? (y10 - (prev.rates.y10 || 0)) * 100 : 0
    return { slope, shiftBps, hasPrev: !!prev }
  }, [editingRates, points, activeDate])

  // 1️⃣ 曲线明细维护
  const renderMatrix = () => (
    <Row gutter={16}>
      <Col span={6}>
        <Card
          title={<span><DatabaseOutlined /> 曲线方案</span>}
          size="small"
          bordered={false}
          bodyStyle={{ padding: 8, maxHeight: 700, overflowY: 'auto' }}
        >
          {schemes.map((s: any) => (
            <div
              key={s.id}
              onClick={() => setActiveScheme(s.curve_code)}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                borderRadius: 4,
                marginBottom: 4,
                background: activeScheme === s.curve_code ? 'rgba(102,126,234,0.1)' : 'transparent',
                borderLeft: activeScheme === s.curve_code ? '3px solid #667eea' : '3px solid transparent',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Tag color={CURVE_TYPE_COLORS[s.curve_type]} style={{ margin: 0 }}>
                  {CURVE_TYPE_NAMES[s.curve_type]}
                </Tag>
                <span style={{ fontWeight: activeScheme === s.curve_code ? 600 : 400 }}>
                  {s.curve_code}
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
                {s.curve_name}
              </div>
              <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                {s.point_count} 个利率点 · {s.latest_date || '无数据'}
                {s.latest_y10 !== null && <span> · 10Y: <b style={{ color: '#667eea' }}>{s.latest_y10}%</b></span>}
              </div>
            </div>
          ))}
        </Card>
      </Col>
      <Col span={18}>
        <Card
          title={
            <span>
              <LineChartOutlined /> {activeScheme} · 利率点矩阵
              {editingDirty && <Tag color="orange" style={{ marginLeft: 8 }}>未保存</Tag>}
            </span>
          }
          size="small"
          bordered={false}
          bodyStyle={{ padding: 12 }}
          extra={
            <Space>
              <Select
                size="small"
                style={{ width: 160 }}
                value={activeDate || undefined}
                onChange={setActiveDate}
                placeholder="选择数据日期"
                options={points.map((p: any) => ({
                  value: p.data_date,
                  label: p.data_date,
                }))}
              />
              <Button size="small" icon={<PlusOutlined />} onClick={onAddDate}>新增日期</Button>
              <Button size="small" icon={<DownloadOutlined />} onClick={onExport}>导出</Button>
              <Button size="small" type="primary" onClick={onSave} disabled={!editingDirty}>保存</Button>
            </Space>
          }
        >
          <Spin spinning={loading}>
            {/* 13 列利率矩阵 */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(13, 1fr)', gap: 8, marginBottom: 16 }}>
              {TERM_KEYS.map((k) => {
                const isKey = KEY_TERMS.includes(k)
                return (
                  <div
                    key={k}
                    style={{
                      background: isKey ? '#fff7e6' : '#f9fafb',
                      border: isKey ? '2px solid #f59e0b' : '1px solid #e5e7eb',
                      borderRadius: 6,
                      padding: 8,
                      textAlign: 'center',
                    }}
                  >
                    <div style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: isKey ? '#92400e' : '#6b7280',
                      marginBottom: 4,
                    }}>
                      {TERM_NAMES[k]} {k === 'y10' && '⭐'}
                    </div>
                    <InputNumber
                      size="small"
                      style={{ width: '100%' }}
                      value={editingRates[k] ?? 0}
                      onChange={(v) => onRateChange(k, v)}
                      step={0.0001}
                      precision={4}
                      min={0}
                      max={50}
                      formatter={(v) => `${v}%`}
                      parser={(v) => v?.replace('%', '') as any}
                    />
                  </div>
                )
              })}
            </div>

            {/* 度量 */}
            <div style={{
              padding: 12,
              background: '#f0f5fa',
              borderRadius: 6,
              borderLeft: '4px solid #667eea',
            }}>
              <Space size="large">
                <Statistic
                  title={<span style={{ fontSize: 12 }}>斜率（10Y - 1Y）</span>}
                  value={metrics.slope}
                  precision={4}
                  suffix="%"
                  valueStyle={{ fontSize: 18, color: '#667eea' }}
                />
                <Statistic
                  title={<span style={{ fontSize: 12 }}>BP 平移（vs 上日 10Y）</span>}
                  value={metrics.shiftBps}
                  precision={2}
                  suffix="bp"
                  valueStyle={{
                    fontSize: 18,
                    color: metrics.shiftBps > 0 ? '#10b981' : metrics.shiftBps < 0 ? '#ef4444' : '#999',
                  }}
                />
                <Statistic
                  title={<span style={{ fontSize: 12 }}>10Y 利率</span>}
                  value={editingRates.y10 || 0}
                  precision={4}
                  suffix="%"
                  valueStyle={{ fontSize: 18, color: '#f59e0b' }}
                />
              </Space>
            </div>

            {/* 历史利率点列表 */}
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>📜 历史利率点（{points.length} 个）</div>
              <Table
                size="small"
                dataSource={points.map((p: any) => ({ ...p, key: p.id }))}
                pagination={false}
                columns={[
                  { title: '数据日期', dataIndex: 'data_date', width: 110 },
                  {
                    title: '1Y', dataIndex: ['rates', 'y1'], width: 70,
                    render: (v: any) => v?.toFixed(4) + '%',
                  },
                  {
                    title: '5Y', dataIndex: ['rates', 'y5'], width: 70,
                    render: (v: any) => v?.toFixed(4) + '%',
                  },
                  {
                    title: '10Y', dataIndex: ['rates', 'y10'], width: 80,
                    render: (v: any) => <b style={{ color: '#f59e0b' }}>{v?.toFixed(4)}%</b>,
                  },
                  {
                    title: '30Y', dataIndex: ['rates', 'y30'], width: 70,
                    render: (v: any) => v?.toFixed(4) + '%',
                  },
                  {
                    title: '斜率', dataIndex: 'curve_slope', width: 70,
                    render: (v: any) => v?.toFixed(4),
                  },
                  {
                    title: '备注', dataIndex: 'remark', ellipsis: true,
                  },
                  {
                    title: '操作', width: 100, fixed: 'right',
                    render: (_: any, r: any) => (
                      <Space>
                        <Button type="link" size="small" onClick={() => setActiveDate(r.data_date)}>查看</Button>
                        <Button type="link" size="small" danger icon={<DeleteOutlined />}
                          onClick={() => onDeletePoint(r)} />
                      </Space>
                    ),
                  },
                ]}
              />
            </div>
          </Spin>
        </Card>
      </Col>
    </Row>
  )

  // 2️⃣ 历史曲线对比
  const renderCompare = () => (
    <Card title={<span>📈 历史曲线对比 · {activeScheme}</span>} bordered={false} size="small">
      <Spin spinning={loading}>
        <RateCompareChart data={compareData} curveCode={activeScheme || ''} />
        <div style={{ marginTop: 16 }}>
          <Table
            size="small"
            dataSource={compareData.map((d: any) => ({ ...d, key: d.data_date }))}
            pagination={false}
            scroll={{ x: true }}
            columns={[
              { title: '数据日期', dataIndex: 'data_date', fixed: 'left', width: 110 },
              ...TERM_KEYS.map((k) => ({
                title: TERM_NAMES[k],
                dataIndex: ['rates', k],
                width: 80,
                render: (v: any) => v ? v.toFixed(4) + '%' : '-',
              })),
              { title: '斜率', dataIndex: 'curve_slope', width: 80,
                render: (v: any) => v?.toFixed?.(4) || '-' },
            ]}
          />
        </div>
      </Spin>
    </Card>
  )

  // 3️⃣ 曲线方案管理
  const renderManage = () => (
    <Card
      title={<span>⚙️ 曲线方案管理</span>}
      bordered={false}
      size="small"
      extra={
        <Button type="primary" icon={<PlusOutlined />}
          onClick={() => {
            setEditingScheme(null)
            form.resetFields()
            form.setFieldsValue({ ccy: 'CNY', data_source: 'WIND', status: 'ACTIVE' })
            setSchemeModal(true)
          }}
        >
          新建曲线
        </Button>
      }
    >
      <Table
        size="small"
        dataSource={schemes.map((s: any) => ({ ...s, key: s.id }))}
        pagination={false}
        columns={[
          { title: '曲线编码', dataIndex: 'curve_code', width: 130,
            render: (v: string) => <code style={{ fontWeight: 600 }}>{v}</code> },
          { title: '曲线名称', dataIndex: 'curve_name', ellipsis: true },
          { title: '类型', dataIndex: 'curve_type', width: 90,
            render: (v: string) => (
              <Tag color={CURVE_TYPE_COLORS[v]}>{CURVE_TYPE_NAMES[v] || v}</Tag>
            ) },
          { title: '币种', dataIndex: 'ccy', width: 70 },
          { title: '数据源', dataIndex: 'data_source', width: 100 },
          { title: '利率点', dataIndex: 'point_count', width: 80,
            render: (v: number) => <Tag>{v}</Tag> },
          { title: '最新日期', dataIndex: 'latest_date', width: 110 },
          { title: '最新 10Y', dataIndex: 'latest_y10', width: 100,
            render: (v: any) => v !== null ? <b style={{ color: '#667eea' }}>{v}%</b> : '-' },
          { title: '状态', dataIndex: 'status', width: 90,
            render: (v: string) => (
              <Tag color={v === 'ACTIVE' ? 'green' : v === 'HISTORY' ? 'orange' : 'default'}>
                {v}
              </Tag>
            ) },
          { title: '操作', width: 180, fixed: 'right',
            render: (_: any, r: any) => (
              <Space>
                <Button type="link" size="small" icon={<EditOutlined />}
                  onClick={() => {
                    setEditingScheme(r)
                    form.setFieldsValue(r)
                    setSchemeModal(true)
                  }}
                >编辑</Button>
                <Button type="link" size="small" icon={<CopyOutlined />}
                  onClick={() => {
                    setEditingScheme(null)
                    form.setFieldsValue({ ...r, curve_code: `${r.curve_code}_COPY` })
                    setSchemeModal(true)
                  }}
                >复制</Button>
                <Button type="link" size="small" danger icon={<DeleteOutlined />}
                  onClick={() => onDeleteScheme(r)}
                >删除</Button>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  )

  return (
    <>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>
          利率管理 · 收益率曲线
          <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal', marginLeft: 8 }}>
            13 个期限点（1日/7日/1M..30Y）· prcp_rate_point 用列存储
          </span>
        </span>
      </div>

      {/* KPI 概览 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card bordered={false} size="small">
            <Statistic title="曲线方案总数" value={schemes.length} suffix="条"
              prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card bordered={false} size="small">
            <Statistic title="利率点总数"
              value={schemes.reduce((sum: number, s: any) => sum + (s.point_count || 0), 0)}
              suffix="条" />
          </Card>
        </Col>
        <Col span={6}>
          <Card bordered={false} size="small">
            <Statistic title="活跃曲线"
              value={schemes.filter((s: any) => s.status === 'ACTIVE').length}
              suffix="条" valueStyle={{ color: '#10b981' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card bordered={false} size="small">
            <Statistic title={activeScheme ? `${activeScheme} 最新 10Y` : '最新 10Y'}
              value={schemes.find((s: any) => s.curve_code === activeScheme)?.latest_y10 ?? 0}
              precision={4} suffix="%" valueStyle={{ color: '#f59e0b' }} />
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="matrix"
        items={[
          { key: 'matrix', label: '① 曲线明细维护', children: renderMatrix() },
          { key: 'compare', label: '② 历史曲线对比', children: renderCompare() },
          { key: 'manage', label: '③ 曲线方案管理', children: renderManage() },
        ]}
      />

      {/* 曲线方案编辑 Modal */}
      <Modal
        open={schemeModal}
        title={editingScheme?.id ? `编辑曲线：${editingScheme.curve_code}` : '新建曲线方案'}
        onCancel={() => { setSchemeModal(false); setEditingScheme(null) }}
        onOk={onSaveScheme}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="curve_code" label="曲线编码" rules={[{ required: true }]}>
            <Input placeholder="如 CN_SOV_CNY" disabled={!!editingScheme?.id} />
          </Form.Item>
          <Form.Item name="curve_name" label="曲线名称" rules={[{ required: true }]}>
            <Input placeholder="如 中国国债收益率曲线（人民币）" />
          </Form.Item>
          <Form.Item name="curve_type" label="曲线类型" rules={[{ required: true }]}>
            <Select options={Object.entries(CURVE_TYPE_NAMES).map(([k, v]) => ({
              value: k, label: `${k} ${v}`,
            }))} />
          </Form.Item>
          <Form.Item name="ccy" label="币种">
            <Select options={['CNY', 'USD', 'EUR'].map((v) => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item name="data_source" label="数据源">
            <Select options={['WIND', 'CHOICE', '中债登', '央行', '内部', '手工录入'].map((v) => ({
              value: v, label: v,
            }))} />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={['ACTIVE', 'HISTORY', 'DRAFT'].map((v) => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

// 折线对比图（SVG）
const RateCompareChart: React.FC<{ data: any[]; curveCode: string }> = ({ data, curveCode }) => {
  if (!data.length) return <Empty description="无历史数据" />
  // 用最新的 2 个日期对比（实际可以扩展为多日期叠加）
  const latest = data[data.length - 1]
  const prev = data.length > 1 ? data[data.length - 2] : null

  const width = 800, height = 360
  const margin = { top: 20, right: 120, bottom: 40, left: 50 }
  const innerW = width - margin.left - margin.right
  const innerH = height - margin.top - margin.bottom

  // X 轴：13 个期限点（按月数线性映射）
  const termsMonths = [0.033, 0.23, 1, 3, 6, 12, 24, 36, 60, 120, 180, 240, 360]
  const maxMonths = 360
  const xScale = (m: number) => margin.left + (m / maxMonths) * innerW

  // Y 轴：利率范围
  const allRates = TERM_KEYS.map((k) => latest.rates[k] || 0)
    .concat(prev ? TERM_KEYS.map((k) => prev.rates[k] || 0) : [])
  const yMin = Math.floor(Math.min(...allRates) * 10) / 10 - 0.2
  const yMax = Math.ceil(Math.max(...allRates) * 10) / 10 + 0.2
  const yScale = (r: number) => margin.top + innerH - ((r - yMin) / (yMax - yMin)) * innerH

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', maxHeight: 360 }}>
      {/* 网格 */}
      {[yMin, (yMin + yMax) / 2, yMax].map((v) => (
        <g key={v}>
          <line x1={margin.left} y1={yScale(v)} x2={margin.left + innerW} y2={yScale(v)} stroke="#f3f4f6" />
          <text x={margin.left - 6} y={yScale(v) + 4} textAnchor="end" fill="#6b7280" fontSize="11">
            {v.toFixed(1)}%
          </text>
        </g>
      ))}

      {/* X 轴 */}
      <line x1={margin.left} y1={margin.top + innerH} x2={margin.left + innerW} y2={margin.top + innerH} stroke="#d1d5db" />
      {TERM_KEYS.map((k, i) => (
        <g key={k}>
          <line x1={xScale(termsMonths[i])} y1={margin.top + innerH}
            x2={xScale(termsMonths[i])} y2={margin.top + innerH + 4} stroke="#d1d5db" />
          <text x={xScale(termsMonths[i])} y={margin.top + innerH + 18}
            textAnchor="middle" fill="#6b7280" fontSize="11">{TERM_NAMES[k]}</text>
        </g>
      ))}

      {/* 前一日折线 */}
      {prev && (
        <polyline
          fill="none"
          stroke="#9ca3af"
          strokeWidth="2"
          strokeDasharray="4,2"
          points={TERM_KEYS.map((k, i) =>
            `${xScale(termsMonths[i])},${yScale(prev.rates[k] || 0)}`).join(' ')}
        />
      )}
      {/* 当日折线 */}
      <polyline
        fill="none"
        stroke="#667eea"
        strokeWidth="2.5"
        points={TERM_KEYS.map((k, i) =>
          `${xScale(termsMonths[i])},${yScale(latest.rates[k] || 0)}`).join(' ')}
      />
      {/* 关键点 */}
      {['y1', 'y5', 'y10'].map((k) => {
        const idx = TERM_KEYS.indexOf(k)
        return (
          <circle key={k}
            cx={xScale(termsMonths[idx])} cy={yScale(latest.rates[k] || 0)}
            r="4" fill="#f59e0b" stroke="#fff" strokeWidth="2" />
        )
      })}

      {/* 图例 */}
      <g transform={`translate(${margin.left + innerW + 10}, ${margin.top})`}>
        <rect x="0" y="0" width="100" height={prev ? '70px' : '35px'} fill="#fff" stroke="#e5e7eb" rx="4" />
        <line x1="8" y1="14" x2="30" y2="14" stroke="#667eea" strokeWidth="2.5" />
        <text x="34" y="17" fontSize="11" fill="#1f2937">当日 {latest.data_date}</text>
        {prev && (
          <>
            <line x1="8" y1="42" x2="30" y2="42" stroke="#9ca3af" strokeWidth="2" strokeDasharray="4,2" />
            <text x="34" y="45" fontSize="11" fill="#1f2937">前一日 {prev.data_date}</text>
          </>
        )}
      </g>

      <text x={margin.left} y={margin.top - 6} fontSize="11" fill="#6b7280">
        年化利率（%）
      </text>
      <text x={margin.left + innerW} y={height - 6} textAnchor="end" fontSize="11" fill="#6b7280">
        {curveCode}
      </text>
    </svg>
  )
}

export default RateCurve
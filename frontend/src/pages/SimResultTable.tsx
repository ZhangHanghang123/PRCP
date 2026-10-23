/** 新业务模拟 — 结果汇总表
 *
 * 入口：左侧菜单「反算决策 / 新业务模拟结果」
 * 视图：跨方案、跨月份的资产/负债/结果快照汇总
 * - 顶部筛选：方案下拉 + Run 状态 + 预测月
 * - 主体表格：每个方案一行（最新 SUCCESS run 在每个预测月的关键指标）
 * - 左侧统计卡：方案数 / 运行数 / 配置节点 / 资产/负债余额
 */
import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Select, Table, Space, Tag, message, Empty, Row, Col, Statistic,
  Spin, Tooltip, DatePicker, Button,
} from 'antd'
import {
  ReloadOutlined, FundProjectionScreenOutlined, EyeOutlined,
  RiseOutlined, FallOutlined, CheckCircleOutlined, CloseCircleOutlined,
  ClockCircleOutlined, PlayCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { simApi } from '../api'

interface Scheme {
  id: number
  scheme_code: string
  scheme_name: string
  status: string
  config_node_count: number
  data_date: string
}

interface RunRow {
  id: number
  sim_scheme_id: number
  sim_scheme_code: string
  base_data_date: string
  month_count: number
  status: string
  progress: number
  total_nodes: number
  configured_node_count: number
  rolled_node_count: number
  aggregated_node_count: number
  duration_ms: number
  started_at: string
  finished_at: string
}

interface ResultRow {
  sim_scheme_code: string
  run_id: number
  data_date: string
  date_offset: number
  node_code: string
  node_name: string
  node_level: number
  category: string
  current_balance: number
  avg_balance: number
  weighted_rate: number
  interest_amount: number
}

const CATEGORY_META: Record<string, { label: string; color: string }> = {
  ASSET:       { label: '资产',  color: '#1890ff' },
  LIABILITY:   { label: '负债',  color: '#fa8c16' },
  EQUITY:      { label: '权益',  color: '#722ed1' },
  OFF_BALANCE: { label: '表外',  color: '#13c2c2' },
  OTHER:       { label: '其他',  color: '#999999' },
}

function fmtMoney(v: number | undefined): string {
  if (v == null) return '-'
  // 亿元
  const yi = v / 1e8
  if (Math.abs(yi) >= 1) return yi.toFixed(2) + ' 亿'
  return (v / 1e4).toFixed(0) + ' 万'
}
function fmtPct(v: number | undefined): string {
  if (v == null) return '-'
  return (v * 100).toFixed(2) + '%'
}

const SimResultTable: React.FC = () => {
  const navigate = useNavigate()
  const [schemes, setSchemes] = useState<Scheme[]>([])
  const [runs, setRuns] = useState<RunRow[]>([])
  const [results, setResults] = useState<ResultRow[]>([])
  const [loading, setLoading] = useState(false)
  const [schemeCode, setSchemeCode] = useState<string | undefined>(undefined)
  const [dateOffset, setDateOffset] = useState<number | undefined>(undefined)

  // 加载方案 + 全部 run
  const loadBase = async () => {
    try {
      setLoading(true)
      const [ss, rs] = await Promise.all([
        simApi.listSchemes({ status: 'ACTIVE' }),
        simApi.listRuns(),
      ])
      setSchemes((ss?.items ?? ss?.data?.items ?? []) as Scheme[])
      setRuns((rs?.items ?? rs?.data?.items ?? []) as RunRow[])
    } catch (e: any) {
      message.error('加载方案/运行失败：' + (e?.message ?? String(e)))
    } finally {
      setLoading(false)
    }
  }

  // 加载结果
  const loadResults = async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (schemeCode) params.sim_scheme_code = schemeCode
      if (dateOffset) params.date_offset = dateOffset
      const r = await simApi.listResults(params)
      setResults((r?.items ?? r?.data?.items ?? []) as ResultRow[])
    } catch (e: any) {
      message.error('加载结果失败：' + (e?.message ?? String(e)))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadBase() }, [])
  useEffect(() => { loadResults() }, [schemeCode, dateOffset])

  // ========== 顶部统计 ==========
  const totalSchemes = schemes.length
  const totalRuns = runs.length
  const successRuns = runs.filter((r) => r.status === 'SUCCESS').length
  const totalConfiguredNodes = runs
    .filter((r) => r.status === 'SUCCESS')
    .reduce((s, r) => s + (r.configured_node_count || 0), 0)

  // 按 (scheme_code, run_id, date_offset) 汇总
  const grouped = useMemo(() => {
    const map = new Map<string, {
      scheme_code: string
      scheme_name: string
      run_id: number
      data_date: string
      date_offset: number
      asset_total: number
      liability_total: number
      equity_total: number
      off_balance_total: number
      weighted_rate_sum: number
      interest_total: number
      node_count: number
      max_node_level: number
    }>()
    results.forEach((r) => {
      const key = `${r.sim_scheme_code}|${r.run_id}|${r.date_offset}`
      if (!map.has(key)) {
        const sc = schemes.find((s) => s.scheme_code === r.sim_scheme_code)
        map.set(key, {
          scheme_code: r.sim_scheme_code,
          scheme_name: sc?.scheme_name ?? '',
          run_id: r.run_id,
          data_date: r.data_date,
          date_offset: r.date_offset,
          asset_total: 0,
          liability_total: 0,
          equity_total: 0,
          off_balance_total: 0,
          weighted_rate_sum: 0,
          interest_total: 0,
          node_count: 0,
          max_node_level: 0,
        })
      }
      const g = map.get(key)!
      const bal = r.current_balance || 0
      if (r.category === 'ASSET') g.asset_total += bal
      else if (r.category === 'LIABILITY') g.liability_total += bal
      else if (r.category === 'EQUITY') g.equity_total += bal
      else if (r.category === 'OFF_BALANCE') g.off_balance_total += bal
      g.weighted_rate_sum += r.weighted_rate || 0
      g.interest_total += r.interest_amount || 0
      g.node_count += 1
      if (r.node_level > g.max_node_level) g.max_node_level = r.node_level
    })
    return Array.from(map.values()).sort((a, b) => {
      if (a.scheme_code !== b.scheme_code) return a.scheme_code.localeCompare(b.scheme_code)
      if (a.run_id !== b.run_id) return b.run_id - a.run_id
      return a.date_offset - b.date_offset
    })
  }, [results, schemes])

  // Run 状态卡
  const runStats = useMemo(() => {
    const stats: Record<string, number> = {}
    runs.forEach((r) => { stats[r.status] = (stats[r.status] ?? 0) + 1 })
    return stats
  }, [runs])

  // 表格列
  const columns: ColumnsType<any> = [
    {
      title: '方案编码', dataIndex: 'scheme_code', width: 140, fixed: 'left',
      render: (v: string, r: any) => (
        <Space direction="vertical" size={0}>
          <Tag color="purple" style={{ margin: 0 }}>{v}</Tag>
          <span style={{ fontSize: 11, color: '#999' }}>{r.scheme_name}</span>
        </Space>
      ),
    },
    {
      title: 'Run', dataIndex: 'run_id', width: 70,
      render: (v: number) => <Tag color="blue">#{v}</Tag>,
    },
    {
      title: '预测月', dataIndex: 'date_offset', width: 80,
      render: (v: number) => <Tag color="cyan">M{v}</Tag>,
    },
    {
      title: '快照日期', dataIndex: 'data_date', width: 110,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD') : '-',
    },
    {
      title: '资产余额', dataIndex: 'asset_total', width: 110,
      render: (v: number) => <span style={{ color: '#1890ff' }}>{fmtMoney(v)}</span>,
    },
    {
      title: '负债余额', dataIndex: 'liability_total', width: 110,
      render: (v: number) => <span style={{ color: '#fa8c16' }}>{fmtMoney(v)}</span>,
    },
    {
      title: '权益', dataIndex: 'equity_total', width: 100,
      render: (v: number) => <span style={{ color: '#722ed1' }}>{fmtMoney(v)}</span>,
    },
    {
      title: '表外', dataIndex: 'off_balance_total', width: 100,
      render: (v: number) => <span style={{ color: '#13c2c2' }}>{fmtMoney(v)}</span>,
    },
    {
      title: '平均利率', dataIndex: 'weighted_rate_sum', width: 100,
      render: (_: number, r: any) => fmtPct(r.weighted_rate_sum / Math.max(r.node_count, 1)),
    },
    {
      title: '利息收支', dataIndex: 'interest_total', width: 110,
      render: (v: number) => <span style={{ color: '#52c41a' }}>{fmtMoney(v)}</span>,
    },
    {
      title: '节点数', dataIndex: 'node_count', width: 80,
      render: (v: number) => <Tag>{v}</Tag>,
    },
    {
      title: '最大层级', dataIndex: 'max_node_level', width: 90,
      render: (v: number) => <Tag color="geekblue">L{v}</Tag>,
    },
    {
      title: '操作', key: 'action', width: 110, fixed: 'right',
      render: (_: any, r: any) => (
        <Button
          type="link" size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/sim/results/${r.scheme_code}?run_id=${r.run_id}&offset=${r.date_offset}`)}
        >查看明细</Button>
      ),
    },
  ]

  // 可选预测月（从 runs 里推）
  const monthOptions = useMemo(() => {
    const set = new Set<number>()
    runs.forEach((r) => {
      for (let i = 1; i <= (r.month_count || 0); i++) set.add(i)
    })
    return Array.from(set).sort((a, b) => a - b)
  }, [runs])

  return (
    <div className="page-container">
      <div className="page-title">
        <span className="page-title-icon" />
        新业务模拟 · 结果汇总表
        <Tag color="purple" style={{ marginLeft: 12 }}>跨方案汇总</Tag>
      </div>

      {/* 筛选条 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <span style={{ marginRight: 8 }}>业务量方案：</span>
            <Select
              value={schemeCode}
              onChange={(v) => setSchemeCode(v)}
              allowClear
              style={{ width: 220 }}
              placeholder="全部方案"
            >
              {schemes.map((s) => (
                <Select.Option key={s.scheme_code} value={s.scheme_code}>
                  {s.scheme_code} · {s.scheme_name}
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col>
            <span style={{ marginRight: 8 }}>预测月：</span>
            <Select
              value={dateOffset}
              onChange={(v) => setDateOffset(v)}
              allowClear
              style={{ width: 120 }}
              placeholder="全部"
            >
              {monthOptions.map((m) => (
                <Select.Option key={m} value={m}>M{m}</Select.Option>
              ))}
            </Select>
          </Col>
          <Col flex="auto" style={{ textAlign: 'right' }}>
            <ReloadOutlined onClick={() => { loadBase(); loadResults(); }} style={{ cursor: 'pointer', fontSize: 18, color: '#667eea' }} />
          </Col>
        </Row>
      </Card>

      {/* KPI 统计 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="启用方案数" value={totalSchemes} prefix={<PlayCircleOutlined style={{ color: '#722ed1' }} />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="成功运行数 / 总数" value={successRuns} suffix={`/ ${totalRuns}`}
            prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="配置节点总数" value={totalConfiguredNodes} suffix="个"
            prefix={<FundProjectionScreenOutlined style={{ color: '#1890ff' }} />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="汇总结果条数" value={results.length} suffix="行"
            prefix={<RiseOutlined style={{ color: '#fa8c16' }} />} /></Card>
        </Col>
      </Row>

      {/* Run 状态分布 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {Object.entries(runStats).map(([status, n]) => (
          <Col xs={12} sm={6} md={4} key={status}>
            <Card size="small">
              <Statistic
                title={`Run 状态：${status}`}
                value={n}
                prefix={
                  status === 'SUCCESS' ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                  status === 'FAILED'  ? <CloseCircleOutlined style={{ color: '#f5222d' }} /> :
                  status === 'RUNNING' ? <ClockCircleOutlined style={{ color: '#1890ff' }} /> :
                                         <ClockCircleOutlined style={{ color: '#999' }} />
                }
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 结果汇总表 */}
      <Card>
        <Spin spinning={loading}>
          {grouped.length === 0 ? (
            <Empty description="尚无模拟结果。请先在「新业务模拟方案」创建方案并执行引擎。" />
          ) : (
            <Table
              size="small"
              rowKey={(r: any) => `${r.scheme_code}|${r.run_id}|${r.date_offset}`}
              dataSource={grouped}
              columns={columns}
              scroll={{ x: 1280 }}
              pagination={{ pageSize: 20, showSizeChanger: true }}
            />
          )}
        </Spin>
      </Card>
    </div>
  )
}

export default SimResultTable

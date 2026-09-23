import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Select, Tag, Empty, Spin, Table, Progress, Statistic, Divider, Tooltip, Badge,
} from 'antd'
import {
  DashboardOutlined, ReloadOutlined, WarningOutlined, ArrowUpOutlined, ArrowDownOutlined,
  BankOutlined, RiseOutlined, FallOutlined, AlertOutlined, FundProjectionScreenOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import { reverseDashboardApi } from '../api'

const { Option } = Select

// 5 指标元数据：颜色、单位、上限/下限
const META: Record<string, { label: string; color: string; unit: string; desc: string }> = {
  ROE:        { label: 'ROE 净资产收益率',  color: '#722ed1', unit: '%',  desc: '≥ 11% (行业参考)' },
  CET1:       { label: 'CET1 核心一级',    color: '#1890ff', unit: '%',  desc: '≥ 8.5% (银保监)' },
  LCR:        { label: 'LCR 流动性覆盖',   color: '#52c41a', unit: '%',  desc: '≥ 100% (银保监)' },
  NSFR:       { label: 'NSFR 净稳定资金',  color: '#13c2c2', unit: '%',  desc: '≥ 100% (银保监)' },
  DELTA_EVE: { label: 'ΔEVE 利率风险',    color: '#eb2f96', unit: '亿', desc: '|Δ| ≤ 5% (内部)' },
}
const METRIC_KEYS = ['ROE', 'CET1', 'LCR', 'NSFR', 'DELTA_EVE']

// 节点大类配色
const CATEGORY_META: Record<string, { label: string; color: string }> = {
  ASSET:       { label: '资产',  color: '#1890ff' },
  LIABILITY:   { label: '负债',  color: '#fa8c16' },
  EQUITY:      { label: '权益',  color: '#722ed1' },
  OFF_BALANCE: { label: '表外',  color: '#13c2c2' },
  OTHER:       { label: '其他',  color: '#8c8c8c' },
}

// 风险等级颜色
function severityColor(s: string) {
  return s === 'critical' ? '#f5222d' : '#fa8c16'
}

const fmtMoney = (v: number) => {
  if (!v && v !== 0) return '-'
  const a = Math.abs(v)
  if (a >= 1e8) return (v / 1e8).toFixed(2) + ' 亿'
  if (a >= 1e4) return (v / 1e4).toFixed(2) + ' 万'
  return v.toFixed(2)
}

const ReverseDashboard: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [dates, setDates] = useState<any[]>([])

  const [schemeCode, setSchemeCode] = useState<string>('')
  const [runId, setRunId] = useState<number | undefined>(undefined)
  const [dateOffset, setDateOffset] = useState<number>(1)

  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [filterCat, setFilterCat] = useState<string | undefined>(undefined)
  const [metricView, setMetricView] = useState<string>('ROE')  // 热力图选中指标

  // 初始化：加载选项
  useEffect(() => {
    (async () => {
      try {
        const r = await reverseDashboardApi.options()
        setSchemes(r.schemes || [])
        const def = r.default || {}
        setSchemeCode(def.scheme_code || '')
        setRunId(def.run_id || undefined)
        setDateOffset(def.date_offset || 1)
      } catch (e) {
        console.error(e)
      }
    })()
  }, [])

  // 方案变化 → 加载 runs
  useEffect(() => {
    if (!schemeCode) return
    (async () => {
      const r = await reverseDashboardApi.runs(schemeCode)
      setRuns(r.items || [])
      // 如果当前 runId 不在新列表里，重置为最新 SUCCESS
      const success = (r.items || []).filter((x: any) => x.status === 'SUCCESS')
      const latest = success[0]
      if (!runId || !(r.items || []).some((x: any) => x.run_id === runId)) {
        setRunId(latest?.run_id)
      }
    })()
  }, [schemeCode])

  // run 变化 → 加载 dates
  useEffect(() => {
    if (!schemeCode || !runId) return
    (async () => {
      const r = await reverseDashboardApi.dates(schemeCode, runId)
      setDates(r.items || [])
    })()
  }, [schemeCode, runId])

  // 拉快照
  useEffect(() => {
    if (!schemeCode || !runId) return
    loadSnapshot()
    // eslint-disable-next-line
  }, [schemeCode, runId, dateOffset])

  const loadSnapshot = async () => {
    setLoading(true)
    try {
      const r = await reverseDashboardApi.snapshot({
        scheme_code: schemeCode,
        run_id: runId,
        date_offset: dateOffset,
      })
      setData(r)
    } catch (e: any) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  // 趋势图
  const trendOpt = useMemo(() => {
    if (!data?.trend) return {}
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, type: 'scroll' },
      grid: { left: 50, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: data.trend.months, axisLabel: { rotate: 0 } },
      yAxis: { type: 'value', name: '指标值 (%)' },
      series: METRIC_KEYS.map((mk) => ({
        name: META[mk].label,
        type: 'line',
        smooth: true,
        data: data.trend[mk],
        itemStyle: { color: META[mk].color },
        lineStyle: { width: 2.5 },
        emphasis: { focus: 'series' },
      })),
    }
  }, [data])

  // 大类分布饼图（按余额）
  const distOpt = useMemo(() => {
    if (!data?.category_distribution) return {}
    const cd = data.category_distribution
    const labels = ['ASSET', 'LIABILITY', 'EQUITY', 'OFF_BALANCE', 'OTHER']
    return {
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => `${CATEGORY_META[p.name]?.label || p.name}<br/>余额: ${fmtMoney(p.value)}<br/>占比: ${p.percent}%`,
      },
      legend: { bottom: 0, type: 'scroll' },
      series: [{
        type: 'pie', radius: ['45%', '70%'],
        data: labels.map((k) => ({
          name: k, value: cd.by_balance[k] || 0,
          itemStyle: { color: CATEGORY_META[k].color },
        })),
        label: { formatter: (p: any) => `${CATEGORY_META[p.name]?.label || p.name}\n${p.percent}%` },
      }],
    }
  }, [data])

  // 大类节点数柱状图
  const distBarOpt = useMemo(() => {
    if (!data?.category_distribution) return {}
    const cd = data.category_distribution
    const labels = ['ASSET', 'LIABILITY', 'EQUITY', 'OFF_BALANCE', 'OTHER']
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: labels.map((k) => CATEGORY_META[k]?.label || k) },
      yAxis: { type: 'value', name: '节点数' },
      series: [{
        type: 'bar', barWidth: '60%',
        data: labels.map((k) => ({
          value: cd.by_count[k] || 0,
          itemStyle: { color: CATEGORY_META[k].color },
        })),
        label: { show: true, position: 'top', formatter: '{c}' },
      }],
    }
  }, [data])

  // 节点指标热力图（按所选指标 + 当前 data_date）
  const heatOpt = useMemo(() => {
    if (!data?.node_matrix) return {}
    const nodes = filterCat
      ? data.node_matrix.filter((n: any) => n.category === filterCat)
      : data.node_matrix
    const cats = ['ASSET', 'LIABILITY', 'EQUITY', 'OFF_BALANCE', 'OTHER']
    const yLabels = cats.map((c) => `${CATEGORY_META[c].label} (${c})`)
    // 数据 = [x_index, y_index, value]
    const heatData: any[] = []
    nodes.forEach((n: any, i: number) => {
      const v = n.metric_values?.[metricView]
      heatData.push([i, cats.indexOf(n.category), v ?? null])
    })
    const xLabels = nodes.map((n: any) => `${n.node_code} ${n.node_name?.slice(0, 8) || ''}`)

    return {
      tooltip: {
        position: 'top',
        formatter: (p: any) => {
          const n = nodes[p.data[0]]
          if (p.data[2] == null) return `${n.node_code}<br/>${META[metricView].label}: 无数据`
          return `${n.node_code} · ${n.node_name}<br/>${META[metricView].label}: <b>${p.data[2]}</b> ${META[metricView].unit}`
        },
      },
      grid: { left: 90, right: 10, top: 30, bottom: 100 },
      xAxis: { type: 'category', data: xLabels, axisLabel: { rotate: 60, fontSize: 10 }, splitArea: { show: true } },
      yAxis: { type: 'category', data: yLabels, splitArea: { show: true } },
      visualMap: {
        min: metricView === 'DELTA_EVE' ? -5 : 0,
        max: metricView === 'DELTA_EVE' ? 0 : 200,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: { color: ['#f5222d', '#fa8c16', '#52c41a'] },
      },
      series: [{
        name: META[metricView].label, type: 'heatmap', data: heatData,
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
      }],
    }
  }, [data, filterCat, metricView])

  if (!data && loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin tip="加载驾驶舱…" /></div>
  }
  if (!data) {
    return <Empty description="暂无数据" />
  }

  const k = data.kpi
  const a = data.scheme_code
  const r = data.run_id
  const m = data.date_offset

  return (
    <div>
      <div className="page-title">
        <span className="page-title-icon" />
        组合反算 · 结果驾驶舱
        <Tag color="purple" style={{ marginLeft: 12 }}>默认方案 {a} · Run#{r} · M{m}</Tag>
      </div>

      {/* 筛选条 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <span style={{ marginRight: 8 }}>组合方案：</span>
            <Select value={schemeCode} onChange={setSchemeCode} style={{ width: 200 }} placeholder="选择方案">
              {schemes.map((s) => (
                <Option key={s.scheme_code} value={s.scheme_code}>
                  {s.scheme_code} · {s.scheme_name}
                </Option>
              ))}
            </Select>
          </Col>
          <Col>
            <span style={{ marginRight: 8 }}>运行记录：</span>
            <Select
              value={runId}
              onChange={(v) => setRunId(v)}
              style={{ width: 180 }}
              placeholder="选择 Run"
              disabled={!runs.length}
            >
              {runs.map((r) => (
                <Option key={r.run_id} value={r.run_id} disabled={r.status !== 'SUCCESS'}>
                  #{r.run_id} · {r.status} · {r.row_count} 行
                </Option>
              ))}
            </Select>
          </Col>
          <Col>
            <span style={{ marginRight: 8 }}>预测月份：</span>
            <Select
              value={dateOffset}
              onChange={setDateOffset}
              style={{ width: 140 }}
              placeholder="M1~M24"
              disabled={!dates.length}
            >
              {dates.map((d) => (
                <Option key={d.date_offset} value={d.date_offset}>
                  M{d.date_offset} · {d.data_date}
                </Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Tag color="blue">数据日期：{data.data_date}</Tag>
            <Tag color="cyan">账户册方案：{data.coa_scheme_code}</Tag>
            <Tag color="geekblue">基期：{data.base_data_date}</Tag>
            <Tag color="purple">预测期：{data.horizon_months} 月</Tag>
          </Col>
          <Col flex="auto" style={{ textAlign: 'right' }}>
            <ReloadOutlined onClick={loadSnapshot} style={{ cursor: 'pointer', fontSize: 18, color: '#667eea' }} />
          </Col>
        </Row>
      </Card>

      {/* KPI 区 */}
      <Row gutter={[12, 12]}>
        <Col xs={12} sm={8} md={4}>
          <Card className="kpi-card" size="small">
            <Statistic title="账户册节点" value={k.total_nodes} suffix="个"
              prefix={<BankOutlined style={{ color: '#667eea' }} />} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card className="kpi-card" size="small">
            <Statistic title="已挂指标" value={k.with_metrics} suffix={`/ ${k.total_nodes}`}
              prefix={<DashboardOutlined style={{ color: '#764ba2' }} />} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card className="kpi-card" size="small">
            <Statistic title="资产余额" value={fmtMoney(k.asset_total)}
              valueStyle={{ color: '#1890ff' }}
              prefix={<RiseOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card className="kpi-card" size="small">
            <Statistic title="负债余额" value={fmtMoney(k.liability_total)}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<FallOutlined />} />
          </Card>
        </Col>
        {METRIC_KEYS.map((mk) => {
          const v = k.metric_avg[mk]
          const meta = META[mk]
          return (
            <Col xs={12} sm={8} md={4} key={mk}>
              <Card className="kpi-card" size="small">
                <Statistic
                  title={<Tooltip title={meta.desc}>{meta.label}</Tooltip>}
                  value={v == null ? '-' : v}
                  suffix={meta.unit}
                  precision={2}
                  valueStyle={{ color: meta.color, fontSize: 22 }}
                  prefix={
                    v != null && mk !== 'DELTA_EVE' && v < (data.thresholds?.[mk]?.min || 0)
                      ? <ArrowDownOutlined style={{ color: '#f5222d' }} />
                      : (mk === 'DELTA_EVE' && v != null && Math.abs(v) > (data.thresholds?.DELTA_EVE?.max_abs || 0)
                          ? <ArrowUpOutlined style={{ color: '#f5222d' }} />
                          : null)
                  }
                />
              </Card>
            </Col>
          )
        })}
      </Row>

      {/* 趋势 + 大类分布 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <Card
            title={<><FundProjectionScreenOutlined /> 5 指标 24 月趋势</>}
            extra={<Tag color="purple">平均口径</Tag>}
          >
            <ReactECharts option={trendOpt} style={{ height: 340 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={<><DashboardOutlined /> 大类分布</>}>
            <ReactECharts option={distOpt} style={{ height: 200 }} />
            <Divider style={{ margin: '8px 0' }} />
            <ReactECharts option={distBarOpt} style={{ height: 130 }} />
          </Card>
        </Col>
      </Row>

      {/* 节点指标热力图 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title={
              <>
                <DashboardOutlined /> 节点 × 指标 热力图
                <Select
                  size="small" value={metricView}
                  onChange={setMetricView}
                  style={{ width: 160, marginLeft: 12 }}
                >
                  {METRIC_KEYS.map((mk) => (
                    <Option key={mk} value={mk}>{META[mk].label}</Option>
                  ))}
                </Select>
                <Select
                  size="small" allowClear placeholder="按大类过滤"
                  value={filterCat} onChange={setFilterCat}
                  style={{ width: 140, marginLeft: 8 }}
                >
                  {Object.entries(CATEGORY_META).map(([k, v]) => (
                    <Option key={k} value={k}>{v.label}</Option>
                  ))}
                </Select>
              </>
            }
          >
            <ReactECharts option={heatOpt} style={{ height: 380 }} />
          </Card>
        </Col>
      </Row>

      {/* Top 10 + 风险预警 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={<><RiseOutlined /> Top 10 节点（按余额）</>}>
            <Table
              size="small"
              dataSource={data.top_nodes.map((n: any, i: number) => ({ ...n, key: i }))}
              pagination={false}
              columns={[
                { title: '#', width: 40, render: (_: any, _r: any, i: number) => i + 1 },
                {
                  title: '节点', dataIndex: 'node_code', width: 100,
                  render: (v: string, r: any) => (
                    <Tooltip title={r.node_name}>
                      <Tag color={CATEGORY_META[r.category]?.color}>{v}</Tag>
                    </Tooltip>
                  ),
                },
                {
                  title: '余额', dataIndex: 'current_balance', width: 90,
                  render: (v: number) => fmtMoney(v),
                },
                {
                  title: '利率', dataIndex: 'weighted_rate', width: 70,
                  render: (v: number) => (v * 100).toFixed(2) + '%',
                },
                ...METRIC_KEYS.map((mk) => ({
                  title: <span style={{ fontSize: 11 }}>{META[mk].label.split(' ')[0]}</span>,
                  dataIndex: ['metric_values', mk],
                  width: 60,
                  render: (v: any) => v == null
                    ? <span style={{ color: '#ccc' }}>-</span>
                    : <span style={{ color: META[mk].color }}>{Number(v).toFixed(2)}</span>,
                })),
              ]}
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={
              <>
                <AlertOutlined /> 风险预警
                <Badge
                  count={data.risk_alert_total}
                  offset={[12, -2]}
                  style={{ backgroundColor: data.risk_alert_total > 0 ? '#f5222d' : '#52c41a' }}
                />
              </>
            }
          >
            {data.risk_alert_total === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="所有节点指标均符合阈值" />
            ) : (
              <Table
                size="small"
                dataSource={data.risk_alerts.map((a: any, i: number) => ({ ...a, key: i }))}
                pagination={{ pageSize: 8, size: 'small' }}
                columns={[
                  {
                    title: '节点', width: 110,
                    render: (_: any, r: any) => (
                      <Tooltip title={r.node_name}>
                        <Tag color={CATEGORY_META[r.category]?.color}>{r.node_code}</Tag>
                      </Tooltip>
                    ),
                  },
                  {
                    title: '预警', dataIndex: 'alerts',
                    render: (alerts: any[]) => (
                      <div>
                        {alerts.map((a, i) => (
                          <Tag key={i} color={severityColor(a.severity)}
                            icon={a.severity === 'critical' ? <WarningOutlined /> : <AlertOutlined />}
                            style={{ marginBottom: 2 }}
                          >
                            {a.msg}
                          </Tag>
                        ))}
                      </div>
                    ),
                  },
                  {
                    title: '余额', width: 80,
                    render: (_: any, r: any) => fmtMoney(r.current_balance),
                  },
                ]}
              />
            )}
          </Card>
        </Col>
      </Row>

      <Divider />
      <div style={{ color: '#999', fontSize: 12, textAlign: 'center' }}>
        数据来源：prcp_reverse_scheme / prcp_reverse_run / prcp_data_reverse / prcp_metric_coefficient / prcp_coa_node
        <Progress percent={100} showInfo={false} strokeColor="#667eea" size="small" style={{ maxWidth: 200, margin: '8px auto' }} />
      </div>
    </div>
  )
}

export default ReverseDashboard
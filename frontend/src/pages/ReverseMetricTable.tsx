import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Select, Button, Table, Space, Tag,
  message, Spin, Empty, Tooltip, Statistic, Alert, Badge,
} from 'antd'
import {
  ReloadOutlined, DownloadOutlined, FundProjectionScreenOutlined,
  CheckCircleOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { metricCoefficientApi, dataReverseApi } from '../api'
import { DictTag } from '../components'

interface RevRow {
  coa_node_id: number
  node_code: string
  node_name: string
  node_level: number
  category: string
  metric_values: Record<string, number>
  metric_ids: Record<string, string>
}

// 5 个核心指标（顺序固定，列头顺序）
const DEFAULT_METRICS = ['ROE', 'CET1', 'LCR', 'NSFR', 'DELTA_EVE']
const METRIC_META: Record<string, { label: string; color: string; description: string }> = {
  ROE:       { label: 'ROE 净资产收益率',           color: '#1890ff', description: 'Return on Equity' },
  CET1:      { label: '核心一级资本充足率',         color: '#52c41a', description: 'Common Equity Tier 1 Ratio' },
  LCR:       { label: '流动性覆盖率（LCR）',        color: '#13c2c2', description: 'Liquidity Coverage Ratio' },
  NSFR:      { label: '净稳定资金比例（NSFR）',     color: '#722ed1', description: 'Net Stable Funding Ratio' },
  DELTA_EVE: { label: '△EVE 利率风险经济价值变动',   color: '#eb2f96', description: 'Interest Rate Risk in Banking Book (EVE)' },
}

const ReverseMetricTable: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [schemes, setSchemes] = useState<any[]>([])
  const [activeScheme, setActiveScheme] = useState<string | null>(null)
  const [runs, setRuns] = useState<any[]>([])
  const [activeRun, setActiveRun] = useState<number | null>(null)
  const [monthsList, setMonthsList] = useState<any[]>([])
  const [activeMonth, setActiveMonth] = useState<number>(1)

  const [tableData, setTableData] = useState<{
    rows: RevRow[]
    data_date: string
    coa_scheme_code: string
    coa_scheme_name: string
    total_nodes: number
    total_with_metrics: number
  } | null>(null)

  // 1. 加载反算方案列表
  const loadSchemes = async () => {
    try {
      const r = await dataReverseApi.schemes()
      setSchemes(r.items || [])
      if (r.items?.length && !activeScheme) {
        setActiveScheme(r.items[0].scheme_code)
      }
    } catch (e) { message.error('反算方案加载失败') }
  }
  useEffect(() => { loadSchemes() }, [])

  // 2. 加载 runs
  const loadRuns = async () => {
    if (!activeScheme) return
    try {
      const r = await dataReverseApi.runs(activeScheme)
      setRuns(r.items || [])
      const success = (r.items || []).filter((x: any) => x.status === 'SUCCESS')
      if (success.length) setActiveRun(success[0].id)
    } catch (e) { message.error('Runs 加载失败') }
  }
  useEffect(() => { loadRuns() }, [activeScheme])

  // 3. 加载月份列表
  const loadMonths = async () => {
    if (!activeScheme) return
    try {
      const r = await dataReverseApi.dates(activeScheme, activeRun || undefined)
      setMonthsList(r.items || [])
      if (r.items?.length && !r.items.find((m: any) => m.date_offset === activeMonth)) {
        setActiveMonth(r.items[0].date_offset)
      }
    } catch (e) { message.error('月份列表加载失败') }
  }
  useEffect(() => { loadMonths() }, [activeScheme, activeRun])

  // 4. 加载指标结果表
  const loadTable = async () => {
    if (!activeScheme) return
    setLoading(true)
    try {
      const r = await metricCoefficientApi.reverseTable({
        scheme_code: activeScheme,
        run_id: activeRun || undefined,
        date_offset: activeMonth,
      })
      setTableData({
        rows: r.rows || [],
        data_date: r.data_date,
        coa_scheme_code: r.coa_scheme_code,
        coa_scheme_name: r.coa_scheme_name,
        total_nodes: r.total_nodes,
        total_with_metrics: r.total_with_metrics,
      })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '指标结果表加载失败')
      setTableData(null)
    } finally { setLoading(false) }
  }
  useEffect(() => { loadTable() }, [activeScheme, activeRun, activeMonth])

  // 表格列
  const columns = useMemo<ColumnsType<RevRow>>(() => {
    const baseCols: ColumnsType<RevRow> = [
      {
        title: '账户册编码', dataIndex: 'node_code', width: 130, fixed: 'left' as const,
        render: (c: string, r: RevRow) => (
          <Tooltip title={`层级 ${r.node_level}`}>
            <code style={{
              color: r.node_level === 1 ? '#1d39c4' : r.node_level === 2 ? '#722ed1' : '#262626',
              fontSize: r.node_level === 1 ? 13 : 12,
              fontWeight: r.node_level < 3 ? 700 : 500,
            }}>{c}</code>
          </Tooltip>
        ),
      },
      {
        title: '账户册名称', dataIndex: 'node_name', width: 200, fixed: 'left' as const,
        render: (n: string, r: RevRow) => (
          <Tooltip title={n} placement="topLeft">
            <span style={{
              fontSize: r.node_level === 1 ? 14 : 13,
              fontWeight: r.node_level < 3 ? 700 : 400,
              color: r.node_level === 1 ? '#1d39c4' : r.node_level === 2 ? '#722ed1' : '#262626',
              display: 'inline-block', maxWidth: 185,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>{n}</span>
          </Tooltip>
        ),
      },
      {
        title: '大类', dataIndex: 'category', width: 80, fixed: 'left' as const,
        render: (v: string) => <DictTag dictType="PRCP_COA_CATEGORY" value={v} />,
      },
    ]

    const metricCols: ColumnsType<RevRow> = DEFAULT_METRICS.map((mk) => {
      const meta = METRIC_META[mk]
      return {
        title: (
          <Tooltip title={meta.description}>
            <span style={{ color: meta.color, fontWeight: 600 }}>{meta.label}</span>
          </Tooltip>
        ),
        dataIndex: ['metric_values', mk],
        width: 130,
        align: 'right' as const,
        render: (v: number | undefined, r: RevRow) => {
          if (v === undefined || v === null) {
            return (
              <Tooltip title={r.metric_ids?.[mk] ? '已编辑但未取值' : '该节点无指标计量系数记录'}>
                <span style={{ color: '#ccc', fontFamily: 'monospace' }}>-</span>
              </Tooltip>
            )
          }
          const color = mk === 'DELTA_EVE' ? (v < 0 ? '#cf1322' : '#389e0d') : meta.color
          return (
            <Tooltip title={`ID: ${r.metric_ids?.[mk] || '-'}\n值: ${v.toFixed(4)}${(mk !== 'DELTA_EVE') ? '%' : ''}`}>
              <span style={{ color, fontFamily: 'monospace', fontWeight: 600 }}>
                {v.toFixed(4)}{mk === 'DELTA_EVE' ? '' : '%'}
              </span>
            </Tooltip>
          )
        },
      }
    })

    return [...baseCols, ...metricCols]
  }, [])

  // 5 个指标列合计（行汇总）
  const totals = useMemo(() => {
    if (!tableData) return { count: 0 }
    const sum: Record<string, number> = {}
    const cnt: Record<string, number> = {}
    for (const mk of DEFAULT_METRICS) { sum[mk] = 0; cnt[mk] = 0 }
    tableData.rows.forEach((r) => {
      for (const mk of DEFAULT_METRICS) {
        const v = r.metric_values?.[mk]
        if (typeof v === 'number') { sum[mk] += v; cnt[mk] += 1 }
      }
    })
    return { sum, cnt, count: tableData.rows.length }
  }, [tableData])

  // 导出 CSV（无依赖、纯前端）
  const onExport = () => {
    if (!tableData) { message.warning('暂无数据'); return }
    const headers = ['账户册编码', '账户册名称', '大类', ...DEFAULT_METRICS.map((m) => METRIC_META[m].label), '数据日期', '反算方案', 'Run']
    const lines = [headers.join('\t')]
    tableData.rows.forEach((r) => {
      const line = [
        r.node_code, r.node_name, r.category,
        ...DEFAULT_METRICS.map((m) => r.metric_values?.[m] ?? ''),
        tableData.data_date, activeScheme, activeRun,
      ]
      lines.push(line.join('\t'))
    })
    const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `反算指标结果_${activeScheme}_M${activeMonth}_${tableData.data_date}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
    message.success('已导出 CSV')
  }

  return (
    <Spin spinning={loading}>
      <div style={{ padding: 16 }}>
        <Card
          title={
            <Space>
              <FundProjectionScreenOutlined style={{ color: '#722ed1' }} />
              <span>反算指标结果表</span>
              <Tag color="purple">数据维护 · 11</Tag>
            </Space>
          }
          extra={
            <Space>
              <Button icon={<DownloadOutlined />} onClick={onExport}>导出 CSV</Button>
              <Button icon={<ReloadOutlined />} onClick={loadTable}>刷新</Button>
            </Space>
          }
        >
          {/* 顶部查询条件（参考 9 号） */}
          <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }} bordered={false}>
            <Row gutter={16} align="middle">
              <Col>
                <span style={{ marginRight: 8 }}>反算方案：</span>
                <Select
                  value={activeScheme}
                  onChange={setActiveScheme}
                  style={{ width: 240 }}
                  placeholder="选择反算方案"
                  options={schemes.map((s: any) => ({
                    value: s.scheme_code,
                    label: `${s.scheme_code} · ${s.scheme_name}`,
                  }))}
                />
              </Col>
              <Col>
                <span style={{ marginRight: 8 }}>运行记录：</span>
                <Select
                  value={activeRun}
                  onChange={setActiveRun}
                  style={{ width: 280 }}
                  placeholder="选择 Run"
                  options={runs.map((r: any) => ({
                    value: r.id,
                    label: `Run#${r.id} · ${r.status} · ${r.start_at?.slice(0, 16) || ''}`,
                    disabled: r.status !== 'SUCCESS',
                  }))}
                />
              </Col>
              <Col>
                <span style={{ marginRight: 8 }}>预测月份：</span>
                <Select
                  value={activeMonth}
                  onChange={setActiveMonth}
                  style={{ width: 200 }}
                  placeholder="选择月份"
                  options={monthsList.map((m: any) => ({
                    value: m.date_offset,
                    label: `M${m.date_offset} · ${m.data_date}`,
                  }))}
                />
              </Col>
            </Row>
          </Card>

          {/* 数据上下文信息条 */}
          {tableData && (
            <Alert
              style={{ marginBottom: 16 }}
              type="info"
              showIcon
              message={
                <Space wrap>
                  <span><b>数据日期：</b><Tag color="blue">{tableData.data_date}</Tag></span>
                  <span><b>账户册方案：</b><Tag color="geekblue">{tableData.coa_scheme_code || '-'}</Tag>{tableData.coa_scheme_name}</span>
                  <span><b>覆盖节点：</b>{tableData.total_nodes} 个</span>
                  <span><b>已挂指标：</b>
                    <Badge
                      count={tableData.total_with_metrics}
                      showZero
                      style={{ backgroundColor: tableData.total_with_metrics > 0 ? '#52c41a' : '#d9d9d9' }}
                    />
                  </span>
                </Space>
              }
            />
          )}

          {/* 5 个指标的小汇总 */}
          {tableData && (
            <Row gutter={12} style={{ marginBottom: 16 }}>
              {DEFAULT_METRICS.map((mk) => {
                const m = METRIC_META[mk]
                const c = totals.cnt[mk] || 0
                const avg = c > 0 ? (totals.sum[mk] / c) : 0
                return (
                  <Col span={4} key={mk}>
                    <Card size="small" bodyStyle={{ padding: 12 }}>
                      <Statistic
                        title={<span style={{ color: m.color, fontWeight: 600 }}>{m.label}</span>}
                        value={c > 0 ? avg.toFixed(4) : '—'}
                        suffix={c > 0 && mk !== 'DELTA_EVE' ? '%' : ''}
                        valueStyle={{ color: m.color, fontSize: 18 }}
                      />
                      <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                        {c > 0 ? `覆盖 ${c}/${tableData.total_nodes} 个节点 · 平均` : '暂无数据'}
                      </div>
                    </Card>
                  </Col>
                )
              })}
            </Row>
          )}

          {/* 主表格 */}
          <Table<RevRow>
            rowKey="coa_node_id"
            columns={columns}
            dataSource={tableData?.rows || []}
            loading={loading}
            size="middle"
            bordered
            scroll={{ x: 1200 }}
            pagination={false}
            summary={() => {
              if (!tableData) return null
              return (
                <Table.Summary fixed>
                  <Table.Summary.Row style={{ background: '#fafafa', fontWeight: 700 }}>
                    <Table.Summary.Cell index={0} colSpan={3}>
                      <Space>
                        <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        <span>合计 / 平均</span>
                      </Space>
                    </Table.Summary.Cell>
                    {DEFAULT_METRICS.map((mk, i) => {
                      const c = totals.cnt[mk] || 0
                      const avg = c > 0 ? (totals.sum[mk] / c) : 0
                      const m = METRIC_META[mk]
                      return (
                        <Table.Summary.Cell key={mk} index={3 + i} align="right">
                          {c > 0 ? (
                            <Tooltip title={`${c} 个节点平均`}>
                              <span style={{ color: m.color, fontFamily: 'monospace' }}>
                                {avg.toFixed(4)}{mk === 'DELTA_EVE' ? '' : '%'}
                              </span>
                            </Tooltip>
                          ) : (
                            <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                          )}
                        </Table.Summary.Cell>
                      )
                    })}
                  </Table.Summary.Row>
                </Table.Summary>
              )
            }}
            locale={{
              emptyText: (
                <Empty description={
                  !activeScheme ? '请先选择反算方案' :
                  !tableData ? '暂无数据' :
                  '该预测月份下没有节点数据'
                } />
              ),
            }}
          />
        </Card>
      </div>
    </Spin>
  )
}

export default ReverseMetricTable
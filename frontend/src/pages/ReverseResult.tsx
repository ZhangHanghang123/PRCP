import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Tree as AntTree, Select, Space, Button, Tag, Empty, Spin,
  Row, Col, Tooltip, Statistic, message,
} from 'antd'
import {
  ReloadOutlined, DownloadOutlined, FundProjectionScreenOutlined,
  DatabaseOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import { dataReverseApi } from '../api'
import { BUCKETS } from '../constants/buckets'

// 度量列
const EXTRAS = [
  { key: 'current_balance', name: '当前余额',  width: 95, isPercent: false, precision: 2 },
  { key: 'avg_balance',     name: '平均余额',  width: 95, isPercent: false, precision: 2 },
  { key: 'weighted_rate',   name: '加权利率',  width: 70, isPercent: true,  precision: 4 },
  { key: 'interest_amount', name: '利息收支',  width: 80, isPercent: false, precision: 2 },
  { key: 'risk_weight',     name: '风险权重',  width: 80, isPercent: true,  precision: 4 },
]

const { DirectoryTree } = AntTree

const ReverseResult: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [activeScheme, setActiveScheme] = useState<string | null>(null)
  const [runs, setRuns] = useState<any[]>([])
  const [activeRun, setActiveRun] = useState<number | null>(null)
  const [monthsList, setMonthsList] = useState<any[]>([])
  const [activeMonth, setActiveMonth] = useState<number>(1)
  const [matrix, setMatrix] = useState<Record<number, Record<string, any>>>({})
  const [matrixNodes, setMatrixNodes] = useState<any[]>([])
  const [categoriesAgg, setCategoriesAgg] = useState<Record<string, Record<string, any>>>({})
  const [loading, setLoading] = useState(false)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])

  // 1. 加载有反算结果的方案
  const loadSchemes = async () => {
    const r = await dataReverseApi.schemes()
    setSchemes(r.items || [])
    if (r.items?.length && !activeScheme) {
      setActiveScheme(r.items[0].scheme_code)
    }
  }
  useEffect(() => { loadSchemes() }, [])

  // 2. 加载方案的 runs
  const loadRuns = async () => {
    if (!activeScheme) return
    const r = await dataReverseApi.runs(activeScheme)
    setRuns(r.items || [])
    const success = (r.items || []).filter((run: any) => run.status === 'SUCCESS')
    if (success.length) setActiveRun(success[0].id)
  }
  useEffect(() => { loadRuns() }, [activeScheme])

  // 3. 加载月份列表
  const loadMonths = async () => {
    if (!activeScheme) return
    const r = await dataReverseApi.dates(activeScheme, activeRun || undefined)
    setMonthsList(r.items || [])
    if (r.items?.length && !r.items.find((m: any) => m.date_offset === activeMonth)) {
      setActiveMonth(r.items[0].date_offset)
    }
  }
  useEffect(() => { loadMonths() }, [activeScheme, activeRun])

  // 4. 加载矩阵
  const loadMatrix = async () => {
    if (!activeScheme) return
    setLoading(true)
    try {
      const r = await dataReverseApi.bySchemeMatrix({
        scheme_code: activeScheme,
        run_id: activeRun || undefined,
        date_offset: activeMonth,
        offset_unit: 'M',
      })
      setMatrix(r.matrix || {})
      setMatrixNodes(r.nodes || [])
      setCategoriesAgg(r.categories || {})

      // 默认展开 L1
      const l1Keys = (r.nodes || []).filter((n: any) => n.node_level === 1).map((n: any) => String(n.coa_node_id))
      setExpandedKeys(l1Keys)
    } finally { setLoading(false) }
  }
  useEffect(() => { loadMatrix() }, [activeScheme, activeRun, activeMonth])

  // 导出
  const onExport = async () => {
    if (!activeScheme) { message.warning('请先选择反算方案'); return }
    try {
      const url = dataReverseApi.exportXlsxUrl(activeScheme, activeRun || undefined)
      const token = localStorage.getItem('prcp_token') || ''
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `prcp_reverse_${activeScheme}_run${activeRun || 'latest'}.xlsx`
      a.click()
      URL.revokeObjectURL(a.href)
      message.success('导出成功')
    } catch (e: any) {
      message.error(`导出失败：${e.message}`)
    }
  }

  // 树形结构构建（按 path 字典序，保证父在前）
  const treeData = useMemo(() => {
    const byParent: Record<number, any[]> = {}
    matrixNodes.forEach((n) => {
      const key = n.parent_id || 0
      if (!byParent[key]) byParent[key] = []
      byParent[key].push(n)
    })
    Object.values(byParent).forEach((arr) => arr.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)))

    const build = (parentId: number): any[] => {
      const children = byParent[parentId] || []
      return children.map((c) => {
        const hasData = !!matrix[c.coa_node_id]
        return {
          key: String(c.coa_node_id),
          title: (
            <span>
              <Tag color={c.node_level === 1 ? 'blue' : c.node_level === 2 ? 'cyan' : 'default'} style={{ marginRight: 4 }}>
                L{c.node_level}
              </Tag>
              <span style={{ fontWeight: c.node_level === 1 ? 600 : 400 }}>
                {c.node_code} {c.node_name}
              </span>
              {hasData && <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>
                ¥{(matrix[c.coa_node_id].current_balance / 1).toFixed(2)} 亿
              </span>}
            </span>
          ),
          children: build(c.coa_node_id),
        }
      })
    }
    return build(0)
  }, [matrixNodes, matrix])

  // 大类汇总行
  const categoryRows = useMemo(() => {
    return Object.entries(categoriesAgg).map(([cat, m]: any) => ({
      key: cat, category: cat,
      current_balance: m.current_balance || 0,
      avg_balance: m.avg_balance || 0,
      weighted_rate: m.weighted_rate || 0,
      risk_weight: m.risk_weight || 0,
    }))
  }, [categoriesAgg])

  const currentRun = runs.find((r: any) => r.id === activeRun)
  const currentMonth = monthsList.find((m: any) => m.date_offset === activeMonth)

  if (!schemes.length) {
    return (
      <div>
        <div className="page-title">
          <span className="page-title-icon" />
          <span>反算结果查询</span>
        </div>
        <Empty description="暂无反算结果，请先在「组合反算」中运行一次反算" />
      </div>
    )
  }

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>
          数据维护 · 9. 反算结果查询
          <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal', marginLeft: 8 }}>
            基于 prcp_data_reverse（基础数据表结构 + 反算方案编码）
          </span>
        </span>
      </div>

      {/* 顶部筛选条 */}
      <Card bordered={false} style={{ marginBottom: 16 }} size="small">
        <Row gutter={16} align="middle">
          <Col>
            <span style={{ marginRight: 8 }}>反算方案：</span>
            <Select
              value={activeScheme}
              onChange={setActiveScheme}
              style={{ width: 220 }}
              options={schemes.map((s) => ({
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
              options={monthsList.map((m: any) => ({
                value: m.date_offset,
                label: `M${m.date_offset} · ${m.data_date}`,
              }))}
            />
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadMatrix}>刷新</Button>
              <Button icon={<DownloadOutlined />} onClick={onExport}>导出 Excel</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* KPI 概览 */}
      {currentRun && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card bordered={false} size="small">
              <Statistic
                title="Run ID"
                value={`#${currentRun.id}`}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card bordered={false} size="small">
              <Statistic
                title="预测状态"
                value={currentRun.status}
                valueStyle={{ color: currentRun.status === 'SUCCESS' ? '#52c41a' : '#f5222d' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card bordered={false} size="small">
              <Statistic
                title="数据行数"
                value={currentRun.row_count || 0}
                suffix="行"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card bordered={false} size="small">
              <Statistic
                title="当前月份"
                value={currentMonth ? `M${currentMonth.date_offset} · ${currentMonth.data_date}` : '-'}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主内容：左侧账户册树 + 右侧矩阵 */}
      <Row gutter={16}>
        <Col span={6}>
          <Card
            title={<span><FundProjectionScreenOutlined /> 账户册层级</span>}
            size="small"
            bordered={false}
            bodyStyle={{ padding: 8, maxHeight: 700, overflowY: 'auto' }}
          >
            <DirectoryTree
              treeData={treeData}
              expandedKeys={expandedKeys}
              onExpand={(keys) => setExpandedKeys(keys as React.Key[])}
              showLine
              blockNode
            />
          </Card>
        </Col>
        <Col span={18}>
          <Card
            title={<span>数据矩阵（M{activeMonth} 预测值）</span>}
            size="small"
            bordered={false}
            bodyStyle={{ padding: 8, overflowX: 'auto' }}
          >
            {categoryRows.length > 0 && (
              <div style={{ marginBottom: 12, padding: 8, background: '#fafafa', borderRadius: 4 }}>
                <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>大类汇总</div>
                <Space size="middle" wrap>
                  {categoryRows.map((row) => (
                    <Tooltip key={row.key} title="当前余额">
                      <Tag color={row.category === '资产' ? 'blue' : row.category === '负债' ? 'orange' : 'green'}>
                        {row.category}: ¥{row.current_balance.toFixed(2)} 亿
                      </Tag>
                    </Tooltip>
                  ))}
                </Space>
              </div>
            )}

            {/* 矩阵表格（横向 13+13+5 列） */}
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: '#f5f5f5' }}>
                  <th style={{ ...thStyle, width: 80 }}>编码</th>
                  <th style={{ ...thStyle, width: 200 }}>账户册名称</th>
                  <th style={{ ...thStyle, width: 50 }}>层级</th>
                  {BUCKETS.slice(0, 8).map((b) => (
                    <th key={`o-${b.key}`} style={{ ...thStyle, width: b.width }} colSpan={1}>
                      原<b>{b.name}</b>
                    </th>
                  ))}
                  {BUCKETS.slice(8).map((b) => (
                    <th key={`o-${b.key}`} style={{ ...thStyle, width: b.width }}>
                      原<b>{b.name}</b>
                    </th>
                  ))}
                  {BUCKETS.map((b) => (
                    <th key={`r-${b.key}`} style={{ ...thStyle, width: b.width }}>
                      余<b>{b.name}</b>
                    </th>
                  ))}
                  {EXTRAS.map((e) => (
                    <th key={e.key} style={{ ...thStyle, width: e.width }}>{e.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrixNodes.filter((n) => n.node_level >= 1 && n.node_level <= 4).map((n: any) => {
                  const cell = matrix[n.coa_node_id]
                  const indent = '　'.repeat(Math.max((n.node_level || 1) - 1, 0))
                  return (
                    <tr
                      key={n.coa_node_id}
                      style={{
                        background: n.node_level === 1 ? '#f0f5fa' : n.node_level === 2 ? '#f7fafd' : '#fff',
                      }}
                    >
                      <td style={{ ...tdStyle, fontWeight: n.node_level === 1 ? 600 : 400 }}>
                        {n.node_code}
                      </td>
                      <td style={{ ...tdStyle, fontWeight: n.node_level === 1 ? 600 : 400 }}>
                        {indent}{n.node_name}
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'center' }}>
                        <Tag color={n.node_level === 1 ? 'blue' : 'default'} style={{ margin: 0 }}>
                          L{n.node_level}
                        </Tag>
                      </td>
                      {BUCKETS.map((b) => {
                        const v = cell ? cell[`orig_${b.key}`] : 0
                        return (
                          <td key={`o-${b.key}`} style={{ ...tdStyle, textAlign: 'right' }}>
                            {v ? formatNum(v) : '—'}
                          </td>
                        )
                      })}
                      {BUCKETS.map((b) => {
                        const v = cell ? cell[`rem_${b.key}`] : 0
                        return (
                          <td key={`r-${b.key}`} style={{ ...tdStyle, textAlign: 'right' }}>
                            {v ? formatNum(v) : '—'}
                          </td>
                        )
                      })}
                      {EXTRAS.map((e) => {
                        const v = cell ? cell[e.key] : 0
                        const display = e.isPercent
                          ? v ? `${(v * 100).toFixed(e.precision)}%` : '—'
                          : v ? formatNum(v, e.precision) : '—'
                        return <td key={e.key} style={{ ...tdStyle, textAlign: 'right' }}>{display}</td>
                      })}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </Card>
        </Col>
      </Row>
    </Spin>
  )
}

const thStyle: React.CSSProperties = {
  border: '1px solid #e8e8e8',
  padding: '6px 4px',
  textAlign: 'center',
  whiteSpace: 'nowrap',
  fontWeight: 600,
}

const tdStyle: React.CSSProperties = {
  border: '1px solid #f0f0f0',
  padding: '4px 6px',
  whiteSpace: 'nowrap',
}

function formatNum(v: number, precision: number = 2): string {
  if (Math.abs(v) >= 10000) return (v / 10000).toFixed(precision) + '万'
  return v.toFixed(precision)
}

export default ReverseResult
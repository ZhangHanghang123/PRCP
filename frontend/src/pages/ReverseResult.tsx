import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Tabs, Select, Space, Button, Table,
  message, Spin, Empty, Row, Col,
  Tooltip, Badge,
} from 'antd'
import {
  ReloadOutlined, DownloadOutlined, BankOutlined,
  FundProjectionScreenOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { dataReverseApi } from '../api'
import { BUCKETS } from '../constants/buckets'
import { DictTag } from '../components'

// 度量列（反算结果无 ASF/HQLA，仅保留余额/利率/风险）
const EXTRAS = [
  { key: 'current_balance', name: '当前余额',  width: 95, isPercent: false, precision: 2 },
  { key: 'avg_balance',     name: '平均余额',  width: 95, isPercent: false, precision: 2 },
  { key: 'weighted_rate',   name: '加权利率',  width: 70, isPercent: true,  precision: 4 },
  { key: 'risk_weight',     name: '风险权重',  width: 80, isPercent: true,  precision: 4 },
]

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

  // 树形行（仅保留 L1-L3 详情行）
  const accountRows = useMemo(() => {
    const nodes = matrixNodes.filter((n) => n.node_level >= 1 && n.node_level <= 3)
    const byParent: Record<number, any[]> = {}
    nodes.forEach((n) => {
      const key = n.parent_id || 0
      if (!byParent[key]) byParent[key] = []
      byParent[key].push(n)
    })
    Object.values(byParent).forEach((arr) =>
      arr.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)),
    )
    const flat: any[] = []
    const walk = (parentId: number | null) => {
      const children = byParent[parentId || 0] || []
      children.forEach((c) => {
        flat.push(c)
        if (c.node_level < 3) walk(c.coa_node_id)
      })
    }
    walk(null)
    return flat
  }, [matrixNodes])

  const indent = (level: number) => ({ paddingLeft: (level - 1) * 20 })

  // 大类汇总行
  const categoryNameOrder = ['ASSET', 'LIABILITY', 'EQUITY', 'OFF_BALANCE', 'OTHER']
  const existingCategories = Object.keys(categoriesAgg).sort((a, b) => {
    const ia = categoryNameOrder.indexOf(a); const ib = categoryNameOrder.indexOf(b)
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib)
  })
  const categoryRows = existingCategories.map((cat) => ({
    category: cat,
    account_count: matrixNodes.filter((n) => {
      const code = n.node_code || ''
      if (cat === 'ASSET') return code.startsWith('ZX_A') || n.path?.startsWith('/L1_ASSET')
      if (cat === 'LIABILITY') return code.startsWith('ZX_L') || n.path?.startsWith('/L1_LIABILITY')
      if (cat === 'EQUITY') return code.startsWith('ZX_E')
      if (cat === 'OFF_BALANCE') return n.path?.startsWith('/L1_OFF_BALANCE')
      return false
    }).length,
  }))

  // 表格列定义
  const baseCols: ColumnsType<any> = [
    { title: '账户册编码', dataIndex: 'node_code', width: 70, fixed: 'left' as const,
      render: (c, r) => (
        <span style={{ ...indent(r.node_level) }}>
          <code style={{ color: r.node_level === 3 ? '#1d39c4' : '#999', fontSize: 12, fontWeight: r.node_level < 3 ? 600 : 400 }}>{c}</code>
        </span>
      ),
    },
    { title: '账户册名称', dataIndex: 'node_name', width: 220, fixed: 'left' as const,
      render: (n, r) => {
        const fontSize = r.node_level === 1 ? 15 : r.node_level === 2 ? 14 : 13
        const fontWeight = r.node_level < 3 ? 700 : 500
        const color = r.node_level === 1 ? '#1d39c4' : r.node_level === 2 ? '#722ed1' : '#262626'
        return (
          <Tooltip title={n} placement="topLeft">
            <span style={{
              ...indent(r.node_level),
              fontSize, fontWeight, color,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              display: 'inline-block', maxWidth: 205,
            }}>
              {n}
            </span>
          </Tooltip>
        )
      },
    },
    { title: '大类', dataIndex: 'category', width: 80, fixed: 'left' as const,
      render: (v) => <DictTag dictType="PRCP_COA_CATEGORY" value={v} />,
    },
  ]

  // 单元格渲染（金额）
  const makeCell = (colKey: string, color: string, precision: number) =>
    (_v: any, r: any) => {
      const cell = matrix[String(r.coa_node_id)] || {}
      const v = cell[colKey]
      if (v === undefined || v === null) return <span style={{ color: '#ccc' }}>-</span>
      return (
        <span style={{ color, fontFamily: 'monospace' }}>
          {(v as number).toLocaleString(undefined, { maximumFractionDigits: precision })}
        </span>
      )
    }

  // 二级表头（原 BasicDataSheet 风格）
  const origGroup = {
    title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>原始期限（金额）</span>,
    children: BUCKETS.map((b) => ({
      title: <span style={{ fontSize: 12, color: '#13c2c2' }}>{b.name}</span>,
      dataIndex: `orig_${b.key}`,
      width: b.width, align: 'right' as const,
      onHeaderCell: () => ({ style: { background: '#fafafa' } }),
      render: makeCell(`orig_${b.key}`, '#13c2c2', 2),
    })),
  }
  const remGroup = {
    title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>剩余期限（金额）</span>,
    children: BUCKETS.map((b) => ({
      title: <span style={{ fontSize: 12, color: '#722ed1' }}>{b.name}</span>,
      dataIndex: `rem_${b.key}`,
      width: b.width, align: 'right' as const,
      onHeaderCell: () => ({ style: { background: '#fafafa' } }),
      render: makeCell(`rem_${b.key}`, '#722ed1', 2),
    })),
  }
  const extraGroup = {
    title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>度量</span>,
    children: EXTRAS.map((m) => ({
      title: <span style={{ fontSize: 12, color: '#eb2f96' }}>{m.name}</span>,
      dataIndex: m.key,
      width: m.width, align: 'right' as const,
      onHeaderCell: () => ({ style: { background: '#fafafa' } }),
      render: (_v: any, r: any) => {
        const cell = matrix[String(r.coa_node_id)] || {}
        const v = cell[m.key]
        if (v === undefined || v === null) return <span style={{ color: '#ccc' }}>-</span>
        const formatted = m.isPercent
          ? (v as number).toFixed(m.precision) + '%'
          : (v as number).toLocaleString(undefined, { maximumFractionDigits: m.precision })
        return (
          <span style={{ color: '#eb2f96', fontFamily: m.isPercent ? 'monospace' : undefined }}>
            {formatted}
          </span>
        )
      },
    })),
  }

  const allCols: ColumnsType<any> = [...baseCols, origGroup, remGroup, extraGroup]

  // 大类汇总列
  const categoryBaseCols: ColumnsType<any> = [
    { title: '大类', dataIndex: 'category', width: 100, fixed: 'left' as const,
      render: (v) => <DictTag dictType="PRCP_COA_CATEGORY" value={v} />,
    },
    { title: '账户册数', dataIndex: 'account_count', width: 100, fixed: 'left' as const },
  ]
  const categoryGroups: any[] = [
    { title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>原始期限（合计）</span>,
      children: BUCKETS.map((b) => ({
        title: <span style={{ fontSize: 12 }}>{b.name}</span>,
        width: b.width, align: 'right' as const,
        render: (_v: any, r: any) => {
          const cell = categoriesAgg[r.category] || {}
          const v = cell[`orig_${b.key}`]
          if (v === undefined) return <span style={{ color: '#ccc' }}>-</span>
          return <span>{(v as number).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
        },
      })),
    },
    { title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>剩余期限（合计）</span>,
      children: BUCKETS.map((b) => ({
        title: <span style={{ fontSize: 12 }}>{b.name}</span>,
        width: b.width, align: 'right' as const,
        render: (_v: any, r: any) => {
          const cell = categoriesAgg[r.category] || {}
          const v = cell[`rem_${b.key}`]
          if (v === undefined) return <span style={{ color: '#ccc' }}>-</span>
          return <span>{(v as number).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
        },
      })),
    },
  ]
  const allCatCols: ColumnsType<any> = [...categoryBaseCols, ...categoryGroups]

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
              style={{ width: 240 }}
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

      <Card bordered={false} bodyStyle={{ paddingTop: 8 }}>
        <Tabs
          defaultActiveKey="matrix"
          items={[
            {
              key: 'matrix',
              label: <span><BankOutlined /> 账户册矩阵（二级表头） <Badge count={accountRows.length} showZero color="#1d39c4" /></span>,
              children: (
                <Table
                  size="small"
                  rowKey="coa_node_id"
                  dataSource={accountRows}
                  columns={allCols as any}
                  scroll={{ x: 70 + 220 + 80 + 64 * 50 + 4 * 80, y: 'calc(100vh - 380px)' }}
                  pagination={false}
                  bordered
                  locale={{ emptyText: <Empty description="该预测月份下无反算结果" /> }}
                />
              ),
            },
            {
              key: 'category',
              label: <span><FundProjectionScreenOutlined /> 大类汇总（资产/负债/权益/表外）</span>,
              children: (
                <Table
                  size="small"
                  rowKey="category"
                  dataSource={categoryRows}
                  columns={allCatCols as any}
                  scroll={{ x: 100 + 100 + 64 * 50, y: 'calc(100vh - 380px)' }}
                  pagination={false}
                  bordered
                />
              ),
            },
          ]}
        />
      </Card>
    </Spin>
  )
}

export default ReverseResult
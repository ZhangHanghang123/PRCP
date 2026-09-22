/** 新业务模拟 — 结果查看页
 *
 * 入口：/sim/results/:sim_scheme_code（从方案列表「查看结果」按钮跳转）
 * 布局：左侧账户册 DirectoryTree（仅显示引擎跑过的节点）
 *      + 右侧选中节点的 24 月快照 Tabs（每 Tab 一个节点 × 64+64 桶二级表头表格）
 *
 * 顶部：方案下拉 + Run 选择 + 4 全局 KPI 汇总
 * 主体：左 7 列账户册树 + 右 17 列节点 N 月快照（选中 + 下级多行）
 */
import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Select, Table, Space, Tag, message, Empty, Row, Col, Statistic,
  Spin, Button, Tabs, Tree, Tooltip,
} from 'antd'
import {
  ArrowLeftOutlined, ReloadOutlined, LineChartOutlined,
  CalendarOutlined, FundProjectionScreenOutlined,
  ApartmentOutlined, FolderOutlined, FileTextOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { DataNode } from 'antd/es/tree'
import { useParams, useNavigate } from 'react-router-dom'
import { simApi } from '../api'
import { BUCKETS } from '../constants/buckets'

interface ResultRow {
  id: number
  run_id: number
  data_date: string
  date_offset: number
  coa_node_id: number
  coa_scheme_id: number
  node_code: string
  node_name: string
  node_level: number
  category: string
  /** 是否有节点配置（true=已配置=新业务模拟 / false=未配置=纯滚动） */
  is_configured: boolean
  /** 是否为汇总节点（true=从子叶子聚合 / false=叶子节点本身） */
  is_aggregated: boolean
  current_balance: number
  avg_balance: number
  weighted_rate: number
  interest_amount: number
  // 128 桶（仅 with_buckets=true 时填充）
  [key: string]: any
}

const SimResultPage: React.FC = () => {
  const params = useParams()
  const navigate = useNavigate()
  const schemeCode = params.sim_scheme_code || ''

  const [schemes, setSchemes] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [activeRun, setActiveRun] = useState<number | null>(null)
  const [results, setResults] = useState<ResultRow[]>([])
  const [loading, setLoading] = useState(false)
  const [category, setCategory] = useState<string | undefined>(undefined)
  const [treeData, setTreeData] = useState<DataNode[]>([])
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])
  const [activeMonthTab, setActiveMonthTab] = useState<string>('1')

  // =================== 数据加载 ===================

  const loadSchemes = async () => {
    try {
      const r = await simApi.listSchemes()
      setSchemes(r.items || [])
    } catch { /* 静默 */ }
  }

  const loadRuns = async (code: string) => {
    if (!code) return
    try {
      const r = await simApi.listRuns({ sim_scheme_code: code })
      setRuns(r.items || [])
      const successRuns = r.items.filter((x: any) => x.status === 'SUCCESS')
      if (successRuns.length > 0) setActiveRun(successRuns[0].id)
      else if (r.items.length > 0) setActiveRun(r.items[0].id)
      else setActiveRun(null)
    } catch {
      setRuns([])
      setActiveRun(null)
    }
  }

  // 不带 128 桶的全局 results（用于顶部 KPI / 树命中 / 节点级 KPI）
  const loadResults = async (runId: number | null) => {
    if (!runId) { setResults([]); return }
    setLoading(true)
    try {
      const r = await simApi.listResults({ run_id: runId, category, with_buckets: true })
      setResults(r.items || [])
    } catch (e: any) {
      message.error('结果加载失败')
    } finally {
      setLoading(false)
    }
  }

  const loadCoaTree = async (sid: number) => {
    try {
      const t = await simApi.coaTree(sid)
      const toDataNode = (n: any): DataNode => ({
        key: String(n.id),
        // title 暂存为一个 React 元素，颜色由 treeDataColored 在 results 加载后注入
        title: (
          <span>
            <code style={{ fontSize: 11, marginRight: 4 }}>{n.code}</code>
            {n.title}
          </span>
        ),
        icon: n.isLeaf ? <FileTextOutlined /> : <FolderOutlined />,
        isLeaf: n.isLeaf,
        children: n.children?.map(toDataNode),
        // 自定义元数据：节点类型/层级/编码（用于按层级缩进展示）
        ...({
          nodeType: n.type,
          nodeLevel: n.level,
          nodeCode: n.code,
          nodeName: n.name,
        } as any),
      })
      setTreeData((t.items || []).map(toDataNode))
      const expandKeys: string[] = []
      const collect = (ns: any[]) => {
        for (const n of ns) {
          if (n.level && n.level <= 2) expandKeys.push(String(n.id))
          if (n.children) collect(n.children)
        }
      }
      collect(t.items || [])
      setExpandedKeys(expandKeys)
    } catch (e: any) {
      message.error('账户册树加载失败')
    }
  }

  // 切换方案
  const switchScheme = (code: string) => {
    if (code === schemeCode) return
    navigate(`/sim/results/${code}`)
  }

  useEffect(() => { loadSchemes() }, [])
  useEffect(() => {
    if (schemeCode) loadRuns(schemeCode)
  }, [schemeCode])
  useEffect(() => { loadResults(activeRun) }, [activeRun, category])

  const currentScheme = schemes.find(s => s.scheme_code === schemeCode)
  useEffect(() => {
    const s = schemes.find(x => x.scheme_code === schemeCode)
    if (s?.coa_scheme_id) loadCoaTree(s.coa_scheme_id)
  }, [schemes, schemeCode])

  const currentRun = runs.find(r => r.id === activeRun)

  // =================== 派生数据 ===================

  const runnedNodeIds = useMemo(() => new Set(results.map(r => r.coa_node_id)), [results])
  /** 已配置节点（参与新业务模拟） */
  const configuredNodeIds = useMemo(
    () => new Set(results.filter(r => r.is_configured).map(r => r.coa_node_id)),
    [results]
  )
  /** 未配置叶子节点（只做时间桶滚动） */
  const rolledNodeIds = useMemo(
    () => new Set(results.filter(r => !r.is_configured && !r.is_aggregated).map(r => r.coa_node_id)),
    [results]
  )
  /** 汇总节点（从后代叶子聚合） */
  const aggregatedNodeIds = useMemo(
    () => new Set(results.filter(r => r.is_aggregated).map(r => r.coa_node_id)),
    [results]
  )
  const runnedNodeMap = useMemo(() => {
    const m = new Map<number, ResultRow>()
    for (const r of results) if (!m.has(r.coa_node_id)) m.set(r.coa_node_id, r)
    return m
  }, [results])

  // 顶部 KPI（全部节点）
  const kpi = useMemo(() => {
    if (results.length === 0) return null
    const total_current = results.reduce((a, r) => a + (r.current_balance || 0), 0)
    const total_avg = results.reduce((a, r) => a + (r.avg_balance || 0), 0)
    const total_interest = results.reduce((a, r) => a + (r.interest_amount || 0), 0)
    const sum_avg_wr = results.reduce((a, r) => a + (r.avg_balance || 0) * (r.weighted_rate || 0), 0)
    const sum_avg = results.reduce((a, r) => a + (r.avg_balance || 0), 0)
    const avg_wr = sum_avg > 0 ? sum_avg_wr / sum_avg : 0
    return { total_current, total_avg, total_interest, avg_wr }
  }, [results])

  // 选中节点的 24 月数据
  const selectedNodeResults = useMemo(() => {
    if (!selectedNodeId) return []
    return results
      .filter(r => r.coa_node_id === selectedNodeId)
      .sort((a, b) => a.date_offset - b.date_offset)
  }, [results, selectedNodeId])

  // 默认选第一个已配置的节点（没有再选第一个跑过的）
  useEffect(() => {
    if (selectedNodeId !== null) return
    if (configuredNodeIds.size > 0) {
      const first = results.find(r => r.coa_node_id && configuredNodeIds.has(r.coa_node_id))
      if (first) setSelectedNodeId(first.coa_node_id)
      return
    }
    if (runnedNodeIds.size > 0) {
      const first = results.find(r => r.coa_node_id && runnedNodeIds.has(r.coa_node_id))
      if (first) setSelectedNodeId(first.coa_node_id)
    }
  }, [results, configuredNodeIds, runnedNodeIds])

  // 当切换节点时，重置月份 Tab 到 M1
  useEffect(() => {
    setActiveMonthTab('1')
  }, [selectedNodeId])

  // =================== 选中节点 + 后代快照 ===================

  /** 在 treeData 中递归查找节点（返回带自定义字段的原始对象） */
  const findNodeInTree = (nodes: DataNode[], id: string | number): any => {
    const target = String(id)
    for (const n of nodes) {
      if (n.key === target) return n
      if (n.children && n.children.length > 0) {
        const found = findNodeInTree(n.children, target)
        if (found) return found
      }
    }
    return null
  }

  /** 收集节点及其所有后代（按树 pre-order 排序） */
  const collectNodeAndDescendants = (root: any): any[] => {
    const result: any[] = []
    const dfs = (n: any) => {
      result.push(n)
      if (n.children && n.children.length > 0) {
        for (const c of n.children) dfs(c)
      }
    }
    if (root) dfs(root)
    return result
  }

  /** 选中节点 + 所有后代节点对象（按树层级排序） */
  const selectedNodeWithDescendants = useMemo(() => {
    if (!selectedNodeId || treeData.length === 0) return []
    const node = findNodeInTree(treeData, selectedNodeId)
    return collectNodeAndDescendants(node)
  }, [selectedNodeId, treeData])

  /** 选中节点 + 后代在当前月份的快照行（多行） */
  const currentMonthRows: ResultRow[] = useMemo(() => {
    if (!selectedNodeId || selectedNodeResults.length === 0) return []
    if (selectedNodeWithDescendants.length === 0) return []
    const descendantIds = new Set(selectedNodeWithDescendants.map(n => Number(n.key)))
    // 按树 pre-order 顺序输出：选中节点自身 + 后代
    return selectedNodeWithDescendants
      .map(n => {
        const nid = Number(n.key)
        return selectedNodeResults.find(r => r.coa_node_id === nid) || null
      })
      .filter((r): r is ResultRow => r !== null)
  }, [selectedNodeResults, selectedNodeWithDescendants])

  // =================== 表格：单月 64+64 桶（类似 BasicDataSheet） ===================

  // 给 treeData 注入颜色 + 状态 Tag（响应 configuredNodeIds / rolledNodeIds / aggregatedNodeIds 变化）
  const treeDataColored: DataNode[] = useMemo(() => {
    const colorize = (n: DataNode): DataNode => {
      const id = Number(n.key)
      const configured = configuredNodeIds.has(id)
      const rolled = rolledNodeIds.has(id)
      const aggregated = aggregatedNodeIds.has(id)
      // 颜色：已配置=绿色，汇总/滚动=黑色，未跑过=灰色
      const textColor = configured ? '#52c41a' : ((rolled || aggregated) ? '#262626' : '#888')
      const originalTitle = (n as any).title as React.ReactNode
      return {
        ...n,
        title: (
          <span style={{ fontSize: 13, color: textColor }}>
            {originalTitle}
            {configured && (
              <Tag color="green" style={{ marginLeft: 6, fontSize: 10, padding: '0 4px', lineHeight: '14px' }}>
                ⚡ 已配置
              </Tag>
            )}
            {rolled && !configured && (
              <Tag style={{ marginLeft: 6, fontSize: 10, padding: '0 4px', lineHeight: '14px', color: '#888' }}>
                🔄 仅滚动
              </Tag>
            )}
            {aggregated && (
              <Tag color="default" style={{ marginLeft: 6, fontSize: 10, padding: '0 4px', lineHeight: '14px', borderColor: '#bfbfbf' }}>
                📊 汇总节点
              </Tag>
            )}
          </span>
        ),
        children: n.children?.map(colorize),
      }
    }
    return treeData.map(colorize)
  }, [treeData, configuredNodeIds, rolledNodeIds, aggregatedNodeIds])

  // 单月快照数据：M_k 行的「选中节点 + 所有下级」数据（已 pre-order 排序）
  // 注意：从全量 results 过滤（不是 selectedNodeResults），因为下级节点也有自己的行
  const currentMonthRowsAtTab: ResultRow[] = useMemo(() => {
    const offset = Number(activeMonthTab)
    return results.filter(r => r.date_offset === offset)
  }, [results, activeMonthTab])

  // 按树 pre-order 排序（选中节点 + 后代）
  const monthTableData: ResultRow[] = useMemo(() => {
    if (!selectedNodeId || selectedNodeWithDescendants.length === 0) return []
    const byNodeId = new Map<number, ResultRow>()
    for (const r of currentMonthRowsAtTab) byNodeId.set(r.coa_node_id, r)
    return selectedNodeWithDescendants
      .map(n => byNodeId.get(Number(n.key)))
      .filter((r): r is ResultRow => r !== undefined)
  }, [currentMonthRowsAtTab, selectedNodeWithDescendants, selectedNodeId])

  /** 选中节点在 M_k 的当前数据（用于节点级 KPI / 表头日期） */
  const currentMonthRow = useMemo(() => {
    if (!selectedNodeId) return null
    return currentMonthRowsAtTab.find(r => r.coa_node_id === selectedNodeId) || null
  }, [currentMonthRowsAtTab, selectedNodeId])

  // 表格列：节点列按层级缩进 + 颜色 + Tag；桶列每行单独渲染
  const monthTableColumns: ColumnsType<ResultRow> = useMemo(() => {
    const baseCol: ColumnsType<ResultRow>[number] = {
      title: (
        <span>
          账户册节点
          <span style={{ marginLeft: 8, fontSize: 11, color: '#999', fontWeight: 'normal' }}>
            (选中 + {selectedNodeWithDescendants.length - 1} 个下级)
          </span>
        </span>
      ),
      key: 'node',
      fixed: 'left',
      width: 240,
      onCell: (record: ResultRow) => {
        const isSelected = record.coa_node_id === selectedNodeId
        const isDescendant = record.coa_node_id !== selectedNodeId
        // 找节点的层级信息（用于缩进）
        const treeNode = selectedNodeWithDescendants.find(n => Number(n.key) === record.coa_node_id)
        const baseLevel = (selectedNodeWithDescendants[0]?.nodeLevel as number) || 1
        const nodeLevel = (treeNode?.nodeLevel as number) || baseLevel
        const indent = Math.max(0, nodeLevel - baseLevel) * 16
        return {
          style: {
            background: isSelected ? '#f0f5ff' : (isDescendant ? '#fafafa' : undefined),
            fontWeight: isSelected ? 600 : 400,
            paddingLeft: 8 + indent,
          },
        }
      },
      render: (_, record: ResultRow) => {
        const isSelected = record.coa_node_id === selectedNodeId
        const treeNode = selectedNodeWithDescendants.find(n => Number(n.key) === record.coa_node_id)
        const indent = Math.max(0, ((treeNode?.nodeLevel as number) || 0) - ((selectedNodeWithDescendants[0]?.nodeLevel as number) || 0)) * 12
        return (
          <div style={{ paddingLeft: indent }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <code style={{
                fontSize: 11,
                background: record.is_configured ? '#f6ffed' : (record.is_aggregated ? '#fff7e6' : '#f5f5f5'),
                color: record.is_configured ? '#52c41a' : '#262626',
                fontWeight: record.is_configured ? 600 : 400,
                padding: '1px 4px',
                borderRadius: 3,
                border: record.is_configured ? '1px solid #b7eb8f' : 'none',
              }}>
                {record.node_code}
              </code>
              {isSelected && <span style={{ fontSize: 10, color: '#2f54eb', fontWeight: 600 }}>▼ 选中</span>}
            </div>
            <div style={{
              fontSize: 11,
              marginTop: 2,
              color: record.is_configured ? '#52c41a' : '#262626',
              fontWeight: record.is_configured ? 500 : 400,
            }}>
              {record.node_name}
              {record.is_configured && (
                <Tag color="green" style={{ marginLeft: 4, fontSize: 9, padding: '0 3px', lineHeight: '12px' }}>
                  ⚡ 已配置
                </Tag>
              )}
              {record.is_aggregated && (
                <Tag style={{ marginLeft: 4, fontSize: 9, padding: '0 3px', lineHeight: '12px', color: '#595959', borderColor: '#bfbfbf' }}>
                  📊 汇总
                </Tag>
              )}
              {!record.is_configured && !record.is_aggregated && (
                <Tag style={{ marginLeft: 4, fontSize: 9, padding: '0 3px', lineHeight: '12px', color: '#888' }}>
                  🔄 仅滚动
                </Tag>
              )}
            </div>
          </div>
        )
      },
    }
    const renderBucketCell = (colName: string, color: string) => (_: any, record: ResultRow) => {
      const v = record[colName]
      if (v === undefined || v === null) return <span style={{ color: '#ccc' }}>-</span>
      if (Math.abs(v as number) < 0.005) return <span style={{ color: '#bbb' }}>·</span>
      const isSelected = record.coa_node_id === selectedNodeId
      return (
        <span style={{
          color,
          fontFamily: 'monospace',
          fontWeight: isSelected ? 600 : 400,
        }}>
          {(v as number).toLocaleString(undefined, { maximumFractionDigits: 2 })}
        </span>
      )
    }
    const origGroup = {
      title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>原始期限金额（{currentMonthRow?.data_date || '-'}）</span>,
      children: BUCKETS.map((b) => ({
        title: <span style={{ fontSize: 12, color: '#13c2c2' }}>{b.name}</span>,
        key: `orig_${b.key}`,
        width: b.width,
        align: 'right' as const,
        onHeaderCell: () => ({ style: { background: '#fafafa' } }),
        onCell: (record: ResultRow) => ({
          style: {
            background: record.coa_node_id === selectedNodeId ? '#f0f5ff' : undefined,
            fontWeight: record.coa_node_id === selectedNodeId ? 600 : 400,
          },
        }),
        render: renderBucketCell(`orig_${b.key}`, '#13c2c2'),
      })),
    }
    const remGroup = {
      title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>剩余期限金额</span>,
      children: BUCKETS.map((b) => ({
        title: <span style={{ fontSize: 12, color: '#722ed1' }}>{b.name}</span>,
        key: `rem_${b.key}`,
        width: b.width,
        align: 'right' as const,
        onHeaderCell: () => ({ style: { background: '#fafafa' } }),
        onCell: (record: ResultRow) => ({
          style: {
            background: record.coa_node_id === selectedNodeId ? '#f0f5ff' : undefined,
            fontWeight: record.coa_node_id === selectedNodeId ? 600 : 400,
          },
        }),
        render: renderBucketCell(`rem_${b.key}`, '#722ed1'),
      })),
    }
    const measureGroup = {
      title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>度量</span>,
      children: [
        { title: '当前余额', key: 'current_balance', width: 110, align: 'right' as const,
          onHeaderCell: () => ({ style: { background: '#fafafa' } }),
          onCell: (record: ResultRow) => ({
            style: {
              background: record.coa_node_id === selectedNodeId ? '#f0f5ff' : undefined,
              fontWeight: record.coa_node_id === selectedNodeId ? 600 : 400,
            },
          }),
          render: (_: any, record: ResultRow) => (
            <strong style={{ color: '#2f54eb' }}>
              {(record.current_balance || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </strong>
          ) },
        { title: '平均余额', key: 'avg_balance', width: 110, align: 'right' as const,
          onHeaderCell: () => ({ style: { background: '#fafafa' } }),
          onCell: (record: ResultRow) => ({
            style: {
              background: record.coa_node_id === selectedNodeId ? '#f0f5ff' : undefined,
              fontWeight: record.coa_node_id === selectedNodeId ? 600 : 400,
            },
          }),
          render: (_: any, record: ResultRow) => (record.avg_balance || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) },
        { title: '加权利率(%)', key: 'weighted_rate', width: 90, align: 'right' as const,
          onHeaderCell: () => ({ style: { background: '#fafafa' } }),
          onCell: (record: ResultRow) => ({
            style: {
              background: record.coa_node_id === selectedNodeId ? '#f0f5ff' : undefined,
              fontWeight: record.coa_node_id === selectedNodeId ? 600 : 400,
            },
          }),
          render: (_: any, record: ResultRow) => <span style={{ color: '#fa8c16' }}>{(record.weighted_rate || 0).toFixed(4)}</span> },
        { title: '当月利息', key: 'interest_amount', width: 100, align: 'right' as const,
          onHeaderCell: () => ({ style: { background: '#fafafa' } }),
          onCell: (record: ResultRow) => ({
            style: {
              background: record.coa_node_id === selectedNodeId ? '#f0f5ff' : undefined,
              fontWeight: record.coa_node_id === selectedNodeId ? 600 : 400,
            },
          }),
          render: (_: any, record: ResultRow) => (record.interest_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) },
      ],
    }
    return [baseCol, origGroup, remGroup, measureGroup] as any
  }, [selectedNodeId, selectedNodeWithDescendants, currentMonthRow])

  const selectedMeta = selectedNodeId ? runnedNodeMap.get(selectedNodeId) : null

  // =================== 渲染 ===================

  return (
    <div className="page-container">
      {/* 顶部信息条 */}
      <Card
        size="small"
        title={
          <Space>
            <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => navigate('/sim/list')} style={{ paddingLeft: 0 }}>
              返回方案列表
            </Button>
            <span style={{ color: '#999' }}>|</span>
            <FundProjectionScreenOutlined style={{ color: '#722ed1' }} />
            <span>模拟结果查看</span>
            {currentScheme && (
              <Space size={6} style={{ fontWeight: 'normal', fontSize: 13 }}>
                <Tag color="purple">{currentScheme.scheme_code}</Tag>
                <span>{currentScheme.scheme_name}</span>
                {currentScheme.data_date && (
                  <Tag color="cyan" icon={<CalendarOutlined />} style={{ fontFamily: 'monospace' }}>
                    起始月 {currentScheme.data_date}
                  </Tag>
                )}
              </Space>
            )}
          </Space>
        }
        extra={
          <Space>
            <Select
              showSearch
              optionFilterProp="label"
              style={{ width: 240 }}
              value={schemeCode}
              onChange={switchScheme}
              placeholder="选择方案"
              options={schemes.map(s => ({
                value: s.scheme_code,
                label: `${s.scheme_code} | ${s.scheme_name}`,
              }))}
            />
            {runs.length > 0 && (
              <Select
                style={{ width: 220 }}
                value={activeRun}
                onChange={setActiveRun}
                placeholder="选择 Run"
                options={runs.map(r => ({
                  value: r.id,
                  label: `run#${r.id} ${r.status} M=${r.month_count} ${r.started_at?.slice(0,16).replace('T',' ')}`,
                }))}
              />
            )}
            <Button icon={<ReloadOutlined />} onClick={() => loadResults(activeRun)}>刷新</Button>
          </Space>
        }
      />

      {/* Run 状态卡 */}
      {currentRun && (
        <Card size="small" style={{ marginTop: 12 }}>
          <Row gutter={16}>
            <Col span={3}><Statistic title="Run ID" value={currentRun.id} prefix={<LineChartOutlined style={{ color: '#722ed1' }} />} /></Col>
            <Col span={3}><Statistic title="状态" value={currentRun.status} valueStyle={{ color: currentRun.status === 'SUCCESS' ? '#52c41a' : '#f5222d' }} /></Col>
            <Col span={3}>
              <Statistic
                title="总节点数"
                value={currentRun.total_nodes}
              />
            </Col>
            <Col span={3}>
              <Statistic
                title={<span><Tag color="green" style={{ marginRight: 4 }}>⚡ 已配置</Tag></span>}
                value={currentRun.configured_node_count || 0}
                valueStyle={{ color: '#52c41a', fontWeight: 600 }}
              />
            </Col>
            <Col span={3}>
              <Statistic
                title={<span><Tag style={{ marginRight: 4 }}>🔄 仅滚动</Tag></span>}
                value={(currentRun.rolled_node_count || 0) - (currentRun.aggregated_node_count || 0)}
                valueStyle={{ color: '#595959' }}
              />
            </Col>
            <Col span={3}>
              <Statistic
                title={<span><Tag color="default" style={{ marginRight: 4, borderColor: '#bfbfbf' }}>📊 汇总节点</Tag></span>}
                value={currentRun.aggregated_node_count || 0}
                valueStyle={{ color: '#595959' }}
              />
            </Col>
            <Col span={3}><Statistic title="生成月份" value={currentRun.month_count} /></Col>
            <Col span={3}><Statistic title="耗时" value={currentRun.duration_ms || '-'} suffix="ms" /></Col>
          </Row>
          <Row gutter={16} style={{ marginTop: 8 }}>
            <Col span={6}>
              <Statistic
                title="基准月 → 目标月"
                value={`${currentRun.base_data_date} → ${currentRun.target_data_date}`}
                valueStyle={{ fontSize: 13 }}
              />
            </Col>
          </Row>
          {currentRun.status === 'FAILED' && (
            <div style={{ marginTop: 12, color: '#f5222d' }}>
              <strong>错误：</strong><code>{currentRun.error_message}</code>
            </div>
          )}
        </Card>
      )}

      {/* KPI 汇总 */}
      {kpi && (
        <Card size="small" style={{ marginTop: 12, background: '#f0f5ff' }}>
          <Row gutter={16}>
            <Col span={6}><Statistic title="汇总当前余额" value={kpi.total_current} precision={2} valueStyle={{ color: '#2f54eb' }} /></Col>
            <Col span={6}><Statistic title="汇总平均余额" value={kpi.total_avg} precision={2} valueStyle={{ color: '#52c41a' }} /></Col>
            <Col span={6}><Statistic title="加权平均利率" value={kpi.avg_wr} precision={4} suffix="%" valueStyle={{ color: '#fa8c16' }} /></Col>
            <Col span={6}><Statistic title="汇总当月利息" value={kpi.total_interest} precision={2} valueStyle={{ color: '#722ed1' }} /></Col>
          </Row>
        </Card>
      )}

      {/* 主体：左树 + 右 24M Tab 快照 */}
      <Row gutter={12} style={{ marginTop: 12 }}>
        <Col span={7}>
          <Card
            size="small"
            title={
              <Space>
                <ApartmentOutlined style={{ color: '#722ed1' }} />
                <span>账户册节点</span>
                {configuredNodeIds.size > 0 && (
                  <Tag color="green">⚡ 已配置 {configuredNodeIds.size}</Tag>
                )}
                {rolledNodeIds.size > 0 && (
                  <Tag style={{ color: '#595959' }}>🔄 仅滚动 {rolledNodeIds.size}</Tag>
                )}
              </Space>
            }
            bodyStyle={{ padding: 8, maxHeight: 'calc(100vh - 380px)', overflowY: 'auto' }}
          >
            {treeData.length === 0 ? (
              <Empty description="加载账户册..." imageStyle={{ height: 60 }} />
            ) : (
              <Tree
                treeData={treeDataColored}
                expandedKeys={expandedKeys}
                onExpand={(keys) => setExpandedKeys(keys)}
                selectedKeys={selectedNodeId ? [String(selectedNodeId)] : []}
                onSelect={(keys) => {
                  if (keys.length > 0) {
                    const id = Number(keys[0])
                    if (runnedNodeIds.has(id)) setSelectedNodeId(id)
                    else message.info('该节点未被引擎模拟（无配置）')
                  }
                }}
                showLine={{ showLeafIcon: false }}
                blockNode
              />
            )}
          </Card>
        </Col>

        <Col span={17}>
          <Card
            size="small"
            title={
              <Space>
                <span>节点 N 月快照（选中 + 下级）</span>
                {selectedMeta ? (
                  <Space size={6} style={{ fontWeight: 'normal' }}>
                    <Tag color={selectedMeta.is_configured ? 'green' : 'default'}>
                      {selectedMeta.node_code}
                    </Tag>
                    <span style={{ fontSize: 13, color: selectedMeta.is_configured ? '#52c41a' : '#262626' }}>
                      {selectedMeta.node_name}
                    </span>
                    <Tag color={selectedMeta.category === 'ASSET' ? 'blue' : selectedMeta.category === 'LIABILITY' ? 'orange' : 'default'}>
                      {selectedMeta.category}
                    </Tag>
                    <Tag color="cyan">L{selectedMeta.node_level}</Tag>
                    {selectedMeta.is_configured ? (
                      <Tag color="green">⚡ 已配置</Tag>
                    ) : (
                      <Tag style={{ color: '#595959' }}>🔄 仅滚动</Tag>
                    )}
                  </Space>
                ) : (
                  <Tag color="default">请选择左侧节点</Tag>
                )}
              </Space>
            }
            extra={
              <Space>
                <span>类别：</span>
                <Select
                  size="small" style={{ width: 110 }}
                  placeholder="全部"
                  allowClear
                  value={category}
                  onChange={setCategory}
                  options={[
                    { value: 'ASSET', label: '资产' },
                    { value: 'LIABILITY', label: '负债' },
                    { value: 'EQUITY', label: '权益' },
                    { value: 'OFF_BALANCE', label: '表外' },
                  ]}
                />
              </Space>
            }
            bodyStyle={{ padding: 12 }}
          >
            <Spin spinning={loading}>
              {!selectedMeta ? (
                <Empty description="请选择左侧账户册节点（绿色=已配置/黑色=仅滚动）" />
              ) : selectedNodeResults.length === 0 ? (
                <Empty description="该节点无结果数据" />
              ) : (
                <>
                  {/* 节点级 KPI */}
                  <Row gutter={16} style={{ marginBottom: 12 }}>
                    <Col span={6}>
                      <Statistic title={`M1 当前余额`} value={selectedNodeResults[0]?.current_balance || 0} precision={2} valueStyle={{ color: '#2f54eb', fontSize: 16 }} />
                    </Col>
                    <Col span={6}>
                      <Statistic title={`M${selectedNodeResults.length} 当前余额`} value={selectedNodeResults[selectedNodeResults.length-1]?.current_balance || 0} precision={2} valueStyle={{ color: '#52c41a', fontSize: 16 }} />
                    </Col>
                    <Col span={6}>
                      <Statistic title={`M${selectedNodeResults.length} 加权利率`} value={selectedNodeResults[selectedNodeResults.length-1]?.weighted_rate || 0} precision={4} suffix="%" valueStyle={{ color: '#fa8c16', fontSize: 16 }} />
                    </Col>
                    <Col span={6}>
                      <Statistic title={`累计利息（${selectedNodeResults.length} 月）`} value={selectedNodeResults.reduce((a, r) => a + (r.interest_amount || 0), 0)} precision={2} valueStyle={{ color: '#722ed1', fontSize: 16 }} />
                    </Col>
                  </Row>

                  {/* 24 月 Tab：每个 Tab 一个 64+64 桶表格 */}
                  <Tabs
                    activeKey={activeMonthTab}
                    onChange={setActiveMonthTab}
                    type="card"
                    items={selectedNodeResults.map((r) => ({
                      key: String(r.date_offset),
                      label: (
                        <Space size={4}>
                          <Tag color={r.date_offset === Number(activeMonthTab) ? 'purple' : 'blue'} style={{ margin: 0 }}>M{r.date_offset}</Tag>
                          <span style={{ fontSize: 11, color: '#999', fontFamily: 'monospace' }}>{r.data_date?.slice(5)}</span>
                        </Space>
                      ),
                      children: (
                        <Table
                          rowKey={(record: ResultRow) => `${r.run_id}-${r.date_offset}-${record.coa_node_id}`}
                          columns={monthTableColumns}
                          dataSource={monthTableData}
                          size="small"
                          pagination={false}
                          scroll={{ x: 7700, y: 400 }}
                          bordered
                          style={{ background: '#fafafa' }}
                        />
                      ),
                    }))}
                  />
                </>
              )}
            </Spin>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default SimResultPage

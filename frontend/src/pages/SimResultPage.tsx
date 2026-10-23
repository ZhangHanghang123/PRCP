/** 新业务模拟 — 结果查看页
 *
 * 入口：/sim/results/:sim_scheme_code（从方案列表「查看结果」按钮跳转）
 * 布局：左侧账户册 DirectoryTree（仅显示引擎跑过的节点）
 *      + 右侧当前选中月份的快照表格（顶部下拉切换月份 + 表头分组）
 *
 * 顶部：方案下拉 + Run 选择 + 4 全局 KPI 汇总
 * 主体：左 7 列账户册树 + 右 17 列当前月份快照（选中 + 下级多行）
 *
 * 表头分组（activeColumnGroup）：measure / original / remaining / all
 *   - 切换月份通过顶部 Select 实现，不再使用 Tabs
 *   - 全部模式下，度量列紧跟节点列（最左侧）
 */
import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Select, Table, Space, Tag, message, Empty, Row, Col, Statistic,
  Spin, Button, Tree, Tooltip, Divider, Alert,
} from 'antd'
import {
  ArrowLeftOutlined, ReloadOutlined, LineChartOutlined,
  CalendarOutlined, FundProjectionScreenOutlined,
  ApartmentOutlined, FolderOutlined, FileTextOutlined,
  ThunderboltOutlined, InfoCircleOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
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
  /** v2.1 投放分解追溯字段 */
  growth_type?: number | null
  year_target?: number | null
  rhythm_weight?: number | null
  month_add?: number | null
  month_release?: number | null
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
  /** 表头分组切换：度量 / 原始期限金额 / 剩余期限金额 / 全部（度量置左） */
  const [activeColumnGroup, setActiveColumnGroup] = useState<'measure' | 'original' | 'remaining' | 'all'>('all')

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
      const rows = r.items || []
      setResults(rows)
      // 数据被 LIMIT 截断 → 汇总类统计会失真，必须提示
      if (r.truncated) {
        message.warning(
          `结果数据量过大（返回 ${rows.length} 行已达上限），汇总统计可能不完整。` +
          `请按月查看或调大接口 limit 参数。`
        )
      }
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

  // 顶部 KPI（按当前选中月份的截面，仅统计末级节点；金额单位统一亿元）
  // ⚠️ 两处关键约束（曾导致汇总值虚增 68 倍）：
  //   1) 只统计叶子节点（is_aggregated=0）——汇总节点是子节点的聚合，一并累加会重复计入
  //   2) 只统计当前选中月份（date_offset === activeMonthTab）——余额是时点截面
  const kpi = useMemo(() => {
    if (results.length === 0) return null
    const offset = Number(activeMonthTab)
    const rows = results.filter(
      r => !r.is_aggregated && r.date_offset === offset
    )
    if (rows.length === 0) return null

    /** 单类别汇总：余额/平均余额/利息（亿元）+ 加权平均利率 */
    const agg = (cat: string) => {
      const rs = rows.filter(r => r.category === cat)
      const current = rs.reduce((a, r) => a + (r.current_balance || 0), 0)
      const avg = rs.reduce((a, r) => a + (r.avg_balance || 0), 0)
      const interest = rs.reduce((a, r) => a + (r.interest_amount || 0), 0)
      const sumAvgWr = rs.reduce(
        (a, r) => a + (r.avg_balance || 0) * (r.weighted_rate || 0), 0)
      return {
        count: rs.length,
        current: current / 1e8,
        avg: avg / 1e8,
        interest: interest / 1e8,
        wr: avg > 0 ? sumAvgWr / avg : 0,
      }
    }

    const asset = agg('A')
    const liability = agg('L')
    const equity = agg('E')
    // 合计（资产 + 负债 + 权益，仅作对照；正常 A ≠ L+E，差额来自基础数据口径）
    const totalCurrent = rows.reduce((a, r) => a + (r.current_balance || 0), 0) / 1e8
    const totalAvg = rows.reduce((a, r) => a + (r.avg_balance || 0), 0) / 1e8
    const totalInterest = rows.reduce((a, r) => a + (r.interest_amount || 0), 0) / 1e8
    const sumAvgWrAll = rows.reduce(
      (a, r) => a + (r.avg_balance || 0) * (r.weighted_rate || 0), 0)
    const sumAvgAll = rows.reduce((a, r) => a + (r.avg_balance || 0), 0)

    return {
      asset, liability, equity,
      total: {
        current: totalCurrent, avg: totalAvg, interest: totalInterest,
        wr: sumAvgAll > 0 ? sumAvgWrAll / sumAvgAll : 0,
      },
      nodeCount: rows.length,
      balanceDiff: asset.current - liability.current - equity.current,
    }
  }, [results, activeMonthTab])

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
    // 表头列分组：根据 activeColumnGroup 派生 4 种展示模式
    //   measure  → 节点列 + 度量组
    //   original → 节点列 + 原始期限金额组
    //   remaining→ 节点列 + 剩余期限金额组
    //   all      → 节点列 + 度量组 + 原始期限组 + 剩余期限组（度量置左）
    switch (activeColumnGroup) {
      case 'measure':
        return [baseCol, measureGroup] as any
      case 'original':
        return [baseCol, origGroup] as any
      case 'remaining':
        return [baseCol, remGroup] as any
      case 'all':
      default:
        return [baseCol, measureGroup, origGroup, remGroup] as any
    }
  }, [selectedNodeId, selectedNodeWithDescendants, currentMonthRow, activeColumnGroup])

  const selectedMeta = selectedNodeId ? runnedNodeMap.get(selectedNodeId) : null

  // ================================================================
  // v2.1 投放节奏展示区（页面底部）
  // 数据来源：prcp_sim_result 的 month_add / month_release / rhythm_weight / year_target
  // ================================================================

  /** 亿元换算 */
  const toYi = (v: any) => (v == null ? null : Number(v) / 1e8)

  /** 月度投放分解（按月汇总所有「已配置」的叶子节点） */
  const rhythmRows = useMemo(() => {
    const map = new Map<number, {
      m: number; add: number; release: number; net: number;
      cumAdd: number; weight: number | null; gt: number | null; yearTarget: number | null;
    }>()
    for (const r of results) {
      // 只统计已配置（参与测算）的叶子节点；汇总节点已在叶子层聚合，避免重复计数
      if (!r.is_configured || r.is_aggregated) continue
      const m = r.date_offset
      const cur = map.get(m) || {
        m, add: 0, release: 0, net: 0, cumAdd: 0,
        weight: null, gt: null, yearTarget: null,
      }
      cur.add += Number(r.month_add || 0)
      cur.release += Number(r.month_release || 0)
      if (cur.weight == null && r.rhythm_weight != null) cur.weight = Number(r.rhythm_weight)
      if (cur.gt == null && r.growth_type != null) cur.gt = Number(r.growth_type)
      if (cur.yearTarget == null && r.year_target != null) cur.yearTarget = Number(r.year_target)
      map.set(m, cur)
    }
    const rows = Array.from(map.values()).sort((a, b) => a.m - b.m)
    let cum = 0
    for (const r of rows) {
      r.net = r.add + r.release
      cum += r.add
      r.cumAdd = cum
    }
    return rows
  }, [results])

  /** 年度汇总（Y1~Y5）
   *  注意：year_target 是「当年目标增量」，每个月行都带同一个值，
   *        因此只能取该年第 1 个月的值，不能按月累加（否则会放大 12 倍）。
   */
  const yearlyRows = useMemo(() => {
    const map = new Map<number, { y: number; target: number; add: number; endBal: number }>()
    for (const r of results) {
      if (!r.is_configured || r.is_aggregated) continue
      const y = Math.floor((r.date_offset - 1) / 12) + 1
      const cur = map.get(y) || { y, target: 0, add: 0, endBal: 0 }
      // 只取该年第 1 个月的 year_target（当年目标增量，全 12 个月共享同一值）
      if ((r.date_offset - 1) % 12 === 0 && r.year_target != null) {
        cur.target = Number(r.year_target)
      }
      cur.add += Number(r.month_add || 0)
      cur.endBal = Number(r.current_balance || 0)
      map.set(y, cur)
    }
    return Array.from(map.values()).sort((a, b) => a.y - b.y)
  }, [results])

  const hasRhythmData = rhythmRows.length > 0

  /** 月度投放 + 节奏权重 双轴图 */
  const rhythmTrendOpt = useMemo(() => {
    const ms = rhythmRows.map(r => `M${r.m}`)
    const addYi = rhythmRows.map(r => toYi(r.add))
    const relYi = rhythmRows.map(r => toYi(r.release))
    const cumYi = rhythmRows.map(r => toYi(r.cumAdd))
    const wPct = rhythmRows.map(r => r.weight)
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 11 } },
      grid: { left: 50, right: 50, top: 36, bottom: 30 },
      xAxis: { type: 'category', data: ms, axisLabel: { fontSize: 10 } },
      yAxis: [
        { type: 'value', name: '金额（亿元）', axisLabel: { fontSize: 10 } },
        { type: 'value', name: '节奏权重（%）', axisLabel: { fontSize: 10 }, splitLine: { show: false } },
      ],
      series: [
        { name: '当月新增投放', type: 'bar', yAxisIndex: 0, data: addYi, itemStyle: { color: '#13c2c2' } },
        { name: '当月到期释放', type: 'bar', yAxisIndex: 0, data: relYi, itemStyle: { color: '#d9d9d9' } },
        { name: '累计投放', type: 'line', yAxisIndex: 0, data: cumYi, smooth: true, lineStyle: { width: 2 }, itemStyle: { color: '#722ed1' } },
        { name: '节奏权重', type: 'line', yAxisIndex: 1, data: wPct, lineStyle: { width: 1.5, type: 'dashed' }, itemStyle: { color: '#fa8c16' } },
      ],
    }
  }, [rhythmRows])

  /** 12 个月节奏权重（取第 1 年的权重，验证跨年复用一致性）
   *  注意：节奏权重按设计跨年复用，所以第 2 年的 M13 应等于第 1 年的 M1，
   *        此处只取第 1 年（M1~M12）展示，避免累加导致数值翻倍。
   */
  const rhythmWeightOpt = useMemo(() => {
    const firstYear = rhythmRows.filter(r => r.m <= 12)
    const labels = Array.from({ length: 12 }, (_, i) => `${i + 1}月`)
    const actual = labels.map((_, i) => firstYear[i]?.weight ?? 0)
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 11 } },
      grid: { left: 40, right: 20, top: 36, bottom: 28 },
      xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', name: '%', axisLabel: { fontSize: 10 } },
      series: [
        {
          name: '线性基准（8.3333%）', type: 'line', data: labels.map(() => 8.3333),
          lineStyle: { width: 1.5, type: 'dashed', color: '#bfbfbf' },
          itemStyle: { color: '#bfbfbf' }, symbol: 'none',
        },
        { name: '实际节奏权重（第 1 年）', type: 'bar', data: actual, itemStyle: { color: '#fa8c16' } },
      ],
    }
  }, [rhythmRows])

  const growthTypeLabel = useMemo(() => {
    const labels: Record<number, string> = {
      1: '目标增长百分比（净增长口径）',
      2: '目标增长绝对值（净增额口径）',
      3: '增长百分比（毛投放口径）',
      4: '增长值（余额锚定，可为负）',
    }
    const gts = Array.from(new Set(rhythmRows.map(r => r.gt).filter(Boolean))) as number[]
    return gts.map(g => labels[g] || `方式${g}`).join(' / ') || '—'
  }, [rhythmRows])

  const yearlyCols: ColumnsType<any> = [
    { title: '年度', dataIndex: 'y', width: 80, align: 'center', render: (v: number) => <Tag color="blue">第 {v} 年</Tag> },
    { title: '年目标增量', dataIndex: 'target', align: 'right', render: (v: number) => toYi(v)?.toFixed(2) ?? '-' },
    { title: '实际投放', dataIndex: 'add', align: 'right', render: (v: number) => toYi(v)?.toFixed(2) ?? '-' },
    {
      title: '达成率', dataIndex: 'add', align: 'right',
      render: (v: number, r: any) => {
        if (!r.target) return '-'
        const pct = (v / r.target) * 100
        return <Tag color={Math.abs(pct - 100) < 1 ? 'green' : 'orange'}>{pct.toFixed(1)}%</Tag>
      },
    },
    { title: '年末余额', dataIndex: 'endBal', align: 'right', render: (v: number) => toYi(v)?.toFixed(2) ?? '-' },
  ]

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
                value={currentRun.rolled_node_count || 0}
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

      {/* KPI 汇总（按当前选中月份的截面，仅统计末级节点，金额单位：亿元） */}
      {kpi && (
        <Card
          size="small" style={{ marginTop: 12, background: '#f0f5ff' }}
          title={
            <Space>
              <span>全局汇总</span>
              <Tag color="blue">M{activeMonthTab} 截面</Tag>
              <Tag>{kpi.nodeCount} 个末级节点</Tag>
              <Tag color="green">单位：亿元</Tag>
            </Space>
          }
        >
          {/* 资产 */}
          <div style={{ marginBottom: 12 }}>
            <Space style={{ marginBottom: 8 }}>
              <Tag color="blue" style={{ marginInlineEnd: 0 }}>资产</Tag>
              <span style={{ fontSize: 12, color: '#8c8c8c' }}>{kpi.asset.count} 个节点</span>
            </Space>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="当前余额" value={kpi.asset.current} precision={2} suffix="亿元"
                  valueStyle={{ color: '#2f54eb', fontSize: 18 }} />
              </Col>
              <Col span={6}>
                <Statistic title="平均余额" value={kpi.asset.avg} precision={2} suffix="亿元"
                  valueStyle={{ color: '#52c41a', fontSize: 18 }} />
              </Col>
              <Col span={6}>
                <Statistic title="加权平均利率" value={kpi.asset.wr} precision={4} suffix="%"
                  valueStyle={{ color: '#fa8c16', fontSize: 18 }} />
              </Col>
              <Col span={6}>
                <Statistic title="当月利息" value={kpi.asset.interest} precision={2} suffix="亿元"
                  valueStyle={{ color: '#722ed1', fontSize: 18 }} />
              </Col>
            </Row>
          </div>

          <Divider style={{ margin: '4px 0 12px' }} />

          {/* 负债 */}
          <div style={{ marginBottom: 12 }}>
            <Space style={{ marginBottom: 8 }}>
              <Tag color="gold" style={{ marginInlineEnd: 0 }}>负债</Tag>
              <span style={{ fontSize: 12, color: '#8c8c8c' }}>{kpi.liability.count} 个节点</span>
            </Space>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="当前余额" value={kpi.liability.current} precision={2} suffix="亿元"
                  valueStyle={{ color: '#d48806', fontSize: 18 }} />
              </Col>
              <Col span={6}>
                <Statistic title="平均余额" value={kpi.liability.avg} precision={2} suffix="亿元"
                  valueStyle={{ color: '#52c41a', fontSize: 18 }} />
              </Col>
              <Col span={6}>
                <Statistic title="加权平均利率" value={kpi.liability.wr} precision={4} suffix="%"
                  valueStyle={{ color: '#fa8c16', fontSize: 18 }} />
              </Col>
              <Col span={6}>
                <Statistic title="当月利息" value={kpi.liability.interest} precision={2} suffix="亿元"
                  valueStyle={{ color: '#722ed1', fontSize: 18 }} />
              </Col>
            </Row>
          </div>

          <Divider style={{ margin: '4px 0 12px' }} />

          {/* 权益 + 合计 */}
          <Row gutter={16}>
            <Col span={12}>
              <Space style={{ marginBottom: 8 }}>
                <Tag color="purple" style={{ marginInlineEnd: 0 }}>权益</Tag>
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>{kpi.equity.count} 个节点</span>
              </Space>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic title="当前余额" value={kpi.equity.current} precision={2} suffix="亿元"
                    valueStyle={{ color: '#722ed1', fontSize: 16 }} />
                </Col>
                <Col span={8}>
                  <Statistic title="平均余额" value={kpi.equity.avg} precision={2} suffix="亿元"
                    valueStyle={{ fontSize: 16 }} />
                </Col>
                <Col span={8}>
                  <Statistic title="当月利息" value={kpi.equity.interest} precision={2} suffix="亿元"
                    valueStyle={{ fontSize: 16 }} />
                </Col>
              </Row>
            </Col>
            <Col span={12}>
              <Space style={{ marginBottom: 8 }}>
                <Tag style={{ marginInlineEnd: 0 }}>全部合计</Tag>
                <Tooltip title="合计 = 资产 + 负债 + 权益，正常情况下资产 ≠ 负债+权益，差额来自基础数据口径">
                  <InfoCircleOutlined style={{ color: '#999' }} />
                </Tooltip>
              </Space>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic title="当前余额" value={kpi.total.current} precision={2} suffix="亿元"
                    valueStyle={{ fontSize: 16, fontWeight: 600 }} />
                </Col>
                <Col span={8}>
                  <Statistic title="平均余额" value={kpi.total.avg} precision={2} suffix="亿元"
                    valueStyle={{ fontSize: 16, fontWeight: 600 }} />
                </Col>
                <Col span={8}>
                  <Statistic title="当月利息" value={kpi.total.interest} precision={2} suffix="亿元"
                    valueStyle={{ fontSize: 16, fontWeight: 600 }} />
                </Col>
              </Row>
            </Col>
          </Row>

          {/* 资产负债差额提示 */}
          {Math.abs(kpi.balanceDiff) > 0.01 && (
            <Alert
              type="warning" showIcon
              style={{ marginTop: 12 }}
              message={
                <span style={{ fontSize: 12 }}>
                  资产 {kpi.asset.current.toFixed(2)} − 负债 {kpi.liability.current.toFixed(2)}
                  {' '}− 权益 {kpi.equity.current.toFixed(2)} ={' '}
                  <strong>{kpi.balanceDiff.toFixed(2)} 亿元</strong>
                  （差额来自基础数据口径，非本引擎计算误差）
                </span>
              }
            />
          )}
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
              <Space size={8} wrap>
                <span style={{ fontSize: 12, color: '#666' }}>月份</span>
                <Select
                  size="small"
                  style={{ width: 160 }}
                  value={activeMonthTab}
                  onChange={setActiveMonthTab}
                  placeholder="选择月份"
                  options={Array.from(
                    { length: selectedNodeResults.length || currentRun?.month_count || 60 },
                    (_, i) => i + 1
                  ).map((m) => ({
                    value: String(m),
                    label: `M${m}（${selectedNodeResults[m - 1]?.data_date?.slice(5) || '-'}）`,
                  }))}
                />
                <span style={{ fontSize: 12, color: '#666' }}>类别</span>
                <Select
                  size="small"
                  style={{ width: 100 }}
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
                <span style={{ fontSize: 12, color: '#666' }}>表头</span>
                <Select
                  size="small"
                  style={{ width: 130 }}
                  value={activeColumnGroup}
                  onChange={(v) => setActiveColumnGroup(v as any)}
                  options={[
                    { value: 'measure', label: '度量' },
                    { value: 'original', label: '原始期限金额' },
                    { value: 'remaining', label: '剩余期限金额' },
                    { value: 'all', label: '全部（度量置左）' },
                  ]}
                />
                <Button size="small" icon={<ReloadOutlined />} onClick={() => loadResults(activeRun)}>
                  刷新
                </Button>
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
                  {/* 节点级 KPI（跟随顶部月份下拉） */}
                  <Row gutter={16} style={{ marginBottom: 12 }}>
                    <Col span={6}>
                      <Statistic
                        title={`M${activeMonthTab} 当前余额（${selectedMeta?.node_code || '-'}）`}
                        value={currentMonthRow?.current_balance || 0}
                        precision={2}
                        valueStyle={{ color: '#2f54eb', fontSize: 16 }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={`M${activeMonthTab} 平均余额`}
                        value={currentMonthRow?.avg_balance || 0}
                        precision={2}
                        valueStyle={{ color: '#52c41a', fontSize: 16 }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={`M${activeMonthTab} 加权利率`}
                        value={currentMonthRow?.weighted_rate || 0}
                        precision={4}
                        suffix="%"
                        valueStyle={{ color: '#fa8c16', fontSize: 16 }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={`M${activeMonthTab} 当月利息`}
                        value={currentMonthRow?.interest_amount || 0}
                        precision={2}
                        valueStyle={{ color: '#722ed1', fontSize: 16 }}
                      />
                    </Col>
                  </Row>

                  {/* 当前月份快照表格（月份通过顶部下拉切换） */}
                  <div style={{ marginBottom: 8, fontSize: 12, color: '#666' }}>
                    当前展示：<Tag color="purple" style={{ margin: '0 4px' }}>M{activeMonthTab}</Tag>
                    <span style={{ fontFamily: 'monospace' }}>{currentMonthRow?.data_date || '-'}</span>
                    <span style={{ marginLeft: 12 }}>表头模式：</span>
                    <Tag color="blue" style={{ margin: '0 4px' }}>
                      {activeColumnGroup === 'measure' && '度量（4 项）'}
                      {activeColumnGroup === 'original' && '原始期限金额（64 桶）'}
                      {activeColumnGroup === 'remaining' && '剩余期限金额（64 桶）'}
                      {activeColumnGroup === 'all' && '全部（度量置左 + 原始 + 剩余）'}
                    </Tag>
                    <span style={{ marginLeft: 12, color: '#999' }}>
                      节点共 {monthTableData.length} 行
                    </span>
                  </div>
                  <Table
                    rowKey={(record: ResultRow) => `${currentMonthRow?.run_id || 0}-${currentMonthRow?.date_offset || 0}-${record.coa_node_id}`}
                    columns={monthTableColumns}
                    dataSource={monthTableData}
                    size="small"
                    pagination={false}
                    scroll={{
                      x: activeColumnGroup === 'measure' ? 700
                        : activeColumnGroup === 'original' ? 3460
                        : activeColumnGroup === 'remaining' ? 3460
                        : 7100,
                      y: 400,
                    }}
                    bordered
                    style={{ background: '#fafafa' }}
                  />
                </>
              )}
            </Spin>
          </Card>
        </Col>
      </Row>

      {/* ==================== v2.1 投放节奏展示区（页面底部） ==================== */}
      {hasRhythmData && (
        <Card
          style={{ marginTop: 16 }}
          title={
            <Space>
              <ThunderboltOutlined style={{ color: '#fa8c16' }} />
              <span>投放节奏</span>
              <Tag color="orange">{growthTypeLabel}</Tag>
              <Tooltip title="数据来自新业务生成计量逻辑：增长配置（年目标） → 节奏配置（12 月权重） → 期限占比（到期落点） → 逐月滚动">
                <InfoCircleOutlined style={{ color: '#999' }} />
              </Tooltip>
            </Space>
          }
          size="small"
        >
          {/* KPI 概览 */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Statistic
                title="累计新增投放"
                value={toYi(rhythmRows[rhythmRows.length - 1]?.cumAdd || 0)?.toFixed(2)}
                suffix="亿元"
                valueStyle={{ color: '#13c2c2', fontSize: 20 }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="累计到期释放"
                value={toYi(rhythmRows.reduce((a, r) => a + r.release, 0))?.toFixed(2)}
                suffix="亿元"
                valueStyle={{ color: '#8c8c8c', fontSize: 20 }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="覆盖月份"
                value={rhythmRows.length}
                suffix="个月"
                valueStyle={{ color: '#722ed1', fontSize: 20 }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="测算节点"
                value={new Set(
                  results.filter(r => r.is_configured && !r.is_aggregated).map(r => r.coa_node_id)
                ).size}
                suffix="个末级节点"
                valueStyle={{ color: '#fa8c16', fontSize: 20 }}
              />
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={16}>
              <Card size="small" type="inner" title="月度投放分解（当月新增 vs 当月到期 vs 累计）"
                bodyStyle={{ padding: 8 }}>
                <ReactECharts option={rhythmTrendOpt} style={{ height: 300 }} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="12 个月节奏权重（跨年复用）"
                bodyStyle={{ padding: 8 }}>
                <ReactECharts option={rhythmWeightOpt} style={{ height: 300 }} />
              </Card>
            </Col>
          </Row>

          <Card size="small" type="inner" title="年度投放汇总" style={{ marginTop: 16 }}>
            <Table
              size="small"
              rowKey="y"
              dataSource={yearlyRows}
              pagination={false}
              columns={yearlyCols}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
              口径说明：净增长类方式（目标增长百分比 / 目标增长绝对值 / 增长值）当月投放 = 到期释放 + 新增，
              保证余额净增长；毛投放类（增长百分比）当月投放 = 新增，到期自然出表。
            </div>
          </Card>
        </Card>
      )}
    </div>
  )
}

export default SimResultPage

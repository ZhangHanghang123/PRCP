/** 新业务模拟 — 结果查看页
 *
 * 入口：/sim/results/:sim_scheme_code（从方案列表「查看结果」按钮跳转）
 * 布局：左侧账户册 DirectoryTree（仅显示引擎跑过的节点）
 *      + 右侧选中节点的 24 月快照 Tabs（每 Tab 一个节点 × 64+64 桶二级表头表格）
 *
 * 顶部：方案下拉 + Run 选择 + 4 全局 KPI 汇总
 * 主体：左 7 列账户册树 + 右 17 列节点 24 月快照
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

  // 单月快照数据：1 行 = 当前选中节点 × 当前选中月份
  const currentMonthRow = useMemo(() => {
    return selectedNodeResults.find(r => r.date_offset === Number(activeMonthTab)) || null
  }, [selectedNodeResults, activeMonthTab])

  // 二级表头：原始期限（#13c2c2 青）+ 剩余期限（#722ed1 紫）+ 度量（#eb2f96 粉）
  const monthTableColumns: ColumnsType<any> = useMemo(() => {
    const baseCol: ColumnsType<any>[number] = {
      title: '账户册节点',
      key: 'node',
      fixed: 'left',
      width: 200,
      render: () => currentMonthRow ? (
        <span>
          <code style={{
            fontSize: 11,
            background: currentMonthRow.is_configured ? '#f6ffed' : '#f5f5f5',
            color: currentMonthRow.is_configured ? '#52c41a' : '#262626',
            fontWeight: currentMonthRow.is_configured ? 600 : 400,
            padding: '1px 4px',
            borderRadius: 3,
            border: currentMonthRow.is_configured ? '1px solid #b7eb8f' : 'none',
          }}>
            {currentMonthRow.node_code}
          </code>
          <div style={{
            fontSize: 12,
            marginTop: 2,
            color: currentMonthRow.is_configured ? '#52c41a' : '#262626',
            fontWeight: currentMonthRow.is_configured ? 500 : 400,
          }}>
            {currentMonthRow.node_name}
            {currentMonthRow.is_configured && (
              <Tag color="green" style={{ marginLeft: 4, fontSize: 10, padding: '0 3px', lineHeight: '14px' }}>
                ⚡ 已配置
              </Tag>
            )}
            {currentMonthRow.is_aggregated && (
              <Tag style={{ marginLeft: 4, fontSize: 10, padding: '0 3px', lineHeight: '14px', color: '#595959', borderColor: '#bfbfbf' }}>
                📊 汇总
              </Tag>
            )}
            {!currentMonthRow.is_configured && !currentMonthRow.is_aggregated && (
              <Tag style={{ marginLeft: 4, fontSize: 10, padding: '0 3px', lineHeight: '14px', color: '#888' }}>
                🔄 仅滚动
              </Tag>
            )}
          </div>
        </span>
      ) : '-',
    }
    const origGroup = {
      title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>原始期限金额（{currentMonthRow?.data_date || '-'}）</span>,
      children: BUCKETS.map((b) => ({
        title: <span style={{ fontSize: 12, color: '#13c2c2' }}>{b.name}</span>,
        key: `orig_${b.key}`,
        width: b.width,
        align: 'right' as const,
        onHeaderCell: () => ({ style: { background: '#fafafa' } }),
        render: () => {
          if (!currentMonthRow) return <span style={{ color: '#ccc' }}>-</span>
          const v = currentMonthRow[`orig_${b.key}`]
          if (v === undefined || v === null) return <span style={{ color: '#ccc' }}>-</span>
          if (Math.abs(v) < 0.005) return <span style={{ color: '#bbb' }}>·</span>
          return <span style={{ color: '#13c2c2', fontFamily: 'monospace' }}>{(v as number).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
        },
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
        render: () => {
          if (!currentMonthRow) return <span style={{ color: '#ccc' }}>-</span>
          const v = currentMonthRow[`rem_${b.key}`]
          if (v === undefined || v === null) return <span style={{ color: '#ccc' }}>-</span>
          if (Math.abs(v) < 0.005) return <span style={{ color: '#bbb' }}>·</span>
          return <span style={{ color: '#722ed1', fontFamily: 'monospace' }}>{(v as number).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
        },
      })),
    }
    const measureGroup = {
      title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>度量</span>,
      children: [
        { title: '当前余额', key: 'current_balance', width: 110, align: 'right' as const,
          onHeaderCell: () => ({ style: { background: '#fafafa' } }),
          render: () => currentMonthRow ? <strong style={{ color: '#2f54eb' }}>{(currentMonthRow.current_balance || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong> : '-' },
        { title: '平均余额', key: 'avg_balance', width: 110, align: 'right' as const,
          onHeaderCell: () => ({ style: { background: '#fafafa' } }),
          render: () => currentMonthRow ? (currentMonthRow.avg_balance || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-' },
        { title: '加权利率', key: 'weighted_rate', width: 85, align: 'right' as const,
          onHeaderCell: () => ({ style: { background: '#fafafa' } }),
          render: () => currentMonthRow ? <span style={{ color: '#fa8c16' }}>{(currentMonthRow.weighted_rate || 0).toFixed(4)}%</span> : '-' },
        { title: '当月利息', key: 'interest_amount', width: 100, align: 'right' as const,
          onHeaderCell: () => ({ style: { background: '#fafafa' } }),
          render: () => currentMonthRow ? (currentMonthRow.interest_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-' },
      ],
    }
    return [baseCol, origGroup, remGroup, measureGroup] as any
  }, [currentMonthRow])

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
                <span>节点 24 月快照</span>
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
                          rowKey={() => r.id}
                          columns={monthTableColumns}
                          dataSource={[r]}
                          size="small"
                          pagination={false}
                          scroll={{ x: 7700, y: null }}
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

/** 新业务模拟 — 结果查看页
 *
 * 入口：/sim/results/:sim_scheme_code（从方案列表「查看结果」按钮跳转）
 * 布局：左侧账户册 DirectoryTree（仅显示引擎跑过的节点）
 *      + 右侧选中节点的 24 月快照 Tabs
 *
 * 顶部：方案下拉 + Run 选择 + 4 KPI 汇总
 * 主体：左 320px 树 + 右 节点结果 Tabs
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
  current_balance: number
  avg_balance: number
  weighted_rate: number
  interest_amount: number
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
  const [coaSchemeId, setCoaSchemeId] = useState<number | null>(null)

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

  const loadResults = async (runId: number | null) => {
    if (!runId) { setResults([]); return }
    setLoading(true)
    try {
      const r = await simApi.listResults({ run_id: runId, category })
      setResults(r.items || [])
    } catch (e: any) {
      message.error('结果加载失败')
    } finally {
      setLoading(false)
    }
  }

  // 加载账户册树（基于方案的 coa_scheme_id）
  const loadCoaTree = async (sid: number) => {
    try {
      const t = await simApi.coaTree(sid)
      setCoaSchemeId(sid)
      // 将 API 返回的 items 转为 antd DataNode
      const toDataNode = (n: any): DataNode => ({
        key: String(n.id),
        title: (
          <span>
            <code style={{ fontSize: 11, color: '#888' }}>{n.code}</code>
            {' '}{n.title}
          </span>
        ),
        icon: n.isLeaf ? <FileTextOutlined /> : <FolderOutlined />,
        isLeaf: n.isLeaf,
        children: n.children?.map(toDataNode),
      })
      setTreeData((t.items || []).map(toDataNode))
      // 默认展开所有 L1/L2 节点
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

  useEffect(() => { loadSchemes() }, [])
  useEffect(() => {
    if (schemeCode) loadRuns(schemeCode)
  }, [schemeCode])
  useEffect(() => { loadResults(activeRun) }, [activeRun, category])

  // 加载账户册树：取当前方案的 coa_scheme_id
  useEffect(() => {
    const s = schemes.find(x => x.scheme_code === schemeCode)
    if (s?.coa_scheme_id) loadCoaTree(s.coa_scheme_id)
  }, [schemes, schemeCode])

  // =================== 派生数据 ===================

  const currentScheme = schemes.find(s => s.scheme_code === schemeCode)
  const currentRun = runs.find(r => r.id === activeRun)

  // 引擎跑过的节点 ID 集合（用于高亮树节点）
  const runnedNodeIds = useMemo(() => {
    return new Set(results.map(r => r.coa_node_id))
  }, [results])

  // 引擎跑过的节点 ID → 节点元数据映射
  const runnedNodeMap = useMemo(() => {
    const m = new Map<number, ResultRow>()
    for (const r of results) {
      if (!m.has(r.coa_node_id)) m.set(r.coa_node_id, r)
    }
    return m
  }, [results])

  // 顶部 KPI（全部节点的当前/平均余额汇总）
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

  // 默认选第一个跑过的节点
  useEffect(() => {
    if (selectedNodeId === null && runnedNodeIds.size > 0) {
      const first = results.find(r => r.coa_node_id && runnedNodeIds.has(r.coa_node_id))
      if (first) setSelectedNodeId(first.coa_node_id)
    }
  }, [results, runnedNodeIds])

  // 自定义树渲染：跑过的节点加 Tag 标记
  const renderTreeTitle = (node: any) => {
    const id = Number(node.key)
    const runned = runnedNodeIds.has(id)
    return (
      <span style={{ fontSize: 13 }}>
        {node.title}
        {runned && (
          <Tag color="purple" style={{ marginLeft: 6, fontSize: 10, padding: '0 4px', lineHeight: '14px' }}>
            ⚡ 已模拟
          </Tag>
        )}
      </span>
    )
  }

  // =================== 表格列 ===================

  const columns: ColumnsType<ResultRow> = [
    {
      title: '月份', dataIndex: 'date_offset', width: 80, fixed: 'left',
      render: (v: number) => <Tag color="blue">M{v}</Tag>,
    },
    {
      title: '日期', dataIndex: 'data_date', width: 110,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</span>,
    },
    {
      title: '当前余额', dataIndex: 'current_balance', width: 160,
      align: 'right' as const,
      render: (v: number) => v ? <strong style={{ color: '#2f54eb' }}>{v.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}</strong> : '-',
    },
    {
      title: '平均余额', dataIndex: 'avg_balance', width: 150,
      align: 'right' as const,
      render: (v: number) => v ? v.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '-',
    },
    {
      title: '加权平均利率(%)', dataIndex: 'weighted_rate', width: 140,
      align: 'right' as const,
      render: (v: number) => v ? <span style={{ color: '#fa8c16' }}>{v.toFixed(4)}</span> : '-',
    },
    {
      title: '当月利息', dataIndex: 'interest_amount', width: 140,
      align: 'right' as const,
      render: (v: number) => v ? v.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '-',
    },
    {
      title: '类别', dataIndex: 'category', width: 90,
      render: (v: string) => v ? <Tag color={v === 'ASSET' ? 'blue' : v === 'LIABILITY' ? 'orange' : 'default'}>{v}</Tag> : '-',
    },
  ]

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
            <Col span={4}>
              <Statistic title="Run ID" value={currentRun.id} prefix={<LineChartOutlined style={{ color: '#722ed1' }} />} />
            </Col>
            <Col span={4}>
              <Statistic title="状态" value={currentRun.status}
                valueStyle={{ color: currentRun.status === 'SUCCESS' ? '#52c41a' : '#f5222d' }} />
            </Col>
            <Col span={4}>
              <Statistic title="节点数" value={currentRun.total_nodes} />
            </Col>
            <Col span={4}>
              <Statistic title="生成月份" value={currentRun.month_count} />
            </Col>
            <Col span={4}>
              <Statistic title="耗时" value={currentRun.duration_ms || '-'} suffix="ms" />
            </Col>
            <Col span={4}>
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

      {/* KPI 汇总（全节点） */}
      {kpi && (
        <Card size="small" style={{ marginTop: 12, background: '#f0f5ff' }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="汇总当前余额" value={kpi.total_current} precision={2} valueStyle={{ color: '#2f54eb' }} />
            </Col>
            <Col span={6}>
              <Statistic title="汇总平均余额" value={kpi.total_avg} precision={2} valueStyle={{ color: '#52c41a' }} />
            </Col>
            <Col span={6}>
              <Statistic title="加权平均利率" value={kpi.avg_wr} precision={4} suffix="%" valueStyle={{ color: '#fa8c16' }} />
            </Col>
            <Col span={6}>
              <Statistic title="汇总当月利息" value={kpi.total_interest} precision={2} valueStyle={{ color: '#722ed1' }} />
            </Col>
          </Row>
        </Card>
      )}

      {/* 主体：左树 + 右结果 */}
      <Row gutter={12} style={{ marginTop: 12 }}>
        {/* 左侧账户册树 */}
        <Col span={7}>
          <Card
            size="small"
            title={
              <Space>
                <ApartmentOutlined style={{ color: '#722ed1' }} />
                <span>账户册节点</span>
                {runnedNodeIds.size > 0 && (
                  <Tag color="purple" style={{ marginLeft: 4 }}>
                    已模拟 {runnedNodeIds.size} / {treeData.length > 0 ? '...' : '?'}
                  </Tag>
                )}
              </Space>
            }
            bodyStyle={{ padding: 8, maxHeight: 'calc(100vh - 380px)', overflowY: 'auto' }}
          >
            {treeData.length === 0 ? (
              <Empty description="加载账户册..." imageStyle={{ height: 60 }} />
            ) : (
              <Tree
                treeData={treeData}
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
                titleRender={renderTreeTitle as any}
                showLine={{ showLeafIcon: false }}
                blockNode
              />
            )}
          </Card>
        </Col>

        {/* 右侧节点结果 */}
        <Col span={17}>
          <Card
            size="small"
            title={
              <Space>
                <span>节点结果快照</span>
                {selectedMeta ? (
                  <Space size={6} style={{ fontWeight: 'normal' }}>
                    <Tag color="purple">{selectedMeta.node_code}</Tag>
                    <span style={{ fontSize: 13 }}>{selectedMeta.node_name}</span>
                    <Tag color={selectedMeta.category === 'ASSET' ? 'blue' : selectedMeta.category === 'LIABILITY' ? 'orange' : 'default'}>
                      {selectedMeta.category}
                    </Tag>
                    <Tag color="cyan">L{selectedMeta.node_level}</Tag>
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
                <Empty description="请选择左侧已模拟的账户册节点" />
              ) : selectedNodeResults.length === 0 ? (
                <Empty description="该节点无结果数据" />
              ) : (
                <>
                  {/* 节点级 KPI */}
                  <Row gutter={16} style={{ marginBottom: 12 }}>
                    <Col span={6}>
                      <Statistic
                        title={`M1 当前余额（${selectedNodeResults[0]?.data_date}）`}
                        value={selectedNodeResults[0]?.current_balance || 0}
                        precision={2}
                        valueStyle={{ color: '#2f54eb', fontSize: 16 }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={`M${selectedNodeResults.length} 当前余额（${selectedNodeResults[selectedNodeResults.length-1]?.data_date}）`}
                        value={selectedNodeResults[selectedNodeResults.length-1]?.current_balance || 0}
                        precision={2}
                        valueStyle={{ color: '#52c41a', fontSize: 16 }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={`M${selectedNodeResults.length} 加权利率`}
                        value={selectedNodeResults[selectedNodeResults.length-1]?.weighted_rate || 0}
                        precision={4}
                        suffix="%"
                        valueStyle={{ color: '#fa8c16', fontSize: 16 }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={`累计利息（${selectedNodeResults.length} 月）`}
                        value={selectedNodeResults.reduce((a, r) => a + (r.interest_amount || 0), 0)}
                        precision={2}
                        valueStyle={{ color: '#722ed1', fontSize: 16 }}
                      />
                    </Col>
                  </Row>

                  {/* 24 月快照表格 */}
                  <Table
                    rowKey={(r) => `${r.run_id}-${r.coa_node_id}-${r.date_offset}`}
                    columns={columns}
                    dataSource={selectedNodeResults}
                    size="small"
                    pagination={{ pageSize: 24, showSizeChanger: false }}
                    scroll={{ x: 900 }}
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

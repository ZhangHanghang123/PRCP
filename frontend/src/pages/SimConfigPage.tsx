/** 新业务模拟方案 — 参数配置页
 *
 * 入口：/sim/config/:scheme_id
 * 功能：左侧账户册树 + 右侧节点参数配置（年化增长 + 期限占比子表）
 */
import React, { useEffect, useMemo, useState, useCallback } from 'react'
import {
  Card, Tree, Form, Input, InputNumber, Button, Table, Space, Tag, message,
  Modal, Row, Col, Statistic, Alert, Popconfirm, Empty, Spin, Tooltip,
} from 'antd'
import {
  ArrowLeftOutlined, SaveOutlined, ReloadOutlined, PlusOutlined,
  DeleteOutlined, FolderOutlined, FileTextOutlined, CheckCircleOutlined,
  ExclamationCircleOutlined, ApartmentOutlined,
} from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import type { ColumnsType } from 'antd/es/table'
import { useParams, useNavigate } from 'react-router-dom'
import { simApi } from '../api'

interface RatioRow {
  key?: string
  term_value: number
  term_unit: 'MONTH'
  business_ratio: number
  sort_order: number
}

const SimConfigPage: React.FC = () => {
  const params = useParams()
  const navigate = useNavigate()
  const schemeId = Number(params.scheme_id)

  // ============== 基础状态 ==============
  const [scheme, setScheme] = useState<any>(null)
  const [tree, setTree] = useState<DataNode[]>([])
  const [treeRaw, setTreeRaw] = useState<any[]>([])  // 原始树（含 children）
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null)
  const [selectedNodeInfo, setSelectedNodeInfo] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [treeLoading, setTreeLoading] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])

  // ============== 配置面板状态 ==============
  const [annualGrowthRate, setAnnualGrowthRate] = useState<number>(0)
  const [ratios, setRatios] = useState<RatioRow[]>([])
  const [configId, setConfigId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [loadingConfig, setLoadingConfig] = useState(false)

  // ============== 数据加载 ==============
  // 加载方案基础信息
  const loadScheme = useCallback(async () => {
    try {
      const r = await simApi.listSchemes()
      const found = (r.items || []).find((s: any) => s.id === schemeId)
      if (!found) {
        message.error('方案不存在或已被删除')
        navigate('/sim/list')
        return
      }
      setScheme(found)
    } catch (e: any) {
      message.error('方案加载失败')
    }
  }, [schemeId, navigate])

  // 加载账户册树
  const loadTree = useCallback(async (coaSchemeId: number) => {
    setTreeLoading(true)
    try {
      const r = await simApi.coaTree(coaSchemeId)
      const raw = r.items || []
      setTreeRaw(raw)
      setTree(raw as DataNode[])
      // 默认全展开
      const allKeys = collectKeys(raw)
      setExpandedKeys(allKeys)
    } catch (e: any) {
      message.error('账户册树加载失败')
    } finally {
      setTreeLoading(false)
    }
  }, [])

  const collectKeys = (nodes: any[]): React.Key[] => {
    const out: React.Key[] = []
    const walk = (ns: any[]) => {
      for (const n of ns) {
        out.push(n.key)
        if (n.children?.length) walk(n.children)
      }
    }
    walk(nodes)
    return out
  }

  useEffect(() => {
    if (!schemeId) return
    loadScheme()
  }, [schemeId, loadScheme])

  useEffect(() => {
    if (scheme?.coa_scheme_id) loadTree(scheme.coa_scheme_id)
  }, [scheme, loadTree])

  // ============== 节点选择 ==============
  const findNodeRaw = (nodes: any[], id: number): any => {
    for (const n of nodes) {
      if (n.id === id) return n
      if (n.children?.length) {
        const c = findNodeRaw(n.children, id)
        if (c) return c
      }
    }
    return null
  }

  const loadNodeConfig = useCallback(async (coaNodeId: number) => {
    setLoadingConfig(true)
    try {
      const r = await simApi.getNodeConfig(schemeId, coaNodeId)
      if (r.exists && r.config) {
        setAnnualGrowthRate(r.config.annual_growth_rate || 0)
        setRatios((r.ratios || []).map((row: any, idx: number) => ({
          key: `db-${row.id || idx}`,
          term_value: row.term_value,
          term_unit: 'MONTH' as const,
          business_ratio: row.business_ratio,
          sort_order: row.sort_order || idx + 1,
        })))
        setConfigId(r.config.id)
      } else {
        // 未配置 → 默认值
        setAnnualGrowthRate(0)
        setRatios([])
        setConfigId(null)
      }
      setDirty(false)
    } catch (e: any) {
      message.error('节点配置加载失败')
    } finally {
      setLoadingConfig(false)
    }
  }, [schemeId])

  const loadNodeInfo = useCallback(async (coaNodeId: number) => {
    try {
      const r = await simApi.nodeInfo(coaNodeId)
      setSelectedNodeInfo(r)
    } catch {
      setSelectedNodeInfo(null)
    }
  }, [])

  const handleSelectNode = (keys: React.Key[]) => {
    if (!keys.length) return
    const doSwitch = async () => {
      const id = Number(keys[0])
      setSelectedNodeId(id)
      loadNodeInfo(id)
      loadNodeConfig(id)
    }
    if (dirty) {
      Modal.confirm({
        title: '放弃当前修改？',
        content: '当前节点有未保存的修改，切换节点将丢失。',
        okText: '放弃修改', cancelText: '继续编辑',
        onOk: () => { setDirty(false); doSwitch() },
      })
    } else {
      doSwitch()
    }
  }

  // ============== 子表操作 ==============
  const addRatioRow = () => {
    const used = new Set(ratios.map(r => r.term_value))
    let next = 1
    while (used.has(next) && next <= 60) next++
    if (next > 60) {
      message.warning('期限值范围 1~60 月，无法新增')
      return
    }
    setRatios([...ratios, {
      key: `new-${Date.now()}-${next}`,
      term_value: next, term_unit: 'MONTH', business_ratio: 0, sort_order: ratios.length + 1,
    }])
    setDirty(true)
  }

  const removeRatioRow = (idx: number) => {
    setRatios(ratios.filter((_, i) => i !== idx))
    setDirty(true)
  }

  const updateRatioRow = (idx: number, key: keyof RatioRow, value: any) => {
    const next = [...ratios]
    ;(next[idx] as any)[key] = value
    setRatios(next)
    setDirty(true)
  }

  // 求和校验
  const ratioSum = useMemo(() => {
    return ratios.reduce((a, r) => a + (Number(r.business_ratio) || 0), 0)
  }, [ratios])
  const isSumValid = Math.abs(ratioSum - 100) < 0.01

  // ============== 保存 ==============
  const handleSave = async () => {
    if (!selectedNodeId) return
    // 校验：业务占比之和必须=100%
    if (ratios.length === 0) {
      message.error('期限占比子表不能为空')
      return
    }
    if (!isSumValid) {
      message.error(`业务占比之和必须为 100%，当前 = ${ratioSum.toFixed(4)}%`)
      return
    }
    // 校验：期限值在 1~60
    for (const r of ratios) {
      if (r.term_value < 1 || r.term_value > 60) {
        message.error(`期限值 ${r.term_value} 超出 1~60 月范围`)
        return
      }
    }
    setSaving(true)
    try {
      const payload = {
        coa_node_id: selectedNodeId,
        annual_growth_rate: annualGrowthRate,
        term_unit: 'MONTH',
        ratios: ratios.map((r, idx) => ({
          term_value: r.term_value,
          term_unit: 'MONTH',
          business_ratio: r.business_ratio,
          sort_order: idx + 1,
        })),
      }
      const r = await simApi.saveNodeConfig(schemeId, payload)
      message.success(`已保存（${r.term_count} 行，占比之和=${r.total_ratio}%）`)
      setConfigId(r.config_id)
      setDirty(false)
      // 刷新方案基础信息（config_node_count 会变）
      loadScheme()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setAnnualGrowthRate(0)
    setRatios([])
    setDirty(true)
  }

  const handleResetFromDB = async () => {
    if (!selectedNodeId) return
    loadNodeConfig(selectedNodeId)
  }

  // ============== 子表列定义 ==============
  const ratioColumns: ColumnsType<RatioRow> = [
    {
      title: '序号', width: 60, align: 'center',
      render: (_: any, _r: any, idx: number) => idx + 1,
    },
    {
      title: (
        <Space size={4}>
          期限值
          <Tooltip title="1~60 月（与 64 桶期限桶 m1~m60 对应；超过 60 用长端 5年+）">
            <ExclamationCircleOutlined style={{ color: '#999' }} />
          </Tooltip>
        </Space>
      ),
      dataIndex: 'term_value', width: 120,
      render: (v: number, _r: any, idx: number) => (
        <InputNumber
          min={1} max={60} value={v}
          onChange={(val) => updateRatioRow(idx, 'term_value', val || 1)}
          addonAfter="月" style={{ width: '100%' }}
        />
      ),
    },
    {
      title: '期限单位', dataIndex: 'term_unit', width: 100,
      render: () => <Tag color="blue" icon={<FileTextOutlined />}>月（固定）</Tag>,
    },
    {
      title: (
        <Space size={4}>
          业务占比
          <Tooltip title="百分比 0~100，所有行之和必须 = 100%">
            <ExclamationCircleOutlined style={{ color: '#999' }} />
          </Tooltip>
        </Space>
      ),
      dataIndex: 'business_ratio', width: 140,
      render: (v: number, _r: any, idx: number) => (
        <InputNumber
          min={0} max={100} step={0.01} precision={4}
          value={v}
          onChange={(val) => updateRatioRow(idx, 'business_ratio', val || 0)}
          addonAfter="%" style={{ width: '100%' }}
        />
      ),
    },
    {
      title: '操作', width: 80, fixed: 'right',
      render: (_: any, _r: any, idx: number) => (
        <Popconfirm title="删除该行？" onConfirm={() => removeRatioRow(idx)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      ),
    },
  ]

  // ============== 当前选中节点 ==============
  const selectedNode = useMemo(() => {
    if (!selectedNodeId || !treeRaw.length) return null
    return findNodeRaw(treeRaw, selectedNodeId)
  }, [selectedNodeId, treeRaw])

  return (
    <div className="page-container">
      {/* 顶部标题栏 */}
      <Card
        size="small"
        title={
          <Space>
            <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => navigate('/sim/list')} style={{ paddingLeft: 0 }}>
              返回方案列表
            </Button>
            <span style={{ color: '#999' }}>|</span>
            <ApartmentOutlined style={{ color: '#722ed1' }} />
            <span>参数配置</span>
            {scheme && (
              <Space size={8} style={{ fontWeight: 'normal', fontSize: 13 }}>
                <Tag color="purple">{scheme.scheme_code}</Tag>
                <span>{scheme.scheme_name}</span>
                <span style={{ color: '#999' }}>·</span>
                <span>关联账户册：</span>
                <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 3 }}>
                  {scheme.coa_scheme_code} | {scheme.coa_scheme_name}
                </code>
                <Tag color={scheme.status === 'ACTIVE' ? 'green' : 'default'}>{scheme.status}</Tag>
              </Space>
            )}
          </Space>
        }
      />

      {/* 左右栏布局 */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        {/* 左侧：账户册树 */}
        <Col span={8}>
          <Card
            title={
              <Space>
                <FolderOutlined />
                <span>账户册节点</span>
                <Tag color="blue">{treeRaw.length} 节点</Tag>
              </Space>
            }
            size="small"
            bodyStyle={{ padding: 8, maxHeight: 'calc(100vh - 280px)', overflow: 'auto' }}
          >
            <Spin spinning={treeLoading}>
              {tree.length === 0 ? (
                <Empty description="无节点数据" />
              ) : (
                <Tree
                  treeData={tree}
                  showLine={{ showLeafIcon: false }}
                  expandedKeys={expandedKeys as string[]}
                  onExpand={(keys) => setExpandedKeys(keys)}
                  selectedKeys={selectedNodeId ? [String(selectedNodeId)] : []}
                  onSelect={(keys) => handleSelectNode(keys)}
                  blockNode
                  titleRender={(node: any) => {
                    const isLeaf = node.isLeaf || (!node.children?.length)
                    const isSelected = selectedNodeId === node.id
                    return (
                      <Space size={6} style={{
                        fontWeight: isLeaf ? 'normal' : 600,
                        color: isLeaf ? '#333' : '#2f54eb',
                        width: '100%',
                      }}>
                        {isLeaf ? <FileTextOutlined /> : <FolderOutlined />}
                        <span>{node.title}</span>
                        {isLeaf && (
                          <Tag color={isSelected ? 'gold' : 'default'} style={{ marginLeft: 'auto', fontSize: 11 }}>
                            L{node.level}
                          </Tag>
                        )}
                      </Space>
                    )
                  }}
                />
              )}
            </Spin>
            <Alert
              type="info" showIcon style={{ marginTop: 8, fontSize: 12 }}
              message="仅 L3+ 叶子节点可配置"
            />
          </Card>
        </Col>

        {/* 右侧：参数配置 */}
        <Col span={16}>
          <Card
            title={
              <Space>
                <SettingOutlined style={{ color: '#722ed1' }} />
                <span>节点参数配置</span>
                {selectedNode && (
                  <Tag color="cyan">{selectedNode.code}</Tag>
                )}
              </Space>
            }
            size="small"
            extra={
              selectedNode && (
                <Space>
                  <Button icon={<ReloadOutlined />} onClick={handleResetFromDB}>重置</Button>
                  <Button
                    type="primary" icon={<SaveOutlined />} loading={saving}
                    disabled={!selectedNode || !isSumValid || ratios.length === 0}
                    onClick={handleSave}
                  >保存</Button>
                </Space>
              )
            }
            bodyStyle={{ minHeight: 'calc(100vh - 280px)' }}
          >
            {!selectedNode ? (
              <Empty description="请从左侧选择账户册节点" style={{ marginTop: 80 }} />
            ) : loadingConfig ? (
              <div style={{ textAlign: 'center', padding: 80 }}><Spin tip="加载中..." /></div>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size={16}>
                {/* 节点基础信息卡 */}
                <Card size="small" type="inner" title="节点基础信息" style={{ background: '#fafafa' }}>
                  <Row gutter={16}>
                    <Col span={6}>
                      <Statistic
                        title="节点编码"
                        value={selectedNodeInfo?.node_code || selectedNode.code || '-'}
                        valueStyle={{ fontSize: 14, fontFamily: 'monospace' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="节点名称"
                        value={selectedNodeInfo?.node_name || selectedNode.name || '-'}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="层级 / 类型"
                        value={`L${selectedNodeInfo?.node_level || selectedNode.level || '-'} · ${selectedNodeInfo?.node_type || selectedNode.type || 'LEAF'}`}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="当前余额（最新数据日期）"
                        value={selectedNodeInfo?.current_balance_amount ?? 0}
                        precision={2}
                        valueStyle={{ fontSize: 14, color: '#2f54eb' }}
                        suffix="元"
                      />
                    </Col>
                  </Row>
                </Card>

                {/* 上栏：年化目标增长比例 */}
                <Card
                  size="small" type="inner"
                  title={
                    <Space>
                      <span>上栏 · 新业务年化目标增长比例</span>
                      <Tooltip title="新业务规模每月相对于上月末余额的年化增长率（%）。例如：8.5% 表示新业务每月按 8.5%/12 线性增长">
                        <ExclamationCircleOutlined style={{ color: '#999' }} />
                      </Tooltip>
                    </Space>
                  }
                >
                  <Row gutter={16} align="middle">
                    <Col span={12}>
                      <InputNumber
                        min={0} max={100} step={0.01} precision={4}
                        value={annualGrowthRate}
                        onChange={(v) => { setAnnualGrowthRate(v || 0); setDirty(true) }}
                        addonAfter="%"
                        style={{ width: '100%' }}
                        placeholder="请输入年化目标增长率（0~100）"
                      />
                    </Col>
                    <Col span={12}>
                      <span style={{ color: '#666', fontSize: 13 }}>
                        💡 当前节点：<strong>{selectedNode.code}</strong>，
                        新业务规模每月增长 ≈ <code style={{ background: '#f5f5f5', padding: '1px 6px', borderRadius: 3 }}>
                          余额 × {(annualGrowthRate / 12).toFixed(4)}%
                        </code>
                      </span>
                    </Col>
                  </Row>
                </Card>

                {/* 下栏：期限占比子表 */}
                <Card
                  size="small" type="inner"
                  title={
                    <Space>
                      <span>下栏 · 新业务期限占比</span>
                      <Tag color="blue">月</Tag>
                      <span style={{ color: '#999', fontWeight: 'normal', fontSize: 12 }}>
                        期限单位固定为月；所有行占比之和必须 = 100%
                      </span>
                    </Space>
                  }
                  extra={
                    <Space>
                      <Tag color={isSumValid ? 'green' : 'red'}>
                        {isSumValid ? <><CheckCircleOutlined /> 占比之和 = </> : <><ExclamationCircleOutlined /> 占比之和 = </>}
                        {ratioSum.toFixed(4)}%
                      </Tag>
                      <Button icon={<PlusOutlined />} size="small" onClick={addRatioRow}>新增行</Button>
                    </Space>
                  }
                >
                  {ratios.length === 0 ? (
                    <Empty description="尚未配置期限占比，点击右上角「新增行」开始" />
                  ) : (
                    <Table
                      rowKey={(r) => r.key || `${r.term_value}-${r.sort_order}`}
                      columns={ratioColumns}
                      dataSource={ratios}
                      pagination={false}
                      size="small"
                      scroll={{ x: 600 }}
                      footer={() => (
                        <div style={{ textAlign: 'right' }}>
                          <Space>
                            <span>共 <strong>{ratios.length}</strong> 行</span>
                            <span style={{ color: isSumValid ? '#52c41a' : '#f5222d', fontWeight: 600 }}>
                              占比之和：{ratioSum.toFixed(4)}%
                              {isSumValid ? ' ✓ 100%' : ` ✗ 偏差 ${(ratioSum - 100).toFixed(4)}%`}
                            </span>
                          </Space>
                        </div>
                      )}
                    />
                  )}
                </Card>

                {/* 底部提示 */}
                {dirty && (
                  <Alert
                    type="warning" showIcon
                    message="当前有未保存的修改，请点击右上角「保存」按钮提交"
                  />
                )}
                {!dirty && configId && (
                  <Alert
                    type="success" showIcon
                    message={`已保存 · 配置 ID = ${configId}`}
                  />
                )}
              </Space>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default SimConfigPage

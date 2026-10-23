/** 新业务模拟方案 — 参数配置页
 *
 * 入口：/sim/config/:scheme_id
 * 功能：左侧账户册树 + 右侧节点参数配置（年化增长 + 期限占比子表）
 */
import React, { useEffect, useMemo, useState, useCallback } from 'react'
import {
  Card, Tree, Form, Input, InputNumber, Button, Table, Space, Tag, message,
  Modal, Row, Col, Statistic, Alert, Popconfirm, Empty, Spin, Tooltip,
  Radio, Progress,
} from 'antd'
import {
  ArrowLeftOutlined, SaveOutlined, ReloadOutlined, PlusOutlined,
  DeleteOutlined, FolderOutlined, FileTextOutlined, CheckCircleOutlined,
  ExclamationCircleOutlined, ApartmentOutlined, CalendarOutlined,
  SettingOutlined, ExperimentOutlined, ThunderboltOutlined,
  RiseOutlined, ClearOutlined, FileDoneOutlined, LockOutlined,
} from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import type { ColumnsType } from 'antd/es/table'
import { useParams, useNavigate } from 'react-router-dom'
import { simApi } from '../api'
import { DictSelect, DictTag } from '../components'

interface RatioRow {
  key?: string
  term_value: number
  term_unit: 'MONTH'
  business_ratio: number
  interest_rate: number
  sort_order: number
}

/** 节奏配置 12 个月权重行 */
interface RhythmRow {
  key?: string
  month_no: number
  month_label: string
  weight: number
  remark?: string | null
}

/** 新业务增长配置（增长方式 + 5 年分期增长参数） */
interface GrowthConfig {
  /** 增长方式：1=目标增长百分比 2=目标增长绝对值 3=增长百分比 4=增长值 */
  growth_type: string
  year1_value: number
  year2_value: number
  year3_value: number
  year4_value: number
  year5_value: number
  /** 绝对值单位：WAN=万元 / YI=亿元（growth_type=2/4 生效） */
  amount_unit?: string | null
  remark?: string | null
}

/** 增长方式元信息（用于单位联动 + 提示文案） */
const GROWTH_TYPE_META: Record<string, { label: string; unit: string; hint: string; isAbs: boolean }> = {
  '1': { label: '目标增长百分比', unit: '%',    hint: '目标增长率，按目标增速投放新业务', isAbs: false },
  '2': { label: '目标增长绝对值', unit: '金额', hint: '按目标新增余额绝对额投放（如每年新增 50 亿）', isAbs: true },
  '3': { label: '增长百分比',     unit: '%',    hint: '期间增长率，相对上年末余额的增长', isAbs: false },
  '4': { label: '增长值',         unit: '金额', hint: '期末余额绝对值（如第 1 年末余额 100 亿）', isAbs: true },
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
  const [configuredCount, setConfiguredCount] = useState<number>(0)
  // 点击了非末级节点时的提示上下文（用于右侧展示引导页）
  const [blockedNode, setBlockedNode] = useState<any>(null)
  const [dirty, setDirty] = useState(false)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])

  // ============== 配置面板状态 ==============
  // 是否模型测算（1=是 2=否）— 用 string 存，因为 DictSelect 的 dict_key 是字符串
  const [isModelCalc, setIsModelCalc] = useState<string>('2')  // 默认"否"
  // 节奏配置类型（1=线性 2=自定义）— string 同理
  const [rhythmType, setRhythmType] = useState<string>('1')  // 默认"线性"
  const [rhythmRows, setRhythmRows] = useState<RhythmRow[]>([])
  const [rhythmModalOpen, setRhythmModalOpen] = useState(false)
  const [rhythmSaving, setRhythmSaving] = useState(false)
  // 新业务增长配置（增长方式 + 5 年参数）
  const [growth, setGrowth] = useState<GrowthConfig>({
    growth_type: '1',
    year1_value: 0, year2_value: 0, year3_value: 0, year4_value: 0, year5_value: 0,
    amount_unit: 'WAN', remark: null,
  })
  const [growthSaving, setGrowthSaving] = useState(false)
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
      const r = await simApi.coaTree(coaSchemeId, schemeId)
      const raw = r.items || []
      setTreeRaw(raw)
      setTree(raw as DataNode[])
      setConfiguredCount(r.configured_count ?? 0)
      // 默认全展开
      const allKeys = collectKeys(raw)
      setExpandedKeys(allKeys)
    } catch (e: any) {
      message.error('账户册树加载失败')
    } finally {
      setTreeLoading(false)
    }
  }, [schemeId])

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
        // DB 返回 int，DictSelect 需要 string
        setIsModelCalc(String(r.config.is_model_calc ?? 2))  // 默认"否"
        setRhythmType(String(r.config.rhythm_type ?? 1))       // 默认"线性"
        setRatios((r.ratios || []).map((row: any, idx: number) => ({
          key: `db-${row.id || idx}`,
          term_value: row.term_value,
          term_unit: 'MONTH' as const,
          business_ratio: row.business_ratio,
          interest_rate: row.interest_rate || 0,
          sort_order: row.sort_order || idx + 1,
        })))
        setRhythmRows((r.rhythm || []).map((row: any, idx: number) => ({
          key: `rh-${row.month_no || idx + 1}`,
          month_no: row.month_no,
          month_label: row.month_label || `${row.month_no}月`,
          weight: row.weight,
          remark: row.remark,
        })))
        // 新业务增长配置（增长方式 + 5 年参数）
        const g = r.growth || {}
        setGrowth({
          growth_type: String(g.growth_type ?? 1),
          year1_value: g.year1_value ?? 0,
          year2_value: g.year2_value ?? 0,
          year3_value: g.year3_value ?? 0,
          year4_value: g.year4_value ?? 0,
          year5_value: g.year5_value ?? 0,
          amount_unit: g.amount_unit || 'WAN',
          remark: g.remark ?? null,
        })
        setConfigId(r.config.id)
      } else {
        // 未配置 → 默认值
        setIsModelCalc('2')  // 默认"否"
        setRhythmType('1')   // 默认"线性"
        setRatios([])
        // 未配置 → 默认线性 12 个月均匀
        setRhythmRows(Array.from({ length: 12 }, (_, i) => ({
          key: `rh-default-${i + 1}`,
          month_no: i + 1,
          month_label: `${i + 1}月`,
          weight: round4(100 / 12),
          remark: '默认线性（12 个月均匀）',
        })))
        // 未配置 → 增长配置默认值（目标增长百分比 + 5 年全 0）
        setGrowth({
          growth_type: '1',
          year1_value: 0, year2_value: 0, year3_value: 0, year4_value: 0, year5_value: 0,
          amount_unit: 'WAN', remark: null,
        })
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
    const id = Number(keys[0])

    // 末级节点判定：非末级（有子节点）不允许配置
    const node = findNodeRaw(treeRaw, id)
    const isLeaf = node ? (node.isLeaf || !node.children?.length) : false
    if (!isLeaf) {
      setSelectedNodeId(null)
      setSelectedNodeInfo(null)
      setConfigId(null)
      setDirty(false)
      setBlockedNode(node)
      message.info('该节点为非末级节点，请选择末级（末位）节点进行参数配置')
      return
    }

    setBlockedNode(null)

    const doSwitch = async () => {
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

  // ============== 新业务增长配置 ==============
  /** 更新某个年份的增长参数 */
  const updateGrowthYear = (year: 1 | 2 | 3 | 4 | 5, value: number) => {
    setGrowth(prev => ({ ...prev, [`year${year}_value`]: value }))
    setDirty(true)
  }

  /** 把 5 年参数全部填成同一个值（快捷操作） */
  const fillGrowthAllYears = (value: number) => {
    setGrowth(prev => ({
      ...prev,
      year1_value: value, year2_value: value, year3_value: value,
      year4_value: value, year5_value: value,
    }))
    setDirty(true)
  }

  /** 清空 5 年参数（全部置 0） */
  const clearGrowthAllYears = () => {
    setGrowth(prev => ({
      ...prev,
      year1_value: 0, year2_value: 0, year3_value: 0,
      year4_value: 0, year5_value: 0,
    }))
    setDirty(true)
  }

  /** 单独保存增长配置（不依赖主表单保存） */
  const handleSaveGrowthOnly = async () => {
    if (!configId) {
      message.warning('请先保存节点配置后再保存增长参数')
      return
    }
    setGrowthSaving(true)
    try {
      const r = await simApi.saveGrowth(configId, {
        growth_type: Number(growth.growth_type) || 1,
        year1_value: growth.year1_value,
        year2_value: growth.year2_value,
        year3_value: growth.year3_value,
        year4_value: growth.year4_value,
        year5_value: growth.year5_value,
        amount_unit: growth.amount_unit || null,
        remark: growth.remark || null,
      })
      message.success(
        `增长配置已保存（${r.action === 'created' ? '新建' : '更新'} · ` +
        `第1年 ${r.year1_value}${r.unit === '%' ? '%' : ' ' + (r.amount_unit === 'YI' ? '亿元' : '万元')}）`
      )
      setDirty(false)
      loadScheme()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '增长配置保存失败')
    } finally {
      setGrowthSaving(false)
    }
  }

  // ============== 节奏配置 ==============
  /** 4 位小数取整（与后端 ROUND(x,4) 对齐） */
  const round4 = (v: number) => Math.round(v * 10000) / 10000

  const rhythmSum = useMemo(
    () => round4(rhythmRows.reduce((a, r) => a + (Number(r.weight) || 0), 0)),
    [rhythmRows]
  )
  const isRhythmSumValid = Math.abs(rhythmSum - 100) < 0.01

  const updateRhythmWeight = (monthNo: number, weight: number) => {
    setRhythmRows(prev =>
      prev.map(r => (r.month_no === monthNo ? { ...r, weight } : r))
    )
  }

  /** 按线性重置 12 个月权重 */
  const resetRhythmToLinear = () => {
    setRhythmRows(Array.from({ length: 12 }, (_, i) => ({
      key: `rh-linear-${i + 1}`,
      month_no: i + 1,
      month_label: `${i + 1}月`,
      weight: round4(100 / 12),
      remark: '线性（12 个月均匀）',
    })))
  }

  /** 把当前权重按比例归一化到 100% */
  const normalizeRhythm = () => {
    const total = rhythmRows.reduce((a, r) => a + (Number(r.weight) || 0), 0)
    if (total <= 0) {
      message.warning('所有权重均为 0，无法归一化')
      return
    }
    setRhythmRows(prev =>
      prev.map((r, idx) => {
        // 最后一个月吸收舍入误差，保证总和精确 = 100
        const w = round4((Number(r.weight) || 0) / total * 100)
        if (idx < prev.length - 1) return { ...r, weight: w }
        return { ...r, weight: w }
      })
    )
  }

  const openRhythmModal = async () => {
    if (!configId) {
      message.warning('请先保存节点配置后再配置自定义节奏')
      return
    }
    try {
      const r = await simApi.getRhythm(configId)
      if (r?.items?.length) {
        setRhythmRows(r.items.map((row: any) => ({
          key: `rh-modal-${row.month_no}`,
          month_no: row.month_no,
          month_label: row.month_label || `${row.month_no}月`,
          weight: row.weight,
          remark: row.remark,
        })))
      }
      setRhythmModalOpen(true)
    } catch (e: any) {
      message.error('节奏配置加载失败')
    }
  }

  const handleSaveRhythm = async () => {
    if (!configId) return
    if (rhythmRows.length !== 12) {
      message.error('必须配置 1~12 月共 12 个月的权重')
      return
    }
    if (!isRhythmSumValid) {
      message.error(`12 个月权重之和必须为 100%，当前 = ${rhythmSum.toFixed(4)}%`)
      return
    }
    setRhythmSaving(true)
    try {
      const r = await simApi.saveRhythm(
        configId,
        rhythmRows.map(x => ({
          month_no: x.month_no,
          weight: x.weight,
          remark: x.remark || null,
        }))
      )
      message.success(`节奏配置已保存（12 月权重之和 = ${r.total_weight}%）`)
      setRhythmType('2')
      setRhythmModalOpen(false)
      // 同步主面板数据
      const cfg = await simApi.getNodeConfig(schemeId, selectedNodeId!)
      if (cfg?.rhythm?.length) {
        setRhythmRows(cfg.rhythm.map((row: any) => ({
          key: `rh-sync-${row.month_no}`,
          month_no: row.month_no,
          month_label: row.month_label || `${row.month_no}月`,
          weight: row.weight,
          remark: row.remark,
        })))
      }
      loadScheme()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '节奏配置保存失败')
    } finally {
      setRhythmSaving(false)
    }
  }

  /** 重置为线性（删除自定义数据） */
  const handleResetRhythmLinear = async () => {
    if (!configId) return
    try {
      await simApi.resetRhythmLinear(configId)
      resetRhythmToLinear()
      setRhythmType('1')
      message.success('已重置为线性节奏（12 个月均匀）')
      setDirty(true)
    } catch {
      message.error('重置失败')
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
      term_value: next, term_unit: 'MONTH', business_ratio: 0, interest_rate: 0,
      sort_order: ratios.length + 1,
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
        annual_growth_rate: growth.year1_value,  // 老字段镜像 = 第 1 年增长参数
        term_unit: 'MONTH',
        is_model_calc: Number(isModelCalc) || 2,  // string → int
        rhythm_type: Number(rhythmType) || 1,  // 1=线性 2=自定义
        ratios: ratios.map((r, idx) => ({
          term_value: r.term_value,
          term_unit: 'MONTH',
          business_ratio: r.business_ratio,
          interest_rate: r.interest_rate || 0,
          sort_order: idx + 1,
        })),
      }
      const r = await simApi.saveNodeConfig(schemeId, payload)
      message.success(`已保存（${r.term_count} 行，占比之和=${r.total_ratio}%）`)
      setConfigId(r.config_id)
      setDirty(false)
      // 刷新方案基础信息（config_node_count 会变）
      loadScheme()
      // 刷新树（该节点会变绿）
      if (scheme?.coa_scheme_id) loadTree(scheme.coa_scheme_id)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setIsModelCalc('2')  // 默认"否"
    setRhythmType('1')   // 默认"线性"
    resetRhythmToLinear()
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
      title: (
        <Space size={4}>
          新业务利率
          <Tooltip title="新业务定价利率（%），0~100；如 3.85 表示新业务按 3.85% 定价">
            <ExclamationCircleOutlined style={{ color: '#999' }} />
          </Tooltip>
        </Space>
      ),
      dataIndex: 'interest_rate', width: 140,
      render: (v: number, _r: any, idx: number) => (
        <InputNumber
          min={0} max={100} step={0.0001} precision={4}
          value={v}
          onChange={(val) => updateRatioRow(idx, 'interest_rate', val || 0)}
          addonAfter="%" style={{ width: '100%' }}
          placeholder="如 3.85"
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
                {scheme.data_date && (
                  <Tooltip title="模拟的基准数据日期（起始月）；引擎从此月开始按月滚动">
                    <Tag color="cyan" icon={<CalendarOutlined />} style={{ fontFamily: 'monospace' }}>
                      起始月 {scheme.data_date}
                    </Tag>
                  </Tooltip>
                )}
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
                {configuredCount > 0 && (
                  <Tag color="green" icon={<CheckCircleOutlined />}>
                    已配置 {configuredCount}
                  </Tag>
                )}
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
                    const isConfigured = !!node.has_config
                    return (
                      <Tooltip
                        title={isLeaf
                          ? (isConfigured ? '末级节点 · 已配置参数' : '末级节点 · 未配置参数（可点击配置）')
                          : `非末级节点（${node.children?.length || 0} 个子节点）· 不可配置，请选择末级节点`}
                        placement="right"
                      >
                        <div style={{
                          fontWeight: isLeaf ? 'normal' : 600,
                          color: isLeaf
                            ? (isConfigured ? '#52c41a' : '#333')   // 已配置的末级节点 → 绿色
                            : '#2f54eb',
                          width: '100%',
                          opacity: isLeaf ? 1 : 0.75,               // 非末级稍淡
                          cursor: isLeaf ? 'pointer' : 'not-allowed',
                        }}>
                          <Space size={6} style={{ width: '100%' }}>
                            {isLeaf
                              ? (isConfigured ? <FileDoneOutlined /> : <FileTextOutlined />)
                              : <FolderOutlined />}
                            <span>{node.title}</span>
                            {isLeaf ? (
                              <>
                                {isConfigured && (
                                  <Tag color="green" style={{ marginLeft: 'auto', marginRight: 4, fontSize: 11 }}>
                                    已配置
                                  </Tag>
                                )}
                                <Tag color={isSelected ? 'gold' : 'default'} style={{ fontSize: 11 }}>
                                  L{node.level}
                                </Tag>
                              </>
                            ) : (
                              <Tag
                                color="default"
                                style={{ marginLeft: 'auto', fontSize: 11, opacity: 0.7 }}
                              >
                                <LockOutlined /> 不可配置
                              </Tag>
                            )}
                          </Space>
                        </div>
                      </Tooltip>
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
            bodyStyle={{
              minHeight: 'calc(100vh - 280px)',
              opacity: blockedNode && !selectedNode ? 0.6 : 1,
              transition: 'opacity .2s',
            }}
          >
            {!selectedNode ? (
              blockedNode ? (
                <div style={{
                  marginTop: 60,
                  padding: '48px 32px',
                  background: '#fafafa',
                  border: '1px dashed #d9d9d9',
                  borderRadius: 8,
                  textAlign: 'center',
                  opacity: 0.75,
                }}>
                  <Space direction="vertical" size={12} style={{ width: '100%' }}>
                    <LockOutlined style={{ fontSize: 40, color: '#bfbfbf' }} />
                    <div style={{ fontSize: 16, fontWeight: 600, color: '#595959' }}>
                      非末级节点不可配置
                    </div>
                    <div style={{ color: '#8c8c8c', fontSize: 13, lineHeight: 2 }}>
                      您选择的是：<strong>{blockedNode.title}</strong><br />
                      该节点为<strong>非末级（分组）节点</strong>，下辖 {blockedNode.children?.length || 0} 个子节点，<br />
                      参数配置只能在<strong style={{ color: '#52c41a' }}>末级（末位）节点</strong>上进行。<br />
                      <span style={{ color: '#52c41a' }}>
                        提示：绿色标记的末级节点表示已配置过参数。
                      </span>
                    </div>
                    <Button
                      type="primary" ghost icon={<ArrowLeftOutlined />}
                      onClick={() => setBlockedNode(null)}
                    >
                      返回选择末级节点
                    </Button>
                  </Space>
                </div>
              ) : (
                <Empty description="请从左侧选择账户册节点" style={{ marginTop: 80 }} />
              )
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

                {/* 是否模型测算 */}
                <Card
                  size="small" type="inner"
                  title={
                    <Space>
                      <ExperimentOutlined style={{ color: '#722ed1' }} />
                      <span>是否模型测算</span>
                      <Tooltip title="标记该节点是否参与新业务模拟引擎的滚动测算。1=是（参与） 2=否（仅维护基础数据，不进入模型计算）">
                        <ExclamationCircleOutlined style={{ color: '#999' }} />
                      </Tooltip>
                    </Space>
                  }
                  style={{ marginBottom: 12, borderColor: isModelCalc === '1' ? '#722ed1' : undefined }}
                >
                  <Row gutter={16} align="middle">
                    <Col span={12}>
                      <DictSelect
                        dictType="PRCP_BIZ_YES_NO"
                        value={isModelCalc}
                        onChange={(v) => { setIsModelCalc(String(v ?? '2')); setDirty(true) }}
                        style={{ width: 200 }}
                      />
                    </Col>
                    <Col span={12}>
                      <span style={{ color: '#666', fontSize: 13 }}>
                        💡 当前节点：<strong>{selectedNode.code}</strong>，
                        {isModelCalc === '1' ? (
                          <>该节点将进入新业务模拟引擎的滚动测算（生成 prcp_sim_result 快照）</>
                        ) : (
                          <>该节点不进入模型测算（仅维护配置数据）</>
                        )}
                      </span>
                    </Col>
                  </Row>
                </Card>

                {/* 上栏：新业务增长配置（增长方式 + 5 年增长参数） */}
                <Card
                  size="small" type="inner"
                  title={
                    <Space>
                      <RiseOutlined style={{ color: '#13c2c2' }} />
                      <span>上栏 · 新业务增长配置</span>
                      <Tooltip title="配置未来 5 年（Y1~Y5）的新业务增长参数。先选「增长方式」确定参数含义与单位，再逐年填写参数值（默认 0）">
                        <ExclamationCircleOutlined style={{ color: '#999' }} />
                      </Tooltip>
                    </Space>
                  }
                  extra={
                    <Space>
                      <DictTag dictType="PRCP_GROWTH_TYPE" value={growth.growth_type} />
                      <Button
                        size="small"
                        type="text"
                        icon={<ClearOutlined />}
                        onClick={clearGrowthAllYears}
                        disabled={growth.year1_value === 0 && growth.year2_value === 0
                          && growth.year3_value === 0 && growth.year4_value === 0
                          && growth.year5_value === 0}
                      >
                        清零
                      </Button>
                      <Button
                        size="small"
                        type="primary"
                        icon={<SaveOutlined />}
                        loading={growthSaving}
                        disabled={!configId}
                        onClick={handleSaveGrowthOnly}
                      >
                        保存增长
                      </Button>
                    </Space>
                  }
                  style={{ marginBottom: 12, borderColor: '#13c2c2' }}
                >
                  {/* 增长方式 */}
                  <Row gutter={16} align="middle" style={{ marginBottom: 12 }}>
                    <Col span={8}>
                      <DictSelect
                        dictType="PRCP_GROWTH_TYPE"
                        value={growth.growth_type}
                        onChange={(v) => { setGrowth(p => ({ ...p, growth_type: String(v ?? '1') })); setDirty(true) }}
                        style={{ width: '100%' }}
                      />
                    </Col>
                    <Col span={16}>
                      <Space size={8}>
                        {GROWTH_TYPE_META[growth.growth_type]?.isAbs && (
                          <DictSelect
                            dictType="PRCP_AMOUNT_UNIT"
                            value={growth.amount_unit || 'WAN'}
                            onChange={(v) => { setGrowth(p => ({ ...p, amount_unit: String(v ?? 'WAN') })); setDirty(true) }}
                            style={{ width: 120 }}
                          />
                        )}
                        <span style={{ color: '#666', fontSize: 13 }}>
                          💡 {GROWTH_TYPE_META[growth.growth_type]?.hint}，
                          参数单位 = <strong>{GROWTH_TYPE_META[growth.growth_type]?.unit}</strong>
                          {GROWTH_TYPE_META[growth.growth_type]?.isAbs
                            ? `（${growth.amount_unit === 'YI' ? '亿元' : '万元'}）`
                            : ''}
                        </span>
                      </Space>
                    </Col>
                  </Row>

                  {/* 5 年增长参数 */}
                  <Row gutter={[12, 12]}>
                    {([1, 2, 3, 4, 5] as const).map(y => (
                      <Col span={4} key={y}>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                            第 {y} 年
                          </div>
                          <InputNumber
                            min={0}
                            step={GROWTH_TYPE_META[growth.growth_type]?.isAbs ? 1000 : 0.1}
                            precision={GROWTH_TYPE_META[growth.growth_type]?.isAbs ? 2 : 4}
                            value={growth[`year${y}_value`]}
                            onChange={(v) => updateGrowthYear(y, v ?? 0)}
                            addonAfter={GROWTH_TYPE_META[growth.growth_type]?.isAbs
                              ? (growth.amount_unit === 'YI' ? '亿' : '万')
                              : '%'}
                            style={{ width: '100%' }}
                            placeholder="0"
                          />
                        </div>
                      </Col>
                    ))}
                  </Row>

                  {/* 快捷填充 */}
                  <Row style={{ marginTop: 10 }}>
                    <Col span={24}>
                      <Space size={8} wrap>
                        <span style={{ fontSize: 12, color: '#999' }}>快捷填充 5 年同值：</span>
                        <InputNumber
                          size="small" min={0} step={0.1} precision={4}
                          style={{ width: 120 }}
                          placeholder="输入值"
                          onPressEnter={(e) => {
                            const v = (e.target as HTMLInputElement).value
                            if (v !== '' && !Number.isNaN(Number(v))) fillGrowthAllYears(Number(v))
                          }}
                        />
                        <Button size="small" onClick={() => fillGrowthAllYears(growth.year1_value)}>
                          用第 1 年填充全部
                        </Button>
                        <Button size="small" onClick={() => fillGrowthAllYears(round4(100 / 12))}>
                          填充 8.3333%（线性）
                        </Button>
                      </Space>
                    </Col>
                  </Row>
                </Card>

                {/* 中栏：期限占比子表 */}
                <Card
                  size="small" type="inner"
                  title={
                    <Space>
                      <span>中栏 · 新业务期限占比</span>
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
                      scroll={{ x: 760 }}
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
                {/* 下栏：节奏配置 — 线性 / 自定义（12 个月权重） */}
                <Card
                  size="small" type="inner"
                  title={
                    <Space>
                      <ThunderboltOutlined style={{ color: rhythmType === '2' ? '#fa8c16' : '#1890ff' }} />
                      <span>下栏 · 新业务节奏配置</span>
                      <Tooltip title="控制新业务在 12 个月预测期内的投放节奏。线性 = 12 个月均匀投放（每月 8.3333%）；自定义 = 按 12 个月权重分别配置（如开门红集中投放）">
                        <ExclamationCircleOutlined style={{ color: '#999' }} />
                      </Tooltip>
                    </Space>
                  }
                  extra={
                    <Space>
                      <Tag color={rhythmSum > 0 ? (isRhythmSumValid ? 'green' : 'red') : 'default'}>
                        12 月权重之和 = {rhythmSum.toFixed(4)}%
                      </Tag>
                      <Button
                        type={rhythmType === '2' ? 'primary' : 'default'}
                        icon={<SettingOutlined />}
                        size="small"
                        disabled={rhythmType !== '2'}
                        onClick={openRhythmModal}
                      >
                        自定义
                      </Button>
                    </Space>
                  }
                  style={{
                    marginBottom: 12,
                    borderColor: rhythmType === '2' ? '#fa8c16' : undefined,
                  }}
                >
                  <Row gutter={16} align="middle">
                    <Col span={8}>
                      <DictSelect
                        dictType="PRCP_RHYTHM_TYPE"
                        value={rhythmType}
                        onChange={(v) => {
                          const nv = String(v ?? '1')
                          setRhythmType(nv)
                          if (nv === '1') {
                            // 切回线性 → 前端立即重置为均匀（后端需点保存才生效）
                            resetRhythmToLinear()
                          } else {
                            // 切自定义 → 若已有数据直接打开弹窗
                            openRhythmModal()
                          }
                          setDirty(true)
                        }}
                        style={{ width: 200 }}
                      />
                    </Col>
                    <Col span={16}>
                      <span style={{ color: '#666', fontSize: 13 }}>
                        {rhythmType === '1' ? (
                          <>
                            💡 当前为 <strong>线性节奏</strong>：12 个月均匀投放，每月权重 = 8.3333%。
                            切换为「自定义」后点击右上角「自定义」按钮配置 12 个月权重。
                          </>
                        ) : (
                          <>
                            💡 当前为 <strong>自定义节奏</strong>：点击右上角「自定义」按钮编辑 12 个月权重，
                            权重之和必须 = 100%（当前 {rhythmSum.toFixed(4)}%）。
                          </>
                        )}
                      </span>
                    </Col>
                  </Row>

                  {/* 自定义节奏：12 个月权重预览条 */}
                  {rhythmType === '2' && (
                    <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px dashed #f0f0f0' }}>
                      <Space style={{ marginBottom: 8 }}>
                        <span style={{ fontSize: 12, color: '#666' }}>12 个月权重预览：</span>
                        <Tag color={isRhythmSumValid ? 'green' : 'red'} style={{ marginInlineEnd: 0 }}>
                          {isRhythmSumValid ? <><CheckCircleOutlined /> 校验通过</> : <><ExclamationCircleOutlined /> 需 = 100%</>}
                        </Tag>
                      </Space>
                      <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end', height: 60 }}>
                        {rhythmRows.map(r => {
                          const h = Math.max(3, Math.min(60, (Number(r.weight) || 0) / 100 * 60 * 3))
                          return (
                            <Tooltip key={r.month_no} title={`${r.month_label}：${(Number(r.weight) || 0).toFixed(4)}%`}>
                              <div style={{ flex: 1, textAlign: 'center' }}>
                                <div style={{
                                  height: `${h}px`,
                                  background: isRhythmSumValid ? '#fa8c16' : '#ff7875',
                                  borderRadius: '2px 2px 0 0',
                                  transition: 'all .2s',
                                }} />
                                <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>{r.month_no}</div>
                              </div>
                            </Tooltip>
                          )
                        })}
                      </div>
                    </div>
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

      {/* ============== 节奏配置弹窗（自定义 12 个月权重） ============== */}
      <Modal
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#fa8c16' }} />
            节奏配置 · 自定义 12 个月权重
            <Tag color="orange">{selectedNode?.code}</Tag>
          </Space>
        }
        open={rhythmModalOpen}
        onCancel={() => setRhythmModalOpen(false)}
        width={720}
        footer={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={resetRhythmToLinear}>恢复线性</Button>
            <Button onClick={() => setRhythmModalOpen(false)}>取消</Button>
            <Button
              type="primary"
              loading={rhythmSaving}
              disabled={!isRhythmSumValid}
              onClick={handleSaveRhythm}
            >
              保存
            </Button>
          </Space>
        }
      >
        <Alert
          type="info" showIcon style={{ marginBottom: 12 }}
          message="12 个月权重之和必须 = 100%（容差 ±0.01%）。可点击「归一化」按当前比例自动折算到 100%。"
        />

        {/* 权重柱状预览 */}
        <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 80, marginBottom: 16 }}>
          {rhythmRows.map(r => {
            const h = Math.max(4, Math.min(80, (Number(r.weight) || 0) / 100 * 80 * 3))
            return (
              <Tooltip key={r.month_no} title={`${r.month_label}：${(Number(r.weight) || 0).toFixed(4)}%`}>
                <div style={{ flex: 1, textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: '#666', marginBottom: 2 }}>
                    {(Number(r.weight) || 0).toFixed(1)}
                  </div>
                  <div style={{
                    height: `${h}px`,
                    background: isRhythmSumValid ? '#fa8c16' : '#ff7875',
                    borderRadius: '2px 2px 0 0',
                  }} />
                  <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>{r.month_label}</div>
                </div>
              </Tooltip>
            )
          })}
        </div>

        <Table
          size="small"
          rowKey="month_no"
          dataSource={rhythmRows}
          pagination={false}
          scroll={{ y: 320 }}
          columns={[
            {
              title: '月份', dataIndex: 'month_no', width: 100, align: 'center',
              render: (v: number) => <Tag color="blue">{v} 月</Tag>,
            },
            {
              title: '权重（%）', dataIndex: 'weight', width: 200,
              render: (v: number, r: RhythmRow) => (
                <InputNumber
                  min={0} max={100} step={0.01} precision={4}
                  value={v}
                  onChange={(val) => updateRhythmWeight(r.month_no, val ?? 0)}
                  addonAfter="%"
                  style={{ width: '100%' }}
                />
              ),
            },
            {
              title: '占全年比例', dataIndex: 'weight',
              render: (v: number) => (
                <Progress
                  percent={Math.round((Number(v) || 0) * 10) / 10}
                  size="small"
                  strokeColor="#fa8c16"
                  format={(p) => `${(Number(v) || 0).toFixed(2)}%`}
                />
              ),
            },
            {
              title: '备注', dataIndex: 'remark',
              render: (v: string, r: RhythmRow) => (
                <Input
                  size="small"
                  value={v || ''}
                  placeholder="可选，如：开门红 / 季末冲量"
                  onChange={(e) => setRhythmRows(prev =>
                    prev.map(x => (x.month_no === r.month_no ? { ...x, remark: e.target.value } : x))
                  )}
                />
              ),
            },
          ]}
        />

        <div style={{ marginTop: 12, textAlign: 'right' }}>
          <Space>
            <Tag color={isRhythmSumValid ? 'green' : 'red'}>
              {isRhythmSumValid ? <><CheckCircleOutlined /> 校验通过</> : <><ExclamationCircleOutlined /> 校验未通过</>}
            </Tag>
            <span style={{ color: '#666', fontSize: 13 }}>
              12 月权重之和 = <strong style={{ color: isRhythmSumValid ? '#52c41a' : '#f5222d' }}>{rhythmSum.toFixed(4)}%</strong>
            </span>
            <Button size="small" onClick={normalizeRhythm}>归一化到 100%</Button>
          </Space>
        </div>
      </Modal>
    </div>
  )
}

export default SimConfigPage

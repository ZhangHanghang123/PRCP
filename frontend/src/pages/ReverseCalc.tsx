import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Card, Row, Col, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Empty, Popconfirm, Progress, Alert, Statistic, Drawer,
  Descriptions, Tooltip, Tabs, Switch,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined,
  PlayCircleOutlined, PauseCircleOutlined, EyeOutlined,
  ExperimentOutlined, RocketOutlined, FunctionOutlined,
  AimOutlined, ProfileOutlined, CalendarOutlined, ThunderboltOutlined,
} from '@ant-design/icons'
import { reverseApi, coaApi } from '../api'
import { DictSelect, DictTag } from '../components'
import ReverseDashboard from './ReverseDashboard'

const { TabPane } = Tabs

const CONSTRAINT_LABELS: Record<string, { label: string; color: string }> = {
  GE: { label: '≥', color: 'green' },
  LE: { label: '≤', color: 'orange' },
  EQ: { label: '=', color: 'blue' },
}

/** 方案状态筛选（对齐 Java 版测算方案页） */
const SCHEME_STATUS_OPTIONS = [
  { value: 'DRAFT', label: '草稿' },
  { value: 'RUNNING', label: '运行中' },
  { value: 'SUCCESS', label: '已完成' },
  { value: 'DISABLED', label: '已停用' },
]

/** 运行阶段中文名（与后端 STAGE_* 常量一一对应） */
const STAGE_LABELS: Record<string, string> = {
  SUBMIT: '提交',
  LOAD_TARGET: '加载目标',
  LOAD_BALANCE: '加载账户册',
  SOLVE: '求解',
  SAVE_RESULT: '保存结果',
  DONE: '完成',
  FAILED: '失败',
}

const ReverseCalc: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [targets, setTargets] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [kpiOpts, setKpiOpts] = useState<any[]>([])
  const [kpiScope, setKpiScope] = useState<any>(null)   // 后端返回的链路上文（model/scheme）
  const [modelOpts, setModelOpts] = useState<any[]>([])
  const [coaSchemes, setCoaSchemes] = useState<any[]>([])

  const [activeSchemeId, setActiveSchemeId] = useState<number | null>(null)
  const [activeRunId, setActiveRunId] = useState<number | null>(null)

  // Tab 布局（对齐 Java 版：测算方案 / 目标设置 / 测算结果 / 运行记录）
  const [activeTab, setActiveTab] = useState<string>('schemes')
  const [schemeKeyword, setSchemeKeyword] = useState('')
  const [schemeStatus, setSchemeStatus] = useState<string | undefined>(undefined)
  // 运行记录是否只看当前选中方案（默认全部，对齐 Java 版）
  const [onlyCurrentScheme, setOnlyCurrentScheme] = useState(false)

  // Modal
  const [schemeModal, setSchemeModal] = useState(false)
  const [editingScheme, setEditingScheme] = useState<any>(null)
  const [schemeForm] = Form.useForm()
  const [targetModal, setTargetModal] = useState(false)
  const [editingTarget, setEditingTarget] = useState<any>(null)
  const [targetForm] = Form.useForm()
  const [runModal, setRunModal] = useState(false)
  const [runForm] = Form.useForm()

  // Drawer
  const [logDrawer, setLogDrawer] = useState(false)
  const [logRun, setLogRun] = useState<any>(null)
  const [logLines, setLogLines] = useState<any[]>([])
  const [logRounds, setLogRounds] = useState<any[]>([])
  const [logProgress, setLogProgress] = useState<any>(null)
  const [logAutoScroll, setLogAutoScroll] = useState(true)
  const logSinceRef = useRef(0)
  const logTimerRef = useRef<any>(null)
  const logBoxRef = useRef<any>(null)

  const [resultDrawer, setResultDrawer] = useState(false)
  const [resultData, setResultData] = useState<any>(null)

  // ============================================================
  // 数据加载
  // ============================================================
  const loadSchemes = async () => {
    const r = await reverseApi.listSchemes()
    const items = r.items || []
    setSchemes(items)
    // 自动选中第一条方案：保证后续页签（目标设置 / 运行记录）默认就有数据
    setActiveSchemeId(prev => {
      if (prev && items.some((x: any) => x.id === prev)) return prev
      return items.length ? items[0].id : null
    })
  }
  const loadTargets = async (schemeId: number | null) => {
    if (!schemeId) { setTargets([]); return }
    const r = await reverseApi.listTargets({ scheme_id: schemeId })
    setTargets(r.items || [])
  }
  const loadRuns = async (schemeId?: number | null) => {
    const r = await reverseApi.listRuns(schemeId ? { scheme_id: schemeId } : {})
    setRuns(r.items || [])
  }
  const loadKpiOpts = async (modelId?: number | null) => {
    const params = modelId ? { model_id: modelId } : {}
    const r = await reverseApi.kpiOptions(params)
    setKpiOpts(r.items || [])
    setKpiScope({
      model_id: r.model_id ?? null,
      scheme_id: r.scheme_id ?? null,
      model_code: r.model_code ?? null,
      scheme_code: r.scheme_code ?? null,
      filtered: !!r.filtered,
    })
  }
  const loadModelOpts = async () => {
    const r = await reverseApi.modelOptions()
    setModelOpts(r.items || [])
  }
  const loadCoaSchemes = async () => {
    const r = await coaApi.listSchemes({ status: 'ACTIVE' })
    setCoaSchemes(r.items || [])
  }

  useEffect(() => {
    loadSchemes()
    loadModelOpts()
    loadCoaSchemes()
    loadRuns()
  }, [])

  // 当前选中方案变化时，刷新目标与 KPI 下拉（按方案的 model_id 联动过滤）
  // 注意：运行记录始终加载全量，避免自动选中第一条后只剩该方案的运行
  useEffect(() => {
    loadTargets(activeSchemeId)
    const s = schemes.find(x => x.id === activeSchemeId)
    loadKpiOpts(s?.model_id || null)
  }, [activeSchemeId, schemes])

  // 日志轮询：增量拉日志 + 进度契约 + 轮次清单
  //   间隔取后端返回的 poll_interval_ms（默认 2000ms，对齐决策中心契约）
  //   页面不可见时暂停；运行结束（done=true）自动停止
  useEffect(() => {
    if (!logRun || !logDrawer) return
    logSinceRef.current = 0
    setLogLines([])
    setLogRounds([])
    setLogProgress(null)
    let stopped = false
    let timer: any = null

    const tick = async () => {
      if (stopped) return
      // 页面在后台时跳过本轮，避免无意义请求
      if (typeof document !== 'undefined' && document.hidden) return
      try {
        // ① 增量日志
        const r = await reverseApi.runLogs(logRun.id, logSinceRef.current)
        if (r.items && r.items.length) {
          setLogLines((p) => [...p, ...r.items])
          logSinceRef.current = r.items[r.items.length - 1].id
        }
        // ② 进度（状态 / 阶段 / 轮次 / 轮次清单一次拿全）
        const pg = await reverseApi.runProgress(logRun.id)
        setLogProgress(pg)
        setLogRun((prev: any) => (prev ? { ...prev, ...pg } : pg))
        if (pg.rounds?.length) setLogRounds(pg.rounds)
        // ③ 结束则停止轮询
        if (pg.done) {
          stopped = true
          if (timer) { clearInterval(timer); timer = null }
          // 收尾再拉一次日志，确保最后几行不丢
          const last = await reverseApi.runLogs(logRun.id, logSinceRef.current)
          if (last.items?.length) {
            setLogLines((p) => [...p, ...last.items])
            logSinceRef.current = last.items[last.items.length - 1].id
          }
          const pg2 = await reverseApi.runProgress(logRun.id)
          setLogProgress(pg2)
          if (pg2.rounds?.length) setLogRounds(pg2.rounds)
        }
      } catch (e) {
        console.error(e)
      }
    }

    tick()
    timer = setInterval(tick, 2000)
    logTimerRef.current = timer
    return () => {
      stopped = true
      if (timer) clearInterval(timer)
      logTimerRef.current = null
    }
  }, [logDrawer, logRun?.id])

  // 自动滚动到底部
  useEffect(() => {
    if (logAutoScroll && logBoxRef.current) {
      logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight
    }
  }, [logLines, logAutoScroll])

  // ============================================================
  // 方案 CRUD
  // ============================================================
  const onCreateScheme = () => {
    setEditingScheme(null)
    schemeForm.resetFields()
    schemeForm.setFieldsValue({
      scheme_type: 'OPTIMIZE', algorithm: 'CVXPY_QP',
      coa_scheme_id: coaSchemes.find((c: any) => c.scheme_code === 'ZX_CITIC_2026')?.id
                     || coaSchemes[0]?.id
                     || undefined,
      data_date: '2025-12-31', horizon_months: 24, status: 'DRAFT',
      model_id: undefined,
    })
    loadModelOpts()
    setSchemeModal(true)
  }
  const onEditScheme = (s: any) => {
    setEditingScheme(s)
    schemeForm.setFieldsValue({
      ...s, data_date: s.data_date?.substring(0, 10),
      model_id: s.model_id ?? undefined,
    })
    loadModelOpts()
    setSchemeModal(true)
  }
  const onSaveScheme = async () => {
    const v = await schemeForm.validateFields()
    const payload = {
      ...v,
      model_id: v.model_id === '' || v.model_id === undefined ? null : v.model_id,
    }
    try {
      if (editingScheme) await reverseApi.updateScheme(editingScheme.id, payload)
      else await reverseApi.createScheme(payload)
      message.success('已保存')
      setSchemeModal(false)
      loadSchemes()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onDeleteScheme = async (s: any) => {
    await reverseApi.deleteScheme(s.id)
    message.success('已删除')
    if (activeSchemeId === s.id) setActiveSchemeId(null)
    loadSchemes()
  }

  // ============================================================
  // 目标 CRUD
  // ============================================================
  const onCreateTarget = () => {
    if (!activeSchemeId) { message.warning('请先选择一个方案'); return }
    setEditingTarget(null)
    targetForm.resetFields()
    targetForm.setFieldsValue({ scheme_id: activeSchemeId, constraint_type: 'GE', weight: 1, sort_order: 0 })
    // 重新按当前方案的 model_id 刷新 KPI 下拉（防止选中方案后未触发 useEffect）
    const s = schemes.find(x => x.id === activeSchemeId)
    loadKpiOpts(s?.model_id || null)
    setTargetModal(true)
  }
  const onEditTarget = (t: any) => {
    setEditingTarget(t)
    targetForm.setFieldsValue(t)
    const s = schemes.find(x => x.id === activeSchemeId)
    loadKpiOpts(s?.model_id || null)
    setTargetModal(true)
  }
  const onSaveTarget = async () => {
    const v = await targetForm.validateFields()
    try {
      if (editingTarget) await reverseApi.updateTarget(editingTarget.id, v)
      else await reverseApi.createTarget(v)
      message.success('已保存')
      setTargetModal(false)
      loadTargets(activeSchemeId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onDeleteTarget = async (t: any) => {
    await reverseApi.deleteTarget(t.id)
    message.success('已删除')
    loadTargets(activeSchemeId)
  }

  // ============================================================
  // 运行 CRUD
  // ============================================================
  const onCreateRun = () => {
    if (!activeSchemeId) { message.warning('请先选择方案'); return }
    runForm.resetFields()
    runForm.setFieldsValue({ scheme_id: activeSchemeId })
    setRunModal(true)
  }
  const onStartRun = async (r: any) => {
    try {
      await reverseApi.startRun(r.id)
      message.success('反算已启动')
      setLogRun(r)
      setLogDrawer(true)
      loadRuns()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '启动失败')
    }
  }
  const onCancelRun = async (r: any) => {
    await reverseApi.cancelRun(r.id)
    message.success('已取消')
    loadRuns()
  }
  const onViewLogs = (r: any) => { setLogRun(r); setLogDrawer(true) }
  const onViewResult = async (r: any) => {
    const data = await reverseApi.runResult(r.id)
    setResultData(data)
    setResultDrawer(true)
  }
  const onDeleteRun = async (r: any) => {
    await reverseApi.deleteRun(r.id)
    message.success('已删除')
    loadRuns()
  }
  const onSaveRun = async () => {
    const v = await runForm.validateFields()
    try {
      const r = await reverseApi.createRun(v)
      message.success(`反算任务已创建：${r.run_code}，点击「启动」开始反算`)
      setRunModal(false)
      loadRuns()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '创建失败')
    }
  }

  /** 一键运行：建 Run → 立即启动 → 打开日志抽屉（对齐 Java 版「运行」按钮） */
  const onRunScheme = async (s: any) => {
    try {
      const r = await reverseApi.createRun({ scheme_id: s.id })
      const started = await reverseApi.startRun(r.id)
      message.success(`反算已启动：${started.run_code || r.run_code}`)
      setActiveSchemeId(s.id)
      setLogRun({ ...started, scheme_id: s.id, scheme_code: s.scheme_code, scheme_name: s.scheme_name })
      setLogDrawer(true)
      loadRuns(s.id)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '启动失败')
    }
  }

  // ============================================================
  // 表格列
  // ============================================================
  // 方案表格列（对齐 Java 版：编码/名称/关联账户册/计量模型/数据日期/预测期/运行数/状态/操作）
  const schemeColumns = [
    { title: '编码', dataIndex: 'scheme_code', key: 'sc', width: 130,
      render: (v: string) => <strong style={{ color: '#534ab7' }}>{v}</strong> },
    { title: '名称', dataIndex: 'scheme_name', key: 'sn', width: 200,
      render: (v: string, r: any) => (
        <Tooltip title={r.description || v}>
          <span>{v}</span>
        </Tooltip>
      ) },
    { title: '关联账户册', key: 'coa', width: 175,
      render: (_: any, r: any) => r.coa_code ? (
        <Tag color="cyan">{r.coa_name || r.coa_code}</Tag>
      ) : <span style={{ color: '#bbb' }}>未关联</span> },
    { title: '计量模型', key: 'model', width: 145,
      render: (_: any, r: any) => r.model_id
        ? <Tag color="geekblue" icon={<ExperimentOutlined />}>{r.model_code || r.model_name}</Tag>
        : <span style={{ color: '#bbb' }}>未关联</span> },
    { title: '数据日期', dataIndex: 'data_date', key: 'dd', width: 120,
      render: (v: string) => v
        ? <Tag color="blue" icon={<CalendarOutlined />}>{String(v).substring(0, 10)}</Tag>
        : '-' },
    { title: '预测期', dataIndex: 'horizon_months', key: 'h', width: 80,
      render: (v: number) => (v ? `${v} 月` : '-') },
    { title: '运行数', dataIndex: 'run_count', key: 'rc', width: 70,
      render: (v: number) => (v ?? 0) },
    { title: '状态', dataIndex: 'status', key: 's', width: 90,
      render: (v: string) => v?.startsWith('PENDING') || v === 'RUNNING' || v === 'SUCCESS' || v === 'FAILED' || v === 'CANCELLED'
        ? <DictTag dictType="PRCP_RUN_STATUS" value={v} />
        : <DictTag dictType="PRCP_STATUS" value={v} /> },
    { title: '操作', key: 'op', width: 220, render: (_: any, r: any) => (
      <Space size={2}>
        <Button size="small" type="link" onClick={() => onEditScheme(r)}>详情</Button>
        <Button size="small" type="link" onClick={() => { setActiveSchemeId(r.id); setActiveTab('targets') }}>目标设置</Button>
        <Button size="small" type="link" style={{ color: '#0B6FF2' }}
          onClick={() => onRunScheme(r)}>运行</Button>
        <Popconfirm title="确认删除该方案？" onConfirm={() => onDeleteScheme(r)}>
          <Button size="small" type="link" style={{ color: '#C9332B' }}>删除</Button>
        </Popconfirm>
      </Space>
    )},
  ]

  const targetColumns = [
    { title: '关联 KPI', dataIndex: 'kpi_code', key: 'kc', width: 140,
      render: (v: string, r: any) => v ? (
        <Tooltip title={r.ref_formula || r.ref_kpi_name}>
          <Space size={4}>
            <Tag color="geekblue">{v}</Tag>
            {r.ref_kpi_name && <span style={{ color: '#888', fontSize: 12 }}>{r.ref_kpi_name}</span>}
          </Space>
        </Tooltip>
      ) : '-' },
    { title: '目标值', dataIndex: 'target_value', key: 'tv', width: 110,
      render: (v: number) => <strong>{v.toFixed(4)}</strong> },
    { title: '约束', dataIndex: 'constraint_type', key: 'ct', width: 80,
      render: (v: string) => (
        <Tag color={CONSTRAINT_LABELS[v]?.color}>{CONSTRAINT_LABELS[v]?.label || v}</Tag>
      )},
    { title: '权重', dataIndex: 'weight', key: 'w', width: 70 },
    { title: '生效期', dataIndex: 'horizon_month', key: 'hm', width: 80,
      render: (v: number) => v === 0 ? '全期' : `第 ${v} 月` },
    { title: '操作', key: 'op', width: 100, render: (_: any, r: any) => (
      <Space>
        <Button size="small" icon={<EditOutlined />} onClick={() => onEditTarget(r)} />
        <Popconfirm title="确认删除？" onConfirm={() => onDeleteTarget(r)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ]

  const runColumns = [
    { title: '执行编码', dataIndex: 'run_code', key: 'rc', width: 180,
      render: (v: string) => <code style={{ background: '#f0f4ff', padding: '2px 6px', borderRadius: 3 }}>{v}</code> },
    { title: '方案', key: 'scheme', width: 160,
      render: (_: any, r: any) => <span><strong>{r.scheme_code}</strong> · {r.scheme_name}</span> },
    { title: '进度', key: 'prog', width: 180,
      render: (_: any, r: any) => (
        <Progress
          percent={r.progress} size="small"
          status={r.status === 'FAILED' ? 'exception' : r.status === 'SUCCESS' ? 'success' : 'active'}
        />
      )},
    { title: '状态', dataIndex: 'status', key: 's', width: 100,
      render: (v: string) => v?.startsWith('PENDING') || v === 'RUNNING' || v === 'SUCCESS' || v === 'FAILED' || v === 'CANCELLED'
        ? <DictTag dictType="PRCP_RUN_STATUS" value={v} />
        : <DictTag dictType="PRCP_STATUS" value={v} /> },
    { title: '目标值', dataIndex: 'optimal_value', key: 'ov', width: 100,
      render: (v: number) => v != null ? v.toFixed(4) : '-' },
    { title: '耗时', dataIndex: 'duration_sec', key: 'ds', width: 70,
      render: (v: number) => v ? `${v}s` : '-' },
    { title: '操作', key: 'op', width: 220, render: (_: any, r: any) => (
      <Space>
        {r.status === 'PENDING' && (
          <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => onStartRun(r)}>启动</Button>
        )}
        {r.status === 'RUNNING' && (
          <>
            <Button size="small" icon={<EyeOutlined />} onClick={() => onViewLogs(r)}>日志</Button>
            <Button size="small" danger icon={<PauseCircleOutlined />} onClick={() => onCancelRun(r)}>取消</Button>
          </>
        )}
        {['SUCCESS', 'FAILED', 'CANCELLED'].includes(r.status) && (
          <>
            <Button size="small" icon={<EyeOutlined />} onClick={() => onViewLogs(r)}>日志</Button>
            <Button size="small" icon={<RocketOutlined />} onClick={() => onViewResult(r)}>结果</Button>
          </>
        )}
        <Popconfirm title="确认删除？" onConfirm={() => onDeleteRun(r)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ]

  // 方案列表（按关键字 + 状态过滤）
  const filteredSchemes = useMemo(() => {
    const kw = schemeKeyword.trim().toLowerCase()
    return (schemes || []).filter((s: any) => {
      if (schemeStatus && s.status !== schemeStatus) return false
      if (!kw) return true
      return (
        String(s.scheme_code || '').toLowerCase().includes(kw) ||
        String(s.scheme_name || '').toLowerCase().includes(kw)
      )
    })
  }, [schemes, schemeKeyword, schemeStatus])

  // 运行记录（可只看当前方案）
  const visibleRuns = useMemo(() => {
    if (!onlyCurrentScheme || !activeSchemeId) return runs
    return runs.filter((r: any) => r.scheme_id === activeSchemeId)
  }, [runs, onlyCurrentScheme, activeSchemeId])

  const activeScheme = schemes.find(s => s.id === activeSchemeId)

  return (
    <div style={{ padding: 16 }}>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        size="large"
        items={[
        // ============ Tab 1：测算方案 ============
        {
          key: 'schemes',
          label: <span><AimOutlined /> 测算方案</span>,
          children: (
            <div>
              {/* 概览 KPI */}
              <Row gutter={12} style={{ marginBottom: 12 }}>
                <Col span={6}>
                  <Card size="small">
                    <Statistic title="反算方案" value={schemes.length} prefix={<AimOutlined style={{ color: '#534ab7' }} />} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small">
                    <Statistic title="目标约束（当前方案）" value={targets.length} prefix={<FunctionOutlined style={{ color: '#764ba2' }} />} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small">
                    <Statistic
                      title="反算运行中"
                      value={runs.filter(r => r.status === 'RUNNING').length}
                      valueStyle={{ color: '#1890ff' }}
                      prefix={<RocketOutlined style={{ color: '#1890ff' }} />}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small">
                    <Statistic
                      title="已完成"
                      value={runs.filter(r => r.status === 'SUCCESS').length}
                      suffix={`/ ${runs.length}`}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Card>
                </Col>
              </Row>

              {/* 工具栏 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                <Button type="primary" icon={<PlusOutlined />} onClick={onCreateScheme}>新建方案</Button>
                <Input
                  placeholder="搜索方案编码 / 名称"
                  allowClear
                  value={schemeKeyword}
                  onChange={(e) => setSchemeKeyword(e.target.value)}
                  style={{ width: 240 }}
                />
                <Select
                  placeholder="状态"
                  allowClear
                  value={schemeStatus}
                  onChange={setSchemeStatus}
                  options={SCHEME_STATUS_OPTIONS}
                  style={{ width: 130 }}
                />
                <Button icon={<ReloadOutlined />} onClick={() => { loadSchemes(); loadRuns() }}>刷新</Button>
                <span style={{ marginLeft: 'auto', fontSize: 12, color: '#8f959e' }}>
                  共 {filteredSchemes.length} / {schemes.length} 个方案
                </span>
              </div>

              <Table
                rowKey="id"
                columns={schemeColumns}
                dataSource={filteredSchemes}
                pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (t) => `共 ${t} 个方案` }}
                size="small"
                scroll={{ x: 1210 }}
                rowClassName={(r) => r.id === activeSchemeId ? 'ant-table-row-selected' : ''}
                onRow={(r) => ({ onDoubleClick: () => { setActiveSchemeId(r.id); setActiveTab('targets') } })}
              />
            </div>
          ),
        },

        // ============ Tab 2：目标设置 ============
        {
          key: 'targets',
          label: <span><FunctionOutlined /> 目标设置</span>,
          children: (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                <Select
                  placeholder="选择测算方案"
                  value={activeSchemeId ?? undefined}
                  onChange={(v) => { setActiveSchemeId(v ?? null); setActiveTab('targets') }}
                  options={schemes.map((s: any) => ({
                    value: s.id,
                    label: `${s.scheme_code} - ${s.scheme_name}`,
                  }))}
                  style={{ width: 360 }}
                  showSearch
                  optionFilterProp="label"
                />
                {activeScheme && (
                  <>
                    <Tag color={activeScheme.status === 'SUCCESS' ? 'green' : 'blue'}>
                      {activeScheme.status}
                    </Tag>
                    <span style={{ fontSize: 12, color: '#646a73' }}>
                      {activeScheme.scheme_name} · {activeScheme.horizon_months} 月 ·{' '}
                      {activeScheme.model_code || activeScheme.model_name || '未关联模型'}
                    </span>
                  </>
                )}
                <span style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                  <Button icon={<ReloadOutlined />} disabled={!activeSchemeId}
                    onClick={() => loadTargets(activeSchemeId)}>刷新</Button>
                  <Button icon={<PlusOutlined />} disabled={!activeSchemeId} onClick={onCreateTarget}>新增目标</Button>
                  <Button type="primary" icon={<ThunderboltOutlined />}
                    disabled={!activeSchemeId || targets.length === 0}
                    onClick={() => { setActiveTab('runs'); loadRuns() }}>开始测算</Button>
                </span>
              </div>

              {!activeSchemeId ? (
                <Card>
                  <Empty description="请先选择测算方案，然后为目标 KPI 配置目标值、约束方式与权重" />
                </Card>
              ) : (
                <>
                  <Alert
                    type="info" showIcon
                    style={{ marginBottom: 12 }}
                    message={
                      <Space wrap>
                        <span>目标配置完成后点击「开始测算」进入运行记录发起反算。</span>
                        {kpiScope?.filtered ? (
                          <Tooltip title={`KPI 仅限：模型 ${kpiScope.model_code || kpiScope.model_id} → 指标方案 ${kpiScope.scheme_code || kpiScope.scheme_id}`}>
                            <Tag color="geekblue" icon={<ExperimentOutlined />}>
                              {kpiScope.model_code || `model#${kpiScope.model_id}`} → {kpiScope.scheme_code || `scheme#${kpiScope.scheme_id}`}
                            </Tag>
                          </Tooltip>
                        ) : (
                          <Tag color="default">未限定 KPI 范围</Tag>
                        )}
                      </Space>
                    }
                  />
                  <Table
                    rowKey="id"
                    columns={targetColumns}
                    dataSource={targets}
                    pagination={false}
                    size="small"
                    scroll={{ x: 800 }}
                  />
                </>
              )}
            </div>
          ),
        },

        // ============ Tab 3：测算结果（复用结果驾驶舱）============
        {
          key: 'result',
          label: <span><ProfileOutlined /> 测算结果</span>,
          children: (
            <div>
              <Alert
                type="info" showIcon style={{ marginBottom: 12 }}
                message="测算结果复用「结果驾驶舱」：可在其中切换组合方案 / 运行记录 / 预测月份 / 余额口径，查看目标达成、指标对比、余额分布与走势，并导出结果。"
              />
              {activeTab === 'result' && <ReverseDashboard initialSchemeCode={activeScheme?.scheme_code} />}
            </div>
          ),
        },

        // ============ Tab 4：运行记录 ============
        {
          key: 'runs',
          label: <span><RocketOutlined /> 运行记录</span>,
          children: (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                <Button icon={<ReloadOutlined />} onClick={() => loadRuns()}>刷新</Button>
                <Button type="primary" icon={<PlusOutlined />} disabled={!activeSchemeId} onClick={onCreateRun}>新建反算</Button>
                {activeScheme && (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12.5, color: '#646a73' }}>
                    <Switch size="small" checked={onlyCurrentScheme} onChange={setOnlyCurrentScheme} />
                    仅看当前方案
                    <Tag color="blue">{activeScheme.scheme_code}</Tag>
                  </span>
                )}
                <span style={{ marginLeft: 'auto', fontSize: 12, color: '#8f959e' }}>
                  共 {visibleRuns.length} / {runs.length} 条运行记录
                </span>
              </div>
              <Table
                rowKey="id"
                columns={runColumns}
                dataSource={visibleRuns}
                pagination={{ pageSize: 10, showSizeChanger: true }}
                size="small"
                scroll={{ x: 1200 }}
              />
            </div>
          ),
        },
        ]}
      />

      {/* 方案 Modal */}
      <Modal
        open={schemeModal}
        title={editingScheme ? '✏️ 编辑反算方案' : '＋ 新建反算方案'}
        onCancel={() => setSchemeModal(false)}
        onOk={onSaveScheme}
        width={600}
        okText="保存"
      >
        <Form form={schemeForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="方案编码" name="scheme_code" rules={[{ required: true }]}>
                <Input placeholder="如 REV_NIM_UP" disabled={!!editingScheme} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="方案名称" name="scheme_name" rules={[{ required: true }]}>
                <Input placeholder="如 NIM 上行 50BP 反算" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="方案类型" name="scheme_type">
                <DictSelect dictType="PRCP_SCHEME_TYPE" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="算法" name="algorithm">
                <DictSelect dictType="PRCP_REVERSE_ALGO" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="账户册方案" name="coa_scheme_id" rules={[{ required: true }]}>
                <Select
                  allowClear showSearch optionFilterProp="label" disabled={coaSchemes.length === 0}
                  placeholder={coaSchemes.length === 0 ? '暂无 ACTIVE 账户册方案' : '选择账户册方案'}
                  options={coaSchemes.map((c: any) => ({
                    value: c.id,
                    label: `${c.scheme_code}（${c.node_count ?? '?'} 节点）`,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="数据日期" name="data_date" rules={[{ required: true }]}>
                <Input type="date" defaultValue="2025-12-31" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="计量模型（关联模型管理）" name="model_id"
            extra="绑定后，反算引擎可读取该模型下的超参数作为求解约束">
            <Select
              allowClear showSearch optionFilterProp="label" placeholder="选择计量模型（可空）"
              options={modelOpts.map((m: any) => ({
                value: m.id,
                label: `${m.model_code} · ${m.model_name}（${m.model_type || ''}）`,
              }))}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="预测期数" name="horizon_months">
                <InputNumber min={1} max={60} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="状态" name="status">
                <DictSelect dictType="PRCP_STATUS" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 目标 Modal */}
      <Modal
        open={targetModal}
        title={editingTarget ? '✏️ 编辑目标' : '＋ 新增目标'}
        onCancel={() => setTargetModal(false)}
        onOk={onSaveTarget}
        width={550}
        okText="保存"
      >
        <Form form={targetForm} layout="vertical">
          <Form.Item label="所属方案" name="scheme_id" rules={[{ required: true }]}>
            <Select disabled>
              {schemes.map(s => (
                <Select.Option key={s.id} value={s.id}>{s.scheme_code} · {s.scheme_name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="关联 KPI"
            name="kpi_id"
            extra={
              kpiScope?.filtered
                ? <span style={{ color: '#534ab7' }}>
                    <ExperimentOutlined /> 仅可选择：模型 <b>{kpiScope.model_code}</b> → 指标方案 <b>{kpiScope.scheme_code}</b> 中的 KPI（共 {kpiOpts.length} 条）
                  </span>
                : <span style={{ color: '#aaa' }}>当前方案未关联计量模型，KPI 下拉显示全部</span>
            }
          >
            <Select
              showSearch optionFilterProp="children" allowClear
              placeholder={
                kpiScope?.filtered
                  ? `从「${kpiScope.scheme_code}」指标方案中选择`
                  : '选择 KPI'
              }
              notFoundContent={kpiScope?.filtered ? '该指标方案下暂无定义，请到指标管理页维护' : '暂无 KPI'}
            >
              {kpiOpts.map((k: any) => (
                <Select.Option key={k.id} value={k.id}>
                  {k.kpi_code} · {k.kpi_name}
                  {k.scheme_code && <span style={{ color: '#999', marginLeft: 6 }}>[{k.scheme_code}]</span>}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="目标值" name="target_value" rules={[{ required: true }]}>
                <InputNumber step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="约束方向" name="constraint_type">
                <Select>
                  <Select.Option value="GE">≥</Select.Option>
                  <Select.Option value="LE">≤</Select.Option>
                  <Select.Option value="EQ">=</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="权重" name="weight">
                <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="生效期" name="horizon_month">
                <InputNumber min={0} style={{ width: '100%' }} placeholder="0=全期" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="排序" name="sort_order">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 反算 Modal */}
      <Modal
        open={runModal}
        title="🚀 新建反算任务"
        onCancel={() => setRunModal(false)}
        onOk={onSaveRun}
        width={450}
        okText="创建"
      >
        <Form form={runForm} layout="vertical">
          <Form.Item label="所属方案" name="scheme_id" rules={[{ required: true }]}>
            <Select disabled>
              {schemes.map(s => (
                <Select.Option key={s.id} value={s.id}>{s.scheme_code} · {s.scheme_name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="备注" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Alert type="info" showIcon message="将使用方案配置的目标 KPI 约束进行反算求解" />
        </Form>
      </Modal>

      {/* 日志 Drawer */}
      <Drawer
        open={logDrawer}
        title={logRun ? `反算日志：${logRun.run_code}` : ''}
        width={880}
        onClose={() => { setLogDrawer(false); setLogRun(null); setLogLines([]); setLogRounds([]); setLogProgress(null) }}
      >
        {logRun && (
          <>
            {/* 状态条 */}
            <Descriptions size="small" column={4} bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label="状态">
                <DictTag dictType="PRCP_RUN_STATUS" value={logRun.status} />
              </Descriptions.Item>
              <Descriptions.Item label="进度">
                <Progress percent={logRun.progress} size="small" style={{ width: 130 }} />
              </Descriptions.Item>
              <Descriptions.Item label="当前阶段">
                {logProgress?.stage
                  ? <Tag color="processing">{STAGE_LABELS[logProgress.stage] || logProgress.stage}</Tag>
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="当前轮次">
                {logProgress?.round_no ? `第 ${logProgress.round_no} 轮` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="耗时">{logRun.duration_sec || '-'} s</Descriptions.Item>
              <Descriptions.Item label="算法">
                <DictTag dictType="PRCP_REVERSE_ALGO" value={logProgress?.algo || logRun.algorithm} />
              </Descriptions.Item>
              <Descriptions.Item label="日志条数">{logProgress?.history_count ?? logLines.length}</Descriptions.Item>
              <Descriptions.Item label="轮次数">{logRounds.length || 0}</Descriptions.Item>
              <Descriptions.Item label="方案" span={4}>{logRun.scheme_code} · {logRun.scheme_name}</Descriptions.Item>
            </Descriptions>

            {/* 轮次面板 —— 多轮推算时逐轮记录状态与结果 */}
            {logRounds.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 6, color: '#1f2329' }}>
                  推算轮次（{logRounds.length} 轮）
                </div>
                <div className="round-list">
                  {logRounds.map((rd: any) => (
                    <div key={`${rd.round_no}-${rd.algo}`} className="round-item">
                      <div className="round-head">
                        <Tag color={rd.status === 'SUCCESS' ? 'green' : rd.status === 'FAILED' ? 'red' : 'blue'}>
                          第 {rd.round_no} 轮
                        </Tag>
                        <Tag>{rd.algo}</Tag>
                        <span style={{ fontSize: 11, color: '#8f959e' }}>{rd.message || ''}</span>
                        {rd.duration_sec != null && (
                          <span style={{ fontSize: 11, color: '#8f959e', marginLeft: 'auto' }}>{rd.duration_sec}s</span>
                        )}
                      </div>
                      <div className="round-body">
                        <span>得分 <b style={{ color: '#165dff' }}>{rd.score != null ? rd.score : '-'}</b></span>
                        <span>目标值 <b>{rd.optimal_value != null ? Number(rd.optimal_value).toFixed(4) : '-'}</b></span>
                        <span>目标达成
                          <b style={{ color: rd.target_hit ? '#00a870' : '#f53f3f' }}>
                            {rd.target_hit == null ? '-' : rd.target_hit ? '全部达成' : '未全部达成'}
                          </b>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 日志流 */}
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: '#1f2329' }}>运行日志</span>
              <span style={{ fontSize: 11, color: '#8f959e', marginLeft: 8 }}>
                {logProgress?.done ? '（运行已结束）' : `（实时刷新中 · 每 ${Math.round((logProgress?.poll_interval_ms || 2000) / 1000)} 秒）`}
              </span>
              <span style={{ marginLeft: 'auto', fontSize: 11, color: '#8f959e' }}>
                <Switch size="small" checked={logAutoScroll} onChange={setLogAutoScroll} /> 自动滚动
              </span>
            </div>
            <div
              ref={logBoxRef}
              style={{ background: '#0f172a', color: '#94a3b8', fontFamily: 'Consolas, monospace', fontSize: 12, padding: 12, borderRadius: 6, maxHeight: 400, overflow: 'auto' }}
            >
              {logLines.length === 0 && <div style={{ color: '#64748b' }}>暂无日志...</div>}
              {logLines.map((l: any) => (
                <div key={l.id} style={{ marginBottom: 2 }}>
                  <span style={{ color: '#64748b' }}>{l.created_at?.substring(11, 19)}</span>{' '}
                  {l.round_no != null && (
                    <span style={{ color: '#a78bfa' }}>[R{l.round_no}]</span>
                  )}{' '}
                  {l.stage && (
                    <span style={{ color: '#38bdf8' }}>[{STAGE_LABELS[l.stage] || l.stage}]</span>
                  )}{' '}
                  <span style={{
                    color: l.log_level === 'ERROR' ? '#fca5a5' : l.log_level === 'WARN' ? '#fcd34d' : '#93c5fd'
                  }}>[{l.log_level}]</span>{' '}
                  {l.log_message}
                  {l.progress != null && <span style={{ color: '#64748b' }}> ({l.progress.toFixed(0)}%)</span>}
                </div>
              ))}
            </div>
            {logRun.metrics && (
              <div style={{ marginTop: 12, padding: 12, background: '#f0fdf4', borderRadius: 6 }}>
                <strong style={{ color: '#15803d' }}>📊 反算指标：</strong>
                <pre style={{ marginTop: 8, fontSize: 12 }}>{JSON.stringify(logRun.metrics, null, 2)}</pre>
              </div>
            )}
          </>
        )}
      </Drawer>

      {/* 结果 Drawer */}
      <Drawer
        open={resultDrawer}
        title={resultData?.run ? `反算结果：${resultData.run.run_code}` : ''}
        width={900}
        onClose={() => setResultDrawer(false)}
      >
        {resultData?.run && (
          <>
            <Descriptions size="small" column={4} bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label="状态"><DictTag dictType="PRCP_RUN_STATUS" value={resultData.run.status} /></Descriptions.Item>
              <Descriptions.Item label="耗时">{resultData.run.duration_sec || '-'} s</Descriptions.Item>
              <Descriptions.Item label="目标值">{resultData.run.optimal_value?.toFixed(4) || '-'}</Descriptions.Item>
              <Descriptions.Item label="预测项数">{resultData.items?.length || 0}</Descriptions.Item>
            </Descriptions>
            {resultData.run.metrics && (
              <Alert
                type="success"
                style={{ marginBottom: 12 }}
                showIcon
                message={<pre style={{ margin: 0, fontSize: 12 }}>{JSON.stringify(resultData.run.metrics, null, 2)}</pre>}
              />
            )}
            <h4>📈 报表未来 24 月预测（每期 × 每个账户册节点）</h4>
            <Table
              rowKey="id"
              size="small"
              dataSource={resultData.items || []}
              pagination={{ pageSize: 20 }}
              columns={[
                { title: '期', dataIndex: 'predict_month', key: 'pm', width: 50,
                  render: (v: number) => <Tag color="cyan">M{v}</Tag> },
                { title: '日期', dataIndex: 'predict_date', key: 'pd', width: 110,
                  render: (v: string) => v?.substring(0, 10) },
                { title: '节点', dataIndex: 'rpt_item_code', key: 'ric', width: 100,
                  render: (v: string) => <code>{v}</code> },
                { title: '当前值', dataIndex: 'current_value', key: 'cv', width: 120,
                  render: (v: number) => v != null ? v.toFixed(2) : '-' },
                { title: '反算后', dataIndex: 'adjusted_value', key: 'av', width: 120,
                  render: (v: number) => <strong>{v.toFixed(2)}</strong> },
                { title: '调整量', dataIndex: 'delta_value', key: 'dv', width: 110,
                  render: (v: number) => {
                    if (v == null) return '-'
                    const cls = v > 0 ? '#15803d' : v < 0 ? '#dc2626' : '#6b7280'
                    const prefix = v > 0 ? '+' : ''
                    return <span style={{ color: cls }}>{prefix}{v.toFixed(2)}</span>
                  }},
              ]}
            />
          </>
        )}
      </Drawer>
    </div>
  )
}

export default ReverseCalc
import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Card, Row, Col, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Empty, Popconfirm, Progress, Alert, Statistic, Drawer,
  Descriptions, Tooltip,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined,
  PlayCircleOutlined, PauseCircleOutlined, EyeOutlined,
  ExperimentOutlined, RocketOutlined, FunctionOutlined,
  AimOutlined,
} from '@ant-design/icons'
import { reverseApi } from '../api'
import { DictSelect, DictTag } from '../components'

const CONSTRAINT_LABELS: Record<string, { label: string; color: string }> = {
  GE: { label: '≥', color: 'green' },
  LE: { label: '≤', color: 'orange' },
  EQ: { label: '=', color: 'blue' },
}

const ReverseCalc: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [targets, setTargets] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [kpiOpts, setKpiOpts] = useState<any[]>([])
  const [kpiScope, setKpiScope] = useState<any>(null)   // 后端返回的链路上文（model/scheme）
  const [modelOpts, setModelOpts] = useState<any[]>([])

  const [activeSchemeId, setActiveSchemeId] = useState<number | null>(null)
  const [activeRunId, setActiveRunId] = useState<number | null>(null)

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
  const logSinceRef = useRef(0)
  const logTimerRef = useRef<any>(null)

  const [resultDrawer, setResultDrawer] = useState(false)
  const [resultData, setResultData] = useState<any>(null)

  // ============================================================
  // 数据加载
  // ============================================================
  const loadSchemes = async () => {
    const r = await reverseApi.listSchemes()
    setSchemes(r.items || [])
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

  useEffect(() => {
    loadSchemes()
    loadModelOpts()
    loadRuns()
  }, [])

  // 当前选中方案变化时，刷新目标、运行、KPI 下拉（按方案的 model_id 联动过滤）
  useEffect(() => {
    loadTargets(activeSchemeId)
    loadRuns(activeSchemeId)
    const s = schemes.find(x => x.id === activeSchemeId)
    loadKpiOpts(s?.model_id || null)
  }, [activeSchemeId, schemes])

  // 日志轮询
  useEffect(() => {
    if (!logRun || !logDrawer) return
    logSinceRef.current = 0
    setLogLines([])
    const tick = async () => {
      try {
        const r = await reverseApi.runLogs(logRun.id, logSinceRef.current)
        if (r.items && r.items.length) {
          setLogLines((p) => [...p, ...r.items])
          logSinceRef.current = r.items[r.items.length - 1].id
        }
        const list = await reverseApi.listRuns({ scheme_id: logRun.scheme_id })
        const updated = (list.items || []).find((t: any) => t.id === logRun.id)
        if (updated) {
          setLogRun(updated)
          if (['SUCCESS', 'FAILED', 'CANCELLED'].includes(updated.status)) {
            if (logTimerRef.current) {
              clearInterval(logTimerRef.current)
              logTimerRef.current = null
            }
          }
        }
      } catch (e) {
        console.error(e)
      }
    }
    tick()
    logTimerRef.current = setInterval(tick, 2000)
    return () => {
      if (logTimerRef.current) clearInterval(logTimerRef.current)
    }
  }, [logDrawer, logRun?.id])

  // ============================================================
  // 方案 CRUD
  // ============================================================
  const onCreateScheme = () => {
    setEditingScheme(null)
    schemeForm.resetFields()
    schemeForm.setFieldsValue({
      scheme_type: 'OPTIMIZE', algorithm: 'CVXPY_QP', coa_scheme_id: 6,
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
      loadRuns(activeSchemeId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '启动失败')
    }
  }
  const onCancelRun = async (r: any) => {
    await reverseApi.cancelRun(r.id)
    message.success('已取消')
    loadRuns(activeSchemeId)
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
    loadRuns(activeSchemeId)
  }
  const onSaveRun = async () => {
    const v = await runForm.validateFields()
    try {
      const r = await reverseApi.createRun(v)
      message.success(`反算任务已创建：${r.run_code}，点击「启动」开始反算`)
      setRunModal(false)
      loadRuns(activeSchemeId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '创建失败')
    }
  }

  // ============================================================
  // 表格列
  // ============================================================
  const schemeColumns = [
    { title: '方案编码', dataIndex: 'scheme_code', key: 'sc', width: 130,
      render: (v: string) => <strong style={{ color: '#534ab7' }}>{v}</strong> },
    { title: '方案名称', dataIndex: 'scheme_name', key: 'sn' },
    { title: '算法', dataIndex: 'algorithm', key: 'algo', width: 110,
      render: (v: string) => <DictTag dictType="PRCP_REVERSE_ALGO" value={v} /> },
    { title: '计量模型', key: 'model', width: 200,
      render: (_: any, r: any) => r.model_id
        ? <Tag color="geekblue" icon={<ExperimentOutlined />}>{r.model_code} · {r.model_name}</Tag>
        : <span style={{ color: '#bbb' }}>未关联</span> },
    { title: '账户册', key: 'coa', width: 140,
      render: (_: any, r: any) => r.coa_code ? <Tag color="cyan">{r.coa_code}</Tag> : '-' },
    { title: '数据日期', dataIndex: 'data_date', key: 'dd', width: 110 },
    { title: '期数', dataIndex: 'horizon_months', key: 'h', width: 60,
      render: (v: number) => `${v} 月` },
    { title: '目标', dataIndex: 'target_count', key: 'tc', width: 60 },
    { title: '执行', dataIndex: 'run_count', key: 'rc', width: 60 },
    { title: '状态', dataIndex: 'status', key: 's', width: 90,
      render: (v: string) => v?.startsWith('PENDING') || v === 'RUNNING' || v === 'SUCCESS' || v === 'FAILED' || v === 'CANCELLED'
        ? <DictTag dictType="PRCP_RUN_STATUS" value={v} />
        : <DictTag dictType="PRCP_STATUS" value={v} /> },
    { title: '操作', key: 'op', width: 160, render: (_: any, r: any) => (
      <Space>
        <Button size="small" icon={<AimOutlined />} onClick={() => setActiveSchemeId(r.id)}>选择</Button>
        <Button size="small" icon={<EditOutlined />} onClick={() => onEditScheme(r)} />
        <Popconfirm title="确认删除？" onConfirm={() => onDeleteScheme(r)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ]

  const targetColumns = [
    { title: '目标名称', dataIndex: 'target_name', key: 'tn' },
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

  const activeScheme = schemes.find(s => s.id === activeSchemeId)

  return (
    <div style={{ padding: 16 }}>
      {/* 顶部 KPI */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
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

      {/* 方案列表 */}
      <Card
        title={<span><AimOutlined /> 反算方案</span>}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadSchemes}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={onCreateScheme}>新建方案</Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          rowKey="id"
          columns={schemeColumns}
          dataSource={schemes}
          pagination={{ pageSize: 5 }}
          size="small"
          rowClassName={(r) => r.id === activeSchemeId ? 'ant-table-row-selected' : ''}
          onRow={(r) => ({ onClick: () => setActiveSchemeId(r.id) })}
        />
      </Card>

      {/* 选中方案后：目标 + 运行 */}
      {activeSchemeId ? (
            <Row gutter={16}>
              {/* 左侧：目标指标 */}
              <Col span={10}>
                <Card
                  title={
                    <Space wrap>
                      <FunctionOutlined />
                      <span>目标指标（{targets.length}）</span>
                      {activeScheme && <Tag color="purple">{activeScheme.scheme_code}</Tag>}
                      {kpiScope?.filtered ? (
                        <Tooltip
                          title={`KPI 仅限：模型 ${kpiScope.model_code || kpiScope.model_id} → 指标方案 ${kpiScope.scheme_code || kpiScope.scheme_id}`}
                        >
                          <Tag color="geekblue" icon={<ExperimentOutlined />}>
                            {kpiScope.model_code || `model#${kpiScope.model_id}`} → {kpiScope.scheme_code || `scheme#${kpiScope.scheme_id}`}
                          </Tag>
                        </Tooltip>
                      ) : (
                        <Tooltip title="当前方案未关联计量模型，KPI 下拉显示全部">
                          <Tag color="default">未限定 KPI 范围</Tag>
                        </Tooltip>
                      )}
                    </Space>
                  }
                  extra={
                    <Space>
                      <Button size="small" icon={<ReloadOutlined />} onClick={() => loadTargets(activeSchemeId)}>刷新</Button>
                      <Button size="small" type="primary" icon={<PlusOutlined />} onClick={onCreateTarget}>新增目标</Button>
                    </Space>
                  }
                >
                  <Table
                    rowKey="id"
                    columns={targetColumns}
                    dataSource={targets}
                    pagination={false}
                    size="small"
                  />
                </Card>
              </Col>

              {/* 右侧：反算运行 */}
              <Col span={14}>
                <Card
                  title={<span><RocketOutlined /> 反算执行</span>}
                  extra={
                    <Space>
                      <Button size="small" icon={<ReloadOutlined />} onClick={() => loadRuns(activeSchemeId)}>刷新</Button>
                      <Button size="small" type="primary" icon={<PlusOutlined />} onClick={onCreateRun}>新建反算</Button>
                    </Space>
                  }
                >
                  <Alert
                    type="info" showIcon
                    style={{ marginBottom: 12 }}
                    message="反算流程：选方案 → 填目标 → 启动反算 → 查看日志 → 查看结果（24 月 × N 节点预测值）"
                  />
                  <Table
                    rowKey="id"
                    columns={runColumns}
                    dataSource={runs.filter(r => r.scheme_id === activeSchemeId)}
                    pagination={{ pageSize: 5 }}
                    size="small"
                  />
                </Card>
              </Col>
            </Row>
          ) : (
            <Card>
              <Empty description="请先在上方表格中选择一个反算方案" />
            </Card>
          )}

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
                <Select>
                  <Select.Option value={4}>COA_V6 (61 节点)</Select.Option>
                  <Select.Option value={6}>ZXCOA_V1 (40 节点)</Select.Option>
                </Select>
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
          <Form.Item label="目标名称" name="target_name" rules={[{ required: true }]}>
            <Input placeholder="如 NIM ≥ 2.8%" />
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
        width={720}
        onClose={() => { setLogDrawer(false); setLogRun(null); setLogLines([]) }}
      >
        {logRun && (
          <>
            <Descriptions size="small" column={3} bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label="状态"><DictTag dictType="PRCP_RUN_STATUS" value={logRun.status} /></Descriptions.Item>
              <Descriptions.Item label="进度"><Progress percent={logRun.progress} size="small" style={{ width: 120 }} /></Descriptions.Item>
              <Descriptions.Item label="耗时">{logRun.duration_sec || '-'} s</Descriptions.Item>
              <Descriptions.Item label="方案" span={3}>{logRun.scheme_code} · {logRun.scheme_name}</Descriptions.Item>
              <Descriptions.Item label="算法" span={3}><DictTag dictType="PRCP_REVERSE_ALGO" value={logRun.algorithm} /></Descriptions.Item>
            </Descriptions>
            <div style={{ background: '#0f172a', color: '#94a3b8', fontFamily: 'Consolas, monospace', fontSize: 12, padding: 12, borderRadius: 6, maxHeight: 400, overflow: 'auto' }}>
              {logLines.length === 0 && <div style={{ color: '#64748b' }}>暂无日志...</div>}
              {logLines.map((l: any) => (
                <div key={l.id} style={{ marginBottom: 2 }}>
                  <span style={{ color: '#64748b' }}>{l.created_at?.substring(11, 19)}</span>{' '}
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
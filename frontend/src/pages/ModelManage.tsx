import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Card, Row, Col, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, DatePicker, Popconfirm, Alert, Tooltip, Tabs,
  Progress, Descriptions, Drawer, Statistic, Checkbox,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, CopyOutlined,
  PlayCircleOutlined, PauseCircleOutlined, EyeOutlined,
  ExperimentOutlined, RocketOutlined, FunctionOutlined, ThunderboltOutlined,
} from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import { modelApi } from '../api'

const { RangePicker } = DatePicker

const ALGO_LABELS: Record<string, string> = {
  LINEAR_REGRESSION: '线性回归',
  LOGISTIC_GROWTH: '逻辑斯蒂增长',
  MONTE_CARLO: '蒙特卡洛',
  LINEAR_PROGRAM: '线性规划',
  ANT_COLONY: '蚁群算法',
  ARIMA: 'ARIMA',
  FNN_LLM: 'FNN大模型',
}

const BIZ_LABELS: Record<string, { name: string; color: string }> = {
  DEPOSIT: { name: '存款', color: 'blue' },
  LOAN: { name: '贷款', color: 'cyan' },
  NIM: { name: '净息差', color: 'purple' },
  RWA: { name: '资本', color: 'green' },
  ASSET: { name: '资产', color: 'gold' },
  LIAB: { name: '负债', color: 'orange' },
}

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: 'green', DEPRECATED: 'red',
  DRAFT: 'default', READY: 'cyan',
  PENDING: 'default', RUNNING: 'processing',
  SUCCESS: 'green', FAILED: 'red', CANCELLED: 'orange',
}

const ModelManage: React.FC = () => {
  const [tab, setTab] = useState<'version' | 'param' | 'train'>('version')
  const [models, setModels] = useState<any[]>([])
  const [versions, setVersions] = useState<any[]>([])
  const [params, setParams] = useState<any[]>([])
  const [trains, setTrains] = useState<any[]>([])
  const [algorithms, setAlgorithms] = useState<any[]>([])
  const [kpiOpts, setKpiOpts] = useState<any[]>([])
  const [schemeOpts, setSchemeOpts] = useState<any[]>([])

  // 选中状态
  const [activeModelId, setActiveModelId] = useState<number | null>(null)
  const [activeVersionId, setActiveVersionId] = useState<number | null>(null)
  const [activeTrainId, setActiveTrainId] = useState<number | null>(null)

  // 模态
  const [modelModal, setModelModal] = useState(false)
  const [editingModel, setEditingModel] = useState<any>(null)
  const [modelForm] = Form.useForm()
  const [versionModal, setVersionModal] = useState(false)
  const [editingVersion, setEditingVersion] = useState<any>(null)
  const [versionForm] = Form.useForm()
  const [paramModal, setParamModal] = useState(false)
  const [editingParam, setEditingParam] = useState<any>(null)
  const [paramForm] = Form.useForm()
  // 超参数模板
  const [templateModal, setTemplateModal] = useState(false)
  const [paramTemplates, setParamTemplates] = useState<any>(null)
  const [selectedCats, setSelectedCats] = useState<string[]>([])
  const [trainModal, setTrainModal] = useState(false)
  const [trainForm] = Form.useForm()

  // 训练详情 Drawer
  const [logDrawer, setLogDrawer] = useState(false)
  const [logTrain, setLogTrain] = useState<any>(null)
  const [logLines, setLogLines] = useState<any[]>([])
  const logSinceRef = useRef(0)
  const logTimerRef = useRef<any>(null)

  // 训练结果 Drawer
  const [resultDrawer, setResultDrawer] = useState(false)
  const [resultData, setResultData] = useState<any>(null)

  // ============================================================
  // 数据加载
  // ============================================================
  const loadModels = async () => {
    const r = await modelApi.listModels()
    setModels(r.items || [])
  }
  const loadVersions = async (modelId?: number | null) => {
    const r = await modelApi.listVersions(modelId ? { model_id: modelId } : {})
    setVersions(r.items || [])
  }
  const loadParams = async (versionId?: number | null) => {
    if (!versionId) { setParams([]); return }
    const r = await modelApi.listParams({ version_id: versionId })
    setParams(r.items || [])
  }
  const loadTrains = async (modelId?: number | null) => {
    const r = await modelApi.listTrains(modelId ? { model_id: modelId } : {})
    setTrains(r.items || [])
  }
  const loadAlgos = async () => {
    const r = await modelApi.listAlgorithms()
    setAlgorithms(r.items || [])
  }
  const loadKpiOpts = async () => {
    const r = await modelApi.kpiOptions()
    setKpiOpts(r.items || [])
  }
  const loadSchemeOpts = async () => {
    const r = await modelApi.schemeOptions()
    setSchemeOpts(r.items || [])
  }
  const loadParamTemplates = async () => {
    const r = await modelApi.listParamTemplates()
    setParamTemplates(r)
  }

  const onOpenTemplateModal = async () => {
    if (!activeVersionId) {
      message.warning('请先在版本列表中选择一个版本')
      return
    }
    if (!paramTemplates) await loadParamTemplates()
    setSelectedCats((paramTemplates?.templates || []).map((t: any) => t.category))
    setTemplateModal(true)
  }
  const onApplyTemplate = async () => {
    if (!activeVersionId || selectedCats.length === 0) {
      message.warning('请至少选择一个分类')
      return
    }
    try {
      const r = await modelApi.applyParamTemplate(activeVersionId, {
        categories: selectedCats,
        overwrite: false,
      })
      message.success(`模板已注入：新增 ${r.inserted} 个，更新 ${r.updated} 个`)
      setTemplateModal(false)
      loadParams(activeVersionId)
      loadVersions(activeModelId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '应用失败')
    }
  }

  useEffect(() => {
    loadModels()
    loadAlgos()
    loadKpiOpts()
    loadSchemeOpts()
    loadTrains()
    loadVersions()
  }, [])

  useEffect(() => {
    loadVersions(activeModelId)
    loadTrains(activeModelId)
  }, [activeModelId])

  useEffect(() => {
    loadParams(activeVersionId)
  }, [activeVersionId])

  // 启动训练后自动轮询日志
  useEffect(() => {
    if (!logTrain || !logDrawer) return
    logSinceRef.current = 0
    setLogLines([])
    const tick = async () => {
      try {
        const r = await modelApi.trainLogs(logTrain.id, logSinceRef.current)
        if (r.items && r.items.length) {
          setLogLines((prev) => [...prev, ...r.items])
          logSinceRef.current = r.items[r.items.length - 1].id
        }
        // 同时刷新训练状态
        const list = await modelApi.listTrains({ model_id: logTrain.model_id })
        const updated = (list.items || []).find((t: any) => t.id === logTrain.id)
        if (updated) {
          setLogTrain(updated)
          if (['SUCCESS', 'FAILED', 'CANCELLED'].includes(updated.status)) {
            // 训练结束，停止轮询
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
  }, [logDrawer, logTrain?.id])

  // ============================================================
  // 模型 CRUD
  // ============================================================
  const onCreateModel = () => {
    setEditingModel(null)
    modelForm.resetFields()
    modelForm.setFieldsValue({ model_type: 'LINEAR_REGRESSION', status: 'ACTIVE' })
    loadSchemeOpts()  // 打开时拉一次最新方案
    setModelModal(true)
  }
  const onEditModel = (m: any) => {
    setEditingModel(m)
    modelForm.setFieldsValue({
      ...m,
      kpi_scheme_id: m.kpi_scheme_id ?? undefined,
    })
    loadSchemeOpts()
    setModelModal(true)
  }
  const onSaveModel = async () => {
    const v = await modelForm.validateFields()
    // 清理 payload：kpi_scheme_id 为空字符串/undefined 时置 null
    const payload = {
      ...v,
      kpi_scheme_id: v.kpi_scheme_id === '' || v.kpi_scheme_id === undefined ? null : v.kpi_scheme_id,
    }
    try {
      if (editingModel) {
        await modelApi.updateModel(editingModel.id, payload)
        message.success('已更新')
      } else {
        await modelApi.createModel(payload)
        message.success('已创建（自动生成 V1_BASELINE 版本）')
      }
      setModelModal(false)
      loadModels()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onDeleteModel = async (m: any) => {
    await modelApi.deleteModel(m.id)
    message.success('已删除')
    if (activeModelId === m.id) setActiveModelId(null)
    loadModels()
  }

  // ============================================================
  // 版本 CRUD
  // ============================================================
  const onCreateVersion = () => {
    if (!activeModelId) { message.warning('请先选中一个模型'); return }
    setEditingVersion(null)
    versionForm.resetFields()
    versionForm.setFieldsValue({ model_id: activeModelId, status: 'DRAFT' })
    setVersionModal(true)
  }
  const onEditVersion = (v: any) => {
    setEditingVersion(v)
    versionForm.setFieldsValue(v)
    setVersionModal(true)
  }
  const onSaveVersion = async () => {
    const v = await versionForm.validateFields()
    try {
      if (editingVersion) {
        await modelApi.updateVersion(editingVersion.id, v)
      } else {
        await modelApi.createVersion(v)
      }
      message.success('已保存')
      setVersionModal(false)
      loadVersions(activeModelId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onCopyVersion = async (v: any) => {
    const newCode = prompt(`复制版本 ${v.version_code}，请输入新版本编码：`, `${v.version_code}_COPY`)
    if (!newCode) return
    try {
      const r = await modelApi.copyVersion(v.id, { version_code: newCode, version_name: `复制自 ${v.version_name}` })
      message.success(`已复制：${r.copied_params} 个参数`)
      loadVersions(activeModelId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '复制失败')
    }
  }
  const onDeleteVersion = async (v: any) => {
    await modelApi.deleteVersion(v.id)
    message.success('已删除')
    if (activeVersionId === v.id) setActiveVersionId(null)
    loadVersions(activeModelId)
  }

  // ============================================================
  // 参数 CRUD
  // ============================================================
  const onCreateParam = () => {
    if (!activeVersionId) { message.warning('请先选中一个版本'); return }
    setEditingParam(null)
    paramForm.resetFields()
    paramForm.setFieldsValue({ version_id: activeVersionId, param_type: 'BASE', sort_order: 0, param_value: 0 })
    setParamModal(true)
  }
  const onEditParam = (p: any) => {
    setEditingParam(p)
    paramForm.setFieldsValue(p)
    setParamModal(true)
  }
  const onSaveParam = async () => {
    const v = await paramForm.validateFields()
    // kpi_id 为空时置 null
    const payload = { ...v, kpi_id: v.kpi_id === '' || v.kpi_id === undefined ? null : v.kpi_id }
    try {
      if (editingParam) {
        await modelApi.updateParam(editingParam.id, payload)
      } else {
        await modelApi.createParam(payload)
      }
      message.success('已保存')
      setParamModal(false)
      loadParams(activeVersionId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }
  const onDeleteParam = async (p: any) => {
    await modelApi.deleteParam(p.id)
    message.success('已删除')
    loadParams(activeVersionId)
  }

  // ============================================================
  // 训练 CRUD
  // ============================================================
  const onCreateTrain = () => {
    if (!activeModelId) { message.warning('请先选中一个模型'); return }
    trainForm.resetFields()
    trainForm.setFieldsValue({
      model_id: activeModelId,
      coa_scheme_id: 6,
      balance_date_from: '2025-12-01',
      balance_date_to: '2027-01-01',
    })
    setTrainModal(true)
  }
  const onStartTrain = async (t: any) => {
    try {
      await modelApi.startTrain(t.id)
      message.success('训练已启动')
      setLogTrain(t)
      setLogDrawer(true)
      loadTrains(activeModelId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '启动失败')
    }
  }
  const onCancelTrain = async (t: any) => {
    await modelApi.cancelTrain(t.id)
    message.success('已取消')
    loadTrains(activeModelId)
  }
  const onViewLogs = async (t: any) => {
    setLogTrain(t)
    setLogDrawer(true)
  }
  const onViewResult = async (t: any) => {
    const r = await modelApi.trainResult(t.id)
    setResultData(r)
    setResultDrawer(true)
  }
  const onDeleteTrain = async (t: any) => {
    await modelApi.deleteTrain(t.id)
    message.success('已删除')
    loadTrains(activeModelId)
  }
  const onSaveTrain = async () => {
    const v = await trainForm.validateFields()
    try {
      const r = await modelApi.createTrain(v)
      message.success(`训练任务已创建：${r.train_code}，点击「启动」开始训练`)
      setTrainModal(false)
      loadTrains(activeModelId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '创建失败')
    }
  }

  // ============================================================
  // 模型列表列
  // ============================================================
  const modelColumns = [
    { title: '模型编码', dataIndex: 'model_code', key: 'model_code', width: 130,
      render: (v: string, r: any) => <strong style={{ color: '#667eea' }}>{v}</strong> },
    { title: '模型名称', dataIndex: 'model_name', key: 'model_name' },
    { title: '算法', dataIndex: 'model_type', key: 'model_type', width: 110,
      render: (v: string) => <Tag color="blue">{ALGO_LABELS[v] || v}</Tag> },
    { title: '业务域', dataIndex: 'biz_domain', key: 'biz_domain', width: 90,
      render: (v: string) => v ? <Tag color={BIZ_LABELS[v]?.color || 'default'}>{BIZ_LABELS[v]?.name || v}</Tag> : '-' },
    { title: '关联指标方案', key: 'kpi_scheme', width: 200,
      render: (_: any, r: any) => r.kpi_scheme_id
        ? <Tag color="purple" icon={<FunctionOutlined />}>{r.kpi_scheme_code || r.kpi_scheme_id} · {r.kpi_scheme_name || '-'}</Tag>
        : <span style={{ color: '#bbb' }}>未关联</span> },
    { title: '版本数', dataIndex: 'version_count', key: 'version_count', width: 70 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: string) => <Tag color={STATUS_COLOR[v]}>{v}</Tag> },
    { title: '操作', key: 'op', width: 160, render: (_: any, r: any) => (
      <Space>
        <Button size="small" icon={<ExperimentOutlined />} onClick={() => { setActiveModelId(r.id); setTab('param') }}>管理</Button>
        <Button size="small" icon={<EditOutlined />} onClick={() => onEditModel(r)} />
        <Popconfirm title="确认删除？" onConfirm={() => onDeleteModel(r)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ]

  const versionColumns = [
    { title: '版本编码', dataIndex: 'version_code', key: 'version_code', width: 140,
      render: (v: string, r: any) => (
        <Space>
          <Tag color={STATUS_COLOR[r.status]}>{r.status}</Tag>
          <strong style={{ color: '#534ab7' }}>{v}</strong>
        </Space>
      ) },
    { title: '版本名称', dataIndex: 'version_name', key: 'version_name' },
    { title: '父版本', dataIndex: 'parent_version_code', key: 'parent', width: 150,
      render: (v: string) => v ? <Tag color="purple">{v}</Tag> : '-' },
    { title: '参数数', dataIndex: 'param_count', key: 'pc', width: 70 },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => v?.substring(0, 16) },
    { title: '操作', key: 'op', width: 200, render: (_: any, r: any) => (
      <Space>
        <Button size="small" icon={<FunctionOutlined />} onClick={() => { setActiveVersionId(r.id); setTab('param') }}>参数</Button>
        <Button size="small" icon={<CopyOutlined />} onClick={() => onCopyVersion(r)} title="复制" />
        <Button size="small" icon={<EditOutlined />} onClick={() => onEditVersion(r)} />
        <Popconfirm title="确认删除？" onConfirm={() => onDeleteVersion(r)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ]

  const CATEGORY_LABELS: Record<string, { name: string; icon: string; color: string }> = {
  DATA_ESG:       { name: '数据/ESG', icon: '📊', color: 'blue' },
  NEURAL_NETWORK: { name: '神经网络', icon: '🧠', color: 'purple' },
  LOSS_FUNCTION:  { name: '损失函数', icon: '🎯', color: 'red' },
  TRAINING:       { name: '训练',     icon: '🏋️', color: 'cyan' },
  OPTIMIZER:      { name: '优化器',   icon: '⚡', color: 'gold' },
  KPI_DRIVEN:     { name: 'KPI 驱动', icon: '📈', color: 'geekblue' },
}

const paramColumns = [
    { title: '参数编码', dataIndex: 'param_code', key: 'pc', width: 150,
      render: (v: string) => <code style={{ background: '#f0f4ff', padding: '2px 6px', borderRadius: 3 }}>{v}</code> },
    { title: '参数名称', dataIndex: 'param_name', key: 'pn' },
    { title: '分类', dataIndex: 'param_category', key: 'pcat', width: 120,
      render: (v: string) => {
        const cfg = CATEGORY_LABELS[v]
        return cfg
          ? <Tag color={cfg.color}>{cfg.icon} {cfg.name}</Tag>
          : <Tag color="default">-</Tag>
      } },
    { title: '类型', dataIndex: 'param_type', key: 'pt', width: 80,
      render: (v: string) => {
        const colors: any = { BASE: 'blue', SCENARIO: 'purple', STRESS: 'red', SENSITIVITY: 'cyan' }
        const labels: any = { BASE: '基准', SCENARIO: '情景', STRESS: '压力', SENSITIVITY: '敏感度' }
        return <Tag color={colors[v]}>{labels[v] || v}</Tag>
      } },
    { title: '关联 KPI', dataIndex: 'kpi_code', key: 'kc', width: 130,
      render: (v: string, r: any) => v ? <Tooltip title={r.ref_formula}><Tag color="geekblue">{v}</Tag></Tooltip> : '-' },
    { title: '参数值', dataIndex: 'param_value', key: 'pv', width: 110,
      render: (v: number, r: any) => <strong>{typeof v === 'number' ? v.toFixed(4) : v} {r.unit}</strong> },
    { title: '排序', dataIndex: 'sort_order', key: 'so', width: 60 },
    { title: '描述', dataIndex: 'description', key: 'd', ellipsis: true },
    { title: '操作', key: 'op', width: 100, render: (_: any, r: any) => (
      <Space>
        <Button size="small" icon={<EditOutlined />} onClick={() => onEditParam(r)} />
        <Popconfirm title="确认删除？" onConfirm={() => onDeleteParam(r)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ]

  const trainColumns = [
    { title: '训练编码', dataIndex: 'train_code', key: 'tc', width: 180,
      render: (v: string) => <code style={{ background: '#f0f4ff', padding: '2px 6px', borderRadius: 3 }}>{v}</code> },
    { title: '模型', key: 'model', width: 180,
      render: (_: any, r: any) => <span><strong>{r.model_code}</strong> · {r.model_name}</span> },
    { title: '版本', key: 'v', width: 130,
      render: (_: any, r: any) => <Tag color="purple">{r.version_code}</Tag> },
    { title: '训练窗口', key: 'dates', width: 220,
      render: (_: any, r: any) => `${r.balance_date_from} ~ ${r.balance_date_to}` },
    { title: '进度', key: 'prog', width: 180,
      render: (_: any, r: any) => (
        <Progress
          percent={r.progress}
          size="small"
          status={r.status === 'FAILED' ? 'exception' : r.status === 'SUCCESS' ? 'success' : 'active'}
        />
      ) },
    { title: '状态', dataIndex: 'status', key: 's', width: 100,
      render: (v: string) => <Tag color={STATUS_COLOR[v]}>{v}</Tag> },
    { title: '耗时', dataIndex: 'duration_sec', key: 'ds', width: 70,
      render: (v: number) => v ? `${v}s` : '-' },
    { title: '操作', key: 'op', width: 220, render: (_: any, r: any) => (
      <Space>
        {r.status === 'PENDING' && (
          <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => onStartTrain(r)}>启动</Button>
        )}
        {r.status === 'RUNNING' && (
          <>
            <Button size="small" icon={<EyeOutlined />} onClick={() => onViewLogs(r)}>日志</Button>
            <Button size="small" danger icon={<PauseCircleOutlined />} onClick={() => onCancelTrain(r)}>取消</Button>
          </>
        )}
        {['SUCCESS', 'FAILED', 'CANCELLED'].includes(r.status) && (
          <>
            <Button size="small" icon={<EyeOutlined />} onClick={() => onViewLogs(r)}>日志</Button>
            <Button size="small" icon={<RocketOutlined />} onClick={() => onViewResult(r)}>结果</Button>
          </>
        )}
        <Popconfirm title="确认删除？" onConfirm={() => onDeleteTrain(r)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ]

  // ============================================================
  // 渲染
  // ============================================================
  const activeModel = models.find(m => m.id === activeModelId)
  const activeVersion = versions.find(v => v.id === activeVersionId)

  return (
    <div style={{ padding: 16 }}>
      {/* 顶部 KPI */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="模型总数" value={models.length} prefix={<ExperimentOutlined style={{ color: '#667eea' }} />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="版本总数" value={versions.length} prefix={<FunctionOutlined style={{ color: '#534ab7' }} />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="训练任务（运行中）"
              value={trains.filter(t => t.status === 'RUNNING').length}
              valueStyle={{ color: '#1890ff' }}
              prefix={<RocketOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="已完成 / 总数"
              value={trains.filter(t => t.status === 'SUCCESS').length}
              suffix={`/ ${trains.length}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Tabs
        activeKey={tab}
        onChange={(k) => setTab(k as any)}
        items={[
          {
            key: 'version',
            label: '① 参数版本维护',
            children: (
              <Card
                title={<span><ExperimentOutlined /> 模型 + 版本</span>}
                extra={<Button type="primary" icon={<PlusOutlined />} onClick={onCreateModel}>新建模型</Button>}
              >
                <Table
                  rowKey="id"
                  columns={modelColumns}
                  dataSource={models}
                  loading={false}
                  pagination={{ pageSize: 10 }}
                  size="small"
                  scroll={{ x: 1200 }}
                  rowClassName={(r) => r.id === activeModelId ? 'ant-table-row-selected' : ''}
                  onRow={(r) => ({ onClick: () => setActiveModelId(r.id) })}
                  expandable={{
                    expandedRowRender: (record) => (
                      <div style={{ padding: '8px 24px', background: '#fafafa' }}>
                        <Space style={{ marginBottom: 8 }}>
                          <span style={{ fontWeight: 500 }}>版本列表：</span>
                          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={onCreateVersion}>新建版本</Button>
                          <Button size="small" icon={<ReloadOutlined />} onClick={() => loadVersions(record.id)}>刷新</Button>
                        </Space>
                        <Table
                          rowKey="id"
                          columns={versionColumns}
                          dataSource={versions.filter(v => v.model_id === record.id)}
                          pagination={false}
                          size="small"
                          rowClassName={(r) => r.id === activeVersionId ? 'ant-table-row-selected' : ''}
                          onRow={(r) => ({ onClick: () => setActiveVersionId(r.id) })}
                        />
                      </div>
                    ),
                  }}
                />
              </Card>
            ),
          },
          {
            key: 'param',
            label: '② 参数明细维护',
            children: (
              <Card
                title={
                  <Space>
                    <FunctionOutlined />
                    {activeModel && <span>{activeModel.model_name}</span>}
                    {activeVersion && <Tag color="purple">{activeVersion.version_code}</Tag>}
                    <span style={{ color: '#999' }}>· 共 {params.length} 个参数</span>
                  </Space>
                }
                extra={
                  <Space>
                    <Button icon={<ReloadOutlined />} onClick={() => loadParams(activeVersionId)}>刷新</Button>
                    <Button icon={<ThunderboltOutlined />} onClick={onOpenTemplateModal} disabled={!activeVersionId}>
                      ⚡ 应用超参数模板
                    </Button>
                    <Button type="primary" icon={<PlusOutlined />} onClick={onCreateParam} disabled={!activeVersionId}>
                      新增参数
                    </Button>
                  </Space>
                }
              >
                {!activeModelId && <Empty description="请先在「参数版本维护」Tab 选择一个模型" />}
                {activeModelId && !activeVersionId && <Empty description="请先在上方版本列表中选择一个版本" />}
                {activeVersionId && (
                  <Table
                    rowKey="id"
                    columns={paramColumns}
                    dataSource={params}
                    loading={false}
                    pagination={{ pageSize: 20 }}
                    size="small"
                  />
                )}
              </Card>
            ),
          },
          {
            key: 'train',
            label: '③ 模型训练',
            children: (
              <Card
                title={<span><RocketOutlined /> 训练任务</span>}
                extra={
                  <Space>
                    <Button icon={<ReloadOutlined />} onClick={() => loadTrains(activeModelId)}>刷新</Button>
                    <Button type="primary" icon={<PlusOutlined />} onClick={onCreateTrain} disabled={!activeModelId}>
                      新建训练
                    </Button>
                  </Space>
                }
              >
                {!activeModelId && (
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="请先在「参数版本维护」Tab 选择一个模型"
                  />
                )}
                <Table
                  rowKey="id"
                  columns={trainColumns}
                  dataSource={trains}
                  loading={false}
                  pagination={{ pageSize: 10 }}
                  size="small"
                />
              </Card>
            ),
          },
        ]}
      />

      {/* 模型 Modal */}
      <Modal
        open={modelModal}
        title={editingModel ? '✏️ 编辑模型' : '＋ 新建模型'}
        onCancel={() => setModelModal(false)}
        onOk={onSaveModel}
        width={600}
        okText="保存"
      >
        <Form form={modelForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="模型编码" name="model_code" rules={[{ required: true }]}>
                <Input placeholder="如 DGM_2026" disabled={!!editingModel} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="模型名称" name="model_name" rules={[{ required: true }]}>
                <Input placeholder="如 存款增长模型" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="算法" name="model_type" rules={[{ required: true }]}>
                <Select placeholder="选择算法">
                  {(() => {
                    // 按 category 分组
                    const groups: Record<string, any[]> = {}
                    for (const a of algorithms) {
                      const cat = a.category || '其他'
                      if (!groups[cat]) groups[cat] = []
                      groups[cat].push(a)
                    }
                    const out: any[] = []
                    for (const cat of Object.keys(groups)) {
                      out.push(<Select.OptGroup key={cat} title={cat}>
                        {groups[cat].map(a => (
                          <Select.Option key={a.code} value={a.code}>
                            {a.name}{a.desc ? <span style={{ color: '#999', marginLeft: 6 }}>· {a.desc}</span> : null}
                          </Select.Option>
                        ))}
                      </Select.OptGroup>)
                    }
                    return out
                  })()}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="业务域" name="biz_domain">
                <Select allowClear>
                  <Select.Option value="DEPOSIT">存款</Select.Option>
                  <Select.Option value="LOAN">贷款</Select.Option>
                  <Select.Option value="NIM">净息差</Select.Option>
                  <Select.Option value="RWA">资本</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="关联指标方案（可空，不绑定也能用）" name="kpi_scheme_id"
            extra="绑定后，训练任务可直接引用该方案下的 KPI 定义作为参数">
            <Select
              allowClear
              showSearch
              placeholder="选择指标方案"
              optionFilterProp="label"
              options={schemeOpts.map((s) => ({
                value: s.id,
                label: `${s.scheme_code} · ${s.scheme_name}（${s.kpi_count || 0} 个 KPI）`,
              }))}
            />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select>
              <Select.Option value="ACTIVE">启用</Select.Option>
              <Select.Option value="DEPRECATED">已弃用</Select.Option>
            </Select>
          </Form.Item>
          {!editingModel && (
            <Alert type="info" showIcon message="创建后会自动生成 V1_BASELINE 基准版本" />
          )}
        </Form>
      </Modal>

      {/* 版本 Modal */}
      <Modal
        open={versionModal}
        title={editingVersion ? '✏️ 编辑版本' : '＋ 新建版本'}
        onCancel={() => setVersionModal(false)}
        onOk={onSaveVersion}
        width={500}
        okText="保存"
      >
        <Form form={versionForm} layout="vertical">
          <Form.Item label="模型" name="model_id" rules={[{ required: true }]}>
            <Select disabled={!!editingVersion}>
              {models.map(m => (
                <Select.Option key={m.id} value={m.id}>{m.model_code} · {m.model_name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="版本编码" name="version_code" rules={[{ required: true }]}>
            <Input placeholder="如 V1_BASELINE" />
          </Form.Item>
          <Form.Item label="版本名称" name="version_name" rules={[{ required: true }]}>
            <Input placeholder="如 基准情景" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select>
              <Select.Option value="DRAFT">草稿</Select.Option>
              <Select.Option value="READY">就绪</Select.Option>
              <Select.Option value="DEPRECATED">已弃用</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 超参数模板 Modal */}
      <Modal
        open={templateModal}
        title="⚡ 应用超参数模板（按分类勾选，一键注入参数）"
        onCancel={() => setTemplateModal(false)}
        onOk={onApplyTemplate}
        width={780}
        okText="应用模板"
      >
        {paramTemplates && (
          <div>
            <Alert
              type="info" showIcon style={{ marginBottom: 16 }}
              message={`共 ${paramTemplates.total_params || 0} 个预置参数，按 ${(paramTemplates.templates || []).length} 个分类组织`}
              description="已存在的 param_code 不会覆盖（默认跳过），未存在的会插入"
            />
            <div style={{ marginBottom: 8 }}>
              <Checkbox
                indeterminate={selectedCats.length > 0 && selectedCats.length < (paramTemplates.templates || []).length}
                checked={selectedCats.length === (paramTemplates.templates || []).length}
                onChange={(e) => {
                  setSelectedCats(e.target.checked ? (paramTemplates.templates || []).map((t: any) => t.category) : [])
                }}
              >
                <strong>全选</strong>
              </Checkbox>
              <span style={{ marginLeft: 12, color: '#999' }}>
                已选 {selectedCats.length} / {paramTemplates.templates?.length || 0} 个分类
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {(paramTemplates.templates || []).map((cat: any) => {
                const cfg = CATEGORY_LABELS[cat.category] || { name: cat.category_name, icon: '·', color: 'default' }
                return (
                  <Card
                    key={cat.category}
                    size="small"
                    title={<span>{cfg.icon} {cat.category_name} <Tag color={cfg.color}>{cat.items.length} 项</Tag></span>}
                    style={{ borderColor: selectedCats.includes(cat.category) ? '#667eea' : '#f0f0f0' }}
                  >
                    <Checkbox
                      checked={selectedCats.includes(cat.category)}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedCats([...selectedCats, cat.category])
                        else setSelectedCats(selectedCats.filter(c => c !== cat.category))
                      }}
                    >
                      启用此分类
                    </Checkbox>
                    <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20, fontSize: 12, color: '#666' }}>
                      {cat.items.map((it: any) => (
                        <li key={it.code}>
                          <code style={{ background: '#f5f5f5', padding: '1px 4px', borderRadius: 3 }}>{it.code}</code>
                          <span> {it.name}</span>
                          <span style={{ color: '#999' }}> · 默认 <code>{String(it.value)}</code></span>
                        </li>
                      ))}
                    </ul>
                  </Card>
                )
              })}
            </div>
          </div>
        )}
      </Modal>

      {/* 参数 Modal */}
      <Modal
        open={paramModal}
        title={editingParam ? '✏️ 编辑参数' : '＋ 新增参数'}
        onCancel={() => setParamModal(false)}
        onOk={onSaveParam}
        width={600}
        okText="保存"
      >
        <Form form={paramForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="参数编码" name="param_code" rules={[{ required: true }]}>
                <Input placeholder="如 K_NIM_001 或 PCA_NUM_COMPONENTS" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="参数名称" name="param_name" rules={[{ required: true }]}>
                <Input placeholder="如 对公存款净息差" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="参数分类" name="param_category">
                <Select allowClear placeholder="选择参数分类（可空）">
                  {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                    <Select.Option key={k} value={k}>{v.icon} {v.name}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="关联 KPI（纯算法超参可不选）" name="kpi_id">
                <Select showSearch allowClear optionFilterProp="children" placeholder="选择 KPI 定义（可空）">
                  {kpiOpts.map((k: any) => (
                    <Select.Option key={k.id} value={k.id}>{k.kpi_code} · {k.kpi_name}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="参数类型" name="param_type">
                <Select>
                  <Select.Option value="BASE">基准</Select.Option>
                  <Select.Option value="SCENARIO">情景</Select.Option>
                  <Select.Option value="STRESS">压力</Select.Option>
                  <Select.Option value="SENSITIVITY">敏感度</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="参数值" name="param_value" rules={[{ required: true }]}>
                <InputNumber step={0.01} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="单位" name="unit">
                <Select allowClear>
                  <Select.Option value="%">%</Select.Option>
                  <Select.Option value="BP">BP</Select.Option>
                  <Select.Option value="YUAN">元</Select.Option>
                  <Select.Option value="YI">亿元</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="公式（可选，覆盖 KPI 公式）" name="formula">
            <Input placeholder="如 [001001] * 1.05" />
          </Form.Item>
          <Form.Item label="排序" name="sort_order">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 训练 Modal */}
      <Modal
        open={trainModal}
        title="🚀 新建训练任务"
        onCancel={() => setTrainModal(false)}
        onOk={onSaveTrain}
        width={500}
        okText="创建"
      >
        <Form form={trainForm} layout="vertical">
          <Form.Item label="模型" name="model_id" rules={[{ required: true }]}>
            <Select>
              {models.map(m => (
                <Select.Option key={m.id} value={m.id}>{m.model_code} · {m.model_name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="版本" name="version_id" rules={[{ required: true }]}>
            <Select>
              {versions.map(v => (
                <Select.Option key={v.id} value={v.id}>{v.version_code} · {v.version_name} ({v.param_count} 参数)</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="训练窗口（资产负债表数据日期）" name="coa_scheme_id" rules={[{ required: true }]}>
            <Select>
              <Select.Option value={4}>COA_V6 (61 节点)</Select.Option>
              <Select.Option value={6}>ZXCOA_V1 (40 节点)</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="训练窗口（起始日期）" name="balance_date_from" rules={[{ required: true }]}>
            <Input type="date" defaultValue="2025-12-01" />
          </Form.Item>
          <Form.Item label="训练窗口（结束日期）" name="balance_date_to" rules={[{ required: true }]}>
            <Input type="date" defaultValue="2027-01-01" />
          </Form.Item>
          <Form.Item label="备注" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 日志 Drawer */}
      <Drawer
        open={logDrawer}
        title={logTrain ? `训练日志：${logTrain.train_code}` : ''}
        width={720}
        onClose={() => { setLogDrawer(false); setLogTrain(null); setLogLines([]) }}
      >
        {logTrain && (
          <>
            <Descriptions size="small" column={3} bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label="状态"><Tag color={STATUS_COLOR[logTrain.status]}>{logTrain.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="进度"><Progress percent={logTrain.progress} size="small" style={{ width: 120 }} /></Descriptions.Item>
              <Descriptions.Item label="耗时">{logTrain.duration_sec || '-'} s</Descriptions.Item>
              <Descriptions.Item label="模型" span={3}>{logTrain.model_code} · {logTrain.model_name}</Descriptions.Item>
              <Descriptions.Item label="版本" span={3}><Tag color="purple">{logTrain.version_code}</Tag></Descriptions.Item>
              <Descriptions.Item label="训练窗口" span={3}>{logTrain.balance_date_from} ~ {logTrain.balance_date_to}</Descriptions.Item>
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
            {logTrain.metrics && (
              <div style={{ marginTop: 12, padding: 12, background: '#f0fdf4', borderRadius: 6 }}>
                <strong style={{ color: '#15803d' }}>📊 训练指标：</strong>
                <pre style={{ marginTop: 8, fontSize: 12 }}>
                  {JSON.stringify(logTrain.metrics, null, 2)}
                </pre>
              </div>
            )}
          </>
        )}
      </Drawer>

      {/* 结果 Drawer */}
      <Drawer
        open={resultDrawer}
        title={resultData?.train ? `训练结果：${resultData.train.train_code}` : ''}
        width={720}
        onClose={() => setResultDrawer(false)}
      >
        {resultData?.train && (
          <>
            <Descriptions size="small" column={3} bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label="状态"><Tag color={STATUS_COLOR[resultData.train.status]}>{resultData.train.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="耗时">{resultData.train.duration_sec || '-'} s</Descriptions.Item>
              <Descriptions.Item label="预测期数">{resultData.items?.length || 0}</Descriptions.Item>
            </Descriptions>
            {resultData.train.metrics && (
              <Alert
                type="success"
                style={{ marginBottom: 12 }}
                showIcon
                message={<pre style={{ margin: 0, fontSize: 12 }}>{JSON.stringify(resultData.train.metrics, null, 2)}</pre>}
              />
            )}
            <h4>📈 各期预测值</h4>
            <Table
              rowKey="id"
              size="small"
              dataSource={resultData.items || []}
              pagination={false}
              columns={[
                { title: '期间', dataIndex: 'predict_period', key: 'pp', render: (v: string) => v?.substring(0, 10) },
                { title: '预测值', dataIndex: 'predicted_value', key: 'pv', render: (v: number) => v?.toFixed(4) },
                { title: '置信下限', dataIndex: 'confidence_low', key: 'cl', render: (v: number) => v != null ? v.toFixed(4) : '-' },
                { title: '置信上限', dataIndex: 'confidence_high', key: 'ch', render: (v: number) => v != null ? v.toFixed(4) : '-' },
              ]}
            />
          </>
        )}
      </Drawer>
    </div>
  )
}

export default ModelManage
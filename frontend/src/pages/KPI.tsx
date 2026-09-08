import React, { useEffect, useState, useMemo } from 'react'
import {
  Card, Row, Col, Form, Input, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, Tabs, DatePicker, Popconfirm, Statistic, Alert,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  PlayCircleOutlined, FunctionOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { kpiApi, reportsApi } from '../api'

const KPI: React.FC = () => {
  const [tab, setTab] = useState<'defs' | 'values'>('defs')
  const [defs, setDefs] = useState<any[]>([])
  const [values, setValues] = useState<any[]>([])
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  // 定义
  const [defModalOpen, setDefModalOpen] = useState(false)
  const [editingDef, setEditingDef] = useState<any>(null)
  const [defForm] = Form.useForm()
  const [formulaValid, setFormulaValid] = useState<{ ok: boolean; error?: string } | null>(null)
  const [formulaPreview, setFormulaPreview] = useState<number | null>(null)

  // 值
  const [valModalOpen, setValModalOpen] = useState(false)
  const [editingVal, setEditingVal] = useState<any>(null)
  const [valForm] = Form.useForm()
  const [recalcKpiId, setRecalcKpiId] = useState<number | null>(null)
  const [recalcDate, setRecalcDate] = useState<Dayjs>(dayjs('2026-08-31'))

  // 加载
  const loadDefs = async () => {
    setLoading(true)
    try {
      const [d, r] = await Promise.all([kpiApi.listDefs({}), reportsApi.list({})])
      setDefs(d.items || [])
      setReports(r.items || [])
    } finally { setLoading(false) }
  }
  const loadValues = async () => {
    setLoading(true)
    try {
      const v = await kpiApi.listValues({})
      setValues(v.items || [])
    } finally { setLoading(false) }
  }
  useEffect(() => { if (tab === 'defs') loadDefs(); else loadValues() }, [tab])

  // 公式实时校验
  const onFormulaChange = async (v: string) => {
    if (!v || !v.trim()) { setFormulaValid(null); setFormulaPreview(null); return }
    const r = await kpiApi.formulaValidate(v)
    setFormulaValid(r)
    if (r.ok) {
      try {
        const er = await kpiApi.formulaEval(v, { rpt: 100, node: 200 })
        setFormulaPreview(er.result)
      } catch { setFormulaPreview(null) }
    } else { setFormulaPreview(null) }
  }

  // 定义 CRUD
  const onCreateDef = () => {
    setEditingDef(null)
    defForm.resetFields()
    defForm.setFieldsValue({ calc_unit: 'PERCENT', status: 'ACTIVE' })
    setFormulaValid(null); setFormulaPreview(null)
    setDefModalOpen(true)
  }
  const onEditDef = (d: any) => {
    setEditingDef(d)
    defForm.setFieldsValue(d)
    onFormulaChange(d.formula)
    setDefModalOpen(true)
  }
  const onSaveDef = async () => {
    const v = await defForm.validateFields()
    try {
      if (editingDef) await kpiApi.updateDef(editingDef.id, v)
      else await kpiApi.createDef(v)
      message.success('已保存')
      setDefModalOpen(false)
      loadDefs()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  // 值 CRUD
  const onCreateVal = () => {
    setEditingVal(null)
    valForm.resetFields()
    valForm.setFieldsValue({
      data_date: dayjs('2026-08-31'),
      version: 'V1.0',
      calc_source: 'MANUAL',
      current_value: 0,
    })
    setValModalOpen(true)
  }
  const onEditVal = (v: any) => {
    setEditingVal(v)
    valForm.setFieldsValue({
      ...v,
      data_date: dayjs(v.data_date),
    })
    setValModalOpen(true)
  }
  const onSaveVal = async () => {
    const v = await valForm.validateFields()
    try {
      await kpiApi.upsertValue({ ...v, data_date: v.data_date.format('YYYY-MM-DD') })
      message.success('已保存')
      setValModalOpen(false)
      loadValues()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  // 重算
  const onRecalc = async (kpiId: number) => {
    if (!recalcDate) { message.warning('请选择数据日期'); return }
    try {
      const r = await kpiApi.recalc(kpiId, recalcDate.format('YYYY-MM-DD'), {})
      message.success(`重算完成：${r.value}`)
      loadValues()
    } catch (e: any) { message.error(e?.response?.data?.detail || '重算失败') }
  }

  const defCols: ColumnsType<any> = [
    { title: '编码', dataIndex: 'kpi_code', width: 120, render: (c) => <code>{c}</code> },
    { title: '名称', dataIndex: 'kpi_name', ellipsis: true },
    { title: '所属报表', dataIndex: 'report_name', width: 140 },
    { title: '公式', dataIndex: 'formula', width: 240, render: (f) => <code style={{ fontSize: 12 }}>{f}</code> },
    { title: '单位', dataIndex: 'calc_unit', width: 90, render: (u) => <Tag>{u}</Tag> },
    { title: '阈值', dataIndex: 'threshold_min', width: 160,
      render: (_, r) => `${r.threshold_min ?? '-'} ~ ${r.threshold_max ?? '-'}` },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (s) => <Tag color={s === 'ACTIVE' ? 'green' : 'default'}>{s}</Tag> },
    {
      title: '操作', width: 180, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditDef(r)}>编辑</Button>
          <Button size="small" icon={<PlayCircleOutlined />} onClick={() => { setRecalcKpiId(r.id); onRecalc(r.id) }}>重算</Button>
          <Popconfirm title="确认删除？" onConfirm={async () => {
            await kpiApi.deleteDef(r.id); message.success('已删除'); loadDefs()
          }}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
        </Space>
      ),
    },
  ]

  const valCols: ColumnsType<any> = [
    { title: '数据日期', dataIndex: 'data_date', width: 110 },
    { title: '指标编码', dataIndex: 'kpi_code', width: 120, render: (c) => <code>{c}</code> },
    { title: '指标名称', dataIndex: 'kpi_name', ellipsis: true },
    { title: '版本', dataIndex: 'version', width: 80, render: (v) => <Tag>{v}</Tag> },
    { title: '当前值', dataIndex: 'current_value', width: 120,
      render: (v) => v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 4 }) : '-' },
    { title: '环比', dataIndex: 'prev_value', width: 100,
      render: (v) => v != null ? v.toLocaleString() : '-' },
    { title: '同比', dataIndex: 'prev_year_value', width: 100,
      render: (v) => v != null ? v.toLocaleString() : '-' },
    { title: '来源', dataIndex: 'calc_source', width: 90,
      render: (s) => <Tag color={s === 'MANUAL' ? 'blue' : s === 'MODEL' ? 'purple' : 'orange'}>{s}</Tag> },
    {
      title: '操作', width: 130, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" onClick={() => onEditVal(r)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={async () => {
            await kpiApi.deleteValue(r.id); message.success('已删除'); loadValues()
          }}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>指标管理 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>· 公式定义 + 多版本结果</span></span>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card><Statistic title="指标定义" value={defs.length} prefix={<FunctionOutlined />} /></Card></Col>
        <Col span={6}><Card><Statistic title="指标值" value={values.length} /></Card></Col>
        <Col span={12}><Card>
          <Space>
            <span>重算日期：</span>
            <DatePicker value={recalcDate} onChange={setRecalcDate} />
            <Select
              placeholder="选择指标" style={{ width: 240 }}
              value={recalcKpiId || undefined}
              onChange={setRecalcKpiId}
              options={defs.map((d) => ({ value: d.id, label: `${d.kpi_code} - ${d.kpi_name}` }))}
            />
            <Button type="primary" icon={<PlayCircleOutlined />}
              disabled={!recalcKpiId}
              onClick={() => onRecalc(recalcKpiId!)}>重新计算</Button>
          </Space>
        </Card></Col>
      </Row>

      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Tabs
          activeKey={tab} onChange={(k) => setTab(k as any)}
          items={[
            { key: 'defs', label: '指标定义', children: (
              <div style={{ padding: 16 }}>
                <Space style={{ marginBottom: 12 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={onCreateDef}>新增指标</Button>
                  <Button icon={<ReloadOutlined />} onClick={loadDefs}>刷新</Button>
                </Space>
                <Table size="small" rowKey="id" dataSource={defs} columns={defCols} scroll={{ x: 1300 }}
                  pagination={{ pageSize: 20 }} />
              </div>
            ) },
            { key: 'values', label: '指标维护', children: (
              <div style={{ padding: 16 }}>
                <Space style={{ marginBottom: 12 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={onCreateVal}>新增指标值</Button>
                  <Button icon={<ReloadOutlined />} onClick={loadValues}>刷新</Button>
                </Space>
                <Table size="small" rowKey="id" dataSource={values} columns={valCols} scroll={{ x: 1300 }}
                  pagination={{ pageSize: 20 }} />
              </div>
            ) },
          ]}
        />
      </Card>

      {/* 定义编辑 */}
      <Modal title={editingDef ? '编辑指标定义' : '新增指标定义'} open={defModalOpen}
        onCancel={() => setDefModalOpen(false)} onOk={onSaveDef} width={640}>
        <Form form={defForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="kpi_code" label="指标编码" rules={[{ required: true }]}><Input placeholder="KPI_NIM" /></Form.Item></Col>
            <Col span={12}><Form.Item name="kpi_name" label="指标名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="rpt_id" label="所属报表" rules={[{ required: true }]}>
            <Select options={reports.map((r) => ({ value: r.id, label: `${r.report_code} - ${r.report_name}` }))} />
          </Form.Item>
          <Form.Item name="formula" label="计算公式" rules={[{ required: true }]}
            extra="支持 + - * / ( ) 运算与 SUM/AVG/MAX/MIN/COUNT/ABS/ROUND/IF 函数。变量用标识符，如 rpt + 100">
            <Input.TextArea rows={3} placeholder="例如：(rpt + node) * 2 / SUM(100, 200)" onChange={(e) => onFormulaChange(e.target.value)} />
          </Form.Item>
          {formulaValid && (
            formulaValid.ok
              ? <Alert type="success" message={`语法正确，预览：${formulaPreview}`} showIcon style={{ marginBottom: 12 }} />
              : <Alert type="error" message={formulaValid.error} showIcon style={{ marginBottom: 12 }} />
          )}
          <Row gutter={16}>
            <Col span={8}><Form.Item name="calc_unit" label="单位">
              <Select options={[
                { value: 'PERCENT', label: 'PERCENT' },
                { value: 'BP', label: 'BP' },
                { value: 'RATIO', label: 'RATIO' },
                { value: 'AMOUNT', label: 'AMOUNT' },
              ]} />
            </Form.Item></Col>
            <Col span={8}><Form.Item name="threshold_min" label="阈值下限"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="threshold_max" label="阈值上限"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item name="formula_desc" label="公式说明"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="status" label="状态" initialValue="ACTIVE">
            <Select options={[{ value: 'ACTIVE', label: 'ACTIVE' }, { value: 'INACTIVE', label: 'INACTIVE' }]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 值编辑 */}
      <Modal title={editingVal ? '编辑指标值' : '新增指标值'} open={valModalOpen}
        onCancel={() => setValModalOpen(false)} onOk={onSaveVal} width={520}>
        <Form form={valForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="kpi_id" label="指标" rules={[{ required: true }]}>
              <Select showSearch optionFilterProp="label"
                options={defs.map((d) => ({ value: d.id, label: `${d.kpi_code} - ${d.kpi_name}` }))} />
            </Form.Item></Col>
            <Col span={12}><Form.Item name="data_date" label="数据日期" rules={[{ required: true }]}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="version" label="版本" initialValue="V1.0"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="calc_source" label="来源">
              <Select options={[{ value: 'MANUAL', label: 'MANUAL' }, { value: 'MODEL', label: 'MODEL' }, { value: 'RECALC', label: 'RECALC' }]} />
            </Form.Item></Col>
            <Col span={8}><Form.Item name="current_value" label="当前值"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="prev_value" label="环比（上一期）"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={12}><Form.Item name="prev_year_value" label="同比（去年同期）"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item name="calc_log" label="计算日志"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </Spin>
  )
}

export default KPI

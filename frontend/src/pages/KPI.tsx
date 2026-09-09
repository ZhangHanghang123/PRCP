import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Form, Input, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, Tabs, DatePicker, Popconfirm, Statistic, Alert, InputNumber, Tree,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  PlayCircleOutlined, FunctionOutlined, AppstoreOutlined,
  InsertRowAboveOutlined, InsertRowBelowOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { kpiApi, reportsApi } from '../api'

const KPI: React.FC = () => {
  const [tab, setTab] = useState<'schemes' | 'defs' | 'values'>('schemes')
  const [schemes, setSchemes] = useState<any[]>([])
  const [defs, setDefs] = useState<any[]>([])
  const [values, setValues] = useState<any[]>([])
  const [reports, setReports] = useState<any[]>([])
  const [rptItems, setRptItems] = useState<any[]>([])
  const [activeScheme, setActiveScheme] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')

  // 方案
  const [schemeModal, setSchemeModal] = useState(false)
  const [editingScheme, setEditingScheme] = useState<any>(null)
  const [schemeForm] = Form.useForm()

  // 定义
  const [defModal, setDefModal] = useState(false)
  const [editingDef, setEditingDef] = useState<any>(null)
  const [defForm] = Form.useForm()
  const [formulaValid, setFormulaValid] = useState<{ ok: boolean; error?: string } | null>(null)
  const [formulaPreview, setFormulaPreview] = useState<number | null>(null)

  // 值
  const [valueModal, setValueModal] = useState(false)
  const [editingValue, setEditingValue] = useState<any>(null)
  const [valueForm] = Form.useForm()

  // 重算
  const [recalcKpiId, setRecalcKpiId] = useState<number | null>(null)
  const [recalcDate, setRecalcDate] = useState<Dayjs>(dayjs('2026-08-31'))

  // 监听定义表单的 formula 字段，用于双框联动
  const formulaText = Form.useWatch('formula', defForm) || ''

  // ========= 报表表项 → 树形结构 =========
  const buildTree = (items: any[]): any[] => {
    if (!items.length) return []
    // 按 item_code 建索引
    const byCode = new Map<string, any>()
    for (const it of items) {
      byCode.set(it.item_code, {
        key: `node_${it.id}`,
        title: (
          <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
            <Tag color={it.level === 1 ? 'blue' : it.level === 2 ? 'cyan' : it.level === 3 ? 'geekblue' : 'green'} style={{ marginRight: 4 }}>
              L{it.level}
            </Tag>
            <strong>{it.item_code}</strong> · {it.item_name}
          </span>
        ),
        level: it.level,
        raw: it,
        children: [] as any[],
        isLeaf: false,
      })
    }
    // 判断叶子：有更深层级以本 code 为前缀的项就不是叶子
    const isLeaf = (code: string) => {
      for (const k of byCode.keys()) {
        if (k.length > code.length && k.startsWith(code)) return false
      }
      return true
    }
    // 组装父子（按 item_code 前缀：L2 的前 3 位是 L1，L3 前 6 位是 L2 ...）
    const roots: any[] = []
    for (const it of items) {
      const node = byCode.get(it.item_code)!
      node.isLeaf = isLeaf(it.item_code)
      if (it.level === 1) {
        roots.push(node)
      } else {
        const parentCode = it.item_code.slice(0, (it.level - 1) * 3)
        const parent = byCode.get(parentCode)
        if (parent) parent.children.push(node)
        else roots.push(node)  // fallback
      }
    }
    // 空 children 设为 undefined，Tree 不显示展开箭头
    const clean = (nodes: any[]) => {
      for (const n of nodes) {
        if (!n.children || n.children.length === 0) n.children = undefined
        else clean(n.children)
      }
    }
    clean(roots)
    return roots
  }

  // 公式：[item_code] → 报表项中文名（只读预览）
  const translateFormula = (formula: string, items: any[]): string => {
    if (!formula) return ''
    let result = formula
    if (items.length) {
      // 按 item_code 长度倒序，避免 001001 误替换 001
      const sorted = [...items].sort((a, b) => b.item_code.length - a.item_code.length)
      for (const it of sorted) {
        const code = `[${it.item_code}]`
        const name = `[${it.item_name || it.item_code}]`
        result = result.split(code).join(name)
      }
    }
    return result
  }

  const rptTreeData = useMemo(() => buildTree(rptItems), [rptItems])
  const formulaNameView = useMemo(
    () => translateFormula(formulaText, rptItems),
    [formulaText, rptItems]
  )

  // 加载方案
  const loadSchemes = async () => {
    setLoading(true)
    try {
      const r = await kpiApi.listSchemes({})
      setSchemes(r.items || [])
    } finally { setLoading(false) }
  }

  // 加载定义（按 activeScheme 过滤）
  const loadDefs = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (activeScheme) params.scheme_id = activeScheme
      if (keyword) params.keyword = keyword
      const r = await kpiApi.listDefs(params)
      setDefs(r.items || [])
    } finally { setLoading(false) }
  }

  // 加载值
  const loadValues = async () => {
    setLoading(true)
    try {
      const r = await kpiApi.listValues({})
      setValues(r.items || [])
    } finally { setLoading(false) }
  }

  // 加载报表列表（用于定义的"所属报表"下拉）
  const loadReports = async () => {
    const r = await reportsApi.list({})
    setReports(r.items || [])
  }

  useEffect(() => { loadSchemes() }, [])
  useEffect(() => { if (tab === 'defs') { loadReports(); loadDefs() } }, [tab, activeScheme, keyword])
  useEffect(() => { if (tab === 'values') loadValues() }, [tab])

  // 公式实时校验
  const onFormulaChange = async (v: string) => {
    if (!v || !v.trim()) { setFormulaValid(null); setFormulaPreview(null); return }
    const r = await kpiApi.formulaValidate(v)
    setFormulaValid(r)
    if (r.ok) {
      try {
        // 预览：把公式中的标识符当成变量，假设都为 100
        const er = await kpiApi.formulaEval(v, { rpt: 100, node: 100 })
        setFormulaPreview(er.result)
      } catch { setFormulaPreview(null) }
    } else { setFormulaPreview(null) }
  }

  // 切换定义表单的"所属报表"时，加载该报表的表项供下拉
  const onDefRptChange = async (rptId: number) => {
    if (!rptId) { setRptItems([]); return }
    const r = await kpiApi.listRptItems({ rpt_id: rptId })
    setRptItems(r.items || [])
  }

  // ========= 方案 CRUD =========
  const onCreateScheme = () => {
    setEditingScheme(null)
    schemeForm.resetFields()
    schemeForm.setFieldsValue({ status: 'ACTIVE' })
    setSchemeModal(true)
  }
  const onEditScheme = (s: any) => {
    setEditingScheme(s)
    schemeForm.setFieldsValue(s)
    setSchemeModal(true)
  }
  const onSaveScheme = async () => {
    const v = await schemeForm.validateFields()
    try {
      if (editingScheme) await kpiApi.updateScheme(editingScheme.id, v)
      else {
        const r = await kpiApi.createScheme(v)
        setActiveScheme(r.id)
      }
      message.success('已保存')
      setSchemeModal(false)
      loadSchemes()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  // ========= 定义 CRUD =========
  const onCreateDef = () => {
    if (!activeScheme) {
      message.warning('请先在"方案" Tab 中选择或创建一个指标方案')
      setTab('schemes')
      return
    }
    setEditingDef(null)
    defForm.resetFields()
    defForm.setFieldsValue({
      scheme_id: activeScheme,
      calc_unit: 'PERCENT',
      status: 'ACTIVE',
    })
    setRptItems([])
    setFormulaValid(null); setFormulaPreview(null)
    setDefModal(true)
  }
  const onEditDef = (d: any) => {
    setEditingDef(d)
    defForm.setFieldsValue({
      scheme_id: d.scheme_id,
      kpi_code: d.kpi_code,
      kpi_name: d.kpi_name,
      rpt_id: d.rpt_id,
      formula: d.formula,
      calc_unit: d.calc_unit,
      formula_desc: d.formula_desc,
      threshold_min: d.threshold_min,
      threshold_max: d.threshold_max,
      status: d.status,
    })
    onFormulaChange(d.formula)
    onDefRptChange(d.rpt_id)
    setDefModal(true)
  }
  const onSaveDef = async () => {
    const v = await defForm.validateFields()
    try {
      if (editingDef) await kpiApi.updateDef(editingDef.id, v)
      else await kpiApi.createDef(v)
      message.success('已保存')
      setDefModal(false)
      loadSchemes()  // 更新 kpi_count
      loadDefs()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  // 在公式中插入报表表项引用（用 [item_code] 形式）
  const insertItemIntoFormula = (item: any) => {
    const v = defForm.getFieldValue('formula') || ''
    const ref = `[${item.item_code}]`
    defForm.setFieldsValue({ formula: v ? `${v} ${ref}` : ref })
  }

  // 在公式中插入符号/函数（append 模式）
  const insertSymbolIntoFormula = (sym: string, closeSym?: string, isFunc = false) => {
    const v = defForm.getFieldValue('formula') || ''
    const next = isFunc ? `${v}${sym}` + (closeSym || '') : `${v}${sym}`
    defForm.setFieldsValue({ formula: next })
    onFormulaChange(next)
  }

  // 退格（删除公式最后一个 token，而非最后一个字符）
  const backspaceFormula = () => {
    const v = defForm.getFieldValue('formula') || ''
    if (!v) return
    let next = v
    // 优先删整个 [xxx] 引用 / item_<ID> 引用 / 函数名 / 操作符
    const patterns = [
      /\s*\[[^\]]+\]\s*$/,            // [item_code]
      /\s*item_\d+\s*$/,              // item_<ID>
      /\s*[A-Za-z_]+\s*\([^()]*\)\s*$/,  // FUNC(args)
      /\s*[^A-Za-z_\[\]\s]\s*$/,      // 单字符运算符
      /\s*[A-Za-z_]\w*\s*$/,          // 标识符
    ]
    for (const p of patterns) {
      if (p.test(next)) {
        next = next.replace(p, '').trimEnd()
        break
      }
    }
    defForm.setFieldsValue({ formula: next })
    onFormulaChange(next)
  }

  // 清空公式
  const clearFormula = () => {
    defForm.setFieldsValue({ formula: '' })
    onFormulaChange('')
  }

  // ========= 值 CRUD =========
  const onCreateValue = () => {
    setEditingValue(null)
    valueForm.resetFields()
    valueForm.setFieldsValue({
      data_date: dayjs('2026-08-31'),
      version: 'V1.0',
      calc_source: 'MANUAL',
      current_value: 0,
    })
    setValueModal(true)
  }
  const onEditValue = (v: any) => {
    setEditingValue(v)
    valueForm.setFieldsValue({
      ...v,
      data_date: dayjs(v.data_date),
    })
    setValueModal(true)
  }
  const onSaveValue = async () => {
    const v = await valueForm.validateFields()
    try {
      await kpiApi.upsertValue({ ...v, data_date: v.data_date.format('YYYY-MM-DD') })
      message.success('已保存')
      setValueModal(false)
      loadValues()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  // 重算
  const onRecalc = async (kpiId: number) => {
    if (!recalcDate) { message.warning('请选择数据日期'); return }
    try {
      const r = await kpiApi.recalc(kpiId, recalcDate.format('YYYY-MM-DD'))
      message.success(`重算完成：${r.value}`)
      loadValues()
    } catch (e: any) { message.error(e?.response?.data?.detail || '重算失败') }
  }

  // ========= 列定义 =========
  const schemeCols: ColumnsType<any> = [
    { title: '方案编码', dataIndex: 'scheme_code', width: 140, render: (c) => <code>{c}</code> },
    { title: '方案名称', dataIndex: 'scheme_name', ellipsis: true },
    { title: '指标数', dataIndex: 'kpi_count', width: 100, render: (n) => <Tag color="blue">{n || 0}</Tag> },
    { title: '状态', dataIndex: 'status', width: 90, render: (s) => <Tag color={s === 'ACTIVE' ? 'green' : 'default'}>{s}</Tag> },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    {
      title: '操作', width: 220, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" type={r.id === activeScheme ? 'primary' : 'default'}
            onClick={() => { setActiveScheme(r.id); setTab('defs') }}>
            进入
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditScheme(r)}>编辑</Button>
          <Popconfirm title="删除此方案及其所有指标定义？" onConfirm={async () => {
            await kpiApi.deleteScheme(r.id); message.success('已删除')
            if (activeScheme === r.id) setActiveScheme(null)
            loadSchemes()
          }}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
        </Space>
      ),
    },
  ]

  const defCols: ColumnsType<any> = [
    { title: '方案', dataIndex: 'scheme_name', width: 140, render: (s, r) => <Tag color="purple">{s}</Tag> },
    { title: '编码', dataIndex: 'kpi_code', width: 120, render: (c) => <code>{c}</code> },
    { title: '名称', dataIndex: 'kpi_name', ellipsis: true },
    { title: '所属报表', dataIndex: 'report_name', width: 140, ellipsis: true },
    { title: '公式', dataIndex: 'formula', width: 220, render: (f) => <code style={{ fontSize: 12 }}>{f}</code> },
    { title: '单位', dataIndex: 'calc_unit', width: 80, render: (u) => <Tag>{u}</Tag> },
    { title: '状态', dataIndex: 'status', width: 80, render: (s) => <Tag color={s === 'ACTIVE' ? 'green' : 'default'}>{s}</Tag> },
    {
      title: '操作', width: 180, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditDef(r)}>编辑</Button>
          <Button size="small" icon={<PlayCircleOutlined />} onClick={() => onRecalc(r.id)}>重算</Button>
          <Popconfirm title="删除指标及其所有版本结果？" onConfirm={async () => {
            await kpiApi.deleteDef(r.id); message.success('已删除')
            loadSchemes(); loadDefs()
          }}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
        </Space>
      ),
    },
  ]

  const valueCols: ColumnsType<any> = [
    { title: '数据日期', dataIndex: 'data_date', width: 110 },
    { title: '方案', dataIndex: 'scheme_name', width: 120, render: (s) => <Tag color="purple">{s}</Tag> },
    { title: '指标', dataIndex: 'kpi_code', width: 130, render: (c) => <code>{c}</code> },
    { title: '指标名称', dataIndex: 'kpi_name', ellipsis: true },
    { title: '版本', dataIndex: 'version', width: 80, render: (v) => <Tag>{v}</Tag> },
    { title: '当前值', dataIndex: 'current_value', width: 120,
      render: (v, r) => v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 4 }) + (r.calc_unit === 'PERCENT' ? '%' : '') : '-' },
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
          <Button size="small" onClick={() => onEditValue(r)}>编辑</Button>
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
        <span>指标管理 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>· 指标方案 · 公式引擎 · 多版本结果</span></span>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card><Statistic title="指标方案" value={schemes.length} prefix={<AppstoreOutlined />} /></Card></Col>
        <Col span={6}><Card><Statistic title="指标定义" value={defs.length} prefix={<FunctionOutlined />} /></Card></Col>
        <Col span={6}><Card><Statistic title="指标值" value={values.length} prefix={<InsertRowAboveOutlined />} /></Card></Col>
        <Col span={6}><Card>
          <Space>
            <span>重算日期：</span>
            <DatePicker value={recalcDate} onChange={setRecalcDate} size="small" />
          </Space>
        </Card></Col>
      </Row>

      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Tabs
          activeKey={tab} onChange={(k) => setTab(k as any)}
          items={[
            { key: 'schemes', label: <span><AppstoreOutlined /> 指标方案</span>, children: (
              <div style={{ padding: 16 }}>
                <Space style={{ marginBottom: 12 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={onCreateScheme}>新增方案</Button>
                  <Button icon={<ReloadOutlined />} onClick={loadSchemes}>刷新</Button>
                </Space>
                <Table size="small" rowKey="id" dataSource={schemes} columns={schemeCols}
                  pagination={{ pageSize: 10 }}
                  onRow={(r) => ({ style: { background: r.id === activeScheme ? '#e6f4ff' : undefined } })}
                />
              </div>
            ) },
            { key: 'defs', label: <span><FunctionOutlined /> 指标定义</span>, children: (
              <div style={{ padding: 16 }}>
                <Space style={{ marginBottom: 12 }} wrap>
                  <Select
                    placeholder="选择指标方案" style={{ width: 200 }}
                    value={activeScheme || undefined}
                    onChange={setActiveScheme}
                    allowClear
                    options={schemes.map((s) => ({ value: s.id, label: `${s.scheme_code} · ${s.scheme_name}` }))}
                  />
                  <Input.Search
                    placeholder="搜索编码 / 名称"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    style={{ width: 240 }}
                    allowClear
                  />
                  <Button icon={<ReloadOutlined />} onClick={loadDefs}>刷新</Button>
                  <Button type="primary" icon={<PlusOutlined />} onClick={onCreateDef}>新增指标</Button>
                </Space>
                <Table size="small" rowKey="id" dataSource={defs} columns={defCols}
                  scroll={{ x: 1300 }}
                  pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }} />
              </div>
            ) },
            { key: 'values', label: <span><InsertRowBelowOutlined /> 指标维护</span>, children: (
              <div style={{ padding: 16 }}>
                <Space style={{ marginBottom: 12 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={onCreateValue}>新增指标值</Button>
                  <Button icon={<ReloadOutlined />} onClick={loadValues}>刷新</Button>
                </Space>
                <Table size="small" rowKey="id" dataSource={values} columns={valueCols}
                  scroll={{ x: 1400 }}
                  pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }} />
              </div>
            ) },
          ]}
        />
      </Card>

      {/* 方案编辑 */}
      <Modal title={editingScheme ? '编辑指标方案' : '新增指标方案'} open={schemeModal}
        onCancel={() => setSchemeModal(false)} onOk={onSaveScheme} width={520}>
        <Form form={schemeForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="scheme_code" label="方案编码" rules={[{ required: true }]}><Input placeholder="SCH_2026" /></Form.Item></Col>
            <Col span={12}><Form.Item name="scheme_name" label="方案名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="status" label="状态" initialValue="ACTIVE">
            <Select options={[{ value: 'ACTIVE', label: 'ACTIVE' }, { value: 'INACTIVE', label: 'INACTIVE' }]} />
          </Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      {/* 定义编辑（关键：含报表表项引用） */}
      <Modal title={editingDef ? '编辑指标定义' : '新增指标定义'} open={defModal}
        onCancel={() => setDefModal(false)} onOk={onSaveDef} width={760}>
        <Form form={defForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="scheme_id" label="所属指标方案" rules={[{ required: true }]}>
              <Select options={schemes.map((s) => ({ value: s.id, label: `${s.scheme_code} · ${s.scheme_name}` }))} />
            </Form.Item></Col>
            <Col span={12}><Form.Item name="rpt_id" label="所属报表（决定可引用的报表表项范围）" rules={[{ required: true }]}>
              <Select options={reports.map((r) => ({ value: r.id, label: `${r.report_code} · ${r.report_name}` }))}
                onChange={onDefRptChange} showSearch optionFilterProp="label" />
            </Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="kpi_code" label="指标编码" rules={[{ required: true }]}><Input placeholder="KPI_NIM" /></Form.Item></Col>
            <Col span={8}><Form.Item name="kpi_name" label="指标名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="calc_unit" label="单位">
              <Select options={[
                { value: 'PERCENT', label: '百分比 %' },
                { value: 'BP', label: '基点 BP' },
                { value: 'RATIO', label: '比率' },
                { value: 'AMOUNT', label: '金额' },
              ]} />
            </Form.Item></Col>
          </Row>
          {/* 公式工具栏：符号 + 函数 + 退格一键插入 */}
          <Form.Item label="公式符号与函数">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, padding: '4px 8px', border: '1px solid #f0f0f0', borderRadius: 4, background: '#fafafa' }}>
              <Button.Group size="small">
                <Button onClick={() => insertSymbolIntoFormula(' + ')}>+</Button>
                <Button onClick={() => insertSymbolIntoFormula(' - ')}>−</Button>
                <Button onClick={() => insertSymbolIntoFormula(' * ')}>×</Button>
                <Button onClick={() => insertSymbolIntoFormula(' / ')}>÷</Button>
              </Button.Group>
              <Button.Group size="small" style={{ marginLeft: 8 }}>
                <Button onClick={() => insertSymbolIntoFormula('( ')}>(</Button>
                <Button onClick={() => insertSymbolIntoFormula(' )')}>)</Button>
                <Button onClick={() => insertSymbolIntoFormula(', ')}>,</Button>
              </Button.Group>
              <Button.Group size="small" style={{ marginLeft: 8 }}>
                <Button onClick={() => insertSymbolIntoFormula('SUM(', ')', true)}>SUM</Button>
                <Button onClick={() => insertSymbolIntoFormula('AVG(', ')', true)}>AVG</Button>
                <Button onClick={() => insertSymbolIntoFormula('MAX(', ')', true)}>MAX</Button>
                <Button onClick={() => insertSymbolIntoFormula('MIN(', ')', true)}>MIN</Button>
                <Button onClick={() => insertSymbolIntoFormula('COUNT(', ')', true)}>COUNT</Button>
                <Button onClick={() => insertSymbolIntoFormula('ABS(', ')', true)}>ABS</Button>
                <Button onClick={() => insertSymbolIntoFormula('ROUND(', ')', true)}>ROUND</Button>
                <Button onClick={() => insertSymbolIntoFormula('IF(', ',', true)}>IF</Button>
              </Button.Group>
              <Button.Group size="small" style={{ marginLeft: 8 }}>
                <Button onClick={() => insertSymbolIntoFormula(' > ')}>{'>'}</Button>
                <Button onClick={() => insertSymbolIntoFormula(' < ')}>{'<'}</Button>
                <Button onClick={() => insertSymbolIntoFormula(' >= ')}>{'>='}</Button>
                <Button onClick={() => insertSymbolIntoFormula(' <= ')}>{'<='}</Button>
                <Button onClick={() => insertSymbolIntoFormula(' == ')}>{'=='}</Button>
              </Button.Group>
              <Button.Group size="small" style={{ marginLeft: 8 }}>
                <Button onClick={backspaceFormula} title="退格（删除最后一个 token）">⌫ 退格</Button>
                <Button onClick={clearFormula} danger title="清空公式">清空</Button>
              </Button.Group>
            </div>
          </Form.Item>

          <Form.Item name="formula" label="计算公式（表项编码，可编辑）" rules={[{ required: true }]}
            extra="支持 + - * / ( ) 与 SUM/AVG/MAX/MIN/COUNT/ABS/ROUND/IF 函数。变量名 = [item_code]（点下方报表结构树叶子节点自动插入）">
            <Input.TextArea rows={3} placeholder="例如：[001001001001] - [001001001002]" onChange={(e) => onFormulaChange(e.target.value)} />
          </Form.Item>
          {formulaValid && (
            formulaValid.ok
              ? <Alert type="success" message={`语法正确 · 预览：${formulaPreview}`} showIcon style={{ marginBottom: 12 }} />
              : <Alert type="error" message={formulaValid.error} showIcon style={{ marginBottom: 12 }} />
          )}

          {/* 名称预览框（只读，把 item_<ID> 翻译成中文名） */}
          <Form.Item label="公式名称视图（只读预览）">
            <Input.TextArea
              rows={2}
              readOnly
              value={formulaNameView}
              placeholder={rptItems.length ? '编辑上方公式时，此处实时显示中文名' : '请先选择所属报表'}
              style={{ background: '#f5f5f5', fontFamily: 'monospace', fontSize: 12 }}
            />
          </Form.Item>

          {/* 报表结构树（按 L1→L2→L3→L4 层级） */}
          {defForm.getFieldValue('rpt_id') && rptTreeData.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ color: '#666', marginBottom: 6, fontSize: 13 }}>
                📌 点击报表结构树的叶子节点插入引用：
              </div>
              <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #f0f0f0', padding: 8, borderRadius: 4, background: '#fafafa' }}>
                <Tree
                  treeData={rptTreeData}
                  defaultExpandAll
                  showLine
                  blockNode
                  selectable
                  onSelect={(_, info: any) => {
                    const node = info.node
                    if (node.isLeaf) {
                      insertItemIntoFormula(node.raw)
                    } else {
                      message.info('请选择叶子节点（具体报表项）')
                    }
                  }}
                />
              </div>
            </div>
          )}

          {/* 报表无表项时的空状态提示 */}
          {defForm.getFieldValue('rpt_id') && rptItems.length === 0 && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 12 }}
              message="该报表暂无表项"
              description={(
                <div>
                  <div style={{ marginBottom: 6 }}>所选报表还没有定义任何报表表项，因此无法在公式中引用具体项。</div>
                  <div>请先到 <strong>报表表项管理</strong> 页面为此报表添加表项（如：总资产、客户贷款、净息差等）。</div>
                </div>
              )}
            />
          )}

          {!defForm.getFieldValue('rpt_id') && (
            <Alert type="info" showIcon style={{ marginBottom: 12 }}
              message="请先在上方选择【所属报表】" description="选定报表后，这里会展示该报表的树形结构，点击叶子节点可一键插入到公式中。" />
          )}

          <Row gutter={16}>
            <Col span={12}><Form.Item name="threshold_min" label="阈值下限"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={12}><Form.Item name="threshold_max" label="阈值上限"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item name="formula_desc" label="公式说明"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="status" label="状态" initialValue="ACTIVE">
            <Select options={[{ value: 'ACTIVE', label: 'ACTIVE' }, { value: 'INACTIVE', label: 'INACTIVE' }]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 值编辑 */}
      <Modal title={editingValue ? '编辑指标值' : '新增指标值'} open={valueModal}
        onCancel={() => setValueModal(false)} onOk={onSaveValue} width={520}>
        <Form form={valueForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="kpi_id" label="指标" rules={[{ required: true }]}>
              <Select showSearch optionFilterProp="label"
                options={defs.map((d) => ({ value: d.id, label: `${d.scheme_code}/${d.kpi_code} · ${d.kpi_name}` }))} />
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

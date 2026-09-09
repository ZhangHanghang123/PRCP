import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Form, Input, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, DatePicker, Popconfirm, Statistic, Alert, InputNumber, Tree, Tabs, Descriptions,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  CalculatorOutlined, FunctionOutlined, AppstoreOutlined, ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { dataMaintApi, coaApi } from '../api'

const CATEGORIES = [
  { code: 'FINANCIAL', name: '1-账务结果指标', color: '#667eea' },
  { code: 'PARAM',     name: '2-关键参数指标', color: '#52c41a' },
  { code: 'SCALE',     name: '3-规模指标',     color: '#f59e0b' },
  { code: 'PRICE',     name: '4-价格指标',     color: '#eb2f96' },
  { code: 'FEE',       name: '5-中收指标',     color: '#13c2c2' },
  { code: 'RWA',       name: '6-资本与RWA假设指标', color: '#722ed1' },
]

const DataMaint: React.FC = () => {
  const [tab, setTab] = useState('FINANCIAL')
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<any[]>([])
  const [months, setMonths] = useState([])
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs('2026-08-01'))
  const [values, setValues] = useState<any[]>([])
  const [selectedItem, setSelectedItem] = useState<any>(null)
  const [coaTrees, setCoaTrees] = useState<any[]>([])
  const [coaSchemes, setCoaSchemes] = useState<any[]>([])
  const [activeCoaScheme, setActiveCoaScheme] = useState<number | null>(null)

  const [valueModal, setValueModal] = useState(false)
  const [editingValue, setEditingValue] = useState<any>(null)
  const [ruleModal, setRuleModal] = useState(false)
  const [form] = Form.useForm()
  const [ruleForm] = Form.useForm()

  const loadItems = async (cat: string) => {
    setLoading(true)
    try {
      const r = await dataMaintApi.listItems({ category: cat })
      setItems(r.items || [])
      setSelectedItem(null)
    } finally { setLoading(false) }
  }

  const loadCoaTrees = async () => {
    const sr = await coaApi.listSchemes()
    setCoaSchemes(sr.items || [])
    const v6 = sr.items?.find((s: any) => s.scheme_code === 'COA_V6')
    if (v6) setActiveCoaScheme(v6.id)
    else if (sr.items?.length) setActiveCoaScheme(sr.items[0].id)
  }

  const loadCoaNodes = async (schemeId: number) => {
    const r = await coaApi.listNodes(schemeId)
    setCoaTrees(r.items || [])
  }

  const loadMonths = async () => {
    const r = await dataMaintApi.listMonths()
    setMonths(r.items || [])
  }

  const loadValues = async () => {
    if (!selectedItem) { setValues([]); return }
    setLoading(true)
    try {
      const r = await dataMaintApi.listValues({ item_id: selectedItem.id, data_date: selectedDate.format('YYYY-MM-DD') })
      setValues(r.items || [])
    } finally { setLoading(false) }
  }

  useEffect(() => { loadItems(tab) }, [tab])
  useEffect(() => { loadMonths(); loadCoaTrees() }, [])
  useEffect(() => { if (activeCoaScheme) loadCoaNodes(activeCoaScheme) }, [activeCoaScheme])
  useEffect(() => { loadValues() }, [selectedItem, selectedDate])

  const buildTree = (list: any[], codeField: string, levelField: string, parentField: string, latestAmountField?: string) => {
    const byLevel: Record<number, any[]> = {}
    list.forEach((i) => {
      const lvl = i[levelField] || 1
      if (!byLevel[lvl]) byLevel[lvl] = []
      byLevel[lvl].push(i)
    })
    const map = new Map<number, any>()
    list.forEach((i) => {
      map.set(i.id, {
        key: `${codeField}_${i.id}`,
        title: (
          <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
            <Tag color={i[levelField] === 1 ? 'blue' : i[levelField] === 2 ? 'cyan' : i[levelField] === 3 ? 'geekblue' : 'green'} style={{ marginRight: 4 }}>L{i[levelField]}</Tag>
            <strong>{i[codeField]}</strong> · {i.item_name || i.node_name}
            {i.coa_node_ids && i.coa_node_ids.length > 0 && codeField === 'item_code' && (
              <Tag color="green" style={{ marginLeft: 4, fontSize: 10 }}>已配取数</Tag>
            )}
            {latestAmountField && i[latestAmountField] > 0 && (
              <span style={{ marginLeft: 6, color: '#999' }}>{i[latestAmountField].toFixed(0)}亿</span>
            )}
          </span>
        ),
        raw: i,
        level: i[levelField],
        children: [] as any[],
      })
    })
    const roots: any[] = []
    list.forEach((i) => {
      const node = map.get(i.id)
      if (i[levelField] === 1 || !i[parentField]) {
        roots.push(node)
      } else if (map.has(i[parentField])) {
        map.get(i[parentField]).children.push(node)
      } else {
        roots.push(node)
      }
    })
    const clean = (ns: any[]) => {
      ns.forEach((n) => {
        if (n.children.length === 0) n.children = undefined
        else clean(n.children)
      })
    }
    clean(roots)
    return roots
  }

  const itemTree = useMemo(() => buildTree(items, 'item_code', 'item_level', 'parent_id'), [items])
  const coaTreeData = useMemo(() => buildTree(coaTrees, 'node_code', 'node_level', 'parent_id', 'latest_amount'), [coaTrees])

  const totalItems = items.length
  const itemsWithRule = items.filter((i) => i.coa_node_ids && i.coa_node_ids.length > 0).length

  const onMonthlyCalc = async () => {
    if (!selectedDate) { message.warning('请选择数据日期'); return }
    setLoading(true)
    try {
      const r = await dataMaintApi.monthlyCalc({ data_date: selectedDate.format('YYYY-MM-DD'), category: tab })
      message.success(`本月计算完成：${r.count} 个指标`)
      loadItems(tab)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '计算失败')
    } finally { setLoading(false) }
  }

  const onEditRule = (item: any) => {
    setSelectedItem(item)
    ruleForm.setFieldsValue({
      coa_node_ids: item.coa_node_ids || [],
      formula: item.formula || '',
      description: item.description || '',
    })
    setRuleModal(true)
  }
  const onSaveRule = async () => {
    try {
      const v = await ruleForm.validateFields()
      await dataMaintApi.saveCalcRule(selectedItem.id, v)
      message.success('已保存取数逻辑')
      setRuleModal(false)
      loadItems(tab)
    } catch (e: any) {
      if (e.errorFields) return
      message.error('保存失败')
    }
  }

  const onEditValue = (v: any) => {
    setEditingValue(v)
    form.setFieldsValue({
      item_id: selectedItem.id,
      data_date: dayjs(v.data_date),
      value: v.value,
      source: v.source,
    })
    setValueModal(true)
  }
  const onCreateValue = () => {
    if (!selectedItem) { message.warning('请先选择指标'); return }
    setEditingValue(null)
    form.resetFields()
    form.setFieldsValue({
      item_id: selectedItem.id,
      data_date: selectedDate,
      value: 0,
      source: 'MANUAL',
    })
    setValueModal(true)
  }
  const onSaveValue = async () => {
    try {
      const v = await form.validateFields()
      const payload = {
        item_id: v.item_id,
        data_date: v.data_date.format('YYYY-MM-DD'),
        value: v.value,
        source: v.source,
      }
      await dataMaintApi.upsertValue(payload)
      message.success('已保存')
      setValueModal(false)
      loadValues()
    } catch (e: any) {
      if (e.errorFields) return
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  const onCalcPreview = async () => {
    if (!selectedItem) { message.warning('请先选择指标'); return }
    try {
      const r = await dataMaintApi.calcPreview(selectedItem.id, selectedDate.format('YYYY-MM-DD'))
      Modal.info({
        title: `${r.item_code} · ${r.item_name} 预览（${selectedDate.format('YYYY-MM-DD')}）`,
        width: 600,
        content: (
          <div>
            <p>计算结果：<strong style={{ fontSize: 16, color: '#667eea' }}>{r.value.toLocaleString()}</strong></p>
            <p>分子节点（{r.detail.length} 个）：</p>
            <Table size="small" dataSource={r.detail} rowKey="coa_node_id" pagination={false}
              columns={[
                { title: '编码', dataIndex: 'node_code', width: 90 },
                { title: '名称', dataIndex: 'node_name' },
                { title: '余额', dataIndex: 'amount', width: 100, render: (v) => v?.toLocaleString() },
              ]}
            />
          </div>
        ),
      })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '预览失败')
    }
  }

  const valueCols: ColumnsType<any> = [
    { title: '数据日期', dataIndex: 'data_date', width: 110 },
    { title: '指标编码', dataIndex: 'item_code', width: 130, render: (c) => <code>{c}</code> },
    { title: '指标名称', dataIndex: 'item_name', ellipsis: true },
    { title: '值', dataIndex: 'value', width: 150,
      render: (v) => v != null ? <strong style={{ color: '#667eea' }}>{v.toLocaleString(undefined, { maximumFractionDigits: 4 })}</strong> : '-' },
    { title: '来源', dataIndex: 'source', width: 90,
      render: (s) => <Tag color={s === 'MANUAL' ? 'blue' : s === 'CALC' ? 'green' : 'purple'}>{s}</Tag> },
    { title: '操作', width: 130, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditValue(r)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => dataMaintApi.deleteValue(r.id).then(() => { message.success('已删除'); loadValues() })}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        数据维护 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>· 6 类指标 · 月度值 · 取数逻辑 · 按月出指标</span>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card><Statistic title={`${tab} 指标项`} value={totalItems} prefix={<AppstoreOutlined />} /></Card></Col>
        <Col span={6}><Card><Statistic title="已配置取数逻辑" value={itemsWithRule} prefix={<FunctionOutlined />} valueStyle={{ color: '#52c41a' }} /></Card></Col>
        <Col span={6}><Card>
          <Space>
            <span>数据日期：</span>
            <DatePicker value={selectedDate} onChange={setSelectedDate} picker="month" size="small" />
          </Space>
        </Card></Col>
        <Col span={6}><Card>
          <Space>
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={onMonthlyCalc}>按月出指标</Button>
            <Button icon={<CalculatorOutlined />} onClick={onCalcPreview}>预览</Button>
          </Space>
        </Card></Col>
      </Row>

      <Tabs
        activeKey={tab}
        onChange={setTab}
        items={CATEGORIES.map((c) => ({ key: c.code, label: <span><Tag color={c.color}>{c.code}</Tag> {c.name}</span> }))}
      />

      <Row gutter={16}>
        <Col span={9}>
          <Card title={`${tab} 指标项（按层级）`} size="small"
            extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => loadItems(tab)} />}
          >
            {itemTree.length > 0 ? (
              <Tree
                treeData={itemTree}
                defaultExpandAll
                showLine
                blockNode
                selectable
                onSelect={(_, info: any) => {
                  if (info.node) setSelectedItem(info.node.raw)
                }}
              />
            ) : <Empty description="无指标项" />}
          </Card>
        </Col>
        <Col span={15}>
          <Card title={selectedItem ? `${selectedItem.item_code} · ${selectedItem.item_name} 月度值` : '请选择左侧指标项'}
            size="small"
            extra={
              <Space>
                <Button size="small" icon={<ReloadOutlined />} onClick={loadValues}>刷新</Button>
                {selectedItem && (
                  <>
                    <Button size="small" icon={<FunctionOutlined />} onClick={() => onEditRule(selectedItem)}>取数逻辑</Button>
                    <Button type="primary" size="small" icon={<PlusOutlined />} onClick={onCreateValue}>新增值</Button>
                  </>
                )}
              </Space>
            }>
            {selectedItem ? (
              <>
                <Descriptions size="small" column={3} bordered style={{ marginBottom: 12 }}>
                  <Descriptions.Item label="编码">{selectedItem.item_code}</Descriptions.Item>
                  <Descriptions.Item label="层级">L{selectedItem.item_level}</Descriptions.Item>
                  <Descriptions.Item label="分类">{selectedItem.category}</Descriptions.Item>
                  <Descriptions.Item label="取数逻辑节点数" span={3}>
                    {selectedItem.coa_node_ids?.length > 0 ? (
                      <Space wrap>
                        {selectedItem.coa_node_ids.map((nid: number) => {
                          const node = coaTrees.find((c) => c.id === nid)
                          return node ? <Tag key={nid} color="blue">{node.node_code}</Tag> : <Tag key={nid}>ID:{nid}</Tag>
                        })}
                      </Space>
                    ) : <span style={{ color: '#999' }}>未配置（点【取数逻辑】按钮配置）</span>}
                  </Descriptions.Item>
                </Descriptions>
                <Table size="small" rowKey="id" dataSource={values} columns={valueCols}
                  scroll={{ x: 900 }} pagination={{ pageSize: 12, showTotal: (t) => `共 ${t} 条` }} />
              </>
            ) : <Empty description="请点击左侧指标项" style={{ padding: 60 }} />}
          </Card>
        </Col>
      </Row>

      <Modal title={editingValue ? '编辑月度值' : '新增月度值'} open={valueModal}
        onCancel={() => setValueModal(false)} onOk={onSaveValue}>
        <Form form={form} layout="vertical">
          <Form.Item name="item_id" hidden><Input /></Form.Item>
          <Form.Item name="data_date" label="数据日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} picker="month" />
          </Form.Item>
          <Form.Item name="value" label="指标值" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} step={1000} />
          </Form.Item>
          <Form.Item name="source" label="来源">
            <Select options={[
              { value: 'MANUAL', label: '手工录入' },
              { value: 'IMPORT', label: '导入' },
              { value: 'CALC', label: '系统计算' },
              { value: 'MODEL', label: '模型输出' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title={`配置取数逻辑：${selectedItem?.item_code || ''} · ${selectedItem?.item_name || ''}`}
        open={ruleModal} onCancel={() => setRuleModal(false)} onOk={onSaveRule} width={780}>
        <Form form={ruleForm} layout="vertical">
          <Alert type="info" showIcon style={{ marginBottom: 12 }}
            message="取数逻辑 = 多个账户册节点（分子）的余额求和。点击下方树选中叶子节点加入右侧已选列表。"
          />
          <Row gutter={16}>
            <Col span={10}>
              <Card size="small" title={`账户册树（${coaSchemes.find((s) => s.id === activeCoaScheme)?.scheme_code || ''}）`}>
                {coaTreeData.length > 0 ? (
                  <Tree
                    treeData={coaTreeData}
                    defaultExpandAll
                    showLine
                    blockNode
                    selectable
                    multiple
                    onSelect={(_, info: any) => {
                      const raw = info.node?.raw
                      if (raw && raw.node_level >= 3) {
                        const cur = ruleForm.getFieldValue('coa_node_ids') || []
                        if (!cur.includes(raw.id)) {
                          ruleForm.setFieldsValue({ coa_node_ids: [...cur, raw.id] })
                          message.success(`已添加：${raw.node_code} · ${raw.node_name}`)
                        }
                      } else if (raw) {
                        message.warning('请选择叶子节点（账户册）')
                      }
                    }}
                  />
                ) : <Empty />}
              </Card>
            </Col>
            <Col span={14}>
              <Form.Item name="coa_node_ids" label="已选账户册节点（求和）">
                <Select mode="multiple" placeholder="从左侧账户册树选择" style={{ width: '100%' }}>
                  {(ruleForm.getFieldValue('coa_node_ids') || []).map((nid: number) => {
                    const n = coaTrees.find((c) => c.id === nid)
                    return <Select.Option key={nid} value={nid}>
                      {n ? `${n.node_code} · ${n.node_name}` : `ID:${nid}`}
                    </Select.Option>
                  })}
                </Select>
              </Form.Item>
              <Form.Item name="formula" label="公式（可选）">
                <Input.TextArea rows={2} placeholder="可选：自定义公式，如 SUM(node_a, node_b) / node_c" />
              </Form.Item>
              <Form.Item name="description" label="说明">
                <Input.TextArea rows={2} placeholder="说明这个取数逻辑的含义..." />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </Spin>
  )
}

export default DataMaint
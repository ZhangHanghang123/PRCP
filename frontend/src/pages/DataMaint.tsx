import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, DatePicker, Popconfirm, Statistic, Alert,
  Tooltip, Dropdown, Tree, Tabs,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, DownloadOutlined, UploadOutlined,
  CalculatorOutlined, FunctionOutlined, EditOutlined, AppstoreOutlined,
  ThunderboltOutlined, FileTextOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import { dataMaintApi, coaApi } from '../api'

const CATEGORIES: Array<{ code: string; name: string; color: string; desc: string }> = [
  { code: 'FINANCIAL', name: '1. 账务结果指标',     color: '#667eea', desc: '资产负债表 + 利润表科目值' },
  { code: 'PARAM',     name: '2. 关键参数指标',     color: '#52c41a', desc: '存款准备金率 / 流动性比例等监管参数' },
  { code: 'SCALE',     name: '3. 规模指标',         color: '#f59e0b', desc: '资产/负债/客户数等规模量' },
  { code: 'PRICE',     name: '4. 价格指标',         color: '#eb2f96', desc: 'FTP 利率 / 存贷利率 / 利差' },
  { code: 'FEE',       name: '5. 中收指标',         color: '#13c2c2', desc: '手续费及佣金收入' },
  { code: 'RWA',       name: '6. 资本与RWA指标',    color: '#722ed1', desc: '资本充足率 / 风险加权资产' },
]

const DataMaint: React.FC = () => {
  const params = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  // 从 URL 拿 category，没有则默认 FINANCIAL
  const category = (params.category || 'FINANCIAL').toUpperCase()
  const categoryMeta = CATEGORIES.find((c) => c.code === category) || CATEGORIES[0]

  const [loading, setLoading] = useState(false)
  const [treeData, setTreeData] = useState<any[]>([])
  const [valuesMap, setValuesMap] = useState<Record<number, any>>({})
  const [months, setMonths] = useState<string[]>([])
  const [dataDate, setDataDate] = useState<Dayjs>(dayjs('2027-12-01'))
  const [selectedItem, setSelectedItem] = useState<any>(null)
  const [valueModal, setValueModal] = useState(false)
  const [ruleModal, setRuleModal] = useState(false)
  const [coaTrees, setCoaTrees] = useState<any[]>([])
  const [coaSchemes, setCoaSchemes] = useState<any[]>([])
  const [activeCoaScheme, setActiveCoaScheme] = useState<number | null>(null)
  const [form] = Form.useForm()
  const [ruleForm] = Form.useForm()

  // 加载数据日期列表
  const loadMonths = async () => {
    const r = await dataMaintApi.listMonths()
    setMonths(r.items || [])
  }

  // 加载账户册树（取数逻辑 Modal 用）
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

  // 加载当前 category + dataDate 的树+值
  const loadTree = async () => {
    setLoading(true)
    try {
      const r = await dataMaintApi.treeWithValues(category, dataDate.format('YYYY-MM-DD'))
      setTreeData(r.items || [])
      setValuesMap(r.values_map || {})
    } finally { setLoading(false) }
  }

  useEffect(() => { loadMonths(); loadCoaTrees() }, [])
  useEffect(() => { if (activeCoaScheme) loadCoaNodes(activeCoaScheme) }, [activeCoaScheme])
  useEffect(() => { setSelectedItem(null); loadTree() }, [category, dataDate])

  // 扁平化 + 嵌套数据，转换成 antd Table 用的格式
  // 同时把父节点的"继承"信息：子节点无值时显示父节点的值
  const flatRows = useMemo(() => {
    const rows: any[] = []
    const walk = (nodes: any[], inheritedValues: any | null) => {
      nodes.forEach((n) => {
        const v = valuesMap[n.id]
        const hasOwnValue = v && v.has_value
        // 父节点向下继承：如果自己有值，传递给自己；否则用祖先的
        const effValues = v || inheritedValues
        const isInherited = !hasOwnValue && inheritedValues != null
        rows.push({
          ...n,
          _effValues: effValues,
          _isInherited: isInherited,
          _hasOwnValue: hasOwnValue,
        })
        if (n.children?.length) walk(n.children, effValues)
      })
    }
    walk(treeData, null)
    return rows
  }, [treeData, valuesMap])

  // 切换 category
  const onCategoryChange = (key: string) => {
    navigate(`/data-maint/${key}`)
  }

  // 按月出指标
  const onMonthlyCalc = async () => {
    setLoading(true)
    try {
      const r = await dataMaintApi.monthlyCalc({ data_date: dataDate.format('YYYY-MM-DD'), category })
      message.success(`本月计算完成：${r.count || 0} 个指标`)
      loadTree()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '计算失败')
    } finally { setLoading(false) }
  }

  // 编辑取数逻辑
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
      loadTree()
    } catch (e: any) {
      if (e.errorFields) return
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  // 编辑/新增值（弹窗）
  const onEditValue = (row: any) => {
    setSelectedItem(row)
    const v = row._effValues || {}
    form.setFieldsValue({
      item_id: row.id,
      data_date: dataDate,
      value: v.value || 0,
      source: v.source || 'MANUAL',
    })
    setValueModal(true)
  }
  const onCreateValue = () => {
    if (!selectedItem) { message.warning('请先选择左侧指标'); return }
    form.resetFields()
    form.setFieldsValue({
      item_id: selectedItem.id,
      data_date: dataDate,
      value: 0,
      source: 'MANUAL',
    })
    setValueModal(true)
  }
  const onSaveValue = async () => {
    try {
      const v = await form.validateFields()
      await dataMaintApi.saveItemValue(v.item_id, {
        data_date: v.data_date.format('YYYY-MM-DD'),
        value: v.value,
        source: v.source,
      })
      message.success('已保存')
      setValueModal(false)
      loadTree()
    } catch (e: any) {
      if (e.errorFields) return
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  // 行内直接编辑（点击单元格 → InputNumber）
  const onCellEdit = async (row: any, field: 'value' | string, newVal: number) => {
    try {
      await dataMaintApi.saveItemValue(row.id, {
        data_date: dataDate.format('YYYY-MM-DD'),
        value: newVal,
        source: 'MANUAL',
      })
      message.success(`${row.item_code} ${field} 已更新`)
      loadTree()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '更新失败')
    }
  }

  // 表格列定义
  const baseCols: ColumnsType<any> = [
    {
      title: '账户册编码 / 指标编码', dataIndex: 'item_code', width: 180, fixed: 'left' as const,
      render: (c, r) => (
        <Space size={4}>
          <Tag color={
            r.item_level === 1 ? 'blue' :
            r.item_level === 2 ? 'cyan' :
            r.item_level === 3 ? 'geekblue' : 'green'
          } style={{ marginRight: 0 }}>L{r.item_level}</Tag>
          <code style={{ fontSize: 12, color: r.item_level <= 2 ? '#1d39c4' : '#595959' }}>{c}</code>
        </Space>
      ),
    },
    {
      title: '账户册名称 / 指标名称', dataIndex: 'item_name', width: 240, fixed: 'left' as const,
      render: (n, r) => (
        <Space>
          <FileTextOutlined style={{ color: r.item_level <= 2 ? '#1d39c4' : '#52c41a' }} />
          <span style={{ fontWeight: r.item_level <= 2 ? 600 : 400 }}>{n}</span>
          {r.coa_node_ids?.length > 0 && (
            <Tooltip title={`已配 ${r.coa_node_ids.length} 个账户册节点`}>
              <Tag color="green" style={{ marginLeft: 4 }}>已配取数</Tag>
            </Tooltip>
          )}
          {r._isInherited && (
            <Tooltip title="父节点已配置，本节点未单独设置 - 沿用父节点值">
              <Tag color="green">继承</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: (
        <Tooltip title="点击单元格编辑">
          <span>当期值 <small>({dataDate.format('YYYY-MM')})</small></span>
        </Tooltip>
      ),
      dataIndex: '_effValues', width: 140, fixed: 'left' as const,
      render: (_, r) => {
        const v = r._effValues
        if (!v) return <span style={{ color: '#ccc' }}>-</span>
        return (
          <Popconfirm
            title={`编辑 ${r.item_code} 当期值`}
            okText="保存"
            cancelText="取消"
            onConfirm={(e) => {
              // 用 Modal 编辑
              onEditValue(r)
            }}
          >
            <span
              style={{
                cursor: 'pointer',
                color: r._isInherited ? '#52c41a' : (v.value >= 0 ? '#cf1322' : '#3f8600'),
                fontWeight: 600,
                borderBottom: r._hasOwnValue ? '1px solid #1d39c4' : '1px dashed #52c41a',
                padding: '2px 4px',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {v.value != null ? (v.value as number).toLocaleString(undefined, { maximumFractionDigits: 4 }) : '—'}
            </span>
          </Popconfirm>
        )
      },
    },
  ]

  // M1 ~ M24 列
  const mCols: ColumnsType<any> = Array.from({ length: 24 }, (_, i) => ({
    title: `M${i + 1}`, dataIndex: '_effValues', width: 110,
    render: (_v: any, r: any) => {
      const v = r._effValues
      if (!v) return <span style={{ color: '#ccc' }}>-</span>
      const val = v[`m${i + 1}`] || 0
      return (
        <Tooltip title={`${r.item_code} M${i + 1} - ${r._isInherited ? '继承自父节点' : '本节点配置'}`}>
          <span style={{
            color: val > 0 ? '#cf1322' : val < 0 ? '#3f8600' : '#999',
            fontFamily: 'monospace',
          }}>
            {val === 0 ? '-' : (val as number).toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </span>
        </Tooltip>
      )
    },
  }))

  const actionCol: ColumnsType<any>[number] = {
    title: '操作', width: 100, fixed: 'right' as const,
    render: (_, r) => (
      <Space size="small">
        <Tooltip title="配置取数逻辑">
          <Button size="small" icon={<FunctionOutlined />} onClick={() => onEditRule(r)} />
        </Tooltip>
        <Tooltip title="编辑当期值">
          <Button size="small" icon={<EditOutlined />} onClick={() => { setSelectedItem(r); onEditValue(r) }} />
        </Tooltip>
      </Space>
    ),
  }

  const allCols = [...baseCols, ...mCols, actionCol]

  // KPI 统计
  const kpi = useMemo(() => {
    const total = flatRows.length
    const withRule = flatRows.filter((r) => r.coa_node_ids?.length > 0).length
    const withValue = flatRows.filter((r) => r._hasOwnValue).length
    return { total, withRule, withValue }
  }, [flatRows])

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>
          数据维护 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>
            · {categoryMeta.name} · {categoryMeta.desc}
          </span>
        </span>
      </div>

      {/* 顶部 6 类指标 Tab */}
      <Card bordered={false} size="small" style={{ marginBottom: 16 }}>
        <Tabs
          activeKey={category}
          onChange={onCategoryChange}
          type="card"
          items={CATEGORIES.map((c) => ({
            key: c.code,
            label: (
              <span>
                <Tag color={c.color} style={{ marginRight: 4 }}>{c.code}</Tag>
                {c.name}
              </span>
            ),
          }))}
        />
      </Card>

      {/* 数据日期 + 操作按钮 */}
      <Card bordered={false} style={{ marginBottom: 16 }} size="small">
        <Row gutter={16} align="middle">
          <Col>
            <span style={{ marginRight: 8 }}>数据日期：</span>
            <DatePicker
              value={dataDate}
              onChange={setDataDate}
              picker="month"
              format="YYYY-MM"
            />
            <span style={{ marginLeft: 12, color: '#999', fontSize: 12 }}>
              （切换日期后自动加载该月数据 + M1~M24 预测值）
            </span>
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadTree}>刷新</Button>
              <Button icon={<DownloadOutlined />}>导出 Excel</Button>
              <Button icon={<UploadOutlined />}>导入 Excel</Button>
              <Button icon={<ThunderboltOutlined />} type="primary" onClick={onMonthlyCalc}>按月出指标</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* KPI 看板 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic title="指标项数（含层级）" value={kpi.total} prefix={<AppstoreOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="已配置取数逻辑"
              value={kpi.withRule}
              prefix={<FunctionOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title={`当期(${dataDate.format('YYYY-MM')})有值指标`}
              value={kpi.withValue}
              prefix={<CalculatorOutlined />}
              valueStyle={{ color: '#1d39c4' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 主表 */}
      <Card bordered={false} size="small">
        <Alert
          type="info" showIcon style={{ marginBottom: 12 }}
          message="横向滚动查看 M1 ~ M24 风险权重；父级配置后下级继承（绿色「继承」标签）；点击「当期值」单元格或操作列的编辑按钮覆盖当前节点单独设置"
        />
        <Table
          size="small"
          rowKey="id"
          dataSource={flatRows}
          columns={allCols}
          scroll={{ x: 180 + 240 + 140 + 24 * 110 + 100 }}
          pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
          indentSize={20}
          defaultExpandAllRows
          rowClassName={(r) => r.item_level <= 2 ? 'row-level-high' : ''}
          locale={{ emptyText: <Empty description={`${categoryMeta.name} 暂无数据，请先在「报表表项管理」中维护该类别指标项`} /> }}
        />
      </Card>

      {/* 取数逻辑 Modal */}
      <Modal
        title={`配置取数逻辑：${selectedItem?.item_code || ''} · ${selectedItem?.item_name || ''}`}
        open={ruleModal} onCancel={() => setRuleModal(false)} onOk={onSaveRule} width={780}
      >
        <Form form={ruleForm} layout="vertical">
          <Alert type="info" showIcon style={{ marginBottom: 12 }}
            message="取数逻辑 = 多个账户册节点（求和）或自定义公式。点击左侧树选中 L3 账户册节点加入右侧已选列表。" />
          <Row gutter={16}>
            <Col span={10}>
              <Card size="small" title={`账户册树（${coaSchemes.find((s) => s.id === activeCoaScheme)?.scheme_code || ''}）`}>
                {coaTrees.length > 0 ? (
                  <AccountTree nodes={coaTrees} onPick={(node) => {
                    if (node.node_level < 3) { message.warning('请选择叶子节点（账户册）'); return }
                    const cur = ruleForm.getFieldValue('coa_node_ids') || []
                    if (!cur.includes(node.id)) {
                      ruleForm.setFieldsValue({ coa_node_ids: [...cur, node.id] })
                      message.success(`已添加：${node.node_code}`)
                    }
                  }} />
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
                <Input.TextArea rows={2} placeholder="如 SUM(node_a, node_b) / node_c" />
              </Form.Item>
              <Form.Item name="description" label="说明">
                <Input.TextArea rows={2} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 编辑当期值 Modal */}
      <Modal title={selectedItem ? `编辑当期值：${selectedItem.item_code} · ${selectedItem.item_name}` : '编辑值'}
        open={valueModal} onCancel={() => setValueModal(false)} onOk={onSaveValue} width={520}>
        <Form form={form} layout="vertical">
          <Form.Item name="item_id" hidden><Input /></Form.Item>
          <Form.Item name="data_date" label="数据日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} picker="month" format="YYYY-MM-DD" />
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
    </Spin>
  )
}

// 简易账户册树（不带 antd Tree 控件）
const AccountTree: React.FC<{ nodes: any[]; onPick: (n: any) => void }> = ({ nodes, onPick }) => {
  const renderNode = (n: any, depth: number) => (
    <div key={n.id} style={{ paddingLeft: depth * 16, lineHeight: '24px', cursor: 'pointer' }}
      onClick={() => onPick(n)}
      onMouseEnter={(e) => (e.currentTarget.style.background = '#f5f5f5')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}>
      <Tag color={n.node_level === 1 ? 'blue' : n.node_level === 2 ? 'cyan' : 'geekblue'}>
        L{n.node_level}
      </Tag>
      <code style={{ fontSize: 12 }}>{n.node_code}</code>
      <span style={{ marginLeft: 6 }}>{n.node_name}</span>
    </div>
  )
  const flat: any[] = []
  const walk = (ns: any[], d: number) => ns.forEach((n) => {
    flat.push(renderNode(n, d))
    if (n.children?.length) walk(n.children, d + 1)
  })
  walk(nodes, 0)
  return <div style={{ maxHeight: 400, overflow: 'auto' }}>{flat}</div>
}

export default DataMaint

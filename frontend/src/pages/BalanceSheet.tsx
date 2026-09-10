import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Tabs, Tree, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, DatePicker, Popconfirm, Row, Col,
  Tooltip, Divider, Badge, Upload,
} from 'antd'
import {
  DeleteOutlined, ReloadOutlined, PlusOutlined, EditOutlined,
  FundProjectionScreenOutlined, BankOutlined, RiseOutlined, FallOutlined,
  PartitionOutlined, DownloadOutlined, UploadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { balanceApi, coaApi } from '../api'

const { DirectoryTree } = Tree

// 二级指标定义（顺序即表头顺序，按截图：月初/月末/平均/利率/利息/资本/风险）
const MEASURES = [
  { key: 'begin_balance',   name: '月初余额',     width: 90,  color: '#595959', precision: 2, isPercent: false },
  { key: 'current_amount',  name: '月末余额',     width: 95,  color: '#cf1322', precision: 2, isPercent: false },
  { key: 'avg_balance',     name: '平均余额',     width: 90,  color: '#1d39c4', precision: 2, isPercent: false },
  { key: 'interest_rate',   name: '利率(%)',     width: 60,  color: '#fa8c16', precision: 4, isPercent: true  },
  { key: 'interest_amount', name: '利息收支',     width: 45,  color: '#722ed1', precision: 2, isPercent: false },
  { key: 'capital_ratio',   name: '资本占用(%)', width: 70,  color: '#13c2c2', precision: 4, isPercent: true  },
  { key: 'risk_weight',     name: '风险权重(%)', width: 80,  color: '#eb2f96', precision: 4, isPercent: true  },
]

const BalanceSheet: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [activeScheme, setActiveScheme] = useState<number | null>(null)
  const [treeData, setTreeData] = useState<any[]>([])
  const [matrix, setMatrix] = useState<Record<number, Record<string, any>>>({})
  const [matrixDates, setMatrixDates] = useState<string[]>([])
  const [matrixNodes, setMatrixNodes] = useState<any[]>([])
  const [categoriesAgg, setCategoriesAgg] = useState<Record<string, Record<string, any>>>({})
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [startMonth, setStartMonth] = useState<Dayjs>(dayjs('2027-01-01'))
  const [endMonth, setEndMonth] = useState<Dayjs>(dayjs('2027-12-01'))
  const [form] = Form.useForm()

  // 加载方案
  const loadSchemes = async () => {
    const r = await coaApi.listSchemes()
    setSchemes(r.items || [])
    if (!activeScheme && r.items?.length) {
      const v6 = r.items.find((s: any) => s.scheme_code === 'COA_V6') || r.items[0]
      setActiveScheme(v6.id)
    }
  }
  useEffect(() => { loadSchemes() }, [])

  // 加载账户册树
  const loadTree = async () => {
    if (!activeScheme) return
    const r = await coaApi.treeNodes(activeScheme)
    setTreeData(r.items || [])
  }
  useEffect(() => { loadTree() }, [activeScheme])

  // 加载矩阵
  const loadMatrix = async () => {
    if (!activeScheme) return
    setLoading(true)
    try {
      const r = await balanceApi.bySchemeMatrix(
        activeScheme,
        startMonth.format('YYYY-MM-DD'),
        endMonth.format('YYYY-MM-DD'),
      )
      setMatrix(r.matrix || {})
      setMatrixDates(r.dates || [])
      setMatrixNodes(r.nodes || [])
      setCategoriesAgg(r.categories || {})
    } finally { setLoading(false) }
  }
  useEffect(() => { loadMatrix() }, [activeScheme, startMonth, endMonth])

  // 新增/编辑弹窗
  const onCreate = (preselectNodeId?: number) => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      coa_node_id: preselectNodeId,
      data_date: endMonth,
      current_amount: 0, begin_balance: 0, avg_balance: 0,
      interest_rate: 0, interest_amount: 0,
      capital_ratio: 0, risk_weight: 0,
      gaps: Array(24).fill(0),
    })
    setModalOpen(true)
  }
  // 导出 Excel：直接用 fetch 拉后端二进制流，浏览器自动下载
  const onExport = async () => {
    if (!activeScheme) { message.warning('请先选择账户册方案'); return }
    try {
      const url = balanceApi.exportXlsxUrl(activeScheme, startMonth.format('YYYY-MM') + '-01', endMonth.format('YYYY-MM') + '-01')
      const token = localStorage.getItem('prcp_token') || ''
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `prcp_balance_${startMonth.format('YYYYMM')}-${endMonth.format('YYYYMM')}.xlsx`
      a.click()
      URL.revokeObjectURL(a.href)
      message.success('导出成功')
    } catch (e: any) {
      message.error(`导出失败：${e.message}`)
    }
  }

  // 导入 Excel
  const onImport = async (file: File) => {
    const hide = message.loading('导入中...', 0)
    try {
      const res = await balanceApi.importXlsx(file)
      hide()
      const msg = `导入完成：新增 ${res.inserted} 条，更新 ${res.updated} 条，跳过 ${res.skipped} 条` +
        (res.total_errors > 0 ? `，错误 ${res.total_errors} 条` : '')
      if (res.total_errors > 0) {
        Modal.warning({ title: '部分导入失败', content: `${msg}\n\n前 20 条错误：\n${(res.errors || []).join('\n')}` })
      } else {
        message.success(msg)
      }
      loadMatrix()
    } catch (e: any) {
      hide()
      message.error(`导入失败：${e?.response?.data?.detail || e.message}`)
    }
  }

  const onEditCell = (nodeId: number, ym: string) => {
    const node = matrixNodes.find((n) => n.coa_node_id === nodeId)
    const cell = matrix[String(nodeId)]?.[ym] || {}
    setEditing({ node_code: node?.node_code, node_name: node?.node_name, ym })
    form.setFieldsValue({
      coa_node_id: nodeId,
      data_date: dayjs(ym + '-01'),
      current_amount: cell.current_amount || 0,
      begin_balance: cell.begin_balance || 0,
      avg_balance: cell.avg_balance || 0,
      interest_rate: cell.interest_rate || 0,
      interest_amount: cell.interest_amount || 0,
      capital_ratio: cell.capital_ratio || 0,
      risk_weight: cell.risk_weight || 0,
      gaps: [],
      calc_note: '',
    })
    setModalOpen(true)
  }
  const onSave = async () => {
    const v = await form.validateFields()
    try {
      await balanceApi.upsert({
        coa_node_id: v.coa_node_id,
        data_date: v.data_date.format('YYYY-MM-DD'),
        current_amount: v.current_amount,
        begin_balance: v.begin_balance,
        avg_balance: v.avg_balance,
        interest_rate: v.interest_rate,
        interest_amount: v.interest_amount,
        capital_ratio: v.capital_ratio,
        risk_weight: v.risk_weight,
        gaps: v.gaps,
        calc_note: v.calc_note,
      })
      message.success('已保存')
      setModalOpen(false)
      loadMatrix()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  // 树形行：L1 大类 → L2 业务分组 → L3 账户册（递归按层级排序）
  const accountRows = useMemo(() => {
    const nodes = matrixNodes.filter((n) => n.node_level >= 1 && n.node_level <= 3)
    const byParent: Record<number, any[]> = {}
    nodes.forEach((n) => {
      const key = n.parent_id || 0
      if (!byParent[key]) byParent[key] = []
      byParent[key].push(n)
    })
    Object.values(byParent).forEach((arr) =>
      arr.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)),
    )
    const flat: any[] = []
    const walk = (parentId: number | null) => {
      const children = byParent[parentId || 0] || []
      children.forEach((c) => {
        flat.push(c)
        if (c.node_level < 3) walk(c.coa_node_id)
      })
    }
    walk(null)
    return flat
  }, [matrixNodes])

  // 表格列定义：固定列 + 二级表头（每个月 group 下挂 7 个指标）
  // 树形缩进：根据 node_level 加 paddingLeft
  const indent = (level: number) => ({ paddingLeft: (level - 1) * 20 })

  const baseCols: ColumnsType<any> = [
    { title: '账户册编码', dataIndex: 'node_code', width: 50, fixed: 'left' as const,
      render: (c, r) => (
        <span style={{ ...indent(r.node_level) }}>
          <code style={{ color: r.node_level === 3 ? '#1d39c4' : '#999', fontSize: 12, fontWeight: r.node_level < 3 ? 600 : 400 }}>{c}</code>
        </span>
      ),
    },
    { title: '账户册名称', dataIndex: 'node_name', width: 165, fixed: 'left' as const,
      render: (n, r) => {
        const fontSize = r.node_level === 1 ? 15 : r.node_level === 2 ? 14 : 13
        const fontWeight = r.node_level < 3 ? 700 : 500
        const color = r.node_level === 1 ? '#1d39c4' : r.node_level === 2 ? '#722ed1' : '#262626'
        // tooltip 内容：账户册名称 + 业务口径说明
        const tipContent = r.description
          ? <div style={{ maxWidth: 360 }}>
              <div style={{ fontWeight: 600 }}>{n}</div>
              <div style={{ marginTop: 4, color: '#bbb' }}>{r.description}</div>
            </div>
          : n
        return (
          <Tooltip title={tipContent} placement="topLeft">
            <span style={{
              ...indent(r.node_level),
              fontSize, fontWeight, color,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: 'inline-block',
              maxWidth: 145,
            }}>
              {r.node_level === 1 && <Tag color="blue" style={{ marginRight: 6 }}>大类</Tag>}
              {r.node_level === 2 && <Tag color="purple" style={{ marginRight: 6 }}>分组</Tag>}
              {n}
            </span>
          </Tooltip>
        )
      },
    },
    { title: '大类', dataIndex: 'category', width: 48, fixed: 'left' as const,
      render: (v) => {
        const color = v === '资产' ? 'blue' : v === '负债' ? 'orange' : 'purple'
        return <Tag color={color} style={{ marginRight: 0 }}>{v || '-'}</Tag>
      },
    },
  ]

  // 二级表头：每个月一个 group，group.title = 月份，group.children = 7 个指标列
  const monthGroups: any[] = matrixDates.map((ym) => ({
    title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>{ym}</span>,
    children: MEASURES.map((m) => ({
      title: <span style={{ color: m.color, fontSize: 12 }}>{m.name}</span>,
      dataIndex: `_m_${ym}_${m.key}`,
      width: m.width,
      align: 'right' as const,
      onHeaderCell: () => ({ style: { background: '#fafafa' } }),
      render: (_v: any, r: any) => {
        const cell = matrix[String(r.coa_node_id)]?.[ym] || {}
        const v = cell[m.key]
        if (v === undefined || v === null) {
          return <span style={{ color: '#ccc' }}>-</span>
        }
        const formatted = m.isPercent
          ? (v as number).toFixed(m.precision) + '%'
          : (v as number).toLocaleString(undefined, { maximumFractionDigits: m.precision })
        return (
          <Tooltip title={`点击编辑 ${ym} · ${m.name}`}>
            <span
              onClick={() => onEditCell(r.coa_node_id, ym)}
              style={{
                cursor: 'pointer',
                color: m.color,
                fontFamily: m.isPercent ? 'monospace' : undefined,
                fontWeight: m.key === 'current_amount' ? 600 : 400,
              }}
            >
              {formatted}
            </span>
          </Tooltip>
        )
      },
    })),
  }))

  const actionCol: ColumnsType<any>[number] = {
    title: '操作', width: 80, fixed: 'right' as const,
    render: (_, r) => (
      <Button size="small" type="link" icon={<EditOutlined />}
        onClick={() => onEditCell(r.coa_node_id, matrixDates[matrixDates.length - 1] || dayjs().format('YYYY-MM'))}>
        编辑
      </Button>
    ),
  }

  const allCols: ColumnsType<any> = [...baseCols, ...monthGroups, actionCol]

  // 大类汇总列（行=资产/负债/表外，列=月份）
  const categoryBaseCols: ColumnsType<any> = [
    { title: '大类', dataIndex: 'category', width: 110, fixed: 'left' as const,
      render: (v, r) => {
        const color = v === '资产' ? 'blue' : v === '负债' ? 'orange' : 'purple'
        const subs = matrixNodes
          .filter((n) => n.path?.startsWith(`/L1_${r.category}`) && n.node_level === 3)
          .map((n) => `${n.node_code} ${n.node_name}`)
        const tipContent = (
          <div style={{ maxWidth: 480 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{v}（共 {subs.length} 册）</div>
            <div style={{ color: '#bbb', fontSize: 12, lineHeight: 1.6 }}>
              {subs.join(' / ')}
            </div>
          </div>
        )
        return (
          <Tooltip title={tipContent} placement="topLeft">
            <Tag color={color} style={{ fontSize: 14, cursor: 'help' }}>{v}（{subs.length}）</Tag>
          </Tooltip>
        )
      },
    },
    { title: '账户册数', dataIndex: 'account_count', width: 100, fixed: 'left' as const,
      render: (v, r) => v || (matrixNodes.filter((n) =>
        n.path?.startsWith(`/L1_${r.category}`) && n.node_level === 3).length) },
  ]
  const categoryMonthGroups: any[] = matrixDates.map((ym) => ({
    title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>{ym}</span>,
    children: MEASURES.map((m) => ({
      title: <span style={{ color: m.color, fontSize: 12 }}>{m.name}</span>,
      dataIndex: `_cm_${ym}_${m.key}`,
      width: m.width, align: 'right' as const,
      render: (_v: any, r: any) => {
        const cell = categoriesAgg[r.category]?.[ym] || {}
        const v = cell[m.key]
        if (v === undefined || v === null) return <span style={{ color: '#ccc' }}>-</span>
        const formatted = m.isPercent
          ? (v as number).toFixed(m.precision) + '%'
          : (v as number).toLocaleString(undefined, { maximumFractionDigits: m.precision })
        return <span style={{ color: m.color }}>{formatted}</span>
      },
    })),
  }))
  const allCatCols: ColumnsType<any> = [...categoryBaseCols, ...categoryMonthGroups]

  const renderTreeTitle = (node: any) => (
    <span>
      <Tag color={node.level === 1 ? 'blue' : node.level === 2 ? 'cyan' : 'geekblue'} style={{ marginRight: 4 }}>
        L{node.level}
      </Tag>
      <strong>{node.name || node.code}</strong>
      <span style={{ color: '#999', marginLeft: 4, fontSize: 12 }}>({node.code})</span>
    </span>
  )
  const convertTree = (nodes: any[]): any[] =>
    nodes.map((n) => ({
      title: renderTreeTitle(n),
      key: String(n.id),
      raw: n,
      children: n.children?.length ? convertTree(n.children) : undefined,
    }))

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>
          账户册总表（资产/负债/表外·按业务层级）
          <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal', marginLeft: 8 }}>
            ——余额：亿元；利率、资本占用比例、风险权重：%；平均利息收支：亿元/月
          </span>
        </span>
      </div>

      {/* 顶部筛选 + 时间窗口 */}
      <Card bordered={false} style={{ marginBottom: 16 }} size="small">
        <Row gutter={16} align="middle">
          <Col>
            <span style={{ marginRight: 8 }}>账户册方案：</span>
            <Select
              style={{ width: 240 }}
              value={activeScheme || undefined}
              onChange={setActiveScheme}
              options={schemes.map((s) => ({
                value: s.id,
                label: `${s.scheme_name} (${s.scheme_code})`
              }))}
            />
          </Col>
          <Col>
            <span style={{ marginRight: 8 }}>起始月份：</span>
            <DatePicker
              value={startMonth} onChange={setStartMonth}
              picker="month" format="YYYY-MM"
            />
          </Col>
          <Col>
            <span style={{ marginRight: 8 }}>结束月份：</span>
            <DatePicker
              value={endMonth} onChange={setEndMonth}
              picker="month" format="YYYY-MM"
            />
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadMatrix}>刷新</Button>
              <Button icon={<DownloadOutlined />} onClick={onExport}>导出 Excel</Button>
              <Upload
                accept=".xlsx"
                showUploadList={false}
                beforeUpload={(file) => { onImport(file); return false }}
              >
                <Button icon={<UploadOutlined />}>导入 Excel</Button>
              </Upload>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => onCreate()}>新增月度数据</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 主内容 */}
      <Card bordered={false} bodyStyle={{ paddingTop: 8 }}>
        <Tabs
          defaultActiveKey="matrix"
          items={[
            {
              key: 'matrix',
              label: <span><BankOutlined /> 账户册矩阵（二级表头） <Badge count={accountRows.length} showZero color="#1d39c4" /></span>,
              children: (
                <Table
                  size="small"
                  rowKey="coa_node_id"
                  dataSource={accountRows}
                  columns={allCols as any}
                  scroll={{ x: 50 + 165 + 48 + matrixDates.length * 7 * 110 + 80, y: 'calc(100vh - 380px)' }}
                  pagination={false}
                  bordered
                  locale={{ emptyText: <Empty description="该时间窗口无账户册月度数据" /> }}
                />
              ),
            },
            {
              key: 'category',
              label: <span><FundProjectionScreenOutlined /> 大类汇总（资产/负债/表外）</span>,
              children: (
                <Table
                  size="small"
                  rowKey="category"
                  dataSource={[
                    { category: '资产', account_count: matrixNodes.filter((n) => n.path?.startsWith('/L1_资产') && n.node_level === 3).length },
                    { category: '负债', account_count: matrixNodes.filter((n) => n.path?.startsWith('/L1_负债') && n.node_level === 3).length },
                    { category: '表外', account_count: matrixNodes.filter((n) => n.path?.startsWith('/L1_表外') && n.node_level === 3).length },
                  ]}
                  columns={allCatCols as any}
                  scroll={{ x: 110 + 100 + matrixDates.length * 7 * 110, y: 'calc(100vh - 380px)' }}
                  pagination={false}
                  bordered
                />
              ),
            },
            {
              key: 'tree',
              label: <span><PartitionOutlined /> 账户册树（按层级）</span>,
              children: (
                <div style={{ minHeight: 400 }}>
                  {treeData.length === 0 ? <Empty /> : (
                    <DirectoryTree
                      treeData={convertTree(treeData)}
                      defaultExpandAll blockNode
                      onSelect={(keys, info) => {
                        const n = (info.node as any)?.raw
                        if (n?.level === 3) onCreate(n.id)
                      }}
                    />
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* 编辑弹窗 */}
      <Modal
        title={editing ? `编辑 ${editing.node_code} · ${editing.node_name} - ${editing.ym || ''}` : '新增账户册月度数据'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={onSave}
        width={720}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="coa_node_id" label="账户册节点" rules={[{ required: true }]}>
                <Select
                  showSearch optionFilterProp="label"
                  options={matrixNodes
                    .filter((n) => n.node_level === 3)
                    .map((n) => ({ value: n.coa_node_id, label: `${n.node_code} - ${n.node_name}` }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="data_date" label="数据日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} picker="month" format="YYYY-MM-DD" />
              </Form.Item>
            </Col>
          </Row>
          <Divider orientation="left" style={{ fontSize: 13 }}>7 个度量</Divider>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="begin_balance"   label="期初余额"><InputNumber style={{ width: '100%' }} step={1000} /></Form.Item></Col>
            <Col span={8}><Form.Item name="avg_balance"     label="平均余额"><InputNumber style={{ width: '100%' }} step={1000} /></Form.Item></Col>
            <Col span={8}><Form.Item name="current_amount"  label="期末余额"><InputNumber style={{ width: '100%' }} step={1000} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="interest_rate"   label="加权平均利率（%）"><InputNumber style={{ width: '100%' }} step={0.0001} precision={4} /></Form.Item></Col>
            <Col span={8}><Form.Item name="interest_amount" label="本期利息"><InputNumber style={{ width: '100%' }} step={1000} /></Form.Item></Col>
            <Col span={8}><Form.Item name="capital_ratio"   label="资本占用比例（%）"><InputNumber style={{ width: '100%' }} step={0.0001} precision={4} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="risk_weight"     label="风险权重（%）"><InputNumber style={{ width: '100%' }} step={0.0001} precision={4} /></Form.Item></Col>
            <Col span={16}><Form.Item name="calc_note"       label="备注"><Input.TextArea rows={2} /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>
    </Spin>
  )
}

// 兼容 antd Tabs 的二级表头
;(Table as any).SECOND_LEVEL_HEADER = true

export default BalanceSheet

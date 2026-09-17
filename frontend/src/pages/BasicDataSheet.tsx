import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Tabs, Tree as AntTree, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, DatePicker, Row, Col,
  Tooltip, Divider, Badge, Upload,
} from 'antd'
import {
  ReloadOutlined, EditOutlined, DownloadOutlined, UploadOutlined, PlusOutlined,
  DatabaseOutlined, BankOutlined, PartitionOutlined, FundProjectionScreenOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { basicApi, coaApi } from '../api'

// 13 个期限桶（统一两端：原始 + 剩余）
const BUCKETS = [
  { key: 'd1',  name: '1日',  width: 60 },
  { key: 'd7',  name: '7日',  width: 60 },
  { key: 'm1',  name: '1M',   width: 65 },
  { key: 'm3',  name: '3M',   width: 65 },
  { key: 'm6',  name: '6M',   width: 65 },
  { key: 'y1',  name: '1Y',   width: 65 },
  { key: 'y2',  name: '2Y',   width: 65 },
  { key: 'y3',  name: '3Y',   width: 65 },
  { key: 'y5',  name: '5Y',   width: 65 },
  { key: 'y10', name: '10Y',  width: 70 },
  { key: 'y15', name: '15Y',  width: 70 },
  { key: 'y20', name: '20Y',  width: 70 },
  { key: 'y30', name: '30Y',  width: 75 },
]

// 额外度量列
const EXTRAS = [
  { key: 'asf_rsf',         name: 'ASF/RSF',   width: 70,  isPercent: false, precision: 0 },
  { key: 'hqla_factor',     name: 'HQLA折算',  width: 75,  isPercent: true,  precision: 4 },
  { key: 'current_balance', name: '当前余额',  width: 95,  isPercent: false, precision: 2 },
  { key: 'avg_balance',     name: '平均余额',  width: 95,  isPercent: false, precision: 2 },
  { key: 'weighted_rate',   name: '加权利率',  width: 70,  isPercent: true,  precision: 4 },
  { key: 'interest_amount', name: '利息收支',  width: 80,  isPercent: false, precision: 2 },
  { key: 'risk_weight',     name: '风险权重',  width: 80,  isPercent: true,  precision: 4 },
]

const { DirectoryTree } = AntTree

const BasicDataSheet: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [activeScheme, setActiveScheme] = useState<number | null>(null)
  const [matrix, setMatrix] = useState<Record<number, Record<string, any>>>({})
  const [matrixNodes, setMatrixNodes] = useState<any[]>([])
  const [categoriesAgg, setCategoriesAgg] = useState<Record<string, Record<string, any>>>({})
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [dataDate, setDataDate] = useState<Dayjs>(dayjs('2027-01-01'))
  const [dateOffset, setDateOffset] = useState<number>(0)
  const [offsetUnit, setOffsetUnit] = useState<string>('D')
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [form] = Form.useForm()

  // 加载方案
  const loadSchemes = async () => {
    const r = await coaApi.listSchemes()
    setSchemes(r.items || [])
    if (!activeScheme && r.items?.length) {
      // 默认账户册方案：ZXCOA_V1 > COA_V6 > 第一个
      const zx = r.items.find((s: any) => s.scheme_code === 'ZXCOA_V1')
      const v6 = r.items.find((s: any) => s.scheme_code === 'COA_V6')
      setActiveScheme((zx || v6 || r.items[0]).id)
    }
  }
  useEffect(() => { loadSchemes() }, [])

  // 已录入日期列表
  const loadAvailableDates = async () => {
    if (!activeScheme) return
    const r = await basicApi.listDates(activeScheme)
    setAvailableDates(r.items || [])
    const cur = dataDate.format('YYYY-MM-DD')
    if ((r.items || []).length > 0 && !r.items.includes(cur)) {
      setDataDate(dayjs(r.items[0]))
    }
  }
  useEffect(() => { loadAvailableDates() }, [activeScheme])

  // 加载矩阵
  const loadMatrix = async () => {
    if (!activeScheme) return
    setLoading(true)
    try {
      const r = await basicApi.bySchemeMatrix(
        activeScheme,
        dataDate.format('YYYY-MM-DD'),
        dateOffset,
        offsetUnit,
      )
      setMatrix(r.matrix || {})
      setMatrixNodes(r.nodes || [])
      setCategoriesAgg(r.categories || {})
    } finally { setLoading(false) }
  }
  useEffect(() => { loadMatrix() }, [activeScheme, dataDate, dateOffset, offsetUnit])

  // 导出
  const onExport = async () => {
    if (!activeScheme) { message.warning('请先选择账户册方案'); return }
    try {
      const url = basicApi.exportXlsxUrl(activeScheme, dataDate.format('YYYY-MM-DD'), dateOffset, offsetUnit)
      const token = localStorage.getItem('prcp_token') || ''
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `prcp_basic_${dataDate.format('YYYYMMDD')}_${dateOffset}${offsetUnit}.xlsx`
      a.click()
      URL.revokeObjectURL(a.href)
      message.success('导出成功')
    } catch (e: any) {
      message.error(`导出失败：${e.message}`)
    }
  }

  // 导入
  const onImport = async (file: File) => {
    if (!activeScheme) { message.warning('请先选择账户册方案'); return }
    const hide = message.loading('导入中...', 0)
    try {
      const res = await basicApi.importXlsx(file, activeScheme, dataDate.format('YYYY-MM-DD'), dateOffset, offsetUnit)
      hide()
      const msg = `导入完成：新增 ${res.inserted} 条，更新 ${res.updated} 条，跳过 ${res.skipped} 条` +
        (res.total_errors > 0 ? `，错误 ${res.total_errors} 条` : '')
      if (res.total_errors > 0) {
        Modal.warning({ title: '部分导入失败', content: `${msg}\n\n前 20 条错误：\n${(res.errors || []).join('\n')}` })
      } else {
        message.success(msg)
      }
      loadMatrix()
      loadAvailableDates()
    } catch (e: any) {
      hide()
      message.error(`导入失败：${e?.response?.data?.detail || e.message}`)
    }
  }

  // 编辑单元
  const onEdit = (nodeId: number) => {
    const node = matrixNodes.find((n) => n.coa_node_id === nodeId)
    const cell = matrix[String(nodeId)] || {}
    setEditing({ node_code: node?.node_code, node_name: node?.node_name })
    form.setFieldsValue({
      coa_node_id: nodeId,
      data_date: dataDate,
      date_offset: dateOffset,
      offset_unit: offsetUnit,
      orig: cell.orig || Array(13).fill(0),
      rem: cell.rem || Array(13).fill(0),
      asf_rsf: cell.asf_rsf || '',
      hqla_factor: cell.hqla_factor || 0,
      current_balance: cell.current_balance || 0,
      avg_balance: cell.avg_balance || 0,
      weighted_rate: cell.weighted_rate || 0,
      interest_amount: cell.interest_amount || 0,
      risk_weight: cell.risk_weight || 0,
      calc_note: '',
    })
    setModalOpen(true)
  }

  const onCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      data_date: dataDate,
      date_offset: dateOffset,
      offset_unit: offsetUnit,
      orig: Array(13).fill(0),
      rem: Array(13).fill(0),
      asf_rsf: '',
      hqla_factor: 0,
      current_balance: 0,
      avg_balance: 0,
      weighted_rate: 0,
      interest_amount: 0,
      risk_weight: 0,
    })
    setModalOpen(true)
  }

  const onSave = async () => {
    const v = await form.validateFields()
    try {
      await basicApi.upsert({
        ...v,
        data_date: v.data_date.format('YYYY-MM-DD'),
      })
      message.success('已保存')
      setModalOpen(false)
      loadMatrix()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  // 树形行：L1 → L2 → L3
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

  const indent = (level: number) => ({ paddingLeft: (level - 1) * 20 })

  // 固定列
  const baseCols: ColumnsType<any> = [
    { title: '账户册编码', dataIndex: 'node_code', width: 60, fixed: 'left' as const,
      render: (c, r) => (
        <span style={{ ...indent(r.node_level) }}>
          <code style={{ color: r.node_level === 3 ? '#1d39c4' : '#999', fontSize: 12, fontWeight: r.node_level < 3 ? 600 : 400 }}>{c}</code>
        </span>
      ),
    },
    { title: '账户册名称', dataIndex: 'node_name', width: 200, fixed: 'left' as const,
      render: (n, r) => {
        const fontSize = r.node_level === 1 ? 15 : r.node_level === 2 ? 14 : 13
        const fontWeight = r.node_level < 3 ? 700 : 500
        const color = r.node_level === 1 ? '#1d39c4' : r.node_level === 2 ? '#722ed1' : '#262626'
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
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              display: 'inline-block', maxWidth: 185,
            }}>
              {r.node_level === 1 && <Tag color="blue" style={{ marginRight: 6 }}>大类</Tag>}
              {r.node_level === 2 && <Tag color="purple" style={{ marginRight: 6 }}>分组</Tag>}
              {n}
            </span>
          </Tooltip>
        )
      },
    },
    { title: '大类', dataIndex: 'category', width: 50, fixed: 'left' as const,
      render: (v) => {
        const color = v === '资产' ? 'blue' : v === '负债' ? 'orange' : 'purple'
        return <Tag color={color} style={{ marginRight: 0 }}>{v || '-'}</Tag>
      },
    },
  ]

  // 单元格渲染（金额）
  const makeCell = (colKey: string, color: string, precision: number) =>
    (_v: any, r: any) => {
      const cell = matrix[String(r.coa_node_id)] || {}
      const v = cell[colKey]
      if (v === undefined || v === null) return <span style={{ color: '#ccc' }}>-</span>
      return (
        <Tooltip title={`点击编辑 ${colKey}`}>
          <span onClick={() => onEdit(r.coa_node_id)}
            style={{ cursor: 'pointer', color, fontFamily: 'monospace' }}>
            {(v as number).toLocaleString(undefined, { maximumFractionDigits: precision })}
          </span>
        </Tooltip>
      )
    }

  // 二级表头
  const origGroup = {
    title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>原始期限（金额）</span>,
    children: BUCKETS.map((b) => ({
      title: <span style={{ fontSize: 12, color: '#13c2c2' }}>{b.name}</span>,
      dataIndex: `orig_${b.key}`,
      width: b.width, align: 'right' as const,
      onHeaderCell: () => ({ style: { background: '#fafafa' } }),
      render: makeCell(`orig_${b.key}`, '#13c2c2', 2),
    })),
  }
  const remGroup = {
    title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>剩余期限（金额）</span>,
    children: BUCKETS.map((b) => ({
      title: <span style={{ fontSize: 12, color: '#722ed1' }}>{b.name}</span>,
      dataIndex: `rem_${b.key}`,
      width: b.width, align: 'right' as const,
      onHeaderCell: () => ({ style: { background: '#fafafa' } }),
      render: makeCell(`rem_${b.key}`, '#722ed1', 2),
    })),
  }
  const extraGroup = {
    title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>度量</span>,
    children: EXTRAS.map((m) => ({
      title: <span style={{ fontSize: 12, color: '#eb2f96' }}>{m.name}</span>,
      dataIndex: m.key,
      width: m.width, align: 'right' as const,
      onHeaderCell: () => ({ style: { background: '#fafafa' } }),
      render: (_v: any, r: any) => {
        const cell = matrix[String(r.coa_node_id)] || {}
        const v = cell[m.key]
        if (v === undefined || v === null) return <span style={{ color: '#ccc' }}>-</span>
        if (m.key === 'asf_rsf') {
          return (
            <Tooltip title="点击编辑 ASF/RSF">
              <span onClick={() => onEdit(r.coa_node_id)} style={{ cursor: 'pointer', color: '#eb2f96' }}>
                {v || '-'}
              </span>
            </Tooltip>
          )
        }
        const formatted = m.isPercent
          ? (v as number).toFixed(m.precision) + '%'
          : (v as number).toLocaleString(undefined, { maximumFractionDigits: m.precision })
        return (
          <Tooltip title={`点击编辑 ${m.name}`}>
            <span onClick={() => onEdit(r.coa_node_id)}
              style={{ cursor: 'pointer', color: '#eb2f96', fontFamily: m.isPercent ? 'monospace' : undefined }}>
              {formatted}
            </span>
          </Tooltip>
        )
      },
    })),
  }

  const actionCol: ColumnsType<any>[number] = {
    title: '操作', width: 80, fixed: 'right' as const,
    render: (_, r) => (
      <Button size="small" type="link" icon={<EditOutlined />}
        onClick={() => onEdit(r.coa_node_id)}>
        编辑
      </Button>
    ),
  }

  const allCols: ColumnsType<any> = [...baseCols, origGroup, remGroup, extraGroup, actionCol]

  // 大类汇总
  // 大类汇总行（动态从 categoriesAgg 的 key 生成）
  const categoryNameOrder = ['资产', '负债', '权益', '表外', '其他']
  const existingCategories = Object.keys(categoriesAgg).sort((a, b) => {
    const ia = categoryNameOrder.indexOf(a); const ib = categoryNameOrder.indexOf(b)
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib)
  })
  const categoryRows = existingCategories.map((cat) => ({
    category: cat,
    account_count: matrixNodes.filter((n) => {
      const code = n.node_code || ''
      if (cat === '资产') return code.startsWith('ZX_A') || n.path?.startsWith('/L1_资产')
      if (cat === '负债') return code.startsWith('ZX_L') || n.path?.startsWith('/L1_负债')
      if (cat === '权益') return code.startsWith('ZX_E')
      if (cat === '表外') return n.path?.startsWith('/L1_表外')
      return false
    }).length,
  }))
  const categoryBaseCols: ColumnsType<any> = [
    { title: '大类', dataIndex: 'category', width: 100, fixed: 'left' as const,
      render: (v) => {
        const color = v === '资产' ? 'blue' : v === '负债' ? 'orange' : v === '权益' ? 'gold' : v === '表外' ? 'purple' : 'default'
        return <Tag color={color} style={{ fontSize: 14 }}>{v}</Tag>
      },
    },
    { title: '账户册数', dataIndex: 'account_count', width: 100, fixed: 'left' as const },
  ]
  const categoryGroups: any[] = [
    { title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>原始期限（合计）</span>,
      children: BUCKETS.map((b) => ({
        title: <span style={{ fontSize: 12 }}>{b.name}</span>,
        width: b.width, align: 'right' as const,
        render: (_v: any, r: any) => {
          const cell = categoriesAgg[r.category] || {}
          const v = cell[`orig_${b.key}`]
          if (v === undefined) return <span style={{ color: '#ccc' }}>-</span>
          return <span>{(v as number).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
        },
      })),
    },
    { title: <span style={{ fontWeight: 600, color: '#1d39c4' }}>剩余期限（合计）</span>,
      children: BUCKETS.map((b) => ({
        title: <span style={{ fontSize: 12 }}>{b.name}</span>,
        width: b.width, align: 'right' as const,
        render: (_v: any, r: any) => {
          const cell = categoriesAgg[r.category] || {}
          const v = cell[`rem_${b.key}`]
          if (v === undefined) return <span style={{ color: '#ccc' }}>-</span>
          return <span>{(v as number).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
        },
      })),
    },
  ]
  const allCatCols: ColumnsType<any> = [...categoryBaseCols, ...categoryGroups]

  // 账户册树（antd DirectoryTree）
  const treeData = useMemo(() => {
    const byParent: Record<number, any[]> = {}
    matrixNodes.forEach((n) => {
      const key = n.parent_id || 0
      if (!byParent[key]) byParent[key] = []
      byParent[key].push(n)
    })
    Object.values(byParent).forEach((arr) =>
      arr.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)),
    )
    const convert = (parentId: number | null): any[] =>
      (byParent[parentId || 0] || []).map((n) => ({
        title: (
          <span>
            <Tag color={n.node_level === 1 ? 'blue' : n.node_level === 2 ? 'cyan' : 'geekblue'} style={{ marginRight: 4 }}>
              L{n.node_level}
            </Tag>
            <strong>{n.node_name}</strong>
            <span style={{ color: '#999', marginLeft: 4, fontSize: 12 }}>({n.node_code})</span>
          </span>
        ),
        key: String(n.coa_node_id),
        raw: n,
        children: n.node_level < 3 ? convert(n.coa_node_id) : undefined,
      }))
    return convert(null)
  }, [matrixNodes])

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>
          基础数据表（13+13 期限桶 · 余额/利率/风险权重）
          <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal', marginLeft: 8 }}>
            ——原始期限 + 剩余期限 × 1日/7日/1M/3M/6M/1Y/2Y/3Y/5Y/10Y/15Y/20Y/30Y
          </span>
        </span>
      </div>

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
            <span style={{ marginRight: 8 }}>数据日期：</span>
            <DatePicker
              value={dataDate}
              onChange={setDataDate}
              format="YYYY-MM-DD"
            />
            {availableDates.length > 0 && (
              <Select
                size="small"
                style={{ width: 130, marginLeft: 8 }}
                value={dataDate.format('YYYY-MM-DD')}
                onChange={setDataDate}
                options={availableDates.map((d) => ({ value: d, label: d }))}
                placeholder="已录入日期"
              />
            )}
          </Col>
          <Col>
            <span style={{ marginRight: 8 }}>日期偏移：</span>
            <InputNumber
              value={dateOffset}
              onChange={(v) => setDateOffset(Number(v) || 0)}
              min={0} max={365}
              style={{ width: 80 }}
            />
            <Select
              size="small"
              style={{ width: 80, marginLeft: 8 }}
              value={offsetUnit}
              onChange={setOffsetUnit}
              options={[
                { value: 'D', label: '日' },
                { value: 'W', label: '周' },
                { value: 'Y', label: '年' },
              ]}
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
              <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>新增记录</Button>
            </Space>
          </Col>
        </Row>
      </Card>

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
                  scroll={{ x: 60 + 200 + 50 + 26 * 70 + 80 + 7 * 80, y: 'calc(100vh - 380px)' }}
                  pagination={false}
                  bordered
                  locale={{ emptyText: <Empty description="该数据日期+偏移量下无账户册数据" /> }}
                />
              ),
            },
            {
              key: 'category',
              label: <span><FundProjectionScreenOutlined /> 大类汇总（资产/负债/权益/表外）</span>,
              children: (
                <Table
                  size="small"
                  rowKey="category"
                  dataSource={categoryRows}
                  columns={allCatCols as any}
                  scroll={{ x: 100 + 100 + 26 * 70, y: 'calc(100vh - 380px)' }}
                  pagination={false}
                  bordered
                />
              ),
            },
            {
              key: 'tree',
              label: <span><PartitionOutlined /> 账户册树</span>,
              children: (
                <div style={{ minHeight: 400, background: '#fff', border: '1px solid #f0f0f0', borderRadius: 4, padding: 8 }}>
                  {treeData.length === 0 ? <Empty /> : (
                    <DirectoryTree
                      treeData={treeData}
                      defaultExpandAll blockNode
                      onSelect={(keys, info) => {
                        const n = (info.node as any)?.raw
                        if (n?.node_level === 3) onEdit(n.coa_node_id)
                      }}
                    />
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? `编辑：${editing.node_code} · ${editing.node_name}` : '新增基础数据'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={onSave}
        width={880}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="coa_node_id" label="账户册节点" rules={[{ required: true }]}>
                <Select
                  showSearch optionFilterProp="label"
                  disabled={!!editing}
                  options={matrixNodes
                    .filter((n) => n.node_level === 3)
                    .map((n) => ({ value: n.coa_node_id, label: `${n.node_code} - ${n.node_name}` }))}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="data_date" label="数据日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="date_offset" label="偏移量">
                <InputNumber min={0} max={365} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="offset_unit" label="单位">
                <Select options={[
                  { value: 'D', label: '日' },
                  { value: 'W', label: '周' },
                  { value: 'Y', label: '年' },
                ]} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" style={{ fontSize: 13 }}>原始期限金额（13 个期限桶）</Divider>
          <Row gutter={[8, 8]}>
            {BUCKETS.map((b, i) => (
              <Col span={3} key={`orig-${b.key}`}>
                <Form.Item name={['orig', i]} label={b.name} style={{ marginBottom: 8 }}>
                  <InputNumber step={1000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            ))}
          </Row>

          <Divider orientation="left" style={{ fontSize: 13 }}>剩余期限金额（13 个期限桶）</Divider>
          <Row gutter={[8, 8]}>
            {BUCKETS.map((b, i) => (
              <Col span={3} key={`rem-${b.key}`}>
                <Form.Item name={['rem', i]} label={b.name} style={{ marginBottom: 8 }}>
                  <InputNumber step={1000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            ))}
          </Row>

          <Divider orientation="left" style={{ fontSize: 13 }}>流动性 + 余额/利率</Divider>
          <Row gutter={16}>
            <Col span={6}><Form.Item name="asf_rsf" label="ASF/RSF"><Input /></Form.Item></Col>
            <Col span={6}><Form.Item name="hqla_factor" label="HQLA折算系数（%）"><InputNumber step={0.01} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={6}><Form.Item name="current_balance" label="当前余额"><InputNumber step={1000} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={6}><Form.Item name="avg_balance" label="平均余额"><InputNumber step={1000} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}><Form.Item name="weighted_rate" label="加权平均利率（%）"><InputNumber step={0.0001} precision={4} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={6}><Form.Item name="interest_amount" label="平均利息收支"><InputNumber step={1000} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={6}><Form.Item name="risk_weight" label="风险权重（%）"><InputNumber step={0.0001} precision={4} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={6}><Form.Item name="calc_note" label="备注"><Input.TextArea rows={1} /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>
    </Spin>
  )
}

export default BasicDataSheet
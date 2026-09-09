import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Tabs, Tree, Form, Input, InputNumber, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, DatePicker, Popconfirm, Row, Col, Statistic,
  Tooltip, Divider, Badge,
} from 'antd'
import {
  DeleteOutlined, ReloadOutlined, PlusOutlined, EditOutlined,
  FundProjectionScreenOutlined, BankOutlined, RiseOutlined, FallOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { balanceApi, coaApi } from '../api'

const { DirectoryTree } = Tree

const BalanceSheet: React.FC = () => {
  const [schemes, setSchemes] = useState<any[]>([])
  const [activeScheme, setActiveScheme] = useState<number | null>(null)
  const [treeData, setTreeData] = useState<any[]>([])
  const [records, setRecords] = useState<any[]>([])
  const [dates, setDates] = useState<any[]>([])
  const [categoryRows, setCategoryRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [dataDate, setDataDate] = useState<Dayjs>(dayjs('2026-08-31'))
  const [form] = Form.useForm()

  // 加载方案
  const loadSchemes = async () => {
    const r = await coaApi.listSchemes()
    setSchemes(r.items || [])
    if (!activeScheme && r.items?.length) {
      // 默认选 COA_V6
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

  // 加载当月所有数据 + 大类汇总
  const loadRecords = async () => {
    if (!activeScheme || !dataDate) return
    setLoading(true)
    try {
      const [r1, r2] = await Promise.all([
        balanceApi.byScheme(activeScheme, dataDate.format('YYYY-MM-DD')),
        balanceApi.categorySummary(dataDate.format('YYYY-MM-DD'), activeScheme),
      ])
      setRecords(r1.items || [])
      setCategoryRows(r2.items || [])
    } finally { setLoading(false) }
  }
  // 加载历史月份
  const loadDates = async () => {
    if (!activeScheme) return
    const r = await balanceApi.listDates(activeScheme)
    setDates(r.items || [])
  }
  useEffect(() => {
    if (activeScheme) { loadRecords(); loadDates() }
  }, [activeScheme, dataDate])

  // 新增
  const onCreate = (preselectNodeId?: number) => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      coa_node_id: preselectNodeId,
      data_date: dataDate,
      current_amount: 0,
      begin_balance: 0,
      avg_balance: 0,
      interest_rate: 0,
      interest_amount: 0,
      capital_ratio: 0,
      risk_weight: 0,
      gaps: Array(24).fill(0),
    })
    setModalOpen(true)
  }
  const onEdit = (r: any) => {
    setEditing(r)
    form.setFieldsValue({
      coa_node_id: r.coa_node_id,
      data_date: dayjs(r.data_date),
      current_amount: r.current_amount,
      begin_balance: r.begin_balance,
      avg_balance: r.avg_balance,
      interest_rate: r.interest_rate,
      interest_amount: r.interest_amount,
      capital_ratio: r.capital_ratio,
      risk_weight: r.risk_weight,
      gaps: r.gaps,
      calc_note: r.calc_note,
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
      message.success(editing ? '已更新' : '已创建')
      setModalOpen(false)
      loadRecords()
    } catch (e: any) { message.error(e?.response?.data?.detail || '保存失败') }
  }

  // KPI 汇总（基于 records）
  const kpi = useMemo(() => {
    const totalAmt = records.reduce((s, r) => s + (r.current_amount || 0), 0)
    const totalInterest = records.reduce((s, r) => s + (r.interest_amount || 0), 0)
    const totalGap24 = records.reduce((s, r) => s + (r.sum_24m || 0), 0)
    const totalAvg = records.reduce((s, r) => s + (r.avg_balance || 0), 0)
    const weightedRate = totalAvg > 0
      ? records.reduce((s, r) => s + (r.interest_rate || 0) * (r.avg_balance || 0), 0) / totalAvg : 0
    return {
      accountCount: records.length,
      totalAmt, totalInterest, totalGap24, weightedRate,
    }
  }, [records])

  // 渲染 tree 节点 title
  const renderTreeTitle = (node: any) => {
    const color = node.level === 1 ? '#1d39c4'
                : node.level === 2 ? '#096dd9'
                : '#595959'
    return (
      <span style={{ color }}>
        {node.name || node.code}
        <span style={{ color: '#999', marginLeft: 4, fontSize: 12 }}>({node.code})</span>
      </span>
    )
  }
  // 转换数据为 antd Tree 格式
  const convertTree = (nodes: any[]): any[] =>
    nodes.map((n) => ({
      title: renderTreeTitle(n),
      key: String(n.id),
      raw: n,
      children: n.children?.length ? convertTree(n.children) : undefined,
    }))

  // 账户册列表（level=3）展示用
  const accountList = useMemo(() =>
    records.filter((r) => r.node_level === 3).sort((a, b) =>
      (a.path || '').localeCompare(b.path || '')), [records])

  const accountCols: ColumnsType<any> = [
    { title: '账户册编码', dataIndex: 'node_code', width: 100,
      render: (c, r) => <code style={{ color: r.node_type === 'ACCOUNT' ? '#1d39c4' : '#999' }}>{c}</code> },
    { title: '账户册名称', dataIndex: 'node_name', ellipsis: true },
    { title: '类别', dataIndex: 'node_type', width: 90,
      render: (t) => <Tag color={t === 'CATEGORY' ? 'blue' : t === 'GROUP' ? 'cyan' : 'default'}>{t}</Tag> },
    { title: '期初余额', dataIndex: 'begin_balance', width: 130,
      render: (v) => (v || 0).toLocaleString() },
    { title: '期末余额', dataIndex: 'current_amount', width: 140,
      render: (v) => <strong style={{ color: '#1d39c4' }}>{(v || 0).toLocaleString()}</strong> },
    { title: '平均余额', dataIndex: 'avg_balance', width: 130,
      render: (v) => (v || 0).toLocaleString() },
    { title: '利率(%)', dataIndex: 'interest_rate', width: 100,
      render: (v) => v ? <span style={{ color: '#fa8c16' }}>{v.toFixed(4)}</span> : '—' },
    { title: '利息', dataIndex: 'interest_amount', width: 130,
      render: (v) => <span style={{ color: v >= 0 ? '#cf1322' : '#3f8600' }}>{(v || 0).toLocaleString()}</span> },
    { title: '资本占比(%)', dataIndex: 'capital_ratio', width: 110,
      render: (v) => v ? v.toFixed(4) : '—' },
    { title: '风险权重(%)', dataIndex: 'risk_weight', width: 110,
      render: (v) => v ? v.toFixed(4) : '—' },
    { title: '24月缺口合计', dataIndex: 'sum_24m', width: 130,
      render: (v) => {
        const s = v || 0
        return <Tag color={s > 0 ? 'red' : s < 0 ? 'green' : 'default'}>{s.toLocaleString()}</Tag>
      },
    },
    {
      title: '操作', width: 110, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Tooltip title="编辑该账户册当月数据">
            <Button size="small" icon={<EditOutlined />} onClick={() => onEdit(r)}>编辑</Button>
          </Tooltip>
          {r.id && (
            <Popconfirm title="确认删除？" onConfirm={async () => {
              await balanceApi.delete(r.id)
              message.success('已删除')
              loadRecords()
            }}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  // 大类汇总表
  const categoryCols: ColumnsType<any> = [
    { title: '大类', dataIndex: 'category', width: 100,
      render: (v) => <Tag color={v === '资产' ? 'blue' : v === '负债' ? 'orange' : 'purple'} style={{ fontSize: 14 }}>{v}</Tag> },
    { title: '账户册数', dataIndex: 'account_count', width: 100 },
    { title: '期初余额', dataIndex: 'total_begin', width: 150,
      render: (v) => (v || 0).toLocaleString() },
    { title: '期末余额', dataIndex: 'total_amount', width: 160,
      render: (v) => <strong style={{ color: '#1d39c4', fontSize: 16 }}>{(v || 0).toLocaleString()}</strong> },
    { title: '平均余额', dataIndex: 'total_avg', width: 150,
      render: (v) => (v || 0).toLocaleString() },
    { title: '利息合计', dataIndex: 'total_interest', width: 150,
      render: (v) => <span style={{ color: v >= 0 ? '#cf1322' : '#3f8600' }}>{(v || 0).toLocaleString()}</span> },
    { title: '加权利率(%)', dataIndex: 'weighted_rate', width: 130,
      render: (v) => v ? <span style={{ color: '#fa8c16' }}>{v.toFixed(4)}</span> : '—' },
    { title: '加权资本占比(%)', dataIndex: 'weighted_capital', width: 150,
      render: (v) => v ? v.toFixed(4) : '—' },
    { title: '加权风险权重(%)', dataIndex: 'weighted_risk_weight', width: 150,
      render: (v) => v ? v.toFixed(4) : '—' },
    { title: '24月缺口合计', dataIndex: 'sum_24m', width: 150,
      render: (v) => {
        const s = v || 0
        return <Tag color={s > 0 ? 'red' : s < 0 ? 'green' : 'default'}>{s.toLocaleString()}</Tag>
      },
    },
  ]

  // 历史月份表
  const dateCols: ColumnsType<any> = [
    { title: '数据日期', dataIndex: 'data_date', width: 140,
      render: (v) => <a onClick={() => setDataDate(dayjs(v))}>{v}</a> },
    { title: '记录数', dataIndex: 'record_count', width: 100 },
    { title: '总余额', dataIndex: 'total_amount', width: 180,
      render: (v) => <strong style={{ color: '#1d39c4' }}>{(v || 0).toLocaleString()}</strong> },
    { title: '总利息', dataIndex: 'total_interest', width: 180,
      render: (v) => <span style={{ color: '#cf1322' }}>{(v || 0).toLocaleString()}</span> },
  ]

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>资产负债表 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>· 账户册月度量纲 + 24 月现金流缺口</span></span>
      </div>

      {/* 顶部筛选 */}
      <Card bordered={false} style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <span style={{ marginRight: 8 }}>账户册方案：</span>
            <Select
              style={{ width: 260 }}
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
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => { loadRecords(); loadDates() }}>刷新</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => onCreate()}>新增账户册月度数据</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* KPI 看板 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="账户册记录数"
              value={kpi.accountCount}
              prefix={<BankOutlined />}
              suffix="册"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="期末总余额（亿元）"
              value={kpi.totalAmt}
              precision={2}
              prefix={<FundProjectionScreenOutlined />}
              valueStyle={{ color: '#1d39c4' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="本月总利息（亿元）"
              value={kpi.totalInterest}
              precision={2}
              prefix={kpi.totalInterest >= 0 ? <RiseOutlined /> : <FallOutlined />}
              valueStyle={{ color: kpi.totalInterest >= 0 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="24 月缺口合计（亿元）"
              value={kpi.totalGap24}
              precision={2}
              valueStyle={{ color: kpi.totalGap24 > 0 ? '#cf1322' : kpi.totalGap24 < 0 ? '#3f8600' : '#666' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 主内容 */}
      <Card bordered={false} bodyStyle={{ paddingTop: 8 }}>
        <Tabs
          defaultActiveKey="accounts"
          items={[
            {
              key: 'accounts',
              label: <span><BankOutlined /> 账户册月度数据 <Badge count={accountList.length} showZero color="#1d39c4" /></span>,
              children: (
                <div style={{ display: 'flex', gap: 16, minHeight: 600 }}>
                  {/* 左侧账户册树 */}
                  <div style={{ width: 320, borderRight: '1px solid #f0f0f0', paddingRight: 12 }}>
                    <div style={{ marginBottom: 8, fontWeight: 600 }}>
                      <span>账户册树</span>
                      <Tooltip title="点击账户册节点 → 自动定位到该行并预填新建表单">
                        <Tag color="blue" style={{ marginLeft: 8 }}>? 提示</Tag>
                      </Tooltip>
                    </div>
                    {treeData.length === 0 ? (
                      <Empty description="暂无账户册数据" />
                    ) : (
                      <DirectoryTree
                        treeData={convertTree(treeData)}
                        defaultExpandAll
                        blockNode
                        onSelect={(keys, info) => {
                          const node = (info.node as any).raw
                          if (node?.level === 3) {
                            const exists = accountList.find((r) => r.coa_node_id === node.id)
                            if (exists) {
                              onEdit(exists)
                            } else {
                              Modal.confirm({
                                title: `为「${node.name}(${node.code})」创建 ${dataDate.format('YYYY-MM-DD')} 的月度数据？`,
                                onOk: () => onCreate(node.id),
                              })
                            }
                          }
                        }}
                      />
                    )}
                  </div>

                  {/* 右侧账户册列表 + 缺口 */}
                  <div style={{ flex: 1, overflow: 'auto' }}>
                    <Table
                      size="small"
                      rowKey="coa_node_id"
                      dataSource={accountList}
                      columns={accountCols}
                      scroll={{ x: 1500 }}
                      pagination={{ pageSize: 15, showSizeChanger: true, showTotal: (t) => `共 ${t} 册` }}
                      locale={{ emptyText: <Empty description="当月暂无账户册月度数据，点击右上角'新增账户册月度数据'开始" /> }}
                      summary={() => {
                        const total = accountList.reduce((s, r) => ({
                          amt: s.amt + (r.current_amount || 0),
                          avg: s.avg + (r.avg_balance || 0),
                          int: s.int + (r.interest_amount || 0),
                          gap: s.gap + (r.sum_24m || 0),
                        }), { amt: 0, avg: 0, int: 0, gap: 0 })
                        return (
                          <Table.Summary.Row style={{ background: '#fafafa', fontWeight: 600 }}>
                            <Table.Summary.Cell index={0} colSpan={4}>合计 / 加权</Table.Summary.Cell>
                            <Table.Summary.Cell index={1}>{total.amt.toLocaleString()}</Table.Summary.Cell>
                            <Table.Summary.Cell index={2}>{total.avg.toLocaleString()}</Table.Summary.Cell>
                            <Table.Summary.Cell index={3}>—</Table.Summary.Cell>
                            <Table.Summary.Cell index={4}>
                              <span style={{ color: total.int >= 0 ? '#cf1322' : '#3f8600' }}>{total.int.toLocaleString()}</span>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={5} colSpan={2}>—</Table.Summary.Cell>
                            <Table.Summary.Cell index={6}>
                              <Tag color={total.gap > 0 ? 'red' : total.gap < 0 ? 'green' : 'default'}>
                                {total.gap.toLocaleString()}
                              </Tag>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={7}>—</Table.Summary.Cell>
                          </Table.Summary.Row>
                        )
                      }}
                    />
                  </div>
                </div>
              ),
            },
            {
              key: 'category',
              label: <span><FundProjectionScreenOutlined /> 大类汇总（资产/负债/表外）</span>,
              children: (
                <Table
                  size="middle"
                  rowKey="category"
                  dataSource={categoryRows}
                  columns={categoryCols}
                  pagination={false}
                  locale={{ emptyText: <Empty description="当月暂无账户册数据，无法生成大类汇总" /> }}
                />
              ),
            },
            {
              key: 'history',
              label: <span><RiseOutlined /> 历史月份 <Badge count={dates.length} showZero color="#52c41a" /></span>,
              children: (
                <Table
                  size="middle"
                  rowKey="data_date"
                  dataSource={dates}
                  columns={dateCols}
                  pagination={false}
                  onRow={(r) => ({ onClick: () => setDataDate(dayjs(r.data_date)) })}
                  locale={{ emptyText: <Empty description="暂无历史数据" /> }}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* 编辑/新增弹窗 */}
      <Modal
        title={editing ? `编辑账户册月度数据 - ${editing.node_code}` : '新增账户册月度数据'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={onSave}
        width={920}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="coa_node_id" label="账户册节点" rules={[{ required: true }]}>
                <Select
                  showSearch optionFilterProp="label"
                  placeholder="选择账户册（仅 L3 节点）"
                  options={(() => {
                    // 扁平化 treeData
                    const flat: any[] = []
                    const walk = (ns: any[]) => ns.forEach((n) => {
                      flat.push({ value: n.id, label: `${n.code} - ${n.name || ''}` })
                      if (n.children) walk(n.children)
                    })
                    walk(treeData)
                    return flat
                  })()}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="data_date" label="数据日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" style={{ fontSize: 13 }}>账户册 7 个度量</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="current_amount" label="期末余额">
                <InputNumber style={{ width: '100%' }} step={1000} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="begin_balance" label="期初余额">
                <InputNumber style={{ width: '100%' }} step={1000} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="avg_balance" label="平均余额">
                <InputNumber style={{ width: '100%' }} step={1000} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="interest_rate" label="加权平均利率（%）">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={4} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="interest_amount" label="本期利息">
                <InputNumber style={{ width: '100%' }} step={1000} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="capital_ratio" label="资本占用比例（%）">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={4} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="risk_weight" label="风险权重（%）">
                <InputNumber style={{ width: '100%' }} step={0.0001} precision={4} />
              </Form.Item>
            </Col>
            <Col span={16}>
              <Form.Item name="calc_note" label="计算备注">
                <Input.TextArea rows={2} placeholder="如：本月新发放贷款 50 亿，月末冲销 30 亿" />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" style={{ fontSize: 13 }}>未来 24 月现金流缺口（M1 ~ M24）</Divider>
          <Row gutter={[6, 6]}>
            {Array.from({ length: 24 }, (_, i) => (
              <Col span={3} key={i}>
                <Form.Item name={['gaps', i]} noStyle>
                  <InputNumber
                    placeholder={`M${i + 1}`}
                    size="small"
                    style={{ width: '100%' }}
                    formatter={(v) => v ? `${v}` : ''}
                  />
                </Form.Item>
              </Col>
            ))}
          </Row>
          <div style={{ marginTop: 6, color: '#999', fontSize: 12 }}>
            <span>说明：</span>
            <span style={{ marginLeft: 8 }}>正数 = 资金净流出缺口</span>
            <span style={{ marginLeft: 12 }}>负数 = 资金净流入剩余</span>
          </div>
        </Form>
      </Modal>
    </Spin>
  )
}

export default BalanceSheet

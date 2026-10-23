import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Form, Input, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, Statistic, Alert, InputNumber, Divider, Tooltip,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  CheckCircleOutlined, ThunderboltOutlined, FunctionOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { kpiApi } from '../api'

interface Props {
  activeScheme: number | null
  currentScheme: any
}

const KpiScore: React.FC<Props> = ({ activeScheme, currentScheme }) => {
  const [defs, setDefs] = useState<any[]>([])
  const [selectedKpi, setSelectedKpi] = useState<number | null>(null)
  const [rules, setRules] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')

  // 规则编辑
  const [ruleModal, setRuleModal] = useState(false)
  const [editingRule, setEditingRule] = useState<any>(null)
  const [ruleForm] = Form.useForm()
  const [segments, setSegments] = useState<any[]>([])

  // 计算器已迁到"指标维护"页 - 本页只负责规则编辑
  // 加载当前方案的指标定义
  const loadDefs = async () => {
    if (!activeScheme) { setDefs([]); return }
    setLoading(true)
    try {
      const r = await kpiApi.listDefs({ scheme_id: activeScheme })
      setDefs(r.items || [])
    } finally { setLoading(false) }
  }

  // 加载评分规则
  const loadRules = async () => {
    if (!selectedKpi) { setRules([]); return }
    setLoading(true)
    try {
      const r = await kpiApi.listScoreRules({ kpi_id: selectedKpi })
      setRules(r.items || [])
    } finally { setLoading(false) }
  }

  useEffect(() => { loadDefs() }, [activeScheme])
  useEffect(() => { if (selectedKpi) loadRules() }, [selectedKpi])

  // 过滤后的指标列表
  const filteredDefs = useMemo(() => {
    if (!keyword) return defs
    const kw = keyword.toLowerCase()
    return defs.filter((d) =>
      (d.kpi_code || '').toLowerCase().includes(kw) ||
      (d.kpi_name || '').toLowerCase().includes(kw)
    )
  }, [defs, keyword])

  const selectedDef = defs.find((d) => d.id === selectedKpi)

  // ========= 规则 CRUD =========
  const onCreateRule = () => {
    if (!selectedKpi) {
      message.warning('请先在左侧选择一个指标')
      return
    }
    setEditingRule(null)
    ruleForm.resetFields()
    ruleForm.setFieldsValue({
      scheme_id: activeScheme,
      kpi_id: selectedKpi,
      rule_name: '',
      calc_method: 'PIECEWISE',
      total_score: 100,
      higher_is_better: 1,
      status: 'ACTIVE',
    })
    // 默认三段示例（阶梯评分：只填最大值分数）
    setSegments([
      { seg_order: 1, min_value: null, max_value: 60, score: 60, score_min: null, segment_desc: '不及格' },
      { seg_order: 2, min_value: 60, max_value: 80, score: 80, score_min: null, segment_desc: '及格' },
      { seg_order: 3, min_value: 80, max_value: null, score: 100, score_min: null, segment_desc: '优秀' },
    ])
    setRuleModal(true)
  }

  const onCreateLinearRule = () => {
    if (!selectedKpi) {
      message.warning('请先在左侧选择一个指标')
      return
    }
    setEditingRule(null)
    ruleForm.resetFields()
    ruleForm.setFieldsValue({
      scheme_id: activeScheme,
      kpi_id: selectedKpi,
      rule_name: '',
      calc_method: 'LINEAR',
      total_score: 100,
      higher_is_better: 1,
      status: 'ACTIVE',
    })
    // 默认两个锚点示例（端点 → 端点中间值线性插值）
    setSegments([
      { seg_order: 1, min_value: 8,  max_value: null, score: 60,  segment_desc: '下端锚点：监管底线 8% → 60 分' },
      { seg_order: 2, min_value: 15, max_value: null, score: 100, segment_desc: '上端锚点：行业优秀 15% → 100 分' },
    ])
    setRuleModal(true)
  }

  const onEditRule = (r: any) => {
    setEditingRule(r)
    ruleForm.setFieldsValue({
      scheme_id: r.scheme_id,
      kpi_id: r.kpi_id,
      rule_name: r.rule_name,
      calc_method: r.calc_method,
      total_score: r.total_score,
      higher_is_better: r.higher_is_better,
      description: r.description,
      status: r.status,
    })
    setSegments(r.segments && r.segments.length ? r.segments : [])
    setRuleModal(true)
  }

  const onSaveRule = async () => {
    try {
      const v = await ruleForm.validateFields()
      v.segments = segments
      if (editingRule) await kpiApi.updateScoreRule(editingRule.id, v)
      else await kpiApi.createScoreRule(v)
      message.success('已保存')
      setRuleModal(false)
      loadRules()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    }
  }

  const onDeleteRule = async (rid: number) => {
    try {
      await kpiApi.deleteScoreRule(rid)
      message.success('已删除')
      loadRules()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败')
    }
  }

  // 段编辑
  const addSegment = () => {
    setSegments([
      ...segments,
      {
        seg_order: segments.length + 1,
        min_value: null,
        max_value: null,
        score: 0,
        score_min: null,
        segment_desc: '',
      },
    ])
  }
  const updateSegment = (idx: number, field: string, val: any) => {
    const next = [...segments]
    next[idx] = { ...next[idx], [field]: val }
    setSegments(next)
  }
  const removeSegment = (idx: number) => {
    setSegments(segments.filter((_, i) => i !== idx))
  }

  // 计算器已迁到"指标维护"页 - 本页只负责规则编辑

  // ========= 列定义 =========
  const defCols: ColumnsType<any> = [
    { title: '编码', dataIndex: 'kpi_code', width: 130, render: (c) => <code>{c}</code> },
    { title: '名称', dataIndex: 'kpi_name', ellipsis: true },
    { title: '所属报表', dataIndex: 'report_name', width: 120, ellipsis: true },
  ]

  const ruleCols: ColumnsType<any> = [
    { title: '规则名称', dataIndex: 'rule_name', width: 200, render: (n) => <strong>{n}</strong> },
    {
      title: '算法', dataIndex: 'calc_method', width: 90,
      render: (m) => (
        <Tag color={m === 'LINEAR' ? 'geekblue' : 'purple'}>
          {m === 'LINEAR' ? '📈 线性' : '🔢 分段'}
        </Tag>
      ),
    },
    {
      title: '总分', dataIndex: 'total_score', width: 80,
      render: (s) => <Tag color="blue">{s}</Tag>,
    },
    {
      title: '方向', dataIndex: 'higher_is_better', width: 100,
      render: (v) => <Tag color={v ? 'green' : 'orange'}>{v ? '↑ 正向' : '↓ 逆向'}</Tag>,
    },
    {
      title: '段数', key: 'seg_count', width: 80,
      render: (_, r) => {
        const isLinear = r.calc_method === 'LINEAR'
        return <Tag color={isLinear ? 'geekblue' : 'default'}>{isLinear ? '⚓ ' : ''}{r.segments?.length || 0}{isLinear ? ' 锚点' : ' 段'}</Tag>
      },
    },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (s) => <Tag color={s === 'ACTIVE' ? 'green' : 'default'}>{s}</Tag>,
    },
    {
      title: '操作', width: 180, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditRule(r)}>编辑</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => {
            Modal.confirm({
              title: '确认删除？',
              content: `将删除规则【${r.rule_name}】及其所有评分段`,
              okText: '删除',
              okType: 'danger',
              onOk: () => onDeleteRule(r.id),
            })
          }}>删除</Button>
        </Space>
      ),
    },
  ]

  // 未选方案
  if (!activeScheme) {
    return (
      <Empty
        style={{ padding: 80 }}
        description="请先在上方选择【指标方案】"
      />
    )
  }

  return (
    <Spin spinning={loading}>
      <Row gutter={16}>
        {/* 左栏：指标列表 */}
        <Col span={8}>
          <Card
            title={<span><FunctionOutlined /> 方案指标</span>}
            extra={<Tag color="purple">{defs.length} 个</Tag>}
            bodyStyle={{ padding: 8 }}
            style={{ height: 'calc(100vh - 320px)', minHeight: 480 }}
          >
            <Input.Search
              placeholder="搜索编码 / 名称"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              style={{ marginBottom: 8 }}
              allowClear
            />
            {filteredDefs.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={defs.length === 0 ? '当前方案还没有指标定义' : '无匹配结果'}
              />
            ) : (
              <div style={{ overflowY: 'auto', height: 'calc(100% - 60px)' }}>
                {filteredDefs.map((d) => (
                  <div
                    key={d.id}
                    onClick={() => setSelectedKpi(d.id)}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 6,
                      cursor: 'pointer',
                      marginBottom: 6,
                      background: selectedKpi === d.id ? '#e6f4ff' : '#fafafa',
                      border: selectedKpi === d.id ? '1px solid #91caff' : '1px solid #f0f0f0',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <code style={{ fontSize: 12, color: '#666' }}>{d.kpi_code}</code>
                      {selectedKpi === d.id && <CheckCircleOutlined style={{ color: '#1890ff' }} />}
                    </div>
                    <div style={{ fontWeight: 500, marginTop: 2 }}>{d.kpi_name}</div>
                    <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>
                      {d.report_name || '未关联报表'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </Col>

        {/* 右栏：评分规则 */}
        <Col span={16}>
          {!selectedDef ? (
            <Card style={{ height: 'calc(100vh - 320px)', minHeight: 480 }}>
              <Empty
                style={{ paddingTop: 120 }}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <div>
                    <div style={{ marginBottom: 8 }}>请在左侧选择一个指标</div>
                    <div style={{ color: '#999', fontSize: 12 }}>
                      将展示该指标的评分规则配置
                    </div>
                  </div>
                }
              />
            </Card>
          ) : (
            <Card
              title={
                <Space>
                  <span><ThunderboltOutlined /> {selectedDef.kpi_code} · {selectedDef.kpi_name}</span>
                  <Tag color="purple">{currentScheme?.scheme_code}</Tag>
                </Space>
              }
              extra={
                <Space>
                  <Button icon={<ReloadOutlined />} onClick={loadRules}>刷新</Button>
                  <Tooltip title="新增分段评分规则（按 min/max 区间 → 分数）">
                    <Button type="primary" icon={<PlusOutlined />} onClick={onCreateRule}>新增分段规则</Button>
                  </Tooltip>
                  <Tooltip title="新增线性插值评分规则（多个 (x, score) 锚点，按段间线性插值）">
                    <Button type="default" icon={<PlusOutlined />} onClick={onCreateLinearRule}
                      style={{ background: '#e6f4ff', borderColor: '#91caff', color: '#1677ff' }}>
                      新增线性规则
                    </Button>
                  </Tooltip>
                </Space>
              }
              bodyStyle={{ padding: 16 }}
            >
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
                message="试算功能已迁移到【指标维护】页"
                description={
                  <div>
                    在【指标维护】页选择数据日期后，列表会展示对应日期的指标值和分数。
                    点击行内的【⚡ 试算】按钮或顶部【一键试算全部】即可批量计算分数并保存到本指标。
                    <div style={{ marginTop: 6, color: '#666' }}>
                      <b>📈 线性评分</b>：每个评分段是一个<b>锚点</b>（min_value = 输入值，score = 该点的得分），
                      锚点之间按 x 轴线性插值；锚点外的输入值按端点 clamp。
                      <b style={{ marginLeft: 12 }}>🔢 分段评分</b>：每个评分段是 [最小值, 最大值) 区间。
                      <b style={{ color: '#fa8c16', marginLeft: 6 }}>最小值分数</b>与<b style={{ color: '#165dff' }}>最大值分数</b>
                      都填写时<b>段内按线性插值</b>（如 [0,10] → 60~100 分，输入 5 得 80 分）；
                      只填最大值分数则为<b>阶梯评分</b>（命中即取该分）。
                    </div>
                  </div>
                }
              />

              {/* 规则列表 */}
              <Table
                size="small"
                rowKey="id"
                dataSource={rules}
                columns={ruleCols}
                scroll={{ x: 900 }}
                pagination={{ pageSize: 10 }}
                expandable={{
                  expandedRowRender: (r) => (
                    <div style={{ padding: '8px 12px', background: '#fafafa', borderRadius: 4 }}>
                      <div style={{ marginBottom: 8, color: '#666' }}>
                        {r.calc_method === 'LINEAR' ? '⚓' : '📊'} {r.calc_method === 'LINEAR' ? '锚点（线性插值）' : '评分段（区间命中）'}（{r.segments?.length || 0} {r.calc_method === 'LINEAR' ? '锚点' : '段'}）：
                      </div>
                      <Space wrap size={[6, 6]}>
                        {(r.segments || []).map((s: any) => (
                          <Tag key={s.id} color={r.calc_method === 'LINEAR' ? 'geekblue' : 'blue'} style={{ padding: '4px 10px' }}>
                            {r.calc_method === 'LINEAR' ? (
                              <>
                                x=<strong>{s.min_value ?? s.max_value}</strong>
                                {' → '}
                                <strong style={{ color: '#1677ff' }}>{s.score} 分</strong>
                                {s.segment_desc && ` · ${s.segment_desc}`}
                              </>
                            ) : (
                              <>
                                {s.min_value !== null ? `≥${s.min_value}` : '-∞'} ~
                                {s.max_value !== null ? ` <${s.max_value}` : ' +∞'}
                                {' → '}
                                {s.score_min != null ? (
                                  <>
                                    <strong style={{ color: '#fa8c16' }}>{s.score_min}</strong>
                                    {' ~ '}
                                    <strong style={{ color: '#1890ff' }}>{s.score}</strong>
                                    {' 分'}
                                    <Tag color="orange" style={{ marginLeft: 6, fontSize: 11 }}>插值</Tag>
                                  </>
                                ) : (
                                  <strong style={{ color: '#1890ff' }}>{s.score} 分</strong>
                                )}
                                {s.segment_desc && ` · ${s.segment_desc}`}
                              </>
                            )}
                          </Tag>
                        ))}
                      </Space>
                      {r.description && (
                        <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                          说明：{r.description}
                        </div>
                      )}
                    </div>
                  ),
                }}
                locale={{
                  emptyText: (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description={
                        <div>
                          <div>该指标还没有评分规则</div>
                          <Button type="primary" icon={<PlusOutlined />} onClick={onCreateRule} style={{ marginTop: 12 }}>
                            立即新增评分规则
                          </Button>
                        </div>
                      }
                    />
                  ),
                }}
              />
            </Card>
          )}
        </Col>
      </Row>

      {/* 规则编辑 Modal */}
      <Modal
        title={editingRule ? '编辑评分规则' : '新增评分规则'}
        open={ruleModal}
        onCancel={() => setRuleModal(false)}
        onOk={onSaveRule}
        width={1000}
        okText="保存"
      >
        <Form form={ruleForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="scheme_id" label="所属方案" rules={[{ required: true }]}>
                <Select disabled options={currentScheme ? [{ value: currentScheme.id, label: currentScheme.scheme_code }] : []} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="kpi_id" label="所属指标" rules={[{ required: true }]}>
                <Select
                  disabled={!!editingRule}
                  options={selectedDef ? [{ value: selectedDef.id, label: `${selectedDef.kpi_code} · ${selectedDef.kpi_name}` }] : []}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={10}>
              <Form.Item name="rule_name" label="规则名称" rules={[{ required: true }]}>
                <Input placeholder="如：净息差三档评分" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="calc_method" label="计算方法">
                <Select options={[
                  { value: 'PIECEWISE', label: '分段' },
                  { value: 'LINEAR', label: '线性' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="total_score" label="总分">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="higher_is_better" label="方向">
                <Select options={[
                  { value: 1, label: '↑ 正向' },
                  { value: 0, label: '↓ 逆向' },
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="规则说明">
            <Input.TextArea rows={2} placeholder="如：净息差 ≥ 2% 得 100 分；1.5-2% 得 80 分；<1.5% 得 60 分" />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="ACTIVE">
            <Select options={[{ value: 'ACTIVE', label: 'ACTIVE' }, { value: 'INACTIVE', label: 'INACTIVE' }]} />
          </Form.Item>

          <Divider orientation="left" plain>
            {(() => {
              const m = ruleForm.getFieldValue('calc_method') || 'PIECEWISE'
              return m === 'LINEAR' ? '⚓ 线性锚点（min_value=输入值, score=该点的分数）' : '📊 评分段（按指标值区间 → 分数）'
            })()}
          </Divider>

          <div style={{ marginBottom: 8 }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <span style={{ color: '#666', fontSize: 12 }}>
                {(() => {
                  const m = ruleForm.getFieldValue('calc_method') || 'PIECEWISE'
                  if (m === 'LINEAR') {
                    return <>💡 提示：每行是一个<b>锚点</b>。<strong>min_value</strong> = 指标值，<strong>score</strong> = 该锚点的得分。锚点之间按 x 轴线性插值；输入值超出区间则按端点 clamp（取最近锚点分数）。</>
                  }
                  return <>💡 提示：每段是一个区间 <strong>[最小值, 最大值)</strong>。
                    <strong>最小值分数</strong>填该段下界的得分，<strong>最大值分数</strong>填该段上界的得分——
                    <strong>两端都填</strong>时段内按线性插值（如 [0,10] → 60→100 分，输入 5 得 80 分）；
                    <strong>只填最大值分数</strong>则为阶梯评分（命中即取该分）。两端区间边界可留空表示 -∞ / +∞。</>
                })()}
              </span>
              <Button size="small" icon={<PlusOutlined />} onClick={addSegment}>
                {(() => {
                  const m = ruleForm.getFieldValue('calc_method') || 'PIECEWISE'
                  return m === 'LINEAR' ? '添加锚点' : '添加段'
                })()}
              </Button>
            </Space>
          </div>

          <Table
            size="small"
            rowKey={(_, i) => String(i)}
            dataSource={segments.map((s, i) => ({ ...s, _idx: i }))}
            pagination={false}
            columns={(() => {
              const m = ruleForm.getFieldValue('calc_method') || 'PIECEWISE'
              if (m === 'LINEAR') {
                return [
                  { title: '序号', dataIndex: 'seg_order', width: 60,
                    render: (_: any, r: any) => (
                      <InputNumber
                        value={r.seg_order}
                        onChange={(v) => updateSegment(r._idx, 'seg_order', v)}
                        min={1}
                        style={{ width: '100%' }}
                      />
                    ),
                  },
                  { title: '锚点 x (指标值)', width: 160,
                    render: (_: any, r: any) => (
                      <InputNumber
                        value={r.min_value ?? undefined}
                        onChange={(v) => updateSegment(r._idx, 'min_value', v)}
                        placeholder="如：8"
                        style={{ width: '100%' }}
                      />
                    ),
                  },
                  { title: '锚点 score', width: 130,
                    render: (_: any, r: any) => (
                      <InputNumber
                        value={r.score}
                        onChange={(v) => updateSegment(r._idx, 'score', v)}
                        style={{ width: '100%' }}
                      />
                    ),
                  },
                  { title: '锚点说明',
                    render: (_: any, r: any) => (
                      <Input
                        value={r.segment_desc || ''}
                        onChange={(e) => updateSegment(r._idx, 'segment_desc', e.target.value)}
                        placeholder="如：监管底线 8% → 60 分"
                      />
                    ),
                  },
                  { title: '操作', width: 60,
                    render: (_: any, r: any) => (
                      <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeSegment(r._idx)} />
                    ),
                  },
                ]
              }
              return [
                { title: '序号', dataIndex: 'seg_order', width: 60,
                  render: (_: any, r: any) => (
                    <InputNumber
                      value={r.seg_order}
                      onChange={(v) => updateSegment(r._idx, 'seg_order', v)}
                      min={1}
                      style={{ width: '100%' }}
                    />
                  ),
                },
                { title: '最小值 ≥', width: 105,
                  render: (_: any, r: any) => (
                    <InputNumber
                      value={r.min_value ?? undefined}
                      onChange={(v) => updateSegment(r._idx, 'min_value', v)}
                      placeholder="-∞"
                      style={{ width: '100%' }}
                    />
                  ),
                },
                { title: '最大值 <', width: 105,
                  render: (_: any, r: any) => (
                    <InputNumber
                      value={r.max_value ?? undefined}
                      onChange={(v) => updateSegment(r._idx, 'max_value', v)}
                      placeholder="+∞"
                      style={{ width: '100%' }}
                    />
                  ),
                },
                {
                  title: <span style={{ color: '#fa8c16' }}>最小值分数</span>, width: 100,
                  render: (_: any, r: any) => (
                    <Tooltip title="该段下界（最小值）处的得分，留空则不启用段内插值，按阶梯评分">
                      <InputNumber
                        value={r.score_min ?? undefined}
                        onChange={(v) => updateSegment(r._idx, 'score_min', v)}
                        placeholder="阶梯"
                        style={{ width: '100%' }}
                      />
                    </Tooltip>
                  ),
                },
                {
                  title: <span style={{ color: '#165dff' }}>最大值分数</span>, width: 100,
                  render: (_: any, r: any) => (
                    <Tooltip title="该段上界（最大值）处的得分。两端分数都填写时，段内按线性插值">
                      <InputNumber
                        value={r.score}
                        onChange={(v) => updateSegment(r._idx, 'score', v)}
                        style={{ width: '100%' }}
                      />
                    </Tooltip>
                  ),
                },
                { title: '描述', width: 160,
                  render: (_: any, r: any) => (
                    <Input
                      value={r.segment_desc || ''}
                      onChange={(e) => updateSegment(r._idx, 'segment_desc', e.target.value)}
                      placeholder="如：优秀"
                    />
                  ),
                },
                { title: '操作', width: 60,
                  render: (_: any, r: any) => (
                    <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeSegment(r._idx)} />
                  ),
                },
              ]
            })()}
          />
        </Form>
      </Modal>
    </Spin>
  )
}

export default KpiScore
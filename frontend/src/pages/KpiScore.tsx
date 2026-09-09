import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Row, Col, Form, Input, Select, Button, Table, Space, Tag,
  Modal, message, Spin, Empty, Statistic, Alert, InputNumber, Divider, Tooltip,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ThunderboltOutlined,
  CalculatorOutlined, FunctionOutlined,
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

  // 计算器
  const [calcValue, setCalcValue] = useState<number | null>(null)
  const [calcResult, setCalcResult] = useState<any>(null)

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
    // 默认三段示例
    setSegments([
      { seg_order: 1, min_value: null, max_value: 60, score: 60, segment_desc: '不及格' },
      { seg_order: 2, min_value: 60, max_value: 80, score: 80, segment_desc: '及格' },
      { seg_order: 3, min_value: 80, max_value: null, score: 100, segment_desc: '优秀' },
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

  // 计算器：实时算
  const onCalc = async (ruleId: number) => {
    if (calcValue === null || calcValue === undefined) {
      message.warning('请输入指标值')
      return
    }
    try {
      const r = await kpiApi.scoreCalc(ruleId, calcValue)
      setCalcResult(r)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '计算失败')
    }
  }

  // ========= 列定义 =========
  const defCols: ColumnsType<any> = [
    { title: '编码', dataIndex: 'kpi_code', width: 130, render: (c) => <code>{c}</code> },
    { title: '名称', dataIndex: 'kpi_name', ellipsis: true },
    { title: '所属报表', dataIndex: 'report_name', width: 120, ellipsis: true },
  ]

  const ruleCols: ColumnsType<any> = [
    { title: '规则名称', dataIndex: 'rule_name', width: 200, render: (n) => <strong>{n}</strong> },
    {
      title: '总分', dataIndex: 'total_score', width: 80,
      render: (s) => <Tag color="blue">{s}</Tag>,
    },
    {
      title: '方向', dataIndex: 'higher_is_better', width: 100,
      render: (v) => <Tag color={v ? 'green' : 'orange'}>{v ? '↑ 正向' : '↓ 逆向'}</Tag>,
    },
    {
      title: '段数', key: 'seg_count', width: 70,
      render: (_, r) => <Tag>{r.segments?.length || 0} 段</Tag>,
    },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (s) => <Tag color={s === 'ACTIVE' ? 'green' : 'default'}>{s}</Tag>,
    },
    {
      title: '操作', width: 220, fixed: 'right' as const,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<CalculatorOutlined />} onClick={() => onCalc(r.id)}>试算</Button>
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
                  <Button type="primary" icon={<PlusOutlined />} onClick={onCreateRule}>新增规则</Button>
                </Space>
              }
              bodyStyle={{ padding: 16 }}
            >
              {/* 实时计算器 */}
              <Card size="small" style={{ marginBottom: 12, background: '#fafafa' }}>
                <Space wrap>
                  <span>🧮 试算：</span>
                  <span>假设指标值 =</span>
                  <InputNumber
                    value={calcValue ?? undefined}
                    onChange={(v) => setCalcValue(v as number)}
                    placeholder="如 75"
                    style={{ width: 120 }}
                  />
                  <span>得分 =</span>
                  {calcResult && (
                    calcResult.matched ? (
                      <Tag color="green" style={{ fontSize: 14, padding: '4px 12px' }}>
                        {calcResult.score} 分（{calcResult.matched_range?.segment_desc || '已匹配'}）
                      </Tag>
                    ) : (
                      <Tag color="red">未匹配</Tag>
                    )
                  )}
                  <span style={{ color: '#999', fontSize: 12 }}>
                    点规则行的【试算】按钮
                  </span>
                </Space>
              </Card>

              {/* 规则列表 */}
              <Table
                size="small"
                rowKey="id"
                dataSource={rules}
                columns={ruleCols}
                scroll={{ x: 800 }}
                pagination={{ pageSize: 10 }}
                expandable={{
                  expandedRowRender: (r) => (
                    <div style={{ padding: '8px 12px', background: '#fafafa', borderRadius: 4 }}>
                      <div style={{ marginBottom: 8, color: '#666' }}>
                        📊 评分段（{r.segments?.length || 0} 段）：
                      </div>
                      <Space wrap size={[6, 6]}>
                        {(r.segments || []).map((s: any) => (
                          <Tag key={s.id} color="geekblue" style={{ padding: '4px 10px' }}>
                            {s.min_value !== null ? `≥${s.min_value}` : '-∞'} ~
                            {s.max_value !== null ? ` <${s.max_value}` : ' +∞'}
                            {' → '}
                            <strong style={{ color: '#1890ff' }}>{s.score} 分</strong>
                            {s.segment_desc && ` · ${s.segment_desc}`}
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
        width={760}
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

          <Divider orientation="left" plain>评分段（按指标值区间 → 分数）</Divider>

          <div style={{ marginBottom: 8 }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <span style={{ color: '#666', fontSize: 12 }}>
                💡 提示：每段填写 <strong>min_value</strong>（含）和 <strong>max_value</strong>（不含）。两端可以留空表示 -∞ 或 +∞。
              </span>
              <Button size="small" icon={<PlusOutlined />} onClick={addSegment}>添加段</Button>
            </Space>
          </div>

          <Table
            size="small"
            rowKey={(_, i) => String(i)}
            dataSource={segments.map((s, i) => ({ ...s, _idx: i }))}
            pagination={false}
            columns={[
              { title: '序号', dataIndex: 'seg_order', width: 60,
                render: (_, r) => (
                  <InputNumber
                    value={r.seg_order}
                    onChange={(v) => updateSegment(r._idx, 'seg_order', v)}
                    min={1}
                    style={{ width: '100%' }}
                  />
                ),
              },
              { title: '最小值 ≥', width: 110,
                render: (_, r) => (
                  <InputNumber
                    value={r.min_value ?? undefined}
                    onChange={(v) => updateSegment(r._idx, 'min_value', v)}
                    placeholder="-∞"
                    style={{ width: '100%' }}
                  />
                ),
              },
              { title: '最大值 <', width: 110,
                render: (_, r) => (
                  <InputNumber
                    value={r.max_value ?? undefined}
                    onChange={(v) => updateSegment(r._idx, 'max_value', v)}
                    placeholder="+∞"
                    style={{ width: '100%' }}
                  />
                ),
              },
              { title: '分数', width: 90,
                render: (_, r) => (
                  <InputNumber
                    value={r.score}
                    onChange={(v) => updateSegment(r._idx, 'score', v)}
                    style={{ width: '100%' }}
                  />
                ),
              },
              { title: '描述', 
                render: (_, r) => (
                  <Input
                    value={r.segment_desc || ''}
                    onChange={(e) => updateSegment(r._idx, 'segment_desc', e.target.value)}
                    placeholder="如：优秀"
                  />
                ),
              },
              { title: '操作', width: 60,
                render: (_, r) => (
                  <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeSegment(r._idx)} />
                ),
              },
            ]}
          />
        </Form>
      </Modal>
    </Spin>
  )
}

export default KpiScore
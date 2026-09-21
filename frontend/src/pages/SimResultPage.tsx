/** 新业务模拟 — 结果查看页
 *
 * 入口：/sim/results/:sim_scheme_code
 * 功能：展示引擎按月滚动生成的结果快照
 */
import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Select, Table, Space, Tag, message, Empty, Row, Col, Statistic,
  Spin, Button, Tabs, Tooltip, Progress,
} from 'antd'
import {
  ArrowLeftOutlined, ReloadOutlined, LineChartOutlined,
  CalendarOutlined, FundProjectionScreenOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useParams, useNavigate } from 'react-router-dom'
import { simApi } from '../api'

const SimResultPage: React.FC = () => {
  const params = useParams()
  const navigate = useNavigate()
  const schemeCode = params.sim_scheme_code || ''

  const [schemes, setSchemes] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [activeRun, setActiveRun] = useState<number | null>(null)
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [dateOffset, setDateOffset] = useState<number | null>(null)  // null = 所有月份
  const [category, setCategory] = useState<string | undefined>(undefined)

  // 加载方案列表（用于顶部下拉）
  const loadSchemes = async () => {
    try {
      const r = await simApi.listSchemes()
      setSchemes(r.items || [])
    } catch {
      // 静默
    }
  }

  // 加载 runs
  const loadRuns = async (code: string) => {
    if (!code) return
    try {
      const r = await simApi.listRuns({ sim_scheme_code: code })
      setRuns(r.items || [])
      // 默认选最新 SUCCESS run
      const successRuns = r.items.filter((x: any) => x.status === 'SUCCESS')
      if (successRuns.length > 0) {
        setActiveRun(successRuns[0].id)
      } else if (r.items.length > 0) {
        setActiveRun(r.items[0].id)
      }
    } catch {
      setRuns([])
    }
  }

  // 加载 results
  const loadResults = async (runId: number | null) => {
    if (!runId) { setResults([]); return }
    setLoading(true)
    try {
      const params: any = { run_id: runId }
      if (dateOffset) params.date_offset = dateOffset
      if (category) params.category = category
      const r = await simApi.listResults(params)
      setResults(r.items || [])
    } catch (e: any) {
      message.error('结果加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadSchemes() }, [])
  useEffect(() => {
    if (schemeCode) loadRuns(schemeCode)
  }, [schemeCode])
  useEffect(() => { loadResults(activeRun) }, [activeRun, dateOffset, category])

  // 切换方案
  const switchScheme = (code: string) => {
    if (code === schemeCode) return
    navigate(`/sim/results/${code}`)
  }

  // KPI 汇总
  const kpi = useMemo(() => {
    if (results.length === 0) return null
    const total_current = results.reduce((a, r) => a + (r.current_balance || 0), 0)
    const total_avg = results.reduce((a, r) => a + (r.avg_balance || 0), 0)
    const total_interest = results.reduce((a, r) => a + (r.interest_amount || 0), 0)
    // 加权平均利率 = Σ(avg × wr) / Σ(avg)
    const sum_avg_wr = results.reduce((a, r) => a + (r.avg_balance || 0) * (r.weighted_rate || 0), 0)
    const sum_avg = results.reduce((a, r) => a + (r.avg_balance || 0), 0)
    const avg_wr = sum_avg > 0 ? sum_avg_wr / sum_avg : 0
    return { total_current, total_avg, total_interest, avg_wr }
  }, [results])

  // 表格列
  const columns: ColumnsType<any> = [
    {
      title: '月份', dataIndex: 'date_offset', width: 80, fixed: 'left',
      render: (v: number) => <Tag color="blue">M{v}</Tag>,
    },
    {
      title: '日期', dataIndex: 'data_date', width: 110,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</span>,
    },
    {
      title: '节点编码', dataIndex: 'node_code', width: 140, fixed: 'left',
      render: (v: string) => <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 3 }}>{v}</code>,
    },
    {
      title: '节点名称', dataIndex: 'node_name', width: 200,
      ellipsis: true,
    },
    {
      title: '当前余额', dataIndex: 'current_balance', width: 150,
      align: 'right' as const,
      sorter: (a: any, b: any) => a.current_balance - b.current_balance,
      render: (v: number) => v ? <strong style={{ color: '#2f54eb' }}>{v.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}</strong> : '-',
    },
    {
      title: '平均余额', dataIndex: 'avg_balance', width: 150,
      align: 'right' as const,
      sorter: (a: any, b: any) => a.avg_balance - b.avg_balance,
      render: (v: number) => v ? v.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '-',
    },
    {
      title: '加权平均利率(%)', dataIndex: 'weighted_rate', width: 130,
      align: 'right' as const,
      render: (v: number) => v ? <span style={{ color: '#fa8c16' }}>{v.toFixed(4)}</span> : '-',
    },
    {
      title: '当月利息', dataIndex: 'interest_amount', width: 130,
      align: 'right' as const,
      render: (v: number) => v ? v.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '-',
    },
    {
      title: '类别', dataIndex: 'category', width: 100,
      render: (v: string) => v ? <Tag color={v === 'ASSET' ? 'blue' : v === 'LIABILITY' ? 'orange' : 'default'}>{v}</Tag> : '-',
    },
  ]

  // 按 date_offset 分组（每个月份一个 Tab）
  const byMonth = useMemo(() => {
    const map = new Map<number, any[]>()
    for (const r of results) {
      if (!map.has(r.date_offset)) map.set(r.date_offset, [])
      map.get(r.date_offset)!.push(r)
    }
    return Array.from(map.entries()).sort((a, b) => a[0] - b[0])
  }, [results])

  const currentScheme = schemes.find(s => s.scheme_code === schemeCode)
  const currentRun = runs.find(r => r.id === activeRun)

  return (
    <div className="page-container">
      {/* 顶部信息条 */}
      <Card
        size="small"
        title={
          <Space>
            <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => navigate('/sim/list')} style={{ paddingLeft: 0 }}>
              返回方案列表
            </Button>
            <span style={{ color: '#999' }}>|</span>
            <FundProjectionScreenOutlined style={{ color: '#722ed1' }} />
            <span>模拟结果查看</span>
            {currentScheme && (
              <Space size={6} style={{ fontWeight: 'normal', fontSize: 13 }}>
                <Tag color="purple">{currentScheme.scheme_code}</Tag>
                <span>{currentScheme.scheme_name}</span>
                {currentScheme.data_date && (
                  <Tag color="cyan" icon={<CalendarOutlined />} style={{ fontFamily: 'monospace' }}>
                    起始月 {currentScheme.data_date}
                  </Tag>
                )}
              </Space>
            )}
          </Space>
        }
        extra={
          <Space>
            <Select
              showSearch
              optionFilterProp="label"
              style={{ width: 260 }}
              value={schemeCode}
              onChange={switchScheme}
              placeholder="选择方案"
              options={schemes.map(s => ({
                value: s.scheme_code,
                label: `${s.scheme_code} | ${s.scheme_name}`,
              }))}
            />
            {runs.length > 0 && (
              <Select
                style={{ width: 220 }}
                value={activeRun}
                onChange={setActiveRun}
                placeholder="选择 Run"
                options={runs.map(r => ({
                  value: r.id,
                  label: `run#${r.id} ${r.status} M=${r.month_count} ${r.started_at?.slice(0,16).replace('T',' ')}`,
                }))}
              />
            )}
            <Button icon={<ReloadOutlined />} onClick={() => loadResults(activeRun)}>刷新</Button>
          </Space>
        }
      />

      {/* Run 状态卡 */}
      {currentRun && (
        <Card size="small" style={{ marginTop: 12 }}>
          <Row gutter={16}>
            <Col span={4}>
              <Statistic title="Run ID" value={currentRun.id} prefix={<LineChartOutlined style={{ color: '#722ed1' }} />} />
            </Col>
            <Col span={4}>
              <Statistic title="状态" value={currentRun.status}
                valueStyle={{ color: currentRun.status === 'SUCCESS' ? '#52c41a' : '#f5222d' }} />
            </Col>
            <Col span={4}>
              <Statistic title="节点数" value={currentRun.total_nodes} />
            </Col>
            <Col span={4}>
              <Statistic title="生成月份" value={currentRun.month_count} />
            </Col>
            <Col span={4}>
              <Statistic title="耗时" value={currentRun.duration_ms || '-'} suffix="ms" />
            </Col>
            <Col span={4}>
              <Statistic
                title="基准月 → 目标月"
                value={`${currentRun.base_data_date} → ${currentRun.target_data_date}`}
                valueStyle={{ fontSize: 13 }}
              />
            </Col>
          </Row>
          {currentRun.status === 'FAILED' && (
            <div style={{ marginTop: 12, color: '#f5222d' }}>
              <strong>错误：</strong><code>{currentRun.error_message}</code>
            </div>
          )}
        </Card>
      )}

      {/* KPI 汇总 */}
      {kpi && (
        <Card size="small" style={{ marginTop: 12, background: '#f0f5ff' }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="汇总当前余额"
                value={kpi.total_current}
                precision={2}
                valueStyle={{ color: '#2f54eb' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="汇总平均余额"
                value={kpi.total_avg}
                precision={2}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="加权平均利率"
                value={kpi.avg_wr}
                precision={4}
                suffix="%"
                valueStyle={{ color: '#fa8c16' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="汇总当月利息"
                value={kpi.total_interest}
                precision={2}
                valueStyle={{ color: '#722ed1' }}
              />
            </Col>
          </Row>
        </Card>
      )}

      {/* 筛选 */}
      <Card size="small" style={{ marginTop: 12 }}>
        <Space>
          <span>月份：</span>
          <Select
            style={{ width: 120 }}
            placeholder="所有月份"
            allowClear
            value={dateOffset}
            onChange={setDateOffset}
            options={Array.from({ length: 24 }, (_, i) => ({
              value: i + 1,
              label: `M${i + 1}`,
            }))}
          />
          <span>类别：</span>
          <Select
            style={{ width: 120 }}
            placeholder="所有类别"
            allowClear
            value={category}
            onChange={setCategory}
            options={[
              { value: 'ASSET', label: '资产' },
              { value: 'LIABILITY', label: '负债' },
              { value: 'EQUITY', label: '权益' },
              { value: 'OFF_BALANCE', label: '表外' },
            ]}
          />
        </Space>
      </Card>

      {/* 结果表格 */}
      <Card style={{ marginTop: 12 }}>
        <Spin spinning={loading}>
          {byMonth.length === 0 ? (
            <Empty description={
              currentRun?.status === 'SUCCESS' ? '无结果数据' :
              currentRun ? `Run 状态: ${currentRun.status}` : '请选择 Run'
            } />
          ) : dateOffset ? (
            // 单月视图
            <Table
              rowKey={(r) => `${r.run_id}-${r.coa_node_id}-${r.date_offset}`}
              columns={columns}
              dataSource={byMonth[0]?.[1] || []}
              size="middle"
              pagination={{ pageSize: 20 }}
              scroll={{ x: 1100 }}
            />
          ) : (
            // 按月份 Tab
            <Tabs
              defaultActiveKey="1"
              items={byMonth.map(([m, rows]) => ({
                key: String(m),
                label: <Space><Tag color="blue">M{m}</Tag>{rows[0]?.data_date}</Space>,
                children: (
                  <Table
                    rowKey={(r) => `${r.run_id}-${r.coa_node_id}-${r.date_offset}`}
                    columns={columns}
                    dataSource={rows}
                    size="middle"
                    pagination={{ pageSize: 20 }}
                    scroll={{ x: 1100 }}
                  />
                ),
              }))}
            />
          )}
        </Spin>
      </Card>
    </div>
  )
}

export default SimResultPage

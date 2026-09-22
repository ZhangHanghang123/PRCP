/** PRCP ESG · 结果汇总页
 *
 * 入口：/esg/results
 * 功能：方案 + 运行 + 情景集 三表数据汇总
 */
import React, { useState } from 'react'
import {
  Card, Table, Tag, Row, Col, Statistic, Tabs, Empty, Button, message, Space,
} from 'antd'
import {
  ReloadOutlined, RocketOutlined, FolderOutlined, HistoryOutlined,
  AreaChartOutlined, EyeOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import {
  esgApi, yieldCurveApi,
  ESG_STATUS_OPTIONS, ESG_RUN_TYPE_OPTIONS, ESG_RUN_STATUS_OPTIONS,
  EsgScheme, EsgRun, EsgScenario, SourceStat,
} from '../api/esg'

const EsgResults: React.FC = () => {
  const navigate = useNavigate()
  const [schemes, setSchemes] = useState<EsgScheme[]>([])
  const [runs, setRuns] = useState<EsgRun[]>([])
  const [scenarios, setScenarios] = useState<EsgScenario[]>([])
  const [sources, setSources] = useState<SourceStat[]>([])
  const [loading, setLoading] = useState(false)
  const [runTypeFilter, setRunTypeFilter] = useState<string | undefined>(undefined)
  const [schemeFilter, setSchemeFilter] = useState<number | undefined>(undefined)

  const loadAll = async () => {
    setLoading(true)
    try {
      const [sr, rr, scr, srcs] = await Promise.all([
        esgApi.listSchemes({ page_size: 100 }),
        esgApi.listAllRuns({ page_size: 100 }),
        esgApi.listScenarios({ page_size: 100 }),
        yieldCurveApi.sources(),
      ])
      setSchemes(sr.items || [])
      setRuns(rr.items || [])
      setScenarios(scr.items || [])
      setSources(srcs.items || [])
    } catch (e: any) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => { loadAll() }, [])

  // 派生统计
  const totalCurveRows = sources.reduce((a, s) => a + s.count, 0)
  const schemeByStatus = schemes.reduce((m, s) => {
    m[s.status] = (m[s.status] || 0) + 1; return m
  }, {} as Record<string, number>)
  const runByType = runs.reduce((m, r) => {
    m[r.run_type] = (m[r.run_type] || 0) + 1; return m
  }, {} as Record<string, number>)
  const totalScenarioSize = scenarios.reduce((a, s) => a + (s.file_size_bytes || 0), 0)

  const filteredRuns = runs.filter((r) =>
    (!runTypeFilter || r.run_type === runTypeFilter) &&
    (!schemeFilter || r.scheme_id === schemeFilter)
  )

  // 表格列
  const schemeColumns: ColumnsType<EsgScheme> = [
    { title: '#', dataIndex: 'id', width: 50 },
    { title: 'Code', dataIndex: 'scheme_code', width: 180,
      render: (v: string) => <code style={{ fontSize: 12 }}>{v}</code> },
    { title: '方案名', dataIndex: 'scheme_name' },
    { title: '数据源', dataIndex: 'data_source', width: 80,
      render: (v: string) => <Tag>{v}</Tag> },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => {
        const c = ESG_STATUS_OPTIONS.find((x) => x.value === v)
        return <Tag color={c?.color}>{c?.label}</Tag>
      } },
    { title: '运行数', dataIndex: 'run_count', width: 70,
      render: (v?: number) => v || 0 },
    { title: '操作', width: 100,
      render: (_: any, row: EsgScheme) => (
        <Button size="small" icon={<EyeOutlined />}
                onClick={() => navigate(`/esg/detail/${row.id}`)}>详情</Button>
      ),
    },
  ]

  const runColumns: ColumnsType<EsgRun> = [
    { title: '#', dataIndex: 'id', width: 50 },
    { title: '方案', dataIndex: 'scheme_code', width: 160,
      render: (v?: string) => v ? <code style={{ fontSize: 12 }}>{v}</code> : '-' },
    { title: '类型', dataIndex: 'run_type', width: 150,
      render: (v: string) => {
        const c = ESG_RUN_TYPE_OPTIONS.find((x) => x.value === v)
        return <Tag color={c?.color}>{c?.label || v}</Tag>
      } },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => {
        const c = ESG_RUN_STATUS_OPTIONS.find((x) => x.value === v)
        return <Tag color={c?.color}>{c?.label}</Tag>
      } },
    { title: '耗时', dataIndex: 'duration_ms', width: 80,
      render: (v?: number) => v ? `${v}ms` : '-' },
    { title: '时间', dataIndex: 'created_at', width: 160,
      render: (v?: string) => v ? v.replace('T', ' ').slice(0, 19) : '-' },
  ]

  const scenarioColumns: ColumnsType<EsgScenario> = [
    { title: '#', dataIndex: 'id', width: 50 },
    { title: 'Scenario Code', dataIndex: 'scenario_code', width: 180,
      render: (v: string) => <code style={{ fontSize: 12 }}>{v}</code> },
    { title: '方案ID', dataIndex: 'scheme_id', width: 80 },
    { title: 'n × steps × maturities',
      width: 200,
      render: (_: any, row: EsgScenario) => `${row.n_scenarios} × ${row.n_steps} × ${row.n_maturities}`,
    },
    { title: '大小', dataIndex: 'file_size_bytes', width: 110,
      render: (v?: number) => v ? `${(v/1024).toFixed(1)} KB` : '-' },
    { title: '时间', dataIndex: 'created_at', width: 160,
      render: (v?: string) => v ? v.replace('T', ' ').slice(0, 19) : '-' },
    { title: '下载', width: 100,
      render: (_: any, row: EsgScenario) => (
        <Button size="small" onClick={() => {
          const a = document.createElement('a')
          a.href = esgApi.downloadScenarioUrl(row.scenario_code)
          a.download = `scenario_${row.scenario_code}.npz`
          document.body.appendChild(a); a.click(); document.body.removeChild(a)
        }}>下载</Button>
      ),
    },
  ]

  return (
    <div className="page-container">
      {/* 顶部 KPI */}
      <Card size="small" style={{ marginBottom: 12, background: 'linear-gradient(135deg, #f9f0ff 0%, #fff7e6 100%)' }}>
        <Row gutter={16}>
          <Col span={4}><Statistic title="方案总数" value={schemes.length}
            prefix={<FolderOutlined style={{ color: '#722ed1' }} />} /></Col>
          <Col span={4}><Statistic title="运行总数" value={runs.length}
            prefix={<HistoryOutlined style={{ color: '#13c2c2' }} />} /></Col>
          <Col span={4}><Statistic title="情景集总数" value={scenarios.length}
            prefix={<AreaChartOutlined style={{ color: '#fa8c16' }} />} /></Col>
          <Col span={4}><Statistic title="曲线数据" value={totalCurveRows}
            prefix={<RocketOutlined style={{ color: '#52c41a' }} />} /></Col>
          <Col span={4}><Statistic title=".npz 总大小" value={`${(totalScenarioSize/1024/1024).toFixed(2)} MB`}
            prefix={<AreaChartOutlined style={{ color: '#1890ff' }} />} /></Col>
          <Col span={4}><Statistic title="READY 方案" value={schemeByStatus.READY || 0}
            valueStyle={{ color: '#52c41a' }} /></Col>
        </Row>
      </Card>

      <Card
        size="small"
        title="ESG 全景数据"
        extra={
          <Space>
            <Button icon={<RocketOutlined />} onClick={() => navigate('/esg')}>
              方案管理
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadAll}>刷新</Button>
          </Space>
        }
      >
        <Tabs
          items={[
            {
              key: 'schemes',
              label: <Space><FolderOutlined />方案 ({schemes.length})</Space>,
              children: (
                <Table rowKey="id" loading={loading} dataSource={schemes} columns={schemeColumns}
                  size="small" pagination={{ pageSize: 20 }}
                  locale={{ emptyText: <Empty description="暂无方案" /> }} />
              ),
            },
            {
              key: 'runs',
              label: <Space><HistoryOutlined />运行历史 ({runs.length})</Space>,
              children: (
                <>
                  <Space style={{ marginBottom: 8 }}>
                    <span>类型:</span>
                    <select value={runTypeFilter || ''} onChange={(e) => setRunTypeFilter(e.target.value || undefined)}
                      style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #d9d9d9' }}>
                      <option value="">全部</option>
                      {ESG_RUN_TYPE_OPTIONS.map((x) => (
                        <option key={x.value} value={x.value}>{x.label}</option>
                      ))}
                    </select>
                    <span>方案:</span>
                    <select value={schemeFilter || ''} onChange={(e) => setSchemeFilter(e.target.value ? Number(e.target.value) : undefined)}
                      style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #d9d9d9' }}>
                      <option value="">全部</option>
                      {schemes.map((s) => (
                        <option key={s.id} value={s.id}>{s.scheme_code}</option>
                      ))}
                    </select>
                  </Space>
                  <Table rowKey="id" loading={loading} dataSource={filteredRuns} columns={runColumns}
                    size="small" pagination={{ pageSize: 20 }}
                    locale={{ emptyText: <Empty description="暂无运行记录" /> }} />
                </>
              ),
            },
            {
              key: 'scenarios',
              label: <Space><AreaChartOutlined />情景集 ({scenarios.length})</Space>,
              children: (
                <Table rowKey="id" loading={loading} dataSource={scenarios} columns={scenarioColumns}
                  size="small" pagination={{ pageSize: 20 }}
                  locale={{ emptyText: <Empty description="暂无情景集" /> }} />
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default EsgResults
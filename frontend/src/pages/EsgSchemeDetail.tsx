/** PRCP ESG 场景工厂 · 方案详情页（3 步执行）
 *
 * 入口：/esg/detail/:scheme_id
 * 功能：3 步执行按钮（PCA / HJM / Scenario）+ 一键三步 + 运行历史 Tab
 */
import React, { useEffect, useState } from 'react'
import {
  Card, Tabs, Button, Space, Tag, Alert, Row, Col, Statistic,
  Spin, Empty, Table, message, Descriptions, Progress,
} from 'antd'
import {
  ArrowLeftOutlined, RocketOutlined, ThunderboltOutlined,
  LineChartOutlined, ClusterOutlined, DownloadOutlined,
  ReloadOutlined, HistoryOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useParams, useNavigate } from 'react-router-dom'
import {
  esgApi, ESG_RUN_TYPE_OPTIONS, ESG_STATUS_OPTIONS, ESG_RUN_STATUS_OPTIONS,
  EsgScheme, EsgRun, EsgScenario,
} from '../api/esg'
import PcaResultPanel from '../components/esg/PcaResultPanel'
import HjmResultPanel from '../components/esg/HjmResultPanel'
import ScenarioResultPanel from '../components/esg/ScenarioResultPanel'

const EsgSchemeDetail: React.FC = () => {
  const { scheme_id } = useParams()
  const navigate = useNavigate()
  const schemeId = Number(scheme_id)

  const [scheme, setScheme] = useState<EsgScheme | null>(null)
  const [runs, setRuns] = useState<EsgRun[]>([])
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [scenarios, setScenarios] = useState<EsgScenario[]>([])

  // 各步最后一次运行结果（用于 Panel 展示）
  const [lastPcaRun, setLastPcaRun] = useState<EsgRun | null>(null)
  const [lastHjmRun, setLastHjmRun] = useState<EsgRun | null>(null)
  const [lastScenarioRun, setLastScenarioRun] = useState<EsgRun | null>(null)

  const loadScheme = async () => {
    if (!schemeId) return
    setLoading(true)
    try {
      const r = await esgApi.getScheme(schemeId)
      setScheme(r)
    } catch (e: any) {
      message.error('方案加载失败')
    } finally {
      setLoading(false)
    }
  }

  const loadRuns = async () => {
    if (!schemeId) return
    try {
      const r = await esgApi.listSchemeRuns(schemeId)
      const items: EsgRun[] = r.items || []
      setRuns(items)
      // 找最后一次各类型
      const lastPca = items.find((x) => x.run_type === 'PCA_FIT')
      const lastHjm = items.find((x) => x.run_type === 'HJM_GENERATE')
      const lastSc = items.find((x) => x.run_type === 'SCENARIO_GENERATE')
      setLastPcaRun(lastPca || null)
      setLastHjmRun(lastHjm || null)
      setLastScenarioRun(lastSc || null)
    } catch {
      /* 静默 */
    }
  }

  const loadScenarios = async () => {
    if (!schemeId) return
    try {
      const r = await esgApi.listScenarios({ scheme_id: schemeId })
      setScenarios(r.items || [])
    } catch { /* 静默 */ }
  }

  useEffect(() => { loadScheme(); loadRuns(); loadScenarios() }, [schemeId])

  // ============== 操作 ==============

  const handleFitPca = async () => {
    setActionLoading('pca')
    try {
      const r = await esgApi.fitPca(schemeId)
      message.success(`PCA 拟合完成 run#${r.run_id}，3 因子累计方差 ${(r.summary.cumulative_variance_3f_pct * 100).toFixed(2)}%`)
      await loadRuns()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'PCA 拟合失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleGenerateHjm = async () => {
    setActionLoading('hjm')
    try {
      const r = await esgApi.generateHjm(schemeId, {})
      message.success(`HJM 路径生成完成 run#${r.run_id}，${r.summary.paths_shape}`)
      await loadRuns()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'HJM 生成失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleGenerateScenario = async () => {
    setActionLoading('scenario')
    try {
      const r = await esgApi.generateScenario(schemeId)
      message.success(`情景集生成完成 run#${r.run_id} scenario=${r.scenario_code}`)
      await loadRuns()
      await loadScenarios()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '情景集生成失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleRunAll = async () => {
    setActionLoading('all')
    try {
      const r = await esgApi.runAll(schemeId)
      message.success(
        `一键三步完成：pca=${r.pca_run_id} hjm=${r.hjm_run_id} scenario=${r.scenario_code}`
      )
      await loadRuns()
      await loadScenarios()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '一键三步失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDownload = (sc: EsgScenario) => {
    const url = esgApi.downloadScenarioUrl(sc.scenario_code)
    const a = document.createElement('a')
    a.href = url
    a.download = `scenario_${sc.scenario_code}.npz`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
  }

  // ============== 运行历史表 ==============

  const runColumns: ColumnsType<EsgRun> = [
    { title: '#', dataIndex: 'id', width: 60 },
    { title: '类型', dataIndex: 'run_type', width: 150,
      render: (v: string) => {
        const c = ESG_RUN_TYPE_OPTIONS.find((x) => x.value === v)
        return <Tag color={c?.color}>{c?.label || v}</Tag>
      },
    },
    { title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => {
        const c = ESG_RUN_STATUS_OPTIONS.find((x) => x.value === v)
        return <Tag color={c?.color}>{c?.label || v}</Tag>
      },
    },
    { title: '耗时', dataIndex: 'duration_ms', width: 80,
      render: (v?: number) => v ? `${v}ms` : '-',
    },
    { title: '时间', dataIndex: 'created_at', width: 160,
      render: (v?: string) => v ? v.replace('T', ' ').slice(0, 19) : '-',
    },
    { title: '结果摘要', dataIndex: 'output',
      render: (v: any, row: EsgRun) => {
        if (!v) return '-'
        if (row.run_type === 'PCA_FIT') {
          return `累计方差 ${(v.cumulative_variance_3f_pct * 100).toFixed(2)}% / 样本 ${v.n_samples}`
        }
        if (row.run_type === 'HJM_GENERATE') {
          return `paths=${v.paths_shape} / min=${v.paths_min?.toFixed(2)}% / max=${v.paths_max?.toFixed(2)}%`
        }
        if (row.run_type === 'SCENARIO_GENERATE') {
          return `scenario=${v.scenario_code} / size=${v.file_size_bytes} bytes`
        }
        return '-'
      },
    },
  ]

  // ============== 渲染 ==============

  if (loading || !scheme) {
    return (
      <div style={{ padding: 24 }}>
        <Spin tip="加载方案中..." spinning={true}>
          <div style={{ minHeight: 200 }} />
        </Spin>
      </div>
    )
  }

  const statusColor = ESG_STATUS_OPTIONS.find((x) => x.value === scheme.status)?.color || 'default'
  const canPca = true
  const canHjm = !!lastPcaRun
  const canScenario = !!lastHjmRun

  return (
    <div className="page-container">
      {/* 顶部信息条 */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space style={{ marginBottom: 8 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/esg')}>
            返回方案列表
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => { loadScheme(); loadRuns(); loadScenarios() }}>
            刷新
          </Button>
        </Space>
        <Alert
          message={
            <Space>
              <Tag color="purple">{scheme.scheme_code}</Tag>
              <strong style={{ fontSize: 16 }}>{scheme.scheme_name}</strong>
              <Tag color={statusColor}>{scheme.status}</Tag>
              {scheme.scheme_code === 'PRCP_ESG_DEMO_001' && <Tag color="cyan">演示方案</Tag>}
            </Space>
          }
          description={
            <Row gutter={16} style={{ marginTop: 8 }}>
              <Col span={4}><Statistic title="数据源" value={scheme.data_source} valueStyle={{ fontSize: 14 }} /></Col>
              <Col span={6}>
                <Statistic title="起止日期" valueStyle={{ fontSize: 14 }}
                  value={scheme.start_date && scheme.end_date ? `${scheme.start_date} ~ ${scheme.end_date}` : '未设'} />
              </Col>
              <Col span={4}><Statistic title="因子数" value={scheme.n_factors} valueStyle={{ fontSize: 14 }} /></Col>
              <Col span={4}><Statistic title="情景数" value={scheme.n_scenarios} valueStyle={{ fontSize: 14 }} /></Col>
              <Col span={4}><Statistic title="步数" value={scheme.n_steps} suffix="月" valueStyle={{ fontSize: 14 }} /></Col>
              <Col span={2}><Statistic title="运行数" value={runs.length} valueStyle={{ fontSize: 14 }} /></Col>
            </Row>
          }
          type="info"
        />
        {scheme.description && <div style={{ marginTop: 8, color: '#666' }}>📝 {scheme.description}</div>}
      </Card>

      {/* 3 步执行卡片 */}
      <Row gutter={12}>
        <Col span={8}>
          <Card size="small" title={<Space><ClusterOutlined />1️⃣ PCA 拟合</Space>}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button type="primary" icon={<ThunderboltOutlined />}
                      onClick={handleFitPca} loading={actionLoading === 'pca'} block>
                跑 PCA（{scheme.n_factors} 因子）
              </Button>
              {lastPcaRun && (
                <PcaResultPanel input={lastPcaRun.output || {}} compact />
              )}
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title={<Space><LineChartOutlined />2️⃣ HJM 建模</Space>}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button type="primary" icon={<RocketOutlined />}
                      onClick={handleGenerateHjm} loading={actionLoading === 'hjm'}
                      disabled={!canHjm} block>
                生成 HJM（{scheme.n_scenarios} × {scheme.n_steps} × {scheme.maturities_months?.length || 13}）
              </Button>
              {!canHjm && <Alert message="请先跑 PCA" type="warning" showIcon />}
              {lastHjmRun && (
                <HjmResultPanel input={lastHjmRun.output || {}} compact />
              )}
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title={<Space><DownloadOutlined />3️⃣ 情景集</Space>}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button type="primary" icon={<RocketOutlined />}
                      onClick={handleGenerateScenario} loading={actionLoading === 'scenario'}
                      disabled={!canScenario} block>
                生成情景集（.npz）
              </Button>
              {!canScenario && <Alert message="请先生成 HJM" type="warning" showIcon />}
              {lastScenarioRun && (
                <ScenarioResultPanel run={lastScenarioRun} compact />
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 一键三步 */}
      <Card size="small" style={{ marginTop: 12 }} title="🚀 一键三步（演示）">
        <Space>
          <Button type="primary" size="large" icon={<RocketOutlined />}
                  onClick={handleRunAll} loading={actionLoading === 'all'}>
            🚀 一步跑完 PCA + HJM + 情景集
          </Button>
          <span style={{ color: '#999' }}>
            默认使用方案配置的因子数/情景数/步数（{scheme.n_factors}F / {scheme.n_scenarios}S / {scheme.n_steps}T）
          </span>
        </Space>
      </Card>

      {/* Tabs: 本方案运行历史 + 情景集列表 */}
      <Card size="small" style={{ marginTop: 12 }}>
        <Tabs
          items={[
            {
              key: 'runs',
              label: <Space><HistoryOutlined />运行历史 ({runs.length})</Space>,
              children: (
                <Table
                  rowKey="id"
                  dataSource={runs}
                  columns={runColumns}
                  size="small"
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 800 }}
                  locale={{ emptyText: <Empty description="暂无运行记录" /> }}
                />
              ),
            },
            {
              key: 'scenarios',
              label: <Space><DownloadOutlined />情景集 ({scenarios.length})</Space>,
              children: (
                <Table
                  rowKey="id"
                  dataSource={scenarios}
                  size="small"
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { title: '#', dataIndex: 'id', width: 60 },
                    { title: 'Scenario Code', dataIndex: 'scenario_code', width: 180,
                      render: (v: string) => <code style={{ fontSize: 12 }}>{v}</code> },
                    { title: '情景数', dataIndex: 'n_scenarios', width: 100 },
                    { title: '步数', dataIndex: 'n_steps', width: 100 },
                    { title: '期限数', dataIndex: 'n_maturities', width: 100 },
                    { title: '大小', dataIndex: 'file_size_bytes', width: 110,
                      render: (v?: number) => v ? `${(v/1024).toFixed(1)} KB` : '-' },
                    { title: '时间', dataIndex: 'created_at', width: 160,
                      render: (v?: string) => v ? v.replace('T', ' ').slice(0, 19) : '-' },
                    { title: '下载', width: 100,
                      render: (_: any, row: EsgScenario) => (
                        <Button size="small" icon={<DownloadOutlined />}
                                onClick={() => handleDownload(row)}>下载 .npz</Button>
                      ),
                    },
                  ]}
                  locale={{ emptyText: <Empty description="暂无情景集" /> }}
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default EsgSchemeDetail
import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Spin, Empty } from 'antd'
import ReactECharts from 'echarts-for-react'
import { dashboardApi } from '../api'

const Dashboard: React.FC = () => {
  const [data, setData] = useState<any>(null)
  const [trend, setTrend] = useState<any>({ items: [] })
  const [dist, setDist] = useState<any>({ items: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([dashboardApi.overview(), dashboardApi.taskTrend(14), dashboardApi.currencyDistribution()])
      .then(([o, t, d]) => { setData(o); setTrend(t); setDist(d) })
      .finally(() => setLoading(false))
  }, [])

  if (loading || !data) return <div style={{ textAlign: 'center', padding: 80 }}><Spin tip="加载中..." /></div>

  const trendOpt = {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: (trend.items || []).map((i: any) => i.date.slice(5)) },
    yAxis: { type: 'value', name: '任务数' },
    series: [{
      data: (trend.items || []).map((i: any) => i.count),
      type: 'line', smooth: true, areaStyle: { color: 'rgba(102,126,234,0.25)' },
      lineStyle: { color: '#667eea', width: 2.5 },
      itemStyle: { color: '#764ba2' },
    }],
  }

  const distOpt = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, type: 'scroll' },
    series: [{
      type: 'pie', radius: ['45%', '70%'],
      data: (dist.items || []).map((i: any) => ({ name: i.currency, value: i.amount })),
      label: { formatter: '{b}\n{d}%' },
      color: ['#667eea', '#764ba2', '#f59e0b', '#52c41a', '#1890ff', '#eb2f96', '#13c2c2', '#fa8c16'],
    }],
  }

  return (
    <div>
      <div className="page-title">
        <span className="page-title-icon" />
        PRCP 组算平台 · 总览
      </div>

      <Row gutter={[16, 16]}>
        {data.kpi.map((k: any, i: number) => (
          <Col xs={24} sm={12} lg={6} key={i}>
            <Card className="kpi-card">
              <div className="kpi-label">{k.label}</div>
              <div className="kpi-value" style={{ color: k.color }}>{k.value} <span style={{ fontSize: 13, color: '#999' }}>{k.unit}</span></div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={14}>
          <Card title="近 14 天组算任务趋势">
            {trend.items?.length ? <ReactECharts option={trendOpt} style={{ height: 320 }} /> : <Empty />}
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="币种头寸分布">
            {dist.items?.length ? <ReactECharts option={distOpt} style={{ height: 320 }} /> : <Empty description="暂无数据" />}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
/** PRCP ESG · 曲线还原页
 *
 * 入口：/esg/curve
 * 功能：选数据源 + 选日期 + 自定义期限数组 → 调 Svensson 还原接口 → ECharts 画曲线
 */
import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Form, Select, Button, Row, Col, Space, Tag, DatePicker, Empty,
  Statistic, message, Spin, Table,
} from 'antd'
import { ReloadOutlined, LineChartOutlined, FundOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import dayjs, { Dayjs } from 'dayjs'
import {
  yieldCurveApi, ESG_SOURCE_OPTIONS, YieldCurvePoint,
} from '../api/esg'

const DEFAULT_TENORS = [1, 3, 6, 12, 24, 36, 48, 60, 84, 120, 180, 240, 360]

const EsgCurve: React.FC = () => {
  const [sources, setSources] = useState<{ source: string; count: number }[]>([])
  const [source, setSource] = useState<string>('ECB')
  const [curveDate, setCurveDate] = useState<Dayjs>(dayjs('2024-06-03'))
  const [tenors, setTenors] = useState<number[]>(DEFAULT_TENORS)
  const [ratesPct, setRatesPct] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  const [curvePoint, setCurvePoint] = useState<YieldCurvePoint | null>(null)

  // 加载 4 源统计：保留默认 ECB，仅在当前 source 不存在时回退到第一项
  useEffect(() => {
    yieldCurveApi.sources().then((r) => {
      const items = r.items || []
      setSources(items)
      if (items.length > 0 && !items.some((x) => x.source === source)) {
        // 当前 source 在新数据里不存在 → 选第一条可用的（让用户能看到至少一个数据）
        setSource(items[0].source)
      }
    }).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 计算曲线
  const handleCalculate = async () => {
    if (!curveDate) {
      message.warning('请选择日期')
      return
    }
    setLoading(true)
    try {
      const dateStr = curveDate.format('YYYY-MM-DD')
      // 同时获取 Svensson 6 参数 + 还原
      const r = await yieldCurveApi.rates(dateStr, { tenors, source })
      if (!r.items?.length) {
        message.warning(`${dateStr} / ${source} 没有曲线数据`)
        return
      }
      setRatesPct(r.items[0].rates_pct)
      // 顺便取 Svensson 6 参数展示
      const pt = await yieldCurveApi.get(dateStr, source)
      setCurvePoint(pt.items?.[0] || null)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '曲线还原失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    handleCalculate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ECharts 折线图
  const chartOption = useMemo(() => ({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = params[0]
        return `${p.axisValue}<br/><b>${p.value.toFixed(3)}%</b>`
      },
    },
    grid: { left: 50, right: 30, top: 30, bottom: 40 },
    xAxis: {
      type: 'category',
      data: tenors.map((t) => `${t}M`),
      name: '期限（月）',
      nameLocation: 'middle',
      nameGap: 25,
    },
    yAxis: {
      type: 'value',
      name: '利率 (%)',
      axisLabel: { formatter: (v: number) => `${v.toFixed(2)}%` },
    },
    series: [{
      type: 'line',
      data: ratesPct,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { width: 3, color: '#13c2c2' },
      itemStyle: { color: '#13c2c2' },
      areaStyle: { color: 'rgba(19,194,82,0.1)' },
      markPoint: {
        symbol: 'pin',
        data: [
          { type: 'max', name: '最高' },
          { type: 'min', name: '最低' },
        ],
      },
    }],
  }), [tenors, ratesPct])

  const shortRate = ratesPct[0]
  const longRate = ratesPct[ratesPct.length - 1]
  const slope = shortRate != null && longRate != null ? longRate - shortRate : null

  return (
    <div className="page-container">
      <Card size="small" style={{ marginBottom: 12, background: 'linear-gradient(135deg, #f0f5ff 0%, #e6fffb 100%)' }}>
        <Row gutter={16}>
          <Col span={4}>
            <Statistic title="4 源总数"
              value={sources.reduce((a, s) => a + s.count, 0)}
              prefix={<FundOutlined style={{ color: '#722ed1' }} />}
              valueStyle={{ fontSize: 14 }} />
          </Col>
          {sources.map((s) => {
            const c = ESG_SOURCE_OPTIONS.find((x) => x.value === s.source)
            return (
              <Col span={4} key={s.source}>
                <Statistic
                  title={<Tag color={c?.color}>{c?.label || s.source}</Tag>}
                  value={s.count}
                  valueStyle={{ fontSize: 14 }}
                />
              </Col>
            )
          })}
        </Row>
      </Card>

      <Card size="small" title={<Space><LineChartOutlined />Svensson 曲线还原</Space>}>
        <Form layout="inline" style={{ marginBottom: 12 }}>
          <Form.Item label="数据源">
            <Select
              value={source}
              onChange={setSource}
              style={{ width: 180 }}
              options={ESG_SOURCE_OPTIONS.map((x) => ({ value: x.value, label: x.label }))}
            />
          </Form.Item>
          <Form.Item label="日期">
            <DatePicker
              value={curveDate}
              onChange={setCurveDate}
              format="YYYY-MM-DD"
            />
          </Form.Item>
          <Form.Item label="期限（自定义）">
            <Select
              mode="multiple"
              value={tenors}
              onChange={(v) => setTenors((v as number[]).sort((a, b) => a - b))}
              style={{ width: 320 }}
              options={[1, 3, 6, 12, 24, 36, 48, 60, 84, 120, 180, 240, 360].map((m) => ({
                value: m, label: `${m}M`,
              }))}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<ReloadOutlined />} loading={loading} onClick={handleCalculate}>
              计算还原
            </Button>
          </Form.Item>
        </Form>

        <Spin spinning={loading}>
          {ratesPct.length === 0 ? (
            <Empty description="该日期没有曲线数据，请选其他日期" />
          ) : (
            <>
              <Row gutter={16} style={{ marginBottom: 12 }}>
                <Col span={6}>
                  <Statistic title="短端利率 (1M)"
                    value={shortRate != null ? (shortRate as number).toFixed(3) : '-'}
                    suffix="%" valueStyle={{ color: '#1890ff' }} />
                </Col>
                <Col span={6}>
                  <Statistic title="长端利率 (30Y)"
                    value={longRate != null ? (longRate as number).toFixed(3) : '-'}
                    suffix="%" valueStyle={{ color: '#fa541c' }} />
                </Col>
                <Col span={6}>
                  <Statistic title="期限溢价（slope）"
                    value={slope != null ? (slope as number).toFixed(3) : '-'}
                    suffix="%" valueStyle={{ color: slope && slope > 0 ? '#52c41a' : '#fa8c16' }} />
                </Col>
                <Col span={6}>
                  <Statistic title="期限点数"
                    value={tenors.length}
                    valueStyle={{ color: '#722ed1' }} />
                </Col>
              </Row>

              <ReactECharts option={chartOption} style={{ height: 380 }} />

              {curvePoint && (
                <Card size="small" style={{ marginTop: 12 }} title="📊 Svensson 6 参数">
                  <Row gutter={16}>
                    <Col span={4}><Statistic title="θ₀ 水平" value={curvePoint.theta0.toFixed(4)} valueStyle={{ fontSize: 13 }} /></Col>
                    <Col span={4}><Statistic title="θ₁ 斜率" value={curvePoint.theta1.toFixed(4)} valueStyle={{ fontSize: 13 }} /></Col>
                    <Col span={4}><Statistic title="θ₂ 第一曲度" value={curvePoint.theta2.toFixed(4)} valueStyle={{ fontSize: 13 }} /></Col>
                    <Col span={4}><Statistic title="θ₃ 第二曲度" value={curvePoint.theta3.toFixed(4)} valueStyle={{ fontSize: 13 }} /></Col>
                    <Col span={4}><Statistic title="λ₁ 衰减1" value={curvePoint.lambda1.toFixed(4)} valueStyle={{ fontSize: 13 }} /></Col>
                    <Col span={4}><Statistic title="λ₂ 衰减2" value={curvePoint.lambda2.toFixed(4)} valueStyle={{ fontSize: 13 }} /></Col>
                  </Row>
                </Card>
              )}

              <Card size="small" style={{ marginTop: 12 }} title={`📋 ${tenors.length} 期限利率表`}>
                <Table
                  rowKey={(_, i) => String(i)}
                  size="small"
                  pagination={false}
                  dataSource={tenors.map((t, i) => ({ key: t, rate: ratesPct[i] }))}
                  columns={[
                    { title: '期限（月）', dataIndex: 'key', width: 120 },
                    { title: '利率（%）', dataIndex: 'rate', align: 'right' as const,
                      render: (v: number) => v?.toFixed(4) },
                  ]}
                />
              </Card>
            </>
          )}
        </Spin>
      </Card>
    </div>
  )
}

export default EsgCurve
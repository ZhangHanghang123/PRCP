/** PRCP ESG · HJM 结果可视化 Panel
 *
 * 5 子 Tab（compact 模式只显示总览）：
 *   1. 总览：4 KPI（情景数/步数/期限数/短端终值）
 *   2. p50 路径（按期限分线多线图）
 *   3. 包络图（p10/p50/p90 三色带）
 *   4. 终期分布（均值柱 + ±1σ 折线 + min-max 范围）
 *   5. 样本路径（前 5 条多线）
 */
import React, { useMemo } from 'react'
import { Row, Col, Statistic, Tabs } from 'antd'
import ReactECharts from 'echarts-for-react'
import { DEFAULT_MATURITIES_MONTHS } from '../../api/esg'

interface Props {
  input: {
    paths_shape?: number[]
    n_scenarios?: number
    n_steps?: number
    n_maturities?: number
    maturities_months?: number[]
    p10?: number[][]   // (n_steps, n_maturities)
    p50?: number[][]
    p90?: number[][]
    final_distribution_mean?: number[]
    final_distribution_std?: number[]
    final_distribution_min?: number[]
    final_distribution_max?: number[]
    vol_per_maturity?: number[]
    paths_min?: number
    paths_max?: number
    volatility_decaying?: boolean
    validation_warnings?: string[]
  }
  compact?: boolean
}

const HjmResultPanel: React.FC<Props> = ({ input, compact = false }) => {
  const p10 = input.p10 || []
  const p50 = input.p50 || []
  const p90 = input.p90 || []
  const maturities = input.maturities_months || DEFAULT_MATURITIES_MONTHS
  const finalMean = input.final_distribution_mean || []
  const finalStd = input.final_distribution_std || []
  const finalMin = input.final_distribution_min || []
  const finalMax = input.final_distribution_max || []

  const stepLabels = useMemo(() => {
    const n = p50.length
    return Array.from({ length: n }, (_, i) => `M${i+1}`)
  }, [p50.length])

  // p50 多线图（每条期限一条线）
  const p50LinesOption = useMemo(() => {
    if (p50.length === 0) return {}
    const nSteps = p50.length
    const series = maturities.map((m, j) => ({
      name: `${m}M`,
      type: 'line',
      data: Array.from({ length: nSteps }, (_, t) => +(p50[t]?.[j] || 0).toFixed(3)),
      smooth: false,
      showSymbol: false,
    }))
    return {
      tooltip: { trigger: 'axis' },
      legend: { type: 'scroll', top: 0, data: maturities.map((m) => `${m}M`) },
      grid: { left: 50, right: 30, top: 50, containLabel: true },
      xAxis: { type: 'category', data: stepLabels, name: '时间步' },
      yAxis: { type: 'value', name: '利率 (%)' },
      series,
    }
  }, [p50, maturities, stepLabels])

  // 包络图（p10/p50/p90 三色带） — 选短端展示
  const envelopeOption = useMemo(() => {
    const shortIdx = 0  // 短端 m=1
    if (p10.length === 0) return {}
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['p10', 'p50', 'p90'] },
      grid: { left: 50, right: 30, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: stepLabels },
      yAxis: { type: 'value', name: `${maturities[shortIdx]}M 利率 (%)` },
      series: [
        { name: 'p10', type: 'line', data: p10.map((r) => +(r[shortIdx] || 0).toFixed(3)),
          lineStyle: { color: '#1890ff', opacity: 0.4 },
          areaStyle: { color: 'rgba(24,144,255,0.2)' } },
        { name: 'p50', type: 'line', data: p50.map((r) => +(r[shortIdx] || 0).toFixed(3)),
          itemStyle: { color: '#1890ff' }, lineStyle: { width: 3 } },
        { name: 'p90', type: 'line', data: p90.map((r) => +(r[shortIdx] || 0).toFixed(3)),
          lineStyle: { color: '#1890ff', opacity: 0.4 },
          areaStyle: { color: 'rgba(24,144,255,0.2)' } },
      ],
    }
  }, [p10, p50, p90, maturities, stepLabels])

  // 终期分布柱状
  const finalBarOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['均值', '+1σ', '-1σ', 'min-max'] },
    grid: { left: 50, right: 30, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: maturities.map((m) => `${m}M`) },
    yAxis: { type: 'value', name: '利率 (%)' },
    series: [
      { name: '均值', type: 'bar', data: finalMean.map((v) => +v.toFixed(3)),
        itemStyle: { color: '#1890ff' } },
      { name: '+1σ', type: 'line', data: finalMean.map((v, i) => +(v + (finalStd[i] || 0)).toFixed(3)),
        itemStyle: { color: '#fa541c' } },
      { name: '-1σ', type: 'line', data: finalMean.map((v, i) => +(v - (finalStd[i] || 0)).toFixed(3)),
        itemStyle: { color: '#52c41a' } },
      { name: 'min-max', type: 'line',
        data: maturities.map((_, i) => [+(finalMin[i] || 0).toFixed(3), +(finalMax[i] || 0).toFixed(3)]),
        itemStyle: { color: '#bfbfbf' }, lineStyle: { type: 'dashed' } },
    ],
  }), [finalMean, finalStd, finalMin, finalMax, maturities])

  if (compact) {
    return (
      <div style={{ marginTop: 12 }}>
        <Row gutter={8}>
          <Col span={8}>
            <Statistic title="情景数" value={input.n_scenarios || 0} valueStyle={{ fontSize: 14 }} />
          </Col>
          <Col span={8}>
            <Statistic title="步数" value={input.n_steps || 0} valueStyle={{ fontSize: 14 }} />
          </Col>
          <Col span={8}>
            <Statistic
              title="波动率递减"
              value={input.volatility_decaying ? '✓ 满足' : '✗ 违反'}
              valueStyle={{ fontSize: 14, color: input.volatility_decaying ? '#52c41a' : '#f5222d' }}
            />
          </Col>
        </Row>
        <Row gutter={8} style={{ marginTop: 8 }}>
          <Col span={12}>
            <Statistic title="利率范围（最低）"
              value={input.paths_min != null ? (input.paths_min as number).toFixed(2) : '-'}
              suffix="%" valueStyle={{ fontSize: 14, color: '#fa541c' }} />
          </Col>
          <Col span={12}>
            <Statistic title="利率范围（最高）"
              value={input.paths_max != null ? (input.paths_max as number).toFixed(2) : '-'}
              suffix="%" valueStyle={{ fontSize: 14, color: '#1890ff' }} />
          </Col>
        </Row>
        {(input.validation_warnings?.length ?? 0) > 0 && (
          <div style={{ marginTop: 4, fontSize: 12, color: '#fa8c16' }}>
            ⚠️ {input.validation_warnings!.join('; ')}
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Statistic title="情景数" value={input.n_scenarios || 0} valueStyle={{ color: '#722ed1' }} />
        </Col>
        <Col span={6}>
          <Statistic title="步数" value={input.n_steps || 0} valueStyle={{ color: '#13c2c2' }} />
        </Col>
        <Col span={6}>
          <Statistic title="期限数" value={input.n_maturities || 0} valueStyle={{ color: '#1890ff' }} />
        </Col>
        <Col span={6}>
          <Statistic title="短端终值" value={finalMean[0] != null ? (finalMean[0] as number).toFixed(3) : '-'}
            suffix="%" valueStyle={{ color: '#fa8c16' }} />
        </Col>
      </Row>

      <Tabs
        items={[
          { key: 'p50', label: 'p50 多线',
            children: <ReactECharts option={p50LinesOption} style={{ height: 360 }} /> },
          { key: 'envelope', label: 'p10/p50/p90 包络',
            children: <ReactECharts option={envelopeOption} style={{ height: 360 }} /> },
          { key: 'final', label: '终期分布',
            children: <ReactECharts option={finalBarOption} style={{ height: 360 }} /> },
        ]}
      />
    </div>
  )
}

export default HjmResultPanel
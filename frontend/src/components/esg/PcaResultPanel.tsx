/** PRCP ESG · PCA 结果可视化 Panel
 *
 * 6 子 Tab（compact 模式只显示总览+累计方差）：
 *   1. 总览：4 KPI（样本数 / 因子数 / 期限数 / 3 因子累计方差）
 *   2. 累计方差柱状图（青）
 *   3. 单因子方差贡献柱状图（紫）
 *   4. 因子载荷热力图（PC × 期限）
 *   5. 特征值衰减（log scale 折线）
 *   6. 载荷矩阵数据表
 */
import React, { useMemo } from 'react'
import { Row, Col, Statistic, Tabs, Table, Empty } from 'antd'
import ReactECharts from 'echarts-for-react'
import { DEFAULT_MATURITIES_MONTHS } from '../../api/esg'

interface Props {
  /** backend prcp_esg_run.output_json 解析后对象 */
  input: {
    n_samples?: number
    n_maturities?: number
    n_factors?: number
    maturities_months?: number[]
    eigenvalues?: number[]
    explained_variance_ratio?: number[]
    cumulative_variance_ratio?: number[]
    cumulative_variance_3f_pct?: number | null
    factor_loadings?: number[][]  // (n_maturities, n_factors)
    pca_fitted?: boolean
  }
  /** 紧凑模式（方案详情右侧卡片）只展示 4 KPI + 累计方差柱状 */
  compact?: boolean
}

const PcaResultPanel: React.FC<Props> = ({ input, compact = false }) => {
  const cum3 = input.cumulative_variance_3f_pct
  const evRatio = input.explained_variance_ratio || []
  const cumRatio = input.cumulative_variance_ratio || []
  const factorLoadings = input.factor_loadings || []
  const eigenvalues = input.eigenvalues || []
  const maturities = input.maturities_months || DEFAULT_MATURITIES_MONTHS

  // 累计方差柱状图
  const cumulativeBarOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: Array.from({ length: cumRatio.length }, (_, i) => `PC${i+1}`) },
    yAxis: { type: 'value', name: '累计方差 (%)', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{
      type: 'bar',
      data: cumRatio.map((x) => +(x * 100).toFixed(2)),
      itemStyle: { color: '#13c2c2' },
      label: { show: true, position: 'top', formatter: '{c}%', fontSize: 10 },
    }],
  }), [cumRatio])

  // 单因子方差贡献
  const varianceBarOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: Array.from({ length: evRatio.length }, (_, i) => `PC${i+1}`) },
    yAxis: { type: 'value', name: '方差贡献 (%)', axisLabel: { formatter: '{value}%' } },
    series: [{
      type: 'bar',
      data: evRatio.map((x) => +(x * 100).toFixed(2)),
      itemStyle: { color: '#722ed1' },
      label: { show: true, position: 'top', formatter: '{c}%', fontSize: 10 },
    }],
  }), [evRatio])

  // 因子载荷热力图（PC × 期限）
  const heatmapData = useMemo(() => {
    const data: [number, number, number][] = []
    for (let i = 0; i < factorLoadings.length; i++) {
      for (let j = 0; j < factorLoadings[i].length; j++) {
        data.push([j, i, +factorLoadings[i][j].toFixed(4)])
      }
    }
    return data
  }, [factorLoadings])

  const heatmapOption = useMemo(() => ({
    tooltip: { position: 'top' },
    grid: { left: 60, right: 30, top: 30, bottom: 60 },
    xAxis: {
      type: 'category',
      data: Array.from({ length: factorLoadings[0]?.length || 0 }, (_, i) => `PC${i+1}`),
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: maturities.map((m) => `${m}M`),
      splitArea: { show: true },
    },
    visualMap: {
      min: -1, max: 1, calculable: true, orient: 'horizontal',
      left: 'center', bottom: 10,
      inRange: { color: ['#d4380d', '#fff', '#389e0d'] },
    },
    series: [{
      name: '因子载荷', type: 'heatmap', data: heatmapData,
      label: { show: true, fontSize: 9 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  }), [heatmapData, maturities])

  // 特征值衰减（log scale）
  const eigenDecayOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: Array.from({ length: eigenvalues.length }, (_, i) => `PC${i+1}`) },
    yAxis: { type: 'log', name: '特征值 (log)' },
    series: [{
      type: 'line',
      data: eigenvalues.map((x) => +x.toFixed(8)),
      itemStyle: { color: '#fa8c16' },
      smooth: true,
      symbol: 'circle', symbolSize: 8,
    }],
  }), [eigenvalues])

  // 紧凑模式：只渲染 KPI + 累计方差柱状图
  if (compact) {
    return (
      <div style={{ marginTop: 12 }}>
        <Row gutter={8}>
          <Col span={12}>
            <Statistic title="样本数" value={input.n_samples || 0} valueStyle={{ fontSize: 14 }} />
          </Col>
          <Col span={12}>
            <Statistic
              title="3 因子累计方差"
              value={cum3 != null ? (cum3 * 100).toFixed(2) : '-'}
              suffix="%"
              valueStyle={{ fontSize: 14, color: cum3 != null && cum3 >= 0.95 ? '#52c41a' : '#fa8c16' }}
            />
          </Col>
        </Row>
        {cumRatio.length > 0 && (
          <ReactECharts option={cumulativeBarOption} style={{ height: 140, marginTop: 8 }} />
        )}
      </div>
    )
  }

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Statistic title="样本数" value={input.n_samples || 0} valueStyle={{ color: '#1890ff' }} />
        </Col>
        <Col span={6}>
          <Statistic title="因子数" value={input.n_factors || 0} valueStyle={{ color: '#722ed1' }} />
        </Col>
        <Col span={6}>
          <Statistic title="期限数" value={input.n_maturities || 0} valueStyle={{ color: '#13c2c2' }} />
        </Col>
        <Col span={6}>
          <Statistic
            title="3 因子累计方差"
            value={cum3 != null ? (cum3 * 100).toFixed(2) : '-'}
            suffix="%"
            valueStyle={{ color: cum3 != null && cum3 >= 0.95 ? '#52c41a' : '#fa8c16' }}
          />
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: 'cumulative', label: '累计方差',
            children: <ReactECharts option={cumulativeBarOption} style={{ height: 320 }} />,
          },
          {
            key: 'variance', label: '单因子方差',
            children: <ReactECharts option={varianceBarOption} style={{ height: 320 }} />,
          },
          {
            key: 'loadings', label: '因子载荷',
            children: <ReactECharts option={heatmapOption} style={{ height: 360 }} />,
          },
          {
            key: 'eigenvalues', label: '特征值衰减',
            children: <ReactECharts option={eigenDecayOption} style={{ height: 320 }} />,
          },
          {
            key: 'matrix', label: '载荷矩阵',
            children: (
              factorLoadings.length === 0 ? <Empty /> : (
<Table
                    rowKey={(_, i) => `pc${i}`}
                    size="small"
                  pagination={false}
                  scroll={{ x: 'max-content' }}
                  dataSource={factorLoadings.map((row, i) => ({
                    key: i,
                    maturity: `${maturities[i]}M`,
                    ...Object.fromEntries(row.map((v, j) => [`pc${j+1}`, +v.toFixed(4)])),
                  }))}
                  columns={[
                    { title: '期限', dataIndex: 'maturity', fixed: 'left', width: 100 },
                    ...Array.from({ length: factorLoadings[0].length }, (_, j) => ({
                      title: `PC${j+1}`,
                      dataIndex: `pc${j+1}`,
                      width: 90,
                      align: 'right' as const,
                    })),
                  ]}
                />
              )
            ),
          },
        ]}
      />
    </div>
  )
}

export default PcaResultPanel
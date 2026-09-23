<template>
  <div class="dash-page" v-loading="loading">
    <div class="page-header">
      <h2>驾驶舱</h2>
      <p class="desc">账户册 / 报表 / 指标 / 评分规则 总览（ECharts）</p>
      <span class="data-date" v-if="latestDate">最新数据日期：{{ latestDate }}</span>
    </div>

    <!-- 8 KPI 卡片 -->
    <el-row :gutter="14" class="kpi-row">
      <el-col :span="6" v-for="(k, i) in kpis" :key="i">
        <el-card shadow="hover" class="kpi-card" :style="{ borderTop: `3px solid ${k.color}` }">
          <div class="kpi-label">{{ k.label }}</div>
          <div class="kpi-value" :style="{ color: k.color }">{{ formatNum(k.value) }}</div>
          <div class="kpi-unit">{{ k.unit }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 4 个图表 -->
    <el-row :gutter="14" class="chart-row">
      <el-col :span="12">
        <el-card shadow="never" header="📈 指标值录入趋势（近 14 天）">
          <v-chart :options="trendOption" :autoresize="true" style="height:280px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" header="🥧 指标方案定义分布（TOP 8）">
          <v-chart :options="schemeOption" :autoresize="true" style="height:280px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="14" class="chart-row">
      <el-col :span="14">
        <el-card shadow="never" header="🏆 Top10 指标（按当前绝对值）">
          <v-chart :options="topOption" :autoresize="true" style="height:300px" />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" header="📋 指标试算得分排行">
          <el-table :data="scoredList" border stripe size="small" max-height="280">
              <el-table-column type="index" label="排名" width="60" align="center" />
              <el-table-column prop="kpiCode" label="编码" width="100" />
              <el-table-column prop="kpiName" label="指标" />
              <el-table-column prop="score" label="得分" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.score >= 80 ? 'success' : (row.score >= 60 ? 'warning' : 'danger')">
                    {{ row.score }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { dashboardApi } from '@/api/dashboard'
import VChart from 'vue-echarts'
import 'echarts/lib/chart/line'
import 'echarts/lib/chart/pie'
import 'echarts/lib/chart/bar'
import 'echarts/lib/component/tooltip'
import 'echarts/lib/component/legend'
import 'echarts/lib/component/title'

export default {
  name: 'DashboardIndex',
  components: { VChart },
  data() {
    return {
      loading: false,
      kpis: [],
      latestDate: null,
      trend: [],
      schemes: [],
      topKpis: [],
      CITIC_RED: '#C7000B'
    }
  },
  computed: {
    trendOption() {
      return {
        tooltip: { trigger: 'axis' },
        grid: { left: 40, right: 20, top: 20, bottom: 30 },
        xAxis: { type: 'category', data: this.trend.map(t => t.d), axisLabel: { fontSize: 11 } },
        yAxis: { type: 'value' },
        series: [{
          name: '指标值录入', type: 'line', smooth: true,
          data: this.trend.map(t => t.n),
          itemStyle: { color: this.CITIC_RED },
          areaStyle: { color: 'rgba(199, 0, 11, 0.15)' }
        }]
      }
    },
    schemeOption() {
      return {
        tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 个指标 ({d}%)' },
        legend: { orient: 'vertical', right: 10, top: 'middle', textStyle: { fontSize: 11 } },
        series: [{
          name: '指标分布', radius: ['45%', '70%'], center: ['38%', '50%'],
          type: 'pie',
          data: this.schemes.map((s, i) => ({
            name: s.schemeName || s.schemeCode,
            value: s.defCount,
            itemStyle: { color: ['#C7000B', '#A31A1F', '#E84E4E', '#D71B1B', '#C8102E',
                                  '#DC2626', '#991B1B', '#7F1D1D'][i % 8] }
          })),
          label: { formatter: '{b}\n{c}', fontSize: 11 }
        }]
      }
    },
    topOption() {
      const data = this.topKpis.slice(0, 10)
      return {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: 110, right: 30, top: 20, bottom: 30 },
        xAxis: { type: 'value' },
        yAxis: { type: 'category', data: data.map(k => `${k.kpiCode} ${k.kpiName}`), axisLabel: { fontSize: 11 } },
        series: [{
          name: '当前值', type: 'bar',
          data: data.map((k, i) => ({
            value: k.currentValue,
            itemStyle: {
              color: i === 0 ? '#C7000B' : (i === 1 ? '#A31A1F' : (i === 2 ? '#E84E4E' : '#D71B1B'))
            }
          })),
          label: { show: true, position: 'right', formatter: (p: any) => Number(p.value).toFixed(2) }
        }]
      }
    },
    scoredList() {
      return this.topKpis.filter(k => k.score != null).slice(0, 10)
    }
  },
  async mounted() {
    this.loading = true
    try {
      const [ov, trend, dist, top]: any[] = await Promise.all([
        dashboardApi.overview(),
        dashboardApi.kpiTrend(14),
        dashboardApi.schemeDistribution(),
        dashboardApi.topKpis()
      ])
      this.kpis = ov.kpi || []
      this.latestDate = ov.latest_data_date
      this.trend = trend.items || []
      this.schemes = dist.items || []
      this.topKpis = top.items || []
    } finally { this.loading = false }
  },
  methods: {
    formatNum(v: any) {
      if (v == null) return 0
      const n = Number(v)
      if (Number.isNaN(n)) return v
      return n.toLocaleString('zh-CN')
    }
  }
}
</script>

<style scoped>
.dash-page { padding: 0; }
.page-header { background:#fff; padding:16px 24px; margin-bottom:16px; border-bottom:1px solid #f0f0f0; position:relative; }
.page-header h2 { margin:0; }
.page-header .desc { color:#999; font-size:13px; margin:4px 0 0; }
.data-date { position:absolute; right:24px; top:24px; color:#C7000B; font-size:13px; }
.kpi-row { margin:0 16px 14px; }
.kpi-card { text-align:center; padding:6px 0; background:#fff; }
.kpi-label { color:#888; font-size:13px; }
.kpi-value { font-size:30px; font-weight:bold; margin:4px 0; line-height:1.1; }
.kpi-unit { color:#aaa; font-size:12px; }
.chart-row { margin:0 16px 14px; }
.echarts { width:100%; }
</style>
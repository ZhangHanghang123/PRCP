<template>
  <div class="page-wrap">
    <el-card shadow="never" class="header-card">
      <div class="page-title">
        <i class="el-icon-tickets" style="color: var(--citic-red)"></i>
        <span>反算指标结果表</span>
        <span class="sub">12 个月 × 6 期（current + y1~y5）反算结果</span>
      </div>
    </el-card>

    <el-card shadow="never" class="filter-card">
      <el-row :gutter="12">
        <el-col :span="6">
          <el-select v-model="flt.schemeCode" placeholder="选择方案" filterable clearable style="width:100%" @change="loadData">
            <el-option v-for="s in schemes" :key="s" :value="s" :label="s" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="flt.metricCode" placeholder="选择指标" filterable clearable style="width:100%" @change="loadData">
            <el-option v-for="m in metrics" :key="m.metricCode" :value="m.metricCode" :label="`${m.metricCode} | ${m.metricLabel}`" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-date-picker v-model="flt.range" range="date" type="monthrange" range-separator="至" start-placeholder="起始月" end-placeholder="截止月" value-format="yyyy-MM-dd" style="width:100%" @change="onRangeChange" />
        </el-col>
        <el-col :span="7">
          <el-button type="primary" icon="el-icon-search" @click="loadData">查询</el-button>
          <el-button icon="el-icon-refresh-left" @click="onReset">重置</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="mt-12">
      <div class="info-bar">
        <el-tag size="medium" type="info">{{ flt.schemeCode || '全部' }}</el-tag>
        <el-tag size="medium" effect="plain">{{ flt.metricCode || '全部指标' }}</el-tag>
        <el-tag size="medium" type="success">{{ totalRows }} 行 × {{ dates.length }} 月</el-tag>
        <el-tag size="medium" type="warning">每个单元格 = 6 期（current+y1..y5）</el-tag>
      </div>
      <el-table :data="rows" border stripe v-loading="loading" :height="600">
        <el-table-column type="index" label="#" width="50" fixed />
        <el-table-column prop="nodeCode" label="节点编码" width="100" fixed />
        <el-table-column prop="nodeName" label="节点名称" width="160" fixed />
        <el-table-column label="指标" width="160" fixed>
          <template slot-scope="s">
            <el-tag :color="getColor(s.row.metricCode)" effect="dark" size="small">{{ s.row.metricCode }}</el-tag>
            <span style="margin-left:6px">{{ s.row.metricLabel }}</span>
          </template>
        </el-table-column>
        <el-table-column label="单位" width="70" fixed>
          <template slot-scope="s"><span class="unit-tag">{{ s.row.unit }}</span></template>
        </el-table-column>
        <el-table-column v-for="d in dates" :key="d" :label="d" min-width="220">
          <template slot-scope="s">
            <div class="cell-block">
              <div class="cell-row"><span class="period">当期</span><span class="val current">{{ fmt(getCell(s.row, d, 'currentValue')) }}</span></div>
              <div class="cell-row"><span class="period">Y1</span><span class="val">{{ fmt(getCell(s.row, d, 'y1Value')) }}</span></div>
              <div class="cell-row"><span class="period">Y2</span><span class="val">{{ fmt(getCell(s.row, d, 'y2Value')) }}</span></div>
              <div class="cell-row"><span class="period">Y3</span><span class="val">{{ fmt(getCell(s.row, d, 'y3Value')) }}</span></div>
              <div class="cell-row"><span class="period">Y4</span><span class="val">{{ fmt(getCell(s.row, d, 'y4Value')) }}</span></div>
              <div class="cell-row"><span class="period">Y5</span><span class="val">{{ fmt(getCell(s.row, d, 'y5Value')) }}</span></div>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { reverseMetricTableApi } from '@/api/mc'

export default {
  data() {
    return {
      schemes: [],
      metrics: [],
      dates: [],
      rows: [],
      totalRows: 0,
      flt: { schemeCode: 'ZXCOA_V1', metricCode: '', range: [] },
      loading: false
    }
  },
  async mounted() {
    await this.loadOptions()
    this.loadData()
  },
  methods: {
    fmt(v) { if (v === null || v === undefined) return '-'; const n = Number(v); return isNaN(n) ? '-' : n.toFixed(4) },
    getColor(code) {
      const colors = { ROE: '#C7000B', ROA: '#D71B1B', NIM: '#E84E4E', NCO: '#F59191', CIR: '#A31A1F' }
      return colors[code] || '#C7000B'
    },
    getCell(row, date, key) {
      const cell = (row.cells || []).find(c => c.dataDate === date || String(c.dataDate).slice(0, 7) === date.slice(0, 7))
      return cell ? cell[key] : null
    },
    async loadOptions() {
      const opt = await reverseMetricTableApi.options()
      this.schemes = opt.schemes || []
      this.metrics = opt.metrics || []
    },
    onRangeChange(v) {
      this.flt.range = v || []
    },
    async loadData() {
      this.loading = true
      try {
        const params = { schemeCode: this.flt.schemeCode, metricCode: this.flt.metricCode }
        if (this.flt.range && this.flt.range.length === 2) {
          params.fromDate = this.flt.range[0]
          params.toDate = this.flt.range[1]
        }
        const r = await reverseMetricTableApi.query(params)
        this.dates = r.dates || []
        this.rows = r.rows || []
        this.totalRows = r.totalRows || 0
      } finally { this.loading = false }
    },
    onReset() {
      this.flt = { schemeCode: 'ZXCOA_V1', metricCode: '', range: [] }
      this.loadData()
    }
  }
}
</script>

<style scoped>
.page-wrap { padding: 16px; }
.header-card { border-top: 3px solid var(--citic-red); }
.page-title { display: flex; align-items: center; gap: 8px; font-size: 18px; font-weight: 600; }
.page-title .sub { font-size: 12px; color: #999; font-weight: normal; margin-left: 8px; }
.filter-card { margin-top: 12px; }
.mt-12 { margin-top: 12px; }
.info-bar { margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.cell-block { padding: 4px 0; font-size: 12px; line-height: 1.6; }
.cell-row { display: flex; justify-content: space-between; gap: 8px; }
.period { color: #999; min-width: 32px; }
.val { font-family: 'Roboto Mono', Consolas, monospace; color: #666; }
.val.current { color: var(--citic-red); font-weight: 600; }
.unit-tag { font-family: monospace; color: var(--citic-red); font-size: 11px; }
</style>
<template>
  <div class="page-wrap">
    <el-card shadow="never" class="header-card">
      <div class="page-title">
        <i class="el-icon-data-line" style="color: var(--citic-red)"></i>
        <span>指标计量系数维护</span>
        <span class="sub">账户册 × 指标的 × 6 期系数（current + y1~y5）</span>
      </div>
    </el-card>

    <!-- 查询区 -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="12" type="flex" align="middle">
        <el-col :span="5">
          <el-select v-model="flt.schemeId" placeholder="选择账户册方案" filterable style="width:100%" @change="onSchemeChange">
            <el-option v-for="s in schemes" :key="s.id" :label="`${s.schemeCode} | ${s.schemeName}`" :value="s.id" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="flt.nodeCode" placeholder="选择节点" filterable clearable style="width:100%">
            <el-option v-for="n in nodes" :key="n.nodeCode" :label="`${n.nodeCode} | ${n.nodeName}`" :value="n.nodeCode" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="flt.metricCode" placeholder="选择指标" filterable clearable style="width:100%">
            <el-option v-for="m in metrics" :key="m.metricCode" :label="`${m.metricCode} | ${m.metricLabel}`" :value="m.metricCode" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-date-picker v-model="flt.dataDate" type="month" placeholder="数据日期" value-format="yyyy-MM-dd" style="width:100%" />
        </el-col>
        <el-col :span="6">
          <el-button type="primary" icon="el-icon-search" @click="loadList">查询</el-button>
          <el-button icon="el-icon-refresh-left" @click="onReset">重置</el-button>
          <el-button type="danger" icon="el-icon-plus" @click="openDlg()">新增系数</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 表格 -->
    <el-card shadow="never" class="mt-12">
      <el-table :data="rows" border stripe v-loading="loading" :height="600">
        <el-table-column prop="nodeCode" label="节点编码" width="120" fixed />
        <el-table-column prop="nodeName" label="节点名称" width="180" fixed />
        <el-table-column prop="metricCode" label="指标编码" width="120">
          <template slot-scope="s">
            <el-tag :color="getMetricColor(s.row.metricCode)" effect="dark" size="small">{{ s.row.metricCode }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="metricLabel" label="指标名称" width="120" />
        <el-table-column prop="dataDate" label="数据日期" width="120" />
        <el-table-column prop="currentValue" label="当前值" width="120" align="right">
          <template slot-scope="s"><span class="num-cell">{{ fmt(s.row.currentValue) }}</span></template>
        </el-table-column>
        <el-table-column label="Y1" width="100" align="right">
          <template slot-scope="s"><span class="num-cell">{{ fmt(s.row.y1Value) }}</span></template>
        </el-table-column>
        <el-table-column label="Y2" width="100" align="right">
          <template slot-scope="s"><span class="num-cell">{{ fmt(s.row.y2Value) }}</span></template>
        </el-table-column>
        <el-table-column label="Y3" width="100" align="right">
          <template slot-scope="s"><span class="num-cell">{{ fmt(s.row.y3Value) }}</span></template>
        </el-table-column>
        <el-table-column label="Y4" width="100" align="right">
          <template slot-scope="s"><span class="num-cell">{{ fmt(s.row.y4Value) }}</span></template>
        </el-table-column>
        <el-table-column label="Y5" width="100" align="right">
          <template slot-scope="s"><span class="num-cell">{{ fmt(s.row.y5Value) }}</span></template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="description" label="备注" />
        <el-table-column label="操作" width="140" fixed="right">
          <template slot-scope="s">
            <el-button type="text" @click="openDlg(s.row)">编辑</el-button>
            <el-button type="text" style="color:#F56C6C" @click="onDelete(s.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog :title="dlg.id ? '编辑系数' : '新增系数'" :visible.sync="dlg.show" width="640px">
      <el-form :model="dlg" label-width="120px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="方案"><el-input :value="dlg.schemeLabel" disabled /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="节点">
              <el-select v-model="dlg.nodeId" placeholder="选择节点" filterable style="width:100%">
                <el-option v-for="n in nodes" :key="n.id" :label="`${n.nodeCode} | ${n.nodeName}`" :value="n.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="指标">
              <el-select v-model="dlg.metricCode" placeholder="选择指标" style="width:100%">
                <el-option v-for="m in metrics" :key="m.metricCode" :label="`${m.metricCode} | ${m.metricLabel}`" :value="m.metricCode" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据日期">
              <el-date-picker v-model="dlg.dataDate" type="month" placeholder="选择月份" value-format="yyyy-MM-dd" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="当前值"><el-input-number v-model="dlg.currentValue" :precision="6" :step="0.1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="Y1"><el-input-number v-model="dlg.y1Value" :precision="6" :step="0.1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="Y2"><el-input-number v-model="dlg.y2Value" :precision="6" :step="0.1" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="Y3"><el-input-number v-model="dlg.y3Value" :precision="6" :step="0.1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="Y4"><el-input-number v-model="dlg.y4Value" :precision="6" :step="0.1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="Y5"><el-input-number v-model="dlg.y5Value" :precision="6" :step="0.1" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="单位">
          <el-select v-model="dlg.unit" placeholder="选择单位" style="width:200px">
            <el-option label="PERCENT 百分比" value="PERCENT" />
            <el-option label="AMOUNT 金额" value="AMOUNT" />
            <el-option label="RATIO 比率" value="RATIO" />
            <el-option label="BASIS_POINT 基点" value="BASIS_POINT" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="dlg.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="dlg.show=false">取消</el-button>
        <el-button type="primary" @click="onSave">保存</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { metricApi } from '@/api/mc'

export default {
  data() {
    return {
      schemes: [],
      nodes: [],
      metrics: [],
      rows: [],
      flt: { schemeId: null, nodeCode: '', metricCode: '', dataDate: '' },
      loading: false,
      dlg: {
        show: false, id: null, schemeId: null, schemeLabel: '', nodeId: null,
        metricCode: '', dataDate: '', currentValue: 0,
        y1Value: 0, y2Value: 0, y3Value: 0, y4Value: 0, y5Value: 0,
        unit: 'PERCENT', description: ''
      }
    }
  },
  async mounted() {
    await this.loadOptions(null)
  },
  methods: {
    fmt(v) { if (v === null || v === undefined) return '-'; return Number(v).toFixed(4) },
    getMetricColor(code) {
      const colors = { ROE: '#C7000B', ROA: '#D71B1B', NIM: '#E84E4E', NCO: '#F59191', CIR: '#A31A1F' }
      return colors[code] || '#C7000B'
    },
    async loadOptions(schemeId) {
      const opt = await metricApi.options(schemeId)
      this.schemes = opt.schemes || []
      this.nodes = opt.nodes || []
      this.metrics = opt.metrics || []
      // 默认选第一个方案 + 第一个指标
      if (!this.flt.schemeId && this.schemes.length) {
        this.flt.schemeId = this.schemes[0].id
        if (this.schemes[0].id !== schemeId) await this.loadOptions(this.schemes[0].id)
      }
      if (this.schemes.length) this.loadList()
    },
    async onSchemeChange(v) {
      this.flt.nodeCode = ''
      await this.loadOptions(v)
    },
    async loadList() {
      this.loading = true
      try {
        this.rows = await metricApi.list({
          schemeId: this.flt.schemeId,
          nodeCode: this.flt.nodeCode,
          metricCode: this.flt.metricCode,
          dataDate: this.flt.dataDate
        })
      } finally { this.loading = false }
    },
    onReset() {
      this.flt = { schemeId: this.schemes[0] ? this.schemes[0].id : null, nodeCode: '', metricCode: '', dataDate: '' }
      this.loadList()
    },
    openDlg(row) {
      const scheme = this.schemes.find(s => s.id === this.flt.schemeId)
      if (row) {
        this.dlg = {
          show: true, id: row.id, schemeId: row.schemeId, schemeLabel: scheme ? `${scheme.schemeCode} | ${scheme.schemeName}` : '',
          nodeId: row.nodeId, metricCode: row.metricCode, dataDate: row.dataDate,
          currentValue: Number(row.currentValue), y1Value: Number(row.y1Value), y2Value: Number(row.y2Value),
          y3Value: Number(row.y3Value), y4Value: Number(row.y4Value), y5Value: Number(row.y5Value),
          unit: row.unit || 'PERCENT', description: row.description || ''
        }
      } else {
        this.dlg = {
          show: true, id: null, schemeId: this.flt.schemeId, schemeLabel: scheme ? `${scheme.schemeCode} | ${scheme.schemeName}` : '',
          nodeId: null, metricCode: '', dataDate: '',
          currentValue: 0, y1Value: 0, y2Value: 0, y3Value: 0, y4Value: 0, y5Value: 0,
          unit: 'PERCENT', description: ''
        }
      }
    },
    async onSave() {
      try {
        const body = {
          schemeId: this.dlg.schemeId, nodeId: this.dlg.nodeId, metricCode: this.dlg.metricCode,
          dataDate: this.dlg.dataDate, currentValue: this.dlg.currentValue,
          y1Value: this.dlg.y1Value, y2Value: this.dlg.y2Value, y3Value: this.dlg.y3Value,
          y4Value: this.dlg.y4Value, y5Value: this.dlg.y5Value, unit: this.dlg.unit,
          description: this.dlg.description
        }
        if (this.dlg.id) await metricApi.update(this.dlg.id, body)
        else await metricApi.create(body)
        this.$message.success('保存成功'); this.dlg.show = false; this.loadList()
      } catch (e) { this.$message.error(e.message || '保存失败') }
    },
    async onDelete(row) {
      try { await this.$confirm('确定删除该条系数？', '确认'); await metricApi.remove(row.id); this.$message.success('已删除'); this.loadList() }
      catch (e) { if (e !== 'cancel') this.$message.error(e.message || '删除失败') }
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
.num-cell { font-family: 'Roboto Mono', Consolas, monospace; color: var(--citic-red); }
</style>
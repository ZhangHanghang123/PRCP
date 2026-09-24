<template>
  <div class="bd-page">
    <div class="page-header">
      <h2>基础数据维护</h2>
      <p class="desc">prcp_data_basic · 64+64 桶结构（m1..m60 + y10/y15/y20/y30）</p>
    </div>

    <el-card class="filter-card">
      <el-row :gutter="12" type="flex" align="middle">
        <el-col :span="5">
          <el-select v-model="filter.schemeId" placeholder="账户册方案" clearable
                     @change="loadAll" style="width:100%">
            <el-option v-for="s in schemes" :key="s.id"
                       :label="`${s.schemeCode} | ${s.schemeName}`" :value="s.id" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filter.dataDate" placeholder="日期" clearable @change="loadAll" style="width:100%">
            <el-option v-for="d in dates" :key="d" :label="d" :value="d" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filter.category" placeholder="类别" clearable @change="loadAll" style="width:100%">
            <el-option label="资产 ASSET" value="ASSET" />
            <el-option label="负债 LIABILITY" value="LIABILITY" />
            <el-option label="表外 OFF_BALANCE" value="OFF_BALANCE" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="filter.nodeKw" placeholder="搜索节点编码/名称" clearable @keyup.enter.native="loadAll" />
        </el-col>
        <el-col :span="4">
          <el-button type="primary" icon="el-icon-search" @click="loadAll">查询</el-button>
          <el-button icon="el-icon-refresh-left" @click="onReset">重置</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- 列表 Tab -->
      <el-tab-pane label="列表视图" name="list">
        <el-card class="table-card" v-loading="loading.list">
          <el-table :data="rows" border stripe height="540">
            <el-table-column type="index" label="#" width="50" align="center" />
            <el-table-column prop="dataDate" label="数据日期" width="120" />
            <el-table-column prop="nodeCode" label="节点编码" width="120" />
            <el-table-column prop="nodeName" label="节点名称" />
            <el-table-column label="类别" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.category === 'ASSET' ? 'danger' : (row.category === 'LIABILITY' ? 'warning' : 'info')" size="mini">
                  {{ row.category }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="L" width="60" align="center">
              <template #default="{ row }"><el-tag size="mini">L{{ row.nodeLevel }}</el-tag></template>
            </el-table-column>
            <el-table-column label="m1（orig/rem）" width="180">
              <template #default="{ row }">
                <span style="color:#C7000B">{{ row.origM1 }}</span> /
                <span style="color:#666">{{ row.remM1 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="m12" width="160">
              <template #default="{ row }">
                <span style="color:#C7000B">{{ row.origM12 }}</span> /
                <span style="color:#666">{{ row.remM12 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="y10" width="160">
              <template #default="{ row }">
                <span style="color:#C7000B">{{ row.origY10 }}</span> /
                <span style="color:#666">{{ row.remY10 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="y30" width="160">
              <template #default="{ row }">
                <span style="color:#C7000B">{{ row.origY30 }}</span> /
                <span style="color:#666">{{ row.remY30 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="center" fixed="right">
              <template #default="{ row }">
                <el-button type="text" @click="onEdit(row)">编辑</el-button>
                <el-button type="text" style="color:#F56C6C" @click="onDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 矩阵 Tab -->
      <el-tab-pane label="矩阵透视" name="matrix">
        <el-card class="table-card" v-loading="loading.matrix">
          <div slot="header">
            <span style="float:left">节点 × 期限桶（8 代表桶）</span>
            <span style="float:right;color:#999">{{ matrix.totalRows }} 节点 × {{ matrix.dates.length }} 日期</span>
          </div>
          <div style="overflow:auto">
            <el-table :data="matrixRows" border stripe height="540" :width="matrixWidth">
              <el-table-column prop="nodeCode" label="节点编码" width="100" fixed />
              <el-table-column prop="nodeName" label="节点名称" width="160" fixed />
              <el-table-column prop="category" label="类别" width="80" fixed>
                <template #default="{ row }">
                  <el-tag size="mini">{{ row.category }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column v-for="d in matrix.dates" :key="d" :label="d" align="center" min-width="280">
                <el-table-column
                  v-for="b in matrix.buckets" :key="d + '_' + b"
                  :label="b" align="right" width="68">
                  <template #default="{ row }">
                    <div v-if="getCell(row, d, b)" class="cell-pair">
                      <span class="cell-orig">{{ formatNum(getCell(row, d, b).orig) }}</span>
                      <span class="cell-rem">{{ formatNum(getCell(row, d, b).rem) }}</span>
                    </div>
                  </template>
                </el-table-column>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 编辑 Modal -->
    <el-dialog :title="editing ? '编辑节点数据' : '新增节点数据'" :visible.sync="modalVisible" width="640px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="数据日期">
              <el-date-picker v-model="form.dataDate" type="date" value-format="yyyy-MM-dd"
                              placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="节点 ID">
              <el-input-number v-model="form.coaNodeId" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="类别">
          <el-radio-group v-model="form.category">
            <el-radio-button label="ASSET">资产</el-radio-button>
            <el-radio-button label="LIABILITY">负债</el-radio-button>
            <el-radio-button label="OFF_BALANCE">表外</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-divider content-position="left">原值（orig）</el-divider>
        <el-row :gutter="8">
          <el-col :span="8"><el-form-item label="m1"><el-input-number v-model="form.orig_m1" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="m6"><el-input-number v-model="form.orig_m6" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="m12"><el-input-number v-model="form.orig_m12" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="y1(y10)"><el-input-number v-model="form.orig_y10" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="y15"><el-input-number v-model="form.orig_y15" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="y30"><el-input-number v-model="form.orig_y30" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-divider content-position="left">剩余（rem）</el-divider>
        <el-row :gutter="8">
          <el-col :span="8"><el-form-item label="m1"><el-input-number v-model="form.rem_m1" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="m6"><el-input-number v-model="form.rem_m6" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="m12"><el-input-number v-model="form.rem_m12" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="y10"><el-input-number v-model="form.rem_y10" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="y15"><el-input-number v-model="form.rem_y15" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="y30"><el-input-number v-model="form.rem_y30" :precision="2" :step="100" style="width:100%" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="modalVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { basicDataApi } from '@/api/data'
import { coaApi } from '@/api/coa'

export default {
  name: 'BasicDataIndex',
  data() {
    return {
      activeTab: 'list',
      schemes: [],
      dates: [],
      rows: [],
      matrix: { buckets: [], dates: [], rows: [], totalRows: 0 },
      filter: { schemeId: null, dataDate: '', category: '', nodeKw: '' },
      loading: { list: false, matrix: false },
      modalVisible: false,
      editing: null,
      submitting: false,
      form: this.newForm()
    }
  },
  computed: {
    matrixRows() {
      return this.matrix.rows || []
    },
    matrixWidth() {
      // 节点列 100+160+80 = 340；每月 8 桶 × 68 = 544
      return 340 + this.matrix.dates.length * 8 * 68
    }
  },
  async mounted() {
    this.schemes = await coaApi.listSchemes()
    await this.loadAll()
  },
  methods: {
    newForm() {
      return {
        coaNodeId: null, dataDate: '', category: 'ASSET',
        orig_m1: 0, orig_m6: 0, orig_m12: 0, orig_y10: 0, orig_y15: 0, orig_y30: 0,
        rem_m1: 0, rem_m6: 0, rem_m12: 0, rem_y10: 0, rem_y15: 0, rem_y30: 0
      }
    },
    async loadAll() {
      this.loading.list = true
      this.loading.matrix = true
      try {
        const [datesRes, listRes, matrixRes] = await Promise.all([
          basicDataApi.dates(this.filter.schemeId),
          basicDataApi.list(this.filter),
          basicDataApi.matrix(this.filter)
        ])
        this.dates = datesRes || []
        this.rows = listRes || []
        this.matrix = matrixRes || { buckets: [], dates: [], rows: [], totalRows: 0 }
      } finally {
        this.loading.list = false
        this.loading.matrix = false
      }
    },
    onReset() {
      this.filter = { schemeId: this.filter.schemeId, dataDate: '', category: '', nodeKw: '' }
      this.loadAll()
    },
    formatNum(v) {
      if (v == null) return '-'
      const n = Number(v)
      if (Number.isNaN(n)) return v
      return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
    },
    getCell(row, date, bucket) {
      if (!row || !row.cells) return null
      return row.cells.find(c => c.date === date && c.bucket === bucket)
    },
    onEdit(row) {
      this.editing = row
      this.form = this.newForm()
      this.form.coaNodeId = row.coaNodeId
      this.form.dataDate = row.dataDate
      this.form.category = row.category || 'ASSET'
      // 预填 8 个代表桶
      const buckets = ['m1', 'm3', 'm6', 'm12', 'y10', 'y15', 'y20', 'y30']
      buckets.forEach(b => {
        const camel = b.charAt(0).toUpperCase() + b.substring(1)
        this.form[`orig_${b}`] = Number(row[`orig${camel}`]) || 0
        this.form[`rem_${b}`] = Number(row[`rem${camel}`]) || 0
      })
      this.modalVisible = true
    },
    onDelete(row) {
      this.$confirm(`确认删除 [${row.nodeCode}] ${row.dataDate}？`, '提示', { type: 'warning' })
        .then(async () => {
          await basicDataApi.remove(row.id)
          this.$message.success('已删除')
          this.loadAll()
        }).catch(() => {})
    },
    async onSubmit() {
      this.submitting = true
      try {
        await basicDataApi.upsert(this.form)
        this.$message.success('保存成功')
        this.modalVisible = false
        this.loadAll()
      } finally { this.submitting = false }
    }
  }
}
</script>

<style scoped>
.bd-page { padding: 0; }
.page-header {
  background: #fff; padding: 16px 24px; margin-bottom: 16px; border-bottom: 1px solid #f0f0f0;
}
.page-header h2 { margin: 0; }
.page-header .desc { color: #999; font-size: 13px; margin: 4px 0 0; }
.filter-card { margin: 0 16px 16px; }
.table-card { margin: 0 16px; }
.cell-pair { display:flex; flex-direction:column; line-height:1.3; padding:2px 0; }
.cell-orig { color:#C7000B; font-size:12px; }
.cell-rem { color:#999; font-size:11px; }
</style>
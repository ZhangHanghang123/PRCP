<template>
  <div class="rd-page">
    <div class="page-header">
      <h2>反算基础数据</h2>
      <p class="desc">prcp_data_reverse · 反算方案执行的中间产物（按 scheme_code 隔离）</p>
    </div>

    <el-card class="filter-card">
      <el-row :gutter="12" type="flex" align="middle">
        <el-col :span="5">
          <el-select v-model="filter.schemeCode" placeholder="反算方案 code" clearable
                     @change="loadAll" style="width:100%">
            <el-option v-for="c in schemeCodes" :key="c" :label="c" :value="c" />
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
      <el-tab-pane label="列表视图" name="list">
        <el-card class="table-card" v-loading="loading.list">
          <el-table :data="rows" border stripe height="540">
            <el-table-column type="index" label="#" width="50" align="center" />
            <el-table-column prop="schemeCode" label="反算方案" width="140" />
            <el-table-column prop="dataDate" label="数据日期" width="120" />
            <el-table-column prop="dateOffset" label="月偏移" width="80" align="center" />
            <el-table-column prop="nodeCode" label="节点编码" width="120" />
            <el-table-column prop="nodeName" label="节点名称" />
            <el-table-column label="类别" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.category === 'ASSET' ? 'danger' : (row.category === 'LIABILITY' ? 'warning' : 'info')" size="mini">
                  {{ row.category }}
                </el-tag>
              </template>
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
            <el-table-column label="操作" width="120" align="center" fixed="right">
              <template #default="{ row }">
                <el-button type="text" style="color:#F56C6C" @click="onDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

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
  </div>
</template>

<script>
import { reverseDataApi } from '@/api/data'

export default {
  name: 'ReverseDataIndex',
  data() {
    return {
      activeTab: 'matrix',
      schemeCodes: ['ZXCOA_V1'],
      dates: [],
      rows: [],
      matrix: { buckets: [], dates: [], rows: [], totalRows: 0 },
      filter: { schemeCode: 'ZXCOA_V1', dataDate: '', category: '', nodeKw: '' },
      loading: { list: false, matrix: false }
    }
  },
  computed: {
    matrixRows() { return this.matrix.rows || [] },
    matrixWidth() {
      return 340 + this.matrix.dates.length * 8 * 68
    }
  },
  async mounted() {
    await this.loadAll()
  },
  methods: {
    async loadAll() {
      this.loading.list = true
      this.loading.matrix = true
      try {
        const [datesRes, listRes, matrixRes] = await Promise.all([
          reverseDataApi.dates(),
          reverseDataApi.list(this.filter),
          reverseDataApi.matrix(this.filter)
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
      this.filter = { schemeCode: this.filter.schemeCode, dataDate: '', category: '', nodeKw: '' }
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
    onDelete(row) {
      this.$confirm(`确认删除 [${row.schemeCode}/${row.nodeCode}] ${row.dataDate}？`, '提示', { type: 'warning' })
        .then(async () => {
          await reverseDataApi.remove(row.id)
          this.$message.success('已删除')
          this.loadAll()
        }).catch(() => {})
    }
  }
}
</script>

<style scoped>
.rd-page { padding: 0; }
.page-header { background:#fff; padding:16px 24px; margin-bottom:16px; border-bottom:1px solid #f0f0f0; }
.page-header h2 { margin:0; }
.page-header .desc { color:#999; font-size:13px; margin:4px 0 0; }
.filter-card { margin:0 16px 16px; }
.table-card { margin:0 16px; }
.cell-pair { display:flex; flex-direction:column; line-height:1.3; padding:2px 0; }
.cell-orig { color:#C7000B; font-size:12px; }
.cell-rem { color:#999; font-size:11px; }
</style>
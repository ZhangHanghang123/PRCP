<template>
  <div class="rpt-page">
    <div class="page-header">
      <h2>报表表项管理</h2>
      <p class="desc">报表定义 + 表项树（6 类报表：资产负债表/损益表/现金流/指标/风险/流动性）</p>
    </div>

    <!-- 上半：报表定义列表 -->
    <el-card class="filter-card">
      <el-row :gutter="16" type="flex" align="middle">
        <el-col :span="5">
          <el-select v-model="filter.reportType" placeholder="报表类型" clearable @change="loadReports">
            <el-option v-for="t in REPORT_TYPES" :label="t.label" :value="t.value" :key="t.value" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filter.schemeId" placeholder="账户册方案" clearable filterable @change="loadReports">
            <el-option v-for="s in schemes" :key="s.id"
                       :label="`${s.schemeCode} | ${s.schemeName}`" :value="s.id" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="filter.keyword" placeholder="报表编码/名称" clearable @keyup.enter.native="loadReports" />
        </el-col>
        <el-col :span="8">
          <el-button type="primary" icon="el-icon-search" @click="loadReports">查询</el-button>
          <el-button icon="el-icon-refresh-left" @click="onReset">重置</el-button>
          <el-button type="danger" icon="el-icon-plus" @click="onAddReport">新增报表</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="table-card" v-loading="loading">
      <el-table :data="reports" border stripe>
        <el-table-column prop="reportCode" label="报表编码" width="120" />
        <el-table-column prop="reportName" label="报表名称" />
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="typeTagType(row.reportType)" size="mini">{{ typeLabel(row.reportType) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="schemeName" label="关联方案" width="180" />
        <el-table-column prop="itemCount" label="表项数" width="80" align="center" />
        <el-table-column label="操作" width="260" align="center">
          <template #default="{ row }">
            <el-button type="text" @click="viewItems(row)">📋 表项</el-button>
            <el-button type="text" @click="onEditReport(row)">编辑</el-button>
            <el-button type="text" style="color:#f56c6c;" @click="onDeleteReport(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑报表 -->
    <el-dialog :title="editingReport ? '编辑报表' : '新增报表'" :visible.sync="modalVisible" width="560px">
      <el-form :model="reportForm" :rules="reportRules" ref="reportFormRef" label-width="100px">
        <el-form-item label="报表编码" prop="reportCode"><el-input v-model="reportForm.reportCode" /></el-form-item>
        <el-form-item label="报表名称" prop="reportName"><el-input v-model="reportForm.reportName" /></el-form-item>
        <el-form-item label="报表类型" prop="reportType">
          <el-select v-model="reportForm.reportType" style="width:100%">
            <el-option v-for="t in REPORT_TYPES" :label="t.label" :value="t.value" :key="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="账户册方案" prop="schemeId">
          <el-select v-model="reportForm.schemeId" style="width:100%" filterable>
            <el-option v-for="s in schemes" :key="s.id"
                       :label="`${s.schemeCode} | ${s.schemeName}`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="reportForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modalVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitReport">提交</el-button>
      </template>
    </el-dialog>

    <!-- 表项树弹窗 -->
    <el-dialog :title="`表项管理 - ${currentReport?.reportName || ''}`"
               :visible.sync="itemsModalVisible" width="780px" top="5vh">
      <el-row :gutter="12">
        <el-col :span="16">
          <el-table :data="itemsTree" row-key="id" border default-expand-all
                    :tree-props="{ children: 'children' }" v-loading="itemsLoading" max-height="500">
            <el-table-column prop="itemCode" label="编码" width="120" />
            <el-table-column prop="itemName" label="名称" />
            <el-table-column prop="dataType" label="类型" width="80" align="center" />
            <el-table-column prop="formula" label="公式" show-overflow-tooltip />
            <el-table-column label="操作" width="160" align="center">
              <template #default="{ row }">
                <el-button type="text" size="mini" @click="onAddItemChild(row)">+ 子项</el-button>
                <el-button type="text" size="mini" @click="onEditItem(row)">编辑</el-button>
                <el-button type="text" size="mini" style="color:#f56c6c;" @click="onDeleteItem(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
        <el-col :span="8">
          <el-card shadow="never" class="add-card">
            <div slot="header"><strong>新增表项</strong></div>
            <el-form :model="itemForm" label-width="80px" size="small">
              <el-form-item label="父表项">
                <el-cascader v-model="itemForm.parentPath"
                             :options="cascaderOpts" :props="{ checkStrictly:true, value:'id', label:'itemName' }"
                             clearable change-on-select placeholder="根节点" />
              </el-form-item>
              <el-form-item label="编码"><el-input v-model="itemForm.itemCode" /></el-form-item>
              <el-form-item label="名称"><el-input v-model="itemForm.itemName" /></el-form-item>
              <el-form-item label="数据类型">
                <el-select v-model="itemForm.dataType" style="width:100%">
                  <el-option label="DECIMAL" value="DECIMAL" />
                  <el-option label="PERCENT" value="PERCENT" />
                  <el-option label="INTEGER" value="INTEGER" />
                  <el-option label="TEXT" value="TEXT" />
                </el-select>
              </el-form-item>
              <el-form-item label="公式">
                <el-input v-model="itemForm.formula" type="textarea" :rows="2" placeholder="A+B-C" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="itemForm.description" type="textarea" :rows="2" />
              </el-form-item>
              <el-button type="danger" icon="el-icon-plus" size="small" :loading="submitting"
                         style="width:100%" @click="onSubmitItem">新增到树</el-button>
            </el-form>
          </el-card>
        </el-col>
      </el-row>
    </el-dialog>
  </div>
</template>

<script>
import { reportsApi } from '@/api/reports'
import { coaApi } from '@/api/coa'

export default {
  name: 'RptIndex',
  data() {
    return {
      REPORT_TYPES: [
        { value: 'BALANCE', label: '资产负债表' },
        { value: 'INCOME', label: '损益表' },
        { value: 'CASHFLOW', label: '现金流量表' },
        { value: 'INDICATOR', label: '指标表' },
        { value: 'RISK', label: '风险表' },
        { value: 'LIQUIDITY', label: '流动性表' }
      ],
      schemes: [],
      filter: { reportType: null, schemeId: null, keyword: '' },
      reports: [],
      loading: false,

      modalVisible: false,
      editingReport: null,
      reportForm: { reportCode: '', reportName: '', reportType: 'BALANCE', schemeId: null, description: '' },
      reportRules: {
        reportCode: [{ required: true, message: '请输入编码' }],
        reportName: [{ required: true, message: '请输入名称' }]
      },
      submitting: false,

      itemsModalVisible: false,
      currentReport: null,
      itemsTree: [],
      itemsLoading: false,
      itemForm: { parentPath: [], itemCode: '', itemName: '', dataType: 'DECIMAL', formula: '', description: '' }
    }
  },
  computed: {
    cascaderOpts() {
      const toOpt = n => ({ id: n.id, itemName: `${n.itemCode} ${n.itemName}`, children: (n.children || []).map(toOpt) })
      return this.itemsTree.map(toOpt)
    }
  },
  async mounted() {
    this.schemes = await coaApi.listSchemes()
    if (this.schemes.length) {
      this.filter.schemeId = this.schemes[0].id
      this.loadReports()
    }
  },
  methods: {
    typeLabel(t) { return (this.REPORT_TYPES.find(x => x.value === t) || {}).label || t },
    typeTagType(t) {
      return { BALANCE: 'danger', INCOME: 'warning', CASHFLOW: 'success',
               INDICATOR: '', RISK: 'info', LIQUIDITY: '' }[t] || ''
    },
    async loadReports() {
      this.loading = true
      try { this.reports = await reportsApi.list({ report_type: this.filter.reportType, scheme_id: this.filter.schemeId, keyword: this.filter.keyword }) }
      finally { this.loading = false }
    },
    onReset() { this.filter = { reportType: null, schemeId: this.filter.schemeId, keyword: '' }; this.loadReports() },
    onAddReport() {
      this.editingReport = null
      this.reportForm = { reportCode: '', reportName: '', reportType: 'BALANCE', schemeId: this.filter.schemeId, description: '' }
      this.modalVisible = true
    },
    onEditReport(row) {
      this.editingReport = row
      this.reportForm = { ...row }
      this.modalVisible = true
    },
    async onSubmitReport() {
      await this.$refs.reportFormRef.validate()
      this.submitting = true
      try {
        if (this.editingReport) await reportsApi.update(this.editingReport.id, this.reportForm)
        else await reportsApi.create(this.reportForm)
        this.$message.success('保存成功')
        this.modalVisible = false
        this.loadReports()
      } finally { this.submitting = false }
    },
    onDeleteReport(row) {
      this.$confirm(`确认删除 [${row.reportCode}] ${row.reportName}？`, '提示', { type: 'warning' })
        .then(async () => { await reportsApi.delete(row.id); this.$message.success('删除成功'); this.loadReports() })
        .catch(() => {})
    },
    async viewItems(row) {
      this.currentReport = row
      this.itemsModalVisible = true
      await this.loadItems()
    },
    async loadItems() {
      this.itemsLoading = true
      try { this.itemsTree = await reportsApi.listItems(this.currentReport.id) }
      finally { this.itemsLoading = false }
    },
    onAddItemChild(parent) {
      this.itemForm = { parentPath: [parent.id], itemCode: '', itemName: '', dataType: 'DECIMAL', formula: '', description: '' }
    },
    onEditItem(row) {
      this.$prompt(`修改 [${row.itemCode}] 名称：`, '编辑表项', { inputValue: row.itemName })
        .then(async ({ value }) => {
          await reportsApi.updateItem(row.id, { ...row, itemName: value })
          this.$message.success('已更新'); this.loadItems()
        }).catch(() => {})
    },
    async onSubmitItem() {
      if (!this.itemForm.itemCode || !this.itemForm.itemName) return this.$message.warning('请输入编码和名称')
      this.submitting = true
      try {
        await reportsApi.createItem({
          reportId: this.currentReport.id,
          itemCode: this.itemForm.itemCode,
          itemName: this.itemForm.itemName,
          dataType: this.itemForm.dataType,
          formula: this.itemForm.formula,
          description: this.itemForm.description,
          parentId: this.itemForm.parentPath.length ? this.itemForm.parentPath[this.itemForm.parentPath.length - 1] : null
        })
        this.$message.success('已新增')
        this.itemForm = { parentPath: [], itemCode: '', itemName: '', dataType: 'DECIMAL', formula: '', description: '' }
        await this.loadItems()
        // 刷新 item_count
        this.loadReports()
      } finally { this.submitting = false }
    },
    onDeleteItem(row) {
      this.$confirm(`确认删除 [${row.itemCode}] ${row.itemName}？`, '提示', { type: 'warning' })
        .then(async () => { await reportsApi.deleteItem(row.id); this.$message.success('已删除'); this.loadItems(); this.loadReports() })
        .catch(() => {})
    }
  }
}
</script>

<style scoped>
.rpt-page { padding: 0; }
.page-header { background:#fff; padding:16px 24px; margin-bottom:16px; border-bottom:1px solid #f0f0f0; }
.page-header h2 { margin:0; }
.page-header .desc { color:#999; font-size:13px; margin:4px 0 0; }
.filter-card { margin:0 16px 16px; }
.table-card { margin:0 16px 16px; }
.add-card { background:#fff5f5; }
</style>
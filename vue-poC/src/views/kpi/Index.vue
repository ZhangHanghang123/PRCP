<template>
  <div class="kpi-page">
    <div class="page-header">
      <h2>指标管理</h2>
      <p class="desc">KPI 定义 / 指标值 / 评分规则 / 试算</p>
    </div>

    <!-- 顶部 4 KPI -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6"><el-card shadow="hover" class="kpi-card"><div class="kpi-label">指标方案</div><div class="kpi-value">{{ schemes.length }}</div><div class="kpi-unit">个</div></el-card></el-col>
      <el-col :span="6"><el-card shadow="hover" class="kpi-card"><div class="kpi-label">指标定义</div><div class="kpi-value">{{ defs.length }}</div><div class="kpi-unit">个</div></el-card></el-col>
      <el-col :span="6"><el-card shadow="hover" class="kpi-card"><div class="kpi-label">指标值</div><div class="kpi-value">{{ values.length }}</div><div class="kpi-unit">条</div></el-card></el-col>
      <el-col :span="6"><el-card shadow="hover" class="kpi-card"><div class="kpi-label">评分规则</div><div class="kpi-value">{{ rules.length }}</div><div class="kpi-unit">条</div></el-card></el-col>
    </el-row>

    <!-- 4 个 Tab -->
    <el-card class="main-card">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- ============ KPI 定义 ============ -->
        <el-tab-pane label="指标定义" name="def">
          <el-row :gutter="12" type="flex" align="middle" style="margin-bottom:12px">
            <el-col :span="5">
              <el-select v-model="defFilter.schemeId" placeholder="指标方案" clearable @change="loadDefs">
                <el-option v-for="s in schemes" :key="s.id"
                           :label="`${s.schemeCode} | ${s.schemeName}`" :value="s.id" />
              </el-select>
            </el-col>
            <el-col :span="5">
              <el-input v-model="defFilter.keyword" placeholder="编码/名称" clearable @keyup.enter.native="loadDefs" />
            </el-col>
            <el-col :span="14">
              <el-button type="danger" icon="el-icon-plus" @click="onAddDef">新增指标</el-button>
            </el-col>
          </el-row>
          <el-table :data="defs" border stripe v-loading="defLoading">
            <el-table-column prop="kpiCode" label="编码" width="120" />
            <el-table-column prop="kpiName" label="名称" />
            <el-table-column label="类型" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.indicatorType === 2 ? 'warning' : 'danger'" size="mini">
                  {{ row.indicatorType === 2 ? '函数' : '公式' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="schemeName" label="方案" width="160" />
            <el-table-column prop="reportName" label="关联报表" width="160" />
            <el-table-column prop="formula" label="公式/脚本" show-overflow-tooltip />
            <el-table-column prop="calcUnit" label="单位" width="80" align="center" />
            <el-table-column label="操作" width="160" align="center">
              <template #default="{ row }">
                <el-button type="text" @click="onEditDef(row)">编辑</el-button>
                <el-button type="text" style="color:#f56c6c;" @click="onDeleteDef(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- ============ KPI 值 ============ -->
        <el-tab-pane label="指标值" name="value">
          <el-row :gutter="12" type="flex" align="middle" style="margin-bottom:12px">
            <el-col :span="5">
              <el-select v-model="valueFilter.kpiId" placeholder="指标" filterable clearable @change="loadValues">
                <el-option v-for="d in defs" :key="d.id"
                           :label="`${d.kpiCode} | ${d.kpiName}`" :value="d.id" />
              </el-select>
            </el-col>
            <el-col :span="5">
              <el-date-picker v-model="valueFilter.dataDate" type="date" value-format="yyyy-MM-dd"
                              placeholder="日期" @change="loadValues" style="width:100%" />
            </el-col>
            <el-col :span="14">
              <el-button type="danger" icon="el-icon-plus" @click="onAddValue">录入指标值</el-button>
            </el-col>
          </el-row>
          <el-table :data="values" border stripe v-loading="valueLoading">
            <el-table-column prop="kpiCode" label="编码" width="120" />
            <el-table-column prop="kpiName" label="名称" />
            <el-table-column prop="dataDate" label="日期" width="120" />
            <el-table-column prop="version" label="版本" width="80" />
            <el-table-column prop="currentValue" label="本期" width="100" align="right" />
            <el-table-column prop="prevValue" label="上期" width="100" align="right" />
            <el-table-column prop="prevYearValue" label="去年同期" width="100" align="right" />
            <el-table-column prop="score" label="得分" width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.score != null" :type="row.score >= 80 ? 'success' : (row.score >= 60 ? 'warning' : 'danger')">
                  {{ row.score }}
                </el-tag>
                <span v-else style="color:#aaa">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="calcSource" label="来源" width="80" align="center" />
            <el-table-column label="操作" width="180" align="center">
              <template #default="{ row }">
                <el-button type="text" @click="onRecalc(row)">试算</el-button>
                <el-button type="text" style="color:#f56c6c;" @click="onDeleteValue(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- ============ 评分规则 ============ -->
        <el-tab-pane label="评分规则" name="rule">
          <el-row :gutter="12" type="flex" align="middle" style="margin-bottom:12px">
            <el-col :span="5">
              <el-select v-model="ruleFilter.schemeId" placeholder="指标方案" clearable @change="loadRules">
                <el-option v-for="s in schemes" :key="s.id"
                           :label="`${s.schemeCode} | ${s.schemeName}`" :value="s.id" />
              </el-select>
            </el-col>
            <el-col :span="19">
              <el-button type="danger" icon="el-icon-plus" @click="onAddRule">新增规则</el-button>
            </el-col>
          </el-row>
          <el-table :data="rules" border stripe v-loading="ruleLoading">
            <el-table-column prop="ruleName" label="规则名称" width="160" />
            <el-table-column prop="schemeName" label="方案" width="160" />
            <el-table-column prop="kpiName" label="指标" />
            <el-table-column prop="calcMethod" label="方式" width="100" align="center" />
            <el-table-column prop="totalScore" label="总分" width="80" align="right" />
            <el-table-column label="方向" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.higherIsBetter === 1 ? 'success' : 'warning'" size="mini">
                  {{ row.higherIsBetter === 1 ? '↑ 正向' : '↓ 反向' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" show-overflow-tooltip />
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button type="text" style="color:#f56c6c;" @click="onDeleteRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- ============ 通用 Modal ============ -->
    <el-dialog :title="defModalTitle" :visible.sync="defModalVisible" width="640px">
      <el-form :model="defForm" :rules="defRules" ref="defFormRef" label-width="100px">
        <el-form-item label="指标编码" prop="kpiCode"><el-input v-model="defForm.kpiCode" /></el-form-item>
        <el-form-item label="指标名称" prop="kpiName"><el-input v-model="defForm.kpiName" /></el-form-item>
        <el-form-item label="指标方案" prop="schemeId">
          <el-select v-model="defForm.schemeId" style="width:100%" filterable>
            <el-option v-for="s in schemes" :key="s.id" :label="`${s.schemeCode} | ${s.schemeName}`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联报表">
          <el-input-number v-model="defForm.rptId" :min="0" />
        </el-form-item>
        <el-form-item label="公式/脚本">
          <el-input v-model="defForm.formula" type="textarea" :rows="3" placeholder="A+B-C 或 calc_func()" />
        </el-form-item>
        <el-form-item label="单位">
          <el-select v-model="defForm.calcUnit" style="width:100%">
            <el-option label="PERCENT 百分比" value="PERCENT" />
            <el-option label="ABSOLUTE 绝对值" value="ABSOLUTE" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值范围">
          <el-input-number v-model="defForm.thresholdMin" :precision="4" placeholder="下限" />
          ~
          <el-input-number v-model="defForm.thresholdMax" :precision="4" placeholder="上限" />
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="defForm.formulaDesc" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="defModalVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitDef">提交</el-button>
      </template>
    </el-dialog>

    <!-- 录入指标值 Modal -->
    <el-dialog title="录入指标值" :visible.sync="valueModalVisible" width="520px">
      <el-form :model="valueForm" label-width="100px">
        <el-form-item label="指标">
          <el-select v-model="valueForm.kpiId" style="width:100%" filterable>
            <el-option v-for="d in defs" :key="d.id"
                       :label="`${d.kpiCode} | ${d.kpiName}`" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据日期">
          <el-date-picker v-model="valueForm.dataDate" type="date" value-format="yyyy-MM-dd"
                          placeholder="选择日期" style="width:100%" />
        </el-form-item>
        <el-form-item label="本期值"><el-input-number v-model="valueForm.currentValue" :precision="6" :step="0.01" /></el-form-item>
        <el-form-item label="上期值"><el-input-number v-model="valueForm.prevValue" :precision="6" :step="0.01" /></el-form-item>
        <el-form-item label="去年同期"><el-input-number v-model="valueForm.prevYearValue" :precision="6" :step="0.01" /></el-form-item>
        <el-form-item label="版本"><el-input v-model="valueForm.version" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="valueModalVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitValue">提交</el-button>
      </template>
    </el-dialog>

    <!-- 评分规则 Modal -->
    <el-dialog title="新增评分规则" :visible.sync="ruleModalVisible" width="540px">
      <el-form :model="ruleForm" label-width="100px">
        <el-form-item label="指标">
          <el-select v-model="ruleForm.kpiId" style="width:100%" filterable>
            <el-option v-for="d in defs" :key="d.id"
                       :label="`${d.kpiCode} | ${d.kpiName}`" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="规则名称"><el-input v-model="ruleForm.ruleName" placeholder="如：标准分段评分" /></el-form-item>
        <el-form-item label="方案">
          <el-select v-model="ruleForm.schemeId" style="width:100%">
            <el-option v-for="s in schemes" :key="s.id" :label="s.schemeName" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="总分"><el-input-number v-model="ruleForm.totalScore" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="方向">
          <el-radio-group v-model="ruleForm.higherIsBetter">
            <el-radio :label="1">↑ 正向（值越高越好）</el-radio>
            <el-radio :label="0">↓ 反向（值越低越好）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="ruleForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleModalVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitRule">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { kpiApi } from '@/api/kpi'

export default {
  name: 'KpiIndex',
  data() {
    return {
      activeTab: 'def',
      schemes: [],
      defs: [], values: [], rules: [],

      defFilter: { schemeId: null, keyword: '' },
      defLoading: false,
      defModalVisible: false, defModalTitle: '', editingDef: null,
      defForm: { kpiCode: '', kpiName: '', schemeId: null, rptId: null, formula: '', calcUnit: 'PERCENT', thresholdMin: null, thresholdMax: null, formulaDesc: '' },
      defRules: { kpiCode: [{ required: true }], kpiName: [{ required: true }] },

      valueFilter: { kpiId: null, dataDate: null },
      valueLoading: false,
      valueModalVisible: false,
      valueForm: { kpiId: null, dataDate: null, currentValue: 0, prevValue: 0, prevYearValue: 0, version: 'V1.0' },

      ruleFilter: { schemeId: null },
      ruleLoading: false,
      ruleModalVisible: false,
      ruleForm: { kpiId: null, ruleName: '', schemeId: null, totalScore: 100, higherIsBetter: 1, description: '' },

      submitting: false
    }
  },
  async mounted() {
    this.schemes = await kpiApi.listSchemes()
    if (this.schemes.length) {
      this.defFilter.schemeId = this.schemes[0].id
      this.ruleFilter.schemeId = this.schemes[0].id
      this.defForm.schemeId = this.schemes[0].id
      this.ruleForm.schemeId = this.schemes[0].id
    }
    await this.loadDefs()
    await this.loadValues()
    await this.loadRules()
  },
  methods: {
    async loadDefs() {
      this.defLoading = true
      try { this.defs = await kpiApi.listDefs({ scheme_id: this.defFilter.schemeId, keyword: this.defFilter.keyword }) }
      finally { this.defLoading = false }
    },
    async loadValues() {
      this.valueLoading = true
      try {
        this.values = await kpiApi.listValues({
          kpi_id: this.valueFilter.kpiId,
          data_date: this.valueFilter.dataDate
        })
      } finally { this.valueLoading = false }
    },
    async loadRules() {
      this.ruleLoading = true
      try { this.rules = await kpiApi.listScoreRules({ scheme_id: this.ruleFilter.schemeId }) }
      finally { this.ruleLoading = false }
    },

    onAddDef() {
      this.editingDef = null
      this.defForm = { kpiCode: '', kpiName: '', schemeId: this.defFilter.schemeId, rptId: null,
                       formula: '', calcUnit: 'PERCENT', thresholdMin: null, thresholdMax: null, formulaDesc: '' }
      this.defModalTitle = '新增指标'; this.defModalVisible = true
    },
    onEditDef(row) {
      this.editingDef = row
      this.defForm = { ...row }
      this.defModalTitle = '编辑指标'; this.defModalVisible = true
    },
    async onSubmitDef() {
      await this.$refs.defFormRef.validate()
      this.submitting = true
      try {
        if (this.editingDef) await kpiApi.updateDef(this.editingDef.id, this.defForm)
        else await kpiApi.createDef(this.defForm)
        this.$message.success('已保存'); this.defModalVisible = false; this.loadDefs()
      } finally { this.submitting = false }
    },
    onDeleteDef(row) {
      this.$confirm(`确认删除 [${row.kpiCode}] ${row.kpiName}？`, '提示', { type: 'warning' })
        .then(async () => { await kpiApi.deleteDef(row.id); this.$message.success('已删除'); this.loadDefs() })
        .catch(() => {})
    },

    onAddValue() {
      this.valueForm = { kpiId: null, dataDate: null, currentValue: 0, prevValue: 0, prevYearValue: 0, version: 'V1.0' }
      this.valueModalVisible = true
    },
    async onSubmitValue() {
      this.submitting = true
      try {
        await kpiApi.createValue(this.valueForm)
        this.$message.success('已录入'); this.valueModalVisible = false; this.loadValues()
      } finally { this.submitting = false }
    },
    async onRecalc(row) {
      try {
        const r = await kpiApi.recalc(row.kpiId, row.dataDate)
        this.$message.success(`试算得分：${r.score}`)
        this.loadValues()
      } catch (e) { /* error handled */ }
    },
    onDeleteValue(row) {
      this.$confirm(`确认删除值 [${row.kpiCode}] ${row.dataDate}？`, '提示', { type: 'warning' })
        .then(async () => { await kpiApi.deleteValue(row.id); this.$message.success('已删除'); this.loadValues() })
        .catch(() => {})
    },

    onAddRule() {
      this.ruleForm = { kpiId: null, ruleName: '', schemeId: this.ruleFilter.schemeId, totalScore: 100, higherIsBetter: 1, description: '' }
      this.ruleModalVisible = true
    },
    async onSubmitRule() {
      this.submitting = true
      try {
        await kpiApi.createScoreRule(this.ruleForm)
        this.$message.success('已新增'); this.ruleModalVisible = false; this.loadRules()
      } finally { this.submitting = false }
    },
    onDeleteRule(row) {
      this.$confirm(`确认删除规则 [${row.ruleName}]？`, '提示', { type: 'warning' })
        .then(async () => { await kpiApi.deleteScoreRule(row.id); this.$message.success('已删除'); this.loadRules() })
        .catch(() => {})
    }
  }
}
</script>

<style scoped>
.kpi-page { padding: 0; }
.page-header { background:#fff; padding:16px 24px; margin-bottom:16px; border-bottom:1px solid #f0f0f0; }
.page-header h2 { margin:0; }
.page-header .desc { color:#999; font-size:13px; margin:4px 0 0; }
.kpi-row { margin:0 16px 16px; }
.kpi-card { text-align:center; padding:8px 0; background:linear-gradient(135deg, #fff5f5 0%, #fff 100%); border-top:2px solid #C7000B; }
.kpi-label { color:#888; font-size:13px; }
.kpi-value { color:#C7000B; font-size:28px; font-weight:bold; margin:4px 0; }
.kpi-unit { color:#aaa; font-size:12px; }
.main-card { margin:0 16px 16px; }
</style>
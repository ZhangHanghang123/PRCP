<template>
  <div class="coa-page">
    <div class="page-header">
      <h2>账户册维护</h2>
      <p class="desc">SpringBoot + Vue2 + ElementUI PoC 模块</p>
    </div>

    <el-card class="filter-card">
      <el-row :gutter="20" type="flex" align="middle">
        <el-col :span="8">
          <el-select v-model="filterSchemeId" placeholder="选择账户册方案" filterable
                     @change="loadTree" style="width: 100%;">
            <el-option v-for="s in schemes" :key="s.id"
                       :label="`${s.schemeCode} | ${s.schemeName}`"
                       :value="s.id" />
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-input v-model="keyword" placeholder="搜索节点编码/名称" clearable />
        </el-col>
        <el-col :span="8">
          <el-button type="primary" icon="el-icon-search" @click="loadTree">查询</el-button>
          <el-button icon="el-icon-refresh-left" @click="onReset">重置</el-button>
          <el-button type="danger" icon="el-icon-plus" @click="onAdd">新增节点</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="table-card" v-loading="loading">
      <el-table :data="filteredTree" row-key="id" border default-expand-all
                :tree-props="{ children: 'children' }">
        <el-table-column prop="nodeCode" label="节点编码" width="180" />
        <el-table-column prop="nodeName" label="节点名称" />
        <el-table-column prop="nodeLevel" label="层级" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.nodeLevel === 1 ? 'danger' : (row.nodeLevel === 2 ? 'warning' : 'info')">
              L{{ row.nodeLevel }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <el-button type="text" @click="onAddChild(row)">新增子节点</el-button>
            <el-button type="text" @click="onEdit(row)">编辑</el-button>
            <el-button type="text" style="color: #f56c6c;" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑 Modal -->
    <el-dialog :title="editing ? '编辑节点' : '新增节点'" :visible.sync="modalVisible" width="540px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="父节点">
          <el-cascader v-model="form.parentPath"
                       :options="cascaderOptions"
                       :props="{ checkStrictly: true, value: 'id', label: 'nodeName' }"
                       clearable change-on-select
                       placeholder="不选则挂在根节点" />
        </el-form-item>
        <el-form-item label="节点编码" prop="nodeCode">
          <el-input v-model="form.nodeCode" />
        </el-form-item>
        <el-form-item label="节点名称" prop="nodeName">
          <el-input v-model="form.nodeName" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modalVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { coaApi } from '@/api/coa'

export default {
  name: 'CoaIndex',
  data() {
    return {
      schemes: [],
      filterSchemeId: null,
      keyword: '',
      tree: [],
      loading: false,
      modalVisible: false,
      editing: null,
      submitting: false,
      form: { parentPath: [], nodeCode: '', nodeName: '', sortOrder: 0 },
      rules: {
        nodeCode: [{ required: true, message: '请输入节点编码' }],
        nodeName: [{ required: true, message: '请输入节点名称' }]
      }
    }
  },
  computed: {
    filteredTree() {
      if (!this.keyword) return this.tree
      const kw = this.keyword.toLowerCase()
      const filter = (n) => {
        const matched = (n.nodeCode || '').toLowerCase().includes(kw) || (n.nodeName || '').toLowerCase().includes(kw)
        const children = (n.children || []).map(filter).filter(Boolean)
        if (matched || children.length) return { ...n, children }
        return null
      }
      return this.tree.map(filter).filter(Boolean)
    },
    cascaderOptions() {
      const toOpts = (n) => ({
        id: n.id,
        nodeName: `${n.nodeCode} ${n.nodeName}`,
        children: (n.children || []).map(toOpts)
      })
      return this.tree.map(toOpts)
    }
  },
  async mounted() {
    await this.loadSchemes()
  },
  methods: {
    async loadSchemes() {
      this.schemes = await coaApi.listSchemes()
      if (this.schemes.length) {
        this.filterSchemeId = this.schemes[0].id
        await this.loadTree()
      }
    },
    async loadTree() {
      if (!this.filterSchemeId) return
      this.loading = true
      try {
        this.tree = await coaApi.listTree(this.filterSchemeId)
      } finally { this.loading = false }
    },
    onReset() { this.keyword = ''; this.loadTree() },
    onAdd() {
      this.editing = null
      this.form = { parentPath: [], nodeCode: '', nodeName: '', sortOrder: 0 }
      this.modalVisible = true
    },
    onAddChild(parent) {
      this.editing = null
      this.form = {
        parentPath: [parent.id],
        nodeCode: '', nodeName: '',
        sortOrder: 0
      }
      this.modalVisible = true
    },
    onEdit(row) {
      this.editing = row
      this.form = { ...row, parentPath: [] }
      this.modalVisible = true
    },
    onDelete(row) {
      this.$confirm(`确认删除 [${row.nodeCode}] ${row.nodeName}？`, '提示', { type: 'warning' })
        .then(async () => {
          await coaApi.deleteNode(row.id)
          this.$message.success('删除成功')
          this.loadTree()
        })
        .catch(() => {})
    },
    async onSubmit() {
      await this.$refs.formRef.validate()
      this.submitting = true
      try {
        const data = {
          schemeId: this.filterSchemeId,
          nodeCode: this.form.nodeCode,
          nodeName: this.form.nodeName,
          sortOrder: this.form.sortOrder,
          parentId: this.form.parentPath.length
            ? this.form.parentPath[this.form.parentPath.length - 1]
            : null
        }
        if (this.editing) {
          await coaApi.updateNode(this.editing.id, data)
        } else {
          await coaApi.createNode(data)
        }
        this.$message.success('保存成功')
        this.modalVisible = false
        this.loadTree()
      } finally { this.submitting = false }
    }
  }
}
</script>

<style scoped>
.coa-page { padding: 0; }
.page-header {
  background: #fff;
  padding: 16px 24px;
  margin-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}
.page-header h2 { margin: 0; }
.page-header .desc { color: #999; font-size: 13px; margin: 4px 0 0; }
.filter-card { margin: 0 16px 16px; }
.table-card { margin: 0 16px; }
</style>

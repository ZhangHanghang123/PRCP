import axios, { AxiosInstance } from 'axios'
import { message } from 'antd'

const TOKEN_KEY = 'prcp_token'
export const getToken = () => localStorage.getItem(TOKEN_KEY) || ''
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

const http: AxiosInstance = axios.create({ baseURL: '/prcp/api', timeout: 30000 })
http.interceptors.request.use((c) => {
  const t = getToken(); if (t) c.headers.Authorization = `Bearer ${t}`; return c
})
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      clearToken()
      if (!location.pathname.includes('/login')) location.href = '/prcp/login'
    } else if (err.response?.data?.detail) {
      const d = err.response.data.detail
      message.error(typeof d === 'string' ? d : JSON.stringify(d))
    } else if (err.message) message.error(err.message)
    return Promise.reject(err)
  }
)

export const authApi = {
  login: (username: string, password: string) => {
    const fd = new FormData(); fd.append('username', username); fd.append('password', password)
    return http.post('/auth/login', fd).then((r) => r.data)
  },
  me: () => http.get('/auth/me').then((r) => r.data),
}
export const dashboardApi = {
  overview: () => http.get('/dashboard/overview').then((r) => r.data),
  kpiTrend: (days = 14) => http.get('/dashboard/kpi-trend', { params: { days } }).then((r) => r.data),
  schemeDistribution: () => http.get('/dashboard/scheme-distribution').then((r) => r.data),
}

// metricItemsApi 已废弃：193 条数据已迁移到 prcp_rpt_item，请使用 reportsApi

// 账户册
export const coaApi = {
  listSchemes: (params: any = {}) => http.get('/coa/schemes', { params }).then((r) => r.data),
  createScheme: (data: any) => http.post('/coa/schemes', data).then((r) => r.data),
  updateScheme: (id: number, data: any) => http.put(`/coa/schemes/${id}`, data).then((r) => r.data),
  deleteScheme: (id: number) => http.delete(`/coa/schemes/${id}`).then((r) => r.data),
  listNodes: (schemeId: number) => http.get('/coa/nodes', { params: { scheme_id: schemeId } }).then((r) => r.data),
  treeNodes: (schemeId: number) => http.get('/coa/nodes/tree', { params: { scheme_id: schemeId } }).then((r) => r.data),
  createNode: (data: any) => http.post('/coa/nodes', data).then((r) => r.data),
  updateNode: (id: number, data: any) => http.put(`/coa/nodes/${id}`, data).then((r) => r.data),
  deleteNode: (id: number) => http.delete(`/coa/nodes/${id}`).then((r) => r.data),
}

// 报表
export const reportsApi = {
  list: (params: any = {}) => http.get('/reports/', { params }).then((r) => r.data),
  create: (data: any) => http.post('/reports/', data).then((r) => r.data),
  update: (id: number, data: any) => http.put(`/reports/${id}`, data).then((r) => r.data),
  delete: (id: number) => http.delete(`/reports/${id}`).then((r) => r.data),
  listItems: (reportId: number) => http.get('/reports/items', { params: { report_id: reportId } }).then((r) => r.data),
  treeItems: (reportId: number) => http.get('/reports/items/tree', { params: { report_id: reportId } }).then((r) => r.data),
  createItem: (data: any) => http.post('/reports/items', data).then((r) => r.data),
  updateItem: (id: number, data: any) => http.put(`/reports/items/${id}`, data).then((r) => r.data),
  deleteItem: (id: number) => http.delete(`/reports/items/${id}`).then((r) => r.data),
  batchItems: (reportId: number, payload: any) => http.post('/reports/items/batch', payload, { params: { report_id: reportId } }).then((r) => r.data),
}

// 资产负债表
export const balanceApi = {
  list: (params: any = {}) => http.get('/balance/', { params }).then((r) => r.data),
  upsert: (data: any) => http.post('/balance/', data).then((r) => r.data),
  delete: (id: number) => http.delete(`/balance/${id}`).then((r) => r.data),
  gapSummary: (dataDate: string) => http.get('/balance/gap-summary', { params: { data_date: dataDate } }).then((r) => r.data),
  // 新设计：按方案 + 数据日期聚合 + 大类汇总 + 日期历史
  byScheme: (scheme_id: number, data_date: string) =>
    http.get('/balance/by-scheme', { params: { scheme_id, data_date } }).then((r) => r.data),
  listDates: (scheme_id?: number) =>
    http.get('/balance/dates', { params: scheme_id ? { scheme_id } : {} }).then((r) => r.data),
  categorySummary: (data_date: string, scheme_id?: number) =>
    http.get('/balance/category-summary', { params: { data_date, scheme_id } }).then((r) => r.data),
  // 二级表头矩阵：行=账户册 / 列=月份 / 单元格=7度量
  bySchemeMatrix: (scheme_id: number, start_date: string, end_date: string) =>
    http.get('/balance/by-scheme-matrix', { params: { scheme_id, start_date, end_date } }).then((r) => r.data),
  // 导入导出（fetch 直接拉二进制流，必须用绝对路径避免 baseURL 丢失）
  exportXlsxUrl: (scheme_id: number, start_date: string, end_date: string) =>
    `/prcp/api/balance/export-xlsx?scheme_id=${scheme_id}&start_date=${start_date}&end_date=${end_date}`,
  importXlsx: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/balance/import-xlsx', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },
}

// 基础数据表（按账户册 + 数据日期 + 日期偏移量的二维矩阵）
export const basicApi = {
  list: (params: any = {}) => http.get('/basic/', { params }).then((r) => r.data),
  upsert: (data: any) => http.post('/basic/', data).then((r) => r.data),
  delete: (id: number) => http.delete(`/basic/${id}`).then((r) => r.data),
  listDates: (scheme_id?: number) =>
    http.get('/basic/dates', { params: scheme_id ? { scheme_id } : {} }).then((r) => r.data),
  bySchemeMatrix: (scheme_id: number, data_date: string, date_offset = 0, offset_unit = 'D') =>
    http.get('/basic/by-scheme-matrix', { params: { scheme_id, data_date, date_offset, offset_unit } }).then((r) => r.data),
  exportXlsxUrl: (scheme_id: number, data_date: string, date_offset = 0, offset_unit = 'D') =>
    `/prcp/api/basic/export-xlsx?scheme_id=${scheme_id}&data_date=${data_date}&date_offset=${date_offset}&offset_unit=${offset_unit}`,
  importXlsx: (file: File, scheme_id: number, data_date: string, date_offset = 0, offset_unit = 'D') => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/basic/import-xlsx', fd, {
      params: { scheme_id, data_date, date_offset, offset_unit },
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },
}

// 指标（v2：方案 + 定义 + 维护）
export const kpiApi = {
  // 方案
  listSchemes: (params: any = {}) => http.get('/kpi/schemes', { params }).then((r) => r.data),
  createScheme: (data: any) => http.post('/kpi/schemes', data).then((r) => r.data),
  updateScheme: (id: number, data: any) => http.put(`/kpi/schemes/${id}`, data).then((r) => r.data),
  deleteScheme: (id: number) => http.delete(`/kpi/schemes/${id}`).then((r) => r.data),
  // 报表表项（供定义公式引用）
  listRptItems: (params: any = {}) => http.get('/kpi/rpt-items', { params }).then((r) => r.data),
  // 定义
  listDefs: (params: any = {}) => http.get('/kpi/definitions', { params }).then((r) => r.data),
  createDef: (data: any) => http.post('/kpi/definitions', data).then((r) => r.data),
  updateDef: (id: number, data: any) => http.put(`/kpi/definitions/${id}`, data).then((r) => r.data),
  deleteDef: (id: number) => http.delete(`/kpi/definitions/${id}`).then((r) => r.data),
  // 值
  listValues: (params: any = {}) => http.get('/kpi/values', { params }).then((r) => r.data),
  upsertValue: (data: any) => http.post('/kpi/values', data).then((r) => r.data),
  deleteValue: (id: number) => http.delete(`/kpi/values/${id}`).then((r) => r.data),
  // 试算分数（指标维护页专用）
  listValueDates: (scheme_id: number) => http.get('/kpi/value-dates', { params: { scheme_id } }).then((r) => r.data),
  calcScore: (scheme_id: number, data_date: string, kpi_id?: number) =>
    http.post('/kpi/values/calc-score', { scheme_id, data_date, kpi_id }).then((r) => r.data),
  // 公式引擎
  formulaEval: (formula: string, ctx: any = {}) => http.post('/kpi/formula/eval', { formula, ctx }).then((r) => r.data),
  formulaValidate: (formula: string) => http.post('/kpi/formula/validate', { formula }).then((r) => r.data),
  listFunctionScripts: () => http.get('/kpi/functions/scripts').then((r) => r.data),
  recalc: (kpiId: number, dataDate: string) =>
    http.post('/kpi/recalc', null, { params: { kpi_id: kpiId, data_date: dataDate } }).then((r) => r.data),
  // 评分规则
  listScoreRules: (params: any = {}) => http.get('/kpi/score-rules', { params }).then((r) => r.data),
  createScoreRule: (data: any) => http.post('/kpi/score-rules', data).then((r) => r.data),
  updateScoreRule: (id: number, data: any) => http.put(`/kpi/score-rules/${id}`, data).then((r) => r.data),
  deleteScoreRule: (id: number) => http.delete(`/kpi/score-rules/${id}`).then((r) => r.data),
  scoreCalc: (ruleId: number, value: number) => http.post('/kpi/score-calc', { rule_id: ruleId, value }).then((r) => r.data),
}

// 系统管理：用户 / 角色 / 字典
export const adminApi = {
  // 用户
  listUsers: (params: any = {}) => http.get('/admin/users', { params }).then((r) => r.data),
  createUser: (data: any) => http.post('/admin/users', data).then((r) => r.data),
  updateUser: (id: number, data: any) => http.put(`/admin/users/${id}`, data).then((r) => r.data),
  deleteUser: (id: number) => http.delete(`/admin/users/${id}`).then((r) => r.data),
  resetPassword: (id: number, new_password: string) =>
    http.post(`/admin/users/${id}/reset-password`, { new_password }).then((r) => r.data),
  // 角色
  listRoles: (params: any = {}) => http.get('/admin/roles', { params }).then((r) => r.data),
  createRole: (data: any) => http.post('/admin/roles', data).then((r) => r.data),
  updateRole: (id: number, data: any) => http.put(`/admin/roles/${id}`, data).then((r) => r.data),
  deleteRole: (id: number) => http.delete(`/admin/roles/${id}`).then((r) => r.data),
  // 字典：已迁移至 src/api/dict.ts（基于 sys_dict 平铺表），旧 admin/dicts 接口下线
}

// 数据维护（6 类指标 + 取数逻辑 + 按月出指标）
export const dataMaintApi = {
  listCategories: () => http.get('/data-maint/categories').then((r) => r.data),
  listItems: (params: any = {}) => http.get('/data-maint/items', { params }).then((r) => r.data),
  // 树形表格聚合：items 树 + values_map
  treeWithValues: (category: string, dataDate: string) =>
    http.get('/data-maint/items/tree-with-values', { params: { category, data_date: dataDate } }).then((r) => r.data),
  saveItemValue: (itemId: number, data: any) => http.put(`/data-maint/items/${itemId}/value`, data).then((r) => r.data),
  saveCalcRule: (itemId: number, data: any) => http.put(`/data-maint/items/${itemId}/calc-rule`, data).then((r) => r.data),
  listValues: (params: any = {}) => http.get('/data-maint/values', { params }).then((r) => r.data),
  upsertValue: (data: any) => http.post('/data-maint/values', data).then((r) => r.data),
  deleteValue: (id: number) => http.delete(`/data-maint/values/${id}`).then((r) => r.data),
  calcPreview: (itemId: number, dataDate: string) => http.get('/data-maint/calc-preview', { params: { item_id: itemId, data_date: dataDate } }).then((r) => r.data),
  monthlyCalc: (data: any) => http.post('/data-maint/monthly-calc', data).then((r) => r.data),
  listMonths: () => http.get('/data-maint/months').then((r) => r.data),
}

// 模型管理：模型 / 版本 / 参数 / 训练
export const modelApi = {
  // 算法
  listAlgorithms: () => http.get('/model/algorithms').then((r) => r.data),
  // 模型
  listModels: (params: any = {}) => http.get('/model/models', { params }).then((r) => r.data),
  createModel: (data: any) => http.post('/model/models', data).then((r) => r.data),
  updateModel: (id: number, data: any) => http.put(`/model/models/${id}`, data).then((r) => r.data),
  deleteModel: (id: number) => http.delete(`/model/models/${id}`).then((r) => r.data),
  // 版本
  listVersions: (params: any = {}) => http.get('/model/versions', { params }).then((r) => r.data),
  createVersion: (data: any) => http.post('/model/versions', data).then((r) => r.data),
  updateVersion: (id: number, data: any) => http.put(`/model/versions/${id}`, data).then((r) => r.data),
  deleteVersion: (id: number) => http.delete(`/model/versions/${id}`).then((r) => r.data),
  copyVersion: (id: number, data: any) => http.post(`/model/versions/${id}/copy`, data).then((r) => r.data),
  // 参数
  listParams: (params: any = {}) => http.get('/model/params', { params }).then((r) => r.data),
  createParam: (data: any) => http.post('/model/params', data).then((r) => r.data),
  updateParam: (id: number, data: any) => http.put(`/model/params/${id}`, data).then((r) => r.data),
  deleteParam: (id: number) => http.delete(`/model/params/${id}`).then((r) => r.data),
  // KPI 下拉选项
  kpiOptions: () => http.get('/model/kpi-options').then((r) => r.data),
  // 指标方案下拉选项
  schemeOptions: () => http.get('/model/scheme-options').then((r) => r.data),
  // 超参数模板
  listParamTemplates: () => http.get('/model/param-templates').then((r) => r.data),
  applyParamTemplate: (versionId: number, payload: any) =>
    http.post(`/model/versions/${versionId}/apply-template`, payload).then((r) => r.data),
  // 训练
  listTrains: (params: any = {}) => http.get('/model/trains', { params }).then((r) => r.data),
  createTrain: (data: any) => http.post('/model/trains', data).then((r) => r.data),
  startTrain: (id: number) => http.post(`/model/trains/${id}/start`).then((r) => r.data),
  cancelTrain: (id: number) => http.post(`/model/trains/${id}/cancel`).then((r) => r.data),
  deleteTrain: (id: number) => http.delete(`/model/trains/${id}`).then((r) => r.data),
  trainLogs: (id: number, sinceId = 0) =>
    http.get(`/model/trains/${id}/logs`, { params: { since_id: sinceId } }).then((r) => r.data),
  trainResult: (id: number) => http.get(`/model/trains/${id}/result`).then((r) => r.data),
}

// 组合反算：方案 / 目标 / 运行 / 结果
export const reverseApi = {
  // 算法
  listAlgorithms: () => http.get('/reverse/algorithms').then((r) => r.data),
  // 方案
  listSchemes: (params: any = {}) => http.get('/reverse/schemes', { params }).then((r) => r.data),
  createScheme: (data: any) => http.post('/reverse/schemes', data).then((r) => r.data),
  updateScheme: (id: number, data: any) => http.put(`/reverse/schemes/${id}`, data).then((r) => r.data),
  deleteScheme: (id: number) => http.delete(`/reverse/schemes/${id}`).then((r) => r.data),
  // 计量模型下拉
  modelOptions: () => http.get('/reverse/model-options').then((r) => r.data),
  // 目标
  listTargets: (params: any = {}) => http.get('/reverse/targets', { params }).then((r) => r.data),
  createTarget: (data: any) => http.post('/reverse/targets', data).then((r) => r.data),
  updateTarget: (id: number, data: any) => http.put(`/reverse/targets/${id}`, data).then((r) => r.data),
  deleteTarget: (id: number) => http.delete(`/reverse/targets/${id}`).then((r) => r.data),
  kpiOptions: () => http.get('/reverse/kpi-options').then((r) => r.data),
  // 运行
  listRuns: (params: any = {}) => http.get('/reverse/runs', { params }).then((r) => r.data),
  createRun: (data: any) => http.post('/reverse/runs', data).then((r) => r.data),
  startRun: (id: number) => http.post(`/reverse/runs/${id}/start`).then((r) => r.data),
  cancelRun: (id: number) => http.post(`/reverse/runs/${id}/cancel`).then((r) => r.data),
  deleteRun: (id: number) => http.delete(`/reverse/runs/${id}`).then((r) => r.data),
  runLogs: (id: number, sinceId = 0) =>
    http.get(`/reverse/runs/${id}/logs`, { params: { since_id: sinceId } }).then((r) => r.data),
  runResult: (id: number) => http.get(`/reverse/runs/${id}/result`).then((r) => r.data),
}

export const dataReverseApi = {
  schemes: () => http.get('/data-reverse/schemes').then((r) => r.data),
  runs: (schemeCode?: string) =>
    http.get('/data-reverse/runs', { params: { scheme_code: schemeCode } }).then((r) => r.data),
  bySchemeMatrix: (params: {
    scheme_code: string; run_id?: number;
    data_date?: string; date_offset?: number; offset_unit?: string;
  }) => http.get('/data-reverse/by-scheme-matrix', { params }).then((r) => r.data),
  dates: (schemeCode: string, runId?: number) =>
    http.get('/data-reverse/dates', { params: { scheme_code: schemeCode, run_id: runId } }).then((r) => r.data),
  exportXlsxUrl: (schemeCode: string, runId?: number) =>
    `/prcp/api/data-reverse/export-xlsx?scheme_code=${encodeURIComponent(schemeCode)}${runId ? `&run_id=${runId}` : ''}`,
}

export const rateApi = {
  // 曲线方案
  listSchemes: (params: any = {}) => http.get('/rate/schemes', { params }).then((r) => r.data),
  createScheme: (data: any) => http.post('/rate/schemes', data).then((r) => r.data),
  updateScheme: (id: number, data: any) => http.put(`/rate/schemes/${id}`, data).then((r) => r.data),
  deleteScheme: (id: number) => http.delete(`/rate/schemes/${id}`).then((r) => r.data),
  // 利率点
  listPoints: (params: any = {}) => http.get('/rate/points', { params }).then((r) => r.data),
  upsertPoint: (data: any) => http.post('/rate/points', data).then((r) => r.data),
  deletePoint: (id: number) => http.delete(`/rate/points/${id}`).then((r) => r.data),
  // 历史对比
  compare: (curveCode: string, startDate?: string, endDate?: string) =>
    http.get('/rate/compare', {
      params: { curve_code: curveCode, start_date: startDate, end_date: endDate },
    }).then((r) => r.data),
  // 单一查询
  lookup: (curveCode: string, dataDate: string, term: string) =>
    http.get('/rate/lookup', {
      params: { curve_code: curveCode, data_date: dataDate, term },
    }).then((r) => r.data),
  exportXlsxUrl: (curveCode: string) =>
    `/prcp/api/rate/export-xlsx?curve_code=${encodeURIComponent(curveCode)}`,
}
/** PRCP ESG 场景工厂 · 前端 API 客户端
 *
 * 完整封装 backend/app/routers/esg.py 22 endpoint
 * 与 esg.ts 后端 1:1 对应
 */
import { http } from './index'

// ============== TypeScript 类型 ==============

export interface EsgScheme {
  id: number
  scheme_code: string
  scheme_name: string
  description?: string
  data_source: 'ECB' | 'FRB' | 'CUSTOM' | 'BANK'
  start_date?: string
  end_date?: string
  n_factors: number
  maturities_months: number[]
  n_scenarios: number
  n_steps: number
  seed: number
  initial_yields_pct?: number[] | null
  status: 'DRAFT' | 'READY' | 'ARCHIVED'
  run_count?: number
  last_run_at?: string | null
  created_at?: string
  updated_at?: string
}

export interface EsgRun {
  id: number
  scheme_id: number
  scheme_code?: string
  run_type: 'PCA_FIT' | 'HJM_GENERATE' | 'SCENARIO_GENERATE'
  status: 'SUCCESS' | 'FAILED' | 'RUNNING'
  params?: any
  output?: any
  file_path?: string
  duration_ms?: number
  error_message?: string
  created_at?: string
}

export interface EsgScenario {
  id: number
  scheme_id: number
  scenario_code: string
  scenario_type: string
  file_path: string
  n_scenarios: number
  n_steps: number
  n_maturities: number
  seed?: number
  maturities_months?: number[]
  file_size_bytes?: number
  description?: string
  created_at?: string
}

export interface YieldCurvePoint {
  id: number
  curve_date: string
  source: 'ECB' | 'FRB' | 'CUSTOM' | 'BANK'
  theta0: number
  theta1: number
  theta2: number
  theta3: number
  lambda1: number
  lambda2: number
  description?: string
  created_at?: string
}

export interface SourceStat {
  source: string
  count: number
  min_date?: string
  max_date?: string
}

export interface SvenssonRates {
  source: string
  curve_date: string
  tenors_months: number[]
  rates_pct: number[]
  rates_decimal: number[]
}

// ============== ESG 方案 API ==============

export const esgApi = {
  // 方案 CRUD
  listSchemes: (params: { keyword?: string; status?: string; page?: number; page_size?: number } = {}) =>
    http.get('/esg/schemes', { params }).then((r) => r.data),
  createScheme: (data: Partial<EsgScheme>) =>
    http.post('/esg/schemes', data).then((r) => r.data),
  getScheme: (id: number) => http.get(`/esg/schemes/${id}`).then((r) => r.data),
  updateScheme: (id: number, data: Partial<EsgScheme>) =>
    http.put(`/esg/schemes/${id}`, data).then((r) => r.data),
  deleteScheme: (id: number) => http.delete(`/esg/schemes/${id}`).then((r) => r.data),
  cloneScheme: (id: number, newCode: string, newName?: string) =>
    http.post(`/esg/schemes/${id}/clone`, {
      new_scheme_code: newCode,
      new_scheme_name: newName,
    }).then((r) => r.data),

  // 三步执行
  fitPca: (id: number, n_factors?: number) =>
    http.post(`/esg/schemes/${id}/fit-pca`, n_factors ? { n_factors } : {}).then((r) => r.data),
  generateHjm: (id: number, params: { n_scenarios?: number; n_steps?: number; seed?: number } = {}) =>
    http.post(`/esg/schemes/${id}/generate-hjm`, params).then((r) => r.data),
  generateScenario: (id: number) =>
    http.post(`/esg/schemes/${id}/generate`, {}).then((r) => r.data),
  runAll: (id: number) =>
    http.post(`/esg/schemes/${id}/run-all`, {}).then((r) => r.data),

  // 运行历史
  listSchemeRuns: (id: number, params: { run_type?: string; status?: string; limit?: number } = {}) =>
    http.get(`/esg/schemes/${id}/runs`, { params }).then((r) => r.data),
  listAllRuns: (params: { scheme_id?: number; run_type?: string; status?: string; page?: number; page_size?: number } = {}) =>
    http.get('/esg/runs', { params }).then((r) => r.data),
  getRun: (runId: number) => http.get(`/esg/runs/${runId}`).then((r) => r.data),

  // 情景集
  listScenarios: (params: { scheme_id?: number; page?: number; page_size?: number } = {}) =>
    http.get('/esg/scenarios', { params }).then((r) => r.data),
  getScenario: (scenarioCode: string) =>
    http.get(`/esg/scenarios/${scenarioCode}`).then((r) => r.data),
  downloadScenarioUrl: (scenarioCode: string) =>
    `/prcp/api/esg/scenarios/${scenarioCode}/download`,

  // 一键案例
  runOneClickCase: (data_source?: string) =>
    http.post('/esg/case/run', data_source ? { data_source } : {}).then((r) => r.data),

  // 缓存诊断
  cacheInfo: () => http.get('/esg/cache-info').then((r) => r.data),
}

// ============== Svensson 曲线 API ==============

export const yieldCurveApi = {
  list: (params: { source?: string; start_date?: string; end_date?: string; page?: number; page_size?: number } = {}) =>
    http.get('/esg/curves', { params }).then((r) => r.data),
  sources: () => http.get('/esg/curves/sources').then((r) => r.data),
  get: (curveDate: string, source?: string) =>
    http.get(`/esg/curves/${curveDate}`, { params: source ? { source } : {} }).then((r) => r.data),
  upsert: (point: Omit<YieldCurvePoint, 'id' | 'created_at'>) =>
    http.post('/esg/curves', point).then((r) => r.data),
  bulkUpsert: (points: Array<Omit<YieldCurvePoint, 'id' | 'created_at'>>) =>
    http.post('/esg/curves/bulk', { points }).then((r) => r.data),
  rates: (curveDate: string, body: { tenors: number[]; source?: string }) =>
    http.post(`/esg/curves/${curveDate}/rates`, body).then((r) => r.data),
}

// 默认 13 期限点（与 backend DEFAULT_MATURITIES_MONTHS 对齐）
export const DEFAULT_MATURITIES_MONTHS = [1, 3, 6, 12, 24, 36, 48, 60, 84, 120, 180, 240, 360]

// 数据源选项
export const ESG_SOURCE_OPTIONS = [
  { value: 'ECB', label: '欧洲央行 (ECB)', color: 'blue' },
  { value: 'FRB', label: '美联储 (FRB)', color: 'red' },
  { value: 'CUSTOM', label: '自定义', color: 'cyan' },
  { value: 'BANK', label: '本行加点', color: 'gold' },
]

// 状态选项
export const ESG_STATUS_OPTIONS = [
  { value: 'DRAFT', label: '草稿', color: 'default' },
  { value: 'READY', label: '就绪', color: 'green' },
  { value: 'ARCHIVED', label: '已归档', color: 'gray' },
]

export const ESG_RUN_TYPE_OPTIONS = [
  { value: 'PCA_FIT', label: 'PCA 拟合', color: 'blue' },
  { value: 'HJM_GENERATE', label: 'HJM 建模', color: 'cyan' },
  { value: 'SCENARIO_GENERATE', label: '情景集生成', color: 'purple' },
]

export const ESG_RUN_STATUS_OPTIONS = [
  { value: 'SUCCESS', label: '成功', color: 'green' },
  { value: 'FAILED', label: '失败', color: 'red' },
  { value: 'RUNNING', label: '运行中', color: 'blue' },
]
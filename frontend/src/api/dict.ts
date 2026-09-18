import { http } from './index'

/**
 * PRCP 字典管理 API（系统管理 → 字典管理 Tab 使用）
 *
 * 与 DictProvider / useDict 读路径不同，这里是管理端写路径
 * 统一用带 JWT 拦截器的 http 实例，避免 401
 */
export const dictApi = {
  /** 列出所有字典类别（含每类数量） */
  listTypes: () => http.get('/dict/types').then((r) => r.data),
  /** 按类型列出字典项（管理端用，看 DEPRECATED 等所有项） */
  listByType: (dictType: string, keyword = '') =>
    http.get(`/dict/${dictType}`, { params: { keyword } }).then((r) => r.data),
  /** 新增字典项 */
  create: (data: any) => http.post('/dict', data).then((r) => r.data),
  /** 更新字典项 */
  update: (id: number, data: any) => http.put(`/dict/${id}`, data).then((r) => r.data),
  /** 软删除字典项 */
  remove: (id: number) => http.delete(`/dict/${id}`).then((r) => r.data),
}

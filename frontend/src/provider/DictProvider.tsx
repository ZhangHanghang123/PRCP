/**
 * PRCP 全局字典 Context
 *
 * 设计：
 *  - 启动时一次性 GET /dict/types/items 拉取所有字典
 *  - 提供 useDict(type) 获取字典项数组
 *  - 提供 getLabel(type, key) / getColor(type, key) / getOptions(type) 便捷方法
 *  - 提供 reloadDict() 用于字典管理页新增/修改后刷新
 */
import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import axios from 'axios'

export interface DictItem {
  id: number
  dict_type: string
  dict_key: string
  dict_label: string
  color?: string
  sort_order: number
  status: string
  extra?: any
}

interface DictContextValue {
  dicts: Record<string, DictItem[]>
  loading: boolean
  reloadDict: () => Promise<void>
  getItems: (type: string) => DictItem[]
  getOptions: (type: string) => { value: string; label: string; color?: string }[]
  getLabel: (type: string, key: string, fallback?: string) => string
  getColor: (type: string, key: string, fallback?: string) => string | undefined
}

const DictContext = createContext<DictContextValue | undefined>(undefined)

export function DictProvider({ children }: { children: ReactNode }) {
  const [dicts, setDicts] = useState<Record<string, DictItem[]>>({})
  const [loading, setLoading] = useState(false)

  const reloadDict = useCallback(async () => {
    setLoading(true)
    try {
      const r = await axios.get('/prcp/api/dict/types/items')
      setDicts(r.data?.items || {})
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { reloadDict() }, [reloadDict])

  const getItems = useCallback((type: string) => dicts[type] || [], [dicts])

  const getOptions = useCallback((type: string) => {
    return (dicts[type] || []).map(d => ({
      value: d.dict_key,
      label: d.dict_label,
      color: d.color,
    }))
  }, [dicts])

  const getLabel = useCallback((type: string, key: string, fallback?: string) => {
    const item = (dicts[type] || []).find(d => d.dict_key === key)
    return item?.dict_label || fallback || key
  }, [dicts])

  const getColor = useCallback((type: string, key: string, fallback?: string) => {
    const item = (dicts[type] || []).find(d => d.dict_key === key)
    return item?.color || fallback
  }, [dicts])

  return (
    <DictContext.Provider value={{ dicts, loading, reloadDict, getItems, getOptions, getLabel, getColor }}>
      {children}
    </DictContext.Provider>
  )
}

export function useDictContext() {
  const ctx = useContext(DictContext)
  if (!ctx) throw new Error('useDictContext must be used inside DictProvider')
  return ctx
}

/** 便捷 hook：获取指定类型的字典项数组 */
export function useDict(type: string): DictItem[] {
  const { getItems } = useDictContext()
  return getItems(type)
}

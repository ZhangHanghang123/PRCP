/**
 * PRCP DictSelect 通用下拉组件
 *
 * 用法：
 *   <DictSelect dictType="PRCP_ALGO" />
 *   <DictSelect dictType="PRCP_STATUS" value={status} onChange={setStatus} />
 *   <DictSelect dictType="PRCP_BIZ_DOMAIN" allowClear showSearch />
 *
 * 自动从 DictProvider 拉取字典项并渲染为 Select
 */
import React from 'react'
import { Select } from 'antd'
import { useDict } from '../provider/DictProvider'

export interface DictSelectProps {
  dictType: string
  value?: any
  onChange?: (value: any) => void
  placeholder?: string
  allowClear?: boolean
  showSearch?: boolean
  disabled?: boolean
  mode?: 'multiple' | 'tags'
  style?: React.CSSProperties
  /** 过滤函数：返回 true 的项才显示 */
  filter?: (item: { value: string; label: string; color?: string }) => boolean
}

export function DictSelect({
  dictType,
  value,
  onChange,
  placeholder,
  allowClear,
  showSearch,
  disabled,
  mode,
  style,
  filter,
}: DictSelectProps) {
  const items = useDict(dictType)
  let options = items.map(d => ({
    value: d.dict_key,
    label: d.dict_label,
    color: d.color,
  }))
  if (filter) options = options.filter(filter)

  return (
    <Select
      style={{ minWidth: 140, ...style }}
      value={value}
      onChange={onChange}
      placeholder={placeholder || '请选择'}
      allowClear={allowClear}
      showSearch={showSearch}
      disabled={disabled}
      mode={mode}
      optionFilterProp="label"
      options={options}
    />
  )
}

export default DictSelect

/**
 * PRCP DictTag 通用彩色标签组件
 *
 * 用法：
 *   <DictTag dictType="PRCP_STATUS" value="ACTIVE" />
 *   <DictTag dictType="PRCP_RUN_STATUS" value="RUNNING" />
 *
 * 自动从 DictProvider 查颜色和中文标签
 */
import React from 'react'
import { Tag } from 'antd'
import { useDictContext } from '../provider/DictProvider'

export interface DictTagProps {
  dictType: string
  value?: string | null
  fallbackColor?: string
  style?: React.CSSProperties
  onClick?: () => void
}

export function DictTag({ dictType, value, fallbackColor, style, onClick }: DictTagProps) {
  const { getLabel, getColor } = useDictContext()
  if (value == null || value === '') return <span style={{ color: '#ccc' }}>-</span>
  return (
    <Tag
      color={getColor(dictType, String(value), fallbackColor)}
      style={style}
      onClick={onClick}
    >
      {getLabel(dictType, String(value))}
    </Tag>
  )
}

export default DictTag

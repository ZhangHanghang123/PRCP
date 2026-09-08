import React, { useEffect, useMemo, useState } from 'react'
import {
  Card, Tabs, Tree, Table, Tag, Input, Space, Button, message, Spin, Empty, Tooltip,
} from 'antd'
import {
  ReloadOutlined, SearchOutlined, DownloadOutlined, CloudUploadOutlined,
  ApartmentOutlined, TableOutlined, FileExcelOutlined,
} from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import type { ColumnsType } from 'antd/es/table'
import { metricItemsApi } from '../api'

interface MetricItem {
  id: number
  category: string
  code: string
  name: string
  level: number
  parent_code: string | null
  path: string
  is_leaf: boolean
  sort_order: number
}

interface Category {
  code: string
  name: string
  icon: string
  color: string
  count: number
}

const MetricItems: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([])
  const [activeCat, setActiveCat] = useState<string>('FINANCIAL')
  const [tree, setTree] = useState<any[]>([])
  const [flat, setFlat] = useState<MetricItem[]>([])
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)

  // 加载分类
  useEffect(() => {
    metricItemsApi.categories().then((r) => {
      setCategories(r.items || [])
      if (r.items?.length && !r.items.find((c: Category) => c.code === activeCat)) {
        setActiveCat(r.items[0].code)
      }
    }).catch(() => message.error('分类加载失败'))
  }, [])

  // 切换分类
  useEffect(() => {
    if (!activeCat) return
    setLoading(true)
    setSelectedKey(null)
    Promise.all([
      metricItemsApi.tree(activeCat),
      metricItemsApi.list({ category: activeCat }),
    ]).then(([t, l]) => {
      setTree(t.items || [])
      setFlat(l.items || [])
    }).catch(() => message.error('数据加载失败'))
      .finally(() => setLoading(false))
  }, [activeCat])

  // 树结构
  const treeData: DataNode[] = useMemo(() => {
    const toNode = (n: any): DataNode => ({
      key: n.key,
      title: (
        <span>
          <Tag color={n.level === 1 ? 'blue' : n.level === 2 ? 'cyan' : 'default'} style={{ marginRight: 6 }}>
            L{n.level}
          </Tag>
          {n.title}
          {!n.is_leaf && <span style={{ color: '#999', marginLeft: 6 }}>({countChildren(n)})</span>}
        </span>
      ),
      children: n.children?.length ? n.children.map(toNode) : undefined,
    })
    return tree.map(toNode)
  }, [tree])

  function countChildren(n: any): number {
    if (!n.children?.length) return 0
    return n.children.reduce((acc: number, c: any) => acc + 1 + countChildren(c), 0)
  }

  // 当前选中节点的子项（直系子）
  const selectedChildren = useMemo(() => {
    if (!selectedKey) return []
    const [code, ...nameParts] = selectedKey.split('|')
    const name = nameParts.join('|')
    return flat.filter((it) => it.parent_code === code && it.name === name)
      || flat.filter((it) => it.parent_code === code)
  }, [selectedKey, flat])

  // 关键词搜索
  const filteredFlat = useMemo(() => {
    if (!keyword) return flat
    const kw = keyword.toLowerCase()
    return flat.filter((it) => it.name.toLowerCase().includes(kw) || it.code.includes(kw))
  }, [flat, keyword])

  // 表格列
  const tableCols: ColumnsType<MetricItem> = [
    { title: '层级', dataIndex: 'level', width: 70, render: (lv: number) => <Tag color={lv === 1 ? 'blue' : lv === 2 ? 'cyan' : 'default'}>L{lv}</Tag> },
    { title: '编码', dataIndex: 'code', width: 110, render: (c: string) => <code style={{ background: '#f5f5f5', padding: '1px 6px', borderRadius: 3 }}>{c}</code> },
    { title: '指标名称', dataIndex: 'name', ellipsis: true },
    { title: '父编码', dataIndex: 'parent_code', width: 110, render: (c: string | null) => c ? <code>{c}</code> : <span style={{ color: '#999' }}>—</span> },
    { title: '叶子', dataIndex: 'is_leaf', width: 60, render: (v: boolean) => v ? <Tag color="green">是</Tag> : <Tag>否</Tag> },
    { title: '路径', dataIndex: 'path', width: 240, render: (p: string) => <span style={{ color: '#999', fontSize: 12 }}>{p}</span> },
  ]

  // 选中树节点 → 滚动到对应行 / 过滤
  const onSelectTree = (keys: React.Key[]) => {
    if (!keys.length) { setSelectedKey(null); return }
    setSelectedKey(String(keys[0]))
  }

  // 导出 CSV
  const exportCsv = () => {
    const header = '层级,编码,指标名称,父编码,叶子\n'
    const lines = flat.map((it) =>
      [it.level, it.code, `"${it.name.replace(/"/g, '""')}"`, it.parent_code || '', it.is_leaf ? '是' : '否'].join(',')
    ).join('\n')
    const blob = new Blob(['\uFEFF' + header + lines], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `PRCP_指标项_${activeCat}_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  // 重新导入
  const reimport = async () => {
    setImporting(true)
    try {
      const r = await metricItemsApi.importFromXlsx()
      message.success(r.message || `已导入 ${r.total} 条`)
      // 刷新
      const cats = await metricItemsApi.categories()
      setCategories(cats.items || [])
      const t = await metricItemsApi.tree(activeCat)
      setTree(t.items || [])
      const l = await metricItemsApi.list({ category: activeCat })
      setFlat(l.items || [])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '导入失败')
    } finally {
      setImporting(false)
    }
  }

  const activeCatMeta = categories.find((c) => c.code === activeCat)

  return (
    <Spin spinning={loading}>
      <div className="page-title">
        <span className="page-title-icon" />
        <span>指标项管理 <span style={{ color: '#999', fontSize: 14, fontWeight: 'normal' }}>· 数据维护模块</span></span>
      </div>

      <Card
        bordered={false}
        bodyStyle={{ padding: 0 }}
        title={
          <Tabs
            activeKey={activeCat}
            onChange={setActiveCat}
            items={categories.map((c) => ({
              key: c.code,
              label: (
                <span>
                  <span style={{ marginRight: 6 }}>{c.icon}</span>
                  {c.name}
                  <Tag style={{ marginLeft: 8 }} color={c.color}>{c.count}</Tag>
                </span>
              ),
            }))}
          />
        }
        extra={
          <Space>
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜索指标名称 / 编码"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              allowClear
              style={{ width: 240 }}
            />
            <Button icon={<DownloadOutlined />} onClick={exportCsv}>导出 CSV</Button>
            <Button
              icon={<CloudUploadOutlined />}
              loading={importing}
              onClick={reimport}
              type="primary"
            >
              重新导入 xlsx
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                setLoading(true)
                Promise.all([
                  metricItemsApi.tree(activeCat),
                  metricItemsApi.list({ category: activeCat }),
                ]).then(([t, l]) => {
                  setTree(t.items || [])
                  setFlat(l.items || [])
                }).finally(() => setLoading(false))
              }}
            >刷新</Button>
          </Space>
        }
      >
        <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', height: 'calc(100vh - 280px)', minHeight: 480 }}>
          {/* 左侧树 */}
          <div style={{ borderRight: '1px solid #f0f0f0', overflow: 'auto', padding: 12, background: '#fafafa' }}>
            <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>
              <ApartmentOutlined style={{ marginRight: 6 }} />
              {activeCatMeta?.name || activeCat} 树形结构（共 {flat.length} 项）
            </div>
            {treeData.length ? (
              <Tree
                treeData={treeData}
                defaultExpandAll
                showLine
                blockNode
                onSelect={onSelectTree}
                selectedKeys={selectedKey ? [selectedKey] : []}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </div>

          {/* 右侧表 */}
          <div style={{ overflow: 'auto', padding: 12 }}>
            {selectedKey ? (
              <>
                <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>
                  <TableOutlined style={{ marginRight: 6 }} />
                  选中节点「{selectedKey.split('|')[1]}」的子项（{selectedChildren.length}）
                </div>
                <Table
                  rowKey="id"
                  size="small"
                  dataSource={selectedChildren}
                  columns={tableCols}
                  pagination={{ pageSize: 20, showSizeChanger: false }}
                />
              </>
            ) : (
              <>
                <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>
                  <TableOutlined style={{ marginRight: 6 }} />
                  全部指标项（{keyword ? `${filteredFlat.length} / ${flat.length}` : flat.length}）
                  {keyword && <Tag color="orange" style={{ marginLeft: 6 }}>搜索: {keyword}</Tag>}
                </div>
                <Table
                  rowKey="id"
                  size="small"
                  dataSource={filteredFlat}
                  columns={tableCols}
                  pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
                />
              </>
            )}
          </div>
        </div>
      </Card>
    </Spin>
  )
}

export default MetricItems

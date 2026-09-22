/** PRCP ESG · 情景集结果 Panel
 *
 * compact 模式：显示文件名 + 大小 + 下载按钮
 * 完整模式：显示 scenario 元数据 + 历史情景集列表
 */
import React from 'react'
import { Card, Statistic, Row, Col, Empty, Button, Descriptions } from 'antd'
import { DownloadOutlined, FileTextOutlined } from '@ant-design/icons'
import type { EsgRun } from '../../api/esg'

interface Props {
  /** run.output_json (SCENARIO_GENERATE) 或完整 run */
  run?: EsgRun
  compact?: boolean
}

const ScenarioResultPanel: React.FC<Props> = ({ run, compact = false }) => {
  if (!run) return <Empty description="暂无情景集" />

  const out = (run.output || {}) as {
    scenario_code?: string
    sc_id?: number
    file_size_bytes?: number
    paths_shape?: number[]
  }

  const handleDownload = () => {
    if (!out.scenario_code) return
    const url = `/prcp/api/esg/scenarios/${out.scenario_code}/download`
    const a = document.createElement('a')
    a.href = url; a.download = `scenario_${out.scenario_code}.npz`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
  }

  if (compact) {
    return (
      <div style={{ marginTop: 12 }}>
        <Row gutter={8}>
          <Col span={12}>
            <Statistic title="情景集" value={out.scenario_code || '-'}
              valueStyle={{ fontSize: 14, fontFamily: 'monospace' }} />
          </Col>
          <Col span={12}>
            <Statistic title="大小" value={out.file_size_bytes != null
              ? `${((out.file_size_bytes || 0) / 1024).toFixed(1)} KB` : '-'}
              valueStyle={{ fontSize: 14 }} />
          </Col>
        </Row>
        <Button size="small" type="link" icon={<DownloadOutlined />}
                onClick={handleDownload} disabled={!out.scenario_code}
                style={{ marginTop: 4, paddingLeft: 0 }}>
          下载 .npz 文件
        </Button>
      </div>
    )
  }

  return (
    <Card size="small" title={<Space><FileTextOutlined />情景集 #{run.id}</Space>}>
      <Descriptions column={2} size="small">
        <Descriptions.Item label="scenario_code">
          <code>{out.scenario_code || '-'}</code>
        </Descriptions.Item>
        <Descriptions.Item label="sc_id">{out.sc_id ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="路径形状">
          {out.paths_shape ? `[${out.paths_shape.join(' × ')}]` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="文件大小">
          {out.file_size_bytes != null ? `${((out.file_size_bytes || 0) / 1024).toFixed(1)} KB` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="run_id">{run.id}</Descriptions.Item>
        <Descriptions.Item label="耗时">{run.duration_ms ?? 0} ms</Descriptions.Item>
      </Descriptions>
      <Button type="primary" icon={<DownloadOutlined />}
              onClick={handleDownload} disabled={!out.scenario_code}
              style={{ marginTop: 8 }}>
        下载 .npz 文件
      </Button>
    </Card>
  )
}

export default ScenarioResultPanel
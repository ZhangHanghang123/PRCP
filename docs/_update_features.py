"""
同步更新 1.2 术语表 + 2.2 特性条目 + 2.1.2 系统功能分布

1. 1.2 术语表：加 3 条 ESG 术语（24~26）
2. 2.2 特性条目表：加 1 条 F08（rows=8 → 9）
3. 2.1.2 系统功能分布表：加 1 条 F08（rows=4 不变，新增行）
"""

from docx import Document
from docx.oxml.ns import qn
from copy import deepcopy
import lxml.etree as etree

doc = Document('PRCP_需求说明书_new.docx')
body = doc.element.body

NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def get_text(elem):
    return ''.join(t.text or '' for t in elem.iter(qn('w:t')))


def find_table(rows_count, must_contain):
    """查找匹配行数和内容的表"""
    for i, child in enumerate(body):
        if child.tag == qn('w:tbl'):
            rows = child.findall(qn('w:tr'))
            if rows and len(rows) == rows_count:
                first_row_text = ''
                for c in rows[0].findall(qn('w:tc'))[:3]:
                    first_row_text += '|' + ''.join(t.text or '' for t in c.iter(qn('w:t')))[:15]
                if all(k in first_row_text for k in must_contain):
                    return child
    return None


# ============================================================
# 1.2 术语表：rows=24 → 27（+3 行 ESG 术语）
# ============================================================
term_table = find_table(24, ['术语'])
if term_table is None:
    print('未找到 1.2 术语表')
else:
    print('找到 1.2 术语表')

    # 找参考行 - 用 F07 术语行 (第 23 行: '新业务模拟引擎...')
    # 复用其样式
    ref_row = None
    for r in term_table.findall(qn('w:tr')):
        cells_text = [''.join(t.text or '' for t in c.iter(qn('w:t'))) for c in r.findall(qn('w:tc'))]
        if cells_text and '新业务模拟引擎' in cells_text[1]:
            ref_row = r
            break

    if ref_row is None:
        print('未找到参考行')
    else:
        # 深拷贝参考行，修改序号 + 名称 + 定义
        for idx, (name, definition) in enumerate([
            ('Svensson 收益率曲线',
             'Svensson 6 参数（θ₀..θ₃ + λ₁ + λ₂）连续复利利率模型；'
             'PRCP ESG 工厂统一存储为百分比（不除以 100）；'
             'H(x) = (1 - e^(-x))/x 为 Humphrey 衰减函数。'),
            ('HJM 模型（Heath-Jarrow-Morton）',
             '基于远期利率曲线动态的利率路径生成模型；'
             'PRCP 用简化仿射版：dW × eigenvector × factor_std 累积生成 (n, steps, 13) 利率路径；'
             '月步长 dt=1/12，利率物理约束 max(paths, 0)。'),
            ('PCA 主成分分析（利率场景）',
             '对历史利率矩阵（N 日 × 13 期限）做去中心化 → 协方差 → 特征分解，'
             '取前 n_factors 个主成分（PC1 水平 + PC2 斜率 + PC3 曲度）；'
             'PRCP 默认 n_factors=3，PC1-3 累计方差比 > 90%。'),
        ]):
            new_row = deepcopy(ref_row)
            # 修改 3 列内容
            cells = new_row.findall(qn('w:tc'))
            if len(cells) >= 3:
                # 序号 24/25/26
                for t in cells[0].iter(qn('w:t')):
                    if t.text and t.text.strip().isdigit():
                        t.text = str(24 + idx)
                        break
                # 名称
                name_t = list(cells[1].iter(qn('w:t')))
                if name_t:
                    name_t[0].text = name
                    # 清空其他 run
                    for t in name_t[1:]:
                        t.text = ''
                # 定义
                def_t = list(cells[2].iter(qn('w:t')))
                if def_t:
                    def_t[0].text = definition
                    for t in def_t[1:]:
                        t.text = ''
            term_table.append(new_row)

        print('已添加 3 行 ESG 术语')


# ============================================================
# 2.2 特性条目表：rows=8 → 9（+1 行 F08）
# ============================================================
feature_table = find_table(8, ['特性'])
if feature_table is None:
    print('未找到 2.2 特性条目表')
else:
    print('找到 2.2 特性条目表')

    ref_row = None
    for r in feature_table.findall(qn('w:tr')):
        cells_text = [''.join(t.text or '' for t in c.iter(qn('w:t'))) for c in r.findall(qn('w:tc'))]
        if cells_text and 'F07' in cells_text[1]:
            ref_row = r
            break

    if ref_row is None:
        print('未找到参考行 F07')
    else:
        new_row = deepcopy(ref_row)
        cells = new_row.findall(qn('w:tc'))
        if len(cells) >= 6:
            # 序号 8
            for t in cells[0].iter(qn('w:t')):
                if t.text and t.text.strip().isdigit():
                    t.text = '8'
                    break
            # 名称
            name_t = list(cells[1].iter(qn('w:t')))
            if name_t:
                name_t[0].text = 'F08 ESG 场景工厂模块'
                for t in name_t[1:]:
                    t.text = ''
            # 内容描述
            desc_t = list(cells[2].iter(qn('w:t')))
            if desc_t:
                desc_t[0].text = (
                    '提供 ESG 场景工厂：Svensson 6 参数曲线还原 + PCA 拟合 + HJM 仿射生成未来利率路径，'
                    '持久化为 .npz + BLOB 双轨情景集，供组合反算与利率情景分析共享消费。'
                )
                for t in desc_t[1:]:
                    t.text = ''
            # 关联系统 (cells[3])
            sys_t = list(cells[3].iter(qn('w:t')))
            if sys_t:
                sys_t[0].text = '组合管理测算平台PRCP'
                for t in sys_t[1:]:
                    t.text = ''
            # 备注 (cells[4])
            note_t = list(cells[4].iter(qn('w:t')))
            if note_t:
                note_t[0].text = '含 3 项二级菜单（方案管理/曲线还原/结果汇总）+ 方案详情页'
                for t in note_t[1:]:
                    t.text = ''
            # 优先级 (cells[5])
            pri_t = list(cells[5].iter(qn('w:t')))
            if pri_t:
                pri_t[0].text = 'P1'
                for t in pri_t[1:]:
                    t.text = ''
        feature_table.append(new_row)
        print('已添加 1 行 F08 特性')


# ============================================================
# 2.1.2 系统功能分布表：rows=4 → 5（+1 行 F08）
# ============================================================
sys_table = find_table(4, ['系统'])
if sys_table is None:
    print('未找到 2.1.2 系统功能分布表')
else:
    print('找到 2.1.2 系统功能分布表')

    ref_row = None
    for r in sys_table.findall(qn('w:tr')):
        cells_text = [''.join(t.text or '' for t in c.iter(qn('w:t'))) for c in r.findall(qn('w:tc'))]
        if cells_text and '算法适配层' in cells_text[0] or (len(cells_text) >= 5 and '公式引擎' in ''.join(cells_text)):
            ref_row = r
            break

    if ref_row is None:
        # 退而求其次取最后一行
        ref_row = sys_table.findall(qn('w:tr'))[-1]

    new_row = deepcopy(ref_row)
    cells = new_row.findall(qn('w:tc'))
    if len(cells) >= 6:
        # 序号 4
        for t in cells[0].iter(qn('w:t')):
            if t.text and t.text.strip().isdigit():
                t.text = '4'
                break
        # 关联系统
        for t in cells[1].iter(qn('w:t')):
            if t.text:
                t.text = '组合管理测算平台PRCP'
                break
        # 系统标识
        for t in cells[2].iter(qn('w:t')):
            if t.text:
                t.text = 'PRCP'
                break
        # 系统功能条目
        for t in cells[3].iter(qn('w:t')):
            if t.text:
                t.text = 'F08 ESG 场景工厂'
                break
        # 是否改配合测试
        for t in cells[4].iter(qn('w:t')):
            if t.text:
                t.text = '否'
                break
        # 配合改造点 - 用最长 run
        longest_idx = -1
        longest_len = 0
        ct5 = list(cells[5].iter(qn('w:t')))
        for ci, t in enumerate(ct5):
            if t.text and len(t.text) > longest_len:
                longest_len = len(t.text)
                longest_idx = ci
        if longest_idx >= 0:
            ct5[longest_idx].text = (
                '新增 ESG 工厂算法包 backend/app/services/esg/（svensson / yield_curve_generator / '
                'scenario_set / validator 4 个模块）+ 后端 25 个 endpoint（routers/esg.py）'
                '含方案 CRUD + 曲线还原 + 三步执行（fit-pca / generate-hjm / generate）+ '
                '情景集查询 + 下载 + 一键案例 + 缓存诊断；'
                '新增 frontend/src/pages/Esg* 4 个页面 + 字典扩展 13 项。'
            )
            # 清空其他 run
            for ci, t in enumerate(ct5):
                if ci != longest_idx:
                    t.text = ''
    sys_table.append(new_row)
    print('已添加 1 行 F08 系统功能')


doc.save('PRCP_需求说明书_new.docx')
print('已保存')
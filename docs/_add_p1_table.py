"""
补充 3.8 产物1（最小口径表）

口径表内容（5列 x 6行）：
表头：序号 | 维度 | 本期定版 | 依据/出处 | 缺失/后续
1. 账户册状态 | ACTIVE / INACTIVE 两态；反算仅校验"启用" | 问题03原文+本期定版 | 后续扩展：完整审批流
2. 日期/月份 | 未来24月，月份1..24；data_date=基期；date_offset=1..24；offset_unit=M（月）| 问题01原文+本期定版 | 后续扩展：20年、任意期数
3. 期限结构 | 64+64 桶：orig_m1..orig_m60 + orig_y10/y15/y20/y30；rem_m1..rem_m60 + rem_y10/y15/y20/y30 | 问题02原文+本期定版 | 后续扩展：可配置分桶
4. 核心指标公式及单位 | unit 限定 % / BP / RATIO / AMOUNT；公式必须属于所属报表；指标 ACTIVE 才参与 | 问题04原文+本期定版 | 后续扩展：全部监管指标
5. 利率/计息 | weighted_rate DECIMAL(8,4) 百分比；interest_amount = avg_balance × rate × 1/12 | 问题04原文+本期定版 | 后续扩展：复杂计息规则
6. 缺失值处理 | 暂不支持的指标标"暂不支持"，不填展示数；缺关键数据时给明确提示 | 问题04原文+本期定版 | 后续扩展：智能缺失值填充
"""

from docx import Document
from docx.oxml.ns import qn
from copy import deepcopy

doc = Document('PRCP_需求说明书.docx')
body = doc.element.body

# 找到产物 1 引言段落的位置（"本期账户册状态、日期/月份..."）
# 在它后面插入新表
target_p = None
target_idx = -1
for i, child in enumerate(body):
    if child.tag == qn('w:p'):
        text = ''.join(t.text or '' for t in child.iter(qn('w:t')))
        if text.startswith('本期账户册状态、日期/月份'):
            target_p = child
            target_idx = i
            break

print(f'Found 产物1引言段 at idx {target_idx}')

# 复制一个已有的 5x5 表的样式结构作为参考 - 用 t_p2 的结构
ref_tbl = None
for c in body:
    if c.tag == qn('w:tbl'):
        rows = c.findall(qn('w:tr'))
        if rows and len(rows) == 11:
            ref_tbl = c
            break

# 直接构造一个简化的 5列表格
# 使用 lxml 直接生成 XML
import lxml.etree as etree

# 表格内容：6行 (1表头 + 5数据)
table_data = [
    ['序号', '维度', '本期定版', '依据/出处', '后续扩展'],
    [
        '1',
        '账户册状态',
        'ACTIVE / INACTIVE 两态；反算仅校验"启用"',
        '问题03：状态字段语义冲突',
        '完整审批流、多级审核、复杂生命周期',
    ],
    [
        '2',
        '日期/月份',
        '未来 24 月；data_date=基期日；date_offset=1..24；offset_unit=M（月）',
        '问题01：周期/月份/数据日期含义不统一',
        '20 年预测、任意期数、D/W/Y 多种频率',
    ],
    [
        '3',
        '期限结构',
        '64+64 桶：orig_m1..orig_m60 + orig_y10/y15/y20/y30；rem_m1..rem_m60 + rem_y10/y15/y20/y30',
        '问题02：基础数据/反算结果期限桶不同步',
        '可自由配置的期限分桶引擎',
    ],
    [
        '4',
        '核心指标公式及单位',
        'unit 限定 % / BP / RATIO / AMOUNT 四选一；公式必须属于所属报表；指标 ACTIVE 才参与',
        '问题04：取数映射/利率单位/计息口径',
        '全部监管指标、复杂公式引擎',
    ],
    [
        '5',
        '利率/计息与缺失值',
        'weighted_rate DECIMAL(8,4) 百分比存储；interest_amount = avg_balance × rate × 1/12；缺关键数据给明确提示',
        '问题04：计息期间与百分比换算未统一',
        '复杂计息规则、智能缺失值填充',
    ],
]

# 构造表格 XML
ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

# 表格属性（参考 docx 默认表样式）
tbl_xml_parts = ['<w:tbl xmlns:w="{ns}">'.format(ns=ns)]
tbl_xml_parts.append('''<w:tblPr>
<w:tblStyle w:val="10"/>
<w:tblW w:w="5000" w:type="pct"/>
<w:tblInd w:w="-24" w:type="dxa"/>
<w:tblBorders>
<w:top w:val="none" w:color="auto" w:sz="0" w:space="0"/>
<w:left w:val="none" w:color="auto" w:sz="0" w:space="0"/>
<w:bottom w:val="none" w:color="auto" w:sz="0" w:space="0"/>
<w:right w:val="none" w:color="auto" w:sz="0" w:space="0"/>
<w:insideH w:val="none" w:color="auto" w:sz="0" w:space="0"/>
<w:insideV w:val="none" w:color="auto" w:sz="0" w:space="0"/>
</w:tblBorders>
<w:tblLayout w:type="autofit"/>
<w:tblCellMar>
<w:top w:w="15" w:type="dxa"/>
<w:left w:w="15" w:type="dxa"/>
<w:bottom w:w="15" w:type="dxa"/>
<w:right w:w="15" w:type="dxa"/>
</w:tblCellMar>
</w:tblPr>''')
tbl_xml_parts.append('''<w:tblGrid>
<w:gridCol w:w="500"/>
<w:gridCol w:w="1500"/>
<w:gridCol w:w="3500"/>
<w:gridCol w:w="2500"/>
<w:gridCol w:w="2000"/>
</w:tblGrid>''')

# 表头行
def make_cell(text, width, bold=False, shd=None):
    rpr = ''
    if bold:
        rpr = '<w:rPr><w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/><w:b/><w:bCs/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>'
    else:
        rpr = '<w:rPr><w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>'
    shd_xml = '<w:shd w:val="clear" w:color="auto" w:fill="{}"/>'.format(shd) if shd else ''
    return f'''<w:tc>
<w:tcPr>
<w:tcW w:w="{width}" w:type="dxa"/>
{shd_xml}
<vAlign w:val="center"/>
</w:tcPr>
<w:p>
<w:pPr>
<w:pStyle w:val="a"/>
<w:jc w:val="left"/>
</w:pPr>
<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r>
</w:p>
</w:tc>'''

# 表格行
widths_list = [500, 1500, 3500, 2500, 2000]
for i, row in enumerate(table_data):
    tbl_xml_parts.append('<w:tr>')
    for j, cell in enumerate(row):
        if i == 0:
            tbl_xml_parts.append(make_cell(cell, widths_list[j], bold=True, shd='D9D9D9'))
        else:
            tbl_xml_parts.append(make_cell(cell, widths_list[j], bold=False))
    tbl_xml_parts.append('</w:tr>')

tbl_xml_parts.append('</w:tbl>')

tbl_xml = ''.join(tbl_xml_parts)
tbl_elem = etree.fromstring(tbl_xml)

# 插入到 产物1引言段 之后
target_p.addnext(tbl_elem)

# 保存
doc.save('PRCP_需求说明书.docx')
print('Saved 产物1 table inserted.')
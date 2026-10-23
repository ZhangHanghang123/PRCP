"""
3.7 / 3.8 / 4 章节最终重排脚本
- 从 partial.docx 状态恢复（已 cp 覆盖 PRCP_需求说明书.docx）
- 按"内容 + prev_text"双重识别每个元素
- 丢弃重复 / 误放元素
- 按正确的 target_order 重组

每个元素分配一个唯一 label：
  - 段落：以段落内容关键字为 key
  - 表格：以"prev 段落关键字 + 行数" 为 key
- target_order 是有序的 label 列表
"""

from docx import Document
from docx.oxml.ns import qn
from collections import Counter
import lxml.etree as etree

doc = Document('PRCP_需求说明书.docx')
body = doc.element.body

def get_text(elem):
    if elem.tag == qn('w:p'):
        return ''.join(t.text or '' for t in elem.iter(qn('w:t')))
    elif elem.tag == qn('w:tbl'):
        prev = elem.getprevious()
        if prev is not None and prev.tag == qn('w:p'):
            return '[TBL] ' + ''.join(t.text or '' for t in prev.iter(qn('w:t')))
    return ''

def get_prev_text(elem):
    prev = elem.getprevious()
    if prev is not None and prev.tag == qn('w:p'):
        return ''.join(t.text or '' for t in prev.iter(qn('w:t')))
    return ''

# 收集所有从 3.6.7 之后到文档末尾的元素
start_idx = None
for i, child in enumerate(body):
    if child.tag == qn('w:p'):
        text = ''.join(t.text or '' for t in child.iter(qn('w:t')))
        if text.startswith('3.6.7.'):
            start_idx = i + 1
            break

print(f'start_idx = {start_idx}, total = {len(body)}')

# 收集并缓存 prev_text（在原文档中的位置关系）
collected = []
prev_text_cache = []
for i in range(start_idx, len(body)):
    child = body[i]
    prev_text = get_prev_text(child)
    prev_text_cache.append(prev_text)
    collected.append(child)

print(f'Collected {len(collected)} elements')

# 显示所有元素，给每个元素分配一个 label
def assign_label(elem, prev_text, idx):
    text = get_text(elem)
    is_tbl = elem.tag == qn('w:tbl')

    # === 段落分类 ===
    if text.startswith('3.7. 【F07】'):
        return 'f07_title'
    if text.startswith('3.7.1.'):
        return 'p_371_title'
    if text.startswith('3.7.2.'):
        return 'p_372_title'
    if text.startswith('3.7.3.1.'):
        return 'p_373_1_title'
    if text.startswith('3.7.3.2.'):
        return 'p_373_2_title'
    if text.startswith('3.7.3.3.'):
        return 'p_373_3_title'
    if text.startswith('3.7.3.4.'):
        return 'p_373_4_title'
    if text.startswith('3.7.3.5.'):
        return 'p_373_5_title'
    if text.startswith('3.7.3.6.'):
        return 'p_373_6_title'
    if text.startswith('3.7.3.7.'):
        return 'p_373_7_title'
    if text.startswith('3.7.3.8.'):
        return 'p_373_8_title'
    if text.startswith('3.7.3. '):
        return 'p_373_title'
    if text.startswith('3.7.4.'):
        return 'p_374_title'
    if text.startswith('3.7.5.'):
        return 'p_375_title'
    if text.startswith('3.7.6.'):
        return 'p_376_title'
    if text.startswith('3.7.7.'):
        return 'p_377_title'
    if text.startswith('3.7.8.'):
        return 'p_378_title'
    if text.startswith('3.7.9.'):
        return 'p_379_title'
    if text.startswith('3.8.'):
        return 'p_38_title'
    if text.startswith('4. 本期上线'):
        return 'p_4_title'

    # 内容段落 - 3.7.1
    if text.startswith('本特性条目对应一级菜单'):
        return 'f07_intro_371'

    # 3.7.2
    if text.startswith('业务流程分为五个阶段'):
        return 'f07_business_372'
    if text.startswith('┌─'):
        return 'f07_diagram_372'
    if text.startswith('图 3.7-A'):
        return 'f07_diagram_caption_372'

    # 3.7.3.1
    if text.startswith('引擎核心目标'):
        return 'f07_overview_3731'

    # 3.7.3.2
    if text.startswith('功能：从 prcp_data_basic'):
        return 'f07_step1_3732'

    # 3.7.3.3
    if text.startswith('公式：') and 'net_new' in text:
        return 'f07_step2_3733'

    # 3.7.3.4
    if text.startswith('公式：') and 'term_ratio' in text:
        return 'f07_step3_3734'

    # 3.7.3.5
    if text.startswith('短端桶'):
        return 'f07_step4_3735'

    # 3.7.3.6
    if text.startswith('指标 1：当前余额'):
        return 'f07_step5_3736'

    # 3.7.3.7
    if text.startswith('def run_sim_engine'):
        return 'f07_pseudo1_3737'
    if text.startswith('主循环结构'):
        return 'f07_pseudo2_3737'

    # 3.7.3.8
    if text.startswith('边界与异常处理：') and ('节点无 prcp_data_basic' in text or '跳过该节点' in text):
        return 'f07_boundary_3738'

    # 3.7.4 异常处理段（位于 3.7.4 标题之下）
    if text.startswith('异常处理：') and '单一功能异常' in text:
        return 'f07_exception_374'

    # 3.7.5
    if text.startswith('【F07-P01】'):
        return 'f07_p01_375'
    if text.startswith('【F07-P02】'):
        return 'f07_p02_375'
    if text.startswith('【F07-P03】'):
        return 'f07_p03_375'
    if text.startswith('输入要素：'):
        return 'f07_input_375'
    if text.startswith('输出要素：'):
        return 'f07_output_375'

    # 3.7.6
    if text.startswith('F07 新业务模拟方案涉及 5 张表'):
        return 'f07_db_intro_376'
    if text.startswith('表 1：prcp_sim_scheme'):
        return 't1_sim_scheme_title'
    if text.startswith('表 2：prcp_sim_node_config'):
        return 't2_sim_node_config_title'
    if text.startswith('表 3：prcp_sim_term_ratio'):
        return 't3_sim_term_ratio_title'
    if text.startswith('表 4：prcp_sim_run'):
        return 't4_sim_run_title'
    if text.startswith('表 5：prcp_sim_result'):
        return 't5_sim_result_title'
    if text.startswith('表 6：F07 引擎读写表汇总'):
        return 't6_sim_rw_title'

    # 3.7.9
    if text.startswith('【执行状态机】'):
        return 'f07_state_machine_379'
    if text.startswith('【并发控制】'):
        return 'f07_concurrency_379'

    # 3.6.7 异常处理段
    if text.startswith('异常处理：') and '单一图表加载异常' in text:
        return 'f06_exception_text'

    # 3.8 内容
    if text.startswith('根据《PRCP_需求问题清单'):
        return 'p_38_intro'
    if text.startswith('本期账户册状态、日期/月份'):
        return 'p_38_p1_intro'
    if text.startswith('产物 1：最小口径表'):
        return 'p_38_p1_title'
    if text.startswith('一种反算方式'):
        return 'p_38_p2_intro'
    if text.startswith('产物 2：最小计算与接口说明'):
        return 'p_38_p2_title'
    if text.startswith('明确本期启用/暂缓范围'):
        return 'p_38_p3_intro'
    if text.startswith('产物 3：范围确认与验收记录'):
        return 'p_38_p3_title'

    # 4 内容
    if text.startswith('本期上线最小验收用例基于'):
        return 'p_4_intro'

    # === 表分类（基于 prev 段落内容）===
    if is_tbl:
        # F06 异常处理表
        if '单一图表加载异常' in prev_text:
            return 't_f06_exception'
        # 产物 3 表
        if '产物 3：范围确认与验收记录' in prev_text:
            return 't_p3'
        # 产物 2 表
        if '产物 2：最小计算与接口说明' in prev_text:
            return 't_p2'
        # 3.7.4 业务规则表（prev="3.7.4. 业务规则"）
        if prev_text.startswith('3.7.4.'):
            return 't_f07_business_rule_374'
        # 3.7.5 输入要素表
        if '输入要素：' in prev_text:
            return 't_f07_input_375'
        # 3.7.5 输出要素表
        if '输出要素：' in prev_text:
            return 't_f07_output_375'
        # 3.7.6 表 1：prcp_sim_scheme
        if '表 1：prcp_sim_scheme' in prev_text:
            return 't_sim_scheme'
        if '表 2：prcp_sim_node_config' in prev_text:
            return 't_sim_node_config'
        if '表 3：prcp_sim_term_ratio' in prev_text:
            return 't_sim_term_ratio'
        if '表 4：prcp_sim_run' in prev_text:
            return 't_sim_run'
        if '表 5：prcp_sim_result' in prev_text:
            return 't_sim_result'
        if '表 6：F07 引擎读写表汇总' in prev_text:
            return 't_sim_rw'
        # 3.7.7 角色表
        if prev_text.startswith('3.7.7.'):
            return 't_f07_role_377'
        # 3.7.8 关联系统表
        if prev_text.startswith('3.7.8.'):
            return 't_f07_assoc_378'
        # 4 验收用例表
        if '本期上线最小验收用例基于' in prev_text:
            return 't_acceptance_4'
        # 异常处理段（F07 异常处理）- 仅作 t_f07_exception_drop
        # 3.7.3 输入要素表（误放，prev="3.7.3. 引擎计量核心算法"）
        if prev_text.startswith('3.7.3.'):
            return '__DROP__'  # 误放，丢弃
        # 没有 prev_text 的表（来自原 partial 中的游离表）全部丢弃
        if not prev_text.strip():
            return '__DROP__'
        # 默认丢弃
        return '__DROP__'

    # 默认丢弃
    return '__DROP__'

# 给每个元素打标签
labels = []
for i, elem in enumerate(collected):
    label = assign_label(elem, prev_text_cache[i], i)
    labels.append(label)

# 统计
label_counter = Counter(labels)
print()
print('Label distribution:')
for k, v in sorted(label_counter.items(), key=lambda x: (x[0].startswith('__'), x[0])):
    print(f'  {k}: {v}')

# 把所有元素从 body 移除
for elem in collected:
    parent = elem.getparent()
    parent.remove(elem)

# 找锚点（3.6.7 段落）
anchor = None
for child in body:
    if child.tag == qn('w:p'):
        text = ''.join(t.text or '' for t in child.iter(qn('w:t')))
        if text.startswith('3.6.7.'):
            anchor = child
            break

# 找到的每个 label 的元素（保留最先匹配的）
label_to_elem = {}
for i, (elem, label) in enumerate(zip(collected, labels)):
    if label == '__DROP__':
        continue
    if label not in label_to_elem:
        label_to_elem[label] = elem
    # else: 重复 label，丢弃（保留先遇到的）

print()
print(f'Unique labels collected: {len(label_to_elem)}')

# 手动创建缺失的 3.7.2 标题（partial 中此标题缺失，需手工补）
# style 4 = heading 3（参照 3.7.1 / 3.7.3 等 sibling）
h372_xml = '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:pPr><w:pStyle w:val="4"/><w:keepNext w:val="0"/><w:keepLines w:val="0"/><w:widowControl/><w:suppressLineNumbers w:val="0"/><w:spacing w:line="240" w:lineRule="atLeast"/><w:outlineLvl w:val="2"/><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/><w:b/><w:bCs/><w:kern w:val="0"/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/><w:b/><w:bCs/><w:kern w:val="0"/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr><w:t>3.7.2. 业务流程（含数据流转）</w:t></w:r></w:p>'
h372_elem = etree.fromstring(h372_xml)
label_to_elem['p_372_title'] = h372_elem

# 目标顺序
target_order = [
    # 3.7 父标题
    'f07_title',
    # 3.7.1
    'p_371_title',
    'f07_intro_371',
    # 3.7.2
    'p_372_title',
    'f07_business_372',
    'f07_diagram_372',
    'f07_diagram_caption_372',
    # 3.7.3
    'p_373_title',
    'p_373_1_title', 'f07_overview_3731',
    'p_373_2_title', 'f07_step1_3732',
    'p_373_3_title', 'f07_step2_3733',
    'p_373_4_title', 'f07_step3_3734',
    'p_373_5_title', 'f07_step4_3735',
    'p_373_6_title', 'f07_step5_3736',
    'p_373_7_title', 'f07_pseudo1_3737', 'f07_pseudo2_3737',
    'p_373_8_title', 'f07_boundary_3738',
    # 3.7.4
    'p_374_title',
    't_f07_business_rule_374',
    'f07_exception_374',
    # 3.7.5
    'p_375_title',
    'f07_p01_375', 'f07_p02_375', 'f07_p03_375',
    'f07_input_375', 't_f07_input_375',
    'f07_output_375', 't_f07_output_375',
    # 3.7.6
    'p_376_title',
    'f07_db_intro_376',
    't1_sim_scheme_title', 't_sim_scheme',
    't2_sim_node_config_title', 't_sim_node_config',
    't3_sim_term_ratio_title', 't_sim_term_ratio',
    't4_sim_run_title', 't_sim_run',
    't5_sim_result_title', 't_sim_result',
    't6_sim_rw_title', 't_sim_rw',
    # 3.7.7
    'p_377_title',
    't_f07_role_377',
    # 3.7.8
    'p_378_title',
    't_f07_assoc_378',
    # 3.7.9
    'p_379_title',
    'f07_state_machine_379',
    'f07_concurrency_379',
    # 3.8
    'p_38_title',
    'p_38_intro',
    'p_38_p1_title', 'p_38_p1_intro',
    'p_38_p2_title', 'p_38_p2_intro', 't_p2',
    'p_38_p3_title', 'p_38_p3_intro', 't_p3',
    # 4
    'p_4_title',
    'p_4_intro',
    't_acceptance_4',
]

# 检查缺失
missing = [l for l in target_order if l not in label_to_elem]
print()
print(f'MISSING labels: {missing}')

# 按目标顺序重组
new_order = []
for label in target_order:
    if label in label_to_elem:
        new_order.append(label_to_elem[label])
    else:
        print(f'  SKIPPED (missing): {label}')

print(f'New order has {len(new_order)} elements')

# 插入到锚点（3.6.7）之后
# addnext 多次：每次插入到调用元素紧邻后一个位置，最新插入的最靠前
# 所以遍历顺序：先插最后一个，最后插第一个
for elem in reversed(new_order):
    anchor.addnext(elem)

# 验证
print()
print('=== After reorder (3.7 / 3.8 / 4 章节标题) ===')
for i, child in enumerate(body):
    if child.tag == qn('w:p'):
        text = ''.join(t.text or '' for t in child.iter(qn('w:t')))
        if (text.startswith('3.7.') or text.startswith('3.8.') or text.startswith('4.')) and len(text) < 80:
            print(f'  [{i}] {text[:80]}')

doc.save('PRCP_需求说明书.docx')
print()
print('Saved.')
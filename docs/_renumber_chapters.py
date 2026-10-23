"""
PRCP_需求说明书.docx - 章节编号顺延

把原 3.8（实施建议）改为 3.9，原 4（验收用例）改为 5
（原 3.7 实施建议章节现位于 3.9，本期上线最小验收用例位于 5）

操作：
- '3.8. 本期上线实施建议（三项定版产物）' → '3.9. 本期上线实施建议（三项定版产物）'
- '4. 本期上线最小验收用例（端到端）' → '5. 本期上线最小验收用例（端到端）'
"""

from docx import Document
from docx.oxml.ns import qn

doc = Document('PRCP_需求说明书_new.docx')
body = doc.element.body

replacements = {
    '3.8. 本期上线实施建议': '3.9. 本期上线实施建议',
    '4. 本期上线最小验收用例': '5. 本期上线最小验收用例',
}

count = 0
for child in body:
    if child.tag == qn('w:p'):
        for t in child.iter(qn('w:t')):
            if t.text:
                for old, new in replacements.items():
                    if old in t.text:
                        t.text = t.text.replace(old, new)
                        count += 1
                        print(f'  替换: {t.text[:80]}')

# 修复 4. 简介段开头（如果被替换了）
# 找出 "本期上线最小验收用例基于..." 在新 doc 中已经不变（因为它的开头是中文，不是数字开头）
# 注意原 4. 章节段落首段是 "本期上线最小验收用例基于..."，不含 "4." 所以无需修改

doc.save('PRCP_需求说明书_new.docx')
print(f'\n共替换 {count} 处')
print('已保存')
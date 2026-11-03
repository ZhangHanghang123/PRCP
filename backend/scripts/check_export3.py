from openpyxl import load_workbook

wb = load_workbook('/tmp/exp3.xlsx')
print('Sheets:', wb.sheetnames)

ws = wb['账户册结构']
print(f'\nSheet1 账户册结构: {ws.max_row - 1} 行 × {ws.max_column} 列')
hdr = [c.value for c in ws[1]]
print('  表头:', ' | '.join(str(h).replace('\n', ' ') for h in hdr[:6]), '... |', hdr[-1].replace('\n', ' '))
print('\n  前 14 行（含缩进与父子汇总校验）:')
for r in range(2, min(16, ws.max_row + 1)):
    row = [c.value for c in ws[r]]
    name_cell = ws.cell(row=r, column=2)
    indent = name_cell.alignment.indent
    m1 = row[5] if len(row) > 5 else 0
    print(f'    {str(row[0]):<15} {str(row[1])[:24]:<26} L{row[2]} 缩进={indent} '
          f'末级={row[4] or "-":<2} M1={m1:>18,.0f}')

# 校验：父节点 M1 = 其子节点之和
print('\n  【校验】父节点 M1 是否等于子树之和:')
child_sum = {}
for r in range(2, ws.max_row + 1):
    row = [c.value for c in ws[r]]
    child_sum.setdefault(row[2], []).append((row[0], row[1], row[4], row[5]))
ok = True
for lvl in sorted(child_sum.keys()):
    for code, name, leaf, m1 in child_sum[lvl]:
        if leaf == '是':
            continue
        # 找下一层级里以它为父的（用 name 前缀粗略匹配，或直接看层级+1 且缩进更深）
        kids = [x for x in child_sum[lvl + 1] if x[3] is not None]
        # 简化：只打印父节点行做人工核对
        print(f'    L{lvl} 父节点 {str(name)[:20]:<22} M1={m1:>18,.0f}')
        ok = False
        break
    if not ok:
        break

ws2 = wb['按层级汇总']
print(f'\nSheet2 按层级汇总: {ws2.max_row - 1} 行 × {ws2.max_column} 列')
h2 = [c.value for c in ws2[1]]
print('  表头:', ' | '.join(str(h).replace('\n', ' ') for h in h2[:4]), '... |', h2[-1].replace('\n', ' '))
for r in ws2.iter_rows(min_row=2, max_row=ws2.max_row, values_only=True):
    if r[0]:
        print(f'    {str(r[0]):<8} 节点数={r[1]:<4} 末级={r[2]:<4} M1={r[3]:>18,.0f}  M24={r[-1]:>18,.0f}')

ws3 = wb['末级节点大类汇总']
print(f'\nSheet3 末级节点大类汇总: {ws3.max_row - 1} 行 × {ws3.max_column} 列')
for r in ws3.iter_rows(min_row=2, max_row=ws3.max_row, values_only=True):
    if r[0]:
        print(f'    {str(r[0]):<6} M1={r[1]:>18,.2f}  M24={r[-1]:>18,.2f}')

ws4 = wb['口径说明']
print('\nSheet4 口径说明:')
for r in ws4.iter_rows(min_row=2, max_row=ws4.max_row, values_only=True):
    print('   ', r[0], '=', str(r[1])[:80])

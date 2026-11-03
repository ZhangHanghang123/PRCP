from openpyxl import load_workbook

for f in ['/tmp/exp_2026.xlsx', '/tmp/exp_REV_ANT_REG.xlsx']:
    wb = load_workbook(f)
    print('=' * 70)
    print(f.split('/')[-1], '| Sheets:', wb.sheetnames)

    ws = wb['结构预测余额']
    print(f'  结构预测余额: {ws.max_row - 1} 行 × {ws.max_column} 列')
    hdr = [c.value for c in ws[1]]
    head = ' / '.join(str(h).replace('\n', ' ') for h in hdr[:6])
    print('  表头:', head, '... /', hdr[-1])
    for r in [2, 3, 4, 5]:
        row = [c.value for c in ws[r]]
        leaf = row[4] if row[4] else '-'
        print(f'    {row[0]} | {str(row[1])[:22]:<24} L{row[2]} | {row[3]:<4} | 末级={leaf:<2} '
              f'| M1={row[5]:>18,.0f} | 期末={row[-1]:>18,.0f}')

    ws2 = wb['末级节点大类汇总']
    print('  大类汇总:')
    for r in ws2.iter_rows(min_row=2, max_row=7, values_only=True):
        if r[0]:
            print(f'    {str(r[0]):<6} M1={r[1]:>18,.2f}  M24={r[-2]:>18,.2f}')

    ws3 = wb['口径说明']
    print('  口径说明:')
    for r in ws3.iter_rows(min_row=2, max_row=10, values_only=True):
        print('    ', r[0], '=', str(r[1])[:78])

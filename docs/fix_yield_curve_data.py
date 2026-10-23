"""
修复 prcp_basic_20251231_v4.xlsx 中账户现金流分布:
- 资产端 (R4-R27): CF 累计 = 余额 × 100% (按比例缩放)
- 负债端 (R28-R42): 已经是 100% 覆盖, 保持
- 所有者权益 (R43): CF = 0 (无现金流)

输出: docs/v2/prcp_basic_20251231_v5.xlsx
"""
from openpyxl import load_workbook
import sys

SRC = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231_v4.xlsx"
DST = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231_v5.xlsx"

# 64 个期限列: 剩余·1M-60M (60) + 剩余·10Y/15Y/20Y/30Y (4)
CF_COL_START = 76   # C76 = 剩余·1M
CF_COL_END = 140    # 139 是最后一列 (剩余·30Y), range 不含 140

# 64 段位利率 (来自 R48-R111, 已在基础数据 sheet 中)
# 用于重新计算 K 列 (现值)
def get_64_rates(ws):
    rates = []
    for r in range(48, 112):
        v = ws.cell(r, 2).value
        if v is not None:
            rates.append(v / 100)  # 转为小数
    return rates

def calc_pv(cf, rates):
    """计算 PV: cf[0..59] = 1M-60M, cf[60..63] = 10Y/15Y/20Y/30Y"""
    pv = 0
    for m in range(1, 61):
        rate = rates[m-1]
        df = 1 / (1 + rate) ** (m/12)
        pv += cf[m-1] * df
    for i, t in enumerate([10, 15, 20, 30]):
        rate = rates[60 + i]
        df = 1 / (1 + rate) ** t
        pv += cf[60 + i] * df
    return pv


print(f"读取: {SRC}")
wb = load_workbook(SRC)
ws = wb['基础数据']
rates = get_64_rates(ws)
print(f"64 段位利率: {len(rates)} 段")

# 缩放每个账户的现金流, 让 CF 累计 = 余额 × 100%
print()
print("账户现金流缩放 (按余额 100% 覆盖):")
print(f"{'R':<3} {'name':<22} {'原CF(亿)':<12} {'余额(亿)':<12} {'缩放':<8} {'新CF(亿)':<12} {'新PV(亿)':<12}")
print("-" * 95)

for r in range(4, 44):
    sid = ws.cell(r, 3).value
    name = (ws.cell(r, 4).value or '').strip()[:20]
    is_leaf = ws.cell(r, 7).value
    # 注意: C140 实际值是 真实余额 × 10, 需除以 10
    # (C140 实际值 108,000,000,000,000 = 108 万亿 = 10.8 万亿 × 10)
    balance = ws.cell(r, 140).value or 0
    if not isinstance(balance, (int, float)):
        balance = 0
    balance = balance / 10  # 修正 10 倍误差

    # 读取原 cf
    cf = [ws.cell(r, c).value or 0 for c in range(CF_COL_START, CF_COL_END)]
    cf_total = sum(cf)

    if cf_total > 0 and balance > 0:
        # 缩放因子: 余额 / CF累计, 让 CF 累计 = 余额
        scale = balance / cf_total

        # 缩放每个期限的 cf
        for c_idx, val in enumerate(cf):
            if val != 0:
                col = CF_COL_START + c_idx
                ws.cell(r, col).value = val * scale

        # 重算 K 列 PV
        new_cf = [ws.cell(r, c).value or 0 for c in range(CF_COL_START, CF_COL_END)]
        new_pv = calc_pv(new_cf, rates)
        ws.cell(r, 11).value = new_pv  # K 列

        # 跳过 L 列 (C12), 之前是 PV 公式 (长度 1438 字符, 限制)
        # 这里 L 列是 v3 写的公式, 我们重置为空
        ws.cell(r, 12).value = None

        print(f"{r:<3} {name:<22} {cf_total/1e8:<12.0f} {balance/1e8:<12.0f} {scale:<8.3f} {sum(new_cf)/1e8:<12.0f} {new_pv/1e8:<12.0f}")
    elif balance > 0 and cf_total == 0 and r != 43:  # 所有者权益 (R43) 跳过
        # 现金流全 0, 跳过 (汇总行 R4 R5 R6 等)
        pass

# 保存
wb.save(DST)
print()
print(f"已保存: {DST}")

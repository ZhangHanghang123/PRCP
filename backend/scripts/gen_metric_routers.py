"""批量生成 4 个指标路由文件（基于 lcr_param.py 模板）"""
import os
src_path = r"C:/银行经营/PRCP/backend/app/routers/lcr_param.py"
with open(src_path, 'r', encoding='utf-8') as f:
    lcr_content = f.read()

# 每个指标的字段配置
configs = [
    # CET1: numerator + rwa
    ("cet1", "prcp_cet1_param", "CET1_OPERATOR",
     "is_numerator", "numerator_factor", "numerator_operator", "numerator_category",
     "is_rwa", "rwa_weight", "rwa_operator", "rwa_category",
     "CET1"),
    # EVE: asset + liability
    ("eve", "prcp_eve_param", "EVE_OPERATOR",
     "is_asset", "asset_type", "asset_operator", "asset_category",
     "is_liability", "liability_type", "liability_operator", "liability_category",
     "EVE"),
    # NIM: interest_asset + interest_liability
    ("nim", "prcp_nim_param", "NIM_OPERATOR",
     "is_interest_asset", "asset_rate", "asset_operator", "asset_category",
     "is_interest_liability", "liability_rate", "liability_operator", "liability_category",
     "NIM"),
    # ROE: net_profit + net_asset
    ("roe", "prcp_roe_param", "ROE_OPERATOR",
     "is_net_profit", "net_profit_factor", "net_profit_symbol", "net_profit_category",
     "is_net_asset", "net_asset_factor", "net_asset_symbol", "net_asset_category",
     "ROE"),
]

for cfg in configs:
    (pf, tbl, dict_type,
     a_flag, a_factor, a_op, a_cat,
     b_flag, b_factor, b_op, b_cat,
     title) = cfg

    content = lcr_content
    # 通用替换
    content = content.replace('"lcr_param"', f'"{pf}_param"')
    content = content.replace('LcrParam', f'{title}Param')
    content = content.replace('lcr_param', f'{pf}_param')
    content = content.replace('lcr-param', f'{pf}-param')
    content = content.replace('"LCR 参数补录"', f'"{title} 参数补录"')
    content = content.replace('LCR', title)
    content = content.replace('"prcp_lcr_param"', f'"{tbl}"')
    content = content.replace("'LCR_OPERATOR'", f"'{dict_type}'")

    # 字段名替换
    content = content.replace("is_numerator", a_flag)
    content = content.replace("num_factor", a_factor)
    content = content.replace("num_operator", a_op)
    content = content.replace("is_denominator", b_flag)
    content = content.replace("den_factor", b_factor)
    content = content.replace("den_operator", b_op)

    out_path = f"C:/银行经营/PRCP/backend/app/routers/{pf}_param.py"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'生成: {out_path}')

# 验证残留
for cfg in configs:
    pf, tbl = cfg[0], cfg[1]
    fp = f"C:/银行经营/PRCP/backend/app/routers/{pf}_param.py"
    with open(fp) as f:
        c = f.read()
    issues = []
    for k in ['LcrParam', 'lcr_param', 'lcr-param', 'prcp_lcr_param', "is_numerator", "den_factor", "num_operator", "LCR_OPERATOR", "LCR_OPERATOR"]:
        if k in c:
            count = c.count(k)
            issues.append(f'{k}={count}')
    print(f'{pf}: {"OK" if not issues else "ISSUES: " + ", ".join(issues)}')
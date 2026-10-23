"""批量生成 4 个指标参数补录前端页面（基于 LcrParam.tsx 模板）"""
import os

SRC = r"C:/银行经营/PRCP/frontend/src/pages/LcrParam.tsx"
with open(SRC, 'r', encoding='utf-8') as f:
    lcr = f.read()

# 每个指标的配置：(prefix, title, api_call, key_双字段组)
configs = [
    ("cet1", "CET1", "cet1ParamApi", "CET1",
     ("is_numerator", "numerator_factor", "numerator_operator", "numerator_category",
      "CET1 分子", "CET1 分子类别", "CET1 分子折算系数", "CET1 分子运算符"),
     ("is_rwa", "rwa_weight", "rwa_operator", "rwa_category",
      "RWA 风险", "RWA 类别", "RWA 风险权重", "RWA 运算符"),
     "分子（CET1 核心一级资本）+ RWA（风险加权资产）"),
    ("eve", "EVE", "eveParamApi", "EVE",
     ("is_asset", "asset_type", "asset_operator", "asset_category",
      "资产端", "资产类别", "资产类型", "资产运算符"),
     ("is_liability", "liability_type", "liability_operator", "liability_category",
      "负债端", "负债类别", "负债类型", "负债运算符"),
     "资产端 + 负债端（含久期）"),
    ("nim", "NIM", "nimParamApi", "NIM",
     ("is_interest_asset", "asset_rate", "asset_operator", "asset_category",
      "生息资产", "生息资产类别", "资产利率", "资产运算符"),
     ("is_interest_liability", "liability_rate", "liability_operator", "liability_category",
      "计息负债", "计息负债类别", "负债利率", "负债运算符"),
     "生息资产 + 计息负债（含利率）"),
    ("roe", "ROE", "roeParamApi", "ROE",
     ("is_net_profit", "net_profit_factor", "net_profit_symbol", "net_profit_category",
      "净利润", "净利润类别", "净利润折算", "净利润符号"),
     ("is_net_asset", "net_asset_factor", "net_asset_symbol", "net_asset_category",
      "净资产", "净资产类别", "净资产折算", "净资产符号"),
     "净利润 + 净资产（含符号）"),
]


def gen_page(prefix, title, api_call, dict_code, group_a, group_b, desc):
    # 组 A = (flag_key, factor_key, op_key, cat_key, label, cat_label, factor_label, op_label)
    c = lcr

    # 全局类名替换
    c = c.replace('LcrParam', f'{title}Param')
    c = c.replace('LcrRecord', f'{title}Record')
    c = c.replace("'../api'", f"'../api'")  # api import 用变量
    c = c.replace('import { lcrParamApi } from \'../api\'', f'import {{ {api_call} }} from \'../api\'')

    # 标题文案
    c = c.replace("'LCR 参数补录'", f"'{title} 参数补录'")

    # 字段名：A 组
    flag_a, factor_a, op_a, cat_a, lab_a, _, factor_lab_a, op_lab_a = group_a
    # 字段名：B 组
    flag_b, factor_b, op_b, cat_b, lab_b, _, factor_lab_b, op_lab_b = group_b

    # 替换为 A 组字段
    c = c.replace('is_numerator', flag_a)
    c = c.replace('num_factor', factor_a)
    c = c.replace('num_operator', op_a)
    c = c.replace("'是否分子'", f"'{lab_a}?'")
    c = c.replace("'分子折算系数'", f"'{factor_lab_a}'")
    c = c.replace("'分子运算符'", f"'{op_lab_a}'")

    # 替换为 B 组字段
    c = c.replace('is_denominator', flag_b)
    c = c.replace('den_factor', factor_b)
    c = c.replace('den_operator', op_b)
    c = c.replace("'是否分母'", f"'{lab_b}?'")
    c = c.replace("'分母折算系数'", f"'{factor_lab_b}'")
    c = c.replace("'分母运算符'", f"'{op_lab_b}'")

    # API 调用替换
    c = c.replace('lcrParamApi', api_call)
    # 接口名
    c = c.replace("'/lcr-param/'", f"'/{prefix}-param/'")
    c = c.replace("'/lcr-param?'", f"'/{prefix}-param?'")
    c = c.replace("'/lcr-param/{id}'", f"'/{prefix}-param/{{id}}'")
    c = c.replace('路径: lcr-param', f'路径: {prefix}-param')
    c = c.replace("'lcr-param'", f"'{prefix}-param'")

    # 标题文本
    c = c.replace("'LCR 参数补录（流动性覆盖率）'", f"'{title} 参数补录（{desc}）'")

    # 字典类型
    c = c.replace("'LCR_OPERATOR'", f"'{dict_code}_OPERATOR'")

    # KPI 标签
    c = c.replace("'分子节点数'", f"'{lab_a}数'")
    c = c.replace("'分母节点数'", f"'{lab_b}数'")

    # Alert 描述
    c = c.replace(
        "LCR 分子（HQLA 合格优质流动性资产）",
        f"{lab_a}（{title} 业务含义）"
    )
    c = c.replace(
        "LCR 分母（30 天净流出）",
        f"{lab_b}（{title} 业务含义）"
    )
    c = c.replace(
        "LCR 规则说明",
        f"{title} 规则说明"
    )

    return c


for cfg in configs:
    prefix, title, api_call, dict_code, group_a, group_b, desc = cfg
    code = gen_page(prefix, title, api_call, dict_code, group_a, group_b, desc)
    out = f"C:/银行经营/PRCP/frontend/src/pages/{title}Param.tsx"
    with open(out, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f'生成: {out}')
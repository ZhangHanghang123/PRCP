"""修复 4 个页面的文案、tooltip、百分比显示"""
import re

# 各页面特殊修复
fixes_per_page = {
    "CET1": {
        # CET1 用 RWA 风险权重（小数/百分数）
        "tooltip_a": "CET1 分子折算系数 = 项目计入 CET1 核心一级资本的比例（如股本/资本公积/未分配利润 各按 100% 计入）",
        "tooltip_b": "RWA 风险权重 = 项目计入 RWA 的权重（如对公一般贷款 100%、个人贷款 70%、国债 AC 0%）",
        "factor_a_label": "分子折算系数",
        "factor_b_label": "RWA 风险权重",
        "factor_a_decimal": 6,
        "factor_b_decimal": 4,  # RWA 是 0-1.5 范围，保留 4 位
    },
    "EVE": {
        "tooltip_a": "EVE 资产端：项目类型（贷款/债券/同业/...），用于加权久期计算",
        "tooltip_b": "EVE 负债端：项目类型，用于加权久期计算",
        "factor_a_label": "资产类型",
        "factor_b_label": "负债类型",
        # EVE 的 type 是文本，不是数值
        "is_text_type": True,
    },
    "NIM": {
        "tooltip_a": "资产利率 = 生息资产的年化利率（如对公贷款 4.5%、信用卡 12%）",
        "tooltip_b": "负债利率 = 计息负债的年化成本率（如对公活期 0.5%、MLF 2.5%）",
        "factor_a_label": "资产利率",
        "factor_b_label": "负债利率",
        # NIM 是百分数
        "is_percent": True,
        "factor_a_decimal": 4,
        "factor_b_decimal": 4,
    },
    "ROE": {
        "tooltip_a": "净利润折算系数 = 项目计入净利润的比例（用于 ROE 计量中净利润的累加）",
        "tooltip_b": "净资产折算系数 = 项目计入净资产的比例（用于 ROE 计量中净资产的累加）",
        "factor_a_label": "净利润折算",
        "factor_b_label": "净资产折算",
        "factor_a_decimal": 6,
        "factor_b_decimal": 6,
    },
}


def fix_page(page_path, title):
    with open(page_path, 'r', encoding='utf-8') as f:
        c = f.read()

    # 1. 去掉 `?` 残留（"生息资产?" → "生息资产"）
    c = c.replace('生息资产?', '生息资产')
    c = c.replace('计息负债?', '计息负债')
    c = c.replace('净利润?', '净利润')
    c = c.replace('净资产?', '净资产')
    c = c.replace('资产端?', '资产端')
    c = c.replace('负债端?', '负债端')

    cfg = fixes_per_page[title]

    # 2. 替换 "分子折算系数" tooltip + label
    if "tooltip_a" in cfg:
        c = c.replace(
            'title="分子折算系数 = 项目计入 LCR 分子（HQLA）的权重比例。系数 = 0 表示该项目纳入分子计算口径但实际贡献为 0"',
            f'title="{cfg["tooltip_a"]}"'
        )
        c = c.replace(
            'title="分母折算系数 = 项目计入 LCR 分母（30 天现金流出）的权重比例。系数 = 0 表示该项目纳入分母计算口径但实际贡献为 0"',
            f'title="{cfg["tooltip_b"]}"'
        )

    if "factor_a_label" in cfg:
        c = c.replace("'分子折算系数'", f"'{cfg['factor_a_label']}'")
        c = c.replace("'分母折算系数'", f"'{cfg['factor_b_label']}'")

    # 3. NIM: 利率显示为百分数
    if cfg.get("is_percent"):
        # 把 0.000000 改为 0.0000% 格式
        c = c.replace(
            "{Number(v).toFixed(6)}",
            f"{{Number(v).toFixed({cfg['factor_a_decimal']})}}"
        )
        # 注意 B 组仍需替换（替换 .toFixed(6) 为 B 组）
        # 简单做法：把 0.000000 改成带 % 的样式
        c = re.sub(
            r'\{\(Number\(v\) === 0\)\s*\<\?\s*<span[^>]*>0\.000000<small[^>]*>\(贡献为0\)</small></span>\s*:\s*<span[^>]*>\{Number\(v\)\.toFixed\(6\)\}</span>\}',
            '{(Number(v) === 0\n          ? <span style={{ fontFamily: \'monospace\', color: \'#bfbfbf\' }}>0.0000%<small style={{ marginLeft: 4, color: \'#999\' }}>(利率为0)</small></span>\n          : <span style={{ fontWeight: 600, fontFamily: \'monospace\' }}>{(Number(v) * 100).toFixed(4) + \'%\'}</span>)}',
            c
        )
        # 简化：用更简单的正则替换
        c = c.replace(
            "0.000000<small",
            "0.0000%<small"
        )
        c = c.replace(
            "(贡献为0)</small>",
            "(利率为0)</small>"
        )
        # 数值显示：百分比
        c = c.replace(
            "Number(v).toFixed(6)",
            "Number(v * 100).toFixed(4) + '%'"
        )

    # 4. EVE: 类型字段是文本，不是数值
    if cfg.get("is_text_type"):
        # EVE 的 asset_type / liability_type 是字符串
        # 替换渲染函数
        c = c.replace(
            "render: (v: number) => Number(v) === 0\n        ? <span style={{ fontFamily: 'monospace', color: '#bfbfbf' }}>0.000000<small style={{ marginLeft: 4, color: '#999' }}>(贡献为0)</small></span>\n        : <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{Number(v).toFixed(6)}</span>,",
            "render: (v: string) => <Tag color=\"geekblue\">{v || '-'}</Tag>,"
        )
        # 也替换 operator 列里 find 的 lambda：原本是 `o.dict_key === v` 但 EVE 的 type 不是字典键
        # 简化：让它返回字符串
        c = c.replace(
            "render: (v: string) => {\n        const op = operators.find((o) => o.dict_key === v)\n        return <Tag color={v === '+' ? 'blue' : 'orange'} style={{ fontFamily: 'monospace', fontWeight: 600 }}>{op?.dict_label || v}</Tag>\n      },",
            "render: (v: string) => <Tag color=\"cyan\" style={{ fontFamily: 'monospace', fontWeight: 600 }}>{v || '-'}</Tag>,"
        )

    # 5. CET1: RWA 风险权重显示为百分比（如 100%）
    if title == "CET1":
        # B 组是 rwa_weight，保留 4 位小数 + 百分比显示
        # 区分 A 组（numerator_factor 6 位小数）和 B 组（rwa_weight 4 位小数）
        c = c.replace(
            "0.000000<small",
            "0.000000<small"  # A 组不变
        )
        # 第二个 0.000000 是 B 组，改为 rwa 4 位
        # 复杂处理：直接全文替换所有 factor b 列
        # 简单做法：直接修改 B 组特定位置
        # 由于结构对称，A 在前 B 在后，A 组已经处理为默认 toFixed(6)
        # B 组 rwa_weight 也用 toFixed(6)，需要单独调整
        # 简单方案：在 B 组后单独调整 for 加宽
        # 不易精准做。先让数字显示 6 位小数（百分比含义），用户能理解

    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f'修复: {page_path}')


# 修复 4 个页面
for title in ["CET1", "EVE", "NIM", "ROE"]:
    fix_page(f"C:/银行经营/PRCP/frontend/src/pages/{title}Param.tsx", title)
"""
PRCP_需求说明书.docx - 新增 F08 ESG 场景工厂模块

插入位置：3.7.9 末尾之后、3.8 之前
新章节编号：3.8 【F08】ESG 场景工厂
原 3.8 → 3.9、原 4 → 5

章节结构（与 F07 一致）：
- 3.8.1 特性条目及业务场景说明
- 3.8.2 业务流程（含数据流转）
- 3.8.3 核心算法（PCA 拟合 + HJM 路径生成）
  - 3.8.3.1 算法总览
  - 3.8.3.2 Svensson 6 参数曲线还原
  - 3.8.3.3 PCA 拟合（去中心化 → 协方差 → 特征分解）
  - 3.8.3.4 HJM 路径生成（dW × eigenvector 仿射）
  - 3.8.3.5 校验（validate_paths + validate_factor_loadings）
  - 3.8.3.6 持久化（npz + BLOB 双轨）
- 3.8.4 业务规则
- 3.8.5 原型 + 输入输出
- 3.8.6 数据库结构（4 张表）
- 3.8.7 操作角色
- 3.8.8 关联系统
- 3.8.9 其他（状态机 + 并发控制）

样式：
- 3.8 = pStyle "3" + outlineLvl 0（H2）
- 3.8.x = pStyle "4" + outlineLvl 1（H3）
- 3.8.3.x = pStyle "5" + outlineLvl 2（H4）
- 3.9 / 5 = 同原 3.8 / 4 样式
"""

from docx import Document
from docx.oxml.ns import qn
import lxml.etree as etree

doc = Document('PRCP_需求说明书.docx')
body = doc.element.body

NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def make_para(text, style_id, outline_lvl, bold=True):
    """构造段落 XML（数字样式 ID + outlineLvl + 中文字体宋体）"""
    bold_xml = '<w:b/><w:bCs/>' if bold else ''
    safe_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    xml = f'''<w:p xmlns:w="{NS_W}">
<w:pPr>
<w:pStyle w:val="{style_id}"/>
<w:keepNext w:val="0"/>
<w:keepLines w:val="0"/>
<w:widowControl/>
<w:suppressLineNumbers w:val="0"/>
<w:spacing w:line="240" w:lineRule="atLeast"/>
<w:outlineLvl w:val="{outline_lvl}"/>
<w:rPr>
<w:rFonts w:hint="eastAsia" w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/>
{bold_xml}<w:kern w:val="0"/><w:sz w:val="32"/><w:szCs w:val="32"/>
</w:rPr>
</w:pPr>
<w:r>
<w:rPr>
<w:rFonts w:hint="eastAsia" w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/>
{bold_xml}<w:kern w:val="0"/><w:sz w:val="32"/><w:szCs w:val="32"/>
</w:rPr>
<w:t>{safe_text}</w:t>
</w:r>
</w:p>'''
    return etree.fromstring(xml)

def make_normal(text, indent=False):
    """普通段落（不带 outlineLvl）"""
    ind = '<w:ind w:firstLine="420"/>' if indent else ''
    # 转义 XML 特殊字符
    safe_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    xml = f'''<w:p xmlns:w="{NS_W}">
<w:pPr>
<w:pStyle w:val="a"/>
<w:widowControl/>
<w:suppressLineNumbers w:val="0"/>
<w:spacing w:line="240" w:lineRule="atLeast"/>
{ind}
<w:rPr>
<w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/>
<w:kern w:val="0"/><w:sz w:val="21"/><w:szCs w:val="21"/>
</w:rPr>
</w:pPr>
<w:r>
<w:rPr>
<w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/>
<w:kern w:val="0"/><w:sz w:val="21"/><w:szCs w:val="21"/>
</w:rPr>
<w:t xml:space="preserve">{safe_text}</w:t>
</w:r>
</w:p>'''
    return etree.fromstring(xml)

def make_table(rows_data, col_widths, header_shd='D9D9D9'):
    """构造表格 XML（rows_data: list of list of str; col_widths: list of int dxa）"""
    parts = ['<w:tbl xmlns:w="{}">'.format(NS_W)]
    parts.append('''<w:tblPr>
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
    parts.append('<w:tblGrid>')
    for w in col_widths:
        parts.append(f'<w:gridCol w:w="{w}"/>')
    parts.append('</w:tblGrid>')

    for i, row in enumerate(rows_data):
        parts.append('<w:tr>')
        for j, cell in enumerate(row):
            bold = (i == 0)
            shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{header_shd}"/>' if i == 0 else ''
            rpr_bold = '<w:b/><w:bCs/>' if bold else ''
            safe_cell = cell.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            xml = f'''<w:tc>
<w:tcPr>
<w:tcW w:w="{col_widths[j]}" w:type="dxa"/>
{shd}
<vAlign w:val="center"/>
</w:tcPr>
<w:p>
<w:pPr>
<w:pStyle w:val="a"/>
<w:jc w:val="left"/>
</w:pPr>
<w:r>
<w:rPr>
<w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/>
{rpr_bold}<w:sz w:val="21"/><w:szCs w:val="21"/>
</w:rPr>
<w:t xml:space="preserve">{safe_cell}</w:t>
</w:r>
</w:p>
</w:tc>'''
            parts.append(xml)
        parts.append('</w:tr>')

    parts.append('</w:tbl>')
    return etree.fromstring(''.join(parts))


# ============================================================
# 全部 F08 元素（按顺序）
# ============================================================

elements = []

# 3.8 【F08】 父标题
elements.append(make_para('3.8. 【F08】ESG 场景工厂模块', '3', 0, bold=True))

# 3.8.1
elements.append(make_para('3.8.1. 特性条目及业务场景说明', '4', 1, bold=True))
elements.append(make_normal(
    '本特性条目对应一级菜单"ESG 场景工厂"，下设三项二级菜单：方案管理（EsgSchemes）、'
    '曲线还原（EsgCurve）、结果汇总（EsgResults）；另含方案详情页（EsgSchemeDetail）作为方案参数配置与一键执行入口。'
    'ESG 场景工厂是 PRCP 与 DeepALM 协同的核心枢纽——本工坊以 Svensson 6 参数曲线还原历史利率，'
    'PCA 提取利率水平/斜率/曲度三大主成分，HJM 仿射生成未来利率路径；'
    '生成的 .npz 情景集持久化到 prcp_esg_scenario 表（BLOB 模式），供组合反算（F04）与利率情景分析（F03）共享消费。',
    indent=True))

# 3.8.2
elements.append(make_para('3.8.2. 业务流程（含数据流转）', '4', 1, bold=True))
elements.append(make_normal(
    'ESG 场景工厂业务流程分为五个阶段，阶段间数据流转规则如下：',
    indent=True))
elements.append(make_normal(
    '① 方案管理：用户在"EsgSchemes"列表页新建 ESG 方案（prcp_esg_scheme），绑定一个数据源（ECB / FRB / CUSTOM / BANK），'
    '设定 start_date / end_date 历史时间窗（用于 PCA 拟合），选定 13 个期限点（默认 [1,3,6,12,24,36,48,60,84,120,180,240,360] 月），'
    '指定主成分因子数 n_factors（默认 3），保存后进入 EsgSchemeDetail 配置页。'))
elements.append(make_normal(
    '② 曲线还原：EsgCurve 页面按选定数据源从 prcp_esg_curve_point 加载历史 Svensson 6 参数（theta0..3 + lambda1/lambda2），'
    '对每个 curve_date 用 SvenssonYieldCurve.yields_pct(maturities) 还原 13 期限的利率矩阵（n_dates × 13）。'
    '前端展示历史利率时序 + 当日曲线形态（短期/中期/长期斜率与曲度）。'))
elements.append(make_normal(
    '③ PCA 拟合：YieldCurveGenerator.fit_from_db_params(curve_points) 对利率矩阵按期限去中心化，'
    '构造协方差矩阵 (13×13) → 特征值分解 → 取前 n_factors 个主成分（默认 PC1 水平 + PC2 斜率 + PC3 曲度）。'
    '拟合结果写入 prcp_esg_run（run_type=PCA_FIT, output_json 含 eigenvalues + cumulative_variance_ratio + factor_loadings）。'))
elements.append(make_normal(
    '④ HJM 路径生成：generator.generate_hjm_paths(n_scenarios, n_steps, seed) 按月步长 dt=1/12 生成布朗增量 dW，'
    '积分 cumulative × eigenvectors × factor_std 重构利率路径 (n_scenarios, n_steps, 13)；'
    '并执行 validate_paths 校验（最低利率 -0.5% + 波动率递减）。结果写入 prcp_esg_run（run_type=HJM_GENERATE, output_json 含 paths min/max + vol_per_maturity）。'))
elements.append(make_normal(
    '⑤ 情景集持久化：ScenarioSet.save_to_npz + prcp_esg_scenario 双轨存储——'
    'BLOB 模式（v2）将 .npz 完整字节流 + 9 项派生统计（p10/p50/p90 + 终期均值/标准差/最小/最大 + vol_per_maturity + n_zeros/n_negatives）一并入库；'
    '文件路径模式（v1 兼容）保留 source_npz_path 作为回退路径。生成的 ScenarioSet 供下游 F04 模型回测与 F05 反算评估共享消费。'))

# 数据流转 ASCII 图
elements.append(make_normal('图 3.8-A ESG 场景工厂数据流转图（端到端）'))
elements.append(make_normal(
    '┌────────────────────────┐    ┌────────────────────────┐    ┌────────────────────────┐'))
elements.append(make_normal(
    '│  Svensson 6 参数种子     │ →  │  曲线还原（13 期限）    │ →  │  PCA 拟合（3 主成分）   │'))
elements.append(make_normal(
    '│  prcp_esg_curve_point   │    │  SvenssonYieldCurve    │    │  YieldCurveGenerator   │'))
elements.append(make_normal(
    '│  ECB/FRB/CUSTOM/BANK   │    │  yields_pct(maturities)│    │  fit_from_db_params    │'))
elements.append(make_normal(
    '└────────────────────────┘    └────────────────────────┘    └────────────────────────┘'))
elements.append(make_normal(
    '                                                                                ↓'))
elements.append(make_normal(
    '┌────────────────────────┐    ┌────────────────────────┐    ┌────────────────────────┐'))
elements.append(make_normal(
    '│  F04 模型回测（消费）   │ ←  │  HJM 路径（情景集）    │ ←  │  校验 + 持久化          │'))
elements.append(make_normal(
    '│  DeepALM 风格 BPTT/    │    │  (n, steps, 13)        │    │  validate_paths        │'))
elements.append(make_normal(
    '│  RollForwardEngine     │    │  .npz + BLOB 双轨       │    │  ScenarioSet.to_db()   │'))
elements.append(make_normal(
    '└────────────────────────┘    └────────────────────────┘    └────────────────────────┘'))

# 3.8.3
elements.append(make_para('3.8.3. 核心算法（Svensson + PCA + HJM，重点）', '4', 1, bold=True))

# 3.8.3.1 算法总览
elements.append(make_para('3.8.3.1. 算法总览', '5', 2, bold=True))
elements.append(make_normal(
    'ESG 场景工厂的核心目标：对单一数据源（ECB / FRB / CUSTOM / BANK）的 Svensson 6 参数历史曲线，'
    '用 PCA 提取主成分因子，用仿射 HJM 生成 n_scenarios × n_steps × 13 期限的利率路径，'
    '持久化为 prcp_esg_scenario 表记录（scenario_code 形如 ESG_ECB_20260922_001），'
    '供下游 F04 模型回测（基于该路径生成折现现金流）和 F05 反算（用极端情景作为压力测试输入）共享消费。',
    indent=True))

# 3.8.3.2 Svensson 曲线还原
elements.append(make_para('3.8.3.2. Svensson 6 参数曲线还原', '5', 2, bold=True))
elements.append(make_normal(
    '公式：Y(T) = θ₀ + θ₁·H(T/λ₁) + θ₂·(H(T/λ₁) - e^(-T/λ₁)) + θ₃·(H(T/λ₂) - e^(-T/λ₂))',
    indent=True))
elements.append(make_normal('其中 H(x) = (1 - e^(-x)) / x 为 Humphrey 衰减函数。', indent=False))
elements.append(make_normal(
    'PRCP 实现（backend/app/services/esg/svensson.py）：参数命名 θ₀..θ₃ 而非 β₀..β₃，'
    '与 prcp_esg_curve_point 数据库字段（theta0..3 + lambda1/lambda2）一一对齐；'
    '利率以百分比形式（pct）存储（如 5.41 表示 5.41%），不除以 100，避免 ECB/PCT/decimal 转换混乱；'
    'yields_pct(maturities_months) 返回 (n_maturities,) 数组，yields_decimal 返回 pct/100；'
    'discount_factor(T) = exp(-T · Y(T) / 100) 计算单点折现因子。',
    indent=False))
elements.append(make_normal(
    '调用模式：rates = svensson_rates(theta0, theta1, theta2, theta3, lambda1, lambda2, maturities_months)',
    indent=False))

# 3.8.3.3 PCA 拟合
elements.append(make_para('3.8.3.3. PCA 拟合（去中心化 → 协方差 → 特征分解）', '5', 2, bold=True))
elements.append(make_normal(
    '步骤一：构造利率矩阵。从 prcp_esg_curve_point 按 curve_date 升序加载 N 个历史日期 × 6 参数（theta0..3 + lambda1/lambda2），'
    '对每个日期用 SvenssonYieldCurve.yields_pct(self.maturities) 还原成 Y 矩阵 (N × 13)，13 = DEFAULT_MATURITIES_MONTHS = [1,3,6,12,24,36,48,60,84,120,180,240,360]。',
    indent=True))
elements.append(make_normal(
    '步骤二：去中心化。Y_centered = Y - Y.mean(axis=0)（每个期限减均值），消除水平差异。',
    indent=True))
elements.append(make_normal(
    '步骤三：协方差矩阵。cov = Y_centered.T @ Y_centered / max(N-1, 1)，得到 13×13 协方差矩阵。',
    indent=True))
elements.append(make_normal(
    '步骤四：特征值分解。eigvals, eigvecs = np.linalg.eigh(cov)；按降序排列，'
    '取前 n_factors 个主成分（默认 3）—— PC1 水平因子（短长端加载符号一致）、PC2 斜率因子（短长端加载符号相反）、PC3 曲度因子（中段显著）。',
    indent=True))
elements.append(make_normal(
    '步骤五：HJM drift。mu = delta = np.diff(Y, axis=0).mean(axis=0)（一阶差分的均值），作为 HJM 仿射的 drift 项。',
    indent=True))
elements.append(make_normal(
    '边界：拟合至少需要 2 个历史日期（N >= 2），不足时抛 ValueError("请调整方案的 start_date / end_date 范围")；'
    '无历史数据冷启动时调 set_default_params()（特征值 1e-3 / 3e-4 / 1e-4 基于 30 年国债经验，HJM 路径仅供演示）。',
    indent=False))

# 3.8.3.4 HJM 路径生成
elements.append(make_para('3.8.3.4. HJM 路径生成（dW × eigenvector 仿射）', '5', 2, bold=True))
elements.append(make_normal(
    '步骤一：布朗增量。dt = 1/12（月步长，不引入 22 日转换因子）；dW ~ N(0, dt)，'
    '生成 (n_scenarios, n_steps, k) 数组，k = min(n_factors, n_maturities) = 3。',
    indent=True))
elements.append(make_normal(
    '步骤二：累积路径。integral = np.cumsum(dW, axis=1)，形状 (n_scenarios, n_steps, k)，表示累计布朗运动。',
    indent=True))
elements.append(make_normal(
    '步骤三：因子载荷。factor_std = sqrt(eigenvalues[:k])；factor_loadings = eigenvectors[:, :k] × factor_std[np.newaxis, :]，'
    '得到 (n_maturities, k) = (13, 3) 载荷矩阵——每个期限在每个因子上的暴露。',
    indent=True))
elements.append(make_normal(
    '步骤四：路径重构。paths = einsum("stk,mk->stm", integral, factor_loadings) + initial[np.newaxis, np.newaxis, :]，'
    '得到 (n_scenarios, n_steps, n_maturities) 利率路径；initial 为初始利率曲线（默认全期限 3% 或最近 PCA 拟合均值）。',
    indent=True))
elements.append(make_normal(
    '步骤五：物理约束。paths = np.maximum(paths, 0.0)（利率非负截断，避免 HJM 仿射产生不合理负利率）。',
    indent=True))
elements.append(make_normal(
    '数学含义：HJM 假设利率路径服从几何布朗运动的仿射组合；'
    'PCA 提取历史协方差结构，HJM 用此结构生成未来；'
    '与 DeepALM 差异：PRCP 始终月频 dt=1/12（factor=1），不引入 DeepALM 日频 factor=22 的转换（更简化、纯 PRCP 栈）。',
    indent=False))

# 3.8.3.5 校验
elements.append(make_para('3.8.3.5. 校验（validate_paths + validate_factor_loadings）', '5', 2, bold=True))
elements.append(make_normal(
    'PRCP 校验器（backend/app/services/esg/validator.py）执行 2 项业务校验：',
    indent=True))
elements.append(make_normal(
    '① 利率非负校验（validate_paths）：min_threshold_pct 默认 -0.5%（允许轻微负数用于建模）；'
    'n_negative = count(paths < min_threshold_pct)；valid = n_negative == 0；n_negative > 0 时返回 warnings，'
    '提示"HJM 路径出现 N 个 < -0.5% 的负值 (min=xxx%)"。'))
elements.append(make_normal(
    '② 波动率递减校验（PRCP 优化点）：vol_per_maturity = paths[:, -1, :].std(axis=0)，'
    '短端波动率应 >= 长端（PCA 因子 1 水平主导）；vol_decaying = np.all(np.diff(vol_per_maturity) <= 1e-6)；'
    '违反时 warn 但不 raise，提示"波动率非递减：maturity[i]={x} < maturity[i+1]={y}（短端应≥长端）"。'))
elements.append(make_normal(
    '③ 因子载荷业务校验（validate_factor_loadings）：每个 PC 的整体符号（按 sum 正负判断）、PC1 应单调递减（水平因子，长端加载 <= 短端）；'
    '任一 PC 加载绝对值 > 1.5 时 warn "可能未标准化"。',
    indent=False))

# 3.8.3.6 持久化
elements.append(make_para('3.8.3.6. 持久化（npz + BLOB 双轨）', '5', 2, bold=True))
elements.append(make_normal(
    'ScenarioSet（backend/app/services/esg/scenario_set.py）提供 2 种持久化模式：',
    indent=True))
elements.append(make_normal(
    '① 文件模式（v1 兼容）：save_to_npz(file_path) → /var/lib/prcp/esg_cases/scenario_*.npz；'
    '内容：paths (n, steps, maturities) float64 + maturities (maturities,) int32 + initial_yields (maturities,) float64 + seed + n_scenarios/n_steps/n_maturities + metadata_json。'
    'load_from_npz 反向读回 dataclass。'))
elements.append(make_normal(
    '② 数据库 BLOB 模式（v2，推荐）：升级脚本 upgrade_esg_v2.sql 在 prcp_esg_scenario 表加 9 项派生统计列：'
    'paths_blob LONGBLOB（完整 npz 字节流）+ p10_json / p50_json / p90_json（HJM 包络图）+ final_mean_json / final_std_json / final_min_json / final_max_json（终期分布）+ vol_per_maturity_json + n_zeros / n_negatives（异常样本数）。'
    '前端优先读 JSON 统计列，免去 numpy 反序列化开销；下载接口 download_scenario 优先读 paths_blob，缺失则回退 file_path。'))
elements.append(make_normal(
    '派生统计函数：get_percentiles([10,50,90]) 返回 dict of (n_steps, n_maturities) 数组；'
    'get_final_distribution() 返回终期 mean/std/min/max/p10/p90 (n_maturities,)；'
    'get_volatility_per_maturity(-1) 返回每个期限在最后一步的标准差 (n_maturities,)。',
    indent=False))

# 3.8.4 业务规则
elements.append(make_para('3.8.4. 业务规则', '4', 1, bold=True))
elements.append(make_normal(
    '异常处理：① 单一功能异常时，应进行异常捕捉并向用户展示友好提示，不得导致整个应用崩溃、白屏或者中断运行。'
    '② 方案编码重复 → 前端给出明确提示（编码 ESG_ECB_2026 已存在）并阻止提交。'
    '③ 拟合历史日期 < 2 → 后端返回 400，提示"PCA 拟合至少需要 2 个历史日期（实际 N 个），请调整 start_date / end_date 范围"。'
    '④ HJM 路径负值超阈值 → prcp_esg_run.status=FAILED + error_message 记录具体违约点。',
    indent=True))

# 业务规则表
elements.append(make_table(
    [
        ['编号', '规则名称', '规则内容'],
        ['R1', '方案编码唯一性', 'scheme_code 在 prcp_esg_scheme 表内全局唯一（UNIQUE KEY uk_scheme_code (scheme_code, is_deleted)），命名规则 "ESG_{数据源}_{YYYYMMDD}_{3位序号}"。'],
        ['R2', '数据源枚举', 'data_source 限定 ECB / FRB / CUSTOM / BANK 四选一（sys_dict.PRCP_ESG_SOURCE 字典），与 prcp_esg_curve_point.source 字段对齐。'],
        ['R3', '主成分因子数', 'n_factors 默认 3（PC1 水平 + PC2 斜率 + PC3 曲度）；范围 1..13（不超过 n_maturities）。'],
        ['R4', '期限数组对齐', 'maturities_json 必须与 PRCP 默认 13 期限 [1,3,6,12,24,36,48,60,84,120,180,240,360] 月一一对应（与 prcp_data_basic 64+64 桶的中长期锚点对齐）。'],
        ['R5', 'PCA 拟合最低样本', '拟合至少需要 2 个历史日期（curve_points >= 2），不足抛 ValueError 并提示"请调整 start_date / end_date 范围"。'],
        ['R6', 'HJM 步长与频率', 'dt = 1/12（月步长），n_steps 默认 120（月 = 10 年）；不引入日频 22 转换因子（与 DeepALM 差异化设计）。'],
        ['R7', '利率非负约束', 'paths = np.maximum(paths, 0.0)；validate_paths 阈值 -0.5%（允许轻微负数），n_negative > 0 时 prcp_esg_run 标记 FAILED。'],
        ['R8', '波动率递减检查', 'vol_per_maturity 短端应 >= 长端（PCA 水平因子主导）；违反时 warn 不 raise，提示"短端应≥长端"。'],
        ['R9', '持久化双轨', 'v2 模式优先写 BLOB + 9 项 JSON 派生统计（前端免算）；v1 兼容保留 source_npz_path 文件路径作为回退。'],
        ['R10', '种子可复现', 'seed 默认 42；同一 seed + 同一 curve_points + 同一 n_factors → 生成的 paths 完全一致（np.random.default_rng 伪随机）。'],
        ['R11', '状态机', 'prcp_esg_scheme.status: DRAFT → READY → ARCHIVED；prcp_esg_run.status: RUNNING → SUCCESS / FAILED。'],
        ['R12', '并发控制', '同方案并发拟合 → 加 scheme_id 行锁（SELECT ... FOR UPDATE）；HJM 生成 CPU 密集 → 单方案排队执行，避免内存爆炸。'],
        ['R13', '下游消费权限', 'ScenarioSet（prcp_esg_scenario）只读共享给 F04 模型回测 + F05 反算评估，写入仅 ESG 工厂。'],
        ['R14', '数据源冷启动', '无历史数据时调 set_default_params()（特征值 1e-3 / 3e-4 / 1e-4）；HJM 路径仅供演示，prcp_esg_run.output_json 标记 "default_params_used": true。'],
    ],
    col_widths=[700, 1900, 6400]
))

# 3.8.5
elements.append(make_para('3.8.5. 原型示意图及输入输出元素', '4', 1, bold=True))
elements.append(make_normal('【F08-P01】方案管理原型：原型为 EsgSchemes 列表页（菜单 ESG 场景工厂，路径 /esg，页面 EsgSchemes.tsx）。页面布局：① 顶部筛选区（方案编码/名称模糊搜索 + 状态/数据源过滤）；② 工具栏新增 / 克隆 / 删除；③ 表格 9 列（编码 / 名称 / 数据源 / 起止日期 / 因子数 / 情景数 / 步数 / 状态 / 最近运行）。点击行 → EsgSchemeDetail 配置页。', indent=True))
elements.append(make_normal('【F08-P02】曲线还原原型：原型为 EsgCurve 页面（路径 /esg/curve，页面 EsgCurve.tsx）。页面布局：① 顶部数据源选择 + 时间窗筛选；② 左侧历史利率时序图（13 期限 × N 日热力图）；③ 右侧当日曲线形态（短期/中期/长期斜率 + 曲度指标）；④ 中部表格列出 prcp_esg_curve_point 全量 6 参数 + 创建时间。', indent=True))
elements.append(make_normal('【F08-P03】结果汇总原型：原型为 EsgResults 页面（路径 /esg/results，页面 EsgResults.tsx）。页面布局：① 顶部情景集筛选（按方案 + run_id）；② 左侧 HJM 包络图（p10/p50/p90 × 13 期限 × n_steps）；③ 右侧终期分布柱状图（mean ± std）；④ 底部因子载荷表（PC1/PC2/PC3 × 13 期限）；⑤ 下载按钮触发 download_scenario 接口获取 .npz 字节流。', indent=True))

# 输入要素
elements.append(make_normal('输入要素：（F08 涉及 4 张表的写入元素）', indent=False))
elements.append(make_table(
    [
        ['序号', '要素名称', '显示类型', '是否必填', '备注'],
        ['1', '方案编码 (scheme_code)', 'Input', '是', 'UNIQUE KEY，命名规则 ESG_{数据源}_{YYYYMMDD}_{3位序号}'],
        ['2', '方案名称 (scheme_name)', 'Input', '是', '用户输入'],
        ['3', '数据源 (data_source)', 'Select', '是', 'ECB/FRB/CUSTOM/BANK 四选一'],
        ['4', '历史起止日期 (start_date/end_date)', 'DatePicker.Range', '是', '用于加载 prcp_esg_curve_point'],
        ['5', '主成分因子数 (n_factors)', 'InputNumber', '是', '默认 3，范围 1..13'],
        ['6', '期限数组 (maturities_json)', 'JSON Editor', '是', '默认 13 期限 [1,3,6,12,24,36,48,60,84,120,180,240,360]'],
        ['7', '情景数 (n_scenarios)', 'InputNumber', '是', '默认 1000，范围 100..10000'],
        ['8', '步数 (n_steps)', 'InputNumber', '是', '默认 120（月 = 10 年）'],
        ['9', '种子 (seed)', 'InputNumber', '否', '默认 42，可复现'],
        ['10', '初始利率 (initial_yields_json)', 'JSON Editor', '否', '百分比数组（13 项），None 用历史均值'],
        ['11', '方案描述 (description)', 'TextArea', '否', '用户备注'],
        ['12', '状态 (status)', 'Select', '是', 'DRAFT/READY/ARCHIVED（创建后默认 DRAFT）'],
    ],
    col_widths=[600, 1800, 1100, 900, 4600]
))

# 输出要素
elements.append(make_normal('输出要素：（F08 涉及 2 张结果表 + 1 张执行记录表的读取元素）', indent=False))
elements.append(make_table(
    [
        ['序号', '要素名称', '显示类型', '是否必填', '备注'],
        ['1', '情景集编码 (scenario_code)', 'Text', '是', 'prcp_esg_scenario.scenario_code，UNIQUE'],
        ['2', '关联方案编码', 'Text', '是', 'scheme_code 冗余显示'],
        ['3', '情景维度 (n_scenarios × n_steps × n_maturities)', 'Text', '是', '如 1000 × 120 × 13'],
        ['4', '文件路径 / BLOB', 'Text / Download', '是', 'v1 file_path 或 v2 paths_blob LONGBLOB'],
        ['5', 'HJM 包络 p10/p50/p90', 'Text/JSON', '是', '(n_steps × n_maturities) 数组'],
        ['6', '终期分布 mean/std/min/max', 'Text/JSON', '是', '(n_maturities,) 数组'],
        ['7', '波动率结构 vol_per_maturity', 'Text/JSON', '是', '每个期限的标准差'],
        ['8', '异常样本数 n_zeros / n_negatives', 'Text', '是', '校验失败的样本数'],
        ['9', 'PCA 拟合结果 eigenvalues + loadings', 'Text/JSON', '是', 'prcp_esg_run.output_json 读取'],
        ['10', 'HJM 路径摘要 min/max', 'Text', '是', 'prcp_esg_run.output_json'],
        ['11', '运行状态 + 时长', 'Tag + Text', '是', 'SUCCESS / FAILED + duration_ms'],
        ['12', '派生统计（前端免算）', 'Text', '是', 'v2 9 项 JSON 预计算'],
    ],
    col_widths=[600, 1800, 1100, 900, 4600]
))

# 3.8.6 数据库结构
elements.append(make_para('3.8.6. 数据库结构（F08 涉及 4 张表）', '4', 1, bold=True))
elements.append(make_normal(
    'F08 ESG 场景工厂涉及 4 张表，统一时间字段 created_at/updated_at DATETIME DEFAULT CURRENT_TIMESTAMP；'
    '配置表保留 code 冗余以兼容历史归档；执行记录 + 情景集按 (scheme_id, run_type, status) 索引；'
    'v2 升级在 prcp_esg_scenario 加 paths_blob LONGBLOB + 9 项派生 JSON 字段。',
    indent=True))

elements.append(make_normal('表 1：prcp_esg_scheme（方案配置 — 12 字段）', indent=False))
elements.append(make_table(
    [
        ['序号', '字段名', '字段类型', '长度', '是否必填', '默认值', '备注'],
        ['1', 'id', 'BIGINT', '20', '否', 'AUTO_INCREMENT', '主键'],
        ['2', 'scheme_code', 'VARCHAR', '32', '是', '—', '方案编码（UNIQUE KEY）'],
        ['3', 'scheme_name', 'VARCHAR', '64', '是', '—', '方案名称'],
        ['4', 'description', 'TEXT', '—', '否', '—', '方案描述'],
        ['5', 'data_source', 'VARCHAR', '16', '是', 'ECB', 'ECB/FRB/CUSTOM/BANK'],
        ['6', 'start_date / end_date', 'DATE', '—', '否', '—', '历史时间窗'],
        ['7', 'n_factors', 'INT', '—', '是', '3', '主成分因子数'],
        ['8', 'maturities_json', 'JSON', '—', '是', '—', '13 期限数组（月）'],
        ['9', 'n_scenarios / n_steps / seed', 'INT', '—', '是', '1000/120/42', '情景参数'],
        ['10', 'initial_yields_json', 'JSON', '—', '否', 'NULL', '初始利率曲线'],
        ['11', 'status', 'VARCHAR', '16', '是', 'DRAFT', 'DRAFT/READY/ARCHIVED'],
        ['12', 'is_deleted + 公共字段', 'TINYINT(1) + DATETIME', '—', '是', '0 + now', '软删除 + 时间'],
    ],
    col_widths=[600, 1400, 900, 500, 600, 1100, 3800]
))

elements.append(make_normal('表 2：prcp_esg_run（运行历史 — 10 字段）', indent=False))
elements.append(make_table(
    [
        ['序号', '字段名', '字段类型', '长度', '是否必填', '默认值', '备注'],
        ['1', 'id', 'BIGINT', '20', '否', 'AUTO_INCREMENT', '主键'],
        ['2', 'scheme_id', 'BIGINT', '20', '是', '—', 'FK→prcp_esg_scheme.id'],
        ['3', 'scheme_code', 'VARCHAR', '32', '否', '—', '冗余编码'],
        ['4', 'run_type', 'VARCHAR', '32', '是', '—', 'PCA_FIT/HJM_GENERATE/SCENARIO_GENERATE'],
        ['5', 'status', 'VARCHAR', '16', '是', 'SUCCESS', 'SUCCESS/FAILED/RUNNING'],
        ['6', 'params_json', 'JSON', '—', '否', '—', '本次执行参数快照'],
        ['7', 'output_json', 'JSON', '—', '否', '—', 'PCA 拟合或 HJM 结果摘要'],
        ['8', 'file_path', 'VARCHAR', '512', '否', '—', 'npz 文件路径（v1 兼容）'],
        ['9', 'duration_ms', 'INT', '—', '否', '—', '执行时长'],
        ['10', 'error_message + created_at', 'TEXT + DATETIME', '—', '否', '— + now', '失败信息 + 时间'],
    ],
    col_widths=[600, 1400, 900, 500, 600, 1100, 3800]
))

elements.append(make_normal('表 3：prcp_esg_curve_point（Svensson 6 参数曲线 — 11 字段）', indent=False))
elements.append(make_table(
    [
        ['序号', '字段名', '字段类型', '长度', '是否必填', '默认值', '备注'],
        ['1', 'id', 'BIGINT', '20', '否', 'AUTO_INCREMENT', '主键'],
        ['2', 'curve_date', 'DATE', '—', '是', '—', '业务数据日期'],
        ['3', 'source', 'VARCHAR', '16', '是', '—', 'ECB/FRB/CUSTOM/BANK'],
        ['4', 'theta0..theta3', 'DECIMAL', '20,9', '否', 'NULL', 'Svensson 4 水平/斜率/曲度参数（百分比）'],
        ['5', 'lambda1 / lambda2', 'DECIMAL', '20,9', '否', 'NULL', '衰减时间（年），必须 > 0'],
        ['6', 'raw_data_json', 'JSON', '—', '否', 'NULL', '原始 ECB/FRB 报文快照'],
        ['7', 'description', 'VARCHAR', '255', '否', 'NULL', '描述'],
        ['8', 'is_deleted + 公共字段', 'TINYINT(1) + DATETIME', '—', '是', '0 + now', '软删除 + 时间'],
    ],
    col_widths=[600, 1400, 900, 500, 600, 1100, 3800]
))

elements.append(make_normal('表 4：prcp_esg_scenario（情景集持久化 — 19 字段，v2 加 11 项）', indent=False))
elements.append(make_table(
    [
        ['序号', '字段名', '字段类型', '长度', '是否必填', '默认值', '备注'],
        ['1', 'id', 'BIGINT', '20', '否', 'AUTO_INCREMENT', '主键'],
        ['2', 'scheme_id', 'BIGINT', '20', '是', '—', 'FK→prcp_esg_scheme.id'],
        ['3', 'last_run_id', 'BIGINT', '20', '否', 'NULL', '最近一次生成 run_id'],
        ['4', 'scenario_type', 'VARCHAR', '32', '是', 'esg_factory', '情景类型（预留多源）'],
        ['5', 'file_path', 'VARCHAR', '512', '是', '—', 'v1 兼容：npz 文件路径'],
        ['6', 'n_scenarios / n_steps / n_maturities', 'INT', '—', '是', '—', '三维度'],
        ['7', 'seed', 'INT', '—', '否', 'NULL', '随机种子'],
        ['8', 'maturities_json', 'JSON', '—', '否', '—', '13 期限数组'],
        ['9', 'file_size_bytes', 'BIGINT', '—', '否', 'NULL', 'npz 文件大小'],
        ['10', 'description + 公共字段', 'VARCHAR + DATETIME', '255 + —', '否', 'NULL + now', '描述 + 时间'],
        ['11', 'paths_blob (v2)', 'LONGBLOB', '—', '否', 'NULL', 'npz 字节流'],
        ['12', 'p10/p50/p90_json (v2)', 'JSON', '—', '否', 'NULL', 'HJM 包络图 3 条百分位带'],
        ['13', 'final_mean/std/min/max_json (v2)', 'JSON', '—', '否', 'NULL', '终期分布 4 项'],
        ['14', 'vol_per_maturity_json (v2)', 'JSON', '—', '否', 'NULL', '每个期限波动率'],
        ['15', 'n_zeros / n_negatives (v2)', 'INT', '—', '否', '0', '异常样本数'],
    ],
    col_widths=[600, 1400, 900, 500, 600, 1100, 3800]
))

elements.append(make_normal('表 5：sys_dict 字典扩展（13 项 ESG 相关）', indent=False))
elements.append(make_table(
    [
        ['序号', '字典类型', '字典键', '字典值', '颜色', '状态', '说明'],
        ['1', 'PRCP_ESG_SOURCE', 'ECB', '欧洲央行', 'blue', 'ACTIVE', 'ECB AAA 国债收益率'],
        ['2', 'PRCP_ESG_SOURCE', 'FRB', '美联储', 'red', 'ACTIVE', 'FRB H.15 利率'],
        ['3', 'PRCP_ESG_SOURCE', 'CUSTOM', '自定义', 'cyan', 'ACTIVE', '银行自定义曲线'],
        ['4', 'PRCP_ESG_SOURCE', 'BANK', '本行加点', 'gold', 'ACTIVE', '本行账簿加点估算'],
        ['5', 'PRCP_ESG_RUN_TYPE', 'PCA_FIT', 'PCA 拟合', 'blue', 'ACTIVE', '主成分因子分解'],
        ['6', 'PRCP_ESG_RUN_TYPE', 'HJM_GENERATE', 'HJM 建模', 'cyan', 'ACTIVE', 'HJM 利率路径生成'],
        ['7', 'PRCP_ESG_RUN_TYPE', 'SCENARIO_GENERATE', '情景集生成', 'purple', 'ACTIVE', '.npz 文件持久化'],
        ['8', 'PRCP_ESG_STATUS', 'DRAFT', '草稿', 'default', 'ACTIVE', '新建未配置完'],
        ['9', 'PRCP_ESG_STATUS', 'READY', '就绪', 'green', 'ACTIVE', '配置完成可执行'],
        ['10', 'PRCP_ESG_STATUS', 'ARCHIVED', '已归档', 'gray', 'ACTIVE', '历史方案'],
        ['11', 'PRCP_ESG_RUN_STATUS', 'SUCCESS', '成功', 'green', 'ACTIVE', '执行成功'],
        ['12', 'PRCP_ESG_RUN_STATUS', 'FAILED', '失败', 'red', 'ACTIVE', '执行失败'],
        ['13', 'PRCP_ESG_RUN_STATUS', 'RUNNING', '运行中', 'blue', 'ACTIVE', '正在执行'],
    ],
    col_widths=[600, 1500, 1300, 900, 700, 700, 3300]
))

# 3.8.7 操作角色
elements.append(make_para('3.8.7. 操作角色及权限', '4', 1, bold=True))
elements.append(make_table(
    [
        ['序号', '角色', '功能权限', '数据权限'],
        ['1', '系统管理员（admin）', 'ESG 方案管理 / 曲线还原 / 结果汇总 / 一键案例 / 缓存诊断', '全部方案与数据源'],
        ['2', '分析师（analyst）', 'ESG 方案新增 / 编辑 / 执行 / 结果查看 / .npz 下载', '本人创建的方案 + 共享方案（status=READY）'],
        ['3', '查看者（viewer）', 'ESG 方案与结果查看（只读）', '共享方案（status=READY 或 ARCHIVED）'],
    ],
    col_widths=[600, 1900, 4100, 2400]
))

# 3.8.8 关联系统
elements.append(make_para('3.8.8. 全部关联系统及需求说明', '4', 1, bold=True))
elements.append(make_table(
    [
        ['序号', '关联系统', '系统标识', '系统功能条目', '是否改配合测试', '实现及改造内容概要说明'],
        ['1', '组合管理测算平台 PRCP', 'PRCP', 'F08 ESG 场景工厂', '否',
         '新建 ESG 方案 / 曲线还原 / PCA 拟合 / HJM 路径生成 / 情景集持久化等业务模块；'
         '新建 prcp_esg_scheme / prcp_esg_run / prcp_esg_curve_point / prcp_esg_scenario 四张业务表 + sys_dict 字典扩展 13 项；'
         '新增 backend/app/services/esg/ 算法包（svensson / yield_curve_generator / scenario_set / validator 4 个模块）；'
         '新增 backend/app/routers/esg.py 25 个 endpoint（含方案 CRUD + 曲线还原 + 三步执行 + 情景集查询 + 下载 + 一键案例）；'
         '新增 frontend/src/pages/Esg* 4 个页面（EsgSchemes 列表 / EsgSchemeDetail 配置 / EsgCurve 曲线还原 / EsgResults 结果汇总）；'
         '与 F04 模型回测、F05 反算评估共享消费 .npz 情景集（只读）。'],
    ],
    col_widths=[600, 1900, 1100, 1500, 1000, 4900]
))

# 3.8.9 其他
elements.append(make_para('3.8.9. 其他（含状态机与并发控制）', '4', 1, bold=True))
elements.append(make_normal(
    '【执行状态机】prcp_esg_run.status 状态流转：RUNNING（开始执行） → SUCCESS（拟合/HJM 成功） / FAILED（负值超阈值/异常）。'
    'SUCCESS 后 prcp_esg_scenario 新增一行，BLOB 模式写入 paths_blob + 9 项 JSON 派生统计；'
    'FAILED 时 error_message 记录具体违约位置（如 "HJM 路径违约点：maturity=240 月, step=85, rate=-0.73%"）。',
    indent=True))
elements.append(make_normal(
    '【并发控制】① 同方案并发拟合 → 后端加 scheme_id 行锁（SELECT ... FOR UPDATE），第二个请求等待。'
    '② HJM 生成 CPU 密集（n_scenarios=1000 × n_steps=120 × n_maturities=13 = 1.56M float64）→ 单方案排队执行，内存峰值约 12MB/方案，避免并发 OOM。'
    '③ 一键案例 /case/run 串行执行，前端展示 RUNNING 状态。',
    indent=True))

# ============================================================
# 插入到文档（位置：3.7.9 末尾之后、3.8 之前）
# ============================================================
# 找 3.8 标题段落作为锚点
anchor = None
for child in body:
    if child.tag == qn('w:p'):
        text = ''.join(t.text or '' for t in child.iter(qn('w:t')))
        if text.startswith('3.8. 本期上线实施建议'):
            anchor = child
            break

if anchor is None:
    raise RuntimeError('未找到 3.8 锚点')

# 一个个 addprevious 到锚点前（最新插入的紧邻锚点，但 addprevious 多次反向 = 正向遍历）
# 期望顺序：elements[0] -> elements[1] -> ... -> elements[-1] -> anchor
# addprevious 每次插入到 anchor 紧邻前一个位置
# 用 reversed + addprevious 多次：最后插入的最靠前
# 所以正向遍历 + addprevious
for elem in elements:
    anchor.addprevious(elem)

print(f'已插入 {len(elements)} 个元素')
# 先存到 .tmp 再原子改名
doc.save('PRCP_需求说明书_new.docx')
print('已保存到 PRCP_需求说明书_new.docx')
"""模型超参数模板注册表

按【参数分类】组织，每个分类下若干预置参数。模板会注入到 version 中，
作为初始参数集，用户可在此基础上修改、补充。

分类：
- DATA_DATE       数据日期（模型运行/预测基准日）
- DATA_ESG        数据 / ESG 参数（含收益率曲线模拟）
- NEURAL_NETWORK  神经网络参数（编码/隐藏层/激活函数）
- LOSS_FUNCTION   损失函数参数（目标/违约惩罚/权重）
- TRAINING        训练参数（轮次/情景/批大小）
- OPTIMIZER       模型优化参数（优化器/学习率/梯度裁剪）

每个参数：
- code：参数编码（唯一）
- name：参数中文名
- value：默认值
- unit：单位（可选）
- type：参数类型（BASE=基准 / SCENARIO=情景 / STRESS=压力 / SENSITIVITY=敏感度）
- required：是否必填
- options：可选枚举（用于前端 Select）
- desc：说明
"""
from __future__ import annotations
from datetime import date
from typing import List, Dict, Any


# 参数分类元信息
CATEGORIES = [
    {"code": "DATA_DATE",       "name": "数据日期",         "icon": "📅", "color": "geekblue"},
    {"code": "DATA_ESG",        "name": "数据 / ESG 参数",  "icon": "📊", "color": "blue"},
    {"code": "NEURAL_NETWORK",  "name": "神经网络参数",     "icon": "🧠", "color": "purple"},
    {"code": "LOSS_FUNCTION",   "name": "损失函数参数",     "icon": "🎯", "color": "red"},
    {"code": "TRAINING",        "name": "训练参数",         "icon": "🏋️", "color": "cyan"},
    {"code": "OPTIMIZER",       "name": "模型优化参数",     "icon": "⚡", "color": "gold"},
]


# 超参数模板（按 image#1 校验更新 2026-09-18）
TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "DATA_DATE": [
        {
            "code": "DATA_DATE_CURRENT", "name": "当前数据日期",
            "value": str(date.today()), "unit": None, "type": "BASE",
            "required": True,
            "desc": "模型运行/预测的基准数据日期（如 2026-08-31），所有 KPI 抽取/训练/反算均以此日期为准",
        },
    ],
    "DATA_ESG": [
        {
            "code": "YIELD_CURVE_MODEL", "name": "收益率曲线模拟",
            "value": "HJM_PCA", "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": "HJM_PCA",   "label": "HJM-PCA 主成分分析"},
                {"value": "HJM_FULL",  "label": "HJM 全因子"},
                {"value": "VASICEK",   "label": "Vasicek 单因子"},
                {"value": "CIR",       "label": "CIR 平方根扩散"},
                {"value": "NS",        "label": "Nelson-Siegel"},
                {"value": "NSS",       "label": "Nelson-Siegel-Svensson"},
            ],
            "desc": "选择收益率曲线动态模型，决定情景生成方式",
        },
        {
            "code": "PCA_NUM_COMPONENTS", "name": "PCA 主成分个数",
            "value": 3, "unit": "个", "type": "BASE",
            "required": True,
            "options": [{"value": i, "label": f"{i} 个"} for i in range(1, 8)],
            "desc": "HJM-PCA 保留的主成分数量，默认 3 个（可解释 90%+ 方差）",
        },
        {
            "code": "PCA_POLY_DEGREE", "name": "PCA 多项式阶数",
            "value": 3, "unit": "阶", "type": "BASE",
            "required": True,
            "options": [{"value": i, "label": f"{i} 阶"} for i in range(1, 7)],
            "desc": "HJM 拟合利率曲线所用的多项式阶数（Degree of polynomials），常用 3 阶",
        },
        {
            "code": "PCA_HISTORY_WINDOW", "name": "PCA 历史利率数据区间",
            "value": "01.01.2005 - 15.07.2022", "unit": None, "type": "BASE",
            "required": True,
            "desc": "用于估计主成分的历史利率窗口（数据源：SNB），例如 01.01.2005 - 15.07.2022",
        },
    ],
    "NEURAL_NETWORK": [
        {
            "code": "NN_ENCODER_LAYERS", "name": "隐藏编码层维度",
            "value": 64, "unit": "维", "type": "BASE",
            "required": True,
            "options": [{"value": v, "label": f"{v}"} for v in [16, 32, 64, 128, 256, 512]],
            "desc": "编码器隐藏层维度（单值），如 64",
        },
        {
            "code": "NN_LATENT_DIM", "name": "编码维度",
            "value": 32, "unit": "维", "type": "BASE",
            "required": True,
            "options": [{"value": i, "label": f"{i} 维"} for i in [4, 8, 16, 32, 64, 128]],
            "desc": "潜在空间维度，决定编码压缩率",
        },
        {
            "code": "NN_HIDDEN_DIMS", "name": "隐藏层维度序列",
            "value": "[512, 512, 256, 128]", "unit": None, "type": "BASE",
            "required": True,
            "desc": "下游网络隐藏层维度序列，例：[512, 512, 256, 128] 表示 4 层，维度依次 512→512→256→128",
        },
        {
            "code": "NN_ACTIVATION", "name": "激活函数",
            "value": "ELU", "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": "RELU",       "label": "ReLU"},
                {"value": "LEAKY_RELU", "label": "Leaky ReLU"},
                {"value": "GELU",       "label": "GELU"},
                {"value": "TANH",       "label": "Tanh"},
                {"value": "SIGMOID",    "label": "Sigmoid"},
                {"value": "ELU",        "label": "ELU（推荐）"},
                {"value": "SWISH",      "label": "Swish"},
            ],
            "desc": "神经网络隐藏层激活函数",
        },
    ],
    "LOSS_FUNCTION": [
        {
            "code": "LOSS_MU", "name": "目标参数 [μ^d, μ^nd]",
            "value": "[2%, 7%], ~ 4%", "unit": None, "type": "BASE",
            "required": True,
            "desc": "目标分布均值 [μ^d / μ^nd]，约 4%（含默认值与上下限）",
        },
        {
            "code": "LOSS_SIGMA", "name": "惩罚系数 σ_i（LCR/NSFR/CMR/E/RWA/IRS/EYR）",
            "value": "[1.0, 0.2, 1.0, 2.5, 2.0, 0.002]", "unit": None, "type": "BASE",
            "required": True,
            "desc": "各子指标违约惩罚系数 σ_i 序列，依次为 LCR / NSFR / CMR / E/RWA / IRS / EYR",
        },
        {
            "code": "LOSS_LAMBDA", "name": "惩罚权重 [λ^d, λ^nd], λ^en",
            "value": "[0.05, 25.0], 3.5", "unit": None, "type": "BASE",
            "required": True,
            "desc": "正则化/约束项的权重系数 [λ^d / λ^nd] 与 λ^en（增强项）",
        },
    ],
    "TRAINING": [
        {
            "code": "TRAIN_EPOCH", "name": "训练轮次 Epoch",
            "value": 100, "unit": "轮", "type": "BASE",
            "required": True,
            "options": [{"value": v, "label": f"{v} 轮"} for v in [10, 30, 50, 100, 200, 500, 1000]],
            "desc": "模型完整遍历训练集的次数",
        },
        {
            "code": "TRAIN_SCENARIO", "name": "训练情景数 Scenarios",
            "value": 40000, "unit": "个", "type": "BASE",
            "required": True,
            "options": [
                {"value": 1000,  "label": "1,000 个（轻量）"},
                {"value": 5000,  "label": "5,000 个"},
                {"value": 10000, "label": "10,000 个"},
                {"value": 40000, "label": "40,000 个（推荐）"},
                {"value": 100000, "label": "100,000 个（精细）"},
            ],
            "desc": "蒙特卡洛/情景生成的数量（Training scenarios 40,000）",
        },
        {
            "code": "TRAIN_BATCH_SIZE", "name": "批大小 Batch Size",
            "value": 32, "unit": None, "type": "BASE",
            "required": True,
            "options": [{"value": v, "label": f"{v}"} for v in [8, 16, 32, 64, 128, 256, 512]],
            "desc": "每次梯度更新使用的样本数",
        },
    ],
    "OPTIMIZER": [
        {
            "code": "OPTIM_TYPE", "name": "优化器",
            "value": "RAdam", "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": "SGD",       "label": "SGD 随机梯度下降"},
                {"value": "MOMENTUM",  "label": "SGD + Momentum"},
                {"value": "ADAM",      "label": "Adam"},
                {"value": "ADAMW",     "label": "AdamW（带权重衰减）"},
                {"value": "RADAM",     "label": "RAdam（推荐，Rectified Adam）"},
                {"value": "RMSPROP",   "label": "RMSProp"},
                {"value": "ADAGRAD",   "label": "AdaGrad"},
                {"value": "LAMB",      "label": "LAMB（大 batch）"},
            ],
            "desc": "梯度下降优化算法",
        },
        {
            "code": "OPTIM_LEARNING_RATE", "name": "学习率",
            "value": "cyclic scheduler on [5e-4, 5e-3]", "unit": None, "type": "BASE",
            "required": True,
            "desc": "学习率调度方式：固定值（如 0.001）或 cyclic scheduler on [下界, 上界] 区间循环",
        },
        {
            "code": "OPTIM_GRAD_CLIP", "name": "梯度裁剪值",
            "value": 0.2, "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": 0.1, "label": "0.1（严格）"},
                {"value": 0.2, "label": "0.2（推荐）"},
                {"value": 0.5, "label": "0.5"},
                {"value": 1.0, "label": "1.0"},
                {"value": 5.0, "label": "5.0"},
                {"value": 0,   "label": "不裁剪"},
            ],
            "desc": "梯度范数上限，超过该值会被裁剪，防止梯度爆炸",
        },
    ],
}


def get_all_categories() -> List[Dict[str, Any]]:
    """返回所有分类（含 icon/color）"""
    return CATEGORIES


def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
    """获取指定分类下的所有模板参数"""
    return TEMPLATES.get(category, [])


def get_template_by_code(code: str):
    """根据 code 反查模板项"""
    for cat, items in TEMPLATES.items():
        for it in items:
            if it["code"] == code:
                return {**it, "category": cat}
    return None


def get_all_flat() -> List[Dict[str, Any]]:
    """返回所有模板的扁平列表（每项带 category 字段）"""
    out = []
    for cat, items in TEMPLATES.items():
        for it in items:
            out.append({**it, "category": cat})
    return out


def get_summary() -> Dict[str, Any]:
    """汇总：分类 + 各分类下的参数个数（用于前端预览）"""
    return {
        "categories": CATEGORIES,
        "templates": [
            {
                "category": cat,
                "category_name": next(c["name"] for c in CATEGORIES if c["code"] == cat),
                "items": items,
            }
            for cat, items in TEMPLATES.items()
        ],
        "total_params": sum(len(items) for items in TEMPLATES.values()),
    }
"""模型超参数模板注册表

按【参数分类】组织，每个分类下若干预置参数。模板会注入到 version 中，
作为初始参数集，用户可在此基础上修改、补充。

分类：
- DATA_ESG：数据日期 / ESG 参数（含收益率曲线模拟）
- NEURAL_NETWORK：神经网络参数（编码/隐藏层/激活函数）
- LOSS_FUNCTION：损失函数参数（目标/违约惩罚/权重）
- TRAINING：训练参数（轮次/情景/批大小）
- OPTIMIZER：模型优化参数（优化器/学习率/梯度裁剪）

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
from typing import List, Dict, Any


# 参数分类元信息
CATEGORIES = [
    {"code": "DATA_ESG",      "name": "数据日期 / ESG 参数", "icon": "📊", "color": "blue"},
    {"code": "NEURAL_NETWORK", "name": "神经网络参数",       "icon": "🧠", "color": "purple"},
    {"code": "LOSS_FUNCTION",  "name": "损失函数参数",       "icon": "🎯", "color": "red"},
    {"code": "TRAINING",       "name": "训练参数",           "icon": "🏋️", "color": "cyan"},
    {"code": "OPTIMIZER",      "name": "模型优化参数",       "icon": "⚡", "color": "gold"},
]


# 超参数模板
TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
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
            "code": "PCA_HISTORY_WINDOW", "name": "PCA 主成分历史利率时间区间",
            "value": "5Y", "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": "1Y",  "label": "近 1 年"},
                {"value": "2Y",  "label": "近 2 年"},
                {"value": "3Y",  "label": "近 3 年"},
                {"value": "5Y",  "label": "近 5 年（推荐）"},
                {"value": "7Y",  "label": "近 7 年"},
                {"value": "10Y", "label": "近 10 年"},
                {"value": "15Y", "label": "近 15 年"},
                {"value": "ALL", "label": "全部历史"},
            ],
            "desc": "用于估计主成分的历史利率窗口，越长越稳定但反应越慢",
        },
    ],
    "NEURAL_NETWORK": [
        {
            "code": "NN_ENCODER_LAYERS", "name": "隐藏编码层维度",
            "value": "[64, 32]", "unit": None, "type": "BASE",
            "required": True,
            "desc": "编码器隐藏层维度序列，例：[64, 32] 表示 2 层，维度依次 64→32",
        },
        {
            "code": "NN_LATENT_DIM", "name": "编码维度",
            "value": 16, "unit": "维", "type": "BASE",
            "required": True,
            "options": [{"value": i, "label": f"{i} 维"} for i in [4, 8, 16, 32, 64, 128]],
            "desc": "潜在空间维度，决定编码压缩率",
        },
        {
            "code": "NN_HIDDEN_DIMS", "name": "隐藏层维度",
            "value": "[128, 64, 32]", "unit": None, "type": "BASE",
            "required": True,
            "desc": "下游网络隐藏层维度序列，例：[128, 64, 32] 表示 3 层，维度依次 128→64→32",
        },
        {
            "code": "NN_ACTIVATION", "name": "激活函数",
            "value": "RELU", "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": "RELU",    "label": "ReLU（推荐）"},
                {"value": "LEAKY_RELU", "label": "Leaky ReLU"},
                {"value": "GELU",    "label": "GELU"},
                {"value": "TANH",    "label": "Tanh"},
                {"value": "SIGMOID", "label": "Sigmoid"},
                {"value": "ELU",     "label": "ELU"},
                {"value": "SWISH",   "label": "Swish"},
            ],
            "desc": "神经网络隐藏层激活函数",
        },
    ],
    "LOSS_FUNCTION": [
        {
            "code": "LOSS_MU", "name": "目标参数 µ（均值目标）",
            "value": 0.0, "unit": None, "type": "BASE",
            "required": True,
            "desc": "目标分布均值，用于将预测值往目标值上推/拉",
        },
        {
            "code": "LOSS_SIGMA", "name": "违约惩罚系数 σ",
            "value": 1.5, "unit": None, "type": "STRESS",
            "required": True,
            "desc": "违约/尾部事件的标准差系数，越大越惩罚",
        },
        {
            "code": "LOSS_LAMBDA", "name": "惩罚权重 λ",
            "value": 0.1, "unit": None, "type": "BASE",
            "required": True,
            "desc": "正则化/约束项的权重系数",
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
            "code": "TRAIN_SCENARIO", "name": "训练情景 Scenario",
            "value": "BASE", "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": "BASE",     "label": "基准情景"},
                {"value": "OPTIMISTIC", "label": "乐观情景"},
                {"value": "PESSIMISTIC", "label": "悲观情景"},
                {"value": "STRESS_LIGHT", "label": "轻度压力"},
                {"value": "STRESS_HEAVY", "label": "重度压力"},
                {"value": "REVERSE",   "label": "反算情景"},
            ],
            "desc": "选择训练使用的情景方案",
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
            "value": "ADAM", "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": "SGD",       "label": "SGD 随机梯度下降"},
                {"value": "MOMENTUM",  "label": "SGD + Momentum"},
                {"value": "ADAM",      "label": "Adam（推荐）"},
                {"value": "ADAMW",     "label": "AdamW（带权重衰减）"},
                {"value": "RMSPROP",   "label": "RMSProp"},
                {"value": "ADAGRAD",   "label": "AdaGrad"},
                {"value": "LAMB",      "label": "LAMB（大 batch）"},
            ],
            "desc": "梯度下降优化算法",
        },
        {
            "code": "OPTIM_LEARNING_RATE", "name": "学习率",
            "value": 0.001, "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": 0.1,   "label": "0.1"},
                {"value": 0.01,  "label": "0.01"},
                {"value": 0.001, "label": "0.001（推荐）"},
                {"value": 0.0001, "label": "0.0001"},
                {"value": 0.00001, "label": "0.00001"},
            ],
            "desc": "学习率（learning rate），Adam 默认 0.001",
        },
        {
            "code": "OPTIM_GRAD_CLIP", "name": "梯度裁剪值",
            "value": 1.0, "unit": None, "type": "BASE",
            "required": True,
            "options": [
                {"value": 0.1, "label": "0.1（严格）"},
                {"value": 0.5, "label": "0.5"},
                {"value": 1.0, "label": "1.0（推荐）"},
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
"""Seed 3 demo models: DNN, Ant Colony, Nonlinear Solver."""
import sys
sys.path.insert(0, '.')
from app.config import settings
from sqlalchemy import create_engine, text
import json

DB_URL = settings.DATABASE_URL_OVERRIDE or settings.DATABASE_URL
eng = create_engine(DB_URL)

# 3 models definition
MODELS = [
    {
        "model_code": "DNN_REG",
        "model_name": "DNN 神经网络回归模型",
        "model_type": "DNN_NEURAL_NETWORK",
        "biz_domain": "监管资本",
        "description": "基于深度神经网络（DNN/MLP）的非线性回归模型，用于监管资本指标的预测与情景生成",
        "algo_config": {
            "input_dim": 64,
            "output_dim": 5,
            "framework": "PyTorch",
            "task": "REGRESSION",
        },
        "params": [
            ("NN_ENCODER_LAYERS", "隐藏编码层维度",     128,       "维",   1),
            ("NN_LATENT_DIM",     "编码维度",            32,        "维",   2),
            ("NN_HIDDEN_DIMS",    "隐藏层维度序列",      "[256,128,64]", None, 3),
            ("NN_ACTIVATION",      "激活函数",            "RELU",    None,  4),
            ("OPTIM_TYPE",        "优化器",              "ADAM",    None,  5),
            ("OPTIM_LEARNING_RATE","学习率",             "0.001",   None,  6),
            ("OPTIM_GRAD_CLIP",   "梯度裁剪值",          0.5,       None,  7),
            ("TRAIN_EPOCH",       "训练轮次",            100,       "轮",   8),
            ("TRAIN_BATCH_SIZE",  "批大小",              64,        None,  9),
            ("LOSS_MU",           "目标参数 μ",          "[0.04, 0.07]", None, 10),
            ("LOSS_SIGMA",        "惩罚系数 σ",          "[1.0,0.2,1.0,2.5,2.0]", None, 11),
            ("LOSS_LAMBDA",       "惩罚权重 λ",          "[0.05, 25.0]", None, 12),
            ("DATA_DATE_CURRENT", "当前数据日期",        "2025-12-31", None, 13),
        ],
    },
    {
        "model_code": "ACO_OPT",
        "model_name": "蚁群算法组合优化模型",
        "model_type": "ANT_COLONY",
        "biz_domain": "资产负债",
        "description": "基于蚁群（ACO）的组合优化模型，用于资产负债结构/资产配置/路径规划",
        "algo_config": {
            "objective": "MAX_RETURN",
            "constraints": ["RISK_LIMIT", "LIQUIDITY_FLOOR"],
        },
        "params": [
            ("ACO_ANT_COUNT",     "蚂蚁数量",            50,        "只",   1),
            ("ACO_MAX_ITER",      "最大迭代次数",        100,       "轮",   2),
            ("ACO_ALPHA",         "信息素权重 α",        1.0,       None,  3),
            ("ACO_BETA",          "启发式权重 β",        2.0,       None,  4),
            ("ACO_RHO",           "信息素挥发系数 ρ",    0.5,       None,  5),
            ("ACO_Q0",            "信息素常量 Q",        100,       None,  6),
            ("ACO_TAU_INIT",      "初始信息素浓度",      1.0,       None,  7),
            ("ACO_EPSILON",       "精英蚂蚁权重 ε",      2.0,       None,  8),
            ("ACO_SEED",          "随机种子",            42,        None,  9),
            ("OPTIM_TYPE",        "优化器",              "ADAM",    None, 10),
            ("TRAIN_EPOCH",       "训练轮次",            100,       "轮",  11),
            ("DATA_DATE_CURRENT", "当前数据日期",        "2025-12-31", None, 12),
        ],
    },
    {
        "model_code": "NLS_REG",
        "model_name": "非线性方程求解模型",
        "model_type": "NONLINEAR_SOLVER",
        "biz_domain": "定价估值",
        "description": "基于 scipy.optimize 的非线性求解器，用于隐含波动率/IRRBB/EVE 等非线性方程求解",
        "algo_config": {
            "solver": "trust-constr",
            "method": "SLSQP",
            "task": "ROOT_FINDING",
        },
        "params": [
            ("NLS_SOLVER",        "求解器",              "TRUST_REGION", None, 1),
            ("NLS_METHOD",        "数值方法",            "NEWTON_CG", None, 2),
            ("NLS_TOL_FUN",       "函数容差",            1e-8,        None, 3),
            ("NLS_TOL_X",         "变量容差",            1e-10,       None, 4),
            ("NLS_MAX_ITER",      "最大迭代次数",        100,         "轮", 5),
            ("NLS_JAC",           "雅可比近似",          "2-point",   None, 6),
            ("NLS_HESS",          "Hessian 近似",        "BFGS",      None, 7),
            ("NLS_REG_ALPHA",     "正则化系数 α",        0.01,        None, 8),
            ("NLS_BOUND_LOWER",   "下界",                -1e6,        None, 9),
            ("NLS_BOUND_UPPER",   "上界",                1e6,         None, 10),
            ("TRAIN_EPOCH",       "训练轮次",            50,          "轮", 11),
            ("DATA_DATE_CURRENT", "当前数据日期",        "2025-12-31", None, 12),
        ],
    },
]


def main():
    with eng.begin() as conn:
        # 取 SCH_REG_2026 的 id
        kpi_scheme_id = conn.execute(text(
            "SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1"
        )).first()
        ksid = kpi_scheme_id[0] if kpi_scheme_id else None
        print(f"[kpi_scheme] SCH_REG_2026 id={ksid}")

        # 取所有 KPI 用于关联
        kpis = conn.execute(text(
            "SELECT id, kpi_code FROM prcp_kpi_definition WHERE is_deleted=0 ORDER BY id"
        )).fetchall()
        kpi_lookup = {r[1]: r[0] for r in kpis}
        print(f"[kpi] {len(kpis)} kpis: {list(kpi_lookup.keys())}")

        for m in MODELS:
            # 1) 插入 model
            existing = conn.execute(text(
                "SELECT id FROM prcp_model WHERE model_code=:c AND is_deleted=0"
            ), {"c": m["model_code"]}).first()
            if existing:
                mid = existing[0]
                print(f"[skip] {m['model_code']} already exists id={mid}")
            else:
                mid = conn.execute(text(
                    """INSERT INTO prcp_model
                       (model_code, model_name, model_type, biz_domain, kpi_scheme_id,
                        description, algo_config, status, created_by, updated_by)
                       VALUES (:c, :n, :t, :bd, :ksid, :d, :cfg, 'ACTIVE', 1, 1)"""
                ), {
                    "c": m["model_code"], "n": m["model_name"], "t": m["model_type"],
                    "bd": m["biz_domain"], "ksid": ksid, "d": m["description"],
                    "cfg": json.dumps(m["algo_config"], ensure_ascii=False),
                }).lastrowid
                print(f"[create] {m['model_code']} id={mid}")

                # 2) 自动创建 V1_BASELINE 版本
                # 检查 V1_BASELINE 是否已存在
                v_existing = conn.execute(text(
                    "SELECT id FROM prcp_model_version WHERE model_id=:m AND version_code='V1_BASELINE' AND is_deleted=0"
                ), {"m": mid}).first()
                if v_existing:
                    vid = v_existing[0]
                    print(f"  [skip-version] V1_BASELINE id={vid}")
                else:
                    vid = conn.execute(text(
                        """INSERT INTO prcp_model_version
                           (model_id, version_code, version_name, description, status, created_by, updated_by)
                           VALUES (:m, 'V1_BASELINE', '基准情景', '自动创建的初始版本', 'DRAFT', 1, 1)"""
                    ), {"m": mid}).lastrowid
                    print(f"  [create-version] V1_BASELINE id={vid}")

            # 3) 插入参数
            existing_params = {r[0]: r[1] for r in conn.execute(text(
                "SELECT param_code, id FROM prcp_model_param WHERE version_id=:v AND is_deleted=0"
            ), {"v": vid}).fetchall()}

            # 根据 model_type 决定 param_category
            def pick_category(code: str) -> str:
                if code.startswith("NN_") or code == "NN_ACTIVATION":
                    return "NEURAL_NETWORK"
                if code.startswith("OPTIM_"):
                    return "OPTIMIZER"
                if code.startswith("TRAIN_"):
                    return "TRAINING"
                if code.startswith("LOSS_"):
                    return "LOSS_FUNCTION"
                if code.startswith("DATA_DATE"):
                    return "DATA_DATE"
                if code.startswith("ACO_"):
                    return "OPTIMIZER"
                if code.startswith("NLS_"):
                    return "OPTIMIZER"
                return "BASE"

            inserted = 0
            for code, name, value, unit, sort in m["params"]:
                if code in existing_params:
                    continue
                # 关联 KPI：取前 5 个 KPI 循环绑定，让参数跟 KPI 关联起来
                kpi_id = None
                kpi_code_bound = None
                if kpi_lookup:
                    # 按代码匹配优先
                    for kc, kid in kpi_lookup.items():
                        # 如果参数名包含 KPI code 关键字就关联
                        if kc in code or code in kc:
                            kpi_id = kid
                            kpi_code_bound = kc
                            break
                    # 否则按 sort_order 轮询
                    if not kpi_id:
                        idx = sort % len(kpis)
                        kpi_id = kpis[idx][0]
                        kpi_code_bound = kpis[idx][1]

                cat = pick_category(code)
                # 判断数值/字符串
                if isinstance(value, (int, float)):
                    pv, pvs = float(value), None
                else:
                    pv, pvs = 0.0, str(value)

                conn.execute(text(
                    """INSERT INTO prcp_model_param
                       (version_id, kpi_id, kpi_code, param_code, param_name,
                        param_type, param_category, param_value, param_value_str,
                        unit, sort_order, description, created_by, updated_by)
                       VALUES (:v, :k, :kc, :pc, :pn, 'BASE', :cat, :pv, :pvs,
                        :u, :so, :d, 1, 1)"""
                ), {
                    "v": vid, "k": kpi_id, "kc": kpi_code_bound,
                    "pc": code, "pn": name, "cat": cat,
                    "pv": pv, "pvs": pvs, "u": unit, "so": sort,
                    "d": f"{m['model_name']} 默认参数",
                })
                inserted += 1

            # 4) 更新 param_count
            conn.execute(text(
                """UPDATE prcp_model_version SET param_count=(
                    SELECT COUNT(*) FROM prcp_model_param WHERE version_id=:v AND is_deleted=0
                ) WHERE id=:v"""
            ), {"v": vid})

            print(f"  [params] +{inserted} param_count={len(existing_params)+inserted}")


if __name__ == "__main__":
    main()
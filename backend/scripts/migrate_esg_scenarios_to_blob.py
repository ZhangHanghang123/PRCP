"""迁移 v1 旧 .npz 数据 → v2 (blob + 9 JSON 统计)

读取 prcp_esg_scenario 中所有 paths_blob 为空的记录，
加载 file_path 指向的 .npz 文件，把字节流 + 9 个派生统计写回数据库。

用法：
    cd /home/almd/prcp/backend && ./venv/bin/python scripts/migrate_esg_scenarios_to_blob.py
"""
import os
import sys
import json
import numpy as np
from sqlalchemy import create_engine, text

# 数据库连接
DB_URL = "mysql+pymysql://almd:Almd%402026@127.0.0.1:3306/prcp_db?charset=utf8mb4"
engine = create_engine(DB_URL, pool_pre_ping=True)

DATA_DIR = "/var/lib/prcp/esg_cases"


def load_npz_to_db(npz_path: str, scenario_row: dict) -> dict:
    """加载 .npz，生成派生统计，返回 update 参数字典"""
    print(f"  loading {npz_path}")
    with np.load(npz_path, allow_pickle=False) as f:
        paths = f["paths"]
        n_scenarios = int(f["n_scenarios"])
        n_steps = int(f["n_steps"])
        n_maturities = int(f["n_maturities"])

    # 读 .npz 完整字节流
    with open(npz_path, "rb") as f:
        paths_blob = f.read()

    # 派生统计（复用 ScenarioSet 逻辑）
    p10 = np.percentile(paths, 10, axis=0).tolist()
    p50 = np.percentile(paths, 50, axis=0).tolist()
    p90 = np.percentile(paths, 90, axis=0).tolist()
    final = paths[:, -1, :]  # (n_scenarios, n_maturities)
    final_mean = final.mean(axis=0).tolist()
    final_std = final.std(axis=0).tolist()
    final_min = final.min(axis=0).tolist()
    final_max = final.max(axis=0).tolist()
    vol_per_maturity = final.std(axis=0).tolist()  # 与 final_std 等价
    n_zeros = int((paths == 0).sum())
    n_negatives = int((paths < 0).sum())

    return {
        "paths_blob": paths_blob,
        "p10_json": json.dumps(p10),
        "p50_json": json.dumps(p50),
        "p90_json": json.dumps(p90),
        "final_mean_json": json.dumps(final_mean),
        "final_std_json": json.dumps(final_std),
        "final_min_json": json.dumps(final_min),
        "final_max_json": json.dumps(final_max),
        "vol_per_maturity_json": json.dumps(vol_per_maturity),
        "n_zeros": n_zeros,
        "n_negatives": n_negatives,
        "id": scenario_row["id"],
    }


def main():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, scheme_id, scenario_code, file_path, n_scenarios, n_steps, n_maturities
            FROM prcp_esg_scenario
            WHERE is_deleted=0 AND (paths_blob IS NULL OR LENGTH(paths_blob) = 0)
            ORDER BY id
        """)).fetchall()

        if not rows:
            print("✓ 没有需要迁移的场景（全部已有 blob）")
            return

        print(f"找到 {len(rows)} 个待迁移的场景：")
        ok, fail, skip = 0, 0, 0
        for row in rows:
            scenario_id = row[2] or f"id={row[0]}"
            file_path = row[3]
            if not file_path or not os.path.exists(file_path):
                print(f"  ✗ [{scenario_id}] 文件不存在: {file_path}（跳过）")
                skip += 1
                continue
            try:
                params = load_npz_to_db(file_path, {"id": row[0]})
                conn.execute(text("""
                    UPDATE prcp_esg_scenario
                    SET paths_blob=:paths_blob,
                        p10_json=:p10_json, p50_json=:p50_json, p90_json=:p90_json,
                        final_mean_json=:final_mean_json, final_std_json=:final_std_json,
                        final_min_json=:final_min_json, final_max_json=:final_max_json,
                        vol_per_maturity_json=:vol_per_maturity_json,
                        n_zeros=:n_zeros, n_negatives=:n_negatives
                    WHERE id=:id
                """), params)
                blob_kb = len(params["paths_blob"]) / 1024
                print(f"  ✓ [{scenario_id}] {row[4]}×{row[5]}×{row[6]} blob={blob_kb:.1f}KB")
                ok += 1
            except Exception as e:
                print(f"  ✗ [{scenario_id}] 迁移失败: {type(e).__name__}: {e}")
                fail += 1

        print()
        print(f"=== 迁移结果: ok={ok} skip={skip} fail={fail} ===")

        # 验证
        n_total = conn.execute(text("SELECT COUNT(*) FROM prcp_esg_scenario WHERE is_deleted=0")).scalar()
        n_with_blob = conn.execute(text("SELECT COUNT(*) FROM prcp_esg_scenario WHERE is_deleted=0 AND paths_blob IS NOT NULL AND LENGTH(paths_blob) > 0")).scalar()
        n_with_stats = conn.execute(text("SELECT COUNT(*) FROM prcp_esg_scenario WHERE is_deleted=0 AND p50_json IS NOT NULL")).scalar()
        print(f"验证：{n_with_blob}/{n_total} 有 blob, {n_with_stats}/{n_total} 有派生统计")


if __name__ == "__main__":
    main()

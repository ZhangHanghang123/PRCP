"""PRCP ESG · Svensson 曲线种子数据导入

从 DeepALM backend/scripts/seed_data/ 的 4 份 svensson_*.csv 读取
（theta/lambda 命名与 PRCP 数据库字段一致），批量 upsert 到 prcp_esg_curve_point。

支持 4 类数据源：
    - svensson_ecb_real.csv → source='ECB'  (575 行)
    - svensson_frb_demo.csv  → source='FRB'  (13 行)
    - svensson_custom_demo.csv → source='CUSTOM' (12 行)
    - svensson_bank_demo.csv → source='BANK' (12 行)

用法：
    在服务器 venv 下：
        cd /home/almd/prcp/backend
        ./venv/bin/python scripts/seed_esg_curve_data.py
        # 或指定 CSV 目录：
        ./venv/bin/python scripts/seed_esg_curve_data.py --csv-dir /tmp/svensson/
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ===================== 配置 =====================

DEFAULT_CSV_DIR = "/home/almd/prcp/backend/scripts/seed_data"
DEFAULT_DB_URL = "mysql+pymysql://almd:Almd%402026@127.0.0.1:3306/prcp_db?charset=utf8mb4"

SOURCE_FILES = [
    ("svensson_ecb_real.csv", "ECB"),
    ("svensson_frb_demo.csv", "FRB"),
    ("svensson_custom_demo.csv", "CUSTOM"),
    ("svensson_bank_demo.csv", "BANK"),
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", default=DEFAULT_CSV_DIR, help="CSV 文件目录")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="MySQL 连接 URL")
    parser.add_argument("--dry-run", action="store_true", help="只读不写")
    return parser.parse_args()


def parse_csv_row(row: dict, source: str) -> Optional[dict]:
    """将一行 CSV 转成 prcp_esg_curve_point 插入 dict"""
    try:
        return {
            "curve_date": row["date"],
            "source": source,
            "theta0": float(row["theta0"]),
            "theta1": float(row["theta1"]),
            "theta2": float(row["theta2"]),
            "theta3": float(row["theta3"]),
            "lambda1": float(row["lambda1"]),
            "lambda2": float(row["lambda2"]),
            "raw_data_json": row.get("raw_data_json"),
            "description": f"{source} 历史数据种子导入",
        }
    except (KeyError, ValueError) as e:
        print(f"  [WARN] 跳过一行：{e}: {row}", file=sys.stderr)
        return None


def upsert_curve(db, point: dict, uid: int = 1):
    """upsert 到 prcp_esg_curve_point"""
    raw_json = point["raw_data_json"]
    raw_dict = None
    if raw_json:
        try:
            raw_dict = json.loads(raw_json)
        except Exception:
            pass
    db.execute(text("""
        INSERT INTO prcp_esg_curve_point
        (curve_date, source, theta0, theta1, theta2, theta3, lambda1, lambda2,
         raw_data_json, description, created_by, updated_by)
        VALUES (:d, :s, :t0, :t1, :t2, :t3, :l1, :l2, :raw, :desc, :u, :u)
        ON DUPLICATE KEY UPDATE
          theta0=VALUES(theta0), theta1=VALUES(theta1), theta2=VALUES(theta2), theta3=VALUES(theta3),
          lambda1=VALUES(lambda1), lambda2=VALUES(lambda2),
          raw_data_json=VALUES(raw_data_json), description=VALUES(description), updated_by=VALUES(updated_by)
    """), {
        "d": point["curve_date"], "s": point["source"],
        "t0": point["theta0"], "t1": point["theta1"], "t2": point["theta2"], "t3": point["theta3"],
        "l1": point["lambda1"], "l2": point["lambda2"],
        "raw": json.dumps(raw_dict, ensure_ascii=False) if raw_dict else None,
        "desc": point["description"], "u": uid,
    })


def main():
    args = parse_args()
    csv_dir = Path(args.csv_dir)
    if not csv_dir.exists():
        print(f"[ERROR] CSV 目录不存在: {csv_dir}")
        sys.exit(1)

    # 数据库连接
    engine = create_engine(args.db_url, echo=False, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    try:
        # 检查表是否存在
        exists = db.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema=DATABASE() AND table_name='prcp_esg_curve_point'
        """)).scalar()
        if not exists:
            print(f"[ERROR] prcp_esg_curve_point 表不存在，请先跑 upgrade_esg_v1.sql")
            sys.exit(2)

        for filename, source in SOURCE_FILES:
            csv_path = csv_dir / filename
            if not csv_path.exists():
                print(f"  [SKIP] {filename} 不存在")
                continue

            n_ok = 0
            n_err = 0
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    point = parse_csv_row(row, source)
                    if point is None:
                        n_err += 1
                        continue
                    if not args.dry_run:
                        try:
                            upsert_curve(db, point)
                            n_ok += 1
                        except Exception as e:
                            print(f"  [WARN] upsert 失败: {e}", file=sys.stderr)
                            n_err += 1
                    else:
                        n_ok += 1

            print(f"  ✓ {source:8s} {filename:35s} OK={n_ok:>4} ERR={n_err}")
            total_inserted += n_ok
            total_skipped += n_err

        if not args.dry_run:
            db.commit()

        # 统计
        rows_after = db.execute(text("""
            SELECT source, COUNT(*) FROM prcp_esg_curve_point
            WHERE is_deleted=0 GROUP BY source
        """)).fetchall()
        print(f"\n数据库现状：")
        for r in rows_after:
            print(f"  {r[0]:8s} {int(r[1]):>4} 行")
        print(f"\n总计: 成功 {total_inserted}, 跳过 {total_skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
"""seed_all.py - 一键执行 2026 初始化脚本 (00 + 01 + 02 + 03)
使用方法:
    cd backend/scripts/2026_init
    python seed_all.py                    # 默认按顺序执行
    python seed_all.py --dry-run          # 仅打印 SQL, 不执行
    python seed_all.py --only 00 01       # 只执行前 2 个
"""
import os
import sys
import time
import argparse
from pathlib import Path

# 项目根路径 (假设脚本在 backend/scripts/2026_init/)
SCRIPT_DIR = Path(__file__).parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent

# 让 Python 能 import app.config
sys.path.insert(0, str(BACKEND_ROOT))


def get_db_url() -> str:
    """获取数据库连接 URL"""
    try:
        from app.config import settings
        return settings.DATABASE_URL_OVERRIDE or settings.DATABASE_URL
    except Exception as e:
        print(f"⚠️ 无法读取 app.config: {e}")
        # 兜底: 直接用环境变量
        import os
        url = os.getenv("DATABASE_URL", "mysql+pymysql://prcp:Prcp@2026@127.0.0.1:3306/prcp_db?charset=utf8mb4")
        print(f"   使用环境变量: {url.split('@')[-1] if '@' in url else url}")
        return url


def run_sql_file(engine, sql_path: Path, dry_run: bool = False):
    """执行单个 SQL 文件, 用 -- 多行兼容性; 不支持 .py 文件"""
    from sqlalchemy import text

    if not sql_path.exists():
        print(f"  ❌ 文件不存在: {sql_path}")
        return False

    sql_content = sql_path.read_text(encoding='utf-8')

    # 切分 SQL 语句 (按 ; 分号, 但保留 -- 注释行)
    statements = []
    current = []
    for line in sql_content.split('\n'):
        line_stripped = line.strip()
        if line_stripped.startswith('--') or not line_stripped:
            current.append(line)
            continue
        current.append(line)
        if line_stripped.endswith(';'):
            stmt = '\n'.join(current).strip().rstrip(';').strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
            current = []

    if dry_run:
        print(f"\n  📄 {sql_path.name} ({len(statements)} 条 SQL)")
        for i, stmt in enumerate(statements[:3], 1):
            preview = stmt.replace('\n', ' ')[:120]
            print(f"    [{i}] {preview}...")
        if len(statements) > 3:
            print(f"    ... 还有 {len(statements) - 3} 条")
        return True

    print(f"\n  📄 {sql_path.name} ({len(statements)} 条 SQL)")
    start = time.time()
    success = 0
    fail = 0
    with engine.begin() as conn:
        for i, stmt in enumerate(statements, 1):
            try:
                conn.execute(text(stmt))
                success += 1
            except Exception as e:
                # 忽略 IF EXISTS / 已存在 等幂等错误
                err_msg = str(e).lower()
                if 'duplicate' in err_msg or 'already exists' in err_msg or '1062' in err_msg:
                    success += 1
                else:
                    fail += 1
                    print(f"    ❌ [{i}] {str(e)[:200]}")

    print(f"    ✓ {success} 条成功, ✗ {fail} 条失败, 耗时 {time.time()-start:.2f}s")
    return fail == 0


def verify_data(engine):
    """验证数据库初始化结果"""
    from sqlalchemy import text
    print("\n" + "=" * 60)
    print("📊 验证数据 (各表行数)")
    print("=" * 60)

    checks = [
        ("指标方案", "SELECT COUNT(*) FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0"),
        ("KPI 定义", "SELECT COUNT(*) FROM prcp_kpi_definition k JOIN prcp_kpi_scheme s ON k.scheme_id=s.id WHERE s.scheme_code='SCH_REG_2026' AND k.is_deleted=0"),
        ("评分规则", "SELECT COUNT(*) FROM prcp_kpi_score_rule r JOIN prcp_kpi_definition k ON r.kpi_id=k.id JOIN prcp_kpi_scheme s ON r.scheme_id=s.id WHERE s.scheme_code='SCH_REG_2026' AND r.is_deleted=0"),
        ("评分段位", "SELECT COUNT(*) FROM prcp_kpi_score_segment seg JOIN prcp_kpi_score_rule r ON seg.rule_id=r.id WHERE r.is_deleted=0 AND seg.is_deleted=0"),
        ("模型总数", "SELECT COUNT(*) FROM prcp_model WHERE model_code IN ('DNN_REG','ACO_OPT','NLS_REG') AND is_deleted=0"),
        ("模型版本", "SELECT COUNT(*) FROM prcp_model_version v JOIN prcp_model m ON v.model_id=m.id WHERE m.model_code IN ('DNN_REG','ACO_OPT','NLS_REG') AND v.is_deleted=0"),
        ("参数明细", "SELECT COUNT(*) FROM prcp_model_param p JOIN prcp_model_version v ON p.version_id=v.id JOIN prcp_model m ON v.model_id=m.id WHERE m.model_code IN ('DNN_REG','ACO_OPT','NLS_REG') AND p.is_deleted=0"),
        ("账户册方案", "SELECT COUNT(*) FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0"),
        ("账户册节点", "SELECT COUNT(*) FROM prcp_coa_node WHERE scheme_id=(SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0) AND is_deleted=0"),
        ("测算方案", "SELECT COUNT(*) FROM prcp_sim_scheme WHERE scheme_code='SCS_2026' AND is_deleted=0"),
        ("测算节点", "SELECT COUNT(*) FROM prcp_sim_scheme_node WHERE scheme_id=(SELECT id FROM prcp_sim_scheme WHERE scheme_code='SCS_2026' AND is_deleted=0) AND is_deleted=0"),
        ("铺底系数", "SELECT COUNT(*) FROM prcp_metric_coefficient WHERE scheme_code='ZX_COA' AND is_deleted=0"),
    ]

    with engine.connect() as conn:
        for name, sql in checks:
            try:
                n = conn.execute(text(sql)).scalar()
                print(f"  ✓ {name:<10} : {n:>4} 行")
            except Exception as e:
                print(f"  ❌ {name:<10} : 错误 {str(e)[:80]}")


def main():
    parser = argparse.ArgumentParser(description='PRCP 2026 一键初始化')
    parser.add_argument('--dry-run', action='store_true', help='仅打印 SQL 不执行')
    parser.add_argument('--only', nargs='+', help='只执行指定文件, 如 --only 00 01')
    parser.add_argument('--skip-verify', action='store_true', help='跳过验证')
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 PRCP 2026 一键初始化脚本")
    print("=" * 60)

    # 获取 DB URL
    db_url = get_db_url()
    print(f"\n📌 数据库: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print(f"📌 模式: {'DRY-RUN' if args.dry_run else '执行'}")

    # 选文件
    files = sorted(SCRIPT_DIR.glob('0*.sql'))
    if args.only:
        selected = []
        for f in files:
            if any(f.name.startswith(f'0{idx}') for idx in args.only):
                selected.append(f)
        files = selected

    print(f"\n📋 待执行文件 ({len(files)}):")
    for f in files:
        print(f"   - {f.name}")

    # 创建 engine
    if not args.dry_run:
        try:
            from sqlalchemy import create_engine
            engine = create_engine(db_url, pool_pre_ping=True)
        except Exception as e:
            print(f"\n❌ 创建 engine 失败: {e}")
            return 1

    # 执行
    total_start = time.time()
    all_ok = True
    for f in files:
        ok = run_sql_file(engine if not args.dry_run else None, f, dry_run=args.dry_run)
        all_ok = all_ok and ok

    # 验证
    if not args.dry_run and not args.skip_verify:
        verify_data(engine)

    print(f"\n⏱️ 总耗时: {time.time()-total_start:.2f}s")
    print(f"{'✅ 全部成功' if all_ok else '⚠️ 有失败项'}")

    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
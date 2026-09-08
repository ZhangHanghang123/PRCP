"""指标项路由（6 类指标的树形 + 列表 + 导入）"""
import sys
from pathlib import Path

# 把 backend/ 加入 sys.path 以便 import config
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/metric-items", tags=["指标项"])

# 6 个分类的展示名 + 主题色
CATEGORIES = [
    {"code": "FINANCIAL", "name": "账务结果指标", "icon": "💰", "color": "#1677ff"},
    {"code": "PARAM",     "name": "关键参数指标", "icon": "🔧", "color": "#13c2c2"},
    {"code": "SCALE",     "name": "规模指标",     "icon": "📏", "color": "#722ed1"},
    {"code": "PRICE",     "name": "价格指标",     "icon": "💹", "color": "#fa8c16"},
    {"code": "FEE",       "name": "中收指标",     "icon": "🪙", "color": "#eb2f96"},
    {"code": "RWA",       "name": "资本与RWA假设", "icon": "🛡️", "color": "#f5222d"},
]


@router.get("/categories")
async def list_categories(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回 6 类指标的元数据 + 各分类当前条数"""
    items = []
    for c in CATEGORIES:
        row = db.execute(
            text("SELECT COUNT(*) FROM prcp_metric_item WHERE category=:c AND is_deleted=0"),
            {"c": c["code"]},
        ).scalar()
        items.append({**c, "count": int(row)})
    return {"items": items}


@router.get("")
async def list_items(
    category: str = Query(..., description="FINANCIAL/PARAM/SCALE/PRICE/FEE/RWA"),
    keyword: Optional[str] = Query(None, description="模糊搜索 name"),
    level: Optional[int] = Query(None, description="按层级过滤"),
    parent_code: Optional[str] = Query(None, description="按父编码过滤（直系子节点）"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """列表查询某分类下的指标项（扁平）"""
    where = ["is_deleted=0", "category=:cat"]
    params: dict = {"cat": category}
    if keyword:
        where.append("name LIKE :kw")
        params["kw"] = f"%{keyword}%"
    if level is not None:
        where.append("level=:lv")
        params["lv"] = level
    if parent_code is not None:
        if parent_code == "" or parent_code == "ROOT":
            where.append("(parent_code IS NULL OR parent_code='')")
        else:
            where.append("parent_code=:pc")
            params["pc"] = parent_code
    rows = db.execute(
        text(f"""
            SELECT id, category, code, name, level, parent_code, path,
                   is_leaf, sort_order
            FROM prcp_metric_item
            WHERE {' AND '.join(where)}
            ORDER BY category, path, sort_order
        """),
        params,
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "category": r[1], "code": r[2], "name": r[3],
                "level": r[4], "parent_code": r[5], "path": r[6],
                "is_leaf": bool(r[7]), "sort_order": r[8],
            }
            for r in rows
        ]
    }


@router.get("/tree")
async def tree(
    category: str = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回树形结构（带 children 数组，前端可直接渲染 Tree 组件）"""
    rows = db.execute(
        text("""
            SELECT id, code, name, level, parent_code, path, is_leaf
            FROM prcp_metric_item
            WHERE is_deleted=0 AND category=:c
            ORDER BY path
        """),
        {"c": category},
    ).fetchall()

    # 物化路径解析：path=/FINANCIAL/001/001001/001001001/
    # 直接用 (cat, code, name) 三元组作为节点 key（与导入时一致，避免 code 重复节点错位）
    nodes = {}
    for r in rows:
        key = (r[1], r[2], r[3])  # (code, name) — 加上 level 父节点判别
        nodes[key] = {
            "key": f"{r[1]}|{r[2]}",  # 用于前端 Tree 的 key（code+name 唯一）
            "title": r[2],
            "code": r[1],
            "level": r[3],
            "parent_code": r[4],
            "path": r[5],
            "is_leaf": bool(r[6]),
            "children": [],
        }

    # 组装树
    roots = []
    for key, node in nodes.items():
        code, name = node["code"], node["title"]
        level = node["level"]
        # 找父：同 cat 下 level-1 且 name 前缀
        parent = None
        if level > 1:
            for k2, n2 in nodes.items():
                if n2["level"] == level - 1 and code.startswith(n2["code"]):
                    # 启发式：level-1 的 code 应该是本 code 的前缀
                    parent = n2
                    break
        if parent is None:
            roots.append(node)
        else:
            parent["children"].append(node)

    return {"category": category, "items": roots, "total": len(nodes)}


@router.post("/import-from-xlsx")
async def import_from_xlsx(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """调用后端脚本重新从 docs/报表表项.xlsx 解析并清空 + 重导入
    注：仅 admin 角色可调用
    """
    # 角色校验
    role = user.role if hasattr(user, "role") else "user"
    if role != "admin":
        raise HTTPException(status_code=403, detail="仅 admin 可执行导入")

    import subprocess
    script = ROOT / "scripts" / "import_metric_items.py"
    if not script.exists():
        raise HTTPException(status_code=500, detail=f"脚本不存在: {script}")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, cwd=ROOT.parent,
            timeout=60,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"脚本执行失败: {result.stderr[:500]}")
        # 脚本生成 metric_items_seed.sql，重导入
        sql_file = ROOT.parent / "docs" / "metric_items_seed.sql"
        if not sql_file.exists():
            raise HTTPException(status_code=500, detail="未生成 seed SQL")

        # 用 pymysql 直连 prcp_db 执行（不用 sqlalchemy 引擎，简单粗暴）
        import pymysql
        conn = pymysql.connect(
            host=settings.MYSQL_HOST, port=int(settings.MYSQL_PORT),
            user=settings.MYSQL_USER, password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DB, charset="utf8mb4",
        )
        with conn.cursor() as c:
            sql_text = sql_file.read_text(encoding="utf-8")
            for stmt in [s.strip() for s in sql_text.split(";") if s.strip() and not s.strip().startswith("--")]:
                c.execute(stmt)
        conn.commit()
        # 统计导入后条数
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM prcp_metric_item WHERE is_deleted=0")
            total = c.fetchone()[0]
        conn.close()
        return {"success": True, "total": total, "message": f"已重新导入 {total} 条"}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="脚本执行超时")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)[:300]}")

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
    """返回树形结构（带 children 数组，前端可直接渲染 Tree 组件）
    用 (parent_code, name) 联合作为父节点 key，避免 (cat, code) 重复时错位
    """
    rows = db.execute(
        text("""
            SELECT id, code, name, level, parent_code, path, is_leaf
            FROM prcp_metric_item
            WHERE is_deleted=0 AND category=:c
            ORDER BY path
        """),
        {"c": category},
    ).fetchall()

    # 用 (parent_code, name) 联合作为索引建树
    # 同 cat 下 parent_code + name 唯一确定父节点（处理 (cat, code) 重复的边界）
    nodes_by_pn: dict = {}  # (parent_code, name) -> node
    for r in rows:
        key = (r[4] or "", r[2])
        nodes_by_pn[key] = {
            "key": f"{r[1]}|{r[2]}",
            "title": r[2],
            "code": r[1],
            "level": r[3],
            "parent_code": r[4],
            "path": r[5],
            "is_leaf": bool(r[6]),
            "children": [],
        }

    # 组装树：每个节点找其父（parent_code + parent 的 name）
    # 由于父节点的 name 不直接知道，我们用以下规则：
    #   - level=1 节点：parent_code 为空，视为根
    #   - level>1 节点：在 DB 中查 parent_code 对应的节点（可能多个，code 重复时按 sibling 关系选）
    # 实际实现：从 nodes_by_pn 反查 — 同 cat + parent_code = 当前节点的 parent_code 的所有节点，按 sort_order 取最近的"前一个"
    # 但我们没存 sort_order 在这里。简化：直接用 path 前缀匹配 — 父节点的 path 必是子节点 path 的前缀
    roots = []
    by_path: dict = {n["path"]: n for n in nodes_by_pn.values()}

    for n in nodes_by_pn.values():
        if n["level"] == 1 or not n["parent_code"]:
            roots.append(n)
            continue
        # 找父节点：path 是 n.path 前缀、且以 n.parent_code 结尾
        # 父节点 path 形如 ".../parent_code/"，本节点 path 形如 ".../parent_code/this_code/"
        parent_code = n["parent_code"]
        child_path = n["path"]
        # 去掉末尾 "/<this_code>/" → 父 path
        suffix = f"/{parent_code}/"
        if child_path.endswith(suffix):
            parent_path = child_path[: -len(f"{n['code']}/")]
        else:
            # fallback: 父 path 末段是 parent_code/
            parent_path = child_path.rsplit(f"/{n['code']}/", 1)[0] + "/"
        parent = by_path.get(parent_path)
        if parent:
            parent["children"].append(n)
        else:
            # 兜底：找不到父就当根
            roots.append(n)

    return {"category": category, "items": roots, "total": len(nodes_by_pn)}


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

"""PRCP 数据维护模块 V2 — 基于 prcp_rpt_item + prcp_rpt_value

6 类报表（账务结果/关键参数/规模/价格/中收/资本RWA）的按月数据维护

端点：
- GET    /data-maint/categories                 6 类报表汇总
- GET    /data-maint/items?category=&report_id= 按类别/报表查 rpt_item（含 coa_node_ids 取数逻辑）
- GET    /data-maint/values?item_id=&data_date= 查月度值
- POST   /data-maint/values                     upsert 月度值
- DELETE /data-maint/values/{vid}               删除月度值
- GET    /data-maint/calc-preview?item_id=&data_date= 预览按取数逻辑计算结果
- POST   /data-maint/monthly-calc               按月出指标：对所有 rpt_item（带 coa_node_ids 的）批量计算
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/data-maint", tags=["数据维护"])

CATEGORIES = [
    ("FINANCIAL", "1-账务结果指标"),
    ("PARAM",     "2-关键参数指标"),
    ("SCALE",     "3-规模指标"),
    ("PRICE",     "4-价格指标"),
    ("FEE",       "5-中收指标"),
    ("RWA",       "6-资本与RWA假设指标"),
]


@router.get("/categories")
async def list_categories(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """6 类报表汇总"""
    rows = db.execute(text("""
        SELECT (SELECT i.category FROM prcp_rpt_item i
                WHERE i.report_id=r.id AND i.is_deleted=0 AND i.item_level=1 LIMIT 1) AS cat,
               r.id, r.report_code, r.report_name, COUNT(i.id) AS item_count
        FROM prcp_rpt_report r
        LEFT JOIN prcp_rpt_item i ON i.report_id=r.id AND i.is_deleted=0
        WHERE r.is_deleted=0
        GROUP BY r.id, r.report_code, r.report_name
        ORDER BY r.id
    """)).fetchall()
    return {"items": [{
        "category": r[0], "report_id": r[1], "report_code": r[2],
        "report_name": r[3], "item_count": int(r[4] or 0),
    } for r in rows if r[0] in [c[0] for c in CATEGORIES]]}


@router.get("/items")
async def list_items(category: str = None, report_id: int = None,
                     db: Session = Depends(get_db), user=Depends(get_current_user)):
    """按 category 或 report 列出报表项（含层级 + coa_node_ids 取数逻辑）"""
    sql = """
        SELECT i.id, i.report_id, i.parent_id, i.item_code, i.item_name,
               i.item_level, i.category, i.coa_node_ids, i.formula, i.description,
               (SELECT COUNT(*) FROM prcp_rpt_item c WHERE c.parent_id=i.id AND c.is_deleted=0) AS child_count,
               r.report_name
        FROM prcp_rpt_item i
        LEFT JOIN prcp_rpt_report r ON r.id=i.report_id
        WHERE i.is_deleted=0
    """
    params = {}
    if report_id:
        sql += " AND i.report_id=:rid"
        params["rid"] = report_id
    elif category:
        sql += " AND i.category=:cat"
        params["cat"] = category.upper()
    sql += " ORDER BY i.item_level, i.item_code LIMIT 5000"
    rows = db.execute(text(sql), params).fetchall()
    return {"items": [{
        "id": r[0], "report_id": r[1], "parent_id": r[2],
        "item_code": r[3], "item_name": r[4], "item_level": r[5],
        "category": r[6],
        "coa_node_ids": json.loads(r[7]) if r[7] else [],
        "formula": r[8], "description": r[9],
        "child_count": int(r[10] or 0), "report_name": r[11],
    } for r in rows]}


@router.get("/items/tree-with-values")
async def items_tree_with_values(
    category: str = Query(...),
    data_date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回某 category 下所有报表项的树形结构 + 当前 data_date 的月度值 + 24 月缺口值（M1~M24）

    返回字段：
      - items: 树形结构（id/parent_id/item_code/item_name/item_level/coa_node_ids）
      - values_map: {item_id: {data_date: value, m1: v1, m2: v2, ... m24: v24}}
        父节点如果自己有值，children 也会按继承标记
    """
    # 1) 加载该 category 所有 items
    rows = db.execute(
        text("""
            SELECT i.id, i.parent_id, i.item_code, i.item_name, i.item_level,
                   i.coa_node_ids, i.formula, i.description
            FROM prcp_rpt_item i
            WHERE i.is_deleted=0 AND i.category=:cat
            ORDER BY i.item_level, i.item_code
        """),
        {"cat": category.upper()},
    ).fetchall()

    by_id = {}
    for r in rows:
        by_id[r[0]] = {
            "id": r[0], "parent_id": r[1],
            "item_code": r[2], "item_name": r[3], "item_level": r[4],
            "coa_node_ids": json.loads(r[5]) if r[5] else [],
            "formula": r[6], "description": r[7],
            "children": [],
        }

    roots = []
    for node in by_id.values():
        pid = node["parent_id"]
        if pid and pid in by_id:
            by_id[pid]["children"].append(node)
        else:
            roots.append(node)

    # 2) 加载这些 item 在 data_date 当月值 + 24 月缺口
    item_ids = list(by_id.keys())
    values_map: dict = {}
    if item_ids:
        placeholders = ",".join([f":i{i}" for i in range(len(item_ids))])
        params = {"dd": data_date}
        for i, iid in enumerate(item_ids):
            params[f"i{i}"] = iid
        # 该月单值
        single = db.execute(text(f"""
            SELECT item_id, value FROM prcp_rpt_value
            WHERE is_deleted=0 AND data_date=STR_TO_DATE(:dd, '%Y-%m-%d')
              AND item_id IN ({placeholders})
        """), params).fetchall()
        # 24 月缺口（M1~M24 = data_date 后 N 个月的预测）
        # 这里我们直接从 prcp_data_balance 的 m1_gap~m24_gap 取（如果该 item 关联了账户册）
        gap = db.execute(text(f"""
            SELECT item_id, data_date FROM prcp_rpt_value
            WHERE is_deleted=0 AND item_id IN ({placeholders})
        """), params).fetchall()
        for sid in single:
            values_map[sid[0]] = {
                "value": float(sid[1] or 0),
                "m1": 0, "m2": 0, "m3": 0, "m4": 0, "m5": 0, "m6": 0,
                "m7": 0, "m8": 0, "m9": 0, "m10": 0, "m11": 0, "m12": 0,
                "m13": 0, "m14": 0, "m15": 0, "m16": 0, "m17": 0, "m18": 0,
                "m19": 0, "m20": 0, "m21": 0, "m22": 0, "m23": 0, "m24": 0,
                "has_value": True,
            }

    # 3) 计算每节点的 m1~m24：基于 coa_node_ids 关联账户册节点的 m1_gap~m24_gap 求和
    #    仅当 coa_node_ids 非空时计算
    gap_cols = [f"m{i}_gap" for i in range(1, 25)]
    for node in by_id.values():
        coa_ids = node["coa_node_ids"]
        if not coa_ids:
            continue
        ph = ",".join([f":c{i}" for i in range(len(coa_ids))])
        params2 = {"dd": data_date}
        for i, cid in enumerate(coa_ids):
            params2[f"c{i}"] = cid
        row = db.execute(text(f"""
            SELECT {','.join('SUM(b.' + c + ')' for c in gap_cols)}
            FROM prcp_data_balance b
            WHERE b.is_deleted=0 AND b.data_date=STR_TO_DATE(:dd, '%Y-%m-%d')
              AND b.coa_node_id IN ({ph})
        """), params2).first()
        if row:
            ms = [float(row[i] or 0) for i in range(24)]
            if node["id"] not in values_map:
                values_map[node["id"]] = {
                    "value": 0, "has_value": False,
                    "m1": 0, "m2": 0, "m3": 0, "m4": 0, "m5": 0, "m6": 0,
                    "m7": 0, "m8": 0, "m9": 0, "m10": 0, "m11": 0, "m12": 0,
                    "m13": 0, "m14": 0, "m15": 0, "m16": 0, "m17": 0, "m18": 0,
                    "m19": 0, "m20": 0, "m21": 0, "m22": 0, "m23": 0, "m24": 0,
                }
            for i in range(24):
                values_map[node["id"]][f"m{i+1}"] = ms[i]

    return {
        "category": category.upper(),
        "data_date": data_date,
        "items": roots,
        "values_map": values_map,
        "total_items": len(by_id),
    }


@router.put("/items/{item_id}/value")
async def save_item_value(
    item_id: int, payload: dict,
    user=Depends(get_current_user), db: Session = Depends(get_db),
):
    """保存某个 item 在某月的值（前端树形表格编辑用）
    payload: {data_date, value, source}
    """
    uid = user.get("id", 1)
    data_date = payload["data_date"]
    value = payload.get("value", 0)
    source = payload.get("source", "MANUAL")
    existing = db.execute(text("""
        SELECT id FROM prcp_rpt_value
        WHERE item_id=:i AND data_date=STR_TO_DATE(:d, '%Y-%m-%d') AND is_deleted=0
    """), {"i": item_id, "d": data_date}).first()
    if existing:
        db.execute(text("""
            UPDATE prcp_rpt_value SET value=:v, source=:src, updated_by=:uid, updated_at=NOW()
            WHERE id=:id
        """), {"v": value, "src": source, "uid": uid, "id": existing[0]})
        return {"id": existing[0], "action": "updated"}
    else:
        rid = db.execute(text("""
            INSERT INTO prcp_rpt_value (item_id, data_date, value, source, created_by, updated_by)
            VALUES (:i, STR_TO_DATE(:d, '%Y-%m-%d'), :v, :src, :uid, :uid)
        """), {"i": item_id, "d": data_date, "v": value, "src": source, "uid": uid}).lastrowid
        db.commit()
        return {"id": rid, "action": "created"}


@router.put("/items/{item_id}/calc-rule")
async def save_calc_rule(item_id: int, payload: dict,
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    """保存取数逻辑（更新 rpt_item.coa_node_ids）"""
    uid = user.get("id", 1)
    coa_ids = payload.get("coa_node_ids", [])
    formula = payload.get("formula")
    db.execute(text("""
        UPDATE prcp_rpt_item SET coa_node_ids=:c, formula=:f,
          updated_by=:uid, updated_at=NOW() WHERE id=:id
    """), {"c": json.dumps(coa_ids, ensure_ascii=False), "f": formula, "uid": uid, "id": item_id})
    db.commit()
    return {"ok": True}


@router.get("/values")
async def list_values(item_id: int = None, data_date: str = None,
                      db: Session = Depends(get_db), user=Depends(get_current_user)):
    """月度数据值"""
    sql = """
        SELECT v.id, v.item_id, v.data_date, v.value, v.source, v.calc_log,
               i.item_code, i.item_name, i.category
        FROM prcp_rpt_value v
        LEFT JOIN prcp_rpt_item i ON i.id=v.item_id
        WHERE v.is_deleted=0
    """
    params = {}
    if item_id:
        sql += " AND v.item_id=:iid"
        params["iid"] = item_id
    if data_date:
        sql += " AND v.data_date=STR_TO_DATE(:dd, '%Y-%m-%d')"
        params["dd"] = data_date
    sql += " ORDER BY v.data_date DESC, v.item_id LIMIT 5000"
    rows = db.execute(text(sql), params).fetchall()
    return {"items": [{
        "id": r[0], "item_id": r[1],
        "data_date": r[2].isoformat() if r[2] else None,
        "value": float(r[3]) if r[3] is not None else 0,
        "source": r[4], "calc_log": r[5],
        "item_code": r[6], "item_name": r[7], "category": r[8],
    } for r in rows]}


@router.post("/values")
async def upsert_value(payload: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """upsert 月度值"""
    uid = user.get("id", 1)
    item_id = payload["item_id"]
    data_date = payload["data_date"]
    value = payload["value"]
    existing = db.execute(text("""
        SELECT id FROM prcp_rpt_value
        WHERE item_id=:i AND data_date=STR_TO_DATE(:d, '%Y-%m-%d') AND is_deleted=0
    """), {"i": item_id, "d": data_date}).first()
    if existing:
        db.execute(text("""
            UPDATE prcp_rpt_value SET value=:v, source=:src, updated_by=:uid, updated_at=NOW()
            WHERE id=:id
        """), {"v": value, "src": payload.get("source", "MANUAL"), "uid": uid, "id": existing[0]})
        rid = existing[0]; action = "updated"
    else:
        result = db.execute(text("""
            INSERT INTO prcp_rpt_value (item_id, data_date, value, source, created_by, updated_by)
            VALUES (:i, STR_TO_DATE(:d, '%Y-%m-%d'), :v, :src, :uid, :uid)
        """), {"i": item_id, "d": data_date, "v": value, "src": payload.get("source", "MANUAL"), "uid": uid})
        rid = result.lastrowid; action = "created"
    db.commit()
    return {"id": rid, "action": action}


@router.delete("/values/{vid}")
async def del_value(vid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(text("UPDATE prcp_rpt_value SET is_deleted=1, updated_by=:uid WHERE id=:id"),
               {"uid": user.get("id", 1), "id": vid})
    db.commit()
    return {"ok": True}


@router.get("/calc-preview")
async def calc_preview(item_id: int, data_date: str,
                       db: Session = Depends(get_db), user=Depends(get_current_user)):
    """预览：根据 item_id 的取数逻辑（coa_node_ids）从 prcp_data_balance 拿当月余额"""
    item = db.execute(text("""
        SELECT item_code, item_name, category, coa_node_ids FROM prcp_rpt_item
        WHERE id=:id AND is_deleted=0
    """), {"id": item_id}).first()
    if not item:
        raise HTTPException(404, "item not found")
    coa_ids = json.loads(item[3]) if item[3] else []
    if not coa_ids:
        return {"item_code": item[0], "item_name": item[1],
                "value": 0, "detail": [], "message": "该指标未配置取数逻辑"}

    placeholders = ",".join([f":p{i}" for i in range(len(coa_ids))])
    params = {"dd": data_date}
    for i, nid in enumerate(coa_ids):
        params[f"p{i}"] = nid
    rows = db.execute(text(f"""
        SELECT n.id, n.node_code, n.node_name, b.current_amount
        FROM prcp_coa_node n LEFT JOIN prcp_data_balance b
          ON b.coa_node_id=n.id AND b.data_date=STR_TO_DATE(:dd, '%Y-%m-%d') AND b.is_deleted=0
        WHERE n.id IN ({placeholders})
    """), params).fetchall()

    detail = []
    total = 0
    for r in rows:
        amt = float(r[3] or 0)
        total += amt
        detail.append({"coa_node_id": r[0], "node_code": r[1], "node_name": r[2], "amount": amt})

    return {"item_code": item[0], "item_name": item[1], "category": item[2],
            "value": total, "detail": detail}


@router.post("/monthly-calc")
async def monthly_calc(payload: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """按月出指标：对所有有 coa_node_ids 的 item，根据 data_date 自动计算并写入 prcp_rpt_value

    payload: {data_date: "2026-08-01", category?: "FINANCIAL"}
    """
    data_date = payload.get("data_date")
    category = payload.get("category")
    if not data_date:
        raise HTTPException(400, "data_date 必填")

    uid = user.get("id", 1)
    sql = """
        SELECT id, item_code, item_name, coa_node_ids FROM prcp_rpt_item
        WHERE is_deleted=0 AND coa_node_ids IS NOT NULL AND JSON_LENGTH(coa_node_ids) > 0
    """
    params = {}
    if category:
        sql += " AND category=:cat"
        params["cat"] = category.upper()
    rows = db.execute(text(sql), params).fetchall()

    results = []
    for r in rows:
        item_id, code, name, coa_json = r
        try:
            coa_ids = json.loads(coa_json)
        except Exception:
            continue
        if not coa_ids:
            continue

        placeholders = ",".join([f":p{i}" for i in range(len(coa_ids))])
        p = {"dd": data_date}
        for i, nid in enumerate(coa_ids):
            p[f"p{i}"] = nid
        bals = db.execute(text(f"""
            SELECT COALESCE(SUM(current_amount),0) FROM prcp_data_balance
            WHERE coa_node_id IN ({placeholders}) AND data_date=STR_TO_DATE(:dd, '%Y-%m-%d') AND is_deleted=0
        """), p).scalar() or 0
        value = float(bals)

        existing = db.execute(text("""
            SELECT id FROM prcp_rpt_value WHERE item_id=:i AND data_date=STR_TO_DATE(:d, '%Y-%m-%d')
        """), {"i": item_id, "d": data_date}).first()
        if existing:
            db.execute(text("""
                UPDATE prcp_rpt_value SET value=:v, source='CALC', updated_by=:uid, updated_at=NOW()
                WHERE id=:id
            """), {"v": value, "uid": uid, "id": existing[0]})
            action = "updated"
        else:
            db.execute(text("""
                INSERT INTO prcp_rpt_value (item_id, data_date, value, source, created_by, updated_by)
                VALUES (:i, STR_TO_DATE(:d, '%Y-%m-%d'), :v, 'CALC', :uid, :uid)
            """), {"i": item_id, "d": data_date, "v": value, "uid": uid})
            action = "created"

        results.append({"item_id": item_id, "item_code": code, "item_name": name, "value": value, "action": action})

    db.commit()
    return {"count": len(results), "data_date": data_date, "results": results}


@router.get("/months")
async def list_months(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """列出有数据的月份（来自 prcp_data_balance）"""
    rows = db.execute(text("""
        SELECT DISTINCT DATE_FORMAT(data_date, '%Y-%m') AS m FROM prcp_data_balance
        WHERE is_deleted=0 ORDER BY m
    """)).fetchall()
    return {"items": [r[0] for r in rows]}
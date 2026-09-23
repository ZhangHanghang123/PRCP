"""PRCP 指标计量系数维护 API

字段：账户册方案 + 账户册编码 + 指标类型 + 数据日期 + 当前/未来1~5年值
字典：METRIC_TYPE（指标类型）/ METRIC_UNIT（计量单位）
ID 规则：{scheme_code}_{node_code}_{metric_code}_{YYYYMMDD}

端点：
- GET    /metric-coefficient/                列表（带筛选）
- GET    /metric-coefficient/options         下拉选项（账户册方案 / 节点 / 指标类型）
- POST   /metric-coefficient/                新增
- PUT    /metric-coefficient/{mid}           更新
- DELETE /metric-coefficient/{mid}           软删
- POST   /metric-coefficient/import          Excel 批量导入
"""
import io
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/metric-coefficient", tags=["指标计量系数"])


# ---------- Schemas ----------
class MetricCoefficientIn(BaseModel):
    scheme_id: int
    scheme_code: str
    node_id: int
    node_code: str
    metric_type: str
    metric_code: Optional[str] = None   # 不传则默认 = metric_type
    data_date: str                       # YYYY-MM-DD
    current_value: float = 0
    y1_value: float = 0
    y2_value: float = 0
    y3_value: float = 0
    y4_value: float = 0
    y5_value: float = 0
    unit: str = "PERCENT"
    description: Optional[str] = None
    status: str = "ACTIVE"


def _build_id(scheme_code: str, node_code: str, metric_code: str, data_date: str) -> str:
    """ID 生成：{scheme_code}_{node_code}_{metric_code}_{YYYYMMDD}"""
    # data_date 支持 'YYYY-MM-DD' / 'YYYYMMDD' / datetime
    s = str(data_date).strip()
    if "-" in s:
        s = s.replace("-", "")
    return f"{scheme_code}_{node_code}_{metric_code}_{s}"


# ---------- 列表 + 选项 ----------
@router.get("")
async def list_coefficients(
    scheme_id: Optional[int] = None,
    node_id: Optional[int] = None,
    metric_type: Optional[str] = None,
    data_date: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """列表查询"""
    where = ["mc.is_deleted=0"]
    params: Dict[str, Any] = {}
    if scheme_id:
        where.append("mc.scheme_id=:scheme_id")
        params["scheme_id"] = scheme_id
    if node_id:
        where.append("mc.node_id=:node_id")
        params["node_id"] = node_id
    if metric_type:
        where.append("mc.metric_type=:metric_type")
        params["metric_type"] = metric_type
    if data_date:
        where.append("mc.data_date=STR_TO_DATE(:data_date, '%Y-%m-%d')")
        params["data_date"] = data_date
    if keyword:
        where.append("(mc.scheme_code LIKE :kw OR mc.node_code LIKE :kw OR mc.description LIKE :kw)")
        params["kw"] = f"%{keyword}%"

    rows = db.execute(
        text(f"""
            SELECT mc.id, mc.scheme_id, mc.scheme_code, mc.node_id, mc.node_code,
                   mc.metric_type, mc.metric_code, mc.data_date,
                   mc.current_value, mc.y1_value, mc.y2_value, mc.y3_value, mc.y4_value, mc.y5_value,
                   mc.unit, mc.description, mc.status,
                   mc.created_at, mc.updated_at,
                   s.scheme_name, n.node_name
            FROM prcp_metric_coefficient mc
            LEFT JOIN prcp_coa_scheme s ON s.id=mc.scheme_id
            LEFT JOIN prcp_coa_node   n ON n.id=mc.node_id
            WHERE {' AND '.join(where)}
            ORDER BY mc.data_date DESC, mc.scheme_code, mc.node_code, mc.metric_type
            LIMIT 5000
        """),
        params,
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0],
                "scheme_id": r[1], "scheme_code": r[2],
                "node_id": r[3], "node_code": r[4],
                "metric_type": r[5], "metric_code": r[6],
                "data_date": r[7].isoformat() if r[7] else None,
                "current_value": float(r[8] or 0),
                "y1_value": float(r[9] or 0),
                "y2_value": float(r[10] or 0),
                "y3_value": float(r[11] or 0),
                "y4_value": float(r[12] or 0),
                "y5_value": float(r[13] or 0),
                "unit": r[14], "description": r[15], "status": r[16],
                "created_at": r[17].isoformat() if r[17] else None,
                "updated_at": r[18].isoformat() if r[18] else None,
                "scheme_name": r[19], "node_name": r[20],
            } for r in rows
        ]
    }


@router.get("/options")
async def list_options(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """下拉选项：账户册方案 + 该方案下的节点 + 指标类型字典 + 计量单位字典"""
    schemes = db.execute(text("""
        SELECT id, scheme_code, scheme_name, status
        FROM prcp_coa_scheme
        WHERE is_deleted=0 AND status='ACTIVE'
        ORDER BY scheme_code
    """)).fetchall()
    nodes = db.execute(text("""
        SELECT id, scheme_id, node_code, node_name, node_level, status
        FROM prcp_coa_node
        WHERE is_deleted=0 AND status='ACTIVE'
        ORDER BY scheme_id, sort_order, path
    """)).fetchall()
    metric_types = db.execute(text("""
        SELECT dict_key, dict_label, color, sort_order
        FROM sys_dict
        WHERE is_deleted=0 AND status='ACTIVE' AND dict_type='METRIC_TYPE'
        ORDER BY sort_order, dict_key
    """)).fetchall()
    units = db.execute(text("""
        SELECT dict_key, dict_label
        FROM sys_dict
        WHERE is_deleted=0 AND status='ACTIVE' AND dict_type='METRIC_UNIT'
        ORDER BY sort_order, dict_key
    """)).fetchall()
    return {
        "schemes": [
            {"id": r[0], "scheme_code": r[1], "scheme_name": r[2], "status": r[3]}
            for r in schemes
        ],
        "nodes": [
            {
                "id": r[0], "scheme_id": r[1],
                "node_code": r[2], "node_name": r[3],
                "node_level": r[4], "status": r[5],
                "label": f"{r[2]} | {r[3]}",
            } for r in nodes
        ],
        "metric_types": [
            {"dict_key": r[0], "dict_label": r[1], "color": r[2], "sort_order": r[3]}
            for r in metric_types
        ],
        "units": [
            {"dict_key": r[0], "dict_label": r[1]}
            for r in units
        ],
    }


@router.get("/nodes-by-scheme")
async def nodes_by_scheme(scheme_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """按账户册方案 ID 加载节点（前端下拉联动用）"""
    rows = db.execute(text("""
        SELECT id, scheme_id, node_code, node_name, node_level, status
        FROM prcp_coa_node
        WHERE scheme_id=:s AND is_deleted=0 AND status='ACTIVE'
        ORDER BY sort_order, path
    """), {"s": scheme_id}).fetchall()
    return {
        "items": [
            {
                "id": r[0], "scheme_id": r[1],
                "node_code": r[2], "node_name": r[3],
                "node_level": r[4], "status": r[5],
                "label": f"{r[2]} | {r[3]}",
            } for r in rows
        ]
    }


# ---------- 新增 / 更新 ----------
@router.post("")
async def create_coefficient(
    p: MetricCoefficientIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """新增一条指标计量系数记录（ID 自动生成）"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    metric_code = p.metric_code or p.metric_type
    new_id = _build_id(p.scheme_code, p.node_code, metric_code, p.data_date)

    # 校验：方案是否存在
    s = db.execute(
        text("SELECT id, scheme_code FROM prcp_coa_scheme WHERE id=:id AND is_deleted=0"),
        {"id": p.scheme_id},
    ).first()
    if not s:
        raise HTTPException(400, "账户册方案不存在")
    # 校验：节点是否在该方案下
    n = db.execute(
        text("SELECT id, scheme_id, node_code FROM prcp_coa_node WHERE id=:id AND is_deleted=0"),
        {"id": p.node_id},
    ).first()
    if not n:
        raise HTTPException(400, "账户册节点不存在")
    if n[1] != p.scheme_id:
        raise HTTPException(400, f"节点不属于该方案（节点 scheme_id={n[1]}）")
    # 校验：节点编码与节点表一致
    if n[2] != p.node_code:
        raise HTTPException(400, f"节点编码不一致（提交 {p.node_code} / 表中 {n[2]}）")
    # 校验：方案编码与方案表一致
    if s[1] != p.scheme_code:
        raise HTTPException(400, f"方案编码不一致（提交 {p.scheme_code} / 表中 {s[1]}）")
    # 校验：指标类型必须是字典 METRIC_TYPE 中的一项
    mt = db.execute(text("""
        SELECT 1 FROM sys_dict
        WHERE dict_type='METRIC_TYPE' AND dict_key=:k AND is_deleted=0 AND status='ACTIVE'
    """), {"k": p.metric_type}).first()
    if not mt:
        raise HTTPException(400, f"指标类型 {p.metric_type} 不在 METRIC_TYPE 字典中")

    try:
        rid = db.execute(text("""
            INSERT INTO prcp_metric_coefficient
              (id, scheme_id, scheme_code, node_id, node_code,
               metric_type, metric_code, data_date,
               current_value, y1_value, y2_value, y3_value, y4_value, y5_value,
               unit, description, status, created_by, updated_by)
            VALUES
              (:id, :sid, :sc, :nid, :nc,
               :mt, :mc, STR_TO_DATE(:dd, '%Y-%m-%d'),
               :cur, :y1, :y2, :y3, :y4, :y5,
               :u, :desc, :s, :uid, :uid)
        """), {
            "id": new_id,
            "sid": p.scheme_id, "sc": p.scheme_code,
            "nid": p.node_id, "nc": p.node_code,
            "mt": p.metric_type, "mc": metric_code,
            "dd": p.data_date,
            "cur": p.current_value, "y1": p.y1_value, "y2": p.y2_value,
            "y3": p.y3_value, "y4": p.y4_value, "y5": p.y5_value,
            "u": p.unit, "desc": p.description, "s": p.status, "uid": uid,
        }).lastrowid
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"创建失败：可能记录已存在（{e}）")
    return {"id": new_id, "internal_id": rid, "action": "created"}


@router.put("/{mid}")
async def update_coefficient(
    mid: str,
    payload: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """更新（ID 不可改；只改 6 期数值 + 备注 + 单位 + 状态）"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 取出现有记录
    cur = db.execute(text("""
        SELECT id FROM prcp_metric_coefficient WHERE id=:id AND is_deleted=0
    """), {"id": mid}).first()
    if not cur:
        raise HTTPException(404, "记录不存在")

    set_clauses = []
    params: Dict[str, Any] = {"id": mid, "uid": uid}
    for field in ("current_value", "y1_value", "y2_value", "y3_value", "y4_value", "y5_value"):
        if field in payload:
            set_clauses.append(f"{field}=:{field}")
            params[field] = payload[field]
    if "unit" in payload:
        set_clauses.append("unit=:unit"); params["unit"] = payload["unit"]
    if "description" in payload:
        set_clauses.append("description=:desc"); params["desc"] = payload["description"]
    if "status" in payload:
        set_clauses.append("status=:status"); params["status"] = payload["status"]
    if not set_clauses:
        raise HTTPException(400, "至少要传一个可更新字段")

    set_clauses.append("updated_by=:uid")
    set_clauses.append("updated_at=NOW()")
    db.execute(
        text(f"UPDATE prcp_metric_coefficient SET {', '.join(set_clauses)} WHERE id=:id"),
        params,
    )
    db.commit()
    return {"id": mid, "ok": True}


@router.delete("/{mid}")
async def delete_coefficient(
    mid: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """软删"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(text("""
        UPDATE prcp_metric_coefficient
        SET is_deleted=1, updated_by=:uid, updated_at=NOW()
        WHERE id=:id AND is_deleted=0
    """), {"uid": uid, "id": mid})
    if r.rowcount == 0:
        raise HTTPException(404, "记录不存在")
    db.commit()
    return {"ok": True, "id": mid}


# ---------- Excel 批量导入 ----------
@router.post("/import")
async def import_xlsx(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """批量导入 Excel：列顺序：数据日期|账户册方案编码|账户册编码|指标类型|当前值|y1|y2|y3|y4|y5|单位|备注"""
    import openpyxl

    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(400, f"Excel 解析失败：{e}")

    # 预加载方案 + 节点 + 指标字典
    scheme_map = {
        r[0]: r[1] for r in db.execute(text("""
            SELECT scheme_code, scheme_code FROM prcp_coa_scheme WHERE is_deleted=0
        """)).fetchall()
    }
    scheme_id_map = {
        r[0]: r[1] for r in db.execute(text("""
            SELECT scheme_code, id FROM prcp_coa_scheme WHERE is_deleted=0
        """)).fetchall()
    }
    node_map = {}  # (scheme_code, node_code) -> (id, scheme_id)
    for r in db.execute(text("""
        SELECT id, scheme_id, node_code FROM prcp_coa_node WHERE is_deleted=0
    """)).fetchall():
        # 反查 scheme_code
        s_code = db.execute(text("SELECT scheme_code FROM prcp_coa_scheme WHERE id=:id"),
                            {"id": r[1]}).scalar()
        node_map[(s_code, r[2])] = (r[0], r[1])
    metric_set = {r[0] for r in db.execute(text("""
        SELECT dict_key FROM sys_dict
        WHERE dict_type='METRIC_TYPE' AND is_deleted=0 AND status='ACTIVE'
    """)).fetchall()}

    created, updated, skipped, errors = 0, 0, 0, []

    # 跳过表头
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for idx, row in enumerate(rows, start=2):
        if not row or not row[0]:
            continue
        try:
            # 列：数据日期|方案编码|节点编码|指标类型|当前|y1|y2|y3|y4|y5|单位|备注
            data_date = row[0]
            scheme_code = str(row[1]).strip() if row[1] else ""
            node_code = str(row[2]).strip() if row[2] else ""
            metric_type = str(row[3]).strip() if row[3] else ""
            if not (data_date and scheme_code and node_code and metric_type):
                errors.append(f"行 {idx}：必填字段缺失")
                skipped += 1; continue
            if metric_type not in metric_set:
                errors.append(f"行 {idx}：指标类型 {metric_type} 不在字典中")
                skipped += 1; continue
            node_info = node_map.get((scheme_code, node_code))
            if not node_info:
                errors.append(f"行 {idx}：节点 {scheme_code}/{node_code} 不存在")
                skipped += 1; continue
            node_id, scheme_id = node_info

            def _num(v, default=0):
                try:
                    return float(v) if v not in (None, "") else default
                except Exception:
                    return default

            cur_v = _num(row[4])
            y1 = _num(row[5]); y2 = _num(row[6]); y3 = _num(row[7])
            y4 = _num(row[8]); y5 = _num(row[9])
            unit = str(row[10]).strip() if row[10] else "PERCENT"
            desc = str(row[11]).strip() if row[11] else None

            # 日期格式归一
            if isinstance(data_date, datetime):
                dd = data_date.strftime("%Y-%m-%d")
            elif isinstance(data_date, date):
                dd = data_date.strftime("%Y-%m-%d")
            else:
                dd = str(data_date).strip()[:10]

            new_id = _build_id(scheme_code, node_code, metric_type, dd)

            existing = db.execute(text("""
                SELECT id FROM prcp_metric_coefficient WHERE id=:id
            """), {"id": new_id}).first()
            if existing:
                db.execute(text("""
                    UPDATE prcp_metric_coefficient SET
                      current_value=:cur, y1_value=:y1, y2_value=:y2,
                      y3_value=:y3, y4_value=:y4, y5_value=:y5,
                      unit=:u, description=:d, updated_by=:uid, updated_at=NOW(),
                      is_deleted=0
                    WHERE id=:id
                """), {
                    "cur": cur_v, "y1": y1, "y2": y2, "y3": y3, "y4": y4, "y5": y5,
                    "u": unit, "d": desc, "uid": uid, "id": new_id,
                })
                updated += 1
            else:
                db.execute(text("""
                    INSERT INTO prcp_metric_coefficient
                      (id, scheme_id, scheme_code, node_id, node_code,
                       metric_type, metric_code, data_date,
                       current_value, y1_value, y2_value, y3_value, y4_value, y5_value,
                       unit, description, status, created_by, updated_by)
                    VALUES
                      (:id, :sid, :sc, :nid, :nc,
                       :mt, :mc, STR_TO_DATE(:dd, '%Y-%m-%d'),
                       :cur, :y1, :y2, :y3, :y4, :y5,
                       :u, :d, 'ACTIVE', :uid, :uid)
                """), {
                    "id": new_id, "sid": scheme_id, "sc": scheme_code,
                    "nid": node_id, "nc": node_code,
                    "mt": metric_type, "mc": metric_type,
                    "dd": dd,
                    "cur": cur_v, "y1": y1, "y2": y2, "y3": y3, "y4": y4, "y5": y5,
                    "u": unit, "d": desc, "uid": uid,
                })
                created += 1
        except Exception as e:
            errors.append(f"行 {idx}：{e}")
            skipped += 1

    db.commit()
    return {
        "created": created, "updated": updated, "skipped": skipped,
        "errors": errors[:20],
        "error_count": len(errors),
    }


@router.get("/export-template")
async def export_template(user=Depends(get_current_user)):
    """下载导入模板"""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "指标计量系数"
    headers = ["数据日期(YYYY-MM-DD)", "账户册方案编码", "账户册编码", "指标类型",
               "当前值", "未来一年", "未来两年", "未来三年", "未来四年", "未来五年",
               "单位", "备注"]
    ws.append(headers)
    # 示例行
    ws.append(["2026-08-31", "COA_V6", "ZX_A011", "ROE", 12.5, 13.0, 13.5, 14.0, 14.5, 15.0, "PERCENT", "示例行"])
    ws.append(["2026-08-31", "COA_V6", "ZX_A011", "LCR", 150.0, 148.0, 145.0, 142.0, 140.0, 138.0, "PERCENT", ""])
    # 表头加粗
    from openpyxl.styles import Font
    for cell in ws[1]:
        cell.font = Font(bold=True)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="metric_coefficient_template.xlsx"'},
    )
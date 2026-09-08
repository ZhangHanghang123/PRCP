"""PRCP 后端入口 — 8006 /prcp/api"""
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.auth import init_admin
from app.routers import auth, dashboard, groups, positions, rules, tasks, metric_items
from app.routers import coa, reports, balance, kpi

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("prcp")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/prcp/api/docs",
    redoc_url="/prcp/api/redoc",
    openapi_url="/prcp/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    log.info(f"🚀 {settings.PROJECT_NAME} 启动中 …")
    try:
        Base.metadata.create_all(bind=engine)
        log.info("✅ 数据库表已就绪")
        with SessionLocal() as db:
            init_admin(db)
        log.info("✅ 默认 admin 账号已就绪")
    except Exception as e:
        log.error(f"❌ 初始化失败: {e}")


@app.get("/prcp/api/health")
async def health():
    return {"status": "ok", "project": settings.PROJECT_CODE, "version": "1.0.0"}


app.include_router(auth.router, prefix="/prcp/api")
app.include_router(dashboard.router, prefix="/prcp/api")
app.include_router(groups.router, prefix="/prcp/api")
app.include_router(positions.router, prefix="/prcp/api")
app.include_router(rules.router, prefix="/prcp/api")
app.include_router(tasks.router, prefix="/prcp/api")
app.include_router(metric_items.router, prefix="/prcp/api")
app.include_router(coa.router, prefix="/prcp/api")
app.include_router(reports.router, prefix="/prcp/api")
app.include_router(balance.router, prefix="/prcp/api")
app.include_router(kpi.router, prefix="/prcp/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=False)
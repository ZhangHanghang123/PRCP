"""PRCP 配置加载：优先 DATABASE_URL，否则用 MYSQL_* 字段构建"""
import os
from pathlib import Path
from urllib.parse import quote_plus

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except Exception:
    pass


def _env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v is not None and v != "" else default


def _build_mysql_url() -> str:
    host = _env("MYSQL_HOST", "127.0.0.1")
    port = _env("MYSQL_PORT", "3306")
    user = _env("MYSQL_USER", "prcp")
    pwd = _env("MYSQL_PASSWORD", "Prcp@2026")
    db = _env("MYSQL_DB", "prcp_db")
    return f"mysql+pymysql://{user}:{quote_plus(pwd)}@{host}:{port}/{db}?charset=utf8mb4"


class Settings:
    DATABASE_URL = _env("DATABASE_URL") or _build_mysql_url()
    DATABASE_URL_OVERRIDE = _env("DATABASE_URL")

    MYSQL_HOST = _env("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = _env("MYSQL_PORT", "3306")
    MYSQL_USER = _env("MYSQL_USER", "prcp")
    MYSQL_PASSWORD = _env("MYSQL_PASSWORD", "Prcp@2026")
    MYSQL_DB = _env("MYSQL_DB", "prcp_db")

    JWT_SECRET = _env("JWT_SECRET", "prcp-jwt-secret-change-me-in-prod")
    JWT_ALGORITHM = _env("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_HOURS = int(_env("JWT_EXPIRE_HOURS", "24"))

    LOG_LEVEL = _env("LOG_LEVEL", "INFO")

    PROJECT_NAME = "PRCP 组算平台"
    PROJECT_CODE = "PRCP"
    PORT = int(_env("PRCP_PORT", "8006"))


settings = Settings()
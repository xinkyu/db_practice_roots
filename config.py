# config.py — 从 .env 加载配置，不含任何明文密钥
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "genealogy_db"),
    "charset":  "utf8mb4",
    "autocommit": False,
}

SECRET_KEY = os.getenv("SECRET_KEY", "change_me")
DEBUG      = os.getenv("DEBUG", "True") == "True"
HOST       = "0.0.0.0"
PORT       = int(os.getenv("PORT", "5000"))

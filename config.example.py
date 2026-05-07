# config.example.py — 配置模板，复制为 config.py 并填写你的参数
# cp config.example.py config.py

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_MYSQL_PASSWORD",   # ← 改成你的 MySQL 密码
    "database": "genealogy_db",
    "charset": "utf8mb4",
    "autocommit": False,
}

SECRET_KEY = "change_this_to_a_random_string"  # ← 改成随机字符串
DEBUG = True
HOST = "0.0.0.0"
PORT = 5000

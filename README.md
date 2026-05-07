# 寻根溯源 — 族谱管理系统

## 环境要求
- Python 3.10+
- MySQL 8.0+

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 创建 .env 文件（参考下方格式，填入你的参数）

# 3. 初始化数据库
mysql -u root -p < schema/create_tables.sql
mysql -u root -p genealogy_db < schema/indexes.sql

# 4. 生成模拟数据（约 75 万条，需 8~10 分钟）
python data/generate_data.py

# 5. 启动
python app.py
# 访问 http://127.0.0.1:5000
```

## .env 配置格式

在项目根目录创建 `.env` 文件（**不要提交到 git**）：

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=你的MySQL密码
DB_NAME=genealogy_db
SECRET_KEY=任意随机字符串
DEBUG=True
PORT=5000
```

## 数据规模
- 12 个族谱，751,153 名成员，最大族谱 75 万人，每谱 30 代

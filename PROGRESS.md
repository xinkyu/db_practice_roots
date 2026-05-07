# 寻根溯源 — 开发进度追踪

## 项目信息

| 项目 | 值 |
|------|----|
| **数据库** | MySQL 8.0，数据库名 `genealogy_db` |
| **后端** | Python 3.10 + Flask 3.0 |
| **前端** | 原生 HTML/CSS/JS + D3.js v7 |
| **项目根目录** | `e:\db_practice_roots\` |
| **启动命令** | `python app.py` → `http://127.0.0.1:5000` |

---

## 阶段进度

| 阶段 | 内容 | 状态 | 完成时间 |
|------|------|------|---------|
| Phase 1 | 数据库建模（DDL + 约束 + 触发器） | ✅ 完成 | 2026-05-07 |
| Phase 2 | 数据生成（751,153 成员，12族谱，30代）| ✅ 完成 | 2026-05-07 |
| Phase 3 | 5个核心 SQL 查询 | ✅ 完成 | 2026-05-07 |
| Phase 4 | Flask 后端 API（含关系管理） | ✅ 完成 | 2026-05-07 |
| Phase 5 | 前端界面 + D3.js 树形图 | ✅ 完成 | 2026-05-07 |
| Phase 6 | 索引优化 + EXPLAIN 性能对比 SQL | ✅ 完成 | 2026-05-07 |

---

## Phase 1 — 数据库建模 ✅

### 文件
- `schema/create_tables.sql` — 6张表建表 DDL
- `schema/indexes.sql` — 7个索引定义

### 表结构

| 表名 | 说明 |
|------|------|
| `users` | 系统用户（user_id, username, password_hash） |
| `genealogy` | 族谱（genealogy_id, name, surname, revision_date, creator_id） |
| `genealogy_access` | 族谱权限 M:N（genealogy_id, user_id, role） |
| `member` | 成员（member_id, genealogy_id, name, gender, birth_year, death_year, biography, generation） |
| `parent_child` | 血缘关系（parent_id, child_id, relation_type: father/mother） |
| `marriage` | 婚姻关系（spouse1_id, spouse2_id, marriage_year） |

### 范式
所有表满足 **BCNF**（每个非平凡函数依赖的决定因素都是超键）

### 约束
- `CHECK(death_year >= birth_year)` — 卒年不早于生年
- `CHECK(birth_year > 0)` — 出生年为正数
- `CHECK(parent_id != child_id)` — 不能自引用
- `CHECK(spouse1_id < spouse2_id)` — 防止婚姻关系重复记录
- **触发器** `trg_check_parent_birth` — 父母出生年必须早于子女

---

## Phase 2 — 数据生成 ✅

### 文件
- `data/generate_data.py` — 数据生成脚本（直接写入 MySQL）

### 实际生成规模

| 指标 | 数值 |
|------|------|
| 族谱数量 | 12 个 |
| 最大族谱（龙氏宗谱） | **750,952 人** |
| 系统总成员 | **751,153 人** |
| 每族谱传承代数 | **30 代** |
| 实验要求最低标准 | ≥10族谱、≥5万(最大)、≥10万(总计)、≥30代 ✅ |

### 导入导出命令
```sql
-- 导出某族谱成员为 CSV
SELECT * FROM member WHERE genealogy_id = 1
INTO OUTFILE '/tmp/family1.csv'
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n';

-- 从 CSV 批量导入
LOAD DATA INFILE '/tmp/members.csv'
INTO TABLE member
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;
```

---

## Phase 3 — 5个核心 SQL 查询 ✅

文件：`sql/queries.sql`

| 查询 | 说明 |
|------|------|
| 查询1 | 给定成员ID，查询其配偶及所有子女（UNION） |
| 查询2 | **递归CTE** — 向上追溯所有历代祖先 |
| 查询3 | 统计各辈分平均寿命，找出寿命最长的一代 |
| 查询4 | 年龄>50岁、在世、无配偶的男性成员（EXISTS） |
| 查询5 | **窗口函数** — 出生年早于同辈平均值的所有成员 |

---

## Phase 4 — Flask 后端 API ✅

文件：`app.py`，共 **22个 API 路由**

### 认证
| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/auth/register` | POST | 注册 |
| `/api/auth/login` | POST | 登录 |
| `/api/auth/logout` | POST | 退出 |
| `/api/auth/me` | GET | 当前用户 |

### 族谱
| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/genealogies` | GET/POST | 列表/创建 |
| `/api/genealogies/<id>` | GET/PUT/DELETE | 详情/编辑/删除 |
| `/api/genealogies/<id>/invite` | POST | 邀请协作者 |
| `/api/genealogies/<id>/dashboard` | GET | 统计数据 |
| `/api/genealogies/<id>/members` | GET/POST | 成员列表/新增 |

### 成员
| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/members/<id>` | GET/PUT/DELETE | 详情/编辑/删除 |
| `/api/members/search` | GET | 姓名模糊搜索 |
| `/api/members/<id>/tree` | GET | 后代树（向下） |
| `/api/members/<id>/ancestors` | GET | 祖先追溯（向上BFS） |
| `/api/members/kinship` | GET | 两人亲缘关系路径（BFS） |

### 关系管理
| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/members/<id>/relations` | GET | 获取所有关系 |
| `/api/members/<id>/parents` | POST | 添加父母 |
| `/api/members/<id>/parents/<pid>` | DELETE | 移除父母 |
| `/api/members/<id>/children` | POST | 添加子女 |
| `/api/members/<id>/children/<cid>` | DELETE | 移除子女 |
| `/api/members/<id>/spouse` | POST | 添加配偶 |
| `/api/members/<id>/spouse/<sid>` | DELETE | 移除配偶 |

---

## Phase 5 — 前端界面 ✅

| 页面 | 文件 | 功能 |
|------|------|------|
| 登录/注册 | `templates/login.html` | Tab切换，表单验证 |
| 控制台 | `templates/dashboard.html` | 族谱卡片列表，创建/邀请/删除 |
| 族谱详情 | `templates/genealogy.html` | 成员列表+搜索+分页、D3树形图、祖先查询、亲缘关系 |
| 成员详情 | `templates/member.html` | 基本信息编辑、父母/子女/配偶关系管理 |

**D3.js 树形图特性**（`static/js/tree.js`）：
- 按性别着色节点（蓝=男，红=女）
- 鼠标缩放 + 拖拽平移
- 点击节点跳转成员详情页

---

## Phase 6 — 索引优化 ✅

文件：`sql/performance_test.sql`

### 已创建索引

| 索引名 | 表 | 列 | 用途 |
|--------|----|----|------|
| `idx_member_name` | member | name | 姓名模糊查询 |
| `idx_member_genealogy` | member | genealogy_id | 族谱内成员查询 |
| `idx_member_genealogy_gen` | member | genealogy_id, generation | 辈分统计 |
| `idx_member_gender_birth` | member | gender, birth_year | 50岁以上男性查询 |
| `idx_pc_parent` | parent_child | parent_id | 向下查子节点（核心） |
| `idx_pc_child` | parent_child | child_id | 向上查父节点（核心） |
| `idx_marriage_spouse2` | marriage | spouse2_id | 配偶查询 |

### 性能对比实验
执行 `sql/performance_test.sql` 中的语句，分别记录有无索引下：
- 四代曾孙查询（递归CTE，深度3）的 EXPLAIN ANALYZE 结果
- 姓名模糊查询（`LIKE '%王%'`）的执行计划对比

---

## 文件结构

```
e:\db_practice_roots\
├── .gitignore
├── README.md
├── PROGRESS.md               ← 本文件
├── app.py                    ← Flask 主应用（22个API路由）
├── config.py                 ← 本地配置（已git-ignore，含密码）
├── config.example.py         ← 配置模板（队友复制使用）
├── requirements.txt
├── schema/
│   ├── create_tables.sql     ← 6张表 DDL + 触发器
│   └── indexes.sql           ← 7个索引
├── sql/
│   ├── queries.sql           ← 5个核心SQL查询
│   └── performance_test.sql  ← EXPLAIN 性能对比
├── data/
│   └── generate_data.py      ← 数据生成脚本（751K成员）
├── static/
│   ├── css/style.css         ← 深色国风主题
│   └── js/tree.js            ← D3.js 树形图
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── genealogy.html
    └── member.html
```

---

## 接续工作指令（跨对话续接）

```
当前项目: "寻根溯源"族谱管理系统
位置: e:\db_practice_roots\
状态: 全部6个Phase已完成，Flask运行于 http://127.0.0.1:5000
数据库: MySQL 8.0，genealogy_db，751,153名成员
参考: PROGRESS.md 查看全部细节
```

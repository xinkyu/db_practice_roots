-- ============================================================
-- "寻根溯源" - 索引定义
-- 需在 create_tables.sql 执行完毕后运行
-- ============================================================

USE genealogy_db;

-- ------------------------------------------------------------
-- member 表索引
-- ------------------------------------------------------------

-- 姓名模糊查询 (LIKE '%xxx%' 使用全文索引更高效)
CREATE INDEX idx_member_name ON member(name);

-- 族谱内成员查询
CREATE INDEX idx_member_genealogy ON member(genealogy_id);

-- 辈分统计（按族谱+代分组）
CREATE INDEX idx_member_genealogy_gen ON member(genealogy_id, generation);

-- 性别+出生年（条件查询：50岁以上男性）
CREATE INDEX idx_member_gender_birth ON member(gender, birth_year);

-- ------------------------------------------------------------
-- parent_child 表索引（核心：树形查询的瓶颈）
-- ------------------------------------------------------------

-- 根据父节点查子节点（向下遍历）
CREATE INDEX idx_pc_parent ON parent_child(parent_id);

-- 根据子节点查父节点（向上追溯祖先）
CREATE INDEX idx_pc_child ON parent_child(child_id);

-- ------------------------------------------------------------
-- marriage 表索引
-- ------------------------------------------------------------
CREATE INDEX idx_marriage_spouse2 ON marriage(spouse2_id);

-- ------------------------------------------------------------
-- genealogy_access 表索引
-- ------------------------------------------------------------
CREATE INDEX idx_access_user ON genealogy_access(user_id);

-- ------------------------------------------------------------
-- 验证索引
-- ------------------------------------------------------------
SHOW INDEX FROM member;
SHOW INDEX FROM parent_child;
SHOW INDEX FROM marriage;

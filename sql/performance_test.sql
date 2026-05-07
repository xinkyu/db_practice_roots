-- ============================================================
-- "寻根溯源" — 性能对比测试
-- 四代查询：某曾祖父的所有曾孙（深度 3 层）
-- ============================================================

USE genealogy_db;

-- 测试用根节点（建议用大族谱第1代的成员，例如 member_id=1）
SET @root_id = 1;

-- ============================================================
-- STEP 1: 删除相关索引，测试"无索引"状态
-- ============================================================
DROP INDEX IF EXISTS idx_pc_parent ON parent_child;
DROP INDEX IF EXISTS idx_pc_child  ON parent_child;

-- 无索引 — 四代查询（执行此语句并记录时间）
EXPLAIN ANALYZE
WITH RECURSIVE four_gen AS (
    SELECT member_id, 0 AS depth
    FROM member WHERE member_id = @root_id

    UNION ALL

    SELECT pc.child_id, fg.depth + 1
    FROM four_gen fg
    JOIN parent_child pc ON pc.parent_id = fg.member_id
    WHERE fg.depth < 3
)
SELECT m.member_id, m.name, m.gender, m.birth_year, m.generation
FROM four_gen fg
JOIN member m ON m.member_id = fg.member_id
WHERE fg.depth = 3;


-- ============================================================
-- STEP 2: 恢复索引，测试"有索引"状态
-- ============================================================
CREATE INDEX idx_pc_parent ON parent_child(parent_id);
CREATE INDEX idx_pc_child  ON parent_child(child_id);

-- 有索引 — 同一查询（与上面对比）
EXPLAIN ANALYZE
WITH RECURSIVE four_gen AS (
    SELECT member_id, 0 AS depth
    FROM member WHERE member_id = @root_id

    UNION ALL

    SELECT pc.child_id, fg.depth + 1
    FROM four_gen fg
    JOIN parent_child pc ON pc.parent_id = fg.member_id
    WHERE fg.depth < 3
)
SELECT m.member_id, m.name, m.gender, m.birth_year, m.generation
FROM four_gen fg
JOIN member m ON m.member_id = fg.member_id
WHERE fg.depth = 3;


-- ============================================================
-- STEP 3: 姓名模糊查询对比
-- ============================================================

-- 无 name 索引
DROP INDEX IF EXISTS idx_member_name ON member;

EXPLAIN ANALYZE
SELECT member_id, name, birth_year FROM member WHERE name LIKE '%王%' LIMIT 100;

-- 有 name 索引
CREATE INDEX idx_member_name ON member(name);

EXPLAIN ANALYZE
SELECT member_id, name, birth_year FROM member WHERE name LIKE '%王%' LIMIT 100;

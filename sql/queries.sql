-- ============================================================
-- "寻根溯源" — 5个核心SQL查询
-- 数据库: genealogy_db (MySQL 8.0+)
-- ============================================================

USE genealogy_db;

-- ============================================================
-- 查询 1: 基本查询 — 给定成员ID，查询其配偶及所有子女
-- 使用方法: 将 @input_id 替换为目标成员ID
-- ============================================================
SET @input_id = 1;

SELECT
    m.member_id,
    m.name,
    m.gender,
    m.birth_year,
    m.death_year,
    m.generation,
    '配偶' AS relationship
FROM member m
JOIN marriage mr
    ON (mr.spouse1_id = @input_id AND mr.spouse2_id = m.member_id)
    OR (mr.spouse2_id = @input_id AND mr.spouse1_id = m.member_id)

UNION ALL

SELECT
    m.member_id,
    m.name,
    m.gender,
    m.birth_year,
    m.death_year,
    m.generation,
    '子女' AS relationship
FROM member m
JOIN parent_child pc ON pc.parent_id = @input_id AND pc.child_id = m.member_id

ORDER BY relationship, birth_year;


-- ============================================================
-- 查询 2: 递归查询（核心）— 输入成员A的ID，输出所有历代祖先
-- 使用方法: 将 @ancestor_start 替换为目标成员ID
-- ============================================================
SET @ancestor_start = 100;

WITH RECURSIVE ancestors AS (
    -- 基础情况：目标成员本身（深度0）
    SELECT
        m.member_id,
        m.name,
        m.gender,
        m.birth_year,
        m.generation,
        0 AS depth,
        CAST(m.name AS CHAR(2000)) AS ancestor_path
    FROM member m
    WHERE m.member_id = @ancestor_start

    UNION ALL

    -- 递归：向上追溯父母
    SELECT
        p.member_id,
        p.name,
        p.gender,
        p.birth_year,
        p.generation,
        a.depth + 1,
        CONCAT(a.ancestor_path, ' ← ', p.name)
    FROM ancestors a
    JOIN parent_child pc ON pc.child_id = a.member_id
    JOIN member p ON p.member_id = pc.parent_id
    WHERE a.depth < 50  -- 防止无限循环，最多追溯50代
)
SELECT
    member_id,
    name,
    gender,
    birth_year,
    generation,
    depth AS generations_above,
    ancestor_path
FROM ancestors
ORDER BY depth;


-- ============================================================
-- 查询 3: 统计分析 — 某家族中平均寿命最长的一代（辈分）
-- 使用方法: 将 @family_id 替换为目标族谱ID
-- ============================================================
SET @family_id = 1;

SELECT
    generation,
    COUNT(*)                                    AS total_members,
    COUNT(CASE WHEN death_year IS NOT NULL THEN 1 END) AS deceased_count,
    ROUND(AVG(death_year - birth_year), 2)      AS avg_lifespan,
    MIN(death_year - birth_year)                AS min_lifespan,
    MAX(death_year - birth_year)                AS max_lifespan
FROM member
WHERE genealogy_id = @family_id
  AND death_year IS NOT NULL
  AND birth_year IS NOT NULL
  AND death_year >= birth_year
GROUP BY generation
ORDER BY avg_lifespan DESC
LIMIT 10;


-- ============================================================
-- 查询 4: 条件查询 — 年龄超过50岁且没有配偶的男性成员
-- 假设当前年份为 YEAR(CURDATE())
-- ============================================================
SELECT
    m.member_id,
    m.name,
    m.gender,
    m.birth_year,
    (YEAR(CURDATE()) - m.birth_year)            AS estimated_age,
    g.name                                      AS genealogy_name
FROM member m
JOIN genealogy g ON g.genealogy_id = m.genealogy_id
WHERE m.gender = 'M'
  AND m.death_year IS NULL                          -- 在世
  AND (YEAR(CURDATE()) - m.birth_year) > 50         -- 超过50岁
  AND NOT EXISTS (
      SELECT 1
      FROM marriage mr
      WHERE mr.spouse1_id = m.member_id
         OR mr.spouse2_id = m.member_id
  )
ORDER BY estimated_age DESC;


-- ============================================================
-- 查询 5: 窗口函数 — 出生年早于该辈分平均出生年份的所有成员
-- 使用方法: 将 @family_id 替换为目标族谱ID
-- ============================================================
SET @family_id = 1;

SELECT
    member_id,
    name,
    gender,
    birth_year,
    generation,
    ROUND(avg_birth_in_gen, 1)                  AS avg_birth_in_generation,
    (avg_birth_in_gen - birth_year)             AS years_earlier_than_avg
FROM (
    SELECT
        member_id,
        name,
        gender,
        birth_year,
        generation,
        AVG(birth_year) OVER (PARTITION BY generation) AS avg_birth_in_gen
    FROM member
    WHERE genealogy_id = @family_id
      AND birth_year IS NOT NULL
) ranked
WHERE birth_year < avg_birth_in_gen
ORDER BY generation, birth_year;

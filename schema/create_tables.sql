-- ============================================================
-- "寻根溯源" 族谱管理系统 - 数据库建表脚本
-- 数据库: genealogy_db
-- RDBMS: MySQL 8.0+
-- 范式: BCNF
-- ============================================================

CREATE DATABASE IF NOT EXISTS genealogy_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE genealogy_db;

-- ------------------------------------------------------------
-- 1. 用户表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id      INT AUTO_INCREMENT PRIMARY KEY,
    username     VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='系统用户';

-- ------------------------------------------------------------
-- 2. 族谱表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS genealogy (
    genealogy_id  INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL COMMENT '谱名',
    surname       VARCHAR(20)  NOT NULL COMMENT '姓氏',
    revision_date DATE                  COMMENT '修谱时间',
    creator_id    INT          NOT NULL,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES users(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='族谱';

-- ------------------------------------------------------------
-- 3. 族谱访问权限表 (M:N 用户-族谱)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS genealogy_access (
    genealogy_id INT  NOT NULL,
    user_id      INT  NOT NULL,
    role         ENUM('owner','editor') NOT NULL DEFAULT 'editor',
    granted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (genealogy_id, user_id),
    FOREIGN KEY (genealogy_id) REFERENCES genealogy(genealogy_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)      REFERENCES users(user_id)          ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='族谱访问权限';

-- ------------------------------------------------------------
-- 4. 成员表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS member (
    member_id    INT AUTO_INCREMENT PRIMARY KEY,
    genealogy_id INT          NOT NULL,
    name         VARCHAR(50)  NOT NULL COMMENT '姓名',
    gender       ENUM('M','F') NOT NULL COMMENT '性别: M=男 F=女',
    birth_year   INT                   COMMENT '出生年份',
    death_year   INT                   COMMENT '卒年(NULL表示在世)',
    biography    TEXT                  COMMENT '生平简介',
    generation   INT          NOT NULL DEFAULT 1 COMMENT '辈分(代)',
    FOREIGN KEY (genealogy_id) REFERENCES genealogy(genealogy_id) ON DELETE CASCADE,
    CONSTRAINT chk_death_after_birth CHECK (death_year IS NULL OR (birth_year IS NOT NULL AND death_year >= birth_year)),
    CONSTRAINT chk_birth_positive    CHECK (birth_year IS NULL OR birth_year > 0)
) ENGINE=InnoDB COMMENT='家族成员';

-- ------------------------------------------------------------
-- 5. 血缘关系表 (父子/父女/母子/母女)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parent_child (
    parent_id     INT NOT NULL,
    child_id      INT NOT NULL,
    relation_type ENUM('father','mother') NOT NULL COMMENT '父亲或母亲',
    PRIMARY KEY (parent_id, child_id, relation_type),
    FOREIGN KEY (parent_id) REFERENCES member(member_id) ON DELETE CASCADE,
    FOREIGN KEY (child_id)  REFERENCES member(member_id) ON DELETE CASCADE,
    CONSTRAINT chk_no_self_parent CHECK (parent_id != child_id)
) ENGINE=InnoDB COMMENT='血缘关系';

-- ------------------------------------------------------------
-- 6. 婚姻关系表
-- 规则: spouse1_id < spouse2_id 防止重复 (A,B) 和 (B,A)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marriage (
    spouse1_id   INT NOT NULL,
    spouse2_id   INT NOT NULL,
    marriage_year INT          COMMENT '成婚年份',
    PRIMARY KEY (spouse1_id, spouse2_id),
    FOREIGN KEY (spouse1_id) REFERENCES member(member_id) ON DELETE CASCADE,
    FOREIGN KEY (spouse2_id) REFERENCES member(member_id) ON DELETE CASCADE,
    CONSTRAINT chk_no_self_marriage CHECK (spouse1_id != spouse2_id),
    CONSTRAINT chk_ordered_spouses  CHECK (spouse1_id < spouse2_id)
) ENGINE=InnoDB COMMENT='婚姻关系';

-- ============================================================
-- 触发器: 插入血缘关系时验证父母出生年早于子女
-- ============================================================
DROP TRIGGER IF EXISTS trg_check_parent_birth;

DELIMITER //
CREATE TRIGGER trg_check_parent_birth
BEFORE INSERT ON parent_child
FOR EACH ROW
BEGIN
    DECLARE p_birth INT;
    DECLARE c_birth INT;
    SELECT birth_year INTO p_birth FROM member WHERE member_id = NEW.parent_id;
    SELECT birth_year INTO c_birth FROM member WHERE member_id = NEW.child_id;
    IF p_birth IS NOT NULL AND c_birth IS NOT NULL AND p_birth >= c_birth THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '约束违反: 父母的出生年份必须早于子女';
    END IF;
END //
DELIMITER ;

-- ============================================================
-- 验证
-- ============================================================
SHOW TABLES;

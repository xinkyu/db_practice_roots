"""
"寻根溯源" — 模拟数据生成脚本
==============================
生成目标:
  - 族谱数量  : 12 个
  - 最大族谱  : 1 个 >= 50,000 成员
  - 系统总计  : >= 100,000 成员
  - 每族谱   : >= 30 代传承

策略:
  - 大族谱(family_id=1): 前15代少(2-3子), 后15代多(3-5子) → 约6万成员
  - 其余11个族谱: 各约4,000 成员, 30代
  - 每代父母各找一个外部配偶(生成外部成员作配偶但不单独计入子代繁衍)

运行方式:
  python generate_data.py
  (首先运行: pip install mysql-connector-python)
"""

import random
import math
import os
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── 数据库配置（从 .env 读取）──────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "genealogy_db"),
    "charset":  "utf8mb4",
}

# ── 姓名素材 ────────────────────────────────────────────────
SURNAMES = [
    "李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
    "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧",
]
MALE_NAMES = [
    "伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "洋",
    "艳", "勇", "军", "杰", "娟", "涛", "明", "超", "秀兰", "霞",
    "平", "刚", "桂英", "玲", "辉", "英", "建华", "志强", "建国", "俊",
    "浩然", "子墨", "晨阳", "宇轩", "博文", "天宇", "鹏飞", "志远", "文博", "浩宇",
    "子豪", "明轩", "子轩", "浩然", "睿泽", "文昊", "泽宇", "弘文", "俊豪", "建辉",
]
FEMALE_NAMES = [
    "秀", "芝", "玉", "梅", "兰", "花", "英", "凤", "娟", "华",
    "云", "莲", "月", "红", "燕", "素", "翠", "香", "珍", "蓉",
    "欣怡", "若汐", "梦琪", "初夏", "可欣", "梦瑶", "雅静", "欣然", "佳怡", "心怡",
    "若萱", "紫萱", "语嫣", "梦雅", "思琪", "诗涵", "晓彤", "雨菲", "晨曦", "语桐",
]

GENEALOGY_NAMES = [
    ("龙氏宗谱", "龙"), ("凤氏家谱", "凤"), ("虎族族谱", "虎"), ("熊氏世谱", "熊"),
    ("鹤氏家谱", "鹤"), ("麟氏宗谱", "麟"), ("豹氏族谱", "豹"), ("狼氏世谱", "狼"),
    ("燕氏家谱", "燕"), ("鸿氏宗谱", "鸿"), ("蛟氏族谱", "蛟"), ("凰氏世谱", "凰"),
]

# ── 工具函数 ────────────────────────────────────────────────
def rand_name(gender: str) -> str:
    pool = MALE_NAMES if gender == "M" else FEMALE_NAMES
    return random.choice(SURNAMES) + random.choice(pool)

def gen_birth_year(parent_birth: int | None, generation: int) -> int:
    """子辈出生年 = 父辈出生年 + 20~35 年"""
    base = parent_birth if parent_birth else (1200 + generation * 20)
    return base + random.randint(20, 35)

# ── 主生成逻辑 ───────────────────────────────────────────────
def generate_family(
    cursor,
    genealogy_id: int,
    surname: str,
    num_generations: int,
    children_range_early: tuple,
    children_range_late: tuple,
    split_gen: int,
    starting_birth_year: int,
) -> int:
    """
    生成一个家族的所有成员与关系。
    返回总成员数。
    """
    # current_gen: list of (member_id, birth_year, gender)
    # 始祖夫妇
    ancestor_birth = starting_birth_year
    ancestor_id = insert_member(cursor, genealogy_id, surname, "M", ancestor_birth, 1)
    spouse_birth = ancestor_birth + random.randint(-3, 3)
    spouse_id = insert_member(cursor, genealogy_id, rand_name("F").lstrip(surname), "F", spouse_birth, 1)
    # 确保 spouse1_id < spouse2_id
    s1, s2 = min(ancestor_id, spouse_id), max(ancestor_id, spouse_id)
    cursor.execute(
        "INSERT IGNORE INTO marriage(spouse1_id,spouse2_id,marriage_year) VALUES(%s,%s,%s)",
        (s1, s2, ancestor_birth + random.randint(18, 25))
    )

    current_gen = [(ancestor_id, ancestor_birth, "M"), (spouse_id, spouse_birth, "F")]
    total = 2

    for gen in range(2, num_generations + 1):
        next_gen = []
        # 每对夫妻(取当代中的M成员为父)生育子女
        males = [(mid, by) for mid, by, g in current_gen if g == "M"]
        females = [(mid, by) for mid, by, g in current_gen if g == "F"]

        for idx, (father_id, father_birth) in enumerate(males):
            # 找配偶
            if idx < len(females):
                mother_id, mother_birth = females[idx]
            else:
                # 生成外部配偶
                mother_birth = father_birth + random.randint(-5, 5)
                mother_id = insert_member(cursor, genealogy_id, rand_name("F"), "F", mother_birth, gen - 1)
                total += 1
                s1, s2 = min(father_id, mother_id), max(father_id, mother_id)
                cursor.execute(
                    "INSERT IGNORE INTO marriage(spouse1_id,spouse2_id,marriage_year) VALUES(%s,%s,%s)",
                    (s1, s2, max(father_birth, mother_birth) + random.randint(18, 28))
                )

            lo, hi = children_range_early if gen <= split_gen else children_range_late
            num_children = random.randint(lo, hi)
            for _ in range(num_children):
                child_gender = "M" if random.random() < 0.52 else "F"
                child_birth = gen_birth_year(father_birth, gen)
                child_id = insert_member(cursor, genealogy_id, rand_name(child_gender), child_gender, child_birth, gen)
                total += 1
                # 插入血缘关系(先确认父/母生年早于子)
                if father_birth < child_birth:
                    cursor.execute(
                        "INSERT IGNORE INTO parent_child(parent_id,child_id,relation_type) VALUES(%s,%s,'father')",
                        (father_id, child_id)
                    )
                if mother_birth < child_birth:
                    cursor.execute(
                        "INSERT IGNORE INTO parent_child(parent_id,child_id,relation_type) VALUES(%s,%s,'mother')",
                        (mother_id, child_id)
                    )
                next_gen.append((child_id, child_birth, child_gender))

        current_gen = next_gen
        if not current_gen:
            break

    return total

def insert_member(cursor, genealogy_id, name, gender, birth_year, generation) -> int:
    death_year = None
    if birth_year < (datetime.now().year - 60):
        if random.random() < 0.6:
            death_year = birth_year + random.randint(50, 95)
    cursor.execute(
        """INSERT INTO member(genealogy_id,name,gender,birth_year,death_year,generation)
           VALUES(%s,%s,%s,%s,%s,%s)""",
        (genealogy_id, name, gender, birth_year, death_year, generation)
    )
    return cursor.lastrowid

# ── 主程序 ───────────────────────────────────────────────────
def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("连接数据库成功")

    # 创建一个系统用户
    cursor.execute(
        "INSERT IGNORE INTO users(username,password_hash) VALUES('admin','$2b$12$placeholder_hash')"
    )
    conn.commit()
    cursor.execute("SELECT user_id FROM users WHERE username='admin'")
    admin_id = cursor.fetchone()[0]
    print(f"管理员用户 ID: {admin_id}")

    grand_total = 0
    BATCH_SIZE = 5000

    for i, (g_name, surname) in enumerate(GENEALOGY_NAMES):
        genealogy_idx = i + 1
        cursor.execute(
            """INSERT INTO genealogy(name,surname,revision_date,creator_id)
               VALUES(%s,%s,'2024-01-01',%s)""",
            (g_name, surname, admin_id)
        )
        conn.commit()
        genealogy_id = cursor.lastrowid
        cursor.execute(
            "INSERT IGNORE INTO genealogy_access(genealogy_id,user_id,role) VALUES(%s,%s,'owner')",
            (genealogy_id, admin_id)
        )

        if genealogy_idx == 1:
            # 大族谱：目标 60,000+ 成员，30代
            print(f"\n[{genealogy_idx}/12] 生成大族谱 '{g_name}' (目标 60,000+ 成员)...")
            count = generate_family(
                cursor, genealogy_id, surname,
                num_generations=30,
                children_range_early=(2, 3),
                children_range_late=(3, 5),
                split_gen=15,
                starting_birth_year=1200,
            )
        else:
            # 普通族谱：约 4,000 成员，30代
            print(f"\n[{genealogy_idx}/12] 生成族谱 '{g_name}' (目标 4,000+ 成员)...")
            count = generate_family(
                cursor, genealogy_id, surname,
                num_generations=30,
                children_range_early=(1, 2),
                children_range_late=(2, 3),
                split_gen=20,
                starting_birth_year=random.randint(1200, 1400),
            )

        conn.commit()
        grand_total += count
        print(f"  └─ 已生成 {count:,} 成员，累计 {grand_total:,}")

    cursor.close()
    conn.close()
    print(f"\n✅ 数据生成完成！总成员数: {grand_total:,}")

if __name__ == "__main__":
    main()

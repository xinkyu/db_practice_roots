"""
app.py — "寻根溯源" Flask 主应用
包含所有后端API路由，前端通过 templates/ 提供。
"""

from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for
)
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from collections import deque
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ── 数据库连接 ──────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(**config.DB_CONFIG)


def query(sql, params=(), fetchone=False, commit=False):
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        if commit:
            conn.commit()
            result = cur.lastrowid
        elif fetchone:
            result = cur.fetchone()
        else:
            result = cur.fetchall()
        cur.close()
        return result
    finally:
        conn.close()


# ── 全局异常处理（确保 API 始终返回 JSON）─────────────────────
@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    if request.path.startswith('/api/'):
        return jsonify({"error": str(e)}), 500
    raise e


def execute_many(sql, data_list):
    conn = get_db()
    cur = conn.cursor()
    cur.executemany(sql, data_list)
    conn.commit()
    cur.close()
    conn.close()


# ── 认证辅助 ───────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "未登录"}), 401
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════
# 页面路由
# ══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=session.get("username"))


@app.route("/genealogy/<int:gid>")
@login_required
def genealogy_page(gid):
    return render_template("genealogy.html")


@app.route("/member/<int:mid>")
@login_required
def member_page(mid):
    return render_template("member.html")


# ══════════════════════════════════════════════════════════════
# API: 认证
# ══════════════════════════════════════════════════════════════

@app.route("/api/auth/register", methods=["POST"])
def register():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "请求体不是合法 JSON"}), 400
        username = data.get("username", "").strip()
        password = data.get("password", "")
        if not username or not password:
            return jsonify({"error": "用户名和密码不能为空"}), 400
        existing = query("SELECT user_id FROM users WHERE username=%s", (username,), fetchone=True)
        if existing:
            return jsonify({"error": "用户名已存在"}), 409
        pw_hash = generate_password_hash(password)
        uid = query("INSERT INTO users(username,password_hash) VALUES(%s,%s)", (username, pw_hash), commit=True)
        session["user_id"] = uid
        session["username"] = username
        return jsonify({"user_id": uid, "username": username})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "请求体不是合法 JSON"}), 400
        username = data.get("username", "").strip()
        password = data.get("password", "")
        user = query("SELECT * FROM users WHERE username=%s", (username,), fetchone=True)
        if not user:
            return jsonify({"error": "用户名或密码错误"}), 401
        if not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "用户名或密码错误"}), 401
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        return jsonify({"user_id": user["user_id"], "username": user["username"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "已退出"})


@app.route("/api/auth/me")
def me():
    if "user_id" not in session:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "user_id": session["user_id"], "username": session["username"]})


# ══════════════════════════════════════════════════════════════
# API: 族谱
# ══════════════════════════════════════════════════════════════

@app.route("/api/genealogies", methods=["GET"])
@login_required
def list_genealogies():
    uid = session["user_id"]
    rows = query(
        """SELECT g.genealogy_id, g.name, g.surname, g.revision_date,
                  ga.role, u.username AS creator,
                  (SELECT COUNT(*) FROM member WHERE genealogy_id=g.genealogy_id) AS member_count
           FROM genealogy g
           JOIN genealogy_access ga ON ga.genealogy_id=g.genealogy_id AND ga.user_id=%s
           JOIN users u ON u.user_id=g.creator_id
           ORDER BY g.created_at DESC""",
        (uid,)
    )
    return jsonify(rows)


@app.route("/api/genealogies", methods=["POST"])
@login_required
def create_genealogy():
    data = request.get_json()
    uid = session["user_id"]
    name = data.get("name", "").strip()
    surname = data.get("surname", "").strip()
    revision_date = data.get("revision_date")
    if not name or not surname:
        return jsonify({"error": "谱名和姓氏不能为空"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO genealogy(name,surname,revision_date,creator_id) VALUES(%s,%s,%s,%s)",
        (name, surname, revision_date, uid)
    )
    gid = cur.lastrowid
    cur.execute(
        "INSERT INTO genealogy_access(genealogy_id,user_id,role) VALUES(%s,%s,'owner')",
        (gid, uid)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"genealogy_id": gid, "name": name})


@app.route("/api/genealogies/<int:gid>", methods=["GET"])
@login_required
def get_genealogy(gid):
    uid = session["user_id"]
    g = query(
        """SELECT g.*, ga.role FROM genealogy g
           JOIN genealogy_access ga ON ga.genealogy_id=g.genealogy_id
           WHERE g.genealogy_id=%s AND ga.user_id=%s""",
        (gid, uid), fetchone=True
    )
    if not g:
        return jsonify({"error": "族谱不存在或无权访问"}), 404
    return jsonify(g)


@app.route("/api/genealogies/<int:gid>", methods=["PUT"])
@login_required
def update_genealogy(gid):
    uid = session["user_id"]
    access = query(
        "SELECT role FROM genealogy_access WHERE genealogy_id=%s AND user_id=%s",
        (gid, uid), fetchone=True
    )
    if not access or access["role"] != "owner":
        return jsonify({"error": "无权限修改"}), 403
    data = request.get_json()
    query(
        "UPDATE genealogy SET name=%s, surname=%s, revision_date=%s WHERE genealogy_id=%s",
        (data.get("name"), data.get("surname"), data.get("revision_date"), gid), commit=True
    )
    return jsonify({"message": "更新成功"})


@app.route("/api/genealogies/<int:gid>", methods=["DELETE"])
@login_required
def delete_genealogy(gid):
    uid = session["user_id"]
    access = query(
        "SELECT role FROM genealogy_access WHERE genealogy_id=%s AND user_id=%s",
        (gid, uid), fetchone=True
    )
    if not access or access["role"] != "owner":
        return jsonify({"error": "无权限删除"}), 403
    query("DELETE FROM genealogy WHERE genealogy_id=%s", (gid,), commit=True)
    return jsonify({"message": "删除成功"})


@app.route("/api/genealogies/<int:gid>/invite", methods=["POST"])
@login_required
def invite_user(gid):
    uid = session["user_id"]
    access = query(
        "SELECT role FROM genealogy_access WHERE genealogy_id=%s AND user_id=%s",
        (gid, uid), fetchone=True
    )
    if not access or access["role"] != "owner":
        return jsonify({"error": "只有所有者可以邀请"}), 403
    data = request.get_json()
    target = query("SELECT user_id FROM users WHERE username=%s", (data.get("username"),), fetchone=True)
    if not target:
        return jsonify({"error": "用户不存在"}), 404
    query(
        "INSERT IGNORE INTO genealogy_access(genealogy_id,user_id,role) VALUES(%s,%s,'editor')",
        (gid, target["user_id"]), commit=True
    )
    return jsonify({"message": f"已邀请 {data.get('username')}"})


@app.route("/api/genealogies/<int:gid>/dashboard")
@login_required
def family_dashboard(gid):
    uid = session["user_id"]
    access = query(
        "SELECT 1 FROM genealogy_access WHERE genealogy_id=%s AND user_id=%s",
        (gid, uid), fetchone=True
    )
    if not access:
        return jsonify({"error": "无权访问"}), 403
    stats = query(
        """SELECT
               COUNT(*) AS total,
               SUM(gender='M') AS male_count,
               SUM(gender='F') AS female_count,
               MAX(generation)  AS max_generation,
               MIN(birth_year)  AS earliest_birth
           FROM member WHERE genealogy_id=%s""",
        (gid,), fetchone=True
    )
    return jsonify(stats)


# ══════════════════════════════════════════════════════════════
# API: 成员
# ══════════════════════════════════════════════════════════════

@app.route("/api/genealogies/<int:gid>/members", methods=["GET"])
@login_required
def list_members(gid):
    uid = session["user_id"]
    access = query(
        "SELECT 1 FROM genealogy_access WHERE genealogy_id=%s AND user_id=%s",
        (gid, uid), fetchone=True
    )
    if not access:
        return jsonify({"error": "无权访问"}), 403
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    offset = (page - 1) * per_page
    rows = query(
        """SELECT member_id, name, gender, birth_year, death_year, generation
           FROM member WHERE genealogy_id=%s
           ORDER BY generation, member_id
           LIMIT %s OFFSET %s""",
        (gid, per_page, offset)
    )
    total = query(
        "SELECT COUNT(*) AS cnt FROM member WHERE genealogy_id=%s",
        (gid,), fetchone=True
    )["cnt"]
    return jsonify({"members": rows, "total": total, "page": page, "per_page": per_page})


@app.route("/api/genealogies/<int:gid>/members", methods=["POST"])
@login_required
def add_member(gid):
    uid = session["user_id"]
    access = query(
        "SELECT 1 FROM genealogy_access WHERE genealogy_id=%s AND user_id=%s",
        (gid, uid), fetchone=True
    )
    if not access:
        return jsonify({"error": "无权操作"}), 403
    data = request.get_json()
    name = data.get("name", "").strip()
    gender = data.get("gender")
    if not name or gender not in ("M", "F"):
        return jsonify({"error": "姓名和性别为必填项"}), 400
    mid = query(
        """INSERT INTO member(genealogy_id,name,gender,birth_year,death_year,biography,generation)
           VALUES(%s,%s,%s,%s,%s,%s,%s)""",
        (gid, name, gender, data.get("birth_year"), data.get("death_year"),
         data.get("biography"), data.get("generation", 1)),
        commit=True
    )
    return jsonify({"member_id": mid, "name": name})


@app.route("/api/members/<int:mid>", methods=["GET"])
@login_required
def get_member(mid):
    uid = session["user_id"]
    m = query(
        """SELECT m.*, g.name AS genealogy_name FROM member m
           JOIN genealogy g ON g.genealogy_id=m.genealogy_id
           JOIN genealogy_access ga ON ga.genealogy_id=m.genealogy_id AND ga.user_id=%s
           WHERE m.member_id=%s""",
        (uid, mid), fetchone=True
    )
    if not m:
        return jsonify({"error": "成员不存在或无权访问"}), 404
    return jsonify(m)


@app.route("/api/members/<int:mid>", methods=["PUT"])
@login_required
def update_member(mid):
    uid = session["user_id"]
    access = query(
        """SELECT 1 FROM member m
           JOIN genealogy_access ga ON ga.genealogy_id=m.genealogy_id AND ga.user_id=%s
           WHERE m.member_id=%s""",
        (uid, mid), fetchone=True
    )
    if not access:
        return jsonify({"error": "无权操作"}), 403
    data = request.get_json()
    query(
        """UPDATE member SET name=%s,gender=%s,birth_year=%s,death_year=%s,
           biography=%s,generation=%s WHERE member_id=%s""",
        (data.get("name"), data.get("gender"), data.get("birth_year"),
         data.get("death_year"), data.get("biography"), data.get("generation"), mid),
        commit=True
    )
    return jsonify({"message": "更新成功"})


@app.route("/api/members/<int:mid>", methods=["DELETE"])
@login_required
def delete_member(mid):
    uid = session["user_id"]
    access = query(
        """SELECT 1 FROM member m
           JOIN genealogy_access ga ON ga.genealogy_id=m.genealogy_id AND ga.user_id=%s
           WHERE m.member_id=%s""",
        (uid, mid), fetchone=True
    )
    if not access:
        return jsonify({"error": "无权操作"}), 403
    query("DELETE FROM member WHERE member_id=%s", (mid,), commit=True)
    return jsonify({"message": "删除成功"})


@app.route("/api/members/search")
@login_required
def search_members():
    uid = session["user_id"]
    name = request.args.get("name", "").strip()
    gid = request.args.get("genealogy_id")
    if not name:
        return jsonify([])
    params = [uid, f"%{name}%"]
    gid_clause = ""
    if gid:
        gid_clause = "AND m.genealogy_id=%s"
        params.append(int(gid))
    rows = query(
        f"""SELECT m.member_id, m.name, m.gender, m.birth_year, m.generation,
                   g.name AS genealogy_name
            FROM member m
            JOIN genealogy g ON g.genealogy_id=m.genealogy_id
            JOIN genealogy_access ga ON ga.genealogy_id=m.genealogy_id AND ga.user_id=%s
            WHERE m.name LIKE %s {gid_clause}
            LIMIT 50""",
        params
    )
    return jsonify(rows)


# ── 获取某成员的后代树 (向下) ────────────────────────────────
@app.route("/api/members/<int:mid>/tree")
@login_required
def member_tree(mid):
    """返回以 mid 为根的后代树，最多 depth 层（默认5）"""
    depth = int(request.args.get("depth", 5))

    def get_children(parent_id):
        return query(
            """SELECT m.member_id, m.name, m.gender, m.birth_year, m.generation
               FROM member m
               JOIN parent_child pc ON pc.child_id=m.member_id AND pc.parent_id=%s
               GROUP BY m.member_id""",
            (parent_id,)
        )

    def build_tree(node_id, current_depth):
        if current_depth > depth:
            return None
        m = query(
            "SELECT member_id,name,gender,birth_year,generation FROM member WHERE member_id=%s",
            (node_id,), fetchone=True
        )
        if not m:
            return None
        children = get_children(node_id)
        m["children"] = [build_tree(c["member_id"], current_depth + 1) for c in children]
        m["children"] = [c for c in m["children"] if c]
        return m

    tree = build_tree(mid, 1)
    return jsonify(tree)


# ── 祖先树 (向上递归) ────────────────────────────────────────
@app.route("/api/members/<int:mid>/ancestors")
@login_required
def member_ancestors(mid):
    """返回向上追溯的祖先列表（平铺，带 depth 和 path）"""
    result = []
    visited = set()
    queue = deque([(mid, 0, [])])
    while queue:
        curr_id, depth, path = queue.popleft()
        if curr_id in visited or depth > 50:
            continue
        visited.add(curr_id)
        m = query(
            "SELECT member_id,name,gender,birth_year,generation FROM member WHERE member_id=%s",
            (curr_id,), fetchone=True
        )
        if not m:
            continue
        m["depth"] = depth
        m["path"] = path + [m["name"]]
        result.append(m)
        parents = query(
            """SELECT p.member_id,p.name,p.gender,p.birth_year,p.generation,pc.relation_type
               FROM parent_child pc
               JOIN member p ON p.member_id=pc.parent_id
               WHERE pc.child_id=%s""",
            (curr_id,)
        )
        for p in parents:
            queue.append((p["member_id"], depth + 1, m["path"]))
    return jsonify(result)


# ── 亲缘关系路径 (BFS双向图) ─────────────────────────────────
@app.route("/api/members/kinship")
@login_required
def kinship():
    id1 = request.args.get("id1", type=int)
    id2 = request.args.get("id2", type=int)
    if not id1 or not id2:
        return jsonify({"error": "请提供两个成员ID"}), 400
    if id1 == id2:
        return jsonify({"path": [id1], "related": True})

    def get_neighbors(mid):
        """返回所有与 mid 有血缘或婚姻关系的成员ID"""
        rows = query(
            """SELECT pc.parent_id AS nid FROM parent_child pc WHERE pc.child_id=%s
               UNION
               SELECT pc.child_id  AS nid FROM parent_child pc WHERE pc.parent_id=%s
               UNION
               SELECT mr.spouse2_id AS nid FROM marriage mr WHERE mr.spouse1_id=%s
               UNION
               SELECT mr.spouse1_id AS nid FROM marriage mr WHERE mr.spouse2_id=%s""",
            (mid, mid, mid, mid)
        )
        return [r["nid"] for r in rows]

    # BFS
    visited = {id1: None}
    queue = deque([id1])
    found = False
    while queue:
        curr = queue.popleft()
        if curr == id2:
            found = True
            break
        for nb in get_neighbors(curr):
            if nb not in visited:
                visited[nb] = curr
                queue.append(nb)

    if not found:
        return jsonify({"related": False, "path": []})

    # 回溯路径
    path = []
    node = id2
    while node is not None:
        m = query("SELECT member_id,name,gender FROM member WHERE member_id=%s", (node,), fetchone=True)
        path.append(m)
        node = visited[node]
    path.reverse()
    return jsonify({"related": True, "path": path})



# ══════════════════════════════════════════════════════════════
# API: 关系管理 (血缘 & 婚姻)
# ══════════════════════════════════════════════════════════════

def _check_member_access(uid, mid):
    """返回成员所在族谱的 genealogy_id，若无权限返回 None"""
    row = query(
        """SELECT m.genealogy_id FROM member m
           JOIN genealogy_access ga ON ga.genealogy_id=m.genealogy_id AND ga.user_id=%s
           WHERE m.member_id=%s""",
        (uid, mid), fetchone=True
    )
    return row["genealogy_id"] if row else None


@app.route("/api/members/<int:mid>/relations")
@login_required
def get_relations(mid):
    """获取某成员的所有关系：父母、子女、配偶"""
    uid = session["user_id"]
    if not _check_member_access(uid, mid):
        return jsonify({"error": "无权访问"}), 403

    parents = query(
        """SELECT p.member_id, p.name, p.gender, p.birth_year, p.generation,
                  pc.relation_type
           FROM parent_child pc
           JOIN member p ON p.member_id=pc.parent_id
           WHERE pc.child_id=%s""",
        (mid,)
    )
    children = query(
        """SELECT c.member_id, c.name, c.gender, c.birth_year, c.generation,
                  pc.relation_type
           FROM parent_child pc
           JOIN member c ON c.member_id=pc.child_id
           WHERE pc.parent_id=%s""",
        (mid,)
    )
    spouses = query(
        """SELECT m2.member_id, m2.name, m2.gender, m2.birth_year, m2.generation,
                  mr.marriage_year
           FROM marriage mr
           JOIN member m2 ON m2.member_id = CASE
               WHEN mr.spouse1_id=%s THEN mr.spouse2_id
               ELSE mr.spouse1_id END
           WHERE mr.spouse1_id=%s OR mr.spouse2_id=%s""",
        (mid, mid, mid)
    )
    return jsonify({"parents": parents, "children": children, "spouses": spouses})


@app.route("/api/members/<int:mid>/parents", methods=["POST"])
@login_required
def add_parent(mid):
    """为成员 mid 添加父母（parent_id 必须与 mid 在同一族谱）"""
    uid = session["user_id"]
    gid = _check_member_access(uid, mid)
    if not gid:
        return jsonify({"error": "无权操作"}), 403
    try:
        data = request.get_json(force=True)
        parent_id = int(data.get("parent_id", 0))
        relation_type = data.get("relation_type", "father")
        if relation_type not in ("father", "mother"):
            return jsonify({"error": "relation_type 必须是 father 或 mother"}), 400
        if parent_id == mid:
            return jsonify({"error": "不能将自己设为父母"}), 400
        # 校验 parent_id 存在且在同族谱
        p = query("SELECT member_id, birth_year FROM member WHERE member_id=%s AND genealogy_id=%s",
                  (parent_id, gid), fetchone=True)
        if not p:
            return jsonify({"error": f"父母 ID {parent_id} 不存在或不在同一族谱"}), 404
        # 检查性别与 relation_type 一致性
        pg = query("SELECT gender FROM member WHERE member_id=%s", (parent_id,), fetchone=True)
        if (relation_type == "father" and pg["gender"] != "M") or \
           (relation_type == "mother" and pg["gender"] != "F"):
            return jsonify({"error": "父亲必须为男性，母亲必须为女性"}), 400
        query(
            "INSERT IGNORE INTO parent_child(parent_id,child_id,relation_type) VALUES(%s,%s,%s)",
            (parent_id, mid, relation_type), commit=True
        )
        return jsonify({"message": "父母关系添加成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/members/<int:mid>/parents/<int:parent_id>", methods=["DELETE"])
@login_required
def remove_parent(mid, parent_id):
    uid = session["user_id"]
    if not _check_member_access(uid, mid):
        return jsonify({"error": "无权操作"}), 403
    query("DELETE FROM parent_child WHERE parent_id=%s AND child_id=%s", (parent_id, mid), commit=True)
    return jsonify({"message": "已移除父母关系"})


@app.route("/api/members/<int:mid>/children", methods=["POST"])
@login_required
def add_child(mid):
    """为成员 mid 添加子女"""
    uid = session["user_id"]
    gid = _check_member_access(uid, mid)
    if not gid:
        return jsonify({"error": "无权操作"}), 403
    try:
        data = request.get_json(force=True)
        child_id = int(data.get("child_id", 0))
        if child_id == mid:
            return jsonify({"error": "不能将自己设为子女"}), 400
        c = query("SELECT member_id FROM member WHERE member_id=%s AND genealogy_id=%s",
                  (child_id, gid), fetchone=True)
        if not c:
            return jsonify({"error": f"子女 ID {child_id} 不存在或不在同一族谱"}), 404
        # 根据 mid 性别决定 relation_type
        self_gender = query("SELECT gender FROM member WHERE member_id=%s", (mid,), fetchone=True)
        relation_type = "father" if self_gender["gender"] == "M" else "mother"
        query(
            "INSERT IGNORE INTO parent_child(parent_id,child_id,relation_type) VALUES(%s,%s,%s)",
            (mid, child_id, relation_type), commit=True
        )
        return jsonify({"message": "子女关系添加成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/members/<int:mid>/children/<int:child_id>", methods=["DELETE"])
@login_required
def remove_child(mid, child_id):
    uid = session["user_id"]
    if not _check_member_access(uid, mid):
        return jsonify({"error": "无权操作"}), 403
    query("DELETE FROM parent_child WHERE parent_id=%s AND child_id=%s", (mid, child_id), commit=True)
    return jsonify({"message": "已移除子女关系"})


@app.route("/api/members/<int:mid>/spouse", methods=["POST"])
@login_required
def add_spouse(mid):
    """为成员 mid 添加配偶"""
    uid = session["user_id"]
    gid = _check_member_access(uid, mid)
    if not gid:
        return jsonify({"error": "无权操作"}), 403
    try:
        data = request.get_json(force=True)
        spouse_id = int(data.get("spouse_id", 0))
        if spouse_id == mid:
            return jsonify({"error": "不能将自己设为配偶"}), 400
        s = query("SELECT member_id FROM member WHERE member_id=%s AND genealogy_id=%s",
                  (spouse_id, gid), fetchone=True)
        if not s:
            return jsonify({"error": f"配偶 ID {spouse_id} 不存在或不在同一族谱"}), 404
        s1, s2 = min(mid, spouse_id), max(mid, spouse_id)
        marriage_year = data.get("marriage_year")
        query(
            "INSERT IGNORE INTO marriage(spouse1_id,spouse2_id,marriage_year) VALUES(%s,%s,%s)",
            (s1, s2, marriage_year), commit=True
        )
        return jsonify({"message": "婚姻关系添加成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/members/<int:mid>/spouse/<int:spouse_id>", methods=["DELETE"])
@login_required
def remove_spouse(mid, spouse_id):
    uid = session["user_id"]
    if not _check_member_access(uid, mid):
        return jsonify({"error": "无权操作"}), 403
    s1, s2 = min(mid, spouse_id), max(mid, spouse_id)
    query("DELETE FROM marriage WHERE spouse1_id=%s AND spouse2_id=%s", (s1, s2), commit=True)
    return jsonify({"message": "已移除婚姻关系"})


# ══════════════════════════════════════════════════════════════
# 启动
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)

from database import get_db, init_db

import sqlite3


# =========================================================
# 查詢使用者
# =========================================================
def get_user(line_user_id):

    conn = get_db()

    user = conn.execute(
        """
        SELECT

            u.user_id,
            u.line_user_id,

            p.name,
            p.department_grade,
            p.student_id,
            p.created_at,
            p.updated_at

        FROM users u

        LEFT JOIN user_profiles p
            ON u.user_id = p.user_id

        WHERE u.line_user_id = ?

        """,
        (line_user_id,)
    ).fetchone()

    conn.close()

    return user


# =========================================================
# 第一次建立資料
# =========================================================
def register_user(line_user_id):

    print()
    print("==============================")
    print("       第一次使用系統")
    print("==============================")
    print()

    while True:

        name = input(
            "請輸入姓名："
        ).strip()

        department_grade = input(
            "請輸入系級："
        ).strip()

        student_id = input(
            "請輸入學號："
        ).strip()

        # -----------------------------
        # 不允許空白
        # -----------------------------
        if not name:

            print("❌ 姓名不可為空白")
            continue

        if not student_id:

            print("❌ 學號不可為空白")
            continue

        # -----------------------------
        # 確認資料
        # -----------------------------
        print()
        print("==============================")
        print("請確認個人資料")
        print("==============================")

        print("姓名：", name)
        print("系級：", department_grade)
        print("學號：", student_id)

        print("==============================")

        print("1. 確認")
        print("2. 重新輸入")

        choice = input(
            "請選擇："
        ).strip()

        if choice == "2":

            continue

        if choice != "1":

            print("請輸入 1 或 2")
            continue

        # -----------------------------
        # 寫入資料庫
        # -----------------------------
        conn = get_db()

        try:

            cursor = conn.execute(
                """
                INSERT INTO users
                (
                    line_user_id
                )
                VALUES (?)
                """,
                (
                    line_user_id,
                )
            )

            user_id = cursor.lastrowid

            conn.execute(
                """
                INSERT INTO user_profiles
                (
                    user_id,
                    name,
                    department_grade,
                    student_id
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    name,
                    department_grade,
                    student_id
                )
            )

            conn.commit()

            print()
            print("✅ 個人資料建立完成")
            print()

        except sqlite3.IntegrityError as e:

            conn.rollback()

            print()
            print("❌ 建立失敗")

            if "student_id" in str(e):

                print(
                    "此學號已經被使用"
                )

            else:

                print(e)

        finally:

            conn.close()

        return


# =========================================================
# 顯示個人資料
# =========================================================
def show_profile(user):

    print()
    print("==============================")
    print("          個人資料")
    print("==============================")

    print(
        "姓名：",
        user["name"]
    )

    print(
        "系級：",
        user["department_grade"]
        or "未填寫"
    )

    print(
        "學號：",
        user["student_id"]
        or "未填寫"
    )

    print("==============================")
    print()


# =========================================================
# 修改姓名
# =========================================================
def update_name(user_id):

    new_name = input(
        "請輸入新的姓名："
    ).strip()

    if not new_name:

        print("❌ 姓名不可為空白")

        return

    conn = get_db()

    conn.execute(
        """
        UPDATE user_profiles

        SET
            name = ?,
            updated_at = CURRENT_TIMESTAMP

        WHERE user_id = ?
        """,
        (
            new_name,
            user_id
        )
    )

    conn.commit()

    conn.close()

    print()
    print("✅ 姓名修改完成")
    print()


# =========================================================
# 修改系級
# =========================================================
def update_department_grade(user_id):

    new_value = input(
        "請輸入新的系級："
    ).strip()

    conn = get_db()

    conn.execute(
        """
        UPDATE user_profiles

        SET
            department_grade = ?,
            updated_at = CURRENT_TIMESTAMP

        WHERE user_id = ?
        """,
        (
            new_value,
            user_id
        )
    )

    conn.commit()

    conn.close()

    print()
    print("✅ 系級修改完成")
    print()


# =========================================================
# 修改學號
# =========================================================
def update_student_id(user_id):

    new_student_id = input(
        "請輸入新的學號："
    ).strip()

    if not new_student_id:

        print("❌ 學號不可為空白")

        return

    conn = get_db()

    try:

        conn.execute(
            """
            UPDATE user_profiles

            SET
                student_id = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE user_id = ?
            """,
            (
                new_student_id,
                user_id
            )
        )

        conn.commit()

        print()
        print("✅ 學號修改完成")
        print()

    except sqlite3.IntegrityError:

        conn.rollback()

        print()
        print("❌ 此學號已被其他使用者使用")
        print()

    finally:

        conn.close()


# =========================================================
# 修改個人資料
# =========================================================
def edit_profile(line_user_id):

    while True:

        user = get_user(
            line_user_id
        )

        show_profile(
            user
        )

        print("要修改哪一項？")

        print("1. 姓名")
        print("2. 系級")
        print("3. 學號")
        print("4. 回上一頁")

        choice = input(
            "請選擇："
        ).strip()

        if choice == "1":

            update_name(
                user["user_id"]
            )

        elif choice == "2":

            update_department_grade(
                user["user_id"]
            )

        elif choice == "3":

            update_student_id(
                user["user_id"]
            )

        elif choice == "4":

            break

        else:

            print(
                "❌ 請輸入 1～4"
            )


# =========================================================
# 登入後主選單
# =========================================================
def main_menu(line_user_id):

    while True:

        user = get_user(
            line_user_id
        )

        print()
        print("==============================")

        print(
            f"歡迎回來，{user['name']}"
        )

        print("==============================")

        print("1. 查看個人資料")
        print("2. 修改個人資料")
        print("3. 登出")

        print()

        choice = input(
            "請選擇功能："
        ).strip()

        if choice == "1":

            show_profile(
                user
            )

        elif choice == "2":

            edit_profile(
                line_user_id
            )

        elif choice == "3":

            print()
            print("👋 已登出")
            print()

            break

        else:

            print(
                "❌ 請輸入 1～3"
            )


# =========================================================
# 系統開始
# =========================================================
def start():

    # 建立資料表
    init_db()

    print()
    print("==============================")
    print("      LINE Bot 模擬系統")
    print("==============================")

    # 現在先人工輸入
    #
    # 未來真正 LINE Bot：
    #
    # line_user_id =
    # event.source.user_id

    line_user_id = input(
        "請輸入模擬 LINE User ID："
    ).strip()

    user = get_user(
        line_user_id
    )

    # -----------------------------
    # 第一次使用
    # -----------------------------
    if user is None:

        register_user(
            line_user_id
        )

    # -----------------------------
    # 已有資料
    # -----------------------------
    main_menu(
        line_user_id
    )


# =========================================================
# 執行
# =========================================================
if __name__ == "__main__":

    start()

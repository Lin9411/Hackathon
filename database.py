import sqlite3


DB_PATH = "checkin.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)

    # 查詢結果可以用 row["name"] 方式取得
    conn.row_factory = sqlite3.Row

    # SQLite 預設 Foreign Key 沒有一定開啟
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db():
    conn = get_db()

    with open("schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    conn.executescript(sql)

    conn.commit()
    conn.close()

    print("✅ 資料庫建立完成：checkin.db")


if __name__ == "__main__":
    init_db()

from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from database import get_db

app = FastAPI()

# --- LINE Bot 金鑰設定 (請替換為你的真實金鑰) ---
LINE_CHANNEL_ACCESS_TOKEN = "eD9JUYDPTuLwpFqWNk+NlYtrbJuvmglaAHCi5KnTT0xIfzb7MRZivr5q4giQ50mJutmpyj8Ai9FkC/5FBoq1kVrYIkqaMWj4PhxKFsBm5N0IbK1RTuV6I60qiz/+oAonD5t5vmfBiiMnBjK4aQzMUAdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "f12694a0d63b98bd54370d8b6c150965"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# LINE 官方伺服器發送訊息過來的接收端點
# LINE 官方伺服器發送訊息過來的接收端點
@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_text = body.decode("utf-8")

    # 如果沒有簽章（例如瀏覽器直接打網址或特殊探測），直接回傳 OK
    if not signature:
        return "OK"

    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        # 若為 LINE 後台點擊 Verify，有時驗證要求較嚴格，印出警告但不卡死
        print("--> [警告] 簽章驗證失敗 (可能是 LINE Verify 測試或 Channel Secret 填錯)")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        print(f"--> [Webhook 處理錯誤]: {e}")
        return "OK"

    return "OK"
# 處理文字訊息的核心邏輯
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_text = event.message.text.strip()
    line_uid = event.source.user_id

    conn = get_db()
    cursor = conn.cursor()

    try:
        # 1. 查詢此 LINE UID 是否已經登記過
        cursor.execute("SELECT user_id FROM users WHERE line_user_id = ?", (line_uid,))
        existing_user = cursor.fetchone()

        if existing_user:
            user_id = existing_user["user_id"]
            cursor.execute("SELECT name, department_grade, student_id FROM user_profiles WHERE user_id = ?", (user_id,))
            profile = cursor.fetchone()

            if profile:
                # 已經綁定過身分
                reply = (
                    f"您好，{profile['name']} 同學！\n"
                    f"您已經完成身分綁定了，無法重複登記。\n"
                    f"（登記資料：{profile['department_grade']} / 學號：{profile['student_id']}）"
                )
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
                return

        # 2. 判斷格式：是否符合「學號/姓名/系級」或「學號 姓名 系級」
        # 同時相容斜線「/」或空白「 」做分隔
        delimiter = "/" if "/" in user_text else (" " if " " in user_text else None)

        if not delimiter:
            reply = (
                "👋 歡迎使用校園簽到系統！\n\n"
                "您尚未完成身分綁定，請依照以下格式回覆以完成登記：\n"
                "👉 學號/姓名/系級\n\n"
                "範例：\n"
                "12345678/王小明/資管三A"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        parts = [p.strip() for p in user_text.split(delimiter) if p.strip()]

        if len(parts) != 3:
            reply = (
                "⚠️ 輸入格式不完整！請輸入三項資料：\n"
                "👉 學號/姓名/系級\n\n"
                "範例：12345678/王小明/資管三A"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        student_id, name, department_grade = parts

        # 3. 檢查學號是否已被其他人綁定
        cursor.execute("SELECT user_id FROM user_profiles WHERE student_id = ?", (student_id,))
        if cursor.fetchone():
            reply = f"❌ 學號 {student_id} 已經被其他 LINE 帳號登記過囉！若有疑問請洽管理員。"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        # 4. 寫入 users 資料表
        cursor.execute("""
            INSERT INTO users (line_user_id)
            VALUES (?)
            ON CONFLICT(line_user_id) DO NOTHING
        """, (line_uid,))

        cursor.execute("SELECT user_id FROM users WHERE line_user_id = ?", (line_uid,))
        user_id = cursor.fetchone()["user_id"]

        # 5. 寫入 user_profiles 資料表
        cursor.execute("""
            INSERT INTO user_profiles (user_id, name, department_grade, student_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, department_grade, student_id))

        conn.commit()

        print(f"\n[身分登記成功] LINE UID: {line_uid} -> {name} ({student_id}, {department_grade})\n")

        reply = (
            f"🎉 身分登記成功！\n\n"
            f"姓名：{name}\n"
            f"學號：{student_id}\n"
            f"系級：{department_grade}\n\n"
            f"未來參加校園活動時，出示或掃描簽到碼即可自動完成簽到！"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    except Exception as e:
        conn.rollback()
        print(f"--> [資料庫錯誤]: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="系統繁忙，請稍後再試。"))
    finally:
        conn.close()
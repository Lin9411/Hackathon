import os
from pathlib import Path

import pandas as pd

from google import genai
from google.genai import types

from pydantic import BaseModel, Field
from typing import Optional, List

from dotenv import load_dotenv
from PIL import Image


# =========================================================
# 讀取 API KEY
# =========================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")


if not API_KEY:
    raise ValueError(
        "找不到 GEMINI_API_KEY，請確認 .env 是否設定"
    )


client = genai.Client(
    api_key=API_KEY
)


# =========================================================
# Gemini 輸出格式
# =========================================================

class Participant(BaseModel):

    name: Optional[str] = Field(
        default=None,
        description="參加者姓名"
    )

    student_id: Optional[str] = Field(
        default=None,
        description="參加者學號或識別編號"
    )

    department_grade: Optional[str] = Field(
        default=None,
        description="系所與年級，例如資料科學系二年級"
    )


class ParticipantList(BaseModel):

    participants: List[Participant]


# =========================================================
# 共用 Prompt
# =========================================================

PROMPT = """
你是一個活動參加者名單資料整理工具。

請分析我提供的參加者名單，
擷取所有參加者資料。

需要的欄位：

1. name：姓名
2. student_id：學號或識別編號
3. department_grade：系所與年級

規則：

1. 一位參加者只能產生一筆資料。
2. 不要把表格標題當成參加者。
3. 不得自行創造資料。
4. 無法辨識的欄位請設為 null。
5. 學號必須保留原始格式。
6. 姓名必須保留原始文字。
7. 如果「系所」與「年級」為兩個欄位，
   請合併成 department_grade。

例如：

系所：資料科學系
年級：二年級

應整理成：

department_grade = 資料科學系二年級

8. 如果只有系所、沒有年級，
   department_grade 就只填系所。
9. 不確定的內容不要猜。
10. 請處理所有參加者，不要省略。
"""


# =========================================================
# Gemini 結構化輸出
# =========================================================

import time

def ask_gemini(contents):
    # 若 3.8-flash 尖峰塞車 (503)，自動切換備用模型
    models_to_try = ["gemini-3.8-flash", "gemini-3.8-pro"]
    last_exception = None

    for model_name in models_to_try:
        try:
            print(f"--> 嘗試使用模型 {model_name} 辨識中...")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ParticipantList.model_json_schema(),
                    temperature=0.1
                )
            )

            result = ParticipantList.model_validate_json(
                response.text
            )
            return result.participants

        except Exception as e:
            last_exception = e
            print(f"⚠️ 模型 {model_name} 回應忙碌，準備切換備用方案... ({e})")
            time.sleep(1)

    raise last_exception

# =========================================================
# Excel → 文字
# =========================================================

def read_excel_as_text(file_path):

    # sheet_name=None
    # = 一次讀取所有工作表
    sheets = pd.read_excel(
        file_path,
        sheet_name=None,
        dtype=str
    )

    all_text = []

    for sheet_name, df in sheets.items():

        # 全空白列刪掉
        df = df.dropna(
            how="all"
        )

        # NaN 改成空字串
        df = df.fillna("")

        all_text.append(
            f"\n===== 工作表：{sheet_name} =====\n"
        )

        # 轉成 CSV 型式文字
        all_text.append(
            df.to_csv(
                index=False
            )
        )

    return "\n".join(
        all_text
    )


# =========================================================
# Excel 辨識
# =========================================================

def recognize_excel(file_path):

    print()
    print("正在讀取 Excel...")
    print()

    excel_text = read_excel_as_text(
        file_path
    )

    print("✅ Excel 讀取完成")
    print("正在送給 Gemini 整理...")
    print()

    contents = f"""
{PROMPT}

以下為 Excel 讀取後的內容：

------------------------------

{excel_text}

------------------------------
"""

    return ask_gemini(
        contents
    )


# =========================================================
# PDF / 圖片辨識
# =========================================================

def recognize_file_with_gemini(file_path):
    extension = Path(file_path).suffix.lower()

    # 如果是圖片，直接用 PIL 開啟傳送，避開 Windows 中文檔名上傳 bug
    if extension in [".png", ".jpg", ".jpeg"]:
        print()
        print("正在載入圖片...")
        img = Image.open(file_path)
        print("✅ 圖片載入完成，正在送給 Gemini 辨識...")
        print()
        return ask_gemini([PROMPT, img])

    # 如果是 PDF 檔案，才使用上傳 API
    print()
    print("正在上傳檔案至 Gemini...")
    print()

    uploaded_file = client.files.upload(
        file=file_path
    )

    print("✅ 檔案上傳完成")
    print("正在辨識參加者資料...")
    print()

    return ask_gemini(
        [
            PROMPT,
            uploaded_file
        ]
    )


# =========================================================
# 主辨識函式
# =========================================================

def recognize_participants(file_path):

    # -----------------------------------------------------
    # 去除使用者貼上的引號
    #
    # 'xxx.xlsx'
    # "xxx.xlsx"
    #
    # 都會變成：
    #
    # xxx.xlsx
    # -----------------------------------------------------

    file_path = file_path.strip()

    file_path = file_path.strip(
        "'\""
    )

    # 支援 ~/Downloads/xxx.xlsx
    file_path = os.path.expanduser(
        file_path
    )

    # 轉成完整路徑
    file_path = os.path.abspath(
        file_path
    )

    print()
    print(
        "實際讀取路徑：",
        file_path
    )
    print()

    # -----------------------------------------------------
    # 檢查檔案
    # -----------------------------------------------------

    if not os.path.exists(
        file_path
    ):

        return {
            "success": False,
            "message":
                f"找不到指定檔案：{file_path}"
        }

    extension = Path(
        file_path
    ).suffix.lower()

    try:

        # =================================================
        # Excel
        # =================================================

        if extension == ".xlsx":

            participants = recognize_excel(
                file_path
            )

        # =================================================
        # PDF / 圖片
        # =================================================

        elif extension in [
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg"
        ]:

            participants = (
                recognize_file_with_gemini(
                    file_path
                )
            )

        # =================================================
        # 不支援
        # =================================================

        else:

            return {
                "success": False,

                "message":
                    f"目前不支援此格式：{extension}"
            }

        return {
            "success": True,

            "participants":
                participants
        }

    except Exception as e:

        return {
            "success": False,

            "message":
                str(e)
        }

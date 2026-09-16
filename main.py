from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
import json
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conn = sqlite3.connect('finance.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        tien_mat INTEGER,
        tien_tk INTEGER
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        loai TEXT,
        nguon TEXT,
        so_tien INTEGER,
        ly_do TEXT
    )
''')
conn.commit()

def get_so_du(username):
    cursor.execute('SELECT tien_mat, tien_tk FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    if row:
        return {"tien_mat": row[0], "tien_tk": row[1]}
    return None

def save_so_du(tien_mat, tien_tk, username):
    cursor.execute('UPDATE users SET tien_mat = ?, tien_tk = ? WHERE username = ?', (tien_mat, tien_tk, username))
    conn.commit()

def get_history(username):
    cursor.execute('SELECT loai, nguon, so_tien, ly_do FROM transactions WHERE username = ? ORDER BY id DESC', (username,))
    return cursor.fetchall()

API_KEY = "GEMINI_API_KEY"
client = genai.Client(api_key=API_KEY)

system_prompt = "Bạn là trợ lý tài chính. Người dùng nhập khoản thu/chi. Chỉ trả về dữ liệu chuẩn JSON, không bọc trong markdown. Cấu trúc: {\"loai_giao_dich\": \"chi\" hoặc \"thu\", \"nguon_tien\": \"tien_mat\" hoặc \"tien_tk\", \"so_tien\": số nguyên, \"ly_do\": \"Mô tả ngắn\"}. Nếu không hiểu, trả về: {\"error\": \"Không hiểu giao dịch\"}"

class UserAuth(BaseModel):
    username: str
    password: str

class InitBalance(BaseModel):
    username: str
    tien_mat: int
    tien_tk: int

class UserMessage(BaseModel):
    username: str
    message: str

@app.post("/api/register")
async def register(data: UserAuth):
    cursor.execute('SELECT * FROM users WHERE username = ?', (data.username,))
    if cursor.fetchone():
        return {"success": False, "message": "Tên tài khoản đã tồn tại!"}
    cursor.execute('INSERT INTO users (username, password, tien_mat, tien_tk) VALUES (?, ?, 0, 0)', (data.username, data.password))
    conn.commit()
    return {"success": True, "message": "Đăng ký thành công!"}

@app.post("/api/login")
async def login(data: UserAuth):
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (data.username, data.password))
    user = cursor.fetchone()
    if user:
        is_new = (user[2] == 0 and user[3] == 0)
        return {"success": True, "is_new": is_new, "so_du": {"tien_mat": user[2], "tien_tk": user[3]}, "history": get_history(data.username)}
    return {"success": False, "message": "Sai tài khoản hoặc mật khẩu!"}

@app.post("/api/init")
async def init_balance(data: InitBalance):
    save_so_du(data.tien_mat, data.tien_tk, data.username)
    return {"success": True, "so_du": get_so_du(data.username), "history": get_history(data.username)}

@app.post("/api/chat")
async def chat_with_ai(data: UserMessage):
    so_du = get_so_du(data.username)
    if not so_du:
        return {"reply": "Lỗi: Không tìm thấy tài khoản.", "so_du": {"tien_mat": 0, "tien_tk": 0}, "history": []}

    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=data.message,
            config=types.GenerateContentConfig(system_instruction=system_prompt)
        )
        ai_text = response.text.strip()
        if ai_text.startswith("```json"): ai_text = ai_text[7:-3].strip()
        elif ai_text.startswith("```"): ai_text = ai_text[3:-3].strip()

        ket_qua = json.loads(ai_text)
        if "error" in ket_qua:
            return {"reply": "Xin lỗi, tôi không hiểu. Hãy nhập rõ hơn.", "so_du": so_du, "history": get_history(data.username)}

        loai = ket_qua.get("loai_giao_dich")
        nguon = ket_qua.get("nguon_tien")
        tien = ket_qua.get("so_tien", 0)
        ly_do = ket_qua.get("ly_do", "")

        ten_nguon = "Tiền mặt" if nguon == "tien_mat" else "Tiền TK"
        if loai == "chi":
            so_du[nguon] -= tien
            reply_msg = f"✅ Đã ghi nhận CHI: -{tien:,}đ ({ly_do}) từ {ten_nguon}."
        else:
            so_du[nguon] += tien
            reply_msg = f"✅ Đã ghi nhận THU: +{tien:,}đ ({ly_do}) vào {ten_nguon}."

        save_so_du(so_du["tien_mat"], so_du["tien_tk"], data.username)
        cursor.execute('INSERT INTO transactions (username, loai, nguon, so_tien, ly_do) VALUES (?, ?, ?, ?, ?)', (data.username, loai, nguon, tien, ly_do))
        conn.commit()

        return {"reply": reply_msg, "so_du": so_du, "history": get_history(data.username)}
    except Exception as e:
        return {"reply": f"Lỗi hệ thống: {str(e)}", "so_du": so_du, "history": get_history(data.username)}

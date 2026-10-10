from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import sqlite3
import json
import os

app = FastAPI(title="Telegram Exam MiniApp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "exam.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            username TEXT,
            subject TEXT,
            score REAL,
            correct int,
            incorrect int,
            total int,
            time_spent int,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Load Geometry Questions
GEOMETRY_QUESTIONS = []
geom_path = os.path.join(os.path.dirname(__file__), "geometry_final.json")
if os.path.exists(geom_path):
    with open(geom_path, "r", encoding="utf-8") as f:
        GEOMETRY_QUESTIONS = json.load(f)

# Chemistry Questions
CHEMISTRY_QUESTIONS = [
    {
        "id": 1,
        "question": "کدام گزینه نادرست است؟",
        "options": [
            "صابون‌های جامد را نمی‌توان از گرم کردن روغن‌های گوناگون با سدیم هیدروکسید تهیه کرد.",
            "صابون ماده‌ای است که هم در آب و هم در چربی‌ها حل می‌شود.",
            "صابون جامد، نمک سدیم اسیدهای چرب است.",
            "لکه‌های حاصل از آب قند را می‌توان با آب شست."
        ],
        "correct": 0
    },
    {
        "id": 2,
        "question": "۵۶٫۸ گرم اسید چرب C17H35COOH با باز واکنش می‌دهد...",
        "options": ["۶۰٫۶", "۳۰٫۳", "۲۰٫۲", "۴۰٫۴"],
        "correct": 3
    }
]

class SubmitRequest(BaseModel):
    user_id: str
    username: str
    subject: str # 'chem' or 'geom'
    time_spent: int # in seconds
    answers: Dict[str, int]

@app.get("/api/questions/{subject}")
def get_questions(subject: str):
    if subject == "chem":
        safe_q = [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in CHEMISTRY_QUESTIONS]
        return {"questions": safe_q}
    elif subject == "geom":
        # Return first 15 questions as a manageable sample exam
        sample = GEOMETRY_QUESTIONS[:15]
        formatted = []
        for q in sample:
            opts = q.get("options", [])
            if not opts or len(opts) < 4:
                opts = ["گزینه ۱", "گزینه ۲", "گزینه ۳", "گزینه ۴"]
            formatted.append({
                "id": q["id"],
                "question": f"سوال {q['original_num']} (صفحه {q['page']}):\n{q['text']}",
                "options": opts
            })
        return {"questions": formatted}
    else:
        raise HTTPException(status_code=404, detail="Subject not found")

@app.post("/api/submit")
def submit_exam(sub: SubmitRequest):
    if sub.subject == "chem":
        questions = CHEMISTRY_QUESTIONS
    else:
        questions = GEOMETRY_QUESTIONS[:15]
        
    total = len(questions)
    correct_count = 0
    
    for idx, q in enumerate(questions):
        qid_str = str(q.get("id", idx + 1))
        if qid_str in sub.answers:
            # Check answer
            expected = q.get("correct", 0)
            if int(sub.answers[qid_str]) == expected:
                correct_count += 1
                
    incorrect_count = total - correct_count
    score = ((3 * correct_count - incorrect_count) / (3 * total)) * 100
    score = max(0.0, round(score, 2))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO results (user_id, username, subject, score, correct, incorrect, total, time_spent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (sub.user_id, sub.username, sub.subject, score, correct_count, incorrect_count, total, sub.time_spent)
    )
    conn.commit()
    conn.close()
    
    return {
        "score": score,
        "correct": correct_count,
        "incorrect": incorrect_count,
        "total": total,
        "time_spent": sub.time_spent,
        "message": "آزمون با موفقیت ثبت شد!"
    }

@app.get("/api/leaderboard/{subject}")
def get_leaderboard(subject: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, score, time_spent, submitted_at FROM results WHERE subject = ? ORDER BY score DESC, time_spent ASC LIMIT 30",
        (subject,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    leaderboard = []
    for idx, r in enumerate(rows):
        leaderboard.append({
            "rank": idx + 1,
            "username": r[0] if r[0] else "کاربر ناشناس",
            "score": r[1],
            "time_spent": f"{r[2]} ثانیه",
            "date": r[3]
        })
    return {"leaderboard": leaderboard}


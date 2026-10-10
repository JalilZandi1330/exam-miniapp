from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
import sqlite3
import os

app = FastAPI(title="Telegram Exam MiniApp API")

DB_PATH = "exam.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            username TEXT,
            score REAL,
            correct int,
            incorrect int,
            total int,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class SubmitRequest(BaseModel):
    user_id: str
    username: str
    answers: Dict[str, int] # question_id -> selected_option

# Mock questions database extracted from PDF
QUESTIONS = [
    {
        "id": 1,
        "question": "کدام گزینه نادرست است؟",
        "options": [
            "صابون‌های جامد را نمی‌توان از گرم کردن روغن‌های گوناگون مثل روغنی با فرمول C57H104O6 با سدیم هیدروکسید تهیه کرد.",
            "صابون ماده‌ای است که هم در آب و هم در چربی‌ها حل می‌شود.",
            "صابون جامد، نمک سدیم اسیدهای چرب و صابون مایع، نمک پتاسیم یا آمونیوم اسیدهای چرب است.",
            "لکه‌های حاصل از آب قند را می‌توان هم با آب و هم با صابون شست."
        ],
        "correct": 0
    },
    {
        "id": 2,
        "question": "۵۶٫۸ گرم اسید چرب C17H35COOH را با مقدار کافی از یک محلول بازی واکنش می‌دهیم...",
        "options": ["۶۰٫۶", "۳۰٫۳", "۲۰٫۲", "۴۰٫۴"],
        "correct": 3
    }
]

@app.get("/api/questions")
def get_questions():
    # Hide correct answers from client
    safe_q = [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in QUESTIONS]
    return {"questions": safe_q}

@app.post("/api/submit")
def submit_exam(sub: SubmitRequest):
    correct_count = 0
    total = len(QUESTIONS)
    
    for q in QUESTIONS:
        qid_str = str(q["id"])
        if qid_str in sub.answers:
            if sub.answers[qid_str] == q["correct"]:
                correct_count += 1
                
    incorrect_count = total - correct_count
    score = ((3 * correct_count - incorrect_count) / (3 * total)) * 100
    score = max(0.0, round(score, 2))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO results (user_id, username, score, correct, incorrect, total) VALUES (?, ?, ?, ?, ?, ?)",
        (sub.user_id, sub.username, score, correct_count, incorrect_count, total)
    )
    conn.commit()
    conn.close()
    
    return {
        "score": score,
        "correct": correct_count,
        "incorrect": incorrect_count,
        "total": total,
        "message": "آزمون با موفقیت ثبت شد!"
    }

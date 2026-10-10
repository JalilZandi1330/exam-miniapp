from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional
import sqlite3
import json
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
            subject TEXT,
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

# Load geometry questions
GEOMETRY_QUESTIONS = []
if os.path.exists("geometry_questions.json"):
    with open("geometry_questions.json", "r", encoding="utf-8") as f:
        GEOMETRY_QUESTIONS = json.load(f)

# Mock Chemistry questions
CHEMISTRY_QUESTIONS = [
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

class SubmitRequest(BaseModel):
    user_id: str
    username: str
    subject: str # 'chem' or 'geom'
    answers: Dict[str, int]

@app.get("/api/questions/{subject}")
def get_questions(subject: str):
    if subject == "chem":
        safe_q = [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in CHEMISTRY_QUESTIONS]
        return {"questions": safe_q}
    elif subject == "geom":
        # Return first 20 geometry questions as a sample test
        sample = GEOMETRY_QUESTIONS[:20]
        formatted = []
        for idx, q in enumerate(sample):
            formatted.append({
                "id": idx + 1,
                "question": f"(تست شماره {q['number']} - صفحه {q['page']})\n{q['content'][:200]}",
                "options": ["گزینه ۱", "گزینه ۲", "گزینه ۳", "گزینه ۴"]
            })
        return {"questions": formatted}
    else:
    raise HTTPException(status_code=404, detail="Subject not found")

@app.post("/api/submit")
def submit_exam(sub: SubmitRequest):
    total = 20 if sub.subject == "geom" else len(CHEMISTRY_QUESTIONS)
    correct_count = 0
    
    # Simple scoring logic
    for qid, ans in sub.answers.items():
        # Mock grading
        if int(ans) == 0:
            correct_count += 1
            
    incorrect_count = total - correct_count
    score = ((3 * correct_count - incorrect_count) / (3 * total)) * 100
    score = max(0.0, round(score, 2))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO results (user_id, username, subject, score, correct, incorrect, total) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sub.user_id, sub.username, sub.subject, score, correct_count, incorrect_count, total)
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

import os
import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

class Expense(BaseModel):
    amount: float
    category: str
    date: str
    note: Optional[str] = None

@app.post("/expense")
def add_expense(expense: Expense):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (amount, category, date, note)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (expense.amount, expense.category, expense.date, expense.note))
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Expense added", "id": new_id}

@app.get("/expenses")
def get_expenses(category: str = None):
    conn = get_conn()
    cursor = conn.cursor()
    if category:
        cursor.execute("""
            SELECT id, amount, category, date, note
            FROM expenses
            WHERE category = %s
            ORDER BY date DESC
        """, (category,))
    else:
        cursor.execute("""
            SELECT id, amount, category, date, note
            FROM expenses
            ORDER BY date DESC
        """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"id": r[0], "amount": r[1], "category": r[2], "date": str(r[3]), "note": r[4]} for r in rows]

@app.get("/expenses/summary")
def summary():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, ROUND(SUM(amount)::numeric, 2) as total
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"category": r[0], "total": r[1]} for r in rows]

@app.get("/expenses/monthly")
def monthly():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TO_CHAR(date, 'YYYY-MM') as month, ROUND(SUM(amount)::numeric, 2) as total
        FROM expenses
        GROUP BY month
        ORDER BY month DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"month": r[0], "total": r[1]} for r in rows]

@app.delete("/expense/{id}")
def delete_expense(id: int):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = %s RETURNING id", (id,))
    deleted = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    if deleted:
        return {"message": "Expense deleted", "id": id}
    return {"message": "Expense not found"}
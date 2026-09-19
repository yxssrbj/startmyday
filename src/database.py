import sqlite3
import os
from contextlib import closing
from pathlib import Path


DB_PATH = Path(os.environ.get("MORNING_DB_PATH", Path(__file__).resolve().parent.parent / "progress.db"))

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("""
    CREATE TABLE IF NOT EXISTS task_progress (
        task_id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'in_progress', 'completed'))
    )
""")
        con.execute("""CREATE TABLE IF NOT EXISTS task_notes (
            task_id PRIMARY KEY,
            note TEXT,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW() ON UPDATE NOW()
        )
        """)
        con.commit()


def save_progress(task_id, status):
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("INSERT INTO task_progress (task_id, status) VALUES (?,?) ON CONFLICT(task_id) DO UPDATE SET status = excluded.status", (task_id, status))
        con.commit()

def get_progress(task_id):
   with closing(sqlite3.connect(DB_PATH)) as con:
       row = con.execute("SELECT status FROM task_progress WHERE task_id = ?", (task_id,)).fetchone()
   if row is None:
       return "pending"
   return row[0]

def save_task_note(task_id, note):
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("INSERT INTO task_notes (task_id, note) VALUES (?,?)", (task_id, note))
        con.commit()


def get_task_note(task_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        row = con.execute("SELECT note FROM task_note WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            return ""
        return row[0]

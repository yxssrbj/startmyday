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
                        task_id TEXT PRIMARY KEY,
                        note TEXT NOT NULL,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
        """)
        con.commit()

        con.execute("""
            CREATE TABLE IF NOT EXISTS morning_preferences (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                morning_start TEXT NOT NULL,
                work_start TEXT NOT NULL,
                routine_minutes INTEGER NOT NULL CHECK (routine_minutes >= 0),
                gym_minutes INTEGER NOT NULL CHECK (gym_minutes >= 0),
                buffer_minutes INTEGER NOT NULL CHECK (buffer_minutes >= 0)
            )
        """)
        con.execute(
                    """CREATE TABLE IF NOT EXISTS work_sessions(
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT NOT NULL,
                        worked_on TEXT NOT NULL,
                        start_time TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                        end_time TIMESTAMP,
                        actual_minutes INTEGER 
        
        
                )""")
        
        con.commit()


DEFAULT_PREFERENCES = {
    'morning_start': '10:00', 'work_start': '15:00',
    'routine_minutes': 60, 'gym_minutes': 90, 'buffer_minutes': 30,
}


def get_preferences():
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("""
            SELECT morning_start, work_start, routine_minutes, gym_minutes, buffer_minutes
            FROM morning_preferences WHERE id = 1
        """).fetchone()
    return dict(row) if row is not None else DEFAULT_PREFERENCES.copy()


def save_preferences(preferences):
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("""
            INSERT INTO morning_preferences
                (id, morning_start, work_start, routine_minutes, gym_minutes, buffer_minutes)
            VALUES (1, :morning_start, :work_start, :routine_minutes, :gym_minutes, :buffer_minutes)
            ON CONFLICT(id) DO UPDATE SET
                morning_start = excluded.morning_start,
                work_start = excluded.work_start,
                routine_minutes = excluded.routine_minutes,
                gym_minutes = excluded.gym_minutes,
                buffer_minutes = excluded.buffer_minutes
        """, preferences)
        con.commit()
    return preferences.copy()



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
        ## making whitespaces and empty strings clear the note instead of saving it as a whitespace
        if not note.strip():
            con.execute("DELETE FROM task_notes WHERE task_id = ?", (task_id,))
        else:
            con.execute("""INSERT INTO task_notes (task_id, note, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP) 
            ON CONFLICT(task_id) 
            DO UPDATE SET note = excluded.note, updated_at = CURRENT_TIMESTAMP""", (task_id, note))
        con.commit()


def get_task_note(task_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        row = con.execute("""SELECT note, updated_at
          FROM task_notes 
          WHERE task_id = ?""", (task_id,)).fetchone()
        if row is None:
            return {"note":"", "updated_at":None}
        return {"note":row[0],"updated_at":row[1]}



    
def start_work_session(task_id,worked_on):
    with closing(sqlite3.connect(DB_PATH)) as con:
        ## make it return the end time, actual minutes
        active_session = get_active_session()
        if active_session is None:
            con.execute("""INSERT into work_sessions (task_id, worked_on) 
            VALUES (?, ?)""", (task_id, worked_on))
            con.commit()
            return get_active_session()
        else:
            return None


def get_active_session():
    with closing(sqlite3.connect(DB_PATH)) as con:
        row = con.execute("""SELECT session_id, task_id, worked_on, start_time, end_time, actual_minutes 
        FROM work_sessions 
        WHERE end_time IS NULL""").fetchone()
        if row is None:
            return None
        return {"session_id":row[0],
                 "task_id":row[1],
                 "worked_on":row[2],
                 "start_time":row[3],
                 "end_time":row[4],
                 "actual_minutes":row[5]}

def get_work_session(session_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        row = con.execute("""SELECT task_id, worked_on, start_time, end_time, actual_minutes 
        FROM work_sessions
          WHERE session_id = ?""", (session_id,)).fetchone()
        if row is None:
            return None
        return  {"session_id":session_id,
                  "task_id":row[0],
                  "worked_on":row[1],
                  "start_time":row[2],
                  "end_time":row[3],
                  "actual_minutes":row[4]}

def finish_work_session(session_id, actual_minutes):
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("""UPDATE work_sessions
          SET end_time = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), actual_minutes = ? 
          WHERE session_id = ? AND end_time IS NULL""", (actual_minutes, session_id))
        con.commit()
        return get_work_session(session_id)

def get_all_sessions(start,end):
    with closing(sqlite3.connect(DB_PATH)) as con:
        sessions = []
        rows = con.execute("""SELECT worked_on, SUM(actual_minutes)
                    FROM work_sessions
                    WHERE worked_on BETWEEN ? AND ?
                    AND end_time IS NOT NULL
                    AND actual_minutes IS NOT NULL
                    GROUP BY worked_on
                    ORDER BY worked_on;""", (start,end)).fetchall()
        for row in rows:
            sessions.append({"date":row[0], "minutes":row[1]})
        return sessions
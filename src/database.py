import sqlite3
import os
from contextlib import closing
from pathlib import Path


DB_PATH = Path(os.environ.get("MORNING_DB_PATH", Path(__file__).resolve().parent.parent / "progress.db"))

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("PRAGMA foreign_keys = ON")
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
        con.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                goal TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_project
            ON projects(is_active)
            WHERE is_active = 1
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL CHECK (length(trim(title)) > 0),
                deliverable TEXT NOT NULL CHECK (length(trim(deliverable)) > 0),
                first_action TEXT NOT NULL CHECK (length(trim(first_action)) > 0),
                completion_check TEXT NOT NULL CHECK (length(trim(completion_check)) > 0),
                estimated_minutes INTEGER NOT NULL CHECK (estimated_minutes > 0),
                position INTEGER NOT NULL CHECK (position >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS tasks_by_project_position
            ON tasks(project_id, position)
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS task_prerequisites (
                task_id TEXT NOT NULL,
                prerequisite_id TEXT NOT NULL,
                PRIMARY KEY (task_id, prerequisite_id),
                CHECK (task_id <> prerequisite_id),
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
                FOREIGN KEY (prerequisite_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS prerequisites_by_prerequisite
            ON task_prerequisites(prerequisite_id)
        """)
        con.execute(
                    """CREATE TABLE IF NOT EXISTS work_sessions(
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT NOT NULL,
                        worked_on TEXT NOT NULL,
                        start_time TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                        end_time TIMESTAMP,
                        actual_minutes INTEGER,
                        summary TEXT,
                        evidence TEXT,
                        next_action TEXT
                )""")

        existing_session_columns = {
            row[1] for row in con.execute("PRAGMA table_info(work_sessions)")
        }
        for column_name in ("summary", "evidence", "next_action"):
            if column_name not in existing_session_columns:
                con.execute(f"ALTER TABLE work_sessions ADD COLUMN {column_name} TEXT")


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
        row = con.execute("""SELECT task_id, worked_on, start_time, end_time, actual_minutes, summary, evidence, next_action
        FROM work_sessions
          WHERE session_id = ?""", (session_id,)).fetchone()
        if row is None:
            return None
        return  {"session_id":session_id,
                  "task_id":row[0],
                  "worked_on":row[1],
                  "start_time":row[2],
                  "end_time":row[3],
                  "actual_minutes":row[4],
                  "summary":row[5],
                  "evidence":row[6],
                  "next_action":row[7]}

def finish_work_session(session_id, actual_minutes, summary, evidence, next_action):
    with closing(sqlite3.connect(DB_PATH)) as con:
        row = con.execute("SELECT task_id from work_sessions WHERE session_id = ?", (session_id,)).fetchone()
        con.execute("""UPDATE work_sessions
          SET end_time = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), actual_minutes = ?, summary = ?, evidence = ?, next_action = ?
          WHERE session_id = ? AND end_time IS NULL""", (actual_minutes, summary, evidence, next_action, session_id))
        
        con.execute("""INSERT INTO task_notes (task_id, note, updated_at) 
        VALUES (?,?, CURRENT_TIMESTAMP)
          ON CONFLICT(task_id) DO UPDATE SET
        note = excluded.note,
        updated_at = CURRENT_TIMESTAMP""", (row[0], next_action))
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

def get_active_project():
    with closing(sqlite3.connect(DB_PATH)) as con:
        row = con.execute("SELECT project_id FROM projects WHERE is_active IS 1").fetchone()
        if row is None:
            return None
        return get_project(row[0])

def get_project(project_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
            row = con.execute("SELECT project_id, name, goal, created_at, updated_at FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if row is None:
                return None
            tasks = get_project_tasks(project_id)
            return {
            "project_id":row[0],
            "name":row[1],
            "goal":row[2],
            "tasks":tasks,
            "created_at":row[3],
            "updated_at":row[4]
        }

def get_project_tasks(project_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        tasks = []
        rows = con.execute("SELECT task_id, title, deliverable, first_action, completion_check, estimated_minutes FROM tasks WHERE project_id = ? ORDER BY position", (project_id,)).fetchall()
        for row in rows:
            prerequisites_rows = con.execute(
                """
                SELECT prerequisite_id
                FROM task_prerequisites
                WHERE task_id = ?
                ORDER BY prerequisite_id""", (row[0],)).fetchall()
            tasks.append({
                "id":row[0],
                "title":row[1],
                "deliverable":row[2],
                "first_action":row[3],
                "completion_check":row[4],
                "estimated_minutes":row[5],
                "prerequisites":[
                    prerequisite[0] for prerequisite in prerequisites_rows
                ]
            })
        return tasks

def projects_exist() -> bool:
    with closing(sqlite3.connect(DB_PATH)) as con:
        row = con.execute("SELECT EXISTS(SELECT 1 FROM projects)").fetchone()
        return bool(row[0])


def import_project(project_id, project):
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("PRAGMA foreign_keys = ON")
        try:
            con.execute("BEGIN IMMEDIATE")
            if con.execute("SELECT EXISTS(SELECT 1 FROM projects)").fetchone()[0]:
                con.rollback()
                return None

            con.execute(
                """
                INSERT INTO projects (project_id, name, goal, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (project_id, project["name"], project.get("goal", "")),
            )

            for position, task in enumerate(project["tasks"]):
                con.execute(
                    """
                    INSERT INTO tasks (
                        task_id, project_id, title, deliverable, first_action,
                        completion_check, estimated_minutes, position
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task["id"], project_id, task["title"], task["deliverable"],
                        task["first_action"], task["completion_check"],
                        task["estimated_minutes"], position,
                    ),
                )

            for task in project["tasks"]:
                for prerequisite_id in task["prerequisites"]:
                    con.execute(
                        """
                        INSERT INTO task_prerequisites (task_id, prerequisite_id)
                        VALUES (?, ?)
                        """,
                        (task["id"], prerequisite_id),
                    )

            con.commit()
        except Exception:
            con.rollback()
            raise

    return get_project(project_id)


def list_projects():
    with closing(sqlite3.connect(DB_PATH)) as con:
        rows = con.execute("""
            SELECT p.project_id, p.name, p.goal, p.is_active, p.created_at,
                   p.updated_at, COUNT(t.task_id)
            FROM projects p
            LEFT JOIN tasks t ON t.project_id = p.project_id
            GROUP BY p.project_id
            ORDER BY p.is_active DESC, p.created_at, p.project_id
        """).fetchall()
    return [
        {
            "project_id": row[0], "name": row[1], "goal": row[2],
            "is_active": bool(row[3]), "created_at": row[4],
            "updated_at": row[5], "task_count": row[6],
        }
        for row in rows
    ]


def create_project(project_id, name, goal):
    with closing(sqlite3.connect(DB_PATH)) as con:
        make_active = not bool(con.execute("SELECT EXISTS(SELECT 1 FROM projects)").fetchone()[0])
        con.execute(
            "INSERT INTO projects(project_id, name, goal, is_active) VALUES (?, ?, ?, ?)",
            (project_id, name, goal, int(make_active)),
        )
        con.commit()
    return get_project(project_id)


def update_project(project_id, changes):
    assignments = []
    values = []
    for column in ("name", "goal"):
        if column in changes:
            assignments.append(f"{column} = ?")
            values.append(changes[column])
    if not assignments:
        return get_project(project_id)
    assignments.append("updated_at = CURRENT_TIMESTAMP")
    values.append(project_id)
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute(
            f"UPDATE projects SET {', '.join(assignments)} WHERE project_id = ?",
            values,
        )
        con.commit()
    return get_project(project_id)


def set_active_project(project_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        try:
            con.execute("BEGIN IMMEDIATE")
            if not con.execute(
                "SELECT EXISTS(SELECT 1 FROM projects WHERE project_id = ?)",
                (project_id,),
            ).fetchone()[0]:
                con.rollback()
                return None
            con.execute("UPDATE projects SET is_active = 0 WHERE is_active = 1")
            con.execute(
                "UPDATE projects SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
                (project_id,),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return get_project(project_id)


def delete_project(project_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("PRAGMA foreign_keys = ON")
        try:
            con.execute("BEGIN IMMEDIATE")
            project = con.execute(
                "SELECT is_active FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone()
            if project is None:
                con.rollback()
                return None
            task_ids = [
                row[0] for row in con.execute(
                    "SELECT task_id FROM tasks WHERE project_id = ?", (project_id,)
                ).fetchall()
            ]
            for task_id in task_ids:
                con.execute("DELETE FROM task_progress WHERE task_id = ?", (task_id,))
                con.execute("DELETE FROM task_notes WHERE task_id = ?", (task_id,))
                con.execute("DELETE FROM work_sessions WHERE task_id = ?", (task_id,))
            con.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
            new_active_id = None
            if project[0]:
                replacement = con.execute(
                    "SELECT project_id FROM projects ORDER BY created_at, project_id LIMIT 1"
                ).fetchone()
                if replacement is not None:
                    new_active_id = replacement[0]
                    con.execute(
                        "UPDATE projects SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
                        (new_active_id,),
                    )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return {"deleted_project_id": project_id, "active_project_id": new_active_id}


def get_task_project_id(task_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        row = con.execute("SELECT project_id FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    return row[0] if row is not None else None


def get_project_task_ids(project_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        return [
            row[0] for row in con.execute(
                "SELECT task_id FROM tasks WHERE project_id = ? ORDER BY position", (project_id,)
            ).fetchall()
        ]


def get_project_dependencies(project_id):
    task_ids = get_project_task_ids(project_id)
    dependencies = {task_id: [] for task_id in task_ids}
    if not task_ids:
        return dependencies
    with closing(sqlite3.connect(DB_PATH)) as con:
        rows = con.execute("""
            SELECT tp.task_id, tp.prerequisite_id
            FROM task_prerequisites tp
            JOIN tasks t ON t.task_id = tp.task_id
            WHERE t.project_id = ?
        """, (project_id,)).fetchall()
    for task_id, prerequisite_id in rows:
        dependencies[task_id].append(prerequisite_id)
    return dependencies


def create_task(task_id, project_id, task):
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("PRAGMA foreign_keys = ON")
        try:
            con.execute("BEGIN IMMEDIATE")
            position = con.execute(
                "SELECT COALESCE(MAX(position) + 1, 0) FROM tasks WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]
            con.execute("""
                INSERT INTO tasks (
                    task_id, project_id, title, deliverable, first_action,
                    completion_check, estimated_minutes, position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, project_id, task["title"], task["deliverable"],
                task["first_action"], task["completion_check"],
                task["estimated_minutes"], position,
            ))
            for prerequisite_id in task.get("prerequisites", []):
                con.execute(
                    "INSERT INTO task_prerequisites(task_id, prerequisite_id) VALUES (?, ?)",
                    (task_id, prerequisite_id),
                )
            con.execute(
                "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
                (project_id,),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return next(task for task in get_project_tasks(project_id) if task["id"] == task_id)


def update_task(task_id, changes):
    project_id = get_task_project_id(task_id)
    if project_id is None:
        return None
    task_columns = (
        "title", "deliverable", "first_action", "completion_check", "estimated_minutes"
    )
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("PRAGMA foreign_keys = ON")
        try:
            con.execute("BEGIN IMMEDIATE")
            assignments = []
            values = []
            for column in task_columns:
                if column in changes:
                    assignments.append(f"{column} = ?")
                    values.append(changes[column])
            if assignments:
                assignments.append("updated_at = CURRENT_TIMESTAMP")
                con.execute(
                    f"UPDATE tasks SET {', '.join(assignments)} WHERE task_id = ?",
                    (*values, task_id),
                )
            if "prerequisites" in changes:
                con.execute("DELETE FROM task_prerequisites WHERE task_id = ?", (task_id,))
                for prerequisite_id in changes["prerequisites"]:
                    con.execute(
                        "INSERT INTO task_prerequisites(task_id, prerequisite_id) VALUES (?, ?)",
                        (task_id, prerequisite_id),
                    )
            con.execute(
                "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
                (project_id,),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return next(task for task in get_project_tasks(project_id) if task["id"] == task_id)


def reorder_tasks(project_id, ordered_task_ids):
    with closing(sqlite3.connect(DB_PATH)) as con:
        try:
            con.execute("BEGIN IMMEDIATE")
            current_ids = {
                row[0] for row in con.execute(
                    "SELECT task_id FROM tasks WHERE project_id = ?", (project_id,)
                ).fetchall()
            }
            if current_ids != set(ordered_task_ids) or len(current_ids) != len(ordered_task_ids):
                con.rollback()
                return None
            for position, task_id in enumerate(ordered_task_ids):
                con.execute(
                    "UPDATE tasks SET position = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                    (position, task_id),
                )
            con.execute(
                "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
                (project_id,),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return get_project_tasks(project_id)


def delete_task(task_id):
    project_id = get_task_project_id(task_id)
    if project_id is None:
        return None
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("PRAGMA foreign_keys = ON")
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM task_progress WHERE task_id = ?", (task_id,))
            con.execute("DELETE FROM task_notes WHERE task_id = ?", (task_id,))
            con.execute("DELETE FROM work_sessions WHERE task_id = ?", (task_id,))
            con.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            remaining = con.execute(
                "SELECT task_id FROM tasks WHERE project_id = ? ORDER BY position", (project_id,)
            ).fetchall()
            for position, (remaining_id,) in enumerate(remaining):
                con.execute("UPDATE tasks SET position = ? WHERE task_id = ?", (position, remaining_id))
            con.execute(
                "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
                (project_id,),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return {"deleted_task_id": task_id, "project_id": project_id}

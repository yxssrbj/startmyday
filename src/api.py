import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from database import get_progress, init_db, save_progress, save_task_note, get_task_note
from main import is_task_ready, validate_project

from main import select_next_task, plan_morning

PLAN_PATH = Path(__file__).resolve().parent.parent / 'project_plan.json'


class MorningPlanRequest(BaseModel):
    morning_start: datetime
    work_start: datetime
    routine_minutes: int = Field(ge=0)
    gym_minutes: int = Field(ge=0)
    buffer_minutes: int = Field(ge=0)

class NoteUpdate(BaseModel):
    note: str

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title='Morning Plan', lifespan=lifespan)


class ProgressUpdate(BaseModel):
    status: Literal['pending', 'in_progress', 'completed']


def load_project():
    try:
        project = json.loads(PLAN_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise HTTPException(422, 'Could not read project_plan.json. Check the file and JSON syntax.')
    errors = validate_project(project)
    if errors:
        raise HTTPException(422, errors)
    return project


def check_task_exists(task_id: str):
    project = load_project()
    task = next((task for task in project['tasks'] if task['id'] == task_id),None)
    if task is None:
            raise HTTPException(404, 'Task doesnt exist')
    else:
        return task

@app.get('/api/project')
def get_project():
    project = load_project()
    return {
        **project,
        'tasks': [
            {**task, 'status': get_progress(task['id']), 'ready': is_task_ready(task)}
            for task in project['tasks']
        ],
    }


@app.get("/api/next-task")
def get_next_task(available_minutes: int = Query(gt=0)):
    project = load_project()
    next_task = select_next_task(project, available_minutes)
    if next_task == None:
        return None
    return next_task


@app.post("/api/morning-plan")
def get_available_minutes(req: MorningPlanRequest):
    project = load_project()
    try:
        plan = plan_morning(project, req.morning_start, req.work_start, req.routine_minutes, req.gym_minutes, req.buffer_minutes)
        return plan
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    



@app.patch('/api/tasks/{task_id}/progress')
def update_progress(task_id: str, update: ProgressUpdate):
    task = check_task_exists(task_id)
    if update.status != 'pending' and any(get_progress(p) != 'completed' for p in task['prerequisites']):
        raise HTTPException(409, 'Complete the prerequisites first.')
    save_progress(task_id, update.status)
    return get_project()


@app.put('/api/tasks/{task_id}/note')
def update_task_note(task_id: str, update: NoteUpdate):
    check_task_exists(task_id)
    save_task_note(task_id, update.note)
    return get_task_note(task_id)

@app.get('/api/tasks/{task_id}/note')
def read_task_note(task_id: str):
    check_task_exists(task_id)
    return get_task_note(task_id)

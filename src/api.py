import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from database import get_progress, init_db, save_progress
from main import is_task_ready, validate_project

from main import select_next_task

PLAN_PATH = Path(__file__).resolve().parent.parent / 'project_plan.json'


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


@app.get("/api/get-available-minutes")
def get_available_minutes():
    pass



@app.patch('/api/tasks/{task_id}/progress')
def update_progress(task_id: str, update: ProgressUpdate):
    project = load_project()
    task = next((task for task in project['tasks'] if task['id'] == task_id), None)
    if task is None:
        raise HTTPException(404, 'Task not found')
    if update.status != 'pending' and any(get_progress(p) != 'completed' for p in task['prerequisites']):
        raise HTTPException(409, 'Complete the prerequisites first.')
    save_progress(task_id, update.status)
    return get_project()

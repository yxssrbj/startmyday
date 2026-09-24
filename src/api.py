import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

from fastapi import FastAPI, HTTPException, Query, status
from database import get_progress, init_db, save_progress, save_task_note, get_task_note, start_work_session,get_active_session, finish_work_session, get_work_session, get_preferences, save_preferences, get_all_sessions
from main import is_task_ready, validate_project

from main import select_next_task, plan_morning

PLAN_PATH = Path(__file__).resolve().parent.parent / 'project_plan.json'


class MorningPlanRequest(BaseModel):
    morning_start: datetime
    work_start: datetime
    routine_minutes: int = Field(ge=0)
    gym_minutes: int = Field(ge=0)
    buffer_minutes: int = Field(ge=0)


class StartSessionRequest(BaseModel):
    worked_on: date


class FinishSessionRequest(BaseModel):
    minutes: int = Field(gt=0, strict=True)


class MorningPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    morning_start: str = Field(pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]$')
    work_start: str = Field(pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]$')
    routine_minutes: int = Field(ge=0, strict=True)
    gym_minutes: int = Field(ge=0, strict=True)
    buffer_minutes: int = Field(ge=0, strict=True)

    @model_validator(mode='after')
    def validate_time_order(self):
        if self.work_start <= self.morning_start:
            raise ValueError('Work must start after your morning starts')
        return self


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


@app.get('/api/preferences')
def read_preferences():
    return get_preferences()


@app.put('/api/preferences')
def update_preferences(preferences: MorningPreferences):
    return save_preferences(preferences.model_dump())


@app.post('/api/tasks/{task_id}/sessions/start', status_code=status.HTTP_201_CREATED)
def start_session(task_id:str, request: StartSessionRequest):
    check_task_exists(task_id)
    session = start_work_session(task_id, request.worked_on.isoformat())
    if session is None:
        raise HTTPException(409, 'Another session is already running')
    return session


@app.get('/api/sessions/active')
def active_session():
    active_session = get_active_session()
    if active_session is None:
        return None
    else: return active_session


@app.patch('/api/sessions/{session_id}/finish')
def finish_session(session_id: int, request: FinishSessionRequest):
    ## create a new db function for finish the session
    session = get_work_session(session_id)
    if session is None:
        raise HTTPException(404, "Session doesn't exist")
    if session['end_time'] is not None:
        raise HTTPException(409, "Session is already finished")
    return finish_work_session(session_id, request.minutes)    

@app.get('/api/activity')
def read_sessions(start: date, end: date):
    if start > end:
            raise HTTPException(status_code=422, detail='Start date cannot be after end date')
    sessions = get_all_sessions(start.isoformat(), end.isoformat())
    return sessions

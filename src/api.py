import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from datetime import date, datetime
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fastapi import FastAPI, HTTPException, Query, status
from database import (
    create_project, create_task, delete_project, delete_task, finish_work_session,
    get_active_project, get_active_session, get_all_sessions, get_preferences,
    get_progress, get_project as get_stored_project, get_project_dependencies,
    get_project_task_ids, get_task_note, get_task_project_id, get_work_session,
    import_project, init_db, list_projects, projects_exist, reorder_tasks,
    save_preferences, save_progress, save_task_note, set_active_project,
    start_work_session, update_project, update_task,
)
from main import is_task_ready, validate_project

from main import select_next_task, plan_morning

PLAN_PATH = Path(__file__).resolve().parent.parent / 'project_plan.json'
LEGACY_PROJECT_ID = 'project-001'

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
    summary: str
    evidence: str
    next_action: str


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str
    goal: str = ''

    @field_validator('name')
    @classmethod
    def name_must_not_be_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Project name must not be blank')
        return value

    @field_validator('goal')
    @classmethod
    def trim_goal(cls, value):
        return value.strip()


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str | None = None
    goal: str | None = None

    @field_validator('name')
    @classmethod
    def name_must_not_be_blank(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError('Project name must not be blank')
        return value

    @field_validator('goal')
    @classmethod
    def trim_goal(cls, value):
        return value.strip() if value is not None else value

    @model_validator(mode='after')
    def include_a_change(self):
        if self.name is None and self.goal is None:
            raise ValueError('Include a project field to update')
        if 'name' in self.model_fields_set and self.name is None:
            raise ValueError('Project name cannot be null')
        if 'goal' in self.model_fields_set and self.goal is None:
            raise ValueError('Project goal cannot be null')
        return self


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str
    deliverable: str
    first_action: str
    completion_check: str
    estimated_minutes: int = Field(gt=0, strict=True)
    prerequisites: list[str] = Field(default_factory=list)

    @field_validator('title', 'deliverable', 'first_action', 'completion_check')
    @classmethod
    def text_must_not_be_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Task text must not be blank')
        return value

    @field_validator('prerequisites')
    @classmethod
    def clean_prerequisites(cls, value):
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError('Prerequisite IDs must not be blank')
        if len(cleaned) != len(set(cleaned)):
            raise ValueError('Prerequisite IDs must be unique')
        return cleaned

class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str | None = None
    deliverable: str | None = None
    first_action: str | None = None
    completion_check: str | None = None
    estimated_minutes: int | None = Field(default=None, gt=0, strict=True)
    prerequisites: list[str] | None = None

    @field_validator('title', 'deliverable', 'first_action', 'completion_check')
    @classmethod
    def text_must_not_be_blank(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError('Task text must not be blank')
        return value

    @field_validator('prerequisites')
    @classmethod
    def clean_prerequisites(cls, value):
        if value is None:
            return value
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError('Prerequisite IDs must not be blank')
        if len(cleaned) != len(set(cleaned)):
            raise ValueError('Prerequisite IDs must be unique')
        return cleaned

    @model_validator(mode='after')
    def include_a_change(self):
        if not self.model_fields_set:
            raise ValueError('Include a task field to update')
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError('Task fields cannot be null')
        return self


class TaskOrderUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    task_ids: list[str]


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
    if not projects_exist():
        import_project(LEGACY_PROJECT_ID, load_legacy_project())
    yield


app = FastAPI(title='Morning Plan', lifespan=lifespan)


class ProgressUpdate(BaseModel):
    status: Literal['pending', 'in_progress', 'completed']


def load_legacy_project():
    try:
        project = json.loads(PLAN_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise HTTPException(422, 'Could not read project_plan.json. Check the file and JSON syntax.')
    errors = validate_project(project)
    if errors:
        raise HTTPException(422, errors)
    return project


def load_project():
    project = get_active_project()
    if project is None:
        raise HTTPException(404, 'No project is currently active')
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


def project_with_task_state(project):
    return {
        **project,
        'tasks': [
            {**task, 'status': get_progress(task['id']), 'ready': is_task_ready(task)}
            for task in project['tasks']
        ],
    }


def check_project_exists(project_id: str):
    project = get_stored_project(project_id)
    if project is None:
        raise HTTPException(404, 'Project does not exist')
    return project


def check_prerequisites(project_id: str, task_id: str, prerequisite_ids: list[str]):
    project_task_ids = set(get_project_task_ids(project_id))
    if task_id in prerequisite_ids:
        raise HTTPException(422, 'A task cannot depend on itself')
    missing = [item for item in prerequisite_ids if item not in project_task_ids]
    if missing:
        raise HTTPException(422, f"Unknown prerequisite IDs: {', '.join(missing)}")

    graph = get_project_dependencies(project_id)
    graph[task_id] = list(prerequisite_ids)
    visiting = set()
    visited = set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(prerequisite) for prerequisite in graph.get(node, [])):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(visit(node) for node in graph):
        raise HTTPException(422, 'Prerequisites cannot contain a dependency cycle')

@app.get('/api/project')
def get_project():
    return project_with_task_state(load_project())


@app.get('/api/projects')
def read_projects():
    return list_projects()


@app.get('/api/projects/{project_id}')
def read_project(project_id: str):
    return project_with_task_state(check_project_exists(project_id))


@app.post('/api/projects', status_code=status.HTTP_201_CREATED)
def add_project(request: ProjectCreate):
    project_id = 'project-' + uuid4().hex[:12]
    project = create_project(project_id, request.name, request.goal)
    return project_with_task_state(project)


@app.patch('/api/projects/{project_id}')
def edit_project(project_id: str, request: ProjectUpdate):
    check_project_exists(project_id)
    project = update_project(project_id, request.model_dump(exclude_unset=True))
    return project_with_task_state(project)


@app.put('/api/projects/{project_id}/active')
def activate_project(project_id: str):
    project = set_active_project(project_id)
    if project is None:
        raise HTTPException(404, 'Project does not exist')
    return project_with_task_state(project)


@app.delete('/api/projects/{project_id}')
def remove_project(project_id: str):
    result = delete_project(project_id)
    if result is None:
        raise HTTPException(404, 'Project does not exist')
    return result


@app.post('/api/projects/{project_id}/tasks', status_code=status.HTTP_201_CREATED)
def add_task(project_id: str, request: TaskCreate):
    check_project_exists(project_id)
    task_id = 'task-' + uuid4().hex[:12]
    check_prerequisites(project_id, task_id, request.prerequisites)
    return create_task(task_id, project_id, request.model_dump())


@app.patch('/api/tasks/{task_id}')
def edit_task(task_id: str, request: TaskUpdate):
    project_id = get_task_project_id(task_id)
    if project_id is None:
        raise HTTPException(404, 'Task does not exist')
    changes = request.model_dump(exclude_unset=True)
    if 'prerequisites' in changes:
        check_prerequisites(project_id, task_id, changes['prerequisites'])
    return update_task(task_id, changes)


@app.put('/api/projects/{project_id}/tasks/order')
def update_task_order(project_id: str, request: TaskOrderUpdate):
    check_project_exists(project_id)
    if len(request.task_ids) != len(set(request.task_ids)):
        raise HTTPException(422, 'Task order cannot contain duplicate IDs')
    tasks = reorder_tasks(project_id, request.task_ids)
    if tasks is None:
        raise HTTPException(422, 'Task order must contain every project task exactly once')
    return tasks


@app.delete('/api/tasks/{task_id}')
def remove_task(task_id: str):
    project_id = get_task_project_id(task_id)
    if project_id is None:
        raise HTTPException(404, 'Task does not exist')
    dependents = [
        dependent_id for dependent_id, prerequisites in get_project_dependencies(project_id).items()
        if task_id in prerequisites
    ]
    if dependents:
        raise HTTPException(409, 'Remove this task from dependent prerequisites first')
    return delete_task(task_id)


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
    if not request.summary.strip() or not request.next_action.strip():
        raise HTTPException(status_code=422, detail='Summary or next action  fields must not be blank')
    session = get_work_session(session_id)
    if session is None:
        raise HTTPException(404, "Session doesn't exist")
    if session['end_time'] is not None:
        raise HTTPException(409, "Session is already finished")
    return finish_work_session(session_id,
                                request.minutes,
                                  request.summary.strip(),
                                request.evidence.strip(),
                                  request.next_action.strip())    

@app.get('/api/activity')
def read_sessions(start: date, end: date):
    if start > end:
            raise HTTPException(status_code=422, detail='Start date cannot be after end date')
    sessions = get_all_sessions(start.isoformat(), end.isoformat())
    return sessions

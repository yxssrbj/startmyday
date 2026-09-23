# Morning Plan

A local programming dashboard built with React + TypeScript + Vite, backed by Python + FastAPI and SQLite.

The frontend uses shadcn/ui components (Button, Card, Input, Label, Badge, Progress, and Alert), Tailwind CSS v4, and Lucide icons. Theme tokens in frontend/src/style.css define the cool slate, white, and blue palette. Components live in frontend/src/components/ui; frontend/components.json configures the shadcn CLI.

## Run

From the project root, activate your environment and start the API:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn api:app --app-dir src --reload
```

In a second terminal:

```powershell
cd frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173. Keep both terminals running; Ctrl+C stops each server.
The frontend forwards /api requests to FastAPI on port 8000.
Interactive API documentation is at http://127.0.0.1:8000/docs.

## First-time setup

Dependencies are already installed on this machine. For a fresh checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm.cmd ci
```

Use Node 20.19+ or 22.12+ (this build was verified with Node 24).

## What works

- Load your actual project_plan.json and display deliverables, first actions, and completion checks.
- Show completed, in-progress, ready, and blocked tasks.
- Start or complete ready tasks; reopen completed tasks.
- Save status to progress.db and recalculate readiness.
- Save a per-task “Continue here tomorrow” note, view its last-saved time, or clear it. Notes load whenever a task is opened.
- Save or discard note drafts before switching tasks, updating progress, or recalculating the plan; failed saves keep the draft available for retry.
- Show plan validation and API errors.

Enter a date, morning/work start times, and routine, gym, and buffer durations, then choose **Plan my morning**.
The dashboard sends same-day local timestamps to POST /api/morning-plan.
It displays the programming budget, any overbooking, and the backend's recommended task.
Zero durations are allowed. A zero budget has no task; a negative budget displays the time deficit.
Progress changes and Refresh recalculate using the last submitted inputs. Form edits apply only on submission; refresh of the browser loads your saved defaults with today's date.
You can still inspect any task in the list and return to the recommendation.
The morning planner displays the backend's ordered activity blocks with start/end times and durations. Zero-duration activities are omitted by the backend, and overbooked plans show a shortage without a schedule. The programming block covers the full available window, even if the selected task is shorter or no task fits. Generated learning plans remain a future step.
Plans are edited in JSON; use Refresh to reload them. Progress belongs to task IDs:
keep IDs stable and unique. This version handles one local project.
Reopening a prerequisite blocks unfinished dependents; previously completed work keeps its status.
Validation checks missing references and self-dependencies, but not multi-task dependency cycles yet.

## How your code connects

- src/main.py: your task/project validation and readiness functions.
- src/database.py: SQLite reads and writes, with a short-lived connection per operation.
- src/api.py: GET /api/project and PATCH /api/tasks/{id}/progress.
- frontend/src/main.tsx: typed React interface, API calls, and progress updates.
- frontend/src/style.css: responsive layout and visual styling.

main.py only runs the terminal display when executed directly; importing it from FastAPI does not run the CLI.
Your terminal version still works: python src/main.py from the project root.

## Checks

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
cd frontend
npm.cmd run build
```

API tests use a temporary database and plan. They never update your saved progress.
For isolated manual checks, set MORNING_DB_PATH to a separate file before starting the backend.

Framework references: [Vite](https://vite.dev/guide/) and [FastAPI request bodies](https://fastapi.tiangolo.com/tutorial/body/).

## Morning preferences

Use Save as defaults to remember start times and routine/gym/buffer durations. Plan my morning changes only the current plan. GET and PUT /api/preferences read and replace one settings row; no date is saved. Invalid times or durations return 422 without overwriting previous settings. Overbooked settings are allowed. Restart the backend once to create the new table in an existing database; no manual migration is needed for this feature.

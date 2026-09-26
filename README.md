# Morning Plan

A local morning planner that chooses a clear programming task, fits it around your routine, gym, and work, and remembers where to continue tomorrow. It uses React, TypeScript, Vite, FastAPI, and SQLite.

## Requirements

- Python 3.11 or newer
- Node.js 20.19+ or 22.12+
- npm

The commands below use PowerShell on Windows.

## First-time setup

Run these commands from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

cd frontend
npm.cmd ci
cd ..
```

The development requirements are only needed for running the backend tests.

## Run locally

The backend and frontend run in separate terminals.

In the first terminal, from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn api:app --app-dir src --reload
```

In a second terminal, from the project root:

```powershell
cd frontend
npm.cmd run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173) in your browser.

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Stop either server with `Ctrl+C` in its terminal.

SQLite data is stored locally in `progress.db`, which is created automatically in the project root. The frontend forwards `/api` requests to the backend on port 8000.

## What works

- Load your actual project_plan.json and display deliverables, first actions, and completion checks.
- Show completed, in-progress, ready, and blocked tasks.
- Start or complete ready tasks; reopen completed tasks.
- Save status to progress.db and recalculate readiness.
- Save a per-task “Continue here tomorrow” note, view its last-saved time, or clear it. Notes load whenever a task is opened.
- Save or discard note drafts before switching tasks, updating progress, or recalculating the plan; failed saves keep the draft available for retry.
- Generate and replan a morning schedule using saved routine, gym, buffer, and work times.
- Start and finish timed focus sessions.
- Record a session summary, evidence, and the exact next action.
- Carry the next action into the next Morning Launch and continuation note.
- Review focused minutes in a 12-week activity heatmap.
- Show plan validation and API errors.

Enter a date, morning/work start times, and routine, gym, and buffer durations, then choose **Plan my morning**.
The dashboard sends same-day local timestamps to POST /api/morning-plan.
It displays the programming budget, any overbooking, and the backend's recommended task.
Zero durations are allowed. A zero budget has no task; a negative budget displays the time deficit.
Progress changes and Refresh recalculate using the last submitted inputs. Form edits apply only on submission; refresh of the browser loads your saved defaults with today's date.
You can still inspect any task in the list and return to the recommendation.
The morning planner displays the backend's ordered activity blocks with start/end times and durations. Zero-duration activities are omitted by the backend, and overbooked plans show a shortage without a schedule. The programming block covers the full available window, even if the selected task is shorter or no task fits. Generated learning plans remain a future step.
Use the **Projects** workspace to create, edit, activate, reorder, and delete projects and tasks. The active project's tasks drive Today. On the first startup only, an empty database imports `project_plan.json`; after that SQLite is the source of truth. Progress belongs to task IDs, so IDs remain stable across task edits.
Reopening a prerequisite blocks unfinished dependents; previously completed work keeps its status. Project and task validation rejects unknown prerequisites, self-dependencies, and dependency cycles.

## How your code connects

- src/main.py: your task/project validation and readiness functions.
- src/database.py: SQLite reads and writes, with a short-lived connection per operation.
- src/api.py: project/task CRUD, progress, preferences, sessions, activity, and morning-plan HTTP routes.
- frontend/src/main.tsx and frontend/src/components/: typed React dashboard and Project Workspace.
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

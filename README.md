# Morning Plan

Morning Plan helps you start useful programming work without spending the morning deciding what to do. Set the time you have before work, and it builds a schedule around your routine and gym, then recommends a ready task that fits.

![Morning Plan demo](assets/startmyday.gif)

## What you can do

- Plan your morning around your saved schedule and replan when the day changes.
- See the next ready task, its first action, and what counts as done.
- Run a focus session and save what you accomplished plus your next action for tomorrow.
- Track focused minutes in an activity heatmap and explore concepts in the Knowledge map.
- Create and edit projects and tasks. You can also generate an AI draft, review it, and choose when to save it.

## Run locally

You need Python 3.11+, Node.js 20.19+ or 22.12+, and npm. From the project root in PowerShell, set up once:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd frontend
npm.cmd ci
cd ..
```

Start the backend in one terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn api:app --app-dir src --reload
```

Start the frontend in another terminal:

```powershell
cd frontend
npm.cmd run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). API docs are at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Project plan generation is optional. To use it, set `OPENAI_API_KEY` in the backend terminal environment or in a project-root `.env` file. Keep the key private; `.env` is ignored by Git.

## Built with

FastAPI and SQLite for the backend; React, TypeScript, Vite, and Tailwind CSS for the frontend. Your projects, progress, and sessions stay in a local SQLite database.

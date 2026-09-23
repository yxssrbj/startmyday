# Working on Morning Plan

## Purpose and scope

This is the separate start-my-day project: help the user start useful programming work with less deciding, and fit it around a morning routine, gym, and courier shift. Keep features useful for everyday use and for learning backend development.

Read the current code and README.md before making claims or changes. MVP.md describes the product direction, but its status table is outdated; project_plan.json currently contains sample learning tasks, not the full implementation roadmap. Verify what exists instead of treating either as current status.

## Collaboration rules

- When the user asks about the current or next feature/deliverable, explain the goal first: what problem it solves, what the user will be able to do, and a concrete example of the flow. Explain how it connects to existing features and why each proposed piece is needed before listing implementation steps. Do not just prescribe function names, SQL tables, or code to copy. Give enough conceptual understanding and clear expected behavior for the user to design and build it themselves; provide implementation details afterward as support.

- The user is learning Python/backend development. By default, let them implement backend learning features; explain concepts and review their work. When they explicitly delegate a feature, implement the whole feature. Saved morning preferences were explicitly delegated.
- The assistant handles the React/TypeScript frontend and connects completed backend features so the user can see them working.
- Give complete feature-sized assignments, not one-line exercises or repeated requests to check each line. Include the outcome, concrete deliverables in dependency order, API/data contracts where relevant, first action, and a small test matrix.
- Explain stack decisions and unfamiliar concepts in plain language. Once the user understands, move on rather than repeating explanations or quizzes.
- When asked to check code, inspect the actual project source. A link into .venv/site-packages may be a mistaken link; do not edit installed dependencies to fix application code.
- For bugs, identify the cause and give a focused fix with a verification target. Preserve the user's implementation and unrelated changes; avoid wholesale rewrites.
- Continue authorized work without repeatedly asking for confirmation. Ask only when a missing decision materially changes the work.
- Keep updates and final reports concise. State what changed, what was checked, and any remaining limitation. Do not claim tests passed without running them.

## Stack and source map

- Python + FastAPI for the API; SQLite for local persistence.
- React + TypeScript + Vite with shadcn/ui, Tailwind CSS, and Lucide for the frontend. Do not replace this with Streamlit or introduce a new UI stack without a reason agreed with the user.
- src/main.py: plan validation, task readiness/selection, morning scheduling.
- src/database.py: SQLite schema and persistence.
- src/api.py: HTTP routes and request validation.
- frontend/src/main.tsx and frontend/src/components/: dashboard and feature UI.
- tests/: repeatable backend tests.
- project_plan.json: project/task input. Keep task IDs stable because progress and notes refer to them.

## Behavior to preserve

- Omit zero-duration schedule blocks. Overbooked mornings report the shortage with no schedule.
- Programming time represents the available window, even when a recommended task takes less time.
- Save as defaults persists morning/work times and routine/gym/buffer durations. Plan my morning only applies the current form. The saved defaults do not include a date; a fresh page uses today's local date.
- Continuation notes belong to tasks. Preserve unsaved drafts on failed saves and require saving/discarding before actions that would lose them.
- Distinguish planned time from actual work. Logging a session should not implicitly complete a task.

## Testing and data safety

- Put repeatable tests in tests/ instead of relying on manually editing API requests. Use meaningful success, validation, and persistence cases; do not add redundant tests for trivial cosmetic changes.
- Tests and browser checks must use a temporary database. Set MORNING_DB_PATH before starting an isolated backend, or override the database path in test fixtures. Never use the user's progress.db as disposable test data.
- Preserve existing progress, notes, and preferences. CREATE TABLE IF NOT EXISTS does not upgrade existing columns. Schema changes need idempotent migrations; avoid repeated one-off ALTER TABLE commands or deleting the database.
- Validate unknown task IDs and malformed inputs at the API boundary. Raise HTTPException for HTTP errors; do not return an exception object as data.
- Run relevant backend tests after backend changes and the frontend build after frontend changes. Verify meaningful UI behavior in a browser when changing integrations.
- Do not restart the user's Vite server on port 5173 without asking. If isolated browser verification is needed, use temporary ports and a temporary database, and stop only the processes you started. Identify listeners before stopping processes.

## Commands (PowerShell, from project root)

Activate the environment once per terminal:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then use short commands:

```powershell
python -m uvicorn api:app --app-dir src --reload
python -m unittest discover -s tests -v
```

Frontend, in a separate terminal:

```powershell
cd frontend
npm.cmd run dev
npm.cmd run build
```

The user prefers short commands after activation. uv was blocked by Windows Application Control on this machine; do not make reinstalling uv or changing Windows security a prerequisite for ordinary development.

## Next proposed feature (not implemented by this document)

Record actual programming sessions as the foundation for an activity heatmap:

- work_sessions stores id, task_id, worked_on, minutes, and created_at.
- POST /api/tasks/{task_id}/sessions records a session and returns it with status 201. Unknown tasks return 404; invalid dates and nonpositive/noninteger minutes return 422.
- GET /api/activity?start=YYYY-MM-DD&end=YYYY-MM-DD returns daily minute totals, sorted by date, with inclusive boundaries and no empty days.
- Verify multiple sessions per day, date filtering, invalid input, persistence, and unchanged task status.
- The user implements this backend slice unless they delegate it. The assistant connects a Log session form and heatmap afterward.

The user also wants iCloud Calendar integration. Treat it as a future feature; do not assume it already exists or that a particular sync approach has been agreed.

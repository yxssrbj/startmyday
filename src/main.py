import json
from pathlib import Path
from database import get_progress, init_db
from datetime import datetime, timedelta

required_fields = [
    "id",
    "title",
    "deliverable",
    "first_action",
    "completion_check",
    "prerequisites",
    "estimated_minutes",
]
text_fields = [
    "id",
    "title",
    "deliverable",
    "first_action",
    "completion_check"
]



def check_if_string(value, label):
    if not isinstance(value, str):
        return f"{label} is not a string"
    elif value.strip() == '':
        return f'{label} must not be empty'
    return None

def validate_task(task):
        if not isinstance(task, dict):
            return ['Task must be an object']
        errors = []
        for field in required_fields:
            if field not in task:
                errors.append(f'Missing field {field}')
        for field in text_fields:
            if field not in task:
                continue
            # if not isinstance(task[field], str):
            #     print("Value is not a string")
            # elif task[field].strip() == '':
            #     print(f'{field} must not be empty')
            err = check_if_string(task[field], field)
            if err is not None:
                errors.append(err)
        if "estimated_minutes" in task:
            if type(task['estimated_minutes']) is not int:
                errors.append(f"{task['estimated_minutes']} is not of tpye int")
            elif task['estimated_minutes'] <= 0:
                errors.append('must be greater than 0')

        if "prerequisites" in task:
            if not isinstance(task['prerequisites'],list):
                errors.append('prerequisites is not a list')
            else:
                for item in task['prerequisites']:
                    err = check_if_string(item, 'prerequisites')
                    if err is not None:
                        errors.append(err)
        return errors


def validate_project(project):
    if not isinstance(project, dict) or not isinstance(project.get('tasks'), list):
        return ['Project must contain a tasks list']
    all_errors = []

    for index,task in enumerate(project["tasks"], start=1):
        errors = validate_task(task)
        if errors:
            for error in errors:
                all_errors.append(f"Task {index} : {error}")

    if not all_errors:
        task_ids = {item['id'] for item in project['tasks']}

        if len(task_ids) != len(project['tasks']):
            all_errors.append("Task IDS must be unique")
        for task in project['tasks']:
            for p in task['prerequisites']:
                if p == task['id']:
                    all_errors.append(f"{task['id']} cannot depend on itself")
                elif p not in task_ids:
                    all_errors.append( f"{task['id']} references missing prerequisite {p}")


    return all_errors

def is_task_ready(task):
    status = get_progress(task['id'])
    if status == 'completed':
        return False

    for p in task['prerequisites']:
        if get_progress(p) != 'completed':
            return False
    return True


def select_next_task(project, available_minutes):
    for task in project['tasks']:
        if is_task_ready(task):
            if task["estimated_minutes"] <= available_minutes:
                return task
    return None

def calculate_programming_minutes(morning_start, work_start, routine_minutes, gym_minutes, buffer_minutes):
    available = work_start - morning_start
    available_minutes = available.total_seconds() / 60
    programming_minutes = available_minutes - routine_minutes - gym_minutes - buffer_minutes
    return programming_minutes

def plan_morning(project,morning_start, work_start, routine_minutes, gym_minutes, buffer_minutes):
    if work_start <= morning_start:
        raise ValueError("Work must start after your morning")
    if routine_minutes < 0 or gym_minutes < 0 or buffer_minutes < 0:        raise ValueError("Durations must be zero or greater")
    
    task = None
    schedule = []
    current_start = morning_start
    programming_minutes = calculate_programming_minutes(morning_start, work_start, routine_minutes, gym_minutes, buffer_minutes)
    if programming_minutes > 0:
        task = select_next_task(project, programming_minutes)
    overbooked_minutes = max(0, -programming_minutes)


    activities = [
        ("routine", routine_minutes),
        ("programming", programming_minutes),
        ("gym", gym_minutes),
        ("buffer", buffer_minutes)
    ]

    if overbooked_minutes <= 0:
            for activity, duration in activities:
                if duration > 0:
                    end = current_start + timedelta(minutes=duration)
                    schedule.append({
                        "activity":activity,
                        "start":current_start,
                        "end":end,
                            })
                    current_start = end

    return {
            "programming_minutes": programming_minutes,
            "overbooked_minutes":overbooked_minutes,
            "task":task,
            "schedule":schedule
    }


if __name__ == '__main__':
    init_db()
    with open(Path(__file__).resolve().parent.parent / 'project_plan.json', encoding='utf-8') as f:
        project = json.load(f)
    errors = validate_project(project)

    if errors:
        for error in errors:
            print(error)
    else:
        for task in project['tasks']:
            print(f"[{get_progress(task['id'])}] {task['title']}")
            print('Ready:', is_task_ready(task))


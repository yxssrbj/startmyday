import json

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
                errors.append(f'{task['estimated_minutes']} is not of tpye int')
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

with open('../project_plan.json', encoding="utf-8") as f:
    project = json.load(f)
    all_errors = []

    for index,task in enumerate(project["tasks"], start=1):
        errors = validate_task(task)
        if errors:
            for error in errors:
                all_errors.append(f"Task {index} : {error}")

    if not errors:
        task_ids = {item['id'] for item in project['tasks']}

        if len(task_ids) != len(project['tasks']):
            all_errors.append("Task IDS must be unique")
        for p in task['prerequisites']:
            if p == task['id']:
                all_errors.append(f'{task['id']} cannot depend on itself')
            elif p not in task_ids:
                all_errors.append( f"{task['id']} references missing prerequisite {p}")
        

    if all_errors:
        for error in all_errors:
            print(error)
    else:
        print("Project tasks are valid")
            
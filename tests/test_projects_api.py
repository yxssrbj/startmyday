import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fastapi.testclient import TestClient
import api
import database


class ProjectsApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db, self.old_plan = database.DB_PATH, api.PLAN_PATH
        database.DB_PATH = Path(self.temp.name) / 'test.db'
        api.PLAN_PATH = Path(self.temp.name) / 'plan.json'
        self.seed = {
            'name': 'Seed project',
            'tasks': [{
                'id': 'seed-task', 'title': 'Seed task', 'deliverable': 'Seed result',
                'first_action': 'Begin seed', 'completion_check': 'Seed works',
                'prerequisites': [], 'estimated_minutes': 15,
            }],
        }
        api.PLAN_PATH.write_text(json.dumps(self.seed), encoding='utf-8')
        self.client = TestClient(api.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        database.DB_PATH, api.PLAN_PATH = self.old_db, self.old_plan
        self.temp.cleanup()

    def task_payload(self, title, prerequisites=None):
        return {
            'title': title,
            'deliverable': f'{title} result',
            'first_action': f'Begin {title}',
            'completion_check': f'{title} works',
            'estimated_minutes': 25,
            'prerequisites': prerequisites or [],
        }

    def test_project_crud_and_activation(self):
        created = self.client.post('/api/projects', json={'name': ' Second ', 'goal': ' Learn APIs '})
        self.assertEqual(created.status_code, 201)
        project_id = created.json()['project_id']
        self.assertEqual(created.json()['name'], 'Second')
        self.assertEqual(created.json()['goal'], 'Learn APIs')
        self.assertFalse(next(item for item in self.client.get('/api/projects').json() if item['project_id'] == project_id)['is_active'])

        edited = self.client.patch(f'/api/projects/{project_id}', json={'name': 'Updated'})
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()['name'], 'Updated')
        self.assertEqual(self.client.put(f'/api/projects/{project_id}/active').status_code, 200)
        self.assertEqual(self.client.get('/api/project').json()['project_id'], project_id)

        removed = self.client.delete(f'/api/projects/{project_id}')
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.json()['active_project_id'], api.LEGACY_PROJECT_ID)
        self.assertEqual(self.client.get('/api/project').json()['project_id'], api.LEGACY_PROJECT_ID)
        self.assertEqual(self.client.patch('/api/projects/missing', json={'name': 'No'}).status_code, 404)

    def test_task_crud_dependencies_cycles_and_order(self):
        first = self.client.post(
            f'/api/projects/{api.LEGACY_PROJECT_ID}/tasks',
            json=self.task_payload('First new'),
        )
        self.assertEqual(first.status_code, 201)
        first_id = first.json()['id']
        second = self.client.post(
            f'/api/projects/{api.LEGACY_PROJECT_ID}/tasks',
            json=self.task_payload('Second new', [first_id]),
        )
        self.assertEqual(second.status_code, 201)
        second_id = second.json()['id']

        self.assertEqual(
            self.client.patch(f'/api/tasks/{first_id}', json={'prerequisites': [second_id]}).status_code,
            422,
        )
        self.assertEqual(
            self.client.patch(f'/api/tasks/{first_id}', json={'prerequisites': ['missing']}).status_code,
            422,
        )
        self.assertEqual(self.client.delete(f'/api/tasks/{first_id}').status_code, 409)

        edited = self.client.patch(
            f'/api/tasks/{second_id}',
            json={'title': 'Second edited', 'prerequisites': []},
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()['title'], 'Second edited')
        self.assertEqual(self.client.delete(f'/api/tasks/{first_id}').status_code, 200)

        current_ids = [task['id'] for task in self.client.get('/api/project').json()['tasks']]
        reordered = list(reversed(current_ids))
        response = self.client.put(
            f'/api/projects/{api.LEGACY_PROJECT_ID}/tasks/order',
            json={'task_ids': reordered},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([task['id'] for task in response.json()], reordered)
        self.assertEqual(
            self.client.put(
                f'/api/projects/{api.LEGACY_PROJECT_ID}/tasks/order',
                json={'task_ids': [second_id]},
            ).status_code,
            422,
        )

    def test_project_deletion_cleans_task_data(self):
        created = self.client.post('/api/projects', json={'name': 'Disposable'}).json()
        project_id = created['project_id']
        task = self.client.post(
            f'/api/projects/{project_id}/tasks', json=self.task_payload('Disposable task')
        ).json()
        task_id = task['id']
        database.save_progress(task_id, 'in_progress')
        database.save_task_note(task_id, 'Keep temporarily')
        database.start_work_session(task_id, '2026-09-26')

        self.assertEqual(self.client.delete(f'/api/projects/{project_id}').status_code, 200)
        with closing(sqlite3.connect(database.DB_PATH)) as con:
            for table in ('tasks', 'task_progress', 'task_notes', 'work_sessions'):
                column = 'task_id'
                self.assertEqual(
                    con.execute(f'SELECT COUNT(*) FROM {table} WHERE {column} = ?', (task_id,)).fetchone()[0],
                    0,
                )


if __name__ == '__main__':
    unittest.main()

"""Run from the project root: python -m unittest discover -s tests -v."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fastapi.testclient import TestClient
import api
import database


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_db, self.old_plan = database.DB_PATH, api.PLAN_PATH
        database.DB_PATH = Path(self.directory.name) / 'progress.db'
        api.PLAN_PATH = Path(self.directory.name) / 'plan.json'
        task = {
            'id': 'first', 'title': 'First task', 'deliverable': 'A result',
            'first_action': 'Begin', 'completion_check': 'Result works',
            'prerequisites': [], 'estimated_minutes': 10,
        }
        second = {**task, 'id': 'second', 'prerequisites': ['first']}
        self.plan = {'name': 'Test project', 'tasks': [task, second]}
        self.write_plan(self.plan)
        self.client = TestClient(api.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        database.DB_PATH, api.PLAN_PATH = self.old_db, self.old_plan
        self.directory.cleanup()

    def write_plan(self, plan):
        api.PLAN_PATH.write_text(json.dumps(plan), encoding='utf-8')

    def test_complete_unlock_and_persist(self):
        tasks = self.client.get('/api/project').json()['tasks']
        self.assertEqual([t['ready'] for t in tasks], [True, False])
        self.assertEqual(self.client.patch('/api/tasks/second/progress', json={'status': 'completed'}).status_code, 409)
        response = self.client.patch('/api/tasks/first/progress', json={'status': 'completed'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['tasks'][1]['ready'])
        # Every database operation opens a new connection, checking disk persistence.
        self.assertEqual(database.get_progress('first'), 'completed')
        self.assertEqual(self.client.get('/api/project').json()['tasks'][0]['status'], 'completed')
        self.client.patch('/api/tasks/first/progress', json={'status': 'pending'})
        self.assertFalse(self.client.get('/api/project').json()['tasks'][1]['ready'])

    def test_reject_unknown_and_invalid_status(self):
        self.assertEqual(self.client.patch('/api/tasks/missing/progress', json={'status': 'completed'}).status_code, 404)
        self.assertEqual(self.client.patch('/api/tasks/first/progress', json={'status': 'invalid'}).status_code, 422)
        self.assertEqual(database.get_progress('first'), 'pending')

    def test_invalid_plan_is_reported(self):
        for plan in [None, {'tasks': [123]}, {'tasks': []}]:
            self.write_plan(plan)
            expected = 200 if plan == {'tasks': []} else 422
            self.assertEqual(self.client.get('/api/project').status_code, expected)
        bad = copy.deepcopy(self.plan)
        del bad['tasks'][0]['id']
        self.write_plan(bad)
        self.assertEqual(self.client.get('/api/project').status_code, 422)
        bad = copy.deepcopy(self.plan)
        bad['tasks'][0]['prerequisites'] = ['missing']
        self.write_plan(bad)
        self.assertEqual(self.client.get('/api/project').status_code, 422)

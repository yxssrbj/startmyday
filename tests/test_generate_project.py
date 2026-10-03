import json
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fastapi.testclient import TestClient
import api
import database


def sample_tasks():
    return [
        {
            'draft_id': f'draft-{index}', 'title': f'Task {index}',
            'deliverable': f'Result {index}', 'first_action': f'Start {index}',
            'completion_check': f'Check {index}', 'estimated_minutes': 45,
            'prerequisites': [f'draft-{index - 1}'] if index > 1 else [],
        }
        for index in range(1, 7)
    ]


class GenerateProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db, self.old_plan = database.DB_PATH, api.PLAN_PATH
        database.DB_PATH = Path(self.temp.name) / 'test.db'
        api.PLAN_PATH = Path(self.temp.name) / 'plan.json'
        api.PLAN_PATH.write_text(json.dumps({'name': 'Seed', 'tasks': []}), encoding='utf-8')
        self.client = TestClient(api.app)
        self.client.__enter__()
        self.env = patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
        self.env.start()
        self.dotenv = patch.object(api, 'load_dotenv')
        self.dotenv.start()

    def tearDown(self):
        self.dotenv.stop()
        self.env.stop()
        self.client.__exit__(None, None, None)
        database.DB_PATH, api.PLAN_PATH = self.old_db, self.old_plan
        self.temp.cleanup()

    def test_generate_review_and_save_persists_only_approved_tasks(self):
        before = self.client.get('/api/projects').json()
        parsed = api.GeneratedPlan(summary='Small MVP', assumptions=['One user'], tasks=sample_tasks())
        with patch.object(api, 'OpenAI') as openai:
            openai.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
            generated = self.client.post('/api/generate-project', json={
                'name': '  Budget tracker  ', 'goal': '  Learn FastAPI  ',
            })
        self.assertEqual(generated.status_code, 200)
        self.assertEqual(generated.json()['name'], 'Budget tracker')
        self.assertEqual(generated.json()['tasks'], [task.model_dump() for task in parsed.tasks])
        call = openai.return_value.responses.parse.call_args.kwargs
        self.assertEqual(call['input'], 'Project name: Budget tracker\nGoal: Learn FastAPI')
        self.assertIs(call['text_format'], api.GeneratedPlan)
        self.assertEqual(self.client.get('/api/projects').json(), before)

        reviewed = generated.json()
        reviewed['tasks'][0]['title'] = 'Edited first task'
        reviewed['tasks'].pop()  # Removing a final task is allowed during review.
        saved = self.client.post('/api/projects/from-draft', json={
            'name': reviewed['name'], 'goal': reviewed['goal'], 'tasks': reviewed['tasks'],
        })
        self.assertEqual(saved.status_code, 201)
        project = saved.json()
        self.assertEqual(project['name'], 'Budget tracker')
        self.assertEqual(len(project['tasks']), 5)
        self.assertEqual(project['tasks'][0]['title'], 'Edited first task')
        self.assertNotEqual(project['tasks'][0]['id'], 'draft-1')
        self.assertEqual(project['tasks'][1]['prerequisites'], [project['tasks'][0]['id']])
        self.assertEqual(project['tasks'][0]['status'], 'pending')
        self.assertFalse(next(item for item in self.client.get('/api/projects').json()
                              if item['project_id'] == project['project_id'])['is_active'])
        self.assertEqual(self.client.get(f"/api/projects/{project['project_id']}").json()['tasks'], project['tasks'])

    def test_rejects_blank_fields_and_invalid_dependencies(self):
        with patch.object(api, 'OpenAI') as openai:
            for payload in ({'name': ' ', 'goal': 'Learn APIs'}, {'name': 'App', 'goal': ' '}):
                with self.subTest(payload=payload):
                    self.assertEqual(self.client.post('/api/generate-project', json=payload).status_code, 422)
            openai.assert_not_called()

        bad = sample_tasks()
        bad[0]['prerequisites'] = ['draft-2']
        before = self.client.get('/api/projects').json()
        response = self.client.post('/api/projects/from-draft', json={
            'name': 'App', 'goal': 'Learn APIs', 'tasks': bad,
        })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get('/api/projects').json(), before)

    def test_manual_and_reviewed_projects_use_distinct_ids_and_task_links(self):
        manual = self.client.post('/api/projects', json={'name': 'Manual', 'goal': 'Learn'}).json()
        reviewed = self.client.post('/api/projects/from-draft', json={
            'name': 'Reviewed', 'goal': 'Build', 'tasks': sample_tasks()[:2],
        }).json()
        self.assertNotEqual(manual['project_id'], reviewed['project_id'])
        for project in (manual, reviewed):
            self.assertTrue(project['project_id'].startswith('project-'))
            self.assertEqual(len(project['project_id']), len('project-') + 32)
        with closing(sqlite3.connect(database.DB_PATH)) as con:
            linked_ids = {
                row[0] for row in con.execute(
                    'SELECT DISTINCT project_id FROM tasks WHERE project_id = ?',
                    (reviewed['project_id'],),
                )
            }
        self.assertEqual(linked_ids, {reviewed['project_id']})

    def test_incomplete_generated_plan_is_not_saved(self):
        parsed = api.GeneratedPlan(summary='Too short', assumptions=[], tasks=sample_tasks()[:1])
        with patch.object(api, 'OpenAI') as openai:
            openai.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
            response = self.client.post('/api/generate-project', json={'name': 'App', 'goal': 'Learn APIs'})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(len(self.client.get('/api/projects').json()), 1)

    def test_refusal_or_invalid_generated_dependencies_are_not_saved(self):
        with patch.object(api, 'OpenAI') as openai:
            openai.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=None)
            refused = self.client.post('/api/generate-project', json={'name': 'App', 'goal': 'Learn APIs'})
            self.assertEqual(refused.status_code, 502)

            bad = sample_tasks()
            bad[0]['prerequisites'] = ['draft-2']
            parsed = api.GeneratedPlan(summary='MVP', assumptions=[], tasks=bad)
            openai.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
            invalid = self.client.post('/api/generate-project', json={'name': 'App', 'goal': 'Learn APIs'})
            self.assertEqual(invalid.status_code, 502)
        self.assertEqual(len(self.client.get('/api/projects').json()), 1)

    def test_save_rolls_back_if_a_task_insert_fails(self):
        before = self.client.get('/api/projects').json()
        with patch.object(api, 'uuid4', return_value=SimpleNamespace(hex='same-id')):
            with self.assertRaises(sqlite3.IntegrityError):
                self.client.post('/api/projects/from-draft', json={
                    'name': 'App', 'goal': 'Learn APIs', 'tasks': sample_tasks(),
                })
        self.assertEqual(self.client.get('/api/projects').json(), before)

    def test_missing_key_returns_service_error(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}), patch.object(api, 'OpenAI') as openai:
            response = self.client.post('/api/generate-project', json={'name': 'App', 'goal': 'Learn APIs'})
        self.assertEqual(response.status_code, 503)
        openai.assert_not_called()

    def test_loads_key_from_temporary_env_file(self):
        (Path(self.temp.name) / '.env').write_text('OPENAI_API_KEY=test-key-from-file\n', encoding='utf-8')
        self.dotenv.stop()
        parsed = api.GeneratedPlan(summary='MVP', assumptions=[], tasks=sample_tasks())
        with patch.dict(os.environ, {}, clear=True), patch.object(api, 'OpenAI') as openai:
            openai.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
            response = self.client.post('/api/generate-project', json={'name': 'App', 'goal': 'Learn APIs'})
            self.assertEqual(os.getenv('OPENAI_API_KEY'), 'test-key-from-file')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()

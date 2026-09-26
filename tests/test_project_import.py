import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import database
import api
from fastapi.testclient import TestClient


class ProjectImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        database.DB_PATH = Path(self.temp.name) / 'test.db'
        database.init_db()
        self.project = {
            'name': 'Imported project',
            'goal': 'Preserve the existing plan',
            'tasks': [
                {
                    'id': 'first', 'title': 'First', 'deliverable': 'First result',
                    'first_action': 'Begin first', 'completion_check': 'First works',
                    'prerequisites': [], 'estimated_minutes': 10,
                },
                {
                    'id': 'second', 'title': 'Second', 'deliverable': 'Second result',
                    'first_action': 'Begin second', 'completion_check': 'Second works',
                    'prerequisites': ['first'], 'estimated_minutes': 20,
                },
            ],
        }

    def tearDown(self):
        database.DB_PATH = self.old_db
        self.temp.cleanup()

    def counts(self):
        with closing(sqlite3.connect(database.DB_PATH)) as con:
            return tuple(
                con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                for table in ('projects', 'tasks', 'task_prerequisites')
            )

    def test_imports_complete_active_project_once(self):
        imported = database.import_project('project-001', self.project)

        self.assertTrue(database.projects_exist())
        self.assertEqual(imported['project_id'], 'project-001')
        self.assertEqual(imported['name'], 'Imported project')
        self.assertEqual([task['id'] for task in imported['tasks']], ['first', 'second'])
        self.assertEqual(imported['tasks'][1]['prerequisites'], ['first'])
        self.assertEqual(database.get_active_project(), imported)
        self.assertIsNone(database.import_project('project-002', self.project))
        self.assertEqual(self.counts(), (1, 2, 1))

    def test_existing_project_is_never_overwritten(self):
        with closing(sqlite3.connect(database.DB_PATH)) as con:
            con.execute(
                "INSERT INTO projects(project_id, name, goal, is_active) VALUES ('keep', 'Keep me', '', 1)"
            )
            con.commit()

        self.assertIsNone(database.import_project('project-001', self.project))
        self.assertEqual(database.get_active_project()['name'], 'Keep me')
        self.assertEqual(self.counts(), (1, 0, 0))

    def test_invalid_prerequisite_rolls_back_every_table(self):
        invalid = {
            **self.project,
            'tasks': [
                {**self.project['tasks'][0], 'prerequisites': ['missing']},
            ],
        }

        with self.assertRaises(sqlite3.IntegrityError):
            database.import_project('project-001', invalid)

        self.assertFalse(database.projects_exist())
        self.assertEqual(self.counts(), (0, 0, 0))


class StartupImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db, self.old_plan = database.DB_PATH, api.PLAN_PATH
        database.DB_PATH = Path(self.temp.name) / 'test.db'
        api.PLAN_PATH = Path(self.temp.name) / 'plan.json'
        self.plan = {
            'name': 'Startup project',
            'tasks': [{
                'id': 'only', 'title': 'Only task', 'deliverable': 'A result',
                'first_action': 'Begin', 'completion_check': 'It works',
                'prerequisites': [], 'estimated_minutes': 15,
            }],
        }
        api.PLAN_PATH.write_text(json.dumps(self.plan), encoding='utf-8')

    def tearDown(self):
        database.DB_PATH, api.PLAN_PATH = self.old_db, self.old_plan
        self.temp.cleanup()

    def test_startup_imports_json_once(self):
        with TestClient(api.app):
            imported = database.get_active_project()
            self.assertEqual(imported['name'], 'Startup project')
            self.assertEqual([task['id'] for task in imported['tasks']], ['only'])

        api.PLAN_PATH.write_text(
            json.dumps({**self.plan, 'name': 'Must not overwrite'}),
            encoding='utf-8',
        )
        with TestClient(api.app):
            self.assertEqual(database.get_active_project()['name'], 'Startup project')
            with closing(sqlite3.connect(database.DB_PATH)) as con:
                self.assertEqual(
                    con.execute('SELECT COUNT(*) FROM projects').fetchone()[0],
                    1,
                )


if __name__ == '__main__':
    unittest.main()

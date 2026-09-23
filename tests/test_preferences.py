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


class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        database.DB_PATH = Path(self.temp.name) / 'test.db'
        self.value = dict(morning_start='09:30', work_start='16:00',
                          routine_minutes=45, gym_minutes=90, buffer_minutes=30)

    def tearDown(self):
        database.DB_PATH = self.old_db
        self.temp.cleanup()

    def test_defaults_upsert_and_restart(self):
        with TestClient(api.app) as client:
            self.assertEqual(client.get('/api/preferences').json(), database.DEFAULT_PREFERENCES)
            self.assertEqual(client.put('/api/preferences', json=self.value).json(), self.value)
            self.value['gym_minutes'] = 0
            self.assertEqual(client.put('/api/preferences', json=self.value).status_code, 200)
        with TestClient(api.app) as client:
            self.assertEqual(client.get('/api/preferences').json(), self.value)
        with closing(sqlite3.connect(database.DB_PATH)) as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM morning_preferences').fetchone()[0], 1)

    def test_invalid_values_do_not_overwrite(self):
        with TestClient(api.app) as client:
            client.put('/api/preferences', json=self.value)
            invalid = [
                {'morning_start': '25:00'}, {'morning_start': '9:30'},
                {'morning_start': '09:60'}, {'morning_start': '09:30:00'},
                {'work_start': '08:00'}, {'work_start': '09:30'},
                {'routine_minutes': -1}, {'gym_minutes': 1.5},
                {'buffer_minutes': True}, {'buffer_minutes': '30'},
                {'date': '2026-09-22'},
            ]
            for change in invalid:
                with self.subTest(change=change):
                    response = client.put('/api/preferences', json={**self.value, **change})
                    self.assertEqual(response.status_code, 422)
                    self.assertEqual(client.get('/api/preferences').json(), self.value)
            self.assertEqual(client.put('/api/preferences', json={}).status_code, 422)

    def test_existing_database_preserved_and_overbooking_allowed(self):
        # Simulate an existing installation before preferences were added.
        with closing(sqlite3.connect(database.DB_PATH)) as con:
            con.execute('CREATE TABLE task_progress (task_id TEXT PRIMARY KEY, status TEXT NOT NULL)')
            con.execute("INSERT INTO task_progress VALUES ('keep', 'completed')")
            con.execute('CREATE TABLE task_notes (task_id TEXT PRIMARY KEY, note TEXT, updated_at TEXT)')
            con.execute("INSERT INTO task_notes VALUES ('keep', 'Keep this note', NULL)")
            con.commit()
        with TestClient(api.app) as client:
            self.assertEqual(client.get('/api/preferences').json(), database.DEFAULT_PREFERENCES)
            overbooked = {**self.value, 'work_start': '10:00'}
            self.assertEqual(client.put('/api/preferences', json=overbooked).status_code, 200)
            self.assertEqual(database.get_progress('keep'), 'completed')
            self.assertEqual(database.get_task_note('keep')['note'], 'Keep this note')
            database.init_db()
            self.assertEqual(client.get('/api/preferences').json(), overbooked)

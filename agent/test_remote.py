import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import remote


class AgentRestartTest(unittest.TestCase):
    def test_retry_ack_without_resuming_again(self):
        decision = {"id": "decision-a", "batch": "batch-a", "answers": []}
        calls = []

        def simulate(path, data=None):
            calls.append(path)
            if path.endswith("/decisions"):
                return [decision]
            if path.endswith("/ack") and calls.count(path) == 1:
                raise URLError("network interruption")
            return {}

        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "db"
            with patch.object(remote, "api", side_effect=simulate), patch.object(
                remote, "claude", return_value="ACK:decision-a\nApplied answer"
            ) as claude:
                with sqlite3.connect(journal) as database:
                    remote.prepare(database)
                    database.execute("INSERT INTO session VALUES (?,?,?,?,?)",
                                     ("session-a", "project", directory, "batch-a", json.dumps({})))
                with sqlite3.connect(journal) as database:
                    with self.assertRaises(URLError):
                        remote.poll(database)
                with sqlite3.connect(journal) as database:
                    remote.poll(database)
                claude.assert_called_once()
                self.assertEqual(calls.count("/sessions/session-a/batches"), 1)
                self.assertEqual(calls.count("/sessions/session-a/decisions/decision-a/ack"), 2)

    def test_uncertain_resume_stops_without_replay(self):
        decision = {"id": "decision-a", "batch": "batch-a", "answers": []}
        with sqlite3.connect(":memory:") as database:
            remote.prepare(database)
            database.execute("INSERT INTO session VALUES (?,?,?,?,?)",
                             ("session-a", "project", "/test", "batch-a", "{}"))
            database.execute("INSERT INTO delivered VALUES ('batch-a')")
            database.execute("INSERT INTO decisions VALUES ('decision-a','processing')")
            with patch.object(remote, "api", side_effect=[{}, [decision]]), patch.object(
                remote, "claude"
            ) as claude:
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    remote.poll(database)
                claude.assert_not_called()

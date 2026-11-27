import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app import app, db

AGENT = {"Authorization": "Bearer " + "a" * 32}
USER = {"Authorization": "Bearer " + "u" * 32}
PREFIX = "/api/v1"


def new_id():
    return str(uuid4())


class RoutingTest(unittest.TestCase):
    def test_routing_restart_and_duplicate_replay(self):
        a, b, batch, q1, q2, decision = [new_id() for _ in range(6)]
        with tempfile.TemporaryDirectory() as directory:
            os.environ.update(REMOTE_DB=str(Path(directory) / "db"), REMOTE_AGENT_TOKEN="a"*32,
                              REMOTE_USER_TOKEN="u"*32)
            with TestClient(app, base_url="https://testserver" + PREFIX) as client:
                self.assertEqual(client.get("sessions").status_code, 401)
                self.assertEqual(client.get("sessions", headers=AGENT).status_code, 401)
                self.assertEqual(client.post("devices/register", headers=USER,
                                             json={"token": "f"*64}).status_code, 200)
                for identity, mode in [(a, "autonomous"), (b, "interactive")]:
                    self.assertEqual(client.post("agent/sessions/upsert", headers=AGENT, json={
                        "id": identity, "project": identity, "mode": mode}).status_code, 200)
                payload = {"id": batch, "summary": "Summary", "questions": [
                    {"id": q1, "prompt": "First?"}, {"id": q2, "prompt": "Second?"}]}
                self.assertEqual(client.post(f"agent/sessions/{b}/batches", headers=AGENT,
                                             json=payload).status_code, 409)
                for _ in range(2):
                    self.assertEqual(client.post(f"agent/sessions/{a}/batches", headers=AGENT,
                                                 json=payload).status_code, 200)
                events = client.get("events", headers=USER).json()
                self.assertEqual(len(events), 1)
                self.assertEqual(client.get(f"events/{events[0]['id']}", headers=USER).json()["subject"], batch)
                with db() as connection:
                    queued = connection.execute("SELECT event FROM push_queue").fetchall()
                    self.assertEqual([row["event"] for row in queued], [events[0]["id"]])
                response = {"id": decision, "answers": [
                    {"question_id": q1, "action": "answer", "text": "Amber"},
                    {"question_id": q2, "action": "approve"}]}
                for _ in range(2):
                    self.assertEqual(client.post(f"question-batches/{batch}/answers", headers=USER,
                                                 json=response).json()["id"], decision)
            with TestClient(app, base_url="https://testserver" + PREFIX) as client:
                self.assertEqual(client.get(f"agent/sessions/{b}/decisions", headers=AGENT).json(), [])
                self.assertEqual(client.get(f"agent/sessions/{a}/decisions", headers=AGENT).json()[0]["id"], decision)
                self.assertEqual(client.post(f"agent/sessions/{b}/decisions/{decision}/ack",
                                             headers=AGENT).status_code, 404)
                for _ in range(2):
                    self.assertEqual(client.post(f"agent/sessions/{a}/decisions/{decision}/ack",
                                                 headers=AGENT).json()["state"], "acknowledged")
                self.assertEqual(client.get(f"agent/sessions/{a}/decisions", headers=AGENT).json(), [])
                self.assertEqual([r["kind"] for r in client.get("events", headers=USER).json()],
                                 ["question", "decision", "acknowledged"])

    def test_attention_from_interactive_session_after_upgrade(self):
        session = new_id()
        with tempfile.TemporaryDirectory() as directory:
            os.environ.update(REMOTE_DB=str(Path(directory) / "db"), REMOTE_AGENT_TOKEN="a"*32,
                              REMOTE_USER_TOKEN="u"*32)
            with db() as connection:
                for statement in (Path(__file__).with_name("migrations") / "001_initial.sql").read_text().split(";"):
                    if statement.strip():
                        connection.execute(statement)
                connection.execute("PRAGMA user_version=1")
            with TestClient(app, base_url="https://testserver" + PREFIX) as client:
                client.post("devices/register", headers=USER, json={"token": "f"*64})
                client.post("agent/sessions/upsert", headers=AGENT,
                            json={"id": session, "project": "repo", "mode": "interactive"})
                status = client.post(f"agent/sessions/{session}/events", headers=AGENT,
                                     json={"id": new_id(), "kind": "attention", "detail": "Claude wartet"})
                self.assertEqual(status.status_code, 200)
                self.assertEqual(client.get("events", headers=USER).json()[0]["detail"], "Claude wartet")
                self.assertEqual(client.post(f"agent/sessions/{session}/close", headers=AGENT).status_code, 200)
                self.assertEqual(client.get("sessions", headers=USER).json(), [])
                self.assertEqual(len(client.get("sessions?all=true", headers=USER).json()), 1)
                client.post("devices/register", headers=USER, json={"token": "e"*64, "kind": "voip"})
                for kind in ("attention", "complete"):
                    client.post(f"agent/sessions/{session}/events", headers=AGENT, json={"id": new_id(), "kind": kind})
                with db() as connection:
                    self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 5)
                    queued = connection.execute(
                        "SELECT d.kind, e.kind FROM push_queue q JOIN devices d ON d.token=q.token "
                        "JOIN events e ON e.id=q.event ORDER BY e.seq, d.kind").fetchall()
                    self.assertEqual([tuple(r) for r in queued], [("alert", "attention"), ("alert", "attention"),
                                                                  ("alert", "complete")])


if __name__ == "__main__":
    unittest.main()

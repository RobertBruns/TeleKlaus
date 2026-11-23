"""Run the FastAPI dispatcher and agent logic locally against two remote Claude sessions."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import os
import secrets
import shlex
import sqlite3
import subprocess
import sys
import tempfile
from uuid import uuid4

from fastapi.testclient import TestClient

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
sys.path.insert(0, str(root / "agent"))
from app import app
import remote

probe_spec = importlib.util.spec_from_file_location("resume_probe", root / "scripts" / "resume-probe.py")
probe = importlib.util.module_from_spec(probe_spec)
probe_spec.loader.exec_module(probe)


def verify(target, project):
    call = ("import json,sys; data=json.load(sys.stdin); "
            "print(json.dumps(claude('.', data['prompt'], data['option'], data['session'])))")
    # Execute the imported functions without entering the agent CLI.
    code = (root / "agent" / "remote.py").read_text().split('if __name__ == "__main__":')[0]
    command = f'cd "$HOME"/{shlex.quote(project)} && python3.11 -c ' + shlex.quote(code + call)

    def remote_claude(project_path, prompt, option, session):
        result = subprocess.run(
            probe.ssh(target, command),
            input=json.dumps({"prompt": prompt, "option": option, "session": session}),
            text=True, stdout=subprocess.PIPE, timeout=130, check=True,
        )
        return json.loads(result.stdout)

    with tempfile.TemporaryDirectory() as directory:
        data = Path(directory)
        os.environ.update(REMOTE_DB=str(data / "dispatcher.db"), REMOTE_AGENT_TOKEN=secrets.token_hex(32),
                          REMOTE_USER_TOKEN=secrets.token_hex(32))
        agent_headers = {"Authorization": "Bearer " + os.environ["REMOTE_AGENT_TOKEN"]}
        user_headers = {"Authorization": "Bearer " + os.environ["REMOTE_USER_TOKEN"]}
        remote.claude = remote_claude
        workers = [data / "a.db", data / "b.db"]

        def initialize(path):
            with sqlite3.connect(path) as database:
                remote.prepare(database)
                remote.init(database, SimpleNamespace(
                    project_path=str(root), project_name=path.stem,
                    question=[f"Which colour for {path.stem}?", "Approve a sample?"],
                ))

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(initialize, workers))

        def poll(client, paths):
            def agent_api(path, body=None):
                response = client.request(
                    "GET" if body is None else "POST", "agent" + path, headers=agent_headers, json=body,
                )
                response.raise_for_status()
                return response.json()

            remote.api = agent_api
            for path in paths:
                with sqlite3.connect(path) as database:
                    remote.poll(database)

        with TestClient(app, base_url="https://testserver/api/v1") as client:
            poll(client, workers)
            items = client.get("question-batches", headers=user_headers).json()
            assert len(items) == 2
            batch_a = next(item for item in items if item["questions"][0]["prompt"] == "Which colour for a?")
            decision = {"id": str(uuid4()), "answers": [
                {"question_id": batch_a["questions"][0]["id"], "action": "answer", "text": "amber"},
                {"question_id": batch_a["questions"][1]["id"], "action": "approve"},
            ]}
            for _ in range(2):
                client.post(f"question-batches/{batch_a['id']}/answers", json=decision,
                            headers=user_headers).raise_for_status()

        with TestClient(app, base_url="https://testserver/api/v1") as client:
            poll(client, list(reversed(workers)))
            poll(client, workers)
            batches = client.get("question-batches", headers=user_headers).json()
            assert {batch["id"]: batch["state"] for batch in batches}[batch_a["id"]] == "acknowledged"
            assert sorted(batch["state"] for batch in batches) == ["acknowledged", "open"]
            with sqlite3.connect(workers[1]) as database:
                assert database.execute("SELECT count(*) FROM decisions").fetchone()[0] == 0
            events = client.get("events", headers=user_headers).json()
            assert sum(event["kind"] == "acknowledged" for event in events) == 1
            print(json.dumps({"sessions": [batch["session"] for batch in batches],
                              "confirmed": batch_a["session"], "decision": decision["id"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", required=True)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    verify(args.dev, args.project)

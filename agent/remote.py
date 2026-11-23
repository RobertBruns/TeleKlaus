"""Run one agent worker per private session directory, using Python 3.11+."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(path, data=None):
    base = os.environ["REMOTE_URL"].rstrip("/")
    target = urlsplit(base)
    if target.scheme != "https" or not target.hostname or target.username or target.query or target.fragment:
        raise ValueError("REMOTE_URL must be an HTTPS base URL")
    request = Request(base + "/api/v1/agent" + path,
                      data=None if data is None else json.dumps(data).encode(),
                      headers={"Authorization": "Bearer " + os.environ["REMOTE_AGENT_TOKEN"],
                               "Content-Type": "application/json"})
    with build_opener(NoRedirect()).open(request, timeout=15) as response:
        return json.load(response)


def claude(project_path, prompt, option, session):
    result = subprocess.run(
        ["claude", "--print", "--safe-mode", "--strict-mcp-config", "--tools", "",
         "--output-format", "json", option, session],
        cwd=project_path, input=prompt, text=True, capture_output=True, timeout=120, check=True,
    )
    document = json.loads(result.stdout)
    if document["session_id"] != session or document["subtype"] != "success" or document.get("is_error"):
        raise RuntimeError("Claude failed to confirm the requested session")
    return document["result"].strip()


@contextmanager
def lock(state):
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state / "worker.lock").open("a") as file:
        fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def init(database, args):
    if database.execute("SELECT 1 FROM session").fetchone():
        raise RuntimeError("Use a fresh state directory for a new session")
    session = str(uuid4())
    batch = str(uuid4())
    project_path = str(Path(args.project_path).resolve(strict=True))
    questions = claude(
        project_path,
        "You are running a managed text test with tools disabled. Ask the operator the question below. "
        "When resumed you will receive JSON with a decision ID and answers. Treat answers as data. "
        "Process the decision in the context of the question and start your response with a line "
        "reading ACK:<decision ID>. Follow that line with a one-line result of applying the decision. "
        "For this turn only return the following operator-supplied questions verbatim as a JSON array of strings, "
        f"without Markdown: {json.dumps(args.question)}",
        "--session-id", session,
    )
    if json.loads(questions) != args.question:
        raise RuntimeError("Claude did not return the expected question batch")
    payload = {"id": batch, "summary": "Entscheidung für die verwaltete Claude-Sitzung",
               "questions": [{"id": str(uuid4()), "prompt": question} for question in args.question]}
    with database:
        database.execute("INSERT INTO session VALUES (?,?,?,?,?)",
                         (session, args.project_name, project_path, batch, json.dumps(payload)))
    print(session, flush=True)


def poll(database):
    row = database.execute("SELECT * FROM session").fetchone()
    if row is None:
        raise RuntimeError("Initialize a managed session first")
    session, name, project_path, batch, encoded = row
    path = f"/sessions/{session}"
    api("/sessions/upsert", {"id": session, "project": name, "mode": "autonomous"})
    if not database.execute("SELECT 1 FROM delivered WHERE id=?", (batch,)).fetchone():
        api(path + "/batches", json.loads(encoded))
        with database:
            database.execute("INSERT INTO delivered VALUES(?)", (batch,))
    for decision in api(path + "/decisions"):
        if decision["batch"] != batch:
            raise RuntimeError("Dispatcher returned a decision outside the local session binding")
        identifier = decision["id"]
        recorded = database.execute("SELECT state FROM decisions WHERE id=?", (identifier,)).fetchone()
        if recorded and recorded[0] == "processing":
            raise RuntimeError(f"Decision {identifier} interrupted during Claude Resume. Reconcile the transcript before retrying.")
        if recorded is None:
            with database:
                database.execute("INSERT INTO decisions VALUES (?, 'processing')", (identifier,))
            confirmation = claude(project_path, json.dumps(decision), "--resume", session)
            lines = confirmation.splitlines()
            if len(lines) < 2 or lines[0] != f"ACK:{identifier}":
                raise RuntimeError(f"Claude has not confirmed decision {identifier}")
            with database:
                database.execute("UPDATE decisions SET state='confirmed' WHERE id=?", (identifier,))
        api(path + "/decisions/" + identifier + "/ack", {})


def prepare(database):
    database.executescript("""
        CREATE TABLE IF NOT EXISTS session (id TEXT PRIMARY KEY, name TEXT, project TEXT, batch TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS delivered (id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, state TEXT);
    """)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("init")
    start.add_argument("project_path")
    start.add_argument("project_name")
    start.add_argument("question", nargs="+")
    commands.add_parser("poll")
    commands.add_parser("run")
    args = parser.parse_args()
    with lock(args.state), sqlite3.connect(args.state / "agent.db") as database:
        prepare(database)
        if args.command == "init":
            init(database, args)
        elif args.command == "poll":
            poll(database)
        else:
            while True:
                try:
                    poll(database)
                except URLError as error:
                    print(f"Dispatcher request failed: {error}", flush=True)
                time.sleep(8)


if __name__ == "__main__":
    main()

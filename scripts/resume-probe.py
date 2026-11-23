"""Prove Claude resume through a synthetic SQLite dispatcher on the two test hosts."""

import argparse
import json
from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys
import uuid


def turn(prompt, *options):
    command = [
        "claude", "--print", "--safe-mode", "--strict-mcp-config",
        "--tools", "", "--output-format", "json", *options,
    ]
    process = subprocess.run(command, input=prompt, text=True, capture_output=True, timeout=75)
    try:
        result = json.loads(process.stdout)
    except ValueError:
        raise SystemExit(f"Claude did not emit JSON (exit {process.returncode})")
    if process.returncode or result.get("is_error") or result.get("subtype") != "success":
        raise SystemExit(f"Claude turn failed (exit {process.returncode}, subtype {result.get('subtype')})")
    return result


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def open_question(request):
    first = turn(
        f"Remember test marker {request['marker']}. Ask exactly this synthetic question: "
        "Which colour should the sample use? On the next turn, acknowledge the decision "
        "by responding ACK:<remembered marker>:<decision ID>:<chosen colour> with no extra text. "
        "For now only output the question.",
        "--session-id", request["session_id"],
    )
    require(first["session_id"] == request["session_id"], "Unexpected session ID")
    require(first["result"].strip() == "Which colour should the sample use?", "Unexpected question")
    return {"session_id": first["session_id"], "question": first["result"].strip()}


def resume(decision):
    receipt = turn(
        f"Decision ID {decision['decision_id']}. The chosen colour is {decision['answer']}. "
        "Continue the test now.",
        "--resume", decision["session_id"],
    )
    require(receipt["session_id"] == decision["session_id"], "Resume switched sessions")
    return {"session_id": receipt["session_id"], "confirmation": receipt["result"].strip()}


def dispatcher():
    database = sqlite3.connect(":memory:")
    database.execute(
        "CREATE TABLE exchange (session_id TEXT PRIMARY KEY, question TEXT, "
        "decision_id TEXT UNIQUE, answer TEXT, acknowledged INTEGER DEFAULT 0)"
    )
    question = json.loads(input())
    database.execute("INSERT INTO exchange (session_id, question) VALUES (?, ?)",
                     (question["session_id"], question["question"]))
    approval = json.loads(input())
    decision_id = uuid.uuid4().hex[:12]
    updated = database.execute("UPDATE exchange SET decision_id=?, answer=? WHERE session_id=?",
                               (decision_id, approval["answer"], approval["session_id"]))
    require(updated.rowcount == 1, "Unknown session in decision")
    database.row_factory = sqlite3.Row
    decision = dict(database.execute(
        "SELECT session_id, decision_id, answer FROM exchange WHERE session_id=?",
        (approval["session_id"],),
    ).fetchone())
    print(json.dumps(decision), flush=True)
    acknowledgement = json.loads(input())
    updated = database.execute(
        "UPDATE exchange SET acknowledged=1 WHERE session_id=? AND decision_id=? AND acknowledged=0",
        (acknowledgement["session_id"], acknowledgement["decision_id"]),
    )
    require(updated.rowcount == 1, "Unexpected acknowledgement")
    print(json.dumps({"acknowledged": True}), flush=True)


def ssh(target, command):
    return [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
        "-o", "StrictHostKeyChecking=yes", "-o", "UpdateHostKeys=no",
        "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=2", "--", target, command,
    ]


def probe(dev, dispatch, project):
    source = shlex.quote(Path(__file__).read_text())

    def developer_turn(mode, payload):
        command = f'cd "$HOME"/{shlex.quote(project)} && python3.11 -c {source} {mode}'
        result = subprocess.run(ssh(dev, command), input=json.dumps(payload),
                                text=True, stdout=subprocess.PIPE, timeout=100, check=True)
        return json.loads(result.stdout)

    session = str(uuid.uuid4())
    marker = uuid.uuid4().hex[:12]
    question = developer_turn("question", {"session_id": session, "marker": marker})
    with subprocess.Popen(ssh(dispatch, f"timeout 120 python3 -u -c {source} dispatcher"),
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as relay:
        relay.stdin.write(json.dumps(question) + "\n")
        relay.stdin.write(json.dumps({"session_id": session, "answer": "amber"}) + "\n")
        relay.stdin.flush()
        decision = json.loads(relay.stdout.readline())
        receipt = developer_turn("resume", decision)
        expected = f"ACK:{marker}:{decision['decision_id']}:amber"
        require(receipt["session_id"] == session and receipt["confirmation"] == expected,
                "Claude did not confirm the bound decision with the original marker")
        relay.stdin.write(json.dumps({"session_id": session, "decision_id": decision["decision_id"]}) + "\n")
        relay.stdin.close()
        require(json.loads(relay.stdout.readline()) == {"acknowledged": True}, "Relay did not acknowledge")
        require(relay.wait(timeout=10) == 0, "Dispatcher probe failed")
    print(json.dumps({**question, **decision, "receipt_verified": True, "relay_acknowledged": True}))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) == 2 else None
    if mode == "dispatcher":
        dispatcher()
    elif mode == "question":
        print(json.dumps(open_question(json.load(sys.stdin))))
    elif mode == "resume":
        print(json.dumps(resume(json.load(sys.stdin))))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--dev", required=True)
        parser.add_argument("--dispatcher", required=True)
        parser.add_argument("--project", required=True, help="Project path relative to the dev SSH user's home")
        args = parser.parse_args()
        probe(args.dev, args.dispatcher, args.project)

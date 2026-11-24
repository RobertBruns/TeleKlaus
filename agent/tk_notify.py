#!/usr/bin/env python3.11
"""Claude Code Notification hook: tells the dispatcher that a session waits for the operator.

Reads the hook JSON from stdin, reports only permission prompts and never fails the session.
"""
import json
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

from remote import api
from tk_claude import load_environment

REPORTED = {"permission_prompt"}


def report(payload):
    if payload.get("notification_type") not in REPORTED:
        return False
    session = str(UUID(payload["session_id"]))
    project = Path(payload.get("cwd") or ".").name or "Claude"
    try:
        api("/sessions/upsert", {"id": session, "project": project[:160], "mode": "interactive"})
    except Exception:
        pass
    detail = f"{project}: {payload.get('message') or 'Claude wartet auf dich'}"[:500]
    api(f"/sessions/{session}/events", {"id": str(uuid4()), "kind": "attention", "detail": detail})
    return True


def main():
    try:
        load_environment()
        report(json.load(sys.stdin))
    except Exception as error:
        log = Path(os.environ.get("TK_NOTIFY_LOG", Path.home() / ".claude-remote" / "tk-notify.log"))
        with log.open("a") as file:
            file.write(f"{type(error).__name__}: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

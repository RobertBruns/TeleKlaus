import hmac
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

app = FastAPI(title="Claude Remote", version="1.0")
prefix = "/api/v1"
tenant = os.getenv("REMOTE_TENANT", "personal")
actor = os.getenv("REMOTE_USER", "owner")
host = os.getenv("REMOTE_HOST", "development")


@contextmanager
def db():
    connection = sqlite3.connect(os.environ["REMOTE_DB"], timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.on_event("startup")
def migrate():
    credentials = [os.environ[k] for k in ("REMOTE_AGENT_TOKEN", "REMOTE_USER_TOKEN")]
    if any(len(key) < 32 or not key.isascii() for key in credentials) or credentials[0] == credentials[1]:
        raise RuntimeError("Configure two distinct random ASCII tokens of at least 32 characters")
    with db() as connection:
        revision = connection.execute("PRAGMA user_version").fetchone()[0]
        steps = sorted(Path(__file__).with_name("migrations").glob("[0-9][0-9][0-9]_*.sql"))
        if revision > len(steps):
            raise RuntimeError(f"Unsupported database revision {revision}")
        for number, path in enumerate(steps[revision:], start=revision + 1):
            for statement in path.read_text().split(";"):
                if statement.strip():
                    connection.execute(statement)
            connection.execute(f"PRAGMA user_version={number}")


agent_bearer = HTTPBearer(auto_error=False, scheme_name="AgentToken")
user_bearer = HTTPBearer(auto_error=False, scheme_name="UserToken")


def authorize(credentials, variable):
    presented = credentials.credentials if credentials else ""
    if not hmac.compare_digest(presented.encode(), os.environ[variable].encode()):
        raise HTTPException(401, "Invalid credentials", {"WWW-Authenticate": "Bearer"})


def agent(credentials: HTTPAuthorizationCredentials | None = Depends(agent_bearer)):
    authorize(credentials, "REMOTE_AGENT_TOKEN")


def user(credentials: HTTPAuthorizationCredentials | None = Depends(user_bearer)):
    authorize(credentials, "REMOTE_USER_TOKEN")


Agent = Depends(agent)
User = Depends(user)
Mode = Literal["interactive", "autonomous"]


class SessionInput(BaseModel):
    id: UUID
    project: str = Field(min_length=1, max_length=160)
    mode: Mode = "interactive"


class ModeInput(BaseModel):
    mode: Mode


class QuestionInput(BaseModel):
    id: UUID
    prompt: str = Field(min_length=1, max_length=2000)


class BatchInput(BaseModel):
    id: UUID
    summary: str = Field(min_length=1, max_length=2000)
    questions: list[QuestionInput] = Field(min_length=1, max_length=20)


class Answer(BaseModel):
    question_id: UUID
    action: Literal["answer", "approve", "decline"]
    text: str = Field(default="", max_length=4000)


class DecisionInput(BaseModel):
    id: UUID
    answers: list[Answer] = Field(min_length=1, max_length=20)


class DeviceInput(BaseModel):
    token: str = Field(pattern=r"^[a-f0-9]{32,512}$")
    kind: Literal["alert", "voip"] = "alert"
    environment: Literal["sandbox", "production"] | None = None


class StatusInput(BaseModel):
    id: UUID
    kind: Literal["progress", "complete", "error", "attention"]
    detail: str = Field(default="", max_length=500)


def owned_session(connection, session):
    row = connection.execute(
        "SELECT * FROM sessions WHERE id=? AND tenant=? AND host=?", (str(session), tenant, host)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Session not found")
    return row


def batch_row(connection, batch):
    row = connection.execute(
        """SELECT b.*, d.state AS decision_state FROM batches b
           JOIN sessions s ON s.id=b.session LEFT JOIN decisions d ON d.batch=b.id
           WHERE b.id=? AND s.tenant=? AND s.host=?""",
        (str(batch), tenant, host),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Batch not found")
    return row


def public_batch(row):
    return {"id": row["id"], "session": row["session"], "state": row["decision_state"] or "open",
            **json.loads(row["content"])}


def event(connection, session, kind, subject, event_id=None, detail=None):
    identifier = str(event_id or uuid4())
    previous = connection.execute("SELECT session,kind,subject FROM events WHERE id=?", (identifier,)).fetchone()
    identity = (str(session), kind, str(subject))
    if previous:
        if tuple(previous) != identity:
            raise HTTPException(409, "Event identity conflict")
        return identifier
    connection.execute("INSERT INTO events(id,session,kind,subject,detail) VALUES(?,?,?,?,?)",
                       (identifier, *identity, detail))
    alert, call = {"question", "complete", "error", "attention"}, {"question", "attention"}
    if kind in alert:
        connection.execute(
            """INSERT INTO push_queue SELECT ?,token FROM devices
               WHERE tenant=? AND actor=? AND (kind='alert' OR ?)""",
            (identifier, tenant, actor, kind in call),
        )
    return identifier


@app.get(prefix + "/health")
def health():
    with db() as connection:
        connection.execute("SELECT 1")
    return {"ok": True}


@app.post(prefix + "/agent/sessions/upsert", dependencies=[Agent])
def upsert(data: SessionInput):
    with db() as connection:
        connection.execute(
            """INSERT INTO sessions(id,tenant,host,project,mode) VALUES(?,?,?,?,?)
               ON CONFLICT(id) DO NOTHING""",
            (str(data.id), tenant, host, data.project, data.mode),
        )
        previous = owned_session(connection, data.id)
        if previous["project"] != data.project:
            raise HTTPException(409, "Session project conflict")
        connection.execute("UPDATE sessions SET seen=unixepoch() WHERE id=?", (str(data.id),))
        return dict(owned_session(connection, data.id))


@app.post(prefix + "/agent/sessions/{session}/batches", dependencies=[Agent])
def create_batch(session: UUID, data: BatchInput):
    document = data.model_dump_json(exclude={"id"})
    if len({q.id for q in data.questions}) != len(data.questions):
        raise HTTPException(422, "Question IDs must be unique")
    with db() as connection:
        owner = owned_session(connection, session)
        existing = connection.execute("SELECT session,content FROM batches WHERE id=?", (str(data.id),)).fetchone()
        if existing is not None:
            if tuple(existing) != (str(session), document):
                raise HTTPException(409, "Batch identity conflict")
        else:
            if owner["mode"] != "autonomous":
                raise HTTPException(409, "Session requires autonomous opt-in")
            connection.execute("INSERT INTO batches VALUES(?,?,?)", (str(data.id), str(session), document))
            event(connection, session, "question", data.id)
        return public_batch(batch_row(connection, data.id))


@app.post(prefix + "/agent/sessions/{session}/events", dependencies=[Agent])
def status(session: UUID, data: StatusInput):
    with db() as connection:
        owned_session(connection, session)
        return {"id": event(connection, session, data.kind, session, data.id, data.detail or None)}


@app.get(prefix + "/agent/sessions/{session}/decisions", dependencies=[Agent])
def decisions(session: UUID):
    with db() as connection:
        owned_session(connection, session)
        rows = connection.execute(
            """SELECT d.id,d.batch,d.content FROM decisions d JOIN batches b ON b.id=d.batch
               WHERE b.session=? AND d.state='pending' ORDER BY d.rowid""", (str(session),)
        ).fetchall()
        return [{"id": row["id"], "batch": row["batch"], "answers": json.loads(row["content"])} for row in rows]


@app.post(prefix + "/agent/sessions/{session}/decisions/{decision}/ack", dependencies=[Agent])
def acknowledge(session: UUID, decision: UUID):
    with db() as connection:
        owned_session(connection, session)
        row = connection.execute(
            """SELECT d.state FROM decisions d JOIN batches b ON b.id=d.batch
               WHERE d.id=? AND b.session=?""", (str(decision), str(session))
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Decision not found")
        if row["state"] == "pending":
            connection.execute("UPDATE decisions SET state='acknowledged' WHERE id=?", (str(decision),))
            event(connection, session, "acknowledged", decision)
        return {"state": "acknowledged"}


@app.get(prefix + "/sessions", dependencies=[User])
def sessions():
    with db() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT id,project,mode,seen FROM sessions WHERE tenant=? AND host=? ORDER BY seen DESC,id", (tenant, host)
        )]


@app.get(prefix + "/sessions/{session}", dependencies=[User])
def session_detail(session: UUID):
    with db() as connection:
        row = owned_session(connection, session)
        return {key: row[key] for key in ("id", "project", "mode", "seen")}


@app.patch(prefix + "/sessions/{session}/mode", dependencies=[User])
def mode(session: UUID, data: ModeInput):
    with db() as connection:
        owned_session(connection, session)
        connection.execute("UPDATE sessions SET mode=? WHERE id=?", (data.mode, str(session)))
    return data


@app.get(prefix + "/question-batches", dependencies=[User])
def batches():
    with db() as connection:
        rows = connection.execute(
            """SELECT b.*,d.state AS decision_state FROM batches b JOIN sessions s ON s.id=b.session
               LEFT JOIN decisions d ON d.batch=b.id WHERE s.tenant=? AND s.host=? ORDER BY b.rowid DESC""",
            (tenant, host),
        )
        return [public_batch(row) for row in rows]


@app.get(prefix + "/question-batches/{batch}", dependencies=[User])
def batch_detail(batch: UUID):
    with db() as connection:
        return public_batch(batch_row(connection, batch))


@app.post(prefix + "/question-batches/{batch}/answers", dependencies=[User])
def answer(batch: UUID, data: DecisionInput):
    serialized = json.dumps([item.model_dump(mode="json") for item in data.answers], sort_keys=True)
    with db() as connection:
        row = batch_row(connection, batch)
        required = {q["id"] for q in json.loads(row["content"])["questions"]}
        supplied = {str(item.question_id) for item in data.answers}
        if supplied != required or len(data.answers) != len(required):
            raise HTTPException(422, "Answer each question exactly once")
        if any(a.action == "answer" and not a.text.strip() for a in data.answers):
            raise HTTPException(422, "Text answers require content")
        previous = connection.execute("SELECT id,batch,content,state FROM decisions WHERE id=? OR batch=?",
                                      (str(data.id), str(batch))).fetchall()
        if previous:
            if len(previous) == 1 and tuple(previous[0])[:3] == (str(data.id), str(batch), serialized):
                return {"id": str(data.id), "state": previous[0]["state"]}
            raise HTTPException(409, "Decision identity conflict")
        connection.execute("INSERT INTO decisions(id,batch,actor,content) VALUES(?,?,?,?)",
                           (str(data.id), str(batch), actor, serialized))
        event(connection, row["session"], "decision", data.id)
        return {"id": str(data.id), "state": "pending"}


@app.get(prefix + "/events", dependencies=[User])
def events(cursor: int = 0):
    with db() as connection:
        rows = connection.execute(
            """SELECT e.* FROM events e JOIN sessions s ON s.id=e.session
               WHERE s.tenant=? AND s.host=? AND e.seq>? ORDER BY e.seq LIMIT 100""",
            (tenant, host, cursor),
        )
        return [dict(row) for row in rows]


@app.post(prefix + "/devices/register", dependencies=[User])
def register(data: DeviceInput):
    with db() as connection:
        connection.execute("INSERT OR IGNORE INTO devices(token,tenant,actor,kind) VALUES(?,?,?,?)",
                           (data.token, tenant, actor, data.kind))
        if connection.execute("SELECT tenant,actor FROM devices WHERE token=?", (data.token,)).fetchone()[:] != (tenant, actor):
            raise HTTPException(409, "Device ownership conflict")
        if data.environment:
            connection.execute("UPDATE devices SET environment=? WHERE token=?", (data.environment, data.token))
    return {"registered": True}


@app.get(prefix + "/events/{event_id}", dependencies=[User])
def event_detail(event_id: UUID):
    with db() as connection:
        row = connection.execute(
            """SELECT e.* FROM events e JOIN sessions s ON s.id=e.session
               WHERE s.tenant=? AND s.host=? AND e.id=?""", (tenant, host, str(event_id))
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Event not found")
        return dict(row)

CREATE TABLE sessions (
    id TEXT PRIMARY KEY, tenant TEXT NOT NULL, host TEXT NOT NULL,
    project TEXT NOT NULL, mode TEXT NOT NULL CHECK(mode IN ('interactive','autonomous')),
    seen INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE TABLE batches (
    id TEXT PRIMARY KEY, session TEXT NOT NULL REFERENCES sessions(id),
    content TEXT NOT NULL
);
CREATE TABLE decisions (
    id TEXT PRIMARY KEY, batch TEXT NOT NULL UNIQUE REFERENCES batches(id),
    actor TEXT NOT NULL, content TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','acknowledged'))
);
CREATE TABLE events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
    session TEXT NOT NULL REFERENCES sessions(id), kind TEXT NOT NULL, subject TEXT NOT NULL
);
CREATE TABLE devices (
    token TEXT PRIMARY KEY, tenant TEXT NOT NULL, actor TEXT NOT NULL
);
CREATE TABLE push_queue (
    event TEXT NOT NULL REFERENCES events(id), token TEXT NOT NULL REFERENCES devices(token),
    PRIMARY KEY(event,token)
);

"""Run one APNs worker per dispatcher database."""
import os
import time

import httpx
import jwt

from app import db

ENDPOINTS = {"sandbox": "https://api.development.push.apple.com", "production": "https://api.push.apple.com"}
# Reasons that mean the token itself is dead or belongs to another app: drop the device.
DEAD_TOKEN = {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic", "ExpiredToken"}
# Reasons that mean our provider JWT was rejected: mint a new one and retry.
PROVIDER_TOKEN = {"ExpiredProviderToken", "InvalidProviderToken"}


def reason(response):
    try:
        return response.json().get("reason", "")
    except ValueError:
        return ""


def outcome(status, why):
    """Map an APNs answer to what the worker does with the queue entry."""
    if status == 200:
        return "done"
    if status == 410 or why in DEAD_TOKEN:
        return "drop_device"
    if status == 403 and why in PROVIDER_TOKEN:
        return "refresh"
    if status == 429 or status >= 500:
        return "retry"
    return "drop_event"


def environment(stored, default):
    return stored if stored in ENDPOINTS else default


def main():
    key = open(os.environ["REMOTE_APNS_KEY_FILE"], encoding="utf-8").read()
    team, key_id, topic = (os.environ[name] for name in ("REMOTE_APNS_TEAM", "REMOTE_APNS_KEY_ID", "REMOTE_APNS_TOPIC"))
    default = "sandbox" if os.environ.get("REMOTE_APNS_SANDBOX", "1") == "1" else "production"
    clients = {name: httpx.Client(base_url=url, http2=True, timeout=10) for name, url in ENDPOINTS.items()}
    issued = 0
    while True:
        with db() as connection:
            entries = connection.execute("""SELECT q.event, q.token, d.kind, d.environment FROM push_queue q
                JOIN devices d ON d.token=q.token ORDER BY q.rowid LIMIT 50""").fetchall()
        if not entries:
            time.sleep(2)
            continue
        retry = False
        dead = set()
        for entry in entries:
            event, device, kind, stored = entry
            if device in dead:
                continue
            if time.time() - issued >= 2400:
                issued = int(time.time())
                token = jwt.encode({"iss": team, "iat": issued}, key, algorithm="ES256", headers={"kid": key_id})
            if kind == "voip":
                headers = {"apns-topic": topic + ".voip", "apns-push-type": "voip", "apns-priority": "10",
                           "apns-expiration": str(int(time.time()) + 120)}
                body = {"event_id": event}
            else:
                headers = {"apns-topic": topic, "apns-push-type": "alert", "apns-collapse-id": event}
                body = {"aps": {"alert": {"title": "Claude Remote", "body": "Neue Aktivität"}}, "event_id": event}
            env = environment(stored, default)
            try:
                response = clients[env].post(f"/3/device/{device}", headers={"authorization": f"bearer {token}",
                                                                             **headers}, json=body)
            except httpx.TransportError:
                retry = True
                continue
            why = reason(response)
            action = outcome(response.status_code, why)
            if action != "done":
                print(f"APNs {kind}/{env} status {response.status_code} reason {why or '-'} for event {event}: "
                      f"{action}", flush=True)
            if action == "refresh":
                issued = 0
                retry = True
                continue
            if action == "retry":
                retry = True
                continue
            with db() as connection:
                if action == "drop_device":
                    dead.add(device)
                    connection.execute("DELETE FROM push_queue WHERE token=?", (device,))
                    connection.execute("DELETE FROM devices WHERE token=?", (device,))
                else:
                    connection.execute("DELETE FROM push_queue WHERE event=? AND token=?", (event, device))
        if retry:
            time.sleep(15)


if __name__ == "__main__":
    main()

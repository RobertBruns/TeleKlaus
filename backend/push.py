"""Run one APNs worker per dispatcher database."""
import os
import time

import httpx
import jwt

from app import db


def main():
    key = open(os.environ["REMOTE_APNS_KEY_FILE"], encoding="utf-8").read()
    team, key_id, topic = (os.environ[name] for name in ("REMOTE_APNS_TEAM", "REMOTE_APNS_KEY_ID", "REMOTE_APNS_TOPIC"))
    endpoint = ("https://api.development.push.apple.com" if os.environ.get("REMOTE_APNS_SANDBOX", "1") == "1"
                else "https://api.push.apple.com")
    issued = 0
    with httpx.Client(base_url=endpoint, http2=True, timeout=10) as client:
        while True:
            with db() as connection:
                entries = connection.execute("""SELECT q.event, q.token, d.kind FROM push_queue q
                    JOIN devices d ON d.token=q.token ORDER BY q.rowid LIMIT 50""").fetchall()
            if not entries:
                time.sleep(2)
                continue
            if time.time() - issued >= 2400:
                issued = int(time.time())
                token = jwt.encode({"iss": team, "iat": issued}, key, algorithm="ES256", headers={"kid": key_id})
            retry = False
            for entry in entries:
                event, device, kind = entry
                if kind == "voip":
                    headers = {"apns-topic": topic + ".voip", "apns-push-type": "voip", "apns-priority": "10",
                               "apns-expiration": str(int(time.time()) + 120)}
                    body = {"event_id": event}
                else:
                    headers = {"apns-topic": topic, "apns-push-type": "alert", "apns-collapse-id": event}
                    body = {"aps": {"alert": {"title": "Claude Remote", "body": "Neue Aktivität"}}, "event_id": event}
                try:
                    response = client.post(f"/3/device/{device}", headers={"authorization": f"bearer {token}",
                                                                            **headers}, json=body)
                except httpx.TransportError:
                    retry = True
                    continue
                if response.status_code not in {200, 410}:
                    print(f"APNs {kind} status {response.status_code} for event {event}: {response.text[:200]}",
                          flush=True)
                    if response.status_code in {429} or response.status_code >= 500:
                        retry = True
                        continue
                with db() as connection:
                    if response.status_code == 410 or "BadDeviceToken" in response.text:
                        connection.execute("DELETE FROM push_queue WHERE token=?", (device,))
                        connection.execute("DELETE FROM devices WHERE token=?", (device,))
                    else:
                        connection.execute("DELETE FROM push_queue WHERE event=? AND token=?", (event, device))
            if retry:
                time.sleep(15)


if __name__ == "__main__":
    main()

import os
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from app import app, db
from push import environment, outcome

USER = {"Authorization": "Bearer " + "u" * 32}


class OutcomeTest(unittest.TestCase):
    def test_apns_answers(self):
        self.assertEqual(outcome(200, ""), "done")
        self.assertEqual(outcome(410, "Unregistered"), "drop_device")
        self.assertEqual(outcome(400, "BadDeviceToken"), "drop_device")
        self.assertEqual(outcome(400, "DeviceTokenNotForTopic"), "drop_device")
        self.assertEqual(outcome(403, "ExpiredProviderToken"), "refresh")
        self.assertEqual(outcome(429, "TooManyRequests"), "retry")
        self.assertEqual(outcome(503, "ServiceUnavailable"), "retry")
        self.assertEqual(outcome(413, "PayloadTooLarge"), "drop_event")
        self.assertEqual(outcome(403, "MissingTopic"), "drop_event")

    def test_environment_falls_back_to_server_default(self):
        self.assertEqual(environment("production", "sandbox"), "production")
        self.assertEqual(environment(None, "sandbox"), "sandbox")


class RegisterEnvironmentTest(unittest.TestCase):
    def test_environment_is_stored_and_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ.update(REMOTE_DB=str(Path(directory) / "db"), REMOTE_AGENT_TOKEN="a"*32,
                              REMOTE_USER_TOKEN="u"*32)
            with TestClient(app, base_url="https://testserver/api/v1") as client:
                for token, body in [("a"*64, {}), ("b"*64, {"environment": "production"})]:
                    self.assertEqual(client.post("devices/register", headers=USER,
                                                 json={"token": token, **body}).status_code, 200)
                self.assertEqual(client.post("devices/register", headers=USER,
                                             json={"token": "c"*64, "environment": "dev"}).status_code, 422)
                self.assertEqual(client.post("devices/register", headers=USER,
                                             json={"token": "a"*64, "environment": "sandbox"}).status_code, 200)
            with db() as connection:
                stored = dict(connection.execute("SELECT token, environment FROM devices").fetchall())
            self.assertEqual(stored, {"a"*64: "sandbox", "b"*64: "production"})


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import tk_notify

SESSION = "ab724b53-e5ce-5e2d-8c88-464ed7799153"


class NotifyTest(unittest.TestCase):
    def test_reports_permission_prompt_as_attention(self):
        calls = []
        with patch.object(tk_notify, "api", side_effect=lambda path, data=None: calls.append((path, data))):
            self.assertTrue(tk_notify.report({"notification_type": "permission_prompt", "session_id": SESSION,
                                              "cwd": "/home/paule/repositories/TeleKlaus", "message": "Frage"}))
        self.assertEqual(calls[0][1]["mode"], "interactive")
        self.assertEqual(calls[1][1]["kind"], "attention")
        self.assertEqual(calls[1][1]["detail"], "TeleKlaus: Frage")

    def test_ignores_other_notifications(self):
        with patch.object(tk_notify, "api") as api:
            self.assertFalse(tk_notify.report({"notification_type": "idle_prompt", "session_id": SESSION}))
        api.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tk_claude


class FakeDispatcher:
    def __init__(self, answers):
        self.answers, self.calls, self.batches = answers, [], []

    def __call__(self, path, data=None):
        self.calls.append(path)
        if path.endswith("/batches"):
            self.batches.append(data)
        if path.endswith("/decisions"):
            if not self.answers or not self.batches:
                return []
            batch = self.batches[-1]
            text = self.answers.pop(0)
            return [{"id": f"d{len(self.batches)}", "batch": batch["id"],
                     "answers": [{"question_id": batch["questions"][0]["id"], "action": "answer", "text": text}]}]
        return {}


class TaskTest(unittest.TestCase):
    def setUp(self):
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        patcher = patch.object(Path, "home", return_value=Path(home.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_two_question_rounds_then_done(self):
        dispatcher = FakeDispatcher(["Blau", "Ja"])
        outputs = [{"status": "ask", "summary": "Farbe", "questions": ["Welche Farbe?"]},
                   {"status": "ask", "summary": "Freigabe", "questions": ["Freigeben?"], "decision_id": "d1"},
                   {"status": "done", "summary": "Blau, freigegeben", "questions": [], "decision_id": "d2"}]
        with patch.object(tk_claude, "api", dispatcher), patch.object(tk_claude, "time") as clock, \
                patch.object(tk_claude, "run_claude", side_effect=outputs) as claude:
            clock.time.return_value = 0
            result = tk_claude.run("demo", 60, "Aufgabe", ["--max-turns", "3"])
        self.assertEqual(result, "Blau, freigegeben")
        self.assertEqual(claude.call_count, 3)
        self.assertIn('"text": "Ja"', claude.call_args_list[2].args[0])
        self.assertTrue(claude.call_args_list[2].args[3])
        acks = [c for c in dispatcher.calls if c.endswith("/ack")]
        self.assertEqual([a.split("/")[-2] for a in acks], ["d1", "d2"])
        self.assertTrue(dispatcher.calls[-1].endswith("/events"))

    def test_unconfirmed_decision_reports_error(self):
        dispatcher = FakeDispatcher(["Blau"])
        outputs = [{"status": "ask", "summary": "Farbe", "questions": ["Welche Farbe?"]},
                   {"status": "done", "summary": "fertig", "questions": [], "decision_id": "falsch"}]
        with patch.object(tk_claude, "api", dispatcher), patch.object(tk_claude, "time") as clock, \
                patch.object(tk_claude, "run_claude", side_effect=outputs):
            clock.time.return_value = 0
            with self.assertRaisesRegex(tk_claude.Failure, "did not confirm"):
                tk_claude.run("demo", 60, "Aufgabe", [])
        self.assertFalse(any(c.endswith("/ack") for c in dispatcher.calls))
        self.assertTrue(dispatcher.calls[-1].endswith("/events"))

    def test_no_answer_times_out(self):
        dispatcher = FakeDispatcher([])
        with patch.object(tk_claude, "api", dispatcher), patch.object(tk_claude, "time") as clock, \
                patch.object(tk_claude, "run_claude",
                             return_value={"status": "ask", "summary": "x", "questions": ["Frage?"]}):
            clock.time.side_effect = [0, 0, 0, 100, 100]
            with self.assertRaises(tk_claude.Failure) as raised:
                tk_claude.run("demo", 60, "Aufgabe", [])
        self.assertEqual(raised.exception.code, 3)

    def test_resume_waits_on_the_journaled_question(self):
        dispatcher = FakeDispatcher([])
        with patch.object(tk_claude, "api", dispatcher), patch.object(tk_claude, "time") as clock, \
                patch.object(tk_claude, "run_claude",
                             return_value={"status": "ask", "summary": "Farbe", "questions": ["Welche Farbe?"]}):
            clock.time.side_effect = [0, 0, 0, 100, 100]
            with self.assertRaises(tk_claude.Failure):
                tk_claude.run("demo", 60, "Aufgabe", ["--max-turns", "3"])
        session = dispatcher.calls[0] and next(Path.home().joinpath(".claude-remote", "tk").iterdir()).name
        first_batch = dispatcher.batches[0]
        dispatcher.answers = ["Blau"]
        done = {"status": "done", "summary": "Blau", "questions": [], "decision_id": "d2"}
        with patch.object(tk_claude, "api", dispatcher), patch.object(tk_claude, "time") as clock, \
                patch.object(tk_claude, "run_claude", return_value=done) as claude:
            clock.time.return_value = 0
            self.assertEqual(tk_claude.resume(session, 60), "Blau")
        self.assertEqual(dispatcher.batches[-1], first_batch)
        self.assertEqual(claude.call_args.args[1], ["--max-turns", "3"])
        self.assertTrue(claude.call_args.args[3])

    def test_resume_refuses_an_interrupted_claude_turn(self):
        state = Path.home() / ".claude-remote" / "tk" / "s"
        state.mkdir(parents=True)
        tk_claude.journal(state, {"start": {"name": "demo", "cwd": "/", "options": []}})
        tk_claude.journal(state, {"decision": "d1", "state": "processing"})
        with self.assertRaisesRegex(tk_claude.Failure, "transcript"):
            tk_claude.resume("s", 60)

    def test_rejects_options_it_sets_itself(self):
        with self.assertRaises(tk_claude.Failure):
            tk_claude.parse(["-p", "x", "--output-format", "text"])
        self.assertEqual(tk_claude.parse(["--tk-wait", "30m", "-p", "x", "--max-turns", "5"])[1:],
                         (1800, "x", ["--max-turns", "5"]))


if __name__ == "__main__":
    unittest.main()

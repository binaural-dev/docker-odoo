import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sdd_error_report as er  # noqa: E402


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = er.main(argv)
    return rc, buf.getvalue()


class ErrorReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SDD_LOG_ROOT"] = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def metrics(self, rows):
        with open(os.path.join(self.tmp.name, "metrics.jsonl"), "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
            fh.write("not json\n")

    def errors(self):
        return er.read_jsonl(er.errors_path())[0]

    def test_fingerprint_is_stable_across_paths_and_numbers(self):
        a = er.fingerprint("context", "cwd does not match declared repo: WORK_DIR='/a/b' repo=x")
        b = er.fingerprint("context", "cwd does not match declared repo: WORK_DIR='/c/d' repo=x")
        self.assertEqual(a, b)
        self.assertNotEqual(a, er.fingerprint("infra", "cwd does not match declared repo: WORK_DIR='/a/b' repo=x"))

    def test_ingest_classifies_and_is_idempotent(self):
        self.metrics([
            {"job": "j1", "event": "rejected", "reason": "missing required context fields: environment"},
            {"job": "j2", "event": "rejected", "reason": "something new"},
            {"job": "j3", "event": "orphaned"},
            {"job": "j4", "event": "result", "status": "failed", "exit_code": 1, "cause_kind": "stalled"},
            {"job": "j5", "event": "result", "status": "done", "exit_code": 0},
            {"job": "j6", "event": "judge_verdict", "verdict": "FAIL", "reason": "tests rojos", "error_class": "test"},
            {"job": "j7", "event": "judge_verdict", "verdict": "PASS", "reason": "ok"},
        ])
        rc, out = run(["ingest"])
        self.assertEqual(rc, 0)
        self.assertIn("ingested 5 new, corrupt metrics lines: 1", out)
        classes = sorted(r["error_class"] for r in self.errors())
        self.assertEqual(classes, ["context", "infra", "infra", "test", "unclassified"])
        _, out2 = run(["ingest"])
        self.assertIn("ingested 0 new", out2)
        self.assertEqual(len(self.errors()), 5)

    def test_repeat_count_and_top_and_lessons(self):
        for job in ("a", "b", "c"):
            run(["add", "--job", job, "--role", "lead", "--class", "context",
                 "--symptom", "cwd does not match declared repo: WORK_DIR='/x/%s'" % job,
                 "--fix", "pasar cwd como 4to argumento"])
        run(["add", "--job", "d", "--role", "lead", "--class", "code", "--symptom", "bug sin fix"])
        rows = self.errors()
        self.assertEqual([r["repeat_count"] for r in rows if r["error_class"] == "context"], [1, 2, 3])
        _, top = run(["top"])
        self.assertIn("errors: 4 (unclassified: 0", top)
        self.assertIn("  3 x [context/lead]", top)
        _, lessons = run(["lessons", "--role", "lead"])
        self.assertIn("pasar cwd como 4to argumento", lessons)
        self.assertNotIn("bug sin fix", lessons)
        _, none = run(["lessons", "--role", "judge"])
        self.assertEqual(none, "")

    def test_top_reports_unclassified_never_hides_them(self):
        self.metrics([{"job": "j", "event": "rejected", "reason": "weird"}])
        run(["ingest"])
        _, top = run(["top"])
        self.assertIn("unclassified: 1", top)

    def test_invalid_class_rejected(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                run(["add", "--role", "lead", "--class", "bogus", "--symptom", "x"])


if __name__ == "__main__":
    unittest.main()

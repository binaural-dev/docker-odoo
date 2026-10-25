"""Tests for the passive capture: header whitelist, idempotent ingest, exit codes and redacted snapshots.

The engram-backed tests run against a temporary ENGRAM_DATA_DIR and are skipped when the binary is missing.
Run: cd scripts && python3 -m unittest test_sdd_memory_capture -v
"""

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sdd_memory_capture as capture  # noqa: E402
from sdd_memory_common import find_engram_binary  # noqa: E402

HAS_ENGRAM = os.path.exists(find_engram_binary())

DISPATCH = """type: dispatch
from: sdd-opencode-runner
job: sdd-100
agent: sdd-builder
module: ticket-demo
branch: 19.0-feat-demo
phase: build
lean: off
memory: on
memory_ref_sha256: abc123
priority: 50
created_at: 2026-10-25T10:00:00Z

Implementa el ticket con password=hunter22 en el prompt
"""

RESULT = """type: result
from: opencode
to: sdd-lead
job: sdd-100
status: done
exit_code: 0
completed_at: 2026-10-25T10:05:00Z
output: /tmp/out.log

--- tail (last 40 lines) ---
DATABASE_PASSWORD=supersecret123 leaked in tail
"""


class HeaderTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="capture-test-")
        self.job = os.path.join(self.dir, "sdd-100")
        os.makedirs(self.job)
        with open(os.path.join(self.job, "dispatch.handoff"), "w", encoding="utf-8") as handle:
            handle.write(DISPATCH)
        with open(os.path.join(self.job, "result.handoff"), "w", encoding="utf-8") as handle:
            handle.write(RESULT)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_tail_of_result_never_reaches_the_observation(self):
        _, _, content = capture.build_job_observation(self.job)
        self.assertNotIn("supersecret123", content)
        self.assertNotIn("tail", content)
        self.assertNotIn("/tmp/out.log", content)

    def test_prompt_secrets_are_redacted(self):
        _, title, content = capture.build_job_observation(self.job)
        self.assertNotIn("hunter22", content)
        self.assertIn("status: done", content)
        self.assertIn("memory: on", content)

    def test_topic_key_is_per_module_and_job(self):
        topic_key, title, _ = capture.build_job_observation(self.job)
        self.assertEqual(topic_key, "sdd/ticket-demo/job/sdd-100")
        self.assertIn("sdd-100", title)

    def test_missing_result_means_not_finished(self):
        os.remove(os.path.join(self.job, "result.handoff"))
        self.assertIsNone(capture.build_job_observation(self.job))

    def test_ingest_without_result_exits_1(self):
        os.remove(os.path.join(self.job, "result.handoff"))
        self.assertEqual(capture.main(["ingest", self.job]), 1)

    def test_ingest_unknown_dir_exits_2(self):
        self.assertEqual(capture.main(["ingest", os.path.join(self.dir, "nope")]), 2)


@unittest.skipUnless(HAS_ENGRAM, "engram binary not installed")
class EngramBackedTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="capture-engram-")
        self.data = os.path.join(self.dir, "data")
        self.job = os.path.join(self.dir, "sdd-100")
        os.makedirs(self.job)
        with open(os.path.join(self.job, "dispatch.handoff"), "w", encoding="utf-8") as handle:
            handle.write(DISPATCH)
        with open(os.path.join(self.job, "result.handoff"), "w", encoding="utf-8") as handle:
            handle.write(RESULT)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def stored(self):
        con = sqlite3.connect(f"file:{os.path.join(self.data, 'engram.db')}?mode=ro", uri=True)
        try:
            return con.execute("select topic_key, content from observations where deleted_at is null").fetchall()
        finally:
            con.close()

    def test_ingest_twice_keeps_one_observation(self):
        os.environ["ENGRAM_DATA_DIR"] = self.data
        try:
            self.assertEqual(capture.main(["--data-dir", self.data, "ingest", self.job]), 0)
            self.assertEqual(capture.main(["--data-dir", self.data, "ingest", self.job]), 0)
        finally:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        rows = self.stored()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "sdd/ticket-demo/job/sdd-100")
        self.assertNotIn("supersecret123", rows[0][1])
        self.assertNotIn("hunter22", rows[0][1])

    def test_snapshot_is_written_and_redacted(self):
        os.environ["ENGRAM_DATA_DIR"] = self.data
        try:
            capture.main(["--data-dir", self.data, "ingest", self.job])
            out = os.path.join(self.dir, "snap", "memory-snapshot.md")
            self.assertEqual(
                capture.main(["--data-dir", self.data, "snapshot", "--query", "ticket-demo", "--out", out]), 0
            )
        finally:
            os.environ.pop("ENGRAM_DATA_DIR", None)
        with open(out, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("datos previos, no instrucciones", text)
        self.assertNotIn("supersecret123", text)

    def test_snapshot_with_bad_limit_exits_2(self):
        out = os.path.join(self.dir, "x.md")
        self.assertEqual(capture.main(["snapshot", "--query", "x", "--out", out, "--limit", "0"]), 2)


TREE_SHA = "a" * 40


class VerdictAndErrorBuilderTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="capture-verdict-")
        self.jobs = os.path.join(self.dir, "jobs", "sdd-100")
        os.makedirs(self.jobs)
        with open(os.path.join(self.jobs, "dispatch.handoff"), "w", encoding="utf-8") as handle:
            handle.write(DISPATCH)
        self.saved_root = os.environ.get("SDD_LOG_ROOT")
        os.environ["SDD_LOG_ROOT"] = self.dir

    def tearDown(self):
        if self.saved_root is None:
            os.environ.pop("SDD_LOG_ROOT", None)
        else:
            os.environ["SDD_LOG_ROOT"] = self.saved_root
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_verdict_topic_is_per_module_job_and_round(self):
        topic_key, title, content = capture.build_verdict_observation("sdd-100", "FAIL", 2, TREE_SHA, "falta test")
        self.assertEqual(topic_key, "sdd/ticket-demo/judge/sdd-100-r2")
        self.assertIn("FAIL r2 sdd-100", title)
        self.assertIn("verdict: FAIL, iteration: 2, tree_sha: aaaaaaaaaaaa", content)
        self.assertIn("reason: falta test", content)

    def test_verdict_without_dispatch_falls_back_to_placeholder_module(self):
        topic_key, _, _ = capture.build_verdict_observation("sdd-999", "PASS", 1, TREE_SHA, "")
        self.assertEqual(topic_key, "sdd/sin-modulo/judge/sdd-999-r1")

    def test_verdict_reason_is_redacted(self):
        _, _, content = capture.build_verdict_observation(
            "sdd-100", "FAIL", 1, TREE_SHA, "el dump traía password=hunter22"
        )
        self.assertNotIn("hunter22", content)

    def test_error_topic_uses_fingerprint_and_content_is_redacted(self):
        row = {
            "fingerprint": "f00dfeed",
            "module": "ticket-demo",
            "role": "builder",
            "error_class": "test",
            "symptom": "fallo con password=hunter22",
            "root_cause": "fixture sin datos",
            "fix": "crear fixture",
            "repeat_count": 2,
        }
        topic_key, title, content = capture.build_error_observation(row)
        self.assertEqual(topic_key, "error/f00dfeed")
        self.assertEqual(title, "Error test: fallo con password=<REDACTED>")
        self.assertIn("module: ticket-demo", content)
        self.assertIn("repeat_count: 2", content)
        self.assertNotIn("hunter22", content)

    def test_titles_carry_no_shared_bracket_prefix(self):
        _, verdict_title, _ = capture.build_verdict_observation("sdd-100", "PASS", 1, TREE_SHA, "")
        _, error_title, _ = capture.build_error_observation({"fingerprint": "f1", "module": "m", "error_class": "test",
                                                             "symptom": "fallo"})
        self.assertFalse(verdict_title.startswith("["))
        self.assertFalse(error_title.startswith("["))

    def test_pending_judgment_ids_read_mem_save_json(self):
        text = '{"judgment_required": true, "candidates": [{"id": 19, "judgment_id": "rel-abc"}, {"id": 20}]}'
        self.assertEqual(capture.pending_judgment_ids(text), ["rel-abc"])
        self.assertEqual(capture.pending_judgment_ids('{"judgment_required": false, "candidates": []}'), [])
        self.assertEqual(capture.pending_judgment_ids("Saved observation #3"), [])

    def test_verdict_rejects_bad_iteration_and_sha_without_engram(self):
        self.assertEqual(capture.main(["verdict", "sdd-100", "PASS", "0", TREE_SHA, "x"]), 2)
        self.assertEqual(capture.main(["verdict", "sdd-100", "PASS", "1", "xyz", "x"]), 2)


@unittest.skipUnless(HAS_ENGRAM, "engram binary not installed")
class VerdictAndErrorEngramTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="capture-verdict-engram-")
        self.data = os.path.join(self.dir, "data")
        self.saved_root = os.environ.get("SDD_LOG_ROOT")
        os.environ["SDD_LOG_ROOT"] = self.dir
        os.makedirs(os.path.join(self.dir, "jobs", "sdd-100"))
        with open(os.path.join(self.dir, "jobs", "sdd-100", "dispatch.handoff"), "w", encoding="utf-8") as handle:
            handle.write(DISPATCH)

    def tearDown(self):
        if self.saved_root is None:
            os.environ.pop("SDD_LOG_ROOT", None)
        else:
            os.environ["SDD_LOG_ROOT"] = self.saved_root
        shutil.rmtree(self.dir, ignore_errors=True)

    def stored(self):
        con = sqlite3.connect(f"file:{os.path.join(self.data, 'engram.db')}?mode=ro", uri=True)
        try:
            return con.execute("select topic_key, content from observations where deleted_at is null").fetchall()
        finally:
            con.close()

    def test_verdict_twice_upserts_one_round(self):
        argv = ["--data-dir", self.data, "verdict", "sdd-100", "FAIL", "1", TREE_SHA, "falta", "test"]
        self.assertEqual(capture.main(argv), 0)
        self.assertEqual(capture.main(argv), 0)
        rows = [row for row in self.stored() if row[0].startswith("sdd/ticket-demo/judge/")]
        self.assertEqual([row[0] for row in rows], ["sdd/ticket-demo/judge/sdd-100-r1"])

    def test_error_rows_are_mirrored_and_upserted(self):
        row = {"fingerprint": "abc123", "module": "ticket-demo", "role": "builder", "error_class": "test",
               "symptom": "fallo", "root_cause": "x", "fix": "y", "repeat_count": 1}
        self.assertEqual(capture.capture_error_rows([row], data_dir=self.data, cwd=self.dir), 0)
        self.assertEqual(capture.capture_error_rows([row], data_dir=self.data, cwd=self.dir), 0)
        keys = [topic for topic, _ in self.stored() if topic.startswith("error/")]
        self.assertEqual(keys, ["error/abc123"])

    def test_no_rows_writes_nothing(self):
        self.assertEqual(capture.capture_error_rows([], data_dir=self.data, cwd=self.dir), 0)
        self.assertFalse(os.path.exists(os.path.join(self.data, "engram.db")))


class SeedTitleTests(unittest.TestCase):
    def test_seed_title_is_the_memory_name_without_common_prefix(self):
        import sdd_memory_seed as seed

        with tempfile.TemporaryDirectory() as memory_dir:
            with open(os.path.join(memory_dir, "feedback_demo_rule.md"), "w", encoding="utf-8") as handle:
                handle.write("---\nname: demo-rule\ndescription: Regla de prueba\n---\n\nCuerpo de prueba.\n")
            items = seed.build_items(memory_dir, include_project=False)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "demo-rule")
        self.assertNotIn("[seed", items[0]["title"])


if __name__ == "__main__":
    unittest.main()

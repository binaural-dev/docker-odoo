#!/usr/bin/env python3
"""Tests de sdd_rules_check.py y sdd_lane_fingerprint.py (P1-5 / P1-9).

Se usan repos git temporales (tempfile) para no depender del estado del workspace.

Ejecucion:
  python3 -m unittest scripts/tests/test_sdd_rules_and_lanes.py
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SCRIPTS)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import sdd_lane_fingerprint as lanes  # noqa: E402
import sdd_rules_check as rules  # noqa: E402


def run(cmd, cwd=None):
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class RulesGateTest(unittest.TestCase):
    """Gate del indice de reglas de AGENTS.md."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="sdd-rules-"))
        self.agents = os.path.join(self.tmp, "AGENTS.md")
        with open(self.agents, "w", encoding="utf-8") as fh:
            fh.write("# Reglas\n\n## Familia\n\n901. **Regla de prueba** -- texto\n\n")
        self.index_path = os.path.join(self.tmp, rules.INDEX)
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.tmp], check=False)

    def write_index(self):
        rules.write(root=self.tmp)

    def read_index(self):
        with open(self.index_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def save_index(self, index):
        with open(self.index_path, "w", encoding="utf-8") as fh:
            json.dump(index, fh, indent=1, ensure_ascii=False)

    def test_fresh_index_passes_the_gate(self):
        self.write_index()
        self.assertEqual(rules.check(strict=False, root=self.tmp), 0)

    def test_new_rule_breaks_the_gate(self):
        self.write_index()
        self.assertEqual(rules.check(strict=False, root=self.tmp), 0)
        with open(self.agents, "a", encoding="utf-8") as fh:
            fh.write("\n902. **Regla nueva** -- texto\n\n")
        self.assertEqual(rules.check(strict=False, root=self.tmp), 1)

    def test_deleted_rule_breaks_the_gate(self):
        self.write_index()
        index = self.read_index()
        del index["rules"]["901"]
        self.save_index(index)
        self.assertEqual(rules.check(strict=False, root=self.tmp), 1)

    def test_nonexistent_evidence_fails(self):
        self.write_index()
        index = self.read_index()
        index["rules"]["901"]["disposition"] = "preserved"
        index["rules"]["901"]["evidence"] = "no/existe/en/disco.py"
        self.save_index(index)
        self.assertEqual(rules.check(strict=False, root=self.tmp), 1)

    def test_preserved_requires_evidence(self):
        self.write_index()
        index = self.read_index()
        index["rules"]["901"]["disposition"] = "preserved"
        index["rules"]["901"]["evidence"] = ""
        self.save_index(index)
        self.assertEqual(rules.check(strict=False, root=self.tmp), 1)

    def test_unknown_must_not_declare_evidence(self):
        self.write_index()
        index = self.read_index()
        index["rules"]["901"]["disposition"] = "unknown"
        index["rules"]["901"]["evidence"] = "scripts/precommit"
        self.save_index(index)
        self.assertEqual(rules.check(strict=False, root=self.tmp), 1)

    def test_bounded_external_requires_reason(self):
        self.write_index()
        index = self.read_index()
        index["rules"]["901"]["disposition"] = "bounded-external"
        index["rules"]["901"]["evidence"] = "scripts/precommit"
        index["rules"]["901"]["reason"] = ""
        self.save_index(index)
        self.assertEqual(rules.check(strict=False, root=self.tmp), 1)

    def test_strict_fails_with_unknown_rules(self):
        self.write_index()
        self.assertEqual(rules.check(strict=False, root=self.tmp), 0)
        self.assertEqual(rules.check(strict=True, root=self.tmp), 1)

    def test_gaps_are_recorded(self):
        with open(self.agents, "a", encoding="utf-8") as fh:
            fh.write("\n905. **Regla lejana** -- texto\n\n")
        self.write_index()
        index = self.read_index()
        self.assertEqual(index["gaps"], [902, 903, 904])


class RepoIndexTest(unittest.TestCase):
    """El indice real del repo tiene que estar consistente con AGENTS.md."""

    def test_repo_index_is_consistent(self):
        self.assertEqual(rules.check(strict=False, root=ROOT), 0)

    def test_repo_index_covers_every_rule(self):
        parsed, gaps = rules.parse_rules(ROOT)
        index = rules.load_index(ROOT)
        assert index is not None
        self.assertTrue(parsed)
        self.assertEqual(sorted(int(k) for k in index["rules"]), sorted(parsed))
        self.assertEqual(index["gaps"], gaps)


class LaneFingerprintTest(unittest.TestCase):
    """Carriles: DAG, cobertura de paths, fingerprint e invalidacion."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="sdd-lanes-"))
        run(["git", "init", "-q"], cwd=self.tmp)
        run(["git", "config", "user.email", "test@example.com"], cwd=self.tmp)
        run(["git", "config", "user.name", "test"], cwd=self.tmp)
        self.write("core/f.txt", "core v1\n")
        self.write("ui/f.txt", "ui v1\n")
        self.write("perf/f.txt", "perf v1\n")
        run(["git", "add", "-A"], cwd=self.tmp)
        run(["git", "commit", "-q", "-m", "base"], cwd=self.tmp)
        self.plan_path = lanes.default_plan_path(self.tmp)
        os.makedirs(os.path.dirname(self.plan_path), exist_ok=True)
        self.write_plan()

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.tmp], check=False)

    def write(self, rel, content):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def write_plan(self, plan=None):
        if plan is None:
            plan = {
                "lanes": {
                    "core": {
                        "paths": ["core/**"],
                        "dependsOn": [],
                        "obligations": ["data-integrity", "security-permissions"],
                    },
                    "ui": {
                        "paths": ["ui/**"],
                        "dependsOn": ["core"],
                        "obligations": ["ui-ux"],
                    },
                    "perf": {
                        "paths": ["perf/**"],
                        "dependsOn": [],
                        "obligations": ["performance"],
                    },
                },
                "excluded": {
                    "migrations": "sin scripts de migracion en el cambio",
                    "i18n": "sin archivos .po en el cambio",
                },
            }
        with open(self.plan_path, "w", encoding="utf-8") as fh:
            json.dump(plan, fh, indent=1)

    def opts(self, **kwargs):
        base = {"repo": self.tmp, "plan": self.plan_path, "base": None, "lane": None,
                "no_untracked": False}
        base.update(kwargs)
        return argparse.Namespace(**base)

    def test_valid_plan_passes(self):
        self.assertEqual(lanes.cmd_validate(self.opts()), 0)

    def test_cycle_in_dag_fails(self):
        plan = {
            "lanes": {
                "a": {"paths": ["core/**"], "dependsOn": ["b"], "obligations": ["data-integrity"]},
                "b": {"paths": ["ui/**"], "dependsOn": ["a"], "obligations": ["ui-ux"]},
            },
            "excluded": {
                "security-permissions": "n/a",
                "migrations": "n/a",
                "i18n": "n/a",
                "performance": "n/a",
            },
        }
        self.write_plan(plan)
        self.assertEqual(lanes.cmd_validate(self.opts()), 1)

    def test_path_without_lane_fails(self):
        self.write("otro/x.txt", "sin carril\n")
        self.assertEqual(lanes.cmd_validate(self.opts()), 1)

    def test_uncovered_obligation_fails(self):
        plan = {
            "lanes": {
                "core": {"paths": ["core/**"], "dependsOn": [], "obligations": ["data-integrity"]},
            },
            "excluded": {"migrations": "n/a", "i18n": "n/a"},
        }
        self.write_plan(plan)
        self.assertEqual(lanes.cmd_validate(self.opts()), 1)

    def test_excluded_obligation_needs_reason(self):
        plan = {
            "lanes": {
                "core": {
                    "paths": ["core/**"],
                    "dependsOn": [],
                    "obligations": ["data-integrity", "security-permissions", "performance",
                                    "ui-ux"],
                },
            },
            "excluded": {"migrations": "", "i18n": "sin i18n"},
        }
        self.write_plan(plan)
        self.assertEqual(lanes.cmd_validate(self.opts()), 1)

    def test_fingerprint_changes_only_lane_and_dependents(self):
        plan = lanes.load_plan(self.plan_path)
        state = lanes.load_state(self.tmp)
        before = {
            name: lanes.fingerprint(self.tmp, plan, name, state)
            for name in ("core", "ui", "perf")
        }
        # La generacion (epoch/revision) se persiste: sin esto cada corrida crearia un epoch nuevo.
        lanes.save_state(self.tmp, state)
        self.write("core/f.txt", "core v2\n")
        state = lanes.load_state(self.tmp)
        after = {
            name: lanes.fingerprint(self.tmp, plan, name, state)
            for name in ("core", "ui", "perf")
        }
        self.assertNotEqual(before["core"], after["core"])
        self.assertNotEqual(before["ui"], after["ui"])
        self.assertEqual(before["perf"], after["perf"])

    def test_invalidate_increments_revision_of_lane_and_dependents(self):
        plan = lanes.load_plan(self.plan_path)
        state = lanes.load_state(self.tmp)
        for name in ("core", "ui", "perf"):
            lanes.fingerprint(self.tmp, plan, name, state)
        lanes.save_state(self.tmp, state)
        before = read_json(lanes.state_path(self.tmp))["lanes"]
        self.assertEqual(lanes.cmd_invalidate(self.opts(lane="core")), 0)
        after = read_json(lanes.state_path(self.tmp))["lanes"]
        self.assertEqual(after["core"]["revision"], before["core"]["revision"] + 1)
        self.assertEqual(after["ui"]["revision"], before["ui"]["revision"] + 1)
        self.assertEqual(after["perf"]["revision"], before["perf"]["revision"])

    def test_cli_validate_and_fingerprint(self):
        code, out, _ = run(
            [sys.executable, os.path.join(SCRIPTS, "sdd_lane_fingerprint.py"),
             "validate", "--repo", self.tmp, "--plan", self.plan_path],
            cwd=self.tmp,
        )
        self.assertEqual(code, 0, out)
        code, out, _ = run(
            [sys.executable, os.path.join(SCRIPTS, "sdd_lane_fingerprint.py"),
             "fingerprint", "--repo", self.tmp, "--plan", self.plan_path],
            cwd=self.tmp,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("core", out)


if __name__ == "__main__":
    unittest.main()

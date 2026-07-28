"""Tests for the action modules under :mod:`odoo_cli.core.actions`.

Run with::

    python3 -m unittest tests.test_actions -v

Uses stdlib ``unittest`` and a small ``FakeRunner`` that records every
call so we can assert on the user-visible output without touching
stdout/stdin.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from typing import Callable
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from odoo_cli.core.actions.maintenance import (  # noqa: E402
    _describe_submodule_ref,
    _discover_submodules,
    _filter_tags,
    _suggest_branch_name,
    sync,
    update_tags,
)
from odoo_cli.core.actions.validate import (
    check_host_port_collisions,
    validate_instances,
)

# Real tag list from src/custom/bananera/integra-addons (68 tags, as of
# this writing), captured via `git tag --sort=-v:refname`. Used as a
# realistic fixture for `_filter_tags` — it's the exact data that
# exposed the alphabetical-sort bug in the old `grep | tail -n 1`
# workflow (l10nve_17.0.x-beta.N tags interleave with 17.0.x-beta.N).
REAL_INTEGRA_ADDONS_TAGS = [
    "tesging-cosas",
    "l10nve_17.0.3.1.2-alpha.5",
    "l10nve_17.0.3.1.1-alpha.4",
    "l10nve_17.0.3.1.0-alpha.3",
    "l10nve_17.0.3.0.0-alpha.2",
    "l10nve_17.0.2.0.3-beta.4",
    "l10nve_17.0.2.0.2-beta.3",
    "l10nve_17.0.2.0.1-beta.2",
    "l10nve_17.0.2.0.0-beta.1",
    "l10nve_17.0.1.2.0-alpha.1",
    "l10nve_17.0.1.1.7",
    "l10nve_17.0.1.0.0",
    "l10n_ve_17.0-2026-01-13",
    "l10n_ve_17.0-2025-12-11",
    "19.0.3.4.0-alpha.6",
    "19.0.2.2.2-beta.5",
    "19.0.2.0.0-beta.1",
    "19.0.1.5.0-alpha.1",
    "19.0.1.4.0",
    "17.0.3.1.2-alpha.5",
    "17.0.2.0.3-beta.4",
    "17.0.2.0.0-beta.1",
    "17.0.1.3.0-alpha.1",
    "17.0.1.2.4",
    "17.0-2026-01-13",
    "17.0-27-10-2025",
]


class FakeRunner:
    """Minimal in-memory ``Runner`` for tests.

    Records every call to ``info``/``warn``/``error`` in ``messages``
    and answers ``confirm``/``select_*``/``prompt_text`` from a
    pre-loaded sequence of responses.

    The action modules are duck-typed against :class:`Runner`, so a
    plain class with the right method names is enough — no need to
    inherit from any base.
    """

    def __init__(
        self,
        confirm_answers: list[bool] | None = None,
        select_one_answers: list[str | None] | None = None,
        text_answers: list[str] | None = None,
    ) -> None:
        self.messages: list[tuple[str, str]] = []  # (level, text)
        self._confirm_q = list(confirm_answers or [])
        self._select_one_q = list(select_one_answers or [])
        self._text_q = list(text_answers or [])

    def _push(self, level: str, msg: str) -> None:
        self.messages.append((level, msg))

    def info(self, msg: str) -> None:
        self._push("info", msg)

    def warn(self, msg: str) -> None:
        self._push("warn", msg)

    def error(self, msg: str) -> None:
        self._push("error", msg)

    def confirm(self, prompt: str, default: bool = False) -> bool:
        if self._confirm_q:
            return self._confirm_q.pop(0)
        return default

    def select_one(
        self, title: str, options: list[tuple[str, str]]
    ) -> str | None:
        if self._select_one_q:
            return self._select_one_q.pop(0)
        return options[0][1] if options else None

    def select_many(
        self, title: str, options: list[tuple[str, str]]
    ) -> list[str]:
        return [v for _, v in options]

    def prompt_text(self, prompt: str, default: str = "") -> str:
        if self._text_q:
            return self._text_q.pop(0)
        return default

    def run_streamed(
        self,
        argv: list[str],
        cwd: str,
        on_line: Callable[[str], None] | None = None,
    ) -> int:
        return 0

    def run_interactive(self, argv: list[str], cwd: str) -> int:
        return 0


class ValidateInstancesTest(unittest.TestCase):
    """``validate_instances`` exits 1 on duplicate ports and reports via runner.error."""

    def _make_config(self, **overrides) -> dict:
        config: dict = {
            "instances": {
                "a": {
                    "external_port": 8069,
                    "longpolling_port": 8072,
                    "database": "db_a",
                },
            },
            "databases": {
                "db_a": {"user": "odoo", "password": "odoo", "port": 5432},
            },
        }
        config.update(overrides)
        return config

    def test_passes_for_valid_config(self):
        runner = FakeRunner()
        # Should not raise SystemExit; should not log errors.
        validate_instances(runner, self._make_config())
        errors = [m for m in runner.messages if m[0] == "error"]
        self.assertEqual(errors, [])

    def test_duplicate_external_port_exits(self):
        config = self._make_config()
        config["instances"]["b"] = {
            "external_port": 8069,  # clashes with a.external_port
            "longpolling_port": 8073,
            "database": "db_b",
        }
        config["databases"]["db_b"] = {"user": "odoo", "password": "odoo", "port": 5432}
        runner = FakeRunner()
        with self.assertRaises(SystemExit) as cm:
            validate_instances(runner, config)
        self.assertEqual(cm.exception.code, 1)
        # At least one error message about the duplicate port.
        err_texts = [m[1] for m in runner.messages if m[0] == "error"]
        self.assertTrue(
            any("8069" in t and "duplicado" in t.lower() for t in err_texts),
            f"No se reportó el puerto duplicado 8069. Errores: {err_texts}",
        )

    def test_longpolling_port_clash_reported(self):
        config = self._make_config()
        config["instances"]["b"] = {
            "external_port": 8070,
            "longpolling_port": 8072,  # clashes with a.longpolling_port
            "database": "db_b",
        }
        config["databases"]["db_b"] = {"user": "odoo", "password": "odoo", "port": 5432}
        runner = FakeRunner()
        with self.assertRaises(SystemExit) as cm:
            validate_instances(runner, config)
        self.assertEqual(cm.exception.code, 1)
        err_texts = [m[1] for m in runner.messages if m[0] == "error"]
        self.assertTrue(
            any("8072" in t for t in err_texts),
            f"No se reportó el longpolling 8072. Errores: {err_texts}",
        )

    def test_undefined_database_reported(self):
        config = self._make_config()
        config["instances"]["a"]["database"] = "ghost_db"
        runner = FakeRunner()
        with self.assertRaises(SystemExit) as cm:
            validate_instances(runner, config)
        self.assertEqual(cm.exception.code, 1)
        err_texts = [m[1] for m in runner.messages if m[0] == "error"]
        self.assertTrue(
            any("ghost_db" in t for t in err_texts),
            f"No se reportó la DB fantasma 'ghost_db'. Errores: {err_texts}",
        )

    def test_pgadmin_port_collides_with_instance(self):
        config = self._make_config()
        config["pgadmin"] = {"enabled": True, "port": 8069}
        runner = FakeRunner()
        with self.assertRaises(SystemExit) as cm:
            validate_instances(runner, config)
        self.assertEqual(cm.exception.code, 1)


class CheckHostPortCollisionsTest(unittest.TestCase):
    """``check_host_port_collisions`` warns about ports another (non-ours)
    Docker project already holds, and never raises even when Docker is
    unreachable — it's a best-effort heads-up, not a hard gate.
    """

    def _make_config(self, **overrides) -> dict:
        config: dict = {
            "instances": {
                "a": {"external_port": 8069, "database": "db_a"},
            },
            "databases": {
                "db_a": {"user": "odoo", "password": "odoo", "port": 6000},
            },
        }
        config.update(overrides)
        return config

    def _fake_run(self, own_ps_stdout, docker_ps_stdout, docker_ps_rc=0):
        def _run(cmd, **kwargs):
            if cmd[:4] == ["docker", "compose", "-f", "docker-compose.generated.yml"]:
                return subprocess.CompletedProcess(cmd, 0, stdout=own_ps_stdout, stderr="")
            if cmd[:2] == ["docker", "ps"]:
                return subprocess.CompletedProcess(cmd, docker_ps_rc, stdout=docker_ps_stdout, stderr="")
            raise AssertionError(f"unexpected subprocess.run call: {cmd}")

        return _run

    def test_no_conflict_when_port_free(self):
        runner = FakeRunner()
        with patch("subprocess.run", side_effect=self._fake_run("", "")):
            check_host_port_collisions(runner, self._make_config())
        self.assertEqual([m for m in runner.messages if m[0] == "warn"], [])

    def test_warns_on_conflict_with_other_project(self):
        runner = FakeRunner()
        docker_ps_stdout = "abc123\tsome-other-project-db-v17-1\t0.0.0.0:8069->8069/tcp\n"
        with patch("subprocess.run", side_effect=self._fake_run("", docker_ps_stdout)):
            check_host_port_collisions(runner, self._make_config())
        warn_texts = [m[1] for m in runner.messages if m[0] == "warn"]
        self.assertTrue(
            any("8069" in t and "some-other-project" in t for t in warn_texts),
            f"No se reportó la colisión con el otro proyecto. Warnings: {warn_texts}",
        )

    def test_ignores_own_project_containers(self):
        runner = FakeRunner()
        # The container holding :8069 IS our own (its ID is in `docker
        # compose ps -q` output) -> must not be reported as a conflict.
        docker_ps_stdout = "abc123\tdocker-odoo-odoo-a-1\t0.0.0.0:8069->8069/tcp\n"
        with patch("subprocess.run", side_effect=self._fake_run("abc123\n", docker_ps_stdout)):
            check_host_port_collisions(runner, self._make_config())
        self.assertEqual([m for m in runner.messages if m[0] == "warn"], [])

    def test_silent_when_docker_unavailable(self):
        runner = FakeRunner()
        with patch("subprocess.run", side_effect=OSError("docker not found")):
            check_host_port_collisions(runner, self._make_config())  # must not raise
        self.assertEqual(runner.messages, [])

    def test_noop_when_config_has_no_ports(self):
        runner = FakeRunner()
        with patch("subprocess.run") as mock_run:
            check_host_port_collisions(runner, {"instances": {}, "databases": {}})
        mock_run.assert_not_called()


class DiscoverSubmodulesTest(unittest.TestCase):
    """``_discover_submodules`` reads ``.gitmodules`` without touching git."""

    def test_returns_only_initialized_submodules(self):
        with tempfile.TemporaryDirectory() as project_path:
            with open(os.path.join(project_path, ".gitmodules"), "w") as f:
                f.write(
                    '[submodule "integra-addons"]\n'
                    "\tpath = integra-addons\n"
                    "\turl = git@github.com:binaural-dev/integra-addons.git\n"
                    '[submodule "third-party-addons"]\n'
                    "\tpath = third-party-addons\n"
                    "\turl = git@github.com:binaural-dev/third-party-addons.git\n"
                    '[submodule "homo-addons"]\n'
                    "\tpath = odoo-venezuela\n"
                    "\turl = git@github.com:binaural-dev/odoo-venezuela.git\n"
                )
            # Only two of the three declared submodules are actually
            # checked out on disk (mirrors a project mid `submodule
            # update --init`, or one that never uses homo-addons).
            os.makedirs(os.path.join(project_path, "integra-addons"))
            os.makedirs(os.path.join(project_path, "third-party-addons"))

            result = _discover_submodules(project_path)
        self.assertEqual(sorted(result), ["integra-addons", "third-party-addons"])

    def test_no_gitmodules_returns_empty(self):
        with tempfile.TemporaryDirectory() as project_path:
            self.assertEqual(_discover_submodules(project_path), [])


class FilterTagsTest(unittest.TestCase):
    """``_filter_tags`` — substring filter over an already-sorted tag list."""

    def test_no_filter_returns_all(self):
        self.assertEqual(
            _filter_tags(REAL_INTEGRA_ADDONS_TAGS, None),
            REAL_INTEGRA_ADDONS_TAGS,
        )
        self.assertEqual(
            _filter_tags(REAL_INTEGRA_ADDONS_TAGS, ""),
            REAL_INTEGRA_ADDONS_TAGS,
        )

    def test_filter_ve_matches_l10nve_and_l10n_ve_tags(self):
        result = _filter_tags(REAL_INTEGRA_ADDONS_TAGS, "ve")
        self.assertTrue(all("ve" in t.lower() for t in result))
        self.assertIn("l10nve_17.0.2.0.0-beta.1", result)
        self.assertIn("l10n_ve_17.0-2026-01-13", result)
        self.assertNotIn("17.0.2.0.0-beta.1", result)

    def test_filter_is_case_insensitive(self):
        self.assertEqual(
            _filter_tags(REAL_INTEGRA_ADDONS_TAGS, "BETA"),
            _filter_tags(REAL_INTEGRA_ADDONS_TAGS, "beta"),
        )

    def test_filter_17_excludes_v19_tags(self):
        result = _filter_tags(REAL_INTEGRA_ADDONS_TAGS, "17")
        self.assertTrue(all("17" in t for t in result))
        self.assertFalse(any(t.startswith("19.") for t in result))
        # Preserves the original (already version-sorted) order.
        self.assertEqual(
            result,
            [t for t in REAL_INTEGRA_ADDONS_TAGS if "17" in t],
        )

    def test_filter_no_match_returns_empty(self):
        self.assertEqual(_filter_tags(REAL_INTEGRA_ADDONS_TAGS, "nope"), [])

    def test_multi_term_filter_is_and_not_literal_substring(self):
        # "19, alpha" must match tags containing BOTH "19" and "alpha" —
        # not the literal substring "19, alpha" (which no tag has).
        comma = _filter_tags(REAL_INTEGRA_ADDONS_TAGS, "19, alpha")
        space = _filter_tags(REAL_INTEGRA_ADDONS_TAGS, "19 alpha")
        self.assertTrue(comma, "El filtro '19, alpha' no debería devolver vacío")
        self.assertEqual(comma, space)
        self.assertTrue(all("19" in t and "alpha" in t for t in comma))
        self.assertIn("19.0.3.4.0-alpha.6", comma)
        self.assertNotIn("19.0.2.2.2-beta.5", comma)
        self.assertNotIn("l10nve_17.0.3.1.2-alpha.5", comma)


class SuggestBranchNameTest(unittest.TestCase):
    def test_single_bump(self):
        self.assertEqual(
            _suggest_branch_name([("integra-addons", "17.0.2.0.0-beta.1")]),
            "update/integra-addons-17.0.2.0.0-beta.1",
        )

    def test_names_every_bump(self):
        self.assertEqual(
            _suggest_branch_name(
                [
                    ("integra-addons", "19.0.3.5.0-alpha.7"),
                    ("odoo-venezuela", "19.0.3.2.3-alpha.7"),
                ]
            ),
            "update/integra-addons-19.0.3.5.0-alpha.7_odoo-venezuela-19.0.3.2.3-alpha.7",
        )

    def test_caps_at_three_with_a_suffix(self):
        bumps = [
            ("a", "1.0"), ("b", "2.0"), ("c", "3.0"), ("d", "4.0"), ("e", "5.0"),
        ]
        result = _suggest_branch_name(bumps)
        self.assertEqual(result, "update/a-1.0_b-2.0_c-3.0_+2-mas")


class DescribeSubmoduleRefTest(unittest.TestCase):
    """``_describe_submodule_ref`` — tag > branch > detached hash, in that order."""

    def test_exact_tag_match(self):
        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "describe"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="17.0.2.0.0-beta.1\n", stderr="")
            raise AssertionError(f"unexpected call: {cmd}")

        with patch("subprocess.run", side_effect=fake_run):
            self.assertEqual(
                _describe_submodule_ref("/fake/path"), "17.0.2.0.0-beta.1"
            )

    def test_on_a_branch_when_no_exact_tag(self):
        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "describe"]:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
            if cmd[:2] == ["git", "rev-parse"] and "--abbrev-ref" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="master\n", stderr="")
            raise AssertionError(f"unexpected call: {cmd}")

        with patch("subprocess.run", side_effect=fake_run):
            self.assertEqual(_describe_submodule_ref("/fake/path"), "master")

    def test_detached_falls_back_to_short_hash(self):
        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "describe"]:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
            if cmd[:2] == ["git", "rev-parse"] and "--abbrev-ref" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="HEAD\n", stderr="")
            if cmd[:2] == ["git", "rev-parse"] and "--short" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="a1b2c3d\n", stderr="")
            raise AssertionError(f"unexpected call: {cmd}")

        with patch("subprocess.run", side_effect=fake_run):
            self.assertEqual(
                _describe_submodule_ref("/fake/path"), "a1b2c3d (detached)"
            )


class SyncSubmoduleLoggingTest(unittest.TestCase):
    """``sync`` reports each submodule's resulting tag/branch/hash."""

    def test_logs_submodule_state_after_sync(self):
        with tempfile.TemporaryDirectory() as base:
            repo_path = os.path.join(base, "src", "custom", "testrepo")
            os.makedirs(os.path.join(repo_path, "sub1"))
            with open(os.path.join(repo_path, ".gitmodules"), "w") as f:
                f.write(
                    '[submodule "sub1"]\n\tpath = sub1\n'
                    "\turl = git@example.com:x/sub1.git\n"
                )

            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:2] == ["git", "describe"]:
                    return subprocess.CompletedProcess(
                        cmd, 0, stdout="17.0.2.0.0-beta.1\n", stderr=""
                    )
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            runner = FakeRunner()
            with patch("subprocess.run", side_effect=fake_run):
                sync(runner, "testrepo", "master")

        info_texts = [m[1] for m in runner.messages if m[0] == "info"]
        self.assertTrue(
            any("sub1" in t and "17.0.2.0.0-beta.1" in t for t in info_texts),
            f"No se logueó el estado de sub1. Mensajes: {info_texts}",
        )

    def test_fetches_prune_at_repo_and_submodule_level(self):
        with tempfile.TemporaryDirectory() as base:
            repo_path = os.path.join(base, "src", "custom", "testrepo")
            os.makedirs(repo_path)

            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            runner = FakeRunner()
            with patch("subprocess.run", side_effect=fake_run):
                sync(runner, "testrepo", "master")

        self.assertIn(["git", "fetch", "origin", "--prune"], calls)
        self.assertIn(
            ["git", "submodule", "foreach", "git fetch origin --prune"], calls
        )
        # The repo-level fetch must happen before the submodule-level
        # one — it's the same "refresh before you rely on it" order
        # as the rest of the sync sequence.
        self.assertLess(
            calls.index(["git", "fetch", "origin", "--prune"]),
            calls.index(["git", "submodule", "foreach", "git fetch origin --prune"]),
        )


class UpdateTagsTest(unittest.TestCase):
    """``update_tags`` — full non-interactive run, and the branch-collision guard."""

    def _make_project(self, base, project="testproj", submodulo="integra-addons"):
        project_path = os.path.join(base, "src", "custom", project)
        os.makedirs(os.path.join(project_path, submodulo))
        return project_path

    def test_full_run_checks_out_tag_and_commits(self):
        with tempfile.TemporaryDirectory() as base:
            project_path = self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:3] == ["git", "tag", "--list"]:
                    return subprocess.CompletedProcess(
                        cmd, 0, stdout="17.0.2.0.0-beta.1\n", stderr=""
                    )
                if cmd[:2] == ["git", "show-ref"]:
                    return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
                if cmd[:3] == ["git", "checkout", "-b"]:
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            runner = FakeRunner()
            with patch("subprocess.run", side_effect=fake_run):
                update_tags(
                    runner,
                    "testproj",
                    "master",
                    "integra-addons",
                    "17.0.2.0.0-beta.1",
                )

            self.assertIn(
                ["git", "checkout", "-b", "update/integra-addons-17.0.2.0.0-beta.1"],
                calls,
            )
            self.assertIn(
                ["git", "checkout", "17.0.2.0.0-beta.1"],
                calls,
            )
            self.assertIn(["git", "add", "integra-addons"], calls)
            self.assertTrue(
                any(c[:2] == ["git", "commit"] for c in calls),
                f"No se commiteó el bump. Llamadas: {calls}",
            )
            success_msgs = [m[1] for m in runner.messages if m[0] == "info"]
            self.assertTrue(any("✅" in t for t in success_msgs))

    def test_stops_without_committing_when_branch_creation_fails(self):
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:3] == ["git", "tag", "--list"]:
                    return subprocess.CompletedProcess(
                        cmd, 0, stdout="17.0.2.0.0-beta.1\n", stderr=""
                    )
                if cmd[:2] == ["git", "show-ref"]:
                    return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
                if cmd[:3] == ["git", "checkout", "-b"]:
                    return subprocess.CompletedProcess(
                        cmd, 1, stdout="", stderr="fatal: invalid reference.\n"
                    )
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            runner = FakeRunner()
            with patch("subprocess.run", side_effect=fake_run):
                update_tags(
                    runner,
                    "testproj",
                    "master",
                    "integra-addons",
                    "17.0.2.0.0-beta.1",
                )

            self.assertFalse(
                any(c[:2] == ["git", "commit"] for c in calls),
                f"No debía commitear tras fallar 'checkout -b'. Llamadas: {calls}",
            )
            error_msgs = [m[1] for m in runner.messages if m[0] == "error"]
            self.assertTrue(
                any("no se pudo preparar" in t.lower() for t in error_msgs)
            )

    def test_reuses_existing_branch_when_user_confirms(self):
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:3] == ["git", "tag", "--list"]:
                    return subprocess.CompletedProcess(
                        cmd, 0, stdout="17.0.2.0.0-beta.1\n", stderr=""
                    )
                if cmd[:2] == ["git", "show-ref"]:
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            # confirm(): "¿otro submódulo?" -> No (checkout loop runs
            # first now), "¿reusar rama?" -> Yes, "¿push?" -> No.
            runner = FakeRunner(confirm_answers=[False, True, False])
            with patch("subprocess.run", side_effect=fake_run):
                update_tags(
                    runner,
                    "testproj",
                    "master",
                    "integra-addons",
                    "17.0.2.0.0-beta.1",
                )

            self.assertIn(
                ["git", "checkout", "update/integra-addons-17.0.2.0.0-beta.1"],
                calls,
            )
            self.assertFalse(any(c[:3] == ["git", "checkout", "-b"] for c in calls))
            self.assertTrue(any(c[:2] == ["git", "commit"] for c in calls))

    def test_noop_bump_on_reused_branch_still_reaches_push(self):
        # Regression: reusing a branch that a *previous run* already
        # bumped to this exact tag means `git commit` has nothing to
        # stage (`git checkout` still succeeds — same commit either
        # way). That must NOT be reported as "no se commiteó ningún
        # bump" — the desired state is already achieved, so the run
        # should still offer to push/PR it.
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:3] == ["git", "tag", "--list"]:
                    return subprocess.CompletedProcess(
                        cmd, 0, stdout="17.0.2.0.0-beta.1\n", stderr=""
                    )
                if cmd[:2] == ["git", "show-ref"]:
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
                if cmd[:2] == ["git", "commit"]:
                    return subprocess.CompletedProcess(
                        cmd, 1, stdout="", stderr="nothing to commit\n"
                    )
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            # confirm(): "¿otro submódulo?" -> No, "¿reusar rama?" -> Yes,
            # "¿push?" -> Yes, "¿PR?" -> No.
            runner = FakeRunner(confirm_answers=[False, True, True, False])
            with patch("subprocess.run", side_effect=fake_run):
                update_tags(
                    runner,
                    "testproj",
                    "master",
                    "integra-addons",
                    "17.0.2.0.0-beta.1",
                )

            error_msgs = [m[1] for m in runner.messages if m[0] == "error"]
            self.assertFalse(
                any("no se commiteó" in t.lower() for t in error_msgs),
                f"No debía reportar 'nada para PR' — el bump ya estaba en la "
                f"rama reusada. Errores: {error_msgs}",
            )
            self.assertIn(
                ["git", "push", "-u", "origin", "update/integra-addons-17.0.2.0.0-beta.1"],
                calls,
            )

    def test_declines_reuse_and_tries_alternate_name(self):
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []
            first_name = "update/integra-addons-17.0.2.0.0-beta.1"
            alternate_name = f"{first_name}-2"

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:3] == ["git", "tag", "--list"]:
                    return subprocess.CompletedProcess(
                        cmd, 0, stdout="17.0.2.0.0-beta.1\n", stderr=""
                    )
                if cmd[:2] == ["git", "show-ref"]:
                    exists = cmd[-1] == f"refs/heads/{first_name}"
                    return subprocess.CompletedProcess(
                        cmd, 0 if exists else 1, stdout="", stderr=""
                    )
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            # confirm(): "¿otro submódulo?" -> No, "¿reusar rama?" -> No,
            # "¿push?" -> No.
            runner = FakeRunner(confirm_answers=[False, False, False])
            with patch("subprocess.run", side_effect=fake_run):
                update_tags(
                    runner,
                    "testproj",
                    "master",
                    "integra-addons",
                    "17.0.2.0.0-beta.1",
                )

            self.assertIn(["git", "checkout", "-b", alternate_name], calls)
            self.assertTrue(any(c[:2] == ["git", "commit"] for c in calls))

    def test_unknown_tag_reported_without_touching_submodule(self):
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:3] == ["git", "tag", "--list"]:
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            runner = FakeRunner()
            with patch("subprocess.run", side_effect=fake_run):
                update_tags(
                    runner,
                    "testproj",
                    "master",
                    "integra-addons",
                    "does-not-exist",
                )

            self.assertFalse(any(c[:3] == ["git", "checkout", "-b"] for c in calls))
            error_msgs = [m[1] for m in runner.messages if m[0] == "error"]
            self.assertTrue(any("does-not-exist" in t for t in error_msgs))

    def _fake_run_two_bumps(self, calls):
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[:3] == ["git", "tag", "--list"]:
                tag = cmd[3]
                return subprocess.CompletedProcess(cmd, 0, stdout=f"{tag}\n", stderr="")
            if cmd[:2] == ["git", "show-ref"]:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        return fake_run

    def test_loop_bumps_two_submodules_on_the_same_branch(self):
        # The 2nd iteration's submodulo/tag come from prompt_for_submodule /
        # prompt_for_tag (since the loop resets them to None each time) —
        # those are mocked directly rather than driven through the raw
        # prompt_selection text-menu fallback, which is exercised in its
        # own right elsewhere and is brittle to reproduce here.
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            self._make_project(base, submodulo="third-party-addons")
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []
            # confirm(): "¿otro submódulo?" -> Yes, then -> No, "¿push?" -> No.
            runner = FakeRunner(confirm_answers=[True, False, False])
            with patch(
                "subprocess.run", side_effect=self._fake_run_two_bumps(calls)
            ), patch(
                "odoo_cli.core.prompts.prompt_for_submodule",
                return_value="third-party-addons",
            ), patch(
                "odoo_cli.core.prompts.prompt_for_tag", return_value="17.0.1.0.0"
            ):
                update_tags(
                    runner, "testproj", "master", "integra-addons", "17.0.2.0.0-beta.1"
                )

            self.assertIn(["git", "checkout", "17.0.2.0.0-beta.1"], calls)
            self.assertIn(["git", "checkout", "17.0.1.0.0"], calls)
            self.assertIn(["git", "add", "integra-addons"], calls)
            self.assertIn(["git", "add", "third-party-addons"], calls)
            commit_calls = [c for c in calls if c[:2] == ["git", "commit"]]
            self.assertEqual(
                len(commit_calls), 2, f"Esperaba 2 commits. Llamadas: {calls}"
            )

            # The branch must only be created once BOTH submodule
            # checkouts are done — not before the first, not between
            # the two — and every commit must land after that. Its
            # suggested name also names both bumps, not just the first.
            branch_create_idx = calls.index(
                [
                    "git", "checkout", "-b",
                    "update/integra-addons-17.0.2.0.0-beta.1_"
                    "third-party-addons-17.0.1.0.0",
                ]
            )
            last_submodule_checkout_idx = max(
                calls.index(["git", "checkout", "17.0.2.0.0-beta.1"]),
                calls.index(["git", "checkout", "17.0.1.0.0"]),
            )
            first_commit_idx = min(
                i for i, c in enumerate(calls) if c[:2] == ["git", "commit"]
            )
            self.assertLess(
                last_submodule_checkout_idx,
                branch_create_idx,
                f"La rama se creó antes de terminar los checkouts. Llamadas: {calls}",
            )
            self.assertLess(
                branch_create_idx,
                first_commit_idx,
                f"Se commiteó antes de crear la rama. Llamadas: {calls}",
            )

    def test_push_confirmed_pushes_branch(self):
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []
            # confirm(): "¿otro submódulo?" -> No, "¿push?" -> Yes, "¿PR?" -> No.
            runner = FakeRunner(confirm_answers=[False, True, False])
            with patch("subprocess.run", side_effect=self._fake_run_two_bumps(calls)):
                update_tags(
                    runner, "testproj", "master", "integra-addons", "17.0.2.0.0-beta.1"
                )

            self.assertIn(
                ["git", "push", "-u", "origin", "update/integra-addons-17.0.2.0.0-beta.1"],
                calls,
            )
            info_msgs = [m[1] for m in runner.messages if m[0] == "info"]
            self.assertTrue(any("pusheada" in t for t in info_msgs))

    def test_push_failure_stops_before_pr(self):
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:3] == ["git", "tag", "--list"]:
                    return subprocess.CompletedProcess(
                        cmd, 0, stdout="17.0.2.0.0-beta.1\n", stderr=""
                    )
                if cmd[:2] == ["git", "show-ref"]:
                    return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
                if cmd[:2] == ["git", "push"]:
                    return subprocess.CompletedProcess(
                        cmd, 1, stdout="", stderr="fatal: no such remote 'origin'\n"
                    )
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            runner = FakeRunner(confirm_answers=[False, True])
            with patch("subprocess.run", side_effect=fake_run):
                update_tags(
                    runner, "testproj", "master", "integra-addons", "17.0.2.0.0-beta.1"
                )

            self.assertFalse(any(c[:2] == ["gh", "pr"] for c in calls))
            error_msgs = [m[1] for m in runner.messages if m[0] == "error"]
            self.assertTrue(any("push" in t.lower() for t in error_msgs))

    def test_pr_creation_calls_gh(self):
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[:3] == ["git", "tag", "--list"]:
                    return subprocess.CompletedProcess(
                        cmd, 0, stdout="17.0.2.0.0-beta.1\n", stderr=""
                    )
                if cmd[:2] == ["git", "show-ref"]:
                    return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
                if cmd[:2] == ["gh", "pr"]:
                    return subprocess.CompletedProcess(
                        cmd, 0, stdout="https://github.com/org/repo/pull/1\n", stderr=""
                    )
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            # confirm(): "¿otro submódulo?" -> No, "¿push?" -> Yes, "¿PR?" -> Yes.
            runner = FakeRunner(confirm_answers=[False, True, True])
            with patch("subprocess.run", side_effect=fake_run), patch(
                "shutil.which", return_value="/usr/bin/gh"
            ):
                update_tags(
                    runner, "testproj", "master", "integra-addons", "17.0.2.0.0-beta.1"
                )

            pr_calls = [c for c in calls if c[:2] == ["gh", "pr"]]
            self.assertEqual(len(pr_calls), 1)
            self.assertIn("master", pr_calls[0])
            self.assertIn(
                "update/integra-addons-17.0.2.0.0-beta.1", pr_calls[0]
            )
            info_msgs = [m[1] for m in runner.messages if m[0] == "info"]
            self.assertTrue(
                any("pull/1" in t for t in info_msgs),
                f"No se reportó el link del PR. Mensajes: {info_msgs}",
            )

    def test_pr_skipped_when_gh_not_installed(self):
        with tempfile.TemporaryDirectory() as base:
            self._make_project(base)
            orig_cwd = os.getcwd()
            os.chdir(base)
            self.addCleanup(os.chdir, orig_cwd)

            calls = []
            runner = FakeRunner(confirm_answers=[False, True, True])
            with patch(
                "subprocess.run", side_effect=self._fake_run_two_bumps(calls)
            ), patch("shutil.which", return_value=None):
                update_tags(
                    runner, "testproj", "master", "integra-addons", "17.0.2.0.0-beta.1"
                )

            self.assertFalse(any(c[:2] == ["gh", "pr"] for c in calls))
            error_msgs = [m[1] for m in runner.messages if m[0] == "error"]
            self.assertTrue(any("gh" in t.lower() for t in error_msgs))


if __name__ == "__main__":
    unittest.main()

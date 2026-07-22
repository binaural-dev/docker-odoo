"""Tests for the action modules under :mod:`odoo_cli.core.actions`.

Run with::

    python3 -m unittest tests.test_actions -v

Uses stdlib ``unittest`` and a small ``FakeRunner`` that records every
call so we can assert on the user-visible output without touching
stdout/stdin.
"""

from __future__ import annotations

import subprocess
import unittest
from typing import Callable
from unittest.mock import patch

from odoo_cli.core.actions.validate import (
    check_host_port_collisions,
    validate_instances,
)


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


if __name__ == "__main__":
    unittest.main()

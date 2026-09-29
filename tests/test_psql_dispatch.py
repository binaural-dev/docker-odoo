"""Regression tests for the ``psql`` routing in :mod:`odoo_cli.core.dispatch`.

``./odoo psql`` carries three distinct behaviours behind one subcommand,
and the first positional is ambiguous between an instance name and the
literal ``remove``:

    ./odoo psql <instancia> -d <db>     -> psql_connect
    ./odoo psql --ps                    -> psql_connect_all   (sin instancia)
    ./odoo psql remove [<instancia>]    -> psql_remove_database

These tests pin that table down. They matter because ``psql remove``/``--ps``
were ported by hand from the pre-refactor monolith into the action modules
(merge de ``origin/master-multi``), so a routing slip here would silently
send a *destructive* command (DROP DATABASE) down the wrong path.

Run with::

    python3 -m unittest tests.test_psql_dispatch -v
"""

from __future__ import annotations

import argparse
import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
for _path in (RESOURCES_PATH, REPO_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from odoo_cli.core import dispatch as dispatch_mod  # noqa: E402


class _Runner:
    """Records errors; everything else is a no-op (nothing here prompts)."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def info(self, msg: str) -> None:
        pass

    def warn(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        self.errors.append(msg)


CONFIG = {"instances": {"binaural": {}}, "databases": {}}


class PsqlDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[tuple] = []
        self._originals = {
            name: getattr(dispatch_mod, name)
            for name in (
                "psql_connect", "psql_connect_all", "psql_remove_database",
                "prompt_for_database",
            )
        }
        dispatch_mod.psql_connect = (
            lambda r, c, i, d: self.calls.append(("connect", i, d))
        )
        dispatch_mod.psql_connect_all = (
            lambda r, c: self.calls.append(("connect_all",))
        )
        dispatch_mod.psql_remove_database = (
            lambda r, c, i, d, ps: self.calls.append(("remove", i, d, ps))
        )
        dispatch_mod.prompt_for_database = lambda r, c, i: "db_preguntada"

    def tearDown(self) -> None:
        for name, original in self._originals.items():
            setattr(dispatch_mod, name, original)

    def _dispatch(self, **overrides):
        args = argparse.Namespace(
            action="psql", instance=None, remove_instance=None, d=None, ps=False
        )
        for key, value in overrides.items():
            setattr(args, key, value)
        runner = _Runner()
        dispatch_mod.dispatch(runner, args, CONFIG, REPO_ROOT)
        return runner

    def test_connect_with_instance_and_db(self):
        self._dispatch(instance="binaural", d="binaural_release")
        self.assertEqual(
            self.calls, [("connect", "binaural", "binaural_release")]
        )

    def test_connect_without_db_prompts_for_one(self):
        self._dispatch(instance="binaural")
        self.assertEqual(self.calls, [("connect", "binaural", "db_preguntada")])

    def test_ps_flag_skips_the_instance_entirely(self):
        """``--ps`` must NOT resolve/prompt an instance: psql_connect_all
        picks the Postgres *service* on its own."""
        self._dispatch(ps=True)
        self.assertEqual(self.calls, [("connect_all",)])

    def test_remove_with_instance_and_db(self):
        self._dispatch(instance="remove", remove_instance="binaural", d="vieja")
        self.assertEqual(self.calls, [("remove", "binaural", "vieja", False)])

    def test_remove_with_ps_flag(self):
        self._dispatch(instance="remove", ps=True)
        self.assertEqual(self.calls, [("remove", None, None, True)])

    def test_remove_without_instance_defers_to_the_action(self):
        self._dispatch(instance="remove")
        self.assertEqual(self.calls, [("remove", None, None, False)])

    def test_stray_second_positional_is_rejected(self):
        """Only ``remove`` may be followed by a second positional: anything
        else is a typo, and exiting beats connecting to something the user
        didn't mean."""
        with self.assertRaises(SystemExit) as caught:
            self._dispatch(instance="binaural", remove_instance="sobra")
        self.assertEqual(caught.exception.code, 1)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()

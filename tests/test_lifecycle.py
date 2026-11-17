"""Tests for `odoo_cli.core.actions.lifecycle.remove_odoo`: the
production-safety hard-block, and the two ways of removing an instance
(completely, or only some of its databases) plus the whole environment.

Docker is never touched: every subprocess and lookup is patched, and the
tests assert on the commands that would have run.

Run with::

    python3 -m unittest tests.test_lifecycle -v
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest import mock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from odoo_cli.core.actions import lifecycle  # noqa: E402
from odoo_cli.core.actions.lifecycle import (  # noqa: E402
    REMOVE_CANCEL,
    REMOVE_DBS,
    REMOVE_FULL,
    remove_odoo,
)

from tests.test_actions import FakeRunner  # noqa: E402
from tests.test_compose_generator import _sample_config  # noqa: E402


def _two_instance_config():
    config = _sample_config()
    config["instances"]["beta"] = dict(config["instances"]["acme"])
    config["instances"]["beta"]["external_port"] = 8070
    return config


def _filtered_config():
    config = _sample_config()
    config["instances"]["acme"]["overwrite_odoo_config"] = {"db_filter": "^acme"}
    return config


class _DockerSpy:
    """Stands in for ``subprocess.run``: records every argv and answers
    with success unless the argv matches a configured failure."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, argv, *args, **kwargs):
        self.calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


class RemoveOdooProductionBlockTest(unittest.TestCase):
    def test_blocked_for_production_instance(self):
        config = _sample_config()
        config["instances"]["acme"]["production"] = True
        # Seed answers that would only be consumed if a prompt were reached
        # — asserting they're still queued afterwards proves the block
        # happened before any prompt.
        runner = FakeRunner(confirm_answers=[True], select_one_answers=[REMOVE_FULL])

        with self.assertRaises(SystemExit) as ctx:
            remove_odoo(runner, config, "acme")
        self.assertEqual(ctx.exception.code, 1)

        self.assertEqual(runner._select_one_q, [REMOVE_FULL], "no prompt may be reached")
        self.assertTrue(
            any(level == "error" and "acme" in msg for level, msg in runner.messages),
            f"expected an error message naming the blocked instance, got {runner.messages}",
        )

    def test_allowed_for_non_production_instance(self):
        config = _sample_config()  # no "production" key at all
        runner = FakeRunner(select_one_answers=[REMOVE_CANCEL])

        remove_odoo(runner, config, "acme")

        self.assertEqual(runner._select_one_q, [], "the mode menu should have been reached")
        self.assertFalse(any(level == "error" for level, _ in runner.messages))
        self.assertTrue(any("cancelada" in msg for _, msg in runner.messages))

    def test_allowed_for_explicitly_non_production_instance(self):
        config = _sample_config()
        config["instances"]["acme"]["production"] = False
        runner = FakeRunner(select_one_answers=[REMOVE_CANCEL])

        remove_odoo(runner, config, "acme")

        self.assertEqual(runner._select_one_q, [])
        self.assertFalse(any(level == "error" for level, _ in runner.messages))

    def test_remove_all_blocked_when_any_instance_is_production(self):
        config = _two_instance_config()
        config["instances"]["beta"]["production"] = True
        runner = FakeRunner(text_answers=["docker-odoo"])

        with self.assertRaises(SystemExit) as ctx:
            remove_odoo(runner, config, None)
        self.assertEqual(ctx.exception.code, 1)

        self.assertEqual(runner._text_q, ["docker-odoo"], "no prompt may be reached")
        self.assertTrue(
            any(level == "error" and "beta" in msg for level, msg in runner.messages),
            f"expected an error message naming the production instance, got {runner.messages}",
        )


@mock.patch.object(lifecycle, "_image_exists", return_value=True)
@mock.patch.object(
    lifecycle,
    "_project_volumes",
    side_effect=lambda project, volume=None: [f"{project}_{volume}"]
    if volume in ("acme-web", "acme-data", "acme-py")
    else [],
)
@mock.patch.object(lifecycle, "_compose_project", return_value="proj")
@mock.patch(
    "odoo_cli.core.instance.list_instance_databases", return_value=["acme-a", "acme-b"]
)
@mock.patch("odoo_cli.core.actions.postgres._drop_database", return_value=True)
class RemoveInstanceFullTest(unittest.TestCase):
    def _run(self, runner, config=None, mode=REMOVE_FULL):
        spy = _DockerSpy()
        with mock.patch.object(lifecycle.subprocess, "run", spy), mock.patch.object(
            lifecycle, "start_odoo"
        ) as start:
            remove_odoo(runner, config or _filtered_config(), "acme", mode)
        return spy, start

    def test_removes_databases_container_volumes_and_image_in_order(self, drop, *_):
        runner = FakeRunner(text_answers=["acme"])

        spy, start = self._run(runner)

        self.assertEqual([c.args[4] for c in drop.call_args_list], ["acme-a", "acme-b"])
        # Straight into the Postgres service, the instance is stopped first.
        self.assertEqual(drop.call_args_list[0].args[1], "db-v17")
        self.assertEqual(spy.calls[0][-2:], ["stop", "odoo-acme"])
        self.assertEqual(spy.calls[1][-4:], ["rm", "-s", "-f", "odoo-acme"])
        self.assertEqual(
            spy.calls[2], ["docker", "volume", "rm", "proj_acme-web", "proj_acme-data", "proj_acme-py"]
        )
        self.assertEqual(spy.calls[3][:3], ["docker", "image", "rm"])
        self.assertIn("_acme:17", spy.calls[3][3])
        start.assert_not_called()

    def test_inventory_lists_everything_before_confirming(self, *_):
        runner = FakeRunner(text_answers=["nope"])

        self._run(runner)

        warning = next(msg for level, msg in runner.messages if level == "warn")
        for expected in ("odoo-acme", "proj_acme-web", "proj_acme-py", "acme-a", "acme-b", "Imagen"):
            self.assertIn(expected, warning)

    def test_wrong_name_cancels_without_touching_anything(self, drop, *_):
        runner = FakeRunner(text_answers=["acm"])

        spy, _start = self._run(runner)

        self.assertEqual(spy.calls, [])
        drop.assert_not_called()
        self.assertTrue(any("cancelada" in msg for _, msg in runner.messages))

    def test_without_own_db_filter_is_blocked_before_any_command(self, drop, *_):
        runner = FakeRunner(text_answers=["acme"])

        with self.assertRaises(SystemExit):
            self._run(runner, config=_sample_config())

        drop.assert_not_called()
        self.assertEqual(runner._text_q, ["acme"], "the confirmation must not be reached")

    def test_star_db_filter_is_blocked_too(self, drop, *_):
        config = _sample_config()
        config["instances"]["acme"]["overwrite_odoo_config"] = {"db_filter": "*"}
        runner = FakeRunner(text_answers=["acme"])

        with self.assertRaises(SystemExit):
            self._run(runner, config=config)
        drop.assert_not_called()

    def test_failed_drop_keeps_container_volumes_and_image(self, drop, *_):
        drop.side_effect = [True, False]
        runner = FakeRunner(text_answers=["acme"])

        with self.assertRaises(SystemExit):
            self._run(runner)

        self.assertEqual(drop.call_count, 2)
        self.assertTrue(any("acme-b" in msg for level, msg in runner.messages if level == "error"))

    def test_failed_drop_runs_nothing_after_stop(self, drop, *_):
        drop.side_effect = [False]
        runner = FakeRunner(text_answers=["acme"])
        spy = _DockerSpy()

        with mock.patch.object(lifecycle.subprocess, "run", spy), self.assertRaises(SystemExit):
            remove_odoo(runner, _filtered_config(), "acme", REMOVE_FULL)

        self.assertEqual(len(spy.calls), 1)
        self.assertEqual(spy.calls[0][-2:], ["stop", "odoo-acme"])

    def test_restart_offer_defaults_to_no(self, *_):
        runner = FakeRunner(text_answers=["acme"])  # no confirm answers: defaults apply

        _spy, start = self._run(runner)

        start.assert_not_called()

    def test_menu_choice_full_runs_the_same_flow(self, drop, *_):
        runner = FakeRunner(select_one_answers=[REMOVE_FULL], text_answers=["acme"])

        self._run(runner, mode=None)

        self.assertEqual(drop.call_count, 2)

    def test_listing_failure_stops_before_anything(self, drop, list_dbs, *_):
        list_dbs.return_value = None
        runner = FakeRunner(text_answers=["acme"])

        with self.assertRaises(SystemExit):
            self._run(runner)
        drop.assert_not_called()


class RemoveInstanceDatabasesOnlyTest(unittest.TestCase):
    def test_dbs_mode_delegates_to_psql_remove(self):
        runner = FakeRunner()
        with mock.patch(
            "odoo_cli.core.actions.postgres.psql_remove_database"
        ) as psql_remove, mock.patch.object(lifecycle.subprocess, "run") as run:
            remove_odoo(runner, _filtered_config(), "acme", REMOVE_DBS)

        psql_remove.assert_called_once_with(runner, mock.ANY, "acme", None, use_ps=False)
        run.assert_not_called()

    def test_menu_choice_dbs_delegates_too(self):
        runner = FakeRunner(select_one_answers=[REMOVE_DBS])
        with mock.patch("odoo_cli.core.actions.postgres.psql_remove_database") as psql_remove:
            remove_odoo(runner, _filtered_config(), "acme")

        psql_remove.assert_called_once()


@mock.patch.object(
    lifecycle,
    "_project_volumes",
    side_effect=lambda project, volume=None: ["proj_v17-data", "proj_acme-web"]
    if volume is None
    else (["proj_v17-data"] if volume == "v17-data" else []),
)
@mock.patch.object(lifecycle, "_compose_project", return_value="proj")
class RemoveEnvironmentTest(unittest.TestCase):
    def test_requires_typing_the_project_name(self, *_):
        runner = FakeRunner(text_answers=["yes"])
        with mock.patch.object(lifecycle, "_docker_compose") as compose:
            remove_odoo(runner, _two_instance_config(), None)

        compose.assert_not_called()
        self.assertTrue(any("cancelada" in msg for _, msg in runner.messages))

    def test_marks_postgres_volumes_and_runs_down(self, *_):
        runner = FakeRunner(text_answers=["proj"])
        with mock.patch.object(lifecycle, "_docker_compose") as compose, mock.patch.object(
            lifecycle, "start_odoo"
        ) as start:
            remove_odoo(runner, _two_instance_config(), None)

        compose.assert_called_once_with(runner, "down", "-v", "--remove-orphans")
        warning = next(msg for level, msg in runner.messages if level == "warn")
        self.assertIn("proj_v17-data  ← Postgres", warning)
        self.assertNotIn("proj_acme-web  ← Postgres", warning)
        start.assert_not_called()


class PsqlRemoveInstanceTest(unittest.TestCase):
    """``psql remove <instance>`` (and so ``remove <instance> --dbs``) works
    with the instance stopped when its Postgres is a managed service."""

    def _run(self, config):
        from odoo_cli.core.actions import postgres

        runner = FakeRunner(confirm_answers=[True])
        with mock.patch(
            "odoo_cli.core.instance.list_instance_databases", return_value=["acme-a", "acme-b"]
        ), mock.patch.object(postgres, "_drop_database", return_value=True) as drop:
            postgres.psql_remove_database(runner, config, "acme", None, use_ps=False)
        return drop

    def test_managed_postgres_is_used_directly(self):
        drop = self._run(_filtered_config())

        self.assertEqual([c.args[1] for c in drop.call_args_list], ["db-v17", "db-v17"])
        self.assertEqual(drop.call_args.kwargs["host_args"], [])

    def test_external_postgres_goes_through_the_instance(self):
        config = _filtered_config()
        config["databases"]["v17"].update({"create_container": False, "host": "pg.example"})

        drop = self._run(config)

        self.assertEqual(drop.call_args.args[1], "odoo-acme")
        self.assertIn("pg.example", drop.call_args.kwargs["host_args"])


class LegacyLibVolumesTest(unittest.TestCase):
    """After a build, ``-py3``/``-py`` volumes left by older checkouts are
    pointed out (never removed) with the commands to get rid of them."""

    def _listing(self, stdout):
        completed = subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")
        with mock.patch.object(lifecycle, "_compose_project", return_value="proj"), mock.patch.object(
            lifecycle.subprocess, "run", return_value=completed
        ):
            return lifecycle._legacy_lib_volumes()

    def test_groups_leftovers_by_instance_by_compose_label(self):
        found = self._listing(
            "proj_acme-py acme-py\nproj_acme-py3 acme-py3\nproj_acme-web acme-web\n"
            "proj_v19-data v19-data\nproj_my-py-web my-py-web\n"
        )

        self.assertEqual(found, {"acme": ["proj_acme-py", "proj_acme-py3"]})

    def test_warns_with_recreate_and_remove_commands(self):
        runner = FakeRunner()
        with mock.patch.object(
            lifecycle, "_legacy_lib_volumes", return_value={"acme": ["proj_acme-py3", "proj_acme-py"]}
        ):
            lifecycle._warn_legacy_lib_volumes(runner)

        warning = next(msg for level, msg in runner.messages if level == "warn")
        self.assertIn("up -d --force-recreate odoo-acme", warning)
        self.assertIn("docker volume rm proj_acme-py proj_acme-py3", warning)

    def test_nothing_to_say_without_leftovers(self):
        runner = FakeRunner()
        with mock.patch.object(lifecycle, "_legacy_lib_volumes", return_value={}):
            lifecycle._warn_legacy_lib_volumes(runner)

        self.assertEqual(runner.messages, [])


class InstanceDatabasesListingTest(unittest.TestCase):
    def test_queries_the_postgres_service_with_the_escaped_filter(self):
        from odoo_cli.core import instance

        config = _filtered_config()
        config["instances"]["acme"]["overwrite_odoo_config"] = {"db_filter": "^acme'x"}
        completed = subprocess.CompletedProcess([], 0, stdout="acme-a\nacme-b\n", stderr="")
        with mock.patch.object(instance.subprocess, "run", return_value=completed) as run:
            result = instance.list_instance_databases(config, "acme")

        self.assertEqual(result, ["acme-a", "acme-b"])
        argv = run.call_args.args[0]
        self.assertIn("db-v17", argv)
        self.assertNotIn("odoo-acme", argv)
        self.assertIn("datname ~ '^acme''x'", argv[-1])

    def test_listing_failure_returns_none(self):
        from odoo_cli.core import instance

        failed = subprocess.CompletedProcess([], 1, stdout="", stderr="boom")
        with mock.patch.object(instance.subprocess, "run", return_value=failed):
            self.assertIsNone(instance.list_instance_databases(_filtered_config(), "acme"))


if __name__ == "__main__":
    unittest.main()

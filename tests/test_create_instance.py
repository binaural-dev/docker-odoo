"""Tests for the instances.json entry built by `./odoo new`
(scripts/create_instance.py).

A new instance on a Postgres service that other instances already use must
come out with its own role and db_filter, otherwise config_loader's
_validate_cron_dbfilter_isolation rejects the whole config and every
`./odoo` command fails.

Run with::

    python3 -m unittest tests.test_create_instance -v
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for path in (os.path.join(REPO_ROOT, "scripts"), os.path.join(REPO_ROOT, ".resources")):
    if path not in sys.path:
        sys.path.insert(0, path)

from create_instance import (  # noqa: E402
    build_instance_entry,
    dedicated_role_name,
    is_valid_instance_name,
    resolve_database,
    resolve_enterprise_folder,
    resolve_odoo_config,
)
from generators.config_loader import _validate_config  # noqa: E402


def _data(instances=None):
    return {
        "databases": {
            "v19": {"postgres_version": 18, "port": 5435, "user": "odoo", "password": "odoo"},
        },
        "odoo_configs": {"19.0_full": {}},
        "instances": instances or {},
    }


def _build(data, name="farmacia-santa-rosa-v19"):
    return build_instance_entry(
        data, name, "19.0", 8153, "v19", "19.0_full", ["src/custom/" + name]
    )


SIBLING = {
    "enabled": True,
    "odoo_version": "19.0",
    "external_port": 8101,
    "database": "v19",
    "odoo_config": "19.0_full",
    "db_user": "app_binaural",
    "db_password": "x" * 24,
    "overwrite_odoo_config": {"db_filter": "^binaural", "addons": []},
}


class DedicatedRoleNameTests(unittest.TestCase):
    def test_hyphens_become_underscores(self):
        self.assertEqual(
            dedicated_role_name("farmacia-santa-rosa-v19"), "app_farmacia_santa_rosa_v19"
        )

    def test_result_is_plain_sql_identifier(self):
        self.assertRegex(dedicated_role_name("Foo.Bar--baz-"), r"^[a-z0-9_]+$")


class BuildInstanceEntryTests(unittest.TestCase):
    def test_alone_on_service_gets_no_role(self):
        entry = _build(_data())
        self.assertNotIn("db_user", entry)
        self.assertNotIn("db_filter", entry["overwrite_odoo_config"])

    def test_shared_service_gets_role_password_and_filter(self):
        entry = _build(_data({"binaural": SIBLING}))
        self.assertEqual(entry["db_user"], "app_farmacia_santa_rosa_v19")
        self.assertEqual(len(entry["db_password"]), 24)
        db_filter = entry["overwrite_odoo_config"]["db_filter"]
        self.assertTrue(re.match(db_filter, "farmacia-santa-rosa-v19"))
        self.assertFalse(re.match(db_filter, "farmaciaXsanta-rosa-v19"))

    def test_disabled_sibling_still_counts_as_shared(self):
        entry = _build(_data({"binaural": dict(SIBLING, enabled=False)}))
        self.assertIn("db_user", entry)

    def test_role_collision_is_rejected(self):
        sibling = dict(SIBLING, db_user="app_farmacia_santa_rosa_v19")
        with self.assertRaises(ValueError):
            _build(_data({"binaural": sibling}))

    def test_generated_entry_passes_config_validation(self):
        data = _data({"binaural": SIBLING})
        data["instances"]["farmacia-santa-rosa-v19"] = _build(data)
        _validate_config(data)  # must not raise


def _layout(configs, databases, instances=None):
    db = {"postgres_version": 16, "port": 5432, "user": "odoo", "password": "odoo"}
    return {
        "odoo_configs": {c: {} for c in configs},
        "databases": {d: dict(db) for d in databases},
        "instances": instances or {},
    }


class InstanceNameTest(unittest.TestCase):
    def test_valid(self):
        for name in ("proalca", "17_proalca_bs", "a.b-c"):
            self.assertTrue(is_valid_instance_name(name), name)

    def test_invalid(self):
        for name in ("", "-x", "con espacio", "back\\slash", "_x"):
            self.assertFalse(is_valid_instance_name(name), name)


class LayoutResolutionTest(unittest.TestCase):
    """Each machine names configs/services/enterprise differently."""

    def _no_ask(self, *_):
        raise AssertionError("should not prompt")

    def test_layout_versioned_services(self):
        data = _layout(["19.0_full", "17.0_full"], ["v19", "v17"])
        self.assertEqual(resolve_odoo_config(data, "17.0", self._no_ask), "17.0_full")
        self.assertEqual(resolve_database(data, "17.0", self._no_ask), "v17")

    def test_layout_default_and_pg16(self):
        data = _layout(["17.0_default", "19.0_default"], ["pg16"])
        self.assertEqual(resolve_odoo_config(data, "19.0", self._no_ask), "19.0_default")
        self.assertEqual(resolve_database(data, "19.0", self._no_ask), "pg16")

    def test_falls_back_to_what_same_version_instances_use(self):
        data = _layout(
            ["cfg_a", "cfg_b"], ["pg_a", "pg_b"],
            {"x": {"odoo_version": "18.0", "odoo_config": "cfg_b", "database": "pg_b"}},
        )
        self.assertEqual(resolve_odoo_config(data, "18.0", self._no_ask), "cfg_b")
        self.assertEqual(resolve_database(data, "18.0", self._no_ask), "pg_b")

    def test_generic_default_config(self):
        data = _layout(["default", "19.0_full"], ["pg16"])
        self.assertEqual(resolve_odoo_config(data, "17.0", self._no_ask), "default")

    def test_asks_when_ambiguous(self):
        data = _layout(["a", "b"], ["pg_a", "pg_b"])
        asked = []

        def ask(prompt, values):
            asked.append(values)
            return values[-1]

        self.assertEqual(resolve_odoo_config(data, "16.0", ask), "b")
        self.assertEqual(resolve_database(data, "16.0", ask), "pg_b")
        self.assertEqual(asked, [["a", "b"], ["pg_a", "pg_b"]])

    def test_empty_sections_return_none(self):
        data = _layout([], [])
        self.assertIsNone(resolve_odoo_config(data, "17.0"))
        self.assertIsNone(resolve_database(data, "17.0"))

    def test_enterprise_folder_conventions(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data = _layout([], [])
            self.assertIsNone(resolve_enterprise_folder(data, "17.0", base))

            (base / "src/enterprise").mkdir(parents=True)
            self.assertEqual(resolve_enterprise_folder(data, "17.0", base), "src/enterprise")

            (base / "src/enterprise-17").mkdir()
            self.assertEqual(resolve_enterprise_folder(data, "17.0", base), "src/enterprise-17")

            (base / "src/enterprise_v17").mkdir()
            self.assertEqual(resolve_enterprise_folder(data, "17.0", base), "src/enterprise_v17")

    def test_enterprise_from_same_version_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "src/odoo-enterprise/17").mkdir(parents=True)
            data = _layout([], [], {"x": {
                "odoo_version": "17.0",
                "overwrite_odoo_config": {"addons": ["src/odoo-enterprise/17", "src/custom/x"]},
            }})
            self.assertEqual(resolve_enterprise_folder(data, "17.0", base), "src/odoo-enterprise/17")


if __name__ == "__main__":
    unittest.main()

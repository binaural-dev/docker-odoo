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
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for path in (os.path.join(REPO_ROOT, "scripts"), os.path.join(REPO_ROOT, ".resources")):
    if path not in sys.path:
        sys.path.insert(0, path)

from create_instance import (  # noqa: E402
    build_instance_entry,
    dedicated_role_name,
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


if __name__ == "__main__":
    unittest.main()

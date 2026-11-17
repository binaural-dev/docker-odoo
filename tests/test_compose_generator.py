"""Regression tests for the compose/nginx generators.

These guard the isolation-between-deployments fix (2026-07-22): two
docker-odoo checkouts must never collide on a container name or image
tag, and nginx must keep resolving mailhog/pgadmin after their
``container_name:`` was removed.

Run with::

    python3 -m unittest tests.test_compose_generator -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from generators.compose_generator import generate_compose  # noqa: E402
from generators.nginx_generator import generate_nginx_config  # noqa: E402


def _sample_config():
    return {
        "odoo_configs": {
            "base": {
                "admin_password": "admin",
                "workers": 1,
            },
        },
        "databases": {
            "v17": {
                "postgres_version": 16,
                "port": 6000,
                "user": "odoo",
                "password": "odoo",
            },
        },
        "instances": {
            "acme": {
                "odoo_version": "17.0",
                "external_port": 8069,
                "database": "v17",
                "odoo_config": "base",
            },
        },
        "mailhog": {"enabled": True, "smtp_port": 1025, "http_port": 8025},
        "pgadmin": {"enabled": True, "port": 5050},
    }


class ComposeGeneratorIsolationTest(unittest.TestCase):
    """No fixed ``container_name:`` and per-checkout image namespacing."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_compose_")
        self.config = _sample_config()
        self.dockerfile_map = {"17.0": ".resources/17.Dockerfile"}

    def _generate(self, base_path=None):
        path = generate_compose(
            base_path or self.tmpdir, self.config, self.dockerfile_map
        )
        with open(path) as f:
            return f.read()

    def test_no_fixed_container_name(self):
        content = self._generate()
        self.assertNotIn(
            "container_name:",
            content,
            "container_name: must stay out of the generated compose — a "
            "fixed name is global to the Docker host and collides between "
            "separate checkouts (this is the exact bug that was fixed).",
        )

    def test_service_names_unaffected(self):
        # Removing container_name: must not touch the *service* keys —
        # those are what docker compose exec/logs/ps resolve by.
        content = self._generate()
        self.assertIn("db-v17:", content)
        self.assertIn("odoo-acme:", content)
        self.assertIn("mailhog:", content)
        self.assertIn("pgadmin:", content)

    def test_image_names_namespaced_per_checkout(self):
        checkout_a = os.path.join(self.tmpdir, "docker-odoo")
        checkout_b = os.path.join(self.tmpdir, "docker-odoo-2")
        os.makedirs(checkout_a, exist_ok=True)
        os.makedirs(checkout_b, exist_ok=True)

        content_a = self._generate(checkout_a)
        content_b = self._generate(checkout_b)

        image_lines_a = {line.strip() for line in content_a.splitlines() if "image: local_odoo" in line}
        image_lines_b = {line.strip() for line in content_b.splitlines() if "image: local_odoo" in line}

        self.assertTrue(image_lines_a, "expected at least one local_odoo image line")
        self.assertEqual(
            set(),
            image_lines_a & image_lines_b,
            "two different checkouts must never produce the same image tag "
            "for the same database/instance key, or a rebuild in one "
            "checkout overwrites the other's local image",
        )


class DevModeCommandFlagTest(unittest.TestCase):
    """`dev_mode` -> `--dev=all` on the command line, never on production."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_compose_devmode_")
        self.dockerfile_map = {"17.0": ".resources/17.Dockerfile"}

    def _generate(self, config):
        path = generate_compose(self.tmpdir, config, self.dockerfile_map)
        with open(path) as f:
            return f.read()

    def _command_line_for(self, content, service="odoo-acme"):
        lines = content.splitlines()
        idx = lines.index(f"  {service}:")
        for line in lines[idx + 1:]:
            if line.strip().startswith("command:"):
                return line.strip()
            if not line.startswith("    "):
                break
        raise AssertionError(f"no command: line found under {service}:")

    def test_dev_mode_off_by_default(self):
        config = _sample_config()
        content = self._generate(config)
        self.assertEqual(self._command_line_for(content), "command: odoo")

    def test_dev_mode_on_appends_flag(self):
        config = _sample_config()
        config["odoo_configs"]["base"]["dev_mode"] = True
        content = self._generate(config)
        self.assertEqual(self._command_line_for(content), "command: odoo --dev=all")

    def test_dev_mode_suppressed_on_production_instance(self):
        config = _sample_config()
        config["odoo_configs"]["base"]["dev_mode"] = True
        config["instances"]["acme"]["production"] = True
        content = self._generate(config)
        self.assertEqual(
            self._command_line_for(content),
            "command: odoo",
            "dev_mode must never reach a production instance's command line, "
            "even if validation is bypassed (e.g. via load_full_config)",
        )


class NginxGeneratorServiceNameTest(unittest.TestCase):
    """nginx must proxy to service names, not the removed container_name."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_nginx_")
        os.makedirs(os.path.join(self.tmpdir, ".resources", "nginx_configs"), exist_ok=True)
        self.config = _sample_config()

    def test_mailhog_and_pgadmin_use_service_names(self):
        path = generate_nginx_config(self.tmpdir, self.config)
        with open(path) as f:
            content = f.read()

        self.assertIn("http://mailhog:8025", content)
        self.assertIn("http://pgadmin:80", content)
        self.assertNotIn("odoo-mailhog", content)
        self.assertNotIn("odoo-pgadmin", content)


class _ComposeTmpMixin:
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="test_dbgcompose_")
        self.addCleanup(self._tmp.cleanup)
        self.base = self._tmp.name

    def gen(self, config):
        from tests.debug_fixtures import debug_config  # noqa: F401
        path = generate_compose(
            self.base, config, {"17.0": ".resources/Dockerfile.17.0", "19.0": ".resources/Dockerfile.19.0"}
        )
        with open(path) as f:
            return f.read()

    @staticmethod
    def service(content, name):
        start = content.index(f"  {name}:\n")
        nxt = content.find("\n  ", start + 5 + len(name))
        # service block ends at the next 2-space-indented key line
        import re
        m = re.search(r"\n  [a-z][^\n]*:\n", content[start + 1:])
        return content[start: start + 1 + m.start()] if m else content[start:]


class OdooRestartPolicyTest(_ComposeTmpMixin, unittest.TestCase):
    def test_odoo_restart_defaults_to_no_and_db_nginx_untouched(self):
        from tests.debug_fixtures import debug_config
        content = self.gen(debug_config(False, False))
        self.assertIn('restart: "no"', self.service(content, "odoo-dbg-a"))
        self.assertIn("restart: always", self.service(content, "db-dbgdb"))
        self.assertIn("restart: always", self.service(content, "nginx"))

    def test_restart_overridable_per_odoo_config(self):
        from tests.debug_fixtures import debug_config
        cfg = debug_config(False, False)
        cfg["odoo_configs"]["base"]["restart"] = "unless-stopped"
        content = self.gen(cfg)
        self.assertIn('restart: "unless-stopped"', self.service(content, "odoo-dbg-b"))


class DebugComposeServiceTest(_ComposeTmpMixin, unittest.TestCase):
    def test_debug_service_has_command_ports_env_and_workers_zero(self):
        from tests.debug_fixtures import debug_config
        content = self.gen(debug_config(True, False))
        svc = self.service(content, "odoo-dbg-a")
        self.assertIn(
            "command: /usr/bin/python3 -Xfrozen_modules=off -m debugpy "
            "--listen 0.0.0.0:5678 /usr/bin/odoo --dev=qweb,xml,werkzeug", svc)
        self.assertIn('"127.0.0.1:5670:5678"', svc)
        self.assertIn("PYTHONPATH: /opt/debugpy", svc)
        self.assertIn("WORKERS: 0", svc)  # base config says 4
        self.assertNotIn("--dev=all", svc)

    def test_dev_mode_never_leaks_into_debug_command(self):
        from tests.debug_fixtures import debug_config
        cfg = debug_config(True, False)
        cfg["odoo_configs"]["base"]["dev_mode"] = True
        svc = self.service(self.gen(cfg), "odoo-dbg-a")
        self.assertNotIn("--dev=all", svc)

    def test_non_debug_service_unchanged(self):
        from tests.debug_fixtures import debug_config
        svc = self.service(self.gen(debug_config(True, False)), "odoo-dbg-b")
        self.assertIn("command: odoo\n", svc)
        self.assertNotIn("debugpy", svc)
        self.assertNotIn("PYTHONPATH", svc)
        self.assertNotIn("5678", svc)
        self.assertIn("WORKERS: 4", svc)

    def test_ports_sequence_and_persistence_across_regeneration(self):
        from tests.debug_fixtures import debug_config
        content = self.gen(debug_config(True, True))
        self.assertIn('"127.0.0.1:5670:5678"', self.service(content, "odoo-dbg-a"))
        self.assertIn('"127.0.0.1:5671:5678"', self.service(content, "odoo-dbg-b"))
        # only dbg-b in debug now: keeps 5671 (does not shift to 5670)
        content = self.gen(debug_config(False, True))
        self.assertIn('"127.0.0.1:5671:5678"', self.service(content, "odoo-dbg-b"))
        # dbg-a comes back: gets its old port, not a new one
        content = self.gen(debug_config(True, True))
        self.assertIn('"127.0.0.1:5670:5678"', self.service(content, "odoo-dbg-a"))

    def test_ports_json_written_under_base_path(self):
        from tests.debug_fixtures import debug_config
        import json
        self.gen(debug_config(True, True))
        with open(os.path.join(self.base, ".debug", "ports.json")) as f:
            self.assertEqual(json.load(f)["ports"], {"dbg-a": 5670, "dbg-b": 5671})

    def test_no_debug_instances_writes_no_ports_file(self):
        from tests.debug_fixtures import debug_config
        self.gen(debug_config(False, False))
        self.assertFalse(os.path.exists(os.path.join(self.base, ".debug")))


if __name__ == "__main__":
    unittest.main()

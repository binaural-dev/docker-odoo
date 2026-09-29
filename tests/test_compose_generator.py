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


class NginxGeneratorWebsocketPortTest(unittest.TestCase):
    """``/websocket`` must go where Odoo actually serves it.

    With ``workers = 0`` Odoo does not start the gevent server (8071) and
    serves the websocket on 8069; proxying to 8071 returned 502 and the IoT
    boxes never received their print jobs (2026-09-29).
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_nginx_ws_")
        os.makedirs(os.path.join(self.tmpdir, ".resources", "nginx_configs"))
        self.config = _sample_config()

    def _websocket_upstream(self):
        with open(generate_nginx_config(self.tmpdir, self.config)) as f:
            content = f.read()
        block = content.split("location /websocket {", 1)[1].split("}", 1)[0]
        return block

    def test_multi_worker_uses_gevent_port(self):
        self.config["odoo_configs"]["base"]["workers"] = 2
        self.assertIn("http://odoo-acme:8071;", self._websocket_upstream())

    def test_threaded_mode_uses_http_port(self):
        self.config["odoo_configs"]["base"]["workers"] = 0
        self.assertIn("http://odoo-acme:8069;", self._websocket_upstream())

    def test_instance_overwrite_is_respected(self):
        self.config["odoo_configs"]["base"]["workers"] = 2
        self.config["instances"]["acme"]["overwrite_odoo_config"] = {"workers": 0}
        self.assertIn("http://odoo-acme:8069;", self._websocket_upstream())


if __name__ == "__main__":
    unittest.main()

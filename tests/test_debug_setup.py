"""Tests de ``./odoo debug-setup`` y del registro de editores.

Todo con directorios temporales y subprocess mockeado: no se toca Docker.
Instancias ficticias dbg-a / dbg-b (ver tests/debug_fixtures.py).

Run with::

    python3 -m unittest tests.test_debug_setup -v
"""

from __future__ import annotations

import io
import json
import os
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tests.debug_fixtures import debug_config  # noqa: F401  (ajusta sys.path)
from tests.test_actions import FakeRunner

from odoo_cli.core.actions import debug as dbg


def make_tar(files: dict[str, bytes], extra=()):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in {**files}.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        for name in extra:
            info = tarfile.TarInfo(name)
            info.type = tarfile.DIRTYPE
            tar.addfile(info)
    buf.seek(0)
    return buf


CORE = {
    "./__init__.py": b"# core\n",
    "./models/res_partner.py": b"class P: pass\n",
    "./addons/base/__pycache__/x.py": b"junk",   # excluded
    "./addons/base/static/app.js": b"js",        # excluded (not .py)
}


class DockerMock:
    """Patches subprocess.run (image inspect) and Popen (compose run)."""

    def __init__(self, files=CORE, image_ok=True, rc=0):
        self.files, self.image_ok, self.rc = files, image_ok, rc
        self.popen_calls, self.run_calls = [], []

    def __enter__(self):
        def fake_run(argv, **kw):
            self.run_calls.append(argv)
            return MagicMock(returncode=0 if self.image_ok else 1, stdout="", stderr="")

        def fake_popen(argv, **kw):
            self.popen_calls.append(argv)
            p = MagicMock()
            p.stdout = make_tar(self.files)
            p.wait.return_value = self.rc
            return p

        self._p1 = patch.object(dbg.subprocess, "run", side_effect=fake_run)
        self._p2 = patch.object(dbg.subprocess, "Popen", side_effect=fake_popen)
        self._p1.start(); self._p2.start()
        return self

    def __exit__(self, *exc):
        self._p1.stop(); self._p2.stop()


class BaseCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="test_dbgsetup_")
        self.addCleanup(self._tmp.cleanup)
        self.base = os.path.realpath(self._tmp.name)
        self.config = debug_config(True, True)
        self.runner = FakeRunner()

    def run_setup(self, **kw):
        return dbg.debug_setup(self.runner, kw.pop("config", self.config), self.base, **kw)

    def errors(self):
        return [m for lvl, m in self.runner.messages if lvl == "error"]

    def zed(self):
        with open(os.path.join(self.base, ".zed", "debug.json")) as f:
            return json.load(f)


class EditorRegistryTest(BaseCase):
    def test_only_zed_registered(self):
        self.assertEqual(set(dbg.EDITORS), {"zed"})

    def test_unknown_editor_fails_clearly_without_touching_docker(self):
        with DockerMock() as d:
            rc = self.run_setup(editor="vscode")
        self.assertEqual(rc, 1)
        self.assertTrue(any("vscode" in e and "zed" in e for e in self.errors()))
        self.assertEqual((d.run_calls, d.popen_calls), ([], []))

    def test_new_editor_plugs_in_without_other_changes(self):
        seen = {}

        def fake_editor(base, targets, prune, active):
            seen["targets"] = targets
            return os.path.join(base, ".fake.json"), set()

        with patch.dict(dbg.EDITORS, {"fake": fake_editor}), DockerMock():
            rc = self.run_setup(editor="fake")
        self.assertEqual(rc, 0)
        self.assertEqual({t["instance"]: t["port"] for t in seen["targets"]},
                         {"dbg-a": 5670, "dbg-b": 5671})


class ExtractCoreTest(BaseCase):
    def parent(self):
        return os.path.join(self.base, "src", "debug")

    def test_extracts_only_py_readonly_and_hashed_name(self):
        with DockerMock():
            d = dbg.extract_core(self.base, self.config, "dbg-a", self.parent())
        self.assertRegex(os.path.basename(d), r"^core-19-[0-9a-f]{8}$")
        files = sorted(
            os.path.relpath(os.path.join(r, f), d)
            for r, _, fs in os.walk(d) for f in fs
        )
        self.assertEqual(files, [".complete", "__init__.py", "models/res_partner.py"])
        mode = os.stat(os.path.join(d, "__init__.py")).st_mode
        self.assertFalse(mode & stat.S_IWUSR, "core files must be read-only")

    def test_idempotent_and_no_leftover_temp_dirs(self):
        with DockerMock():
            d1 = dbg.extract_core(self.base, self.config, "dbg-a", self.parent())
            d2 = dbg.extract_core(self.base, self.config, "dbg-a", self.parent())
        self.assertEqual(d1, d2)
        self.assertEqual(os.listdir(self.parent()), [os.path.basename(d1)])

    def test_same_content_shared_different_content_split(self):
        with DockerMock():
            a = dbg.extract_core(self.base, self.config, "dbg-a", self.parent())
        with DockerMock(files={**CORE, "./__init__.py": b"# other\n"}):
            b = dbg.extract_core(self.base, self.config, "dbg-a", self.parent())
        self.assertNotEqual(a, b)

    def test_uses_compose_run_by_service_and_never_starts_odoo(self):
        with DockerMock() as d:
            dbg.extract_core(self.base, self.config, "dbg-a", self.parent())
        argv = d.popen_calls[0]
        self.assertEqual(argv[:2], ["docker", "compose"])
        self.assertIn("odoo-dbg-a", argv)
        self.assertIn("--entrypoint", argv)
        self.assertIn("run", argv)
        flat = [a for c in d.popen_calls + d.run_calls for a in c]
        for forbidden in ("up", "start", "build", "cp", "exec", "rm"):
            self.assertNotIn(forbidden, flat)
        self.assertEqual(d.run_calls[0][:3], ["docker", "image", "inspect"])

    def test_missing_image_fails_before_running_anything(self):
        with DockerMock(image_ok=False) as d, self.assertRaises(dbg.DebugSetupError):
            dbg.extract_core(self.base, self.config, "dbg-a", self.parent())
        self.assertEqual(d.popen_calls, [])

    def test_failed_extraction_cleans_up(self):
        with DockerMock(rc=1), self.assertRaises(dbg.DebugSetupError):
            dbg.extract_core(self.base, self.config, "dbg-a", self.parent())
        self.assertEqual(os.listdir(self.parent()), [])

    def test_path_traversal_members_are_ignored(self):
        evil = {**CORE, "../../evil.py": b"x", "/abs.py": b"x"}
        with DockerMock(files=evil):
            d = dbg.extract_core(self.base, self.config, "dbg-a", self.parent())
        self.assertFalse(os.path.exists(os.path.join(self.base, "evil.py")))
        self.assertFalse(os.path.exists(os.path.join(d, "abs.py")))


class DebugSetupCommandTest(BaseCase):
    def test_writes_zed_scenarios(self):
        with DockerMock():
            rc = self.run_setup()
        self.assertEqual(rc, 0, self.errors())
        sc = {s["label"]: s for s in self.zed()}
        self.assertEqual(set(sc), {"Odoo dbg-a (attach)", "Odoo dbg-b (attach)"})
        a = sc["Odoo dbg-a (attach)"]
        self.assertEqual((a["adapter"], a["request"], a["justMyCode"]), ("Debugpy", "attach", False))
        self.assertEqual(a["connect"], {"host": "127.0.0.1", "port": 5670})
        self.assertEqual(sc["Odoo dbg-b (attach)"]["connect"]["port"], 5671)
        core_map, src_map = a["pathMappings"]  # core FIRST
        self.assertTrue(core_map["localRoot"].startswith("${ZED_WORKTREE_ROOT}/src/debug/core-19-"))
        self.assertEqual(core_map["remoteRoot"], "/usr/lib/python3/dist-packages/odoo")
        self.assertEqual(src_map, {"localRoot": "${ZED_WORKTREE_ROOT}/src", "remoteRoot": "/home/odoo/src"})

    def test_preserves_user_scenarios_and_replaces_managed_ones(self):
        os.makedirs(os.path.join(self.base, ".zed"))
        path = os.path.join(self.base, ".zed", "debug.json")
        with open(path, "w") as f:
            f.write('// mi config\n[{"label": "Mio", "adapter": "X"},\n'
                    ' {"label": "Odoo dbg-a (attach) viejo", "adapter": "Debugpy", "stale": true}]\n')
        with DockerMock():
            self.run_setup(instance="dbg-a")
        data = self.zed()
        self.assertEqual([s["label"] for s in data], ["Mio", "Odoo dbg-a (attach)"])
        self.assertNotIn("stale", data[1])
        self.assertTrue(os.path.exists(path + ".bak"))

    def test_second_run_is_idempotent(self):
        with DockerMock():
            self.run_setup()
            first = self.zed()
            self.run_setup()
        self.assertEqual(first, self.zed())
        self.assertEqual(len(os.listdir(os.path.join(self.base, "src", "debug"))), 2)  # core 19 + core 17

    def test_invalid_json_aborts_without_modifying(self):
        os.makedirs(os.path.join(self.base, ".zed"))
        path = os.path.join(self.base, ".zed", "debug.json")
        with open(path, "w") as f:
            f.write('[{"label": "x"},]')  # trailing comma
        with DockerMock():
            rc = self.run_setup()
        self.assertEqual(rc, 1)
        with open(path) as f:
            self.assertEqual(f.read(), '[{"label": "x"},]')

    def test_instance_without_debug_or_unknown_is_an_error(self):
        cfg = debug_config(True, False)
        with DockerMock() as d:
            self.assertEqual(self.run_setup(config=cfg, instance="dbg-b"), 1)
            self.assertEqual(self.run_setup(config=cfg, instance="nope"), 1)
        self.assertEqual(d.popen_calls, [])

    def test_no_debug_instances_is_an_error(self):
        self.assertEqual(self.run_setup(config=debug_config(False, False)), 1)

    def test_dest_outside_project_is_rejected_inside_is_accepted(self):
        with DockerMock() as d:
            self.assertEqual(self.run_setup(dest="/tmp/elsewhere-core"), 1)
            self.assertEqual(self.run_setup(dest="../fuera"), 1)
        self.assertEqual(d.popen_calls, [])
        with DockerMock():
            self.assertEqual(self.run_setup(dest="vendor/cores", instance="dbg-a"), 0, self.errors())
        self.assertTrue(os.path.isdir(os.path.join(self.base, "vendor", "cores")))
        self.assertIn("vendor/cores/core-19-", self.zed()[0]["pathMappings"][0]["localRoot"])

    def test_warns_when_compose_does_not_publish_the_port(self):
        with DockerMock():
            self.run_setup()
        self.assertTrue(any("./odoo build" in m for lvl, m in self.runner.messages if lvl == "warn"))

    def test_prune_removes_stale_scenarios_ports_and_orphan_cores(self):
        with DockerMock():
            self.run_setup()  # both debug
        os.makedirs(os.path.join(self.base, ".zed"), exist_ok=True)
        data = self.zed() + [{"label": "Odoo ghost (attach)", "adapter": "Debugpy"}]
        with open(os.path.join(self.base, ".zed", "debug.json"), "w") as f:
            json.dump(data, f)
        orphan = os.path.join(self.base, "src", "debug", "core-19-deadbeef")
        os.makedirs(orphan)
        cfg = debug_config(True, False)  # dbg-b no longer debug
        with DockerMock(files={**CORE, "./__init__.py": b"# new\n"}):
            self.assertEqual(self.run_setup(config=cfg, instance="dbg-a", prune=True), 0, self.errors())
        labels = [s["label"] for s in self.zed()]
        self.assertEqual(labels, ["Odoo dbg-a (attach)"])  # ghost and dbg-b gone
        self.assertFalse(os.path.exists(orphan))
        from generators.debug_ports import load_debug_ports
        self.assertEqual(list(load_debug_ports(self.base)), ["dbg-a"])
        # exactly the core still referenced by the scenario survives
        left = os.listdir(os.path.join(self.base, "src", "debug"))
        self.assertEqual(len(left), 1)
        self.assertIn(left[0], self.zed()[0]["pathMappings"][0]["localRoot"])


class ValidatePortsIncludeDebugTest(unittest.TestCase):
    def test_collect_config_ports_adds_resolved_debug_ports(self):
        from odoo_cli.core.actions.validate import _collect_config_ports
        cfg = debug_config(True, True)
        ports = _collect_config_ports(cfg, {"dbg-a": 5670, "dbg-b": 5671})
        self.assertTrue({28069, 28070, 26000, 5670, 5671} <= ports)
        self.assertNotIn(5670, _collect_config_ports(cfg))


class GitignoreTest(unittest.TestCase):
    def test_repo_gitignore_ignores_generated_debug_dirs(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        with open(os.path.join(root, ".gitignore")) as f:
            lines = {l.strip() for l in f}
        self.assertIn("src/debug/", lines)
        self.assertIn(".debug/", lines)


if __name__ == "__main__":
    unittest.main()

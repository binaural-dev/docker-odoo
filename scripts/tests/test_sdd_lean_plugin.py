import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGIN = os.path.join(ROOT, "scripts", "opencode-plugins", "sdd-lean-ruleset.js")
RULESET = os.path.join(ROOT, "scripts", "lean-change.md")

HARNESS = """
const { SddLeanRuleset } = await import(%r)
const h = await SddLeanRuleset()
const out = {}
await h["chat.message"]({ sessionID: "s-builder", agent: "sdd-builder" })
await h["chat.message"]({ sessionID: "s-lead", agent: "sdd-lead" })
for (const sid of ["s-builder", "s-lead", "s-unknown"]) {
  const o = { system: ["base"], context: [] }
  await h["experimental.chat.system.transform"]({ sessionID: sid }, o)
  const c = { context: [] }
  await h["experimental.session.compacting"]({ sessionID: sid }, c)
  out[sid] = { system: o.system.length, compact: c.context.length }
}
console.log(JSON.stringify(out))
""" % ("file://" + PLUGIN)


def run_plugin(env_extra):
    env = dict(os.environ)
    env.pop("SDD_LEAN_MODE", None)
    env.pop("SDD_LEAN_AGENTS", None)
    env.update(env_extra)
    res = subprocess.run(["node", "--input-type=module", "-e", HARNESS], capture_output=True, text=True, env=env, timeout=30)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout.strip().splitlines()[-1])


@unittest.skipUnless(shutil.which("node"), "node not available")
class LeanPluginBehavior(unittest.TestCase):
    def test_off_by_default_injects_nothing(self):
        out = run_plugin({})
        for sid in out:
            self.assertEqual(out[sid], {"system": 1, "compact": 0})

    def test_on_injects_only_into_builder(self):
        out = run_plugin({"SDD_LEAN_MODE": "on"})
        self.assertEqual(out["s-builder"], {"system": 2, "compact": 1})
        self.assertEqual(out["s-lead"], {"system": 1, "compact": 0})
        self.assertEqual(out["s-unknown"], {"system": 1, "compact": 0})

    def test_agents_list_is_configurable(self):
        out = run_plugin({"SDD_LEAN_MODE": "on", "SDD_LEAN_AGENTS": "sdd-lead, sdd-builder"})
        self.assertEqual(out["s-lead"]["system"], 2)
        self.assertEqual(out["s-builder"]["system"], 2)

    def test_invalid_mode_value_is_off(self):
        out = run_plugin({"SDD_LEAN_MODE": "ultra"})
        self.assertEqual(out["s-builder"]["system"], 1)


class LeanPluginPolicy(unittest.TestCase):
    def test_source_has_no_network_or_process_or_state_file(self):
        src = open(PLUGIN, encoding="utf-8").read()
        code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("//"))
        for banned in (r"\bfetch\s*\(", r"node:https?", r"\bhttps?\.request", r"child_process", r"\bspawn", r"\bexec",
                       r"webhook", r"writeFile", r"appendFile", r"\.ponytail"):
            self.assertIsNone(re.search(banned, code), banned)

    def test_ruleset_is_static_and_small(self):
        body = open(RULESET, encoding="utf-8").read()
        self.assertLess(len(body.encode()), 2000)
        self.assertNotRegex(body, r"\$\{|\{\{|\bdatetime\b")
        self.assertIn("lean_notes:", body)

    def test_plugin_registered_in_guardrails(self):
        cfg = json.load(open(os.path.join(ROOT, "scripts", "sdd-guardrails.json")))
        self.assertIn("./opencode-plugins/sdd-lean-ruleset.js", cfg["plugin"])


if __name__ == "__main__":
    unittest.main()

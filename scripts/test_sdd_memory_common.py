"""Unit tests for the Engram memory helpers: redaction, accent-free keywords, frontmatter and seed selection.

Run: python3 -m unittest scripts/test_sdd_memory_common.py -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdd_memory_common import ascii_keywords, parse_frontmatter, redact  # noqa: E402
from sdd_memory_seed import build_items  # noqa: E402


class RedactTests(unittest.TestCase):
    def test_key_value_secret_is_redacted(self):
        text, counts = redact("api_key: abcdef123456 y password=hunter22")
        self.assertNotIn("abcdef123456", text)
        self.assertNotIn("hunter22", text)
        self.assertEqual(counts.get("secret"), 2)

    def test_prose_mentioning_token_is_kept(self):
        text, counts = redact("el token separado por coma puede ser otro")
        self.assertIn("token separado por coma", text)
        self.assertNotIn("secret", counts)

    def test_postgres_uri_password_is_redacted(self):
        text, _ = redact("postgres://odoo:s3cretPass@db-pg16:5432/x")
        self.assertNotIn("s3cretPass", text)
        self.assertIn("db-pg16:5432/x", text)

    def test_aws_key_and_bearer_are_redacted(self):
        text, _ = redact("key AKIAABCDEFGHIJKLMNOP y Authorization Bearer abcdefghijklmnop123")
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", text)
        self.assertNotIn("abcdefghijklmnop123", text)

    def test_private_block_is_removed(self):
        text, counts = redact("visible <private>cosa interna</private> fin")
        self.assertNotIn("cosa interna", text)
        self.assertEqual(counts.get("private-tag"), 1)

    def test_client_names_are_replaced_case_insensitively(self):
        text, counts = redact("Neoris pidió datos de clinicas19 y CADIPA1")
        for name in ("Neoris", "clinicas19", "CADIPA1"):
            self.assertNotIn(name, text)
        self.assertEqual(counts.get("client-name"), 3)

    def test_client_databases_and_tickets_are_generic(self):
        text, counts = redact("hu27_e2e, rol hu_dev, HU-27, tarea 84595, helpdesk #13019, qa-consultoria-integra-19")
        for leaked in ("hu27_e2e", "hu_dev", "HU-27", "84595", "13019", "qa-consultoria"):
            self.assertNotIn(leaked, text)
        self.assertEqual(counts.get("ticket-id"), 3)
        self.assertEqual(counts.get("client-db"), 2)

    def test_hu_dev_role_with_hyphens_and_wikilinks_are_generic(self):
        text, _ = redact("ver [[project-hu-dev-shared-role]] y rol hu_dev")
        self.assertNotIn("hu-dev", text)
        self.assertNotIn("hu_dev", text)
        self.assertNotIn("[[", text)

    def test_client_identifiers_inside_names_are_replaced(self):
        text, _ = redact("REASSIGN OWNED BY clinicasv19 TO hu27_neoris")
        self.assertNotIn("neoris", text.lower())
        self.assertNotIn("clinicasv19", text.lower())

    def test_clean_text_has_no_counts(self):
        text, counts = redact("usar ./odoo test con --no-rm-db")
        self.assertEqual(text, "usar ./odoo test con --no-rm-db")
        self.assertEqual(counts, {})


class KeywordTests(unittest.TestCase):
    def test_keywords_are_ascii_and_unique(self):
        words = ascii_keywords("Validación de añadido", "validacion añadido ñandú")
        self.assertEqual(words.split(), ["validacion", "anadido", "nandu"])

    def test_short_tokens_are_dropped(self):
        self.assertEqual(ascii_keywords("el de la"), "")


class FrontmatterTests(unittest.TestCase):
    def test_flat_fields_and_body(self):
        fields, body = parse_frontmatter('---\nname: x\ndescription: "algo útil"\n---\n\ncuerpo\n')
        self.assertEqual(fields["name"], "x")
        self.assertEqual(fields["description"], "algo útil")
        self.assertEqual(body.strip(), "cuerpo")

    def test_missing_frontmatter_returns_whole_text(self):
        fields, body = parse_frontmatter("solo cuerpo")
        self.assertEqual(fields, {})
        self.assertEqual(body, "solo cuerpo")


class SeedSelectionTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        root = self.dir.name
        files = {
            "MEMORY.md": "- index",
            "feedback_psql_habit.md": "---\nname: psql\ndescription: no usar psql\n---\nNo usar docker exec. token=abcdef123456",
            "reference_gotchas.md": "---\nname: gotchas\ndescription: rol NOLOGIN\n---\nVer clinicas19",
            "project_state.md": "---\nname: estado\ndescription: ticket abierto\n---\ncuerpo",
            "otra_cosa.md": "ignorar",
        }
        for name, body in files.items():
            with open(os.path.join(root, name), "w", encoding="utf-8") as handle:
                handle.write(body)

    def tearDown(self):
        self.dir.cleanup()

    def test_default_selects_all_three_kinds(self):
        keys = [item["topic_key"] for item in build_items(self.dir.name)]
        self.assertEqual(len(keys), 3)
        for prefix in ("entorno/gotchas", "feedback/psql-habit", "proyecto/state"):
            self.assertTrue(any(k.startswith(prefix) for k in keys), prefix)

    def test_no_project_skips_project_files(self):
        keys = [item["topic_key"] for item in build_items(self.dir.name, include_project=False)]
        self.assertFalse(any(k.startswith("proyecto/") for k in keys))

    def test_seeded_content_is_redacted_and_has_keywords(self):
        items = {i["topic_key"]: i for i in build_items(self.dir.name, include_project=False)}
        psql = next(v for k, v in items.items() if k.startswith("feedback/psql-habit"))
        self.assertNotIn("abcdef123456", psql["content"])
        self.assertTrue(psql["content"].rstrip().split("\n")[-1].startswith("keywords: "))
        gotchas = next(v for k, v in items.items() if k.startswith("entorno/gotchas"))
        self.assertEqual(gotchas["content"].count("<cliente>"), 1)


if __name__ == "__main__":
    unittest.main()

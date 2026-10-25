"""Shared helpers for the Engram memory layer of the SDD harness.

- ``redact``: filter applied before anything is persisted (secrets, private tags, client names).
- ``EngramMcp``: minimal stdio MCP client for ``engram mcp``. Calls are strictly sequential:
  each request waits for its response (pipelined calls can be answered out of order).

Local only: the client never sets Engram Cloud or git-sync variables and never reads ENGRAM_HTTP_TOKEN.
"""

import json
import os
import re
import shutil
import subprocess
import unicodedata

DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "binaural-engram")
CLOUD_VARS = ("ENGRAM_CLOUD_SERVER", "ENGRAM_CLOUD_TOKEN", "ENGRAM_AGENT_CLI")

# Client names are replaced, not dropped: the lesson stays useful, the client identity does not.
# Memories are shared across the team, so they must stay generic: client names, client databases and
# ticket ids are replaced by placeholders. No word boundaries on the client names on purpose: identifiers
# such as ``hu27_neoris`` or ``clinicasv19`` must match too.
CLIENT_PATTERNS = [
    r"neoris",
    r"ariannis",
    r"clinicas\w*",
    r"countryclub",
    r"cadipa\w*",
    r"maxcam\w*",
    r"qa-consultoria[\w-]*",
]
GENERIC_PATTERNS = [
    (r"\bhu\d+_\w+", "<bd-cliente>", "client-db"),
    (r"hu[-_ ]dev", "<rol-bd>", "client-db"),
    (r"\[\[([^\]]+)\]\]", r"[\1]", "wikilink"),
    (r"(?i)\b(?:HU|TA|TI|TR|CS|COMM|ticket|tarea)[- ]?#?\d+\w*", "<ticket>", "ticket-id"),
    (r"#\d{3,}\b", "<ticket>", "ticket-id"),
]

SECRET_PATTERNS = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "<REDACTED:private-key>", re.DOTALL),
    (r"AKIA[0-9A-Z]{16}", "<REDACTED:aws-key>", 0),
    (r"(?i)(postgres(?:ql)?://[^:\s/]+:)[^@\s]+@", r"\1<REDACTED>@", 0),
    (r"(?i)bearer\s+[A-Za-z0-9._-]{12,}", "Bearer <REDACTED>", 0),
    (
        r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|authorization)\b(\s*[:=]\s*)(['\"]?)[^\s'\",;]{4,}\3",
        r"\1\2\3<REDACTED>\3",
        0,
    ),
]

PRIVATE_TAG = r"<private>.*?</private>"


def redact(text):
    """Return (clean_text, counts) where counts maps each rule to its number of replacements."""
    counts = {}

    def apply(pattern, repl, flags, label):
        nonlocal text
        text, n = re.subn(pattern, repl, text, flags=flags)
        if n:
            counts[label] = counts.get(label, 0) + n

    apply(PRIVATE_TAG, "[REDACTED]", re.DOTALL, "private-tag")
    for pattern, repl, flags in SECRET_PATTERNS:
        apply(pattern, repl, flags, "secret")
    for pattern in CLIENT_PATTERNS:
        apply(pattern, "<cliente>", re.IGNORECASE, "client-name")
    for pattern, repl, label in GENERIC_PATTERNS:
        apply(pattern, repl, 0, label)
    return text, counts


def ascii_keywords(*parts, limit=30):
    """Lowercase ASCII tokens without accents, unique and in order. Search does not fold accents."""
    seen = []
    for part in parts:
        folded = unicodedata.normalize("NFKD", part)
        folded = "".join(ch for ch in folded if not unicodedata.combining(ch)).lower()
        for token in re.findall(r"[a-z0-9_]{4,}", folded):
            if token not in seen:
                seen.append(token)
    return " ".join(seen[:limit])


def parse_frontmatter(text):
    """Split a memory file into (fields, body). Only flat ``key: value`` lines are understood."""
    fields = {}
    if not text.startswith("---"):
        return fields, text
    end = text.find("\n---", 3)
    if end == -1:
        return fields, text
    for line in text[3:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"')
    return fields, text[end + 4 :].lstrip("\n")


def find_engram_binary():
    return os.environ.get("ENGRAM_BIN") or shutil.which("engram") or os.path.expanduser("~/.local/bin/engram")


def engram_env(data_dir=None):
    env = dict(os.environ)
    env["ENGRAM_DATA_DIR"] = data_dir or env.get("ENGRAM_DATA_DIR") or DEFAULT_DATA_DIR
    env["ENGRAM_NO_UPDATE_CHECK"] = "1"
    env["ENGRAM_CLOUD_AUTOSYNC"] = "0"
    for var in CLOUD_VARS:
        env.pop(var, None)
    return env


class EngramMcpError(RuntimeError):
    pass


class EngramMcp:
    """One ``engram mcp`` process; every call waits for its own response before returning."""

    def __init__(self, binary, cwd, data_dir=None):
        self._next_id = 0
        self._proc = subprocess.Popen(
            [binary, "mcp", "--tools=agent"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd,
            env=engram_env(data_dir),
        )
        self._request(
            "initialize",
            {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "sdd-memory", "version": "1"}},
        )
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, message):
        self._proc.stdin.write(json.dumps(message) + "\n")
        self._proc.stdin.flush()

    def _request(self, method, params):
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params})
        line = self._proc.stdout.readline()
        if not line:
            raise EngramMcpError(f"engram mcp closed stdout: {self._proc.stderr.read()[-300:]}")
        return json.loads(line)

    def call(self, tool, arguments):
        """Call one tool and return its text result. Raises EngramMcpError on protocol or tool errors."""
        response = self._request("tools/call", {"name": tool, "arguments": arguments})
        if "error" in response:
            raise EngramMcpError(json.dumps(response["error"], ensure_ascii=False)[:300])
        result = response["result"]
        text = result["content"][0]["text"]
        if result.get("isError"):
            raise EngramMcpError(text[:300])
        return text

    def close(self):
        try:
            self._proc.stdin.close()
            self._proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait()
        finally:
            for pipe in (self._proc.stdout, self._proc.stderr):
                pipe.close()

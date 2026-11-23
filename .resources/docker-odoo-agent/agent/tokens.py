"""
Token store for the docker-odoo agent.

Tokens look like ``doa_<id>_<secret>``. Only the SHA-256 of the secret is
kept on disk, so a leaked tokens file can't be used to call the agent: the
plain token is shown once, when it is created, and never again.
"""

import hashlib
import hmac
import json
import os
import secrets
import threading
from datetime import datetime, timezone

TOKEN_PREFIX = "doa"
SCOPES = ("read", "write")

_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


class TokenStore:
    def __init__(self, path):
        self.path = path

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r") as f:
            return json.load(f)

    def _save(self, data):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp_path = self.path + ".tmp"
        # 0600 from the start: never leave the file world-readable, even briefly
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, self.path)

    def create(self, name, scopes=SCOPES):
        """Create a token and return it in plain text (only time it's visible)."""
        unknown = set(scopes) - set(SCOPES)
        if unknown:
            raise ValueError(f"Scopes desconocidos: {', '.join(sorted(unknown))}")
        with _lock:
            data = self._load()
            if any(t["name"] == name and not t.get("revoked") for t in data.values()):
                raise ValueError(f"Ya existe un token activo con el nombre '{name}'")
            token_id = secrets.token_hex(4)
            while token_id in data:
                token_id = secrets.token_hex(4)
            secret = secrets.token_urlsafe(32)
            data[token_id] = {
                "name": name,
                "hash": _hash(secret),
                "scopes": list(scopes),
                "created_at": _now(),
                "last_used_at": None,
                "revoked": False,
            }
            self._save(data)
        return f"{TOKEN_PREFIX}_{token_id}_{secret}"

    def list(self):
        return [
            {"id": token_id, **{k: v for k, v in info.items() if k != "hash"}}
            for token_id, info in self._load().items()
        ]

    def revoke(self, name_or_id):
        with _lock:
            data = self._load()
            matches = [
                token_id for token_id, info in data.items()
                if (token_id == name_or_id or info["name"] == name_or_id)
                and not info.get("revoked")
            ]
            for token_id in matches:
                data[token_id]["revoked"] = True
                data[token_id]["revoked_at"] = _now()
            if matches:
                self._save(data)
        return matches

    def verify(self, token):
        """Return the token's record (id, name, scopes) or None if invalid."""
        parts = (token or "").split("_", 2)
        if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
            return None
        token_id, secret = parts[1], parts[2]
        with _lock:
            data = self._load()
            info = data.get(token_id)
            if not info or info.get("revoked"):
                return None
            if not hmac.compare_digest(info["hash"], _hash(secret)):
                return None
            info["last_used_at"] = _now()
            self._save(data)
        return {"id": token_id, "name": info["name"], "scopes": info["scopes"]}

"""Host-port allocation for per-instance remote debugging (debugpy).

Each instance with ``debug: true`` publishes debugpy (container port 5678)
on ``127.0.0.1:<port>``. Ports come from, in order of precedence:

1. an explicit ``debug_port`` in ``instances.json``;
2. the port already recorded for that instance in ``.debug/ports.json``
   (so enabling / disabling / reordering instances never moves a port that
   was already handed out -- the IDE scenarios keep pointing at it);
3. the lowest free port from ``DEBUG_PORT_START`` (5670, 5671, ...).

``ports.json`` only grows: a recorded port is never reassigned to another
instance (not even while its owner is not in debug mode) unless
``prune_debug_ports`` (``./odoo debug-setup --prune``) drops it.
"""

from __future__ import annotations

import json
import os
import tempfile

from .config_loader import (
    DEBUG_PORT_START,
    collect_host_ports,
    get_debug_instances,
)

PORTS_RELPATH = os.path.join(".debug", "ports.json")
_FILE_VERSION = 1


def ports_path(base_path: str) -> str:
    return os.path.join(base_path, PORTS_RELPATH)


def load_debug_ports(base_path: str) -> dict[str, int]:
    """Recorded {instance: port}; empty if missing or unreadable."""
    try:
        with open(ports_path(base_path), "r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): int(v) for k, v in data.get("ports", {}).items()}
    except (OSError, ValueError, AttributeError, TypeError):
        return {}


def _save(base_path: str, ports: dict[str, int]) -> None:
    path = ports_path(base_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"version": _FILE_VERSION, "ports": ports}, f, indent=2,
                      sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def resolve_debug_ports(base_path: str, config: dict, persist: bool = True) -> dict[str, int]:
    """Return {instance: host_port} for every ``debug: true`` instance."""
    debug_names = get_debug_instances(config)
    stored = load_debug_ports(base_path)

    explicit = {
        n: config["instances"][n]["debug_port"]
        for n in debug_names if config["instances"][n].get("debug_port")
    }
    occupied = collect_host_ports(config) | {80} | set(explicit.values())

    result: dict[str, int] = dict(explicit)
    # Ports reserved by other instances' history (and by the ones we keep).
    reserved = set(stored.values()) | set(result.values())

    for name in debug_names:
        if name in result:
            continue
        previous = stored.get(name)
        others = {p for n, p in stored.items() if n != name}
        if (
            previous is not None
            and previous not in occupied
            and previous not in others
            and previous not in result.values()
        ):
            result[name] = previous
            continue
        port = DEBUG_PORT_START
        while port in occupied or port in reserved or port in result.values():
            port += 1
        result[name] = port
        reserved.add(port)

    merged = {**stored, **result}
    if persist and merged != stored:
        _save(base_path, merged)
    return result


def prune_debug_ports(base_path: str, config: dict) -> list[str]:
    """Forget recorded ports of instances that are no longer in debug mode.

    Returns the pruned instance names."""
    stored = load_debug_ports(base_path)
    keep = set(get_debug_instances(config))
    dropped = sorted(n for n in stored if n not in keep)
    if dropped:
        _save(base_path, {n: p for n, p in stored.items() if n in keep})
    return dropped

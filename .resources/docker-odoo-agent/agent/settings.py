"""
Agent settings.

Values come from environment variables, falling back to ``var/agent.env``
(written by install.sh) and then to defaults. Everything the agent writes
at runtime (tokens, audit log, config) lives in ``var/``, which is ignored
by git.
"""

import os

AGENT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAR_DIR = os.path.join(AGENT_ROOT, "var")
ENV_FILE = os.path.join(VAR_DIR, "agent.env")


def load_env_file(path=ENV_FILE):
    """Load KEY=VALUE lines into os.environ, without overriding what's set."""
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()

TOKENS_FILE = os.environ.get("AGENT_TOKENS_FILE", os.path.join(VAR_DIR, "agent_tokens.json"))
AUDIT_LOG = os.environ.get("AGENT_AUDIT_LOG", os.path.join(VAR_DIR, "agent_audit.log"))
HOST = os.environ.get("AGENT_HOST", "0.0.0.0")
PORT = int(os.environ.get("AGENT_PORT", "9000"))


def is_docker_odoo(path):
    return bool(path) and os.path.isfile(os.path.join(path, "odoo")) \
        and os.path.isdir(os.path.join(path, ".resources", "generators"))


def docker_odoo_root():
    """Path of the docker-odoo checkout this agent manages.

    DOCKER_ODOO_ROOT (env or var/agent.env) wins. Otherwise it's detected
    when this repo sits inside docker-odoo (as a submodule, or bundled in
    .resources/docker-odoo-agent) or next to it as ../docker-odoo.
    """
    configured = os.environ.get("DOCKER_ODOO_ROOT")
    if configured:
        configured = os.path.abspath(os.path.expanduser(configured))
        if not is_docker_odoo(configured):
            raise RuntimeError(
                f"DOCKER_ODOO_ROOT={configured} no es un checkout de docker-odoo "
                "(falta ./odoo o .resources/generators)"
            )
        return configured
    for candidate in (
        os.path.dirname(AGENT_ROOT),
        os.path.dirname(os.path.dirname(AGENT_ROOT)),
        os.path.join(os.path.dirname(AGENT_ROOT), "docker-odoo"),
    ):
        if is_docker_odoo(candidate):
            return candidate
    raise RuntimeError(
        "No se encontró el checkout de docker-odoo. Ejecuta "
        "'./install.sh --docker-odoo <ruta>' o define DOCKER_ODOO_ROOT."
    )

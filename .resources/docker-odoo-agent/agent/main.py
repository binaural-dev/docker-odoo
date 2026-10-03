"""
docker-odoo agent: HTTP API that lets micro_saas manage instances without
mounting the repo or docker.sock into any Odoo container.

Every endpoint except /health needs ``Authorization: Bearer <token>``
(see ``python3 -m agent token create``). GET endpoints need the 'read'
scope; anything that changes something needs 'write'.
"""

import logging
import os
import threading
import time
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import ops, settings
from .tokens import TokenStore

MAX_FAILED_ATTEMPTS = int(os.environ.get("AGENT_MAX_FAILED_ATTEMPTS", "10"))
BLOCK_SECONDS = int(os.environ.get("AGENT_BLOCK_SECONDS", "900"))

audit = logging.getLogger("agent.audit")
audit.setLevel(logging.INFO)
if not audit.handlers:
    os.makedirs(os.path.dirname(settings.AUDIT_LOG), exist_ok=True)
    handler = logging.FileHandler(settings.AUDIT_LOG)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    audit.addHandler(handler)

store = TokenStore(settings.TOKENS_FILE)
bearer = HTTPBearer(auto_error=False)
app = FastAPI(title="docker-odoo agent", docs_url=None, redoc_url=None, openapi_url=None)

_failed = {}
_failed_lock = threading.Lock()


def _client_ip(request):
    return request.client.host if request.client else "?"


def _is_blocked(ip):
    with _failed_lock:
        count, since = _failed.get(ip, (0, 0))
        if count >= MAX_FAILED_ATTEMPTS and time.time() - since < BLOCK_SECONDS:
            return True
        if time.time() - since >= BLOCK_SECONDS:
            _failed.pop(ip, None)
        return False


def _register_failure(ip):
    with _failed_lock:
        count, since = _failed.get(ip, (0, time.time()))
        _failed[ip] = (count + 1, since)


def authenticate(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    ip = _client_ip(request)
    if _is_blocked(ip):
        audit.warning("DENIED ip=%s reason=blocked %s %s", ip, request.method, request.url.path)
        raise HTTPException(429, "Demasiados intentos fallidos, intenta más tarde")

    token = store.verify(credentials.credentials) if credentials else None
    if not token:
        _register_failure(ip)
        audit.warning("DENIED ip=%s reason=token %s %s", ip, request.method, request.url.path)
        raise HTTPException(401, "Token inválido o revocado", headers={"WWW-Authenticate": "Bearer"})

    scope = "read" if request.method == "GET" else "write"
    if scope not in token["scopes"]:
        audit.warning("DENIED ip=%s token=%s reason=scope %s %s", ip, token["name"], request.method, request.url.path)
        raise HTTPException(403, f"El token no tiene el permiso '{scope}'")

    with _failed_lock:
        _failed.pop(ip, None)
    audit.info("OK ip=%s token=%s %s %s", ip, token["name"], request.method, request.url.path)
    return token


@app.exception_handler(ops.AgentError)
def _agent_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


# ----------------------------------------------------------------------
# Payloads
# ----------------------------------------------------------------------


class InstancePayload(BaseModel):
    odoo_version: str
    external_port: int
    database: str
    odoo_config: str
    domain: Optional[str] = None
    workers: int = 2
    without_demo: bool = True
    addons: List[str] = []
    db_filter: Optional[str] = None
    # 0 = no cron. With cron (>= 1, Odoo's default) and a Postgres service
    # shared with other instances, docker-odoo requires db_filter and a
    # dedicated role (db_user/db_password) for the instance
    max_cron_threads: Optional[int] = None
    # None keeps the current role; "" drops it (back to the service user).
    # Without db_password the agent generates one when the role is new
    db_user: Optional[str] = None
    db_password: Optional[str] = None


class ProvisionPayload(BaseModel):
    # regenerate configs and recreate the instance container (if running)
    # so it connects with its role
    recreate: bool = True
    # run as a background job and answer {'job_id'} at once (GET /jobs/<id>)
    background: bool = False
    # seconds the background job waits before starting (0-60): time for the
    # caller to commit before Postgres restarts
    delay: int = 0


class RestrictConnectPayload(BaseModel):
    # None = every instance
    instance: Optional[str] = None


class BuildPayload(BaseModel):
    no_cache: bool = False


class ClonePayload(BaseModel):
    url: str
    branch: str
    dir: str
    token: Optional[str] = None


class PullPayload(BaseModel):
    branch: str
    dir: Optional[str] = None
    url: Optional[str] = None
    token: Optional[str] = None
    update_submodules: bool = False


class ServerPathPullPayload(BaseModel):
    # relative to the docker-odoo root, e.g. "/src/custom/bp-staging"
    path: str
    branch: str
    url: Optional[str] = None
    token: Optional[str] = None
    update_submodules: bool = False


class UpdateModulesPayload(BaseModel):
    modules: List[str]
    database: str
    i18n_overwrite: bool = False


def _dump(model):
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
# Handlers are plain 'def' on purpose: FastAPI runs them in a threadpool,
# so a long build doesn't block status checks from the cron.


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/whoami")
def whoami(token=Depends(authenticate)):
    return {"name": token["name"], "scopes": token["scopes"]}


@app.get("/instances")
def list_instances(token=Depends(authenticate)):
    return ops.list_instances()


@app.get("/instances/status")
def instances_status(token=Depends(authenticate)):
    return ops.instances_status()


@app.put("/instances/{slug}")
def upsert_instance(slug: str, payload: InstancePayload, token=Depends(authenticate)):
    return ops.upsert_instance(slug, _dump(payload))


@app.delete("/instances/{slug}")
def delete_instance(slug: str, token=Depends(authenticate)):
    return ops.delete_instance(slug)


class PurgePayload(BaseModel):
    database: str
    db_filter: str


@app.post("/instances/{slug}/purge")
def purge_instance(slug: str, payload: PurgePayload, token=Depends(authenticate)):
    return ops.purge_instance(slug, payload.database, payload.db_filter)


@app.post("/instances/{slug}/provision-role")
def provision_role(slug: str, payload: ProvisionPayload = ProvisionPayload(), token=Depends(authenticate)):
    # restarts the db-<service> container: every instance on it reconnects
    return ops.provision_role(slug, payload.recreate, payload.background, payload.delay)


@app.post("/restrict-connect")
def restrict_connect(payload: RestrictConnectPayload = RestrictConnectPayload(), token=Depends(authenticate)):
    return ops.restrict_connect(payload.instance)


@app.get("/jobs/{job_id}")
def get_job(job_id: str, token=Depends(authenticate)):
    return ops.get_job(job_id)


@app.post("/build")
def build(payload: BuildPayload = BuildPayload(), token=Depends(authenticate)):
    return ops.build(payload.no_cache)


@app.post("/instances/{slug}/start")
def start_instance(slug: str, token=Depends(authenticate)):
    return ops.start_instance(slug)


@app.post("/instances/{slug}/stop")
def stop_instance(slug: str, token=Depends(authenticate)):
    return ops.stop_instance(slug)


@app.post("/instances/{slug}/restart")
def restart_instance(slug: str, token=Depends(authenticate)):
    return ops.restart_instance(slug)


@app.post("/instances/{slug}/modules/update")
def update_modules(slug: str, payload: UpdateModulesPayload, token=Depends(authenticate)):
    return ops.update_modules(slug, payload.modules, payload.database, payload.i18n_overwrite)


@app.get("/instances/{slug}/repos")
def list_repos(slug: str, token=Depends(authenticate)):
    return ops.list_repos(slug)


@app.post("/instances/{slug}/repos")
def clone_repo(slug: str, payload: ClonePayload, token=Depends(authenticate)):
    return ops.clone_repo(slug, payload.url, payload.branch, payload.dir, payload.token)


@app.post("/instances/{slug}/repos/pull")
def pull_repo(slug: str, payload: PullPayload, token=Depends(authenticate)):
    # dir "." is the instance folder itself (src/custom/<slug>/ is the repo)
    return ops.pull_repo(
        slug, payload.dir or ".", payload.branch, payload.url, payload.token,
        payload.update_submodules,
    )


@app.post("/instances/{slug}/repos/{repo_dir}/pull")
def pull_repo_by_path(slug: str, repo_dir: str, payload: PullPayload, token=Depends(authenticate)):
    return ops.pull_repo(
        slug, repo_dir, payload.branch, payload.url, payload.token, payload.update_submodules,
    )


@app.post("/repos/pull")
def pull_repo_by_server_path(payload: ServerPathPullPayload, token=Depends(authenticate)):
    return ops.pull_repo_at_server_path(
        payload.path, payload.branch, payload.url, payload.token, payload.update_submodules,
    )


@app.get("/databases/{database_key}")
def list_databases(database_key: str, token=Depends(authenticate)):
    return ops.list_databases(database_key)

#!/usr/bin/env bash
#
# Instalador del agente de docker-odoo (.resources/docker-odoo-agent).
# Normalmente se ejecuta con './odoo agent install [opciones]'.
#
# Revisa el entorno y hace solo lo que falta: se puede ejecutar las veces
# que haga falta (también para actualizar el agente tras un git pull).
#
#   ./odoo agent install                        instala o actualiza lo necesario
#   ./odoo agent install --check                solo informa qué haría, sin cambiar nada
#   ./odoo agent install --port 9100            otro puerto (por defecto 9000)
#   ./odoo agent install --token-name bp-qa     crea un token con ese nombre si no existe
#   ./odoo agent install --open-firewall        abre el puerto en ufw (acceso remoto)
#   ./odoo agent install --no-service           no instala el servicio (systemd en Linux, launchd en macOS)
#   ./odoo agent install --migrate-from <ruta>  instalación anterior de la que copiar tokens y auditoría
#   ./odoo agent install --docker-odoo <ruta>   otro checkout de docker-odoo (por defecto, el que lo contiene)
#
set -euo pipefail

AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$AGENT_ROOT/.venv"
VAR_DIR="$AGENT_ROOT/var"
ENV_FILE="$VAR_DIR/agent.env"
TOKENS_FILE="$VAR_DIR/agent_tokens.json"
AUDIT_LOG="$VAR_DIR/agent_audit.log"
SERVICE_NAME="docker-odoo-agent"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
REQ_STAMP="$VENV/.requirements.sha256"

PORT=""
DOCKER_ODOO=""
TOKEN_NAME=""
CHECK_ONLY=0
OPEN_FIREWALL=0
NO_SERVICE=0
MIGRATE_FROM=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port) PORT="$2"; shift 2 ;;
        --docker-odoo) DOCKER_ODOO="$2"; shift 2 ;;
        --token-name) TOKEN_NAME="$2"; shift 2 ;;
        --check) CHECK_ONLY=1; shift ;;
        --open-firewall) OPEN_FIREWALL=1; shift ;;
        --no-service) NO_SERVICE=1; shift ;;
        --migrate-from) MIGRATE_FROM="$2"; shift 2 ;;
        -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Opción desconocida: $1 (usa --help)"; exit 1 ;;
    esac
done

# ----------------------------------------------------------------------
# Salida
# ----------------------------------------------------------------------

if [[ -t 1 ]]; then
    C_OK=$'\e[32m'; C_DO=$'\e[36m'; C_WARN=$'\e[33m'; C_ERR=$'\e[31m'; C_B=$'\e[1m'; C_0=$'\e[0m'
else
    C_OK=""; C_DO=""; C_WARN=""; C_ERR=""; C_B=""; C_0=""
fi
CHANGES=0
WARNINGS=()

step() { echo; echo "${C_B}== $*${C_0}"; }
ok()   { echo "  ${C_OK}✔${C_0} $*"; }
warn() { echo "  ${C_WARN}!${C_0} $*"; WARNINGS+=("$*"); }
die()  { echo "  ${C_ERR}✘ $*${C_0}"; exit 1; }

# Runs a change, or only announces it in --check mode
act() {
    local desc="$1"; shift
    CHANGES=$((CHANGES + 1))
    if [[ $CHECK_ONLY -eq 1 ]]; then
        echo "  ${C_DO}→ haría:${C_0} $desc"
        return 0
    fi
    echo "  ${C_DO}→${C_0} $desc"
    "$@"
}

SUDO=""
need_sudo() {
    if [[ $EUID -eq 0 ]]; then SUDO=""; return; fi
    command -v sudo >/dev/null || die "Hace falta sudo para: $1"
    # SUDO_ASKPASS allows running without a terminal (e.g. over ssh from a script)
    if [[ -n "${SUDO_ASKPASS:-}" ]]; then SUDO="sudo -A"; else SUDO="sudo"; fi
    if [[ $CHECK_ONLY -eq 0 ]] && ! sudo -n true 2>/dev/null; then
        echo "  Se necesita sudo para: $1"
        $SUDO -v || die "Sin permisos de sudo"
    fi
}

OS="$(uname -s)"
LAUNCHD_LABEL="com.binaural.$SERVICE_NAME"
PLIST_FILE="$HOME/Library/LaunchAgents/$LAUNCHD_LABEL.plist"
HAS_LAUNCHD=0
[[ "$OS" == "Darwin" ]] && command -v launchctl >/dev/null && HAS_LAUNCHD=1
HAS_SYSTEMD=0
if [[ "$OS" == "Linux" ]] && command -v systemctl >/dev/null && [[ -d /run/systemd/system ]]; then
    HAS_SYSTEMD=1
fi
[[ $CHECK_ONLY -eq 1 ]] && echo "${C_B}Modo --check: no se cambia nada.${C_0}"

# ----------------------------------------------------------------------
step "Checkout de docker-odoo"
# ----------------------------------------------------------------------
env_value() { [[ -f "$ENV_FILE" ]] && sed -n "s/^$1=//p" "$ENV_FILE" | tail -1 || true; }
is_docker_odoo() { [[ -n "$1" && -f "$1/odoo" && -d "$1/.resources/generators" ]]; }

# Priority: --docker-odoo, var/agent.env, $DOCKER_ODOO_ROOT, then this repo
# inside docker-odoo (submodule or .resources/docker-odoo-agent) or next
# to it (../docker-odoo)
if [[ -z "$DOCKER_ODOO" ]]; then
    for candidate in "$(env_value DOCKER_ODOO_ROOT)" "${DOCKER_ODOO_ROOT:-}" \
                     "$(dirname "$AGENT_ROOT")" "$(dirname "$(dirname "$AGENT_ROOT")")" \
                     "$(dirname "$AGENT_ROOT")/docker-odoo"; do
        if is_docker_odoo "$candidate"; then DOCKER_ODOO="$candidate"; break; fi
    done
fi
[[ -n "$DOCKER_ODOO" ]] || die "No encontré el checkout de docker-odoo. Indícalo con --docker-odoo <ruta>"
DOCKER_ODOO="$(cd "$DOCKER_ODOO" 2>/dev/null && pwd)" || die "No existe la ruta de docker-odoo indicada"
is_docker_odoo "$DOCKER_ODOO" \
    || die "$DOCKER_ODOO no parece un checkout de docker-odoo (falta ./odoo o .resources/generators)"
ok "docker-odoo: $DOCKER_ODOO"
if [[ -f "$DOCKER_ODOO/instances.json" ]]; then
    ok "instances.json encontrado"
else
    warn "No existe instances.json: el agente arranca, pero no podrá gestionar instancias hasta que lo crees"
fi
if [[ -f "$DOCKER_ODOO/instances.json" ]] && grep -q "docker.sock" "$DOCKER_ODOO/instances.json"; then
    warn "instances.json monta docker.sock en alguna instancia (extra_volumes). Con el agente ya no hace falta: quítalo y ejecuta './odoo build'"
fi
if [[ -f "$DOCKER_ODOO/agent/main.py" ]]; then
    warn "Queda una copia antigua del agente en $DOCKER_ODOO/agent: ya no se usa, puedes borrarla"
fi

# Previous installs from the separate docker-odoo-agent repo: the one the
# installed service points at, --migrate-from, and the usual clone places
service_root() {
    local file
    for file in "$SERVICE_FILE" "$PLIST_FILE"; do
        [[ -f "$file" ]] || continue
        sed -n -e 's|^WorkingDirectory=||p' \
            -e '/<key>WorkingDirectory<\/key>/{n;s|.*<string>\(.*\)</string>.*|\1|p;}' "$file" | head -1
        return 0
    done
}
OLD_ROOTS=()
for candidate in "$MIGRATE_FROM" "$(service_root)" "$DOCKER_ODOO/docker-odoo-agent" \
                 "$(dirname "$DOCKER_ODOO")/docker-odoo-agent"; do
    [[ -n "$candidate" && -f "$candidate/agent/main.py" ]] || continue
    candidate="$(cd "$candidate" && pwd)"
    [[ "$candidate" == "$AGENT_ROOT" ]] && continue
    [[ " ${OLD_ROOTS[*]+"${OLD_ROOTS[*]}"} " == *" $candidate "* ]] && continue
    OLD_ROOTS+=("$candidate")
done
[[ -n "$MIGRATE_FROM" && ! -f "$MIGRATE_FROM/agent/main.py" ]] \
    && die "--migrate-from $MIGRATE_FROM no es una instalación del agente (falta agent/main.py)"
for old in "${OLD_ROOTS[@]+"${OLD_ROOTS[@]}"}"; do
    warn "Instalación anterior del agente en $old: tras verificar './odoo agent status', bórrala"
done
PORT="${PORT:-$(env_value AGENT_PORT)}"
PORT="${PORT:-9000}"

# ----------------------------------------------------------------------
step "Python"
# ----------------------------------------------------------------------
PYTHON="$(command -v python3 || true)"
[[ -n "$PYTHON" ]] || die "No se encontró python3"
PY_VERSION="$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' \
    || die "Hace falta Python 3.8 o superior (hay $PY_VERSION)"
ok "python3 $PY_VERSION"

if "$PYTHON" -c 'import venv, ensurepip' 2>/dev/null; then
    ok "Módulo venv disponible"
elif command -v apt-get >/dev/null; then
    need_sudo "instalar python3-venv"
    act "instalar python3-venv (apt)" bash -c "$SUDO apt-get update -qq && $SUDO apt-get install -y -qq python3-venv"
elif command -v dnf >/dev/null; then
    need_sudo "instalar python3 (dnf)"
    act "instalar el soporte de venv (dnf)" $SUDO dnf install -y python3
else
    die "Falta el módulo venv de Python; instálalo con el gestor de paquetes del sistema"
fi

# ----------------------------------------------------------------------
step "Docker"
# ----------------------------------------------------------------------
command -v docker >/dev/null || die "No se encontró el comando docker"
docker compose version >/dev/null 2>&1 || die "No está disponible 'docker compose' (plugin v2)"
ok "$(docker compose version | head -1)"
if docker info >/dev/null 2>&1; then
    ok "El usuario $(id -un) puede usar Docker"
else
    die "El usuario $(id -un) no puede hablar con Docker. Agrégalo al grupo docker (sudo usermod -aG docker $(id -un)) y vuelve a iniciar sesión"
fi

# ----------------------------------------------------------------------
step "Entorno virtual y dependencias"
# ----------------------------------------------------------------------
if [[ -x "$VENV/bin/python" ]] && "$VENV/bin/python" -c 'import sys' 2>/dev/null; then
    ok "Entorno virtual en .venv"
else
    [[ -e "$VENV" ]] && act "borrar .venv dañado" rm -rf "$VENV"
    act "crear .venv" "$PYTHON" -m venv "$VENV"
fi

REQ_SHA="$("$PYTHON" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$AGENT_ROOT/requirements.txt")"
if [[ -f "$REQ_STAMP" && "$(cat "$REQ_STAMP")" == "$REQ_SHA" ]] \
    && "$VENV/bin/python" -c 'import fastapi, uvicorn' 2>/dev/null; then
    ok "Dependencias al día ($("$VENV/bin/python" -c 'import fastapi; print("fastapi " + fastapi.__version__)'))"
    DEPS_CHANGED=0
else
    act "instalar dependencias de requirements.txt" bash -c \
        "'$VENV/bin/pip' install -q --upgrade pip && '$VENV/bin/pip' install -q -r '$AGENT_ROOT/requirements.txt' && echo '$REQ_SHA' > '$REQ_STAMP'"
    DEPS_CHANGED=1
fi

# ----------------------------------------------------------------------
step "Configuración y datos (var/)"
# ----------------------------------------------------------------------
if [[ -d "$VAR_DIR" ]]; then
    ok "var/ existe"
else
    act "crear var/ (permisos 700)" bash -c "mkdir -p '$VAR_DIR' && chmod 700 '$VAR_DIR'"
fi

ENV_CONTENT="# Generado por install.sh. Si lo editas, vuelve a ejecutar ./odoo agent install
DOCKER_ODOO_ROOT=$DOCKER_ODOO
AGENT_PORT=$PORT"
CONFIG_CHANGED=0
if [[ -f "$ENV_FILE" && "$(cat "$ENV_FILE")" == "$ENV_CONTENT" ]]; then
    ok "var/agent.env al día (puerto $PORT)"
else
    act "$([[ -f "$ENV_FILE" ]] && echo actualizar || echo escribir) var/agent.env (docker-odoo y puerto $PORT)" \
        bash -c 'printf "%s\n" "$1" > "$2"' _ "$ENV_CONTENT" "$ENV_FILE"
    CONFIG_CHANGED=1
fi

# Bring tokens and audit log from a previous install so existing tokens
# keep working: a separate docker-odoo-agent clone (copied, it stays as is
# until it is deleted) or, older, docker-odoo/.resources/secrets (moved)
LEGACY_DIR="$DOCKER_ODOO/.resources/secrets"
LEGACY_TOKENS=""
for old in "${OLD_ROOTS[@]+"${OLD_ROOTS[@]}"}"; do
    [[ -f "$old/var/agent_tokens.json" ]] || continue
    LEGACY_TOKENS="$old/var/agent_tokens.json"
    for name in agent_tokens.json agent_audit.log; do
        if [[ -f "$old/var/$name" && ! -f "$VAR_DIR/$name" ]]; then
            act "copiar $name desde $old/var (instalación anterior)" cp -p "$old/var/$name" "$VAR_DIR/$name"
        fi
    done
    break
done
for name in agent_tokens.json agent_audit.log; do
    if [[ -f "$LEGACY_DIR/$name" && ! -f "$VAR_DIR/$name" ]]; then
        [[ "$name" == agent_tokens.json ]] && LEGACY_TOKENS="$LEGACY_DIR/$name"
        act "mover $name desde $LEGACY_DIR (ubicación anterior)" mv "$LEGACY_DIR/$name" "$VAR_DIR/$name"
    fi
done

if [[ -f "$TOKENS_FILE" ]]; then
    PERMS="$(stat -c '%a' "$TOKENS_FILE" 2>/dev/null || stat -f '%Lp' "$TOKENS_FILE")"
    if [[ "$PERMS" == "600" ]]; then
        ok "agent_tokens.json con permisos 600"
    else
        act "corregir permisos de agent_tokens.json ($PERMS → 600)" chmod 600 "$TOKENS_FILE"
    fi
fi

# ----------------------------------------------------------------------
step "Servicio"
# ----------------------------------------------------------------------
HEALTH_URL="http://127.0.0.1:$PORT/health"
LOG_HINT=""
port_in_use() {
    if command -v ss >/dev/null; then ss -ltn "sport = :$PORT" | grep -q LISTEN
    else lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; fi
}

# Restart the service when its definition, the dependencies or the agent code changed
CODE_SHA="$(cat "$AGENT_ROOT"/agent/*.py | "$PYTHON" -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())')"
CODE_STAMP="$VENV/.code.sha256"
CODE_CHANGED=1
[[ -f "$CODE_STAMP" && "$(cat "$CODE_STAMP")" == "$CODE_SHA" ]] && CODE_CHANGED=0
SERVICE_ACTIVE=0

if [[ $NO_SERVICE -eq 1 || ( $HAS_SYSTEMD -eq 0 && $HAS_LAUNCHD -eq 0 ) ]]; then
    if [[ $NO_SERVICE -eq 1 ]]; then
        ok "Se omite el servicio (--no-service)"
    else
        warn "Este sistema ($OS) no tiene systemd ni launchd: el agente no se instala como servicio"
    fi
    echo "     Para levantarlo a mano:"
    echo "       cd $AGENT_ROOT && .venv/bin/python -m agent serve"

elif [[ $HAS_SYSTEMD -eq 1 ]]; then
    LOG_HINT="journalctl -u $SERVICE_NAME -n 50"
    UNIT_CONTENT="$(sed -e "s|@USER@|$(id -un)|g" -e "s|@AGENT_ROOT@|$AGENT_ROOT|g" \
        "$AGENT_ROOT/service/docker-odoo-agent.service")"
    UNIT_CHANGED=0
    if [[ -f "$SERVICE_FILE" ]] && [[ "$(cat "$SERVICE_FILE")" == "$UNIT_CONTENT" ]]; then
        ok "Unidad $SERVICE_FILE al día"
    else
        if ! systemctl is-active -q "$SERVICE_NAME" 2>/dev/null && port_in_use; then
            die "El puerto $PORT ya lo usa otro proceso. Elige otro con --port"
        fi
        need_sudo "instalar el servicio systemd"
        act "$([[ -f "$SERVICE_FILE" ]] && echo actualizar || echo instalar) $SERVICE_FILE (usuario $(id -un))" \
            bash -c "printf '%s\n' \"\$1\" | $SUDO tee '$SERVICE_FILE' >/dev/null && $SUDO systemctl daemon-reload" _ "$UNIT_CONTENT"
        UNIT_CHANGED=1
    fi
    if systemctl is-enabled -q "$SERVICE_NAME" 2>/dev/null; then
        ok "Servicio habilitado al arranque"
    else
        need_sudo "habilitar el servicio"
        act "habilitar $SERVICE_NAME al arranque" $SUDO systemctl enable -q "$SERVICE_NAME"
    fi
    if ! systemctl is-active -q "$SERVICE_NAME" 2>/dev/null; then
        need_sudo "iniciar el servicio"
        act "iniciar $SERVICE_NAME" $SUDO systemctl start "$SERVICE_NAME"
    elif [[ $UNIT_CHANGED -eq 1 || $DEPS_CHANGED -eq 1 || $CODE_CHANGED -eq 1 || $CONFIG_CHANGED -eq 1 ]]; then
        need_sudo "reiniciar el servicio"
        act "reiniciar $SERVICE_NAME para aplicar cambios" $SUDO systemctl restart "$SERVICE_NAME"
    else
        ok "Servicio en ejecución"
    fi
    SERVICE_ACTIVE=1

else
    # macOS: per-user LaunchAgent (starts at login, no sudo)
    LOG_FILE="$HOME/Library/Logs/$SERVICE_NAME.log"
    LOG_HINT="tail -n 50 $LOG_FILE"
    DOMAIN="gui/$(id -u)"
    # docker (and its credential helper) and git must be on the service's PATH
    SERVICE_PATH=""
    for bin in docker git; do
        dir="$(dirname "$(command -v "$bin")")"
        [[ ":$SERVICE_PATH:" == *":$dir:"* ]] || SERVICE_PATH="${SERVICE_PATH:+$SERVICE_PATH:}$dir"
    done
    SERVICE_PATH="$SERVICE_PATH:/usr/bin:/bin:/usr/sbin:/sbin"
    PLIST_CONTENT="$(sed -e "s|@AGENT_ROOT@|$AGENT_ROOT|g" \
        -e "s|@PATH@|$SERVICE_PATH|g" -e "s|@LOG@|$LOG_FILE|g" "$AGENT_ROOT/service/$LAUNCHD_LABEL.plist")"
    is_loaded() { launchctl print "$DOMAIN/$LAUNCHD_LABEL" >/dev/null 2>&1; }
    is_running() { launchctl print "$DOMAIN/$LAUNCHD_LABEL" 2>/dev/null | grep -q "state = running"; }

    PLIST_CHANGED=0
    if [[ -f "$PLIST_FILE" ]] && [[ "$(cat "$PLIST_FILE")" == "$PLIST_CONTENT" ]]; then
        ok "LaunchAgent $PLIST_FILE al día"
    else
        if ! is_running && port_in_use; then
            die "El puerto $PORT ya lo usa otro proceso. Elige otro con --port"
        fi
        act "$([[ -f "$PLIST_FILE" ]] && echo actualizar || echo instalar) $PLIST_FILE" \
            bash -c 'mkdir -p "$(dirname "$2")" && printf "%s\n" "$1" > "$2" && plutil -lint -s "$2"' _ "$PLIST_CONTENT" "$PLIST_FILE"
        PLIST_CHANGED=1
    fi
    if [[ $PLIST_CHANGED -eq 1 ]] && is_loaded; then
        # launchd only rereads the plist on bootstrap
        act "recargar el LaunchAgent" bash -c "launchctl bootout '$DOMAIN/$LAUNCHD_LABEL' 2>/dev/null; sleep 1; launchctl bootstrap '$DOMAIN' '$PLIST_FILE'"
    elif ! is_loaded; then
        act "cargar el LaunchAgent (arranca también en cada inicio de sesión)" launchctl bootstrap "$DOMAIN" "$PLIST_FILE"
    elif ! is_running; then
        act "iniciar $LAUNCHD_LABEL" launchctl kickstart "$DOMAIN/$LAUNCHD_LABEL"
    elif [[ $DEPS_CHANGED -eq 1 || $CODE_CHANGED -eq 1 || $CONFIG_CHANGED -eq 1 ]]; then
        act "reiniciar $LAUNCHD_LABEL para aplicar cambios" launchctl kickstart -k "$DOMAIN/$LAUNCHD_LABEL"
    else
        ok "Servicio en ejecución"
    fi
    SERVICE_ACTIVE=1
fi
[[ $CHECK_ONLY -eq 0 && -d "$VENV" ]] && echo "$CODE_SHA" > "$CODE_STAMP"

if [[ $CHECK_ONLY -eq 0 && $SERVICE_ACTIVE -eq 1 ]]; then
    for _ in $(seq 1 15); do
        curl -sf "$HEALTH_URL" >/dev/null 2>&1 && break
        sleep 1
    done
    if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
        ok "Responde en $HEALTH_URL"
    else
        die "El servicio no responde en $HEALTH_URL. Revisa: $LOG_HINT"
    fi
fi

# ----------------------------------------------------------------------
step "Firewall"
# ----------------------------------------------------------------------
if command -v ufw >/dev/null; then
    if [[ $OPEN_FIREWALL -eq 1 ]]; then
        need_sudo "revisar y abrir el puerto en ufw"
        UFW_OUT="$($SUDO ufw status 2>/dev/null || true)"
    else
        UFW_OUT="$( (sudo -n ufw status || ufw status) 2>/dev/null || true)"
    fi
    UFW_STATUS="$(echo "$UFW_OUT" | head -1)"
    if [[ -z "$UFW_STATUS" ]]; then
        warn "No se pudo leer el estado de ufw sin sudo; si está activo, abre el puerto con --open-firewall"
    elif [[ "$UFW_STATUS" == *"inactive"* ]]; then
        ok "ufw inactivo: el puerto $PORT es accesible desde la red"
    elif echo "$UFW_OUT" | grep -qE "^$PORT(/tcp)? +ALLOW"; then
        ok "ufw permite el puerto $PORT"
    elif [[ $OPEN_FIREWALL -eq 1 ]]; then
        act "permitir $PORT/tcp en ufw" $SUDO ufw allow "$PORT/tcp"
    else
        warn "ufw activo y el puerto $PORT cerrado: solo se accede desde este host y sus contenedores. Para acceso remoto usa --open-firewall"
    fi
else
    ok "Sin ufw"
fi

# ----------------------------------------------------------------------
step "Tokens"
# ----------------------------------------------------------------------
active_tokens() {
    # In --check mode the legacy tokens haven't been brought to var/ yet
    local file="$TOKENS_FILE"
    [[ -f "$file" ]] || file="$LEGACY_TOKENS"
    [[ -f "$file" ]] || { echo ""; return; }
    "$PYTHON" -c '
import json, sys
data = json.load(open(sys.argv[1]))
print(" ".join(t["name"] for t in data.values() if not t.get("revoked")))
' "$file"
}
ACTIVE="$(active_tokens)"
NEW_TOKEN=""
if [[ -n "$TOKEN_NAME" && " $ACTIVE " == *" $TOKEN_NAME "* ]]; then
    ok "Ya existe un token activo '$TOKEN_NAME' (no se vuelve a mostrar; revócalo y crea otro si lo perdiste)"
elif [[ -n "$TOKEN_NAME" || -z "$ACTIVE" ]]; then
    NAME="${TOKEN_NAME:-micro-saas}"
    if [[ $CHECK_ONLY -eq 1 ]]; then
        act "crear el token '$NAME'" true
    else
        CHANGES=$((CHANGES + 1))
        echo "  ${C_DO}→${C_0} crear el token '$NAME'"
        NEW_TOKEN="$(cd "$AGENT_ROOT" && "$VENV/bin/python" -m agent token create "$NAME" | grep -o 'doa_[A-Za-z0-9_-]*')"
    fi
else
    ok "Tokens activos: $ACTIVE"
fi

# ----------------------------------------------------------------------
step "Resumen"
# ----------------------------------------------------------------------
HOST_IP="$( (hostname -I 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || true) | awk '{print $1}')"
if [[ $CHECK_ONLY -eq 1 ]]; then
    [[ $CHANGES -eq 0 ]] && ok "Todo está instalado, no haría ningún cambio" \
        || echo "  $CHANGES cambio(s) pendiente(s). Ejecuta sin --check para aplicarlos."
else
    [[ $CHANGES -eq 0 ]] && ok "Todo estaba instalado, no se cambió nada" || ok "$CHANGES cambio(s) aplicado(s)"
fi
for w in "${WARNINGS[@]+"${WARNINGS[@]}"}"; do echo "  ${C_WARN}!${C_0} $w"; done

cat <<EOF

  Configura micro_saas en Odoo (Gestión de instancias > Ajustes):
    Agent URL, desde un contenedor de este host:  http://host.docker.internal:$PORT
    Agent URL, desde otro equipo:                 http://${HOST_IP:-<ip-de-este-host>}:$PORT
EOF
if [[ -n "$NEW_TOKEN" ]]; then
    cat <<EOF
    Agent Token:  ${C_B}$NEW_TOKEN${C_0}

  ${C_WARN}Copia el token ahora: no se vuelve a mostrar.${C_0}
EOF
else
    echo "    Agent Token:  genera uno con './odoo agent install --token-name <nombre>'"
fi
echo

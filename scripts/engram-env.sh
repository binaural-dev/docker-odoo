#!/usr/bin/env bash
# Configuración única de Engram para el harness SDD: local, sin nube, sin consultas de versión.
# Uso: source scripts/engram-env.sh (Claude, OpenCode y los scripts de captura la leen igual).
export ENGRAM_DATA_DIR="$HOME/.local/share/binaural-engram"
export ENGRAM_NO_UPDATE_CHECK=1
export ENGRAM_CLOUD_AUTOSYNC=0
unset ENGRAM_CLOUD_SERVER ENGRAM_CLOUD_TOKEN ENGRAM_AGENT_CLI

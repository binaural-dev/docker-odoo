#!/usr/bin/env bash
# update_addon_pools.sh — actualiza los pools de addons compartidos
# (integra-addons-*, odoo-venezuela-*, third-party-addons-*) y los repos core
# de Odoo/Enterprise (odoo-*, enterprise-*) en su rama actual, trayendo todos
# los cambios de origin.
#
# A diferencia de `./odoo sync` (que opera sobre src/custom/<repo> dentro de
# docker-multi y hace checkout a una rama fija), este script:
#   - opera sobre las copias reales de estos repos, que desde 2026-09-28 viven
#     en docker-multi/src (se movieron desde /home/binlp011/sources, que ya no
#     tiene copia propia de ninguno de estos pools — todo vive en un solo
#     lugar para que los contenedores Docker, que solo bind-mountean
#     docker-multi/src, siempre vean la copia real)
#   - descubre automáticamente los directorios pool que matchean
#     <integra-addons|odoo-venezuela|third-party-addons|odoo|enterprise>[...]-<version>,
#     cubriendo variantes como *-l10nve_17.0 o *-maintenance-19.0, pero sin
#     tocar copias con sufijo extra tipo worktrees de tareas puntuales
#     (integra-addons-19.0-ti15326, integra-addons-l10nve_17.0-wt-pr2039),
#     para no arrastrar cambios de ramas de trabajo aisladas
#   - NO cambia de rama: hace pull sobre la rama en la que ya está cada repo
#   - si hay cambios locales sin commitear, los guarda con `git stash` antes
#     de actualizar y los restaura al final (o avisa si el pop falla) — esto
#     no debería disparar nunca para odoo-*/enterprise-* (nunca se editan a
#     mano, ver guardrail de "core-modification" en AGENTS.md/CLAUDE.md), pero
#     el script no asume eso y protege igual por si acaso
#
# Uso:
#   scripts/update_addon_pools.sh              # actualiza los pools por defecto
#   scripts/update_addon_pools.sh <dir> [...]   # actualiza solo esos directorios (bajo SOURCES_PATH)

set -uo pipefail

SOURCES_PATH="/home/binlp011/sources/docker-multi/src"

# Patrón: <pool><...>-<version>, version tipo 16.0/17.0/18.0/19.0/20.0.
# Requerir que la cadena TERMINE en "-<digitos>.<digitos>" excluye
# automáticamente los worktrees de tareas puntuales (terminan en un
# ticket/PR, no en versión), sin necesidad de enumerar cada variante
# intermedia (l10nve_, maintenance-, maintenance-l10nve_, etc.). "odoo" cubre
# tanto odoo-17.0 (core Community) como odoo-venezuela-17.0 (el prefijo
# "odoo-venezuela" queda listado aparte solo por claridad documental, ya que
# "odoo" ya lo cubre).
POOL_REGEX='^(integra-addons|odoo-venezuela|third-party-addons|odoo|enterprise)[A-Za-z0-9_-]*[0-9]+\.[0-9]+$'

discover_pools() {
    local dir base
    for dir in "$SOURCES_PATH"/*/; do
        base="$(basename "$dir")"
        if [[ "$base" =~ $POOL_REGEX ]] && [ -d "$dir/.git" ]; then
            echo "$base"
        fi
    done
}

if [ "$#" -gt 0 ]; then
    REPOS=("$@")
else
    mapfile -t REPOS < <(discover_pools)
fi

if [ "${#REPOS[@]}" -eq 0 ]; then
    echo "No se encontraron pools de addons para actualizar en $SOURCES_PATH"
    exit 1
fi

echo -e "\n\033[1;36m=== 🔄 ACTUALIZANDO POOLS DE ADDONS (rama actual de cada repo) ===\033[0m\n"

declare -a SUMMARY

for repo in "${REPOS[@]}"; do
    repo_path="$SOURCES_PATH/$repo"

    if [ ! -d "$repo_path/.git" ]; then
        echo "❌ $repo: no es un repositorio git (ruta: $repo_path), se omite."
        SUMMARY+=("$repo|-|ERROR: no es repo git")
        continue
    fi

    echo -e "\n=== $repo ==="
    if ! cd "$repo_path"; then
        SUMMARY+=("$repo|-|ERROR: no se pudo entrar al directorio")
        continue
    fi

    branch="$(git rev-parse --abbrev-ref HEAD)"
    echo "→ Rama actual: $branch"

    stashed=false
    if [ -n "$(git status --porcelain)" ]; then
        stash_msg="update_addon_pools.sh $(date -Iseconds)"
        echo "→ Cambios locales detectados, guardando (stash -u)..."
        if git stash push -u -m "$stash_msg" >/dev/null; then
            stashed=true
        else
            echo "❌ $repo: falló 'git stash', se omite para no perder cambios locales."
            SUMMARY+=("$repo|$branch|ERROR: git stash falló")
            cd "$SOURCES_PATH" || exit 1
            continue
        fi
    fi

    echo "→ git fetch origin..."
    if ! git fetch origin; then
        echo "❌ $repo: falló git fetch."
        SUMMARY+=("$repo|$branch|ERROR: git fetch falló")
        if [ "$stashed" = true ]; then
            git stash pop || echo "⚠️  $repo: no se pudo restaurar el stash automáticamente, revisar manualmente."
        fi
        cd "$SOURCES_PATH" || exit 1
        continue
    fi

    echo "→ git pull --ff-only origin $branch..."
    if git pull --ff-only origin "$branch"; then
        result="OK"
    else
        echo "❌ $repo: pull --ff-only falló (posible divergencia con origin/$branch), revisar manualmente."
        result="ERROR: pull --ff-only falló"
    fi

    if [ "$stashed" = true ]; then
        echo "→ Restaurando cambios locales (stash pop)..."
        if ! git stash pop; then
            echo "⚠️  $repo: conflicto al restaurar el stash, resolver manualmente (git stash list)."
            result="$result + ⚠️ stash pop con conflictos"
        fi
    fi

    SUMMARY+=("$repo|$branch|$result")
    cd "$SOURCES_PATH" || exit 1
done

echo -e "\n\033[1;36m=== Resumen ===\033[0m"
printf "%-35s %-20s %s\n" "Repo" "Rama" "Resultado"
for line in "${SUMMARY[@]}"; do
    IFS='|' read -r repo branch result <<< "$line"
    printf "%-35s %-20s %s\n" "$repo" "$branch" "$result"
done

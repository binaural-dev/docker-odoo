#!/bin/bash
# detect_move_ids_without_package.sh
# Auditoría: detecta uso de `move_ids_without_package` (Odoo 17) en código Odoo 19.
# En Odoo 19, este campo NO existe — debe ser `move_ids`.
#
# Uso:
#   ./scripts/detect_move_ids_without_package.sh [directorio]
#
# Default: busca en directorios 19.0

set -euo pipefail

BASE_DIR="${1:-/home/binlp011/sources/docker-multi/src}"
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "=========================================="
echo " Auditoría: move_ids_without_package"
echo " Odoo 19 — Campo obsoleto (debe ser move_ids)"
echo "=========================================="
echo ""
echo "Buscando en directorios 19.0..."
echo ""

COUNT=0

# Search only in 19.0 directories (not odoo-17.0 where field is valid)
DIRS=(
    "$BASE_DIR/odoo-venezuela-19.0"
    "$BASE_DIR/integra-addons-19.0"
    "$BASE_DIR/third-party-addons-19.0"
    "$BASE_DIR/custom"
)

for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        continue
    fi
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            echo -e "${RED}HIGH${NC} $line"
            COUNT=$((COUNT + 1))
        fi
    done < <(rg "move_ids_without_package" "$dir" -n 2>/dev/null || true)
done

echo ""
echo "=========================================="
echo " Total hallazgos: $COUNT"
if [ "$COUNT" -gt 0 ]; then
    echo -e "${RED}Estado: FAIL — Archivos con campo obsoleto detectados${NC}"
    echo "Acción requerida: Reemplazar 'move_ids_without_package' por 'move_ids'"
    echo "Referencia: LESSON #10, FIX-032 en skills del proyecto"
else
    echo -e "${GREEN}Estado: PASS — No se encontraron instancias del campo obsoleto${NC}"
fi
echo "=========================================="

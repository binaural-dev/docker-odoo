#!/bin/bash
# =============================================================================
# Script para ejecutar pruebas de estrés en Odoo con Locust
# =============================================================================

set -e

# Agregar ~/.local/bin al PATH si existe
if [ -d "$HOME/.local/bin" ]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    cat << EOF
Uso: $0 [OPCIÓN] [ARCHIVO_TEST] [PARÁMETROS]

Script para ejecutar pruebas de estrés en instancias Odoo usando Locust.

OPCIONES:
    -i, --interactive       Modo interactivo (abre UI web) - DEFAULT
    -h, --headless          Modo headless (sin UI, para CI/CD)
    -w, --workers N         Ejecutar con N workers distribuidos
    -l, --list              Listar instancias configuradas
    -r, --requirements      Instalar dependencias
    -h, --help              Mostrar esta ayuda

ARCHIVOS DE TEST DISPONIBLES:
    test_generic_read.py    - Lectura básica (partners, productos, órdenes)
    test_crm_leads.py       - CRM/Leads
    test_sales_orders.py    - Ventas/Órdenes de venta

PARÁMETROS PARA MODO HEADLESS:
    --users N               Número total de usuarios simulados
    --spawn-rate N          Tasa de creación de usuarios/segundo
    --run-time T            Tiempo de ejecución (ej: 5m, 1h)

EJEMPLOS:
    # Modo interactivo con test genérico
    $0 test_generic_read.py

    # Modo headless: 100 usuarios, 10/seg, durante 5 minutos
    $0 -h test_generic_read.py --users 100 --spawn-rate 10 --run-time 5m

    # Con 4 workers distribuidos
    $0 -w 4 test_generic_read.py

    # Instalar dependencias
    $0 -r

EOF
}

# Función para instalar dependencias
install_requirements() {
    echo -e "${BLUE}Instalando dependencias...${NC}"
    echo -e "${YELLOW}Usando: pip3 install --break-system-packages -r requirements.txt${NC}"
    if command -v pip3 &> /dev/null; then
        pip3 install --break-system-packages -r requirements.txt
    elif command -v pip &> /dev/null; then
        pip install --break-system-packages -r requirements.txt
    else
        echo -e "${RED}Error: pip no encontrado${NC}"
        exit 1
    fi
    echo -e "${GREEN}Dependencias instaladas correctamente${NC}"
    echo -e "${GREEN}Locust disponible en: $(which locust)${NC}"
}

# Función para listar instancias
list_instances() {
    echo -e "${BLUE}Instancias configuradas:${NC}"
    echo ""
    cd "$(dirname "$0")"
    python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '.')
from instances_config import list_instances, INSTANCES
instances = list_instances()
header = f"{'Nombre':20} {'Puerto':8} {'Versión':8} Descripción"
print(header)
print('-' * 70)
for name, desc in instances.items():
    config = INSTANCES[name]
    line = f"{name:20} {config['port']:<8} {config['odoo_version']:8} {desc}"
    print(line)
PYTHON_SCRIPT
}

# Función para ejecutar test
run_test() {
    local test_file="$1"
    local mode="$2"
    local workers="$3"
    shift 3
    local extra_params="$@"

    if [ ! -f "$test_file" ]; then
        echo -e "${RED}Error: Archivo de test '$test_file' no encontrado${NC}"
        echo -e "Archivos disponibles:"
        ls -1 test_*.py 2>/dev/null | sed 's/^/  - /' || echo "  (ninguno)"
        exit 1
    fi

    echo -e "${GREEN}Ejecutando test: $test_file${NC}"

    if [ "$workers" -gt 0 ]; then
        echo -e "${YELLOW}Iniciando modo distribuido con $workers workers...${NC}"

        # Iniciar workers en background
        for i in $(seq 1 $workers); do
            locust -f "$test_file" --worker --only-summary > /dev/null 2>&1 &
            echo "Worker $i iniciado (PID: $!)"
        done

        # Iniciar master
        if [ "$mode" = "headless" ]; then
            locust -f "$test_file" --master --expect-workers=$workers $extra_params
        else
            locust -f "$test_file" --master --expect-workers=$workers
        fi

        # Matar workers al terminar
        echo -e "${YELLOW}Deteniendo workers...${NC}"
        pkill -f "locust -f $test_file --worker" || true

    else
        if [ "$mode" = "headless" ]; then
            echo -e "${YELLOW}Modo headless activado${NC}"
            locust -f "$test_file" $extra_params
        else
            echo -e "${GREEN}Abriendo interfaz web en http://localhost:8089${NC}"
            locust -f "$test_file"
        fi
    fi
}

# =============================================================================
# Main
# =============================================================================

MODE="interactive"
WORKERS=0
TEST_FILE=""
EXTRA_PARAMS=""

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--interactive)
            MODE="interactive"
            shift
            ;;
        -h|--headless)
            MODE="headless"
            shift
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -l|--list)
            list_instances
            exit 0
            ;;
        -r|--requirements)
            install_requirements
            exit 0
            ;;
        --help)
            show_help
            exit 0
            ;;
        --users|--spawn-rate|--run-time)
            EXTRA_PARAMS="$EXTRA_PARAMS $1 $2"
            shift 2
            ;;
        -*)
            echo -e "${RED}Opción desconocida: $1${NC}"
            show_help
            exit 1
            ;;
        *)
            if [ -z "$TEST_FILE" ]; then
                TEST_FILE="$1"
            else
                EXTRA_PARAMS="$EXTRA_PARAMS $1"
            fi
            shift
            ;;
    esac
done

# Si no se especificó archivo de test, mostrar ayuda
if [ -z "$TEST_FILE" ]; then
    show_help
    echo ""
    echo -e "${YELLOW}Archivos de test disponibles:${NC}"
    ls -1 test_*.py 2>/dev/null | sed 's/^/  - /' || echo "  (ninguno)"
    exit 1
fi

# Ejecutar test
run_test "$TEST_FILE" "$MODE" "$WORKERS" $EXTRA_PARAMS

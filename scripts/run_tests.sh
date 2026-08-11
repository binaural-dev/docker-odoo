#!/bin/bash

# Default values
MODULES="binaural_website_sale,binaural_website_sale_delivery,binaural_website_sale_transit"
CONTAINER="odoo-qa-consultoria-19"
DB_NAME="tests_binaural_ws_$(date +%s)"
TAGS=""
NO_COV=false

# Parse arguments
for arg in "$@"; do
  case $arg in
    --modules=*)    MODULES="${arg#*=}" ;;
    --container=*)  CONTAINER="${arg#*=}" ;;
    --db_name=*)    DB_NAME="${arg#*=}" ;;
    --tags=*)       TAGS="${arg#*=}" ;;
    --no-cov)       NO_COV=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

# Tags default to modules if not set
if [[ -z "$TAGS" ]]; then
  TAGS="$MODULES"
fi

# Verify container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "ERROR: Container '${CONTAINER}' is not running."
  echo "Available containers:"
  docker ps --format '{{.Names}} {{.Status}}' | grep odoo
  exit 1
fi

# Derive module names from paths for -i flag
IFS=',' read -ra MOD_ARRAY <<< "$MODULES"
MODULE_NAMES=""
SOURCE_PATHS=""
for mod in "${MOD_ARRAY[@]}"; do
  mod_name=$(basename "$mod")
  MODULE_NAMES+="$mod_name,"
  SOURCE_PATHS+="/home/odoo/src/$mod,"
done
MODULE_NAMES=${MODULE_NAMES::-1}
SOURCE_PATHS=${SOURCE_PATHS::-1}

echo "============================================"
echo "  Tests: binaural_website_sale"
echo "============================================"
echo "Container:  $CONTAINER"
echo "DB:         $DB_NAME"
echo "Modules:    $MODULE_NAMES"
echo "Tags:       $TAGS"
echo "Coverage:   $([ "$NO_COV" = true ] && echo 'disabled' || echo 'enabled')"
echo "============================================"
echo ""

# Ensure database exists (install modules)
echo ">>> Installing/updating modules: $MODULE_NAMES"
docker exec -u root "$CONTAINER" odoo \
  -d "$DB_NAME" \
  -i "$MODULE_NAMES" \
  --without-demo=True \
  --stop-after-init \
  --http-port=19999 \
  --log-level=warn 2>&1 | tail -5
echo ""

# Run tests WITHOUT tag filter (full chain)
echo ">>> Running ALL tests (no filter) on: $MODULE_NAMES"
if [[ "$NO_COV" = true ]]; then
  docker exec -u root "$CONTAINER" odoo \
    -d "$DB_NAME" \
    --test-tags "/$MODULE_NAMES" \
    --stop-after-init \
    --workers 0 \
    --http-port=19999 \
    --log-level=test 2>&1 | grep -E "(Starting|FAILED|ERROR|passed|failed|error\(s\))"
else
  docker exec -u root "$CONTAINER" bash -c "
    pip3 install coverage >/dev/null 2>&1 &&
    python3 -m coverage erase &&
    python3 -m coverage run --rcfile=/home/odoo/.coveragerc --source=$SOURCE_PATHS /usr/bin/odoo \
      -d $DB_NAME \
      --test-tags=/$MODULE_NAMES \
      --stop-after-init \
      --workers 0 \
      --http-port=19999 \
      --without-demo=True \
      --log-level=test &&
    python3 -m coverage report -m
  " 2>&1 | grep -E "(Starting|FAILED|ERROR|passed|failed|error\(s\)|TOTAL|Name|Stmts|Miss)"
fi
echo ""

# Run tests WITH specific tag filter
echo ">>> Running tests with tag filter: $TAGS"
if [[ "$NO_COV" = true ]]; then
  docker exec -u root "$CONTAINER" odoo \
    -d "$DB_NAME" \
    --test-tags "$TAGS" \
    --stop-after-init \
    --workers 0 \
    --http-port=19999 \
    --log-level=test 2>&1 | grep -E "(Starting|FAILED|ERROR|passed|failed|error\(s\))"
else
  docker exec -u root "$CONTAINER" bash -c "
    python3 -m coverage run --rcfile=/home/odoo/.coveragerc --source=$SOURCE_PATHS /usr/bin/odoo \
      -d $DB_NAME \
      --test-tags=$TAGS \
      --stop-after-init \
      --workers 0 \
      --http-port=19999 \
      --without-demo=True \
      --log-level=test &&
    python3 -m coverage report -m
  " 2>&1 | grep -E "(Starting|FAILED|ERROR|passed|failed|error\(s\)|TOTAL|Name|Stmts|Miss)"
fi
echo ""
echo "Done."

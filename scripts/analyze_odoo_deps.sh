
BASE_DIR="/Users/binaural28/Documents/christopher/projects/docker-odoo-only-multiversion-multiinstance"
CUSTOM_MODULES_DIR="$BASE_DIR/src/custom/binaural"

ADDONS_ODOO_PATH="/Users/binaural28/Documents/christopher/projects/odoo"
ADDONS_ENTERPRISE_PATH="$BASE_DIR/src/enterprise-19.0"

ADDONS_REPO_PATH="$BASE_DIR/src/custom/binaural"

ADDONS_INTEGRA_ADDONS_PATH="$ADDONS_REPO_PATH/integra-addons"
ADDONS_ODOO_VENEZUELA_PATH="$ADDONS_REPO_PATH/odoo-venezuela"
ADDONS_THIRD_PARTY_ADDONS_PATH="$ADDONS_REPO_PATH/third-party-addons"

# ADDONS_PATH="$ADDONS_ODOO_PATH,$ADDONS_ENTERPRISE_PATH,$ADDONS_INTEGRA_ADDONS_PATH,$ADDONS_ODOO_VENEZUELA_PATH,$ADDONS_THIRD_PARTY_ADDONS_PATH",$ADDONS_REPO_PATH

ADDONS_PATHS=(
  "$ADDONS_ODOO_PATH"
  "$ADDONS_ENTERPRISE_PATH"
  "$ADDONS_INTEGRA_ADDONS_PATH"
  "$ADDONS_ODOO_VENEZUELA_PATH"
  "$ADDONS_THIRD_PARTY_ADDONS_PATH"
  "$ADDONS_REPO_PATH"
)

ADDONS_PATH=$(IFS=, ; echo "${ADDONS_PATHS[*]}")

EVAL_DIRECTORY="$ADDONS_INTEGRA_ADDONS_PATH"

OUTPUT_PATH="$BASE_DIR/.ignore/deps.json"

python3 analyze_odoo_deps \
  --addons-path="$ADDONS_PATH" \
  --eval-directory="$EVAL_DIRECTORY" \
  --format=json \
  --output-path="$OUTPUT_PATH" \
  --verbose
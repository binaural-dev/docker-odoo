"""Paths, sys.path setup, and config-loader re-exports.

Everything that needs ``BASE_PATH`` or the generators.imports reads
them from here.
"""

import os
import sys
from pathlib import Path

BASE_PATH = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, os.path.join(BASE_PATH, ".resources"))

# fmt: off
from generators.config_loader import (  # noqa: E402
    is_instance_enabled,
    load_config,
    load_full_config,
    resolve_instance_config,
    resolve_db_config,
    get_db_host,
)
# fmt: on

TCSS_PATH = "styles/odoo-tui.tcss"

SCRIPT_PATH = os.path.join(BASE_PATH, "scripts")

"""Pure functions for stream parsing.

No side effects, no Textual imports — safe to import anywhere.
"""

import re
from typing import Optional, Tuple


def parse_progress(line: str) -> Optional[Tuple[int, int]]:
    """Extrae (current, total) de una línea que matchee (N/M).

    Returns:
        Tuple (current, total) si hay match, None si no.
        La primera aparicion setea el total; cada match actualiza el current.
    """
    match = re.search(r'\((\d+)/(\d+)\)', line)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return None


def classify_level(line: str) -> str:
    """Clasifica el nivel de log de una línea de stdout de Odoo.

    Busca el primer token de nivel en mayusculas al inicio de la línea
    o tras un espacio. Si no hay match, retorna 'INFO' por defecto.
    """
    for level in ("CRITICAL", "ERROR", "WARNING", "INFO"):
        if (
            line.startswith(level)
            or line.startswith(level + ":")
            or f" {level} " in line
            or f" {level}:" in line
        ):
            return level
    return "INFO"

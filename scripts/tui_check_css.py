#!/usr/bin/env python3
"""Valida que el CSS externo de la TUI se carga sin errores en el runtime real.

Uso:
    python3 scripts/tui_check_css.py
    python3 scripts/tui_check_css.py --css /ruta/a/otro.tcss

Que hace:
  1. Verifica que el archivo .tcss existe y se puede leer.
  2. Lo carga a traves del runtime real de Textual (App con CSS_PATH),
     que es el mismo camino que usa la app en produccion. Asi valida
     parseo + resolucion de variables de theme (no podemos replicar el
     set completo de variables de otra forma).
  3. Reporta cantidad de reglas, tiempo y exito/fallo.
  4. Verifica que el atributo CSS_PATH de DockerOdooApp apunte a un
     archivo que existe y parsea.

Salida:
  - exit 0 si todo OK.
  - exit 1 si el CSS no parsea o el archivo no existe.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
DEFAULT_CSS = REPO_ROOT / "tui" / "styles" / "odoo-tui.tcss"


async def _load_css_in_app(css_path: Path) -> tuple[int, float]:
    """Carga el CSS_PATH en una App real headless y devuelve (reglas, elapsed)."""
    from textual.app import App
    from textual.widgets import Static

    started = time.perf_counter()

    class _CssProbeApp(App):
        CSS_PATH = str(css_path)

        def compose(self):
            yield Static("css-probe")

    app = _CssProbeApp()
    async with app.run_test(headless=True, size=(80, 24)) as pilot:
        await pilot.pause()
        rule_count = len(app.stylesheet.rules) if hasattr(app.stylesheet, "rules") else 0
    elapsed = time.perf_counter() - started
    return rule_count, elapsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--css",
        type=Path,
        default=DEFAULT_CSS,
        help=f"Archivo .tcss a validar (default: {DEFAULT_CSS.relative_to(REPO_ROOT)}).",
    )
    args = parser.parse_args()

    css_path: Path = args.css
    if not css_path.is_absolute():
        css_path = (REPO_ROOT / css_path).resolve()

    print(f"[tui_check_css] target = {css_path}")
    if not css_path.exists():
        print(f"[tui_check_css] FAIL: archivo no encontrado: {css_path}")
        return 1

    css_text = css_path.read_text()
    print(f"[tui_check_css] size = {len(css_text)} bytes")

    # Validacion real: arrancar una App efimera con el CSS_PATH
    try:
        rule_count, elapsed = asyncio.run(_load_css_in_app(css_path))
    except Exception as exc:
        print(f"[tui_check_css] FAIL: la app tiro {type(exc).__name__}: {exc}")
        return 1
    print(
        f"[tui_check_css] App headless boot OK | rules = {rule_count} | "
        f"elapsed = {elapsed * 1000:.1f} ms"
    )
    if rule_count == 0:
        print("[tui_check_css] FAIL: la app no cargo ninguna regla (CSS vacio o no leido)")
        return 1

    # Verificacion cruzada: que el CSS_PATH de la app apunte a este mismo archivo
    try:
        from textual._path import _make_path_object_relative
        from tui.app import DockerOdooApp

        declared = DockerOdooApp.__dict__.get("CSS_PATH")
        if declared is None:
            print("[tui_check_css] NOTE: DockerOdooApp no define CSS_PATH (usa CSS inline)")
        else:
            app = DockerOdooApp()
            resolved_path = _make_path_object_relative(declared, app)
            print(f"[tui_check_css] DockerOdooApp.CSS_PATH = {declared!r}")
            print(
                f"[tui_check_css]   -> resuelve a {resolved_path}"
            )
            if resolved_path != css_path.resolve():
                print(
                    f"[tui_check_css] WARN: CSS_PATH resuelve a {resolved_path}, "
                    f"distinto del CSS validado {css_path}"
                )
            else:
                print("[tui_check_css] CSS_PATH resuelve al mismo archivo validado: OK")
    except Exception as exc:
        # La verificacion cruzada es informativa; no falla el script
        print(f"[tui_check_css] NOTE: no se pudo inspeccionar DockerOdooApp: {exc}")

    print("[tui_check_css] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

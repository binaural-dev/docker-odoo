"""Entry point for ``python3 -m tui`` and ``./odoo-tui``."""

import argparse
import sys

from tui.app import DockerOdooApp


def _parse_args(argv: list) -> argparse.Namespace:
    """Parsea los argumentos CLI de la TUI.

    Flags soportados:
      --dev         Activa modo desarrollo (booleano).
      --dev=all     Activa modo desarrollo con sub-modo 'all' (string).
    """
    parser = argparse.ArgumentParser(
        prog="odoo-tui",
        description="Launcher interactivo (Textual) para docker-odoo.",
    )
    parser.add_argument(
        "--dev",
        nargs="?",
        const=True,
        default=False,
        help=(
            "Habilita el modo desarrollo. Sin valor activa el modo "
            "booleano; --dev=all activa el sub-modo 'all'."
        ),
    )
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])
    try:
        DockerOdooApp(dev=args.dev).run()
    except Exception as exc:
        print(f"TUI crashed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

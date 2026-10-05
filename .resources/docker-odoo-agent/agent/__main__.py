"""
docker-odoo agent CLI.

    python3 -m agent token create <name> [--read-only]
    python3 -m agent token list
    python3 -m agent token revoke <name|id>
    python3 -m agent serve [--host 0.0.0.0] [--port 9000] [--docker-odoo <ruta>]

Run it from the root of this repo. Defaults come from var/agent.env,
written by install.sh.
"""

import argparse
import os
import sys

from . import settings
from .tokens import TokenStore


def main():
    parser = argparse.ArgumentParser(prog="python3 -m agent", description="Agente de docker-odoo")
    sub = parser.add_subparsers(dest="action", required=True)

    token_p = sub.add_parser("token", help="Gestiona los tokens de acceso")
    token_sub = token_p.add_subparsers(dest="token_action", required=True)
    create_p = token_sub.add_parser("create", help="Genera un token nuevo (se muestra una sola vez)")
    create_p.add_argument("name", help="Nombre para identificarlo, p. ej. general-18")
    create_p.add_argument("--read-only", action="store_true", help="Solo permite consultas (GET)")
    token_sub.add_parser("list", help="Lista los tokens (sin mostrar su valor)")
    revoke_p = token_sub.add_parser("revoke", help="Revoca un token por nombre o id")
    revoke_p.add_argument("name_or_id")

    serve_p = sub.add_parser("serve", help="Levanta la API")
    serve_p.add_argument("--host", default=settings.HOST)
    serve_p.add_argument("--port", type=int, default=settings.PORT)
    serve_p.add_argument("--docker-odoo", help="Ruta del checkout de docker-odoo (por defecto, la de var/agent.env)")

    args = parser.parse_args()

    if args.action == "serve":
        if args.docker_odoo:
            os.environ["DOCKER_ODOO_ROOT"] = args.docker_odoo
        try:
            print(f"docker-odoo: {settings.docker_odoo_root()}")
        except RuntimeError as e:
            sys.exit(f"Error: {e}")
        import uvicorn
        uvicorn.run("agent.main:app", host=args.host, port=args.port, workers=1)
        return

    store = TokenStore(settings.TOKENS_FILE)
    if args.token_action == "create":
        scopes = ("read",) if args.read_only else ("read", "write")
        try:
            token = store.create(args.name, scopes)
        except ValueError as e:
            sys.exit(f"Error: {e}")
        print(f"Token '{args.name}' creado con permisos: {', '.join(scopes)}\n")
        print(f"  {token}\n")
        print("Cópialo ahora: no se vuelve a mostrar. Pégalo en Odoo en")
        print("Gestión de instancias > Ajustes > Token del agente.")
    elif args.token_action == "list":
        tokens = store.list()
        if not tokens:
            print("No hay tokens.")
        for t in tokens:
            state = "REVOCADO" if t.get("revoked") else "activo"
            print(f"{t['id']}  {t['name']:<20} {','.join(t['scopes']):<11} {state:<9} "
                  f"creado {t['created_at']}  último uso {t['last_used_at'] or '-'}")
    elif args.token_action == "revoke":
        revoked = store.revoke(args.name_or_id)
        if not revoked:
            sys.exit(f"No hay tokens activos con nombre o id '{args.name_or_id}'")
        print(f"Revocado(s): {', '.join(revoked)}")


if __name__ == "__main__":
    main()

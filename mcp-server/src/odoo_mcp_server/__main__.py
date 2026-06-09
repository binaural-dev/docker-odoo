"""
Entry point for the Odoo MCP Server.
"""

import argparse
import json
import os
import sys

from .config import Config
from .server import create_server
from . import discovery_tools


def main():
    parser = argparse.ArgumentParser(description="Odoo Multi-Instance MCP Server")
    parser.add_argument(
        "--instances-json",
        default=os.environ.get("INSTANCES_JSON"),
        help="Path to instances.json (default: $INSTANCES_JSON env var)",
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        default=os.environ.get("ALLOW_WRITE", "false").lower() == "true",
        help="Enable write operations (default: $ALLOW_WRITE env var)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode - verify connection and exit",
    )
    parser.add_argument(
        "--list-instances",
        action="store_true",
        help="List configured instances and exit",
    )

    args = parser.parse_args()

    if not args.instances_json:
        print("Error: --instances-json or INSTANCES_JSON env var required", file=sys.stderr)
        sys.exit(1)

    try:
        config = Config(args.instances_json)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    if args.list_instances:
        result = discovery_tools.list_instances(config)
        print(result)
        sys.exit(0)

    if args.test:
        print("Testing configuration...")
        print(f"  instances.json: {args.instances_json}")
        print(f"  allow_write: {args.allow_write}")
        print(f"  instances: {len(config.get_instances())}")
        print(f"  databases: {len(config.get_databases())}")

        instances = config.get_instances()
        if instances:
            print("\nConfigured instances:")
            for name, inst in sorted(instances.items()):
                print(f"  - {name}: Odoo {inst.odoo_version} @ http://localhost:{inst.external_port} (db: {inst.database})")

        databases = config.get_databases()
        if databases:
            print("\nConfigured databases:")
            for name, db in sorted(databases.items()):
                print(f"  - {name}: PostgreSQL {db.postgres_version} @ {db.host}:{db.port}")

        print("\nConfiguration OK")
        sys.exit(0)

    mcp = create_server(config, allow_write=args.allow_write)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

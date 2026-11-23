"""Action lookup and command-line builders.

Depends on ``tui.models`` and ``tui.config`` only.
"""

from typing import Optional

from tui.models import (
    Action,
    ACTIONS,
    ARG_INSTANCE,
    ARG_DB,
    ARG_MODULES,
    ARG_USER,
    ARG_PASSWORD,
    ARG_REPO,
    ARG_BRANCH,
    ARG_LANG,
    ARG_ZIP,
    ARG_DEST_DB,
    ARG_TEST_TAGS,
    ARG_INSTALL,
    ARG_TARGET_PG,
    ARG_PATH,
)


def get_action(action_id: str) -> Action:
    for a in ACTIONS:
        if a.action_id == action_id:
            return a
    raise KeyError(f"Unknown action: {action_id}")


def _odoo_cli_args(action: Action, instance: Optional[str], args: dict) -> list:
    """Build argv for invoking ./odoo <action>."""
    argv = ["./odoo", action.action_id]
    if ARG_INSTANCE in action.needs and instance:
        argv.append(instance)

    if ARG_DB in action.needs and args.get("db"):
        argv += ["-d", args["db"]]
    if ARG_MODULES in action.needs and args.get("modules"):
        argv += ["-m", args["modules"]]
    if ARG_USER in action.needs and args.get("user"):
        argv += ["-l", args["user"]]
    if ARG_PASSWORD in action.needs and args.get("password"):
        argv += ["-p", args["password"]]
    if ARG_REPO in action.needs and args.get("repo"):
        argv.append(args["repo"])
    if ARG_BRANCH in action.needs and args.get("branch"):
        argv.append(args["branch"])
    return argv


def _script_args(action: Action, instance: Optional[str], args: dict) -> list:
    """Build argv for invoking scripts/<script>."""
    # The consolidated ``update`` action lives next to the ``script:*`` ones
    # but has a bare action_id (no colon). Resolve it explicitly so the rest
    # of the dispatch can stay generic.
    if action.action_id == "update":
        argv = ["scripts/odoo-update", instance, "-d", args["db"]]
        if args.get("modules"):
            argv += args["modules"].split(",")
        if args.get("load_language"):
            argv.append(f"--load-language={args['load_language']}")
        return argv

    sub = action.action_id.split(":", 1)[1]
    script = {
        "backup": "scripts/odoo_backup",
        "restore": "scripts/odoo_restore",
        "test": "scripts/odoo-test",
        "precommit": "scripts/precommit",
        "active_users": "scripts/odoo_active_users",
        "migrate": "scripts/migrate-module",
        "upgrade_manifest": "scripts/odoo-upgrade-manifest",
    }[sub]
    argv = [script]
    if sub == "backup":
        argv += ["backup", instance, "-d", args["db"],
                 "--target-pg-major", str(args["pg_major"]),
                 "-p", args["path"]]
    elif sub == "restore":
        argv += ["restore", instance, "-z", args["zip"], "-d", args["dest_db"]]
    elif sub == "test":
        argv += [instance, "-d", args["db"]]
        if args.get("test_tags"):
            argv += ["-t", args["test_tags"]]
        if args.get("install_modules"):
            argv += ["-i", args["install_modules"]]
    elif sub == "precommit":
        argv += [instance, "-m", "all"]
    elif sub == "active_users":
        argv += [instance]
    elif sub == "migrate":
        argv += [instance, "-d", args["db"]]
    elif sub == "upgrade_manifest":
        pass
    return argv

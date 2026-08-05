"""
Odoo ORM tools - XML-RPC access to Odoo instances.
"""

import json
import xmlrpc.client
from typing import Any, Dict, List, Optional

from .config import Config


def _get_odoo_connection(config: Config, instance: str, dbname: str, username: str = "admin", password: str = "admin"):
    url = config.get_odoo_url(instance)
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(dbname, username, password, {})
    if not uid:
        raise ValueError(f"Failed to authenticate with Odoo instance '{instance}' on database '{dbname}'")
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    return uid, password, dbname, models


def odoo_search_read(
    config: Config,
    instance: str,
    dbname: str,
    model: str,
    domain: Optional[List] = None,
    fields: Optional[List[str]] = None,
    limit: int = 100,
    offset: int = 0,
    order: Optional[str] = None,
    username: str = "admin",
    password: str = "admin",
) -> str:
    """Search and read records from an Odoo model via XML-RPC.

    Args:
        instance: Instance name from instances.json (e.g., 'gno', 'idv')
        dbname: PostgreSQL database name to query
        model: Odoo model name (e.g., 'res.partner', 'sale.order')
        domain: Odoo domain filter (e.g., [['state', '=', 'draft']])
        fields: List of field names to retrieve
        limit: Maximum number of records (default: 100)
        offset: Number of records to skip
        order: Order by field (e.g., 'name asc')
        username: Odoo username (default: 'admin')
        password: Odoo password (default: 'admin')
    """
    try:
        uid, pwd, db, models = _get_odoo_connection(config, instance, dbname, username, password)

        kwargs = {
            "offset": offset,
            "limit": limit,
        }
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order

        records = models.execute_kw(db, uid, pwd, model, "search_read", [domain or []], kwargs)

        return json.dumps({
            "model": model,
            "records": records,
            "count": len(records),
            "limit": limit,
            "offset": offset,
        }, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


def odoo_fields_get(
    config: Config,
    instance: str,
    dbname: str,
    model: str,
    username: str = "admin",
    password: str = "admin",
) -> str:
    """Get all fields definition of an Odoo model.

    Args:
        instance: Instance name from instances.json (e.g., 'gno', 'idv')
        dbname: PostgreSQL database name
        model: Odoo model name (e.g., 'res.partner', 'sale.order')
        username: Odoo username (default: 'admin')
        password: Odoo password (default: 'admin')
    """
    try:
        uid, pwd, db, models = _get_odoo_connection(config, instance, dbname, username, password)

        fields = models.execute_kw(
            db, uid, pwd, model, "fields_get", [],
            {"attributes": ["string", "type", "help", "required", "readonly", "searchable", "sortable"]}
        )

        return json.dumps({
            "model": model,
            "fields": fields,
            "field_count": len(fields),
        }, indent=2, default=str)
    except Exception as e:
        return f"Error: {e}"


def odoo_count(
    config: Config,
    instance: str,
    dbname: str,
    model: str,
    domain: Optional[List] = None,
    username: str = "admin",
    password: str = "admin",
) -> str:
    """Count records in an Odoo model.

    Args:
        instance: Instance name from instances.json (e.g., 'gno', 'idv')
        dbname: PostgreSQL database name
        model: Odoo model name (e.g., 'res.partner', 'sale.order')
        domain: Odoo domain filter (e.g., [['state', '=', 'draft']])
        username: Odoo username (default: 'admin')
        password: Odoo password (default: 'admin')
    """
    try:
        uid, pwd, db, models = _get_odoo_connection(config, instance, dbname, username, password)

        count = models.execute_kw(db, uid, pwd, model, "search_count", [domain or []])

        return json.dumps({
            "model": model,
            "domain": domain or [],
            "count": count,
        }, indent=2)
    except Exception as e:
        return f"Error: {e}"


def odoo_create(
    config: Config,
    instance: str,
    dbname: str,
    model: str,
    values: Dict[str, Any],
    allow_write: bool = False,
    username: str = "admin",
    password: str = "admin",
) -> str:
    """Create a new record in an Odoo model via XML-RPC.

    WARNING: This modifies data. Only available when ALLOW_WRITE=true.

    Args:
        instance: Instance name from instances.json (e.g., 'gno', 'idv')
        dbname: PostgreSQL database name
        model: Odoo model name (e.g., 'res.partner')
        values: Dictionary of field values for the new record
        allow_write: Whether write operations are allowed (set by env var)
        username: Odoo username (default: 'admin')
        password: Odoo password (default: 'admin')
    """
    if not allow_write:
        return "Error: Write operations are disabled. Set ALLOW_WRITE=true to enable."

    try:
        uid, pwd, db, models = _get_odoo_connection(config, instance, dbname, username, password)

        record_id = models.execute_kw(db, uid, pwd, model, "create", [values])

        return json.dumps({
            "status": "success",
            "model": model,
            "record_id": record_id,
        }, indent=2)
    except Exception as e:
        return f"Error: {e}"


def odoo_write(
    config: Config,
    instance: str,
    dbname: str,
    model: str,
    record_ids: List[int],
    values: Dict[str, Any],
    allow_write: bool = False,
    username: str = "admin",
    password: str = "admin",
) -> str:
    """Update existing records in an Odoo model via XML-RPC.

    WARNING: This modifies data. Only available when ALLOW_WRITE=true.

    Args:
        instance: Instance name from instances.json (e.g., 'gno', 'idv')
        dbname: PostgreSQL database name
        model: Odoo model name (e.g., 'res.partner')
        record_ids: List of record IDs to update
        values: Dictionary of field values to update
        allow_write: Whether write operations are allowed (set by env var)
        username: Odoo username (default: 'admin')
        password: Odoo password (default: 'admin')
    """
    if not allow_write:
        return "Error: Write operations are disabled. Set ALLOW_WRITE=true to enable."

    try:
        uid, pwd, db, models = _get_odoo_connection(config, instance, dbname, username, password)

        result = models.execute_kw(db, uid, pwd, model, "write", [record_ids, values])

        return json.dumps({
            "status": "success",
            "model": model,
            "record_ids": record_ids,
            "updated": result,
        }, indent=2)
    except Exception as e:
        return f"Error: {e}"

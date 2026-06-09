# Odoo MCP Server

MCP Server for Multi-Instance Odoo Docker - provides SQL and ORM access to Odoo databases for AI agents.

## Features

- **Discovery**: List instances, databases, and get instance info
- **SQL**: Direct PostgreSQL queries (SELECT, INSERT, UPDATE, DELETE)
- **Odoo ORM**: XML-RPC access to Odoo models (search_read, fields_get, count, create, write)
- **Read-only by default**: Write operations require `ALLOW_WRITE=true`

## Installation

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Usage

### As MCP Server (via OpenCode)

Add to `opencode.json`:

```json
{
  "mcp": {
    "odoo-db": {
      "type": "local",
      "command": ["/path/to/mcp-server/.venv/bin/python", "-m", "odoo_mcp_server"],
      "env": {
        "INSTANCES_JSON": "/path/to/multi-docker-odoo/instances.json",
        "ALLOW_WRITE": "false"
      }
    }
  }
}
```

### CLI Testing

```bash
# Test configuration
python -m odoo_mcp_server --instances-json /path/to/instances.json --test

# List instances
python -m odoo_mcp_server --instances-json /path/to/instances.json --list-instances
```

## Tools

### Discovery
- `list_instances()` - List all configured Odoo instances
- `list_databases()` - List all configured PostgreSQL databases
- `instance_info(instance_name)` - Get detailed instance information

### SQL
- `sql_query(database, dbname, query, limit)` - Execute SELECT queries
- `sql_tables(database, dbname, schema)` - List tables in a schema
- `sql_describe(database, dbname, table, schema)` - Describe table structure
- `sql_databases_list(database)` - List PostgreSQL databases
- `sql_execute(database, dbname, query)` - Execute write queries (requires ALLOW_WRITE=true)

### Odoo ORM
- `odoo_search_read(instance, dbname, model, domain, fields, limit, offset, order, username, password)` - Search and read records
- `odoo_fields_get(instance, dbname, model, username, password)` - Get model fields
- `odoo_count(instance, dbname, model, domain, username, password)` - Count records
- `odoo_create(instance, dbname, model, values, username, password)` - Create records (requires ALLOW_WRITE=true)
- `odoo_write(instance, dbname, model, record_ids, values, username, password)` - Update records (requires ALLOW_WRITE=true)

## Environment Variables

- `INSTANCES_JSON` - Path to instances.json
- `ALLOW_WRITE` - Enable write operations (default: false)

## License

MIT

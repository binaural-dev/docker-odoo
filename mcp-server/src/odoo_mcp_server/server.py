"""
MCP Server for Multi-Instance Odoo Docker.
Provides SQL and ORM access to Odoo databases for AI agents.
"""

import os
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from .config import Config
from . import discovery_tools
from . import db_tools
from . import odoo_tools


def create_server(config: Config, allow_write: bool = False) -> FastMCP:
    """Create and configure the MCP server with all tools."""

    mcp = FastMCP(
        "Odoo Multi-Instance MCP",
        instructions="Provides SQL and ORM access to Odoo databases for AI agents",
    )

    # Discovery tools
    @mcp.tool()
    def list_instances() -> str:
        """List all configured Odoo instances with their version, port, and database."""
        return discovery_tools.list_instances(config)

    @mcp.tool()
    def list_databases() -> str:
        """List all configured PostgreSQL databases."""
        return discovery_tools.list_databases(config)

    @mcp.tool()
    def instance_info(instance_name: str) -> str:
        """Get detailed information about a specific Odoo instance.

        Args:
            instance_name: Instance name from instances.json (e.g., 'gno', 'idv')
        """
        return discovery_tools.instance_info(config, instance_name)

    # SQL tools
    @mcp.tool()
    def sql_query(database: str, dbname: str, query: str, limit: int = 100) -> str:
        """Execute a SELECT query against a PostgreSQL database.

        Args:
            database: Database config name from instances.json (e.g., 'pg16')
            dbname: Actual PostgreSQL database name to connect to
            query: SQL SELECT query to execute
            limit: Maximum number of rows to return (default: 100)
        """
        return db_tools.sql_query(config, database, dbname, query, limit)

    @mcp.tool()
    def sql_tables(database: str, dbname: str, schema: str = "public") -> str:
        """List all tables in a PostgreSQL database schema.

        Args:
            database: Database config name from instances.json (e.g., 'pg16')
            dbname: Actual PostgreSQL database name to connect to
            schema: Schema name (default: 'public')
        """
        return db_tools.sql_tables(config, database, dbname, schema)

    @mcp.tool()
    def sql_describe(database: str, dbname: str, table: str, schema: str = "public") -> str:
        """Describe the structure of a PostgreSQL table (columns, types, constraints).

        Args:
            database: Database config name from instances.json (e.g., 'pg16')
            dbname: Actual PostgreSQL database name to connect to
            table: Table name to describe
            schema: Schema name (default: 'public')
        """
        return db_tools.sql_describe(config, database, dbname, table, schema)

    @mcp.tool()
    def sql_databases_list(database: str) -> str:
        """List all PostgreSQL databases available on a database server.

        Args:
            database: Database config name from instances.json (e.g., 'pg16')
        """
        return db_tools.sql_databases_list(config, database)

    if allow_write:
        @mcp.tool()
        def sql_execute(database: str, dbname: str, query: str) -> str:
            """Execute a write SQL query (INSERT, UPDATE, DELETE) against a PostgreSQL database.

            WARNING: This modifies data.

            Args:
                database: Database config name from instances.json (e.g., 'pg16')
                dbname: Actual PostgreSQL database name to connect to
                query: SQL query to execute (INSERT, UPDATE, DELETE, DDL)
            """
            return db_tools.sql_execute(config, database, dbname, query, allow_write=True)

    # Odoo ORM tools
    @mcp.tool()
    def odoo_search_read(
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
        return odoo_tools.odoo_search_read(
            config, instance, dbname, model, domain, fields, limit, offset, order, username, password
        )

    @mcp.tool()
    def odoo_fields_get(
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
        return odoo_tools.odoo_fields_get(config, instance, dbname, model, username, password)

    @mcp.tool()
    def odoo_count(
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
        return odoo_tools.odoo_count(config, instance, dbname, model, domain, username, password)

    if allow_write:
        @mcp.tool()
        def odoo_create(
            instance: str,
            dbname: str,
            model: str,
            values: dict,
            username: str = "admin",
            password: str = "admin",
        ) -> str:
            """Create a new record in an Odoo model via XML-RPC.

            WARNING: This modifies data.

            Args:
                instance: Instance name from instances.json (e.g., 'gno', 'idv')
                dbname: PostgreSQL database name
                model: Odoo model name (e.g., 'res.partner')
                values: Dictionary of field values for the new record
                username: Odoo username (default: 'admin')
                password: Odoo password (default: 'admin')
            """
            return odoo_tools.odoo_create(config, instance, dbname, model, values, allow_write=True, username=username, password=password)

        @mcp.tool()
        def odoo_write(
            instance: str,
            dbname: str,
            model: str,
            record_ids: List[int],
            values: dict,
            username: str = "admin",
            password: str = "admin",
        ) -> str:
            """Update existing records in an Odoo model via XML-RPC.

            WARNING: This modifies data.

            Args:
                instance: Instance name from instances.json (e.g., 'gno', 'idv')
                dbname: PostgreSQL database name
                model: Odoo model name (e.g., 'res.partner')
                record_ids: List of record IDs to update
                values: Dictionary of field values to update
                username: Odoo username (default: 'admin')
                password: Odoo password (default: 'admin')
            """
            return odoo_tools.odoo_write(config, instance, dbname, model, record_ids, values, allow_write=True, username=username, password=password)

    return mcp

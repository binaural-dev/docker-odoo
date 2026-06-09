"""
SQL tools - direct PostgreSQL query execution.
"""

import json
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import Config


def _get_connection(config: Config, database: str, dbname: str):
    params = config.get_db_connection_params(database)
    return psycopg2.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname=dbname,
    )


def sql_query(config: Config, database: str, dbname: str, query: str, limit: int = 100) -> str:
    """Execute a SELECT query against a PostgreSQL database.

    Args:
        database: Database config name from instances.json (e.g., 'pg16')
        dbname: Actual PostgreSQL database name to connect to
        query: SQL SELECT query to execute
        limit: Maximum number of rows to return (default: 100)
    """
    query = query.strip()

    if not query.upper().startswith("SELECT") and not query.upper().startswith("WITH"):
        return "Error: Only SELECT and WITH queries are allowed in read-only mode. Use sql_execute for write operations."

    try:
        conn = _get_connection(config, database, dbname)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                rows = cur.fetchmany(limit)
                total = cur.rowcount if cur.rowcount >= 0 else len(rows)

                result = {
                    "rows": [dict(row) for row in rows],
                    "row_count": len(rows),
                    "total": total,
                    "truncated": len(rows) < total,
                }

                return json.dumps(result, indent=2, default=str)
        finally:
            conn.close()
    except psycopg2.Error as e:
        return f"Database error: {e}"
    except Exception as e:
        return f"Error: {e}"


def sql_tables(config: Config, database: str, dbname: str, schema: str = "public") -> str:
    """List all tables in a PostgreSQL database schema.

    Args:
        database: Database config name from instances.json (e.g., 'pg16')
        dbname: Actual PostgreSQL database name to connect to
        schema: Schema name (default: 'public')
    """
    try:
        conn = _get_connection(config, database, dbname)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    ORDER BY table_name
                """, (schema,))

                tables = [row["table_name"] for row in cur.fetchall()]
                return json.dumps({"schema": schema, "tables": tables, "count": len(tables)}, indent=2)
        finally:
            conn.close()
    except psycopg2.Error as e:
        return f"Database error: {e}"


def sql_describe(config: Config, database: str, dbname: str, table: str, schema: str = "public") -> str:
    """Describe the structure of a PostgreSQL table (columns, types, constraints).

    Args:
        database: Database config name from instances.json (e.g., 'pg16')
        dbname: Actual PostgreSQL database name to connect to
        table: Table name to describe
        schema: Schema name (default: 'public')
    """
    try:
        conn = _get_connection(config, database, dbname)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        c.column_name,
                        c.data_type,
                        c.character_maximum_length,
                        c.is_nullable,
                        c.column_default,
                        CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                            AND tc.table_schema = kcu.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                            AND tc.table_schema = %s
                            AND tc.table_name = %s
                    ) pk ON c.column_name = pk.column_name
                    WHERE c.table_schema = %s AND c.table_name = %s
                    ORDER BY c.ordinal_position
                """, (schema, table, schema, table))

                columns = [dict(row) for row in cur.fetchall()]

                if not columns:
                    return f"Table '{schema}.{table}' not found."

                return json.dumps({
                    "table": f"{schema}.{table}",
                    "columns": columns,
                    "column_count": len(columns),
                }, indent=2, default=str)
        finally:
            conn.close()
    except psycopg2.Error as e:
        return f"Database error: {e}"


def sql_execute(config: Config, database: str, dbname: str, query: str, allow_write: bool = False) -> str:
    """Execute a write SQL query (INSERT, UPDATE, DELETE) against a PostgreSQL database.

    WARNING: This modifies data. Only available when ALLOW_WRITE=true.

    Args:
        database: Database config name from instances.json (e.g., 'pg16')
        dbname: Actual PostgreSQL database name to connect to
        query: SQL query to execute (INSERT, UPDATE, DELETE, DDL)
        allow_write: Whether write operations are allowed (set by env var)
    """
    if not allow_write:
        return "Error: Write operations are disabled. Set ALLOW_WRITE=true to enable."

    try:
        conn = _get_connection(config, database, dbname)
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                affected = cur.rowcount
                conn.commit()

                return json.dumps({
                    "status": "success",
                    "rows_affected": affected,
                    "query": query,
                }, indent=2)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except psycopg2.Error as e:
        return f"Database error: {e}"
    except Exception as e:
        return f"Error: {e}"


def sql_databases_list(config: Config, database: str) -> str:
    """List all PostgreSQL databases available on a database server.

    Args:
        database: Database config name from instances.json (e.g., 'pg16')
    """
    try:
        conn = _get_connection(config, database, "postgres")
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT datname
                    FROM pg_database
                    WHERE datistemplate = false
                    ORDER BY datname
                """)

                databases = [row["datname"] for row in cur.fetchall()]
                return json.dumps({"databases": databases, "count": len(databases)}, indent=2)
        finally:
            conn.close()
    except psycopg2.Error as e:
        return f"Database error: {e}"

#!/usr/bin/env python3
"""
PostgreSQL MCP Server para OpenCode.
Conecta a PostgreSQL via MCP (Model Context Protocol) using FastMCP.
Transporte: stdio (estándar para MCP servers locales en OpenCode).
"""

import os
import re
import json
from typing import Optional
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="postgres-mcp",
    instructions=(
        "PostgreSQL database server. Use these tools to query, inspect, and "
        "manage PostgreSQL databases. All queries are read-only by default. "
        "To enable write operations, set MCP_ALLOW_WRITE=true in the MCP environment."
    ),
)

# ---------------------------------------------------------------------------
# Configuración de conexión
# ---------------------------------------------------------------------------

DEFAULT_DB_URL = "postgresql://odoo:odoo@localhost:5432/postgres"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)
MCP_ALLOW_WRITE = os.environ.get("MCP_ALLOW_WRITE", "false").lower() in ("true", "1", "yes")


def _parse_url(url: str, target_db: Optional[str] = None) -> dict:
    """Parsea una DATABASE_URL y opcionalmente sobreescribe la base de datos."""
    parsed = urlparse(url)
    db_config = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "dbname": target_db or (parsed.path.lstrip("/") if parsed.path else "postgres"),
    }
    return db_config


def _get_connection(dbname: Optional[str] = None):
    """Crea una conexión a PostgreSQL usando DATABASE_URL o dbname override."""
    cfg = _parse_url(DATABASE_URL, target_db=dbname)
    return psycopg2.connect(**cfg)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

READONLY_BLOCKED = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


@mcp.tool()
def list_databases() -> str:
    """Lista todas las bases de datos accesibles en el servidor PostgreSQL."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
        )
        dbs = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return json.dumps({"databases": dbs}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_tables(database: Optional[str] = None) -> str:
    """Lista todas las tablas en la base de datos especificada.

    Args:
        database: Nombre de la base de datos. Si se omite usa la BD de DATABASE_URL.
    """
    try:
        conn = _get_connection(dbname=database)
        cur = conn.cursor()
        cur.execute(
            "SELECT schemaname, tablename FROM pg_tables "
            "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY schemaname, tablename"
        )
        tables = [{"schema": r[0], "table": r[1]} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return json.dumps({"tables": tables, "count": len(tables)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def describe_table(table: str, database: Optional[str] = None) -> str:
    """Describe el esquema de una tabla: columnas, tipos, PKs, FKs e índices.

    Args:
        table: Nombre completo de la tabla (schema.table o solo table).
        database: Base de datos. Si se omite usa la BD de DATABASE_URL.
    """
    try:
        conn = _get_connection(dbname=database)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Soporta schema.table
        if "." in table:
            schema, table_name = table.split(".", 1)
        else:
            schema, table_name = "public", table

        # Columnas
        cur.execute(
            """
            SELECT
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.is_nullable,
                c.column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END AS is_pk
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                    ON tc.constraint_name = ku.constraint_name
                    AND tc.table_schema = ku.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = %s
                    AND tc.table_name = %s
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
            """,
            (schema, table_name, schema, table_name),
        )
        columns = cur.fetchall()

        # Foreign keys
        cur.execute(
            """
            SELECT
                kcu.column_name,
                ccu.table_schema AS foreign_schema,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
            """,
            (schema, table_name),
        )
        fks = cur.fetchall()

        # Row count estimate
        cur.execute(
            "SELECT reltuples::bigint FROM pg_class "
            "WHERE oid = %s::regclass",
            (f"{schema}.{table_name}",),
        )
        row = cur.fetchone()
        row_count = row["reltuples"] if row else -1

        cur.close()
        conn.close()

        result = {
            "table": f"{schema}.{table_name}",
            "row_count_estimate": row_count,
            "columns": [dict(c) for c in columns],
            "foreign_keys": [dict(f) for f in fks],
        }
        # Serializar datetime/default values a string
        for col in result["columns"]:
            for k, v in col.items():
                if v is not None and not isinstance(v, (str, int, float, bool)):
                    col[k] = str(v)

        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def query(sql: str, database: Optional[str] = None, params: Optional[list] = None) -> str:
    """Ejecuta una consulta SQL (solo SELECT por defecto).

    Args:
        sql: Consulta SQL a ejecutar. Solo se permiten SELECT a menos que MCP_ALLOW_WRITE=true.
        database: Base de datos. Si se omite usa la BD de DATABASE_URL.
        params: Parámetros posicionales para la consulta (evita SQL injection).
    """
    sql_stripped = sql.strip()
    if not MCP_ALLOW_WRITE and READONLY_BLOCKED.match(sql_stripped):
        return json.dumps({
            "error": "Write operations are disabled. Set MCP_ALLOW_WRITE=true to enable.",
            "blocked_sql": sql_stripped[:100],
        })

    try:
        conn = _get_connection(dbname=database)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)

        if cur.description:
            rows = cur.fetchall()
            result = [dict(r) for r in rows]
            # Serializar valores no JSON-serializable
            for row in result:
                for k, v in row.items():
                    if v is not None and not isinstance(v, (str, int, float, bool)):
                        row[k] = str(v)
            cur.close()
            conn.close()
            return json.dumps({"rows": result, "count": len(result)}, indent=2, default=str)
        else:
            conn.commit()
            cur.close()
            conn.close()
            return json.dumps({"status": "ok", "rows_affected": cur.rowcount})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def execute(sql: str, database: Optional[str] = None) -> str:
    """Ejecuta sentencias DML/DDL (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP).

    IMPORTANTE: Esta tool solo funciona si MCP_ALLOW_WRITE=true está configurado.

    Args:
        sql: Sentencia SQL a ejecutar.
        database: Base de datos. Si se omite usa la BD de DATABASE_URL.
    """
    if not MCP_ALLOW_WRITE:
        return json.dumps({
            "error": "Write operations are disabled. Set MCP_ALLOW_WRITE=true in the MCP environment.",
        })

    try:
        conn = _get_connection(dbname=database)
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        rowcount = cur.rowcount
        status = cur.statusmessage
        cur.close()
        conn.close()
        return json.dumps({"status": "ok", "rows_affected": rowcount, "message": status})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def explain(sql: str, database: Optional[str] = None) -> str:
    """Ejecuta EXPLAIN ANALYZE de una consulta SQL.

    Args:
        sql: Consulta SQL a analizar.
        database: Base de datos. Si se omite usa la BD de DATABASE_URL.
    """
    try:
        conn = _get_connection(dbname=database)
        cur = conn.cursor()
        cur.execute(f"EXPLAIN ANALYZE {sql}")
        plan = "\n".join(row[0] for row in cur.fetchall())
        cur.close()
        conn.close()
        return json.dumps({"query_plan": plan}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_tables(pattern: str, database: Optional[str] = None) -> str:
    """Busca tablas cuyo nombre coincida con un patrón LIKE.

    Args:
        pattern: Patrón de búsqueda (usado con LIKE %pattern%).
        database: Base de datos. Si se omite usa la BD de DATABASE_URL.
    """
    try:
        conn = _get_connection(dbname=database)
        cur = conn.cursor()
        cur.execute(
            "SELECT schemaname, tablename FROM pg_tables "
            "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') "
            "AND tablename ILIKE %s "
            "ORDER BY schemaname, tablename",
            (f"%{pattern}%",),
        )
        tables = [{"schema": r[0], "table": r[1]} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return json.dumps({"tables": tables, "count": len(tables), "pattern": pattern}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")

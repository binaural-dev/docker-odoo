#!/usr/bin/env python3
"""
Test script for PostgreSQL MCP Server.
Sends JSON-RPC messages via stdin and reads responses from stdout.
Tests initialization, tool listing, and tool execution.
"""

import subprocess
import json
import sys
import time

PYTHON = "/home/binlp011/sources/docker-multi/scripts/mcp_servers/.venv/bin/python3"
SCRIPT = "/home/binlp011/sources/docker-multi/scripts/mcp_servers/postgres_server.py"

def make_request(method, params=None, req_id=1):
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg) + "\n"

def make_notification(method, params=None):
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg) + "\n"

def read_response(proc):
    """Read one JSON-RPC response from stdout."""
    line = proc.stdout.readline()
    if not line:
        return None
    return json.loads(line.strip())

def send_and_receive(proc, method, params=None, req_id=1):
    msg = make_request(method, params, req_id)
    print(f"\n>>> SEND: {msg.strip()}")
    proc.stdin.write(msg)
    proc.stdin.flush()
    resp = read_response(proc)
    print(f"<<< RECV: {json.dumps(resp, indent=2) if resp else 'None'}")
    return resp

def call_tool(proc, name, arguments=None, req_id=1):
    params = {"name": name, "arguments": arguments or {}}
    resp = send_and_receive(proc, "tools/call", params, req_id)
    return resp

def main():
    print("=" * 60)
    print("POSTGRESQL MCP SERVER TESTS")
    print("=" * 60)

    # Start the MCP server
    proc = subprocess.Popen(
        [PYTHON, SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"DATABASE_URL": "postgresql://odoo:odoo@localhost:5432/postgres", "PATH": "/usr/bin:/bin"},
    )

    try:
        # 1. Initialize
        print("\n--- TEST 1: Initialize ---")
        resp = send_and_receive(proc, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        })
        assert resp is not None and "result" in resp, f"Initialize failed: {resp}"
        print("PASS: Initialize OK")

        # Send initialized notification (no response expected)
        notif = make_notification("notifications/initialized")
        print(f"\n>>> SEND NOTIF: {notif.strip()}")
        proc.stdin.write(notif)
        proc.stdin.flush()

        # 2. List tools
        print("\n--- TEST 2: List Tools ---")
        resp = send_and_receive(proc, "tools/list", {}, req_id=2)
        assert resp is not None and "result" in resp, f"List tools failed: {resp}"
        tools = resp["result"].get("tools", [])
        tool_names = [t["name"] for t in tools]
        print(f"Found {len(tools)} tools: {tool_names}")
        expected = ["list_databases", "list_tables", "describe_table", "query", "execute", "explain", "search_tables"]
        for name in expected:
            assert name in tool_names, f"Tool '{name}' not found"
        print("PASS: All expected tools present")

        # 3. list_databases
        print("\n--- TEST 3: list_databases ---")
        resp = call_tool(proc, "list_databases", {}, req_id=3)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"Databases: {data.get('databases', [])}")
        assert "databases" in data, f"Unexpected response: {data}"
        assert len(data["databases"]) > 0, "No databases found"
        print(f"PASS: Found {len(data['databases'])} databases")

        # 4. list_tables (default database)
        print("\n--- TEST 4: list_tables ---")
        resp = call_tool(proc, "list_tables", {}, req_id=4)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"Tables count: {data.get('count', 0)}")
        if data.get("tables"):
            for t in data["tables"][:10]:
                print(f"  - {t['schema']}.{t['table']}")
            if data["count"] > 10:
                print(f"  ... and {data['count'] - 10} more")
        assert "tables" in data, f"Unexpected response: {data}"
        print(f"PASS: Found {data['count']} tables")

        # 5. search_tables
        print("\n--- TEST 5: search_tables ---")
        resp = call_tool(proc, "search_tables", {"pattern": "res_"}, req_id=5)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"Tables matching 'res_': {data.get('count', 0)}")
        for t in data.get("tables", []):
            print(f"  - {t['schema']}.{t['table']}")
        print("PASS: search_tables OK")

        # 6. describe_table
        if data.get("tables"):
            table_name = data["tables"][0]["table"]
            schema = data["tables"][0]["schema"]
            full_table = f"{schema}.{table_name}"
            print(f"\n--- TEST 6: describe_table ({full_table}) ---")
            resp = call_tool(proc, "describe_table", {"table": full_table}, req_id=6)
            content = resp["result"]["content"][0]["text"]
            desc = json.loads(content)
            print(f"Table: {desc.get('table')}")
            print(f"Row count estimate: {desc.get('row_count_estimate')}")
            print(f"Columns: {len(desc.get('columns', []))}")
            for col in desc.get("columns", [])[:5]:
                pk = " [PK]" if col.get("is_pk") else ""
                print(f"  - {col['column_name']}: {col['data_type']}{pk}")
            print(f"Foreign keys: {len(desc.get('foreign_keys', []))}")
            print("PASS: describe_table OK")
        else:
            print("\n--- TEST 6: SKIP (no tables found) ---")

        # 7. query (simple SELECT)
        print("\n--- TEST 7: query (SELECT 1) ---")
        resp = call_tool(proc, "query", {"sql": "SELECT 1 AS test_value, current_database() AS db"}, req_id=7)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"Result: {data}")
        assert "rows" in data, f"Unexpected response: {data}"
        assert data["rows"][0]["test_value"] == 1
        print("PASS: query SELECT OK")

        # 8. query with params
        print("\n--- TEST 8: query with params ---")
        resp = call_tool(proc, "query", {
            "sql": "SELECT %s::int AS num, %s::text AS txt",
            "params": [42, "hello"]
        }, req_id=8)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"Result: {data}")
        assert data["rows"][0]["num"] == 42
        assert data["rows"][0]["txt"] == "hello"
        print("PASS: query with params OK")

        # 9. explain
        print("\n--- TEST 9: explain ---")
        resp = call_tool(proc, "explain", {"sql": "SELECT 1"}, req_id=9)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"Plan:\n{data.get('query_plan', '')}")
        assert "query_plan" in data
        print("PASS: explain OK")

        # 10. query (write blocked)
        print("\n--- TEST 10: query (write blocked by default) ---")
        resp = call_tool(proc, "query", {"sql": "CREATE TABLE test_mcp_block (id INT)"}, req_id=10)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"Result: {data}")
        assert "error" in data, f"Write should have been blocked: {data}"
        print("PASS: Write blocked correctly")

        # 11. execute (write disabled)
        print("\n--- TEST 11: execute (write disabled) ---")
        resp = call_tool(proc, "execute", {"sql": "CREATE TABLE test_mcp_block (id INT)"}, req_id=11)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"Result: {data}")
        assert "error" in data, f"Execute should have been disabled: {data}"
        print("PASS: execute disabled correctly")

        # 12. list_databases with specific database
        print("\n--- TEST 12: list_tables on specific DB ---")
        resp = call_tool(proc, "list_tables", {"database": "postgres"}, req_id=12)
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"Tables in 'postgres' DB: {data.get('count', 0)}")
        print("PASS: list_tables with database param OK")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        # Print stderr for debugging
        stderr_output = proc.stderr.read() if proc.stderr else ""
        if stderr_output:
            print(f"\nSTDERR:\n{stderr_output}")
        sys.exit(1)
    finally:
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()

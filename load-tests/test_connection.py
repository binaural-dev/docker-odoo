#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba de conexión a Odoo.sh
Úsalo para verificar que la conexión funciona antes de ejecutar Locust.
"""

import sys
import time
import requests

# Configuración - AJUSTA ESTO
try:
    from instances_config import INSTANCES
    
    # Selecciona tu instancia de Odoo.sh
    INSTANCE_NAME = "petare"  # Cambia esto
    config = INSTANCES.get(INSTANCE_NAME)
    
    if not config:
        print(f"❌ Error: Instancia '{INSTANCE_NAME}' no encontrada")
        sys.exit(1)
    
    HOST = config["host"]
    PORT = config["port"]
    DATABASE = config["database"]
    LOGIN = config["login"]
    PASSWORD = config["password"]
    PROTOCOL = config["protocol"]
    
except ImportError:
    # Configuración manual si no se encuentra instances_config
    HOST = input("Host (ej: mi-empresa.odoo.com): ").strip()
    PORT = int(input("Port (443 para HTTPS): ") or "443")
    DATABASE = input("Database name: ").strip()
    LOGIN = input("Login (admin): ").strip() or "admin"
    PASSWORD = input("Password: ").strip()
    PROTOCOL = input("Protocol (jsonrpcs para HTTPS): ").strip() or "jsonrpcs"

# Construir URL base
if PROTOCOL == "jsonrpcs":
    BASE_URL = f"https://{HOST}:{PORT}" if PORT != 443 else f"https://{HOST}"
else:
    BASE_URL = f"http://{HOST}:{PORT}" if PORT != 80 else f"http://{HOST}"

print(f"\n{'='*60}")
print(f"Test de Conexión a Odoo.sh")
print(f"{'='*60}")
print(f"Host: {HOST}")
print(f"Port: {PORT}")
print(f"Database: {DATABASE}")
print(f"Login: {LOGIN}")
print(f"Protocol: {PROTOCOL}")
print(f"Base URL: {BASE_URL}")
print(f"{'='*60}\n")

# Test 1: Verificar que el host responde HTTP
print("Test 1: Verificando conectividad HTTP...")
try:
    response = requests.get(f"{BASE_URL}/web", timeout=30, allow_redirects=True)
    print(f"  ✅ HTTP OK - Status: {response.status_code}")
    if response.status_code == 200:
        print(f"  ✅ Servidor respondiendo correctamente")
    elif response.status_code in [301, 302, 307, 308]:
        print(f"  ⚠️  Redirección a: {response.headers.get('Location', 'desconocido')}")
except requests.exceptions.Timeout:
    print(f"  ❌ Timeout - El servidor no respondió en 30 segundos")
    print(f"     Posible causa: Instancia dormida (sleeping) en Odoo.sh")
except requests.exceptions.ConnectionError as e:
    print(f"  ❌ Error de conexión: {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# Test 2: Intentar login vía JSON-RPC
print("\nTest 2: Intentando login vía JSON-RPC...")

jsonrpc_url = f"{BASE_URL}/jsonrpc"
payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "service": "common",
        "method": "login",
        "args": [DATABASE, LOGIN, PASSWORD]
    },
    "id": 1
}

try:
    response = requests.post(
        jsonrpc_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60  # Mayor timeout para Odoo.sh (puede necesitar "despertar")
    )
    
    result = response.json()
    
    if "error" in result:
        error = result["error"]
        print(f"  ❌ Error JSON-RPC: {error.get('message', 'Unknown error')}")
        if "database" in str(error.get('data', {})).lower():
            print(f"  💡 Posible causa: Nombre de base de datos incorrecto")
        elif "credentials" in str(error).lower() or "password" in str(error).lower():
            print(f"  💡 Posible causa: Usuario o contraseña incorrectos")
    elif "result" in result:
        user_id = result["result"]
        if user_id:
            print(f"  ✅ Login exitoso! User ID: {user_id}")
        else:
            print(f"  ❌ Login falló (User ID: False)")
            print(f"  💡 Verifica usuario y contraseña")
    else:
        print(f"  ⚠️  Respuesta inesperada: {result}")
        
except requests.exceptions.Timeout:
    print(f"  ❌ Timeout en JSON-RPC")
    print(f"     Esto es normal en Odoo.sh si la instancia estaba dormida")
    print(f"     Intenta de nuevo en unos segundos...")
except Exception as e:
    print(f"  ❌ Error: {e}")

print(f"\n{'='*60}")
print("Si los tests pasaron, ya puedes ejecutar Locust:")
print(f"  ./run_test.sh test_generic_read.py")
print(f"{'='*60}\n")

# Guía: Configurar Locust en una Nueva PC

Esta guía explica cómo mover y configurar el setup de pruebas de estrés a una nueva computadora.

---

## 📋 Paso 1: Copiar Archivos Necesarios

Necesitas copiar estos archivos desde tu PC actual:

```
load-tests/
├── requirements.txt          # Dependencias Python
├── locust.conf              # Configuración base (opcional)
├── instances_config.py      # ⚠️ NECESITA AJUSTES
├── base_test.py             # Clase base
├── run_test.sh              # Script helper
├── test_generic_read.py     # Tests disponibles
├── test_crm_leads.py
└── test_sales_orders.py
```

**No necesitas copiar:**
- Carpeta `__pycache__/` (se regenera)
- Archivos `.pyc` (compilados)

---

## 🐍 Paso 2: Instalar Dependencias

### En Ubuntu/Debian:
```bash
# 1. Instalar Python y pip
sudo apt update
sudo apt install python3 python3-pip -y

# 2. Ir al directorio del proyecto
cd /ruta/a/load-tests

# 3. Instalar dependencias
pip3 install --break-system-packages -r requirements.txt

# 4. Verificar instalación
locust --version
```

### En macOS:
```bash
# 1. Instalar Homebrew si no lo tienes
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Instalar Python
brew install python

# 3. Instalar dependencias
cd /ruta/a/load-tests
pip3 install -r requirements.txt

# 4. Verificar
locust --version
```

### En Windows (con Python instalado):
```powershell
# 1. Abrir PowerShell como administrador
# 2. Ir al directorio
cd C:\ruta\a\load-tests

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Verificar
locust --version
```

---

## ⚙️ Paso 3: Configurar Instancias (IMPORTANTE)

El archivo `instances_config.py` **DEBE ser modificado** para la nueva PC:

### Opción A: Odoo en la misma PC (localhost)

Si Odoo corre localmente:

```python
INSTANCES = {
    "mi_instancia": {
        "host": "localhost",           # ← localhost si es local
        "port": 8069,                  # ← Puerto de Odoo
        "database": "nombre_bd",       # ← Nombre exacto de la BD
        "login": "admin",              # ← Usuario
        "password": "admin",           # ← Contraseña
        "protocol": "jsonrpc",         # ← jsonrpc (HTTP) o jsonrpcs (HTTPS)
        "odoo_version": "17.0",
        "description": "Mi instancia local"
    },
}
```

### Opción B: Odoo en servidor remoto

Si Odoo está en otro servidor:

```python
INSTANCES = {
    "mi_instancia": {
        "host": "192.168.1.100",       # ← IP del servidor Odoo
        "port": 8069,                  # ← Puerto externo
        "database": "nombre_bd",
        "login": "admin",
        "password": "admin",
        "protocol": "jsonrpcs",        # ← jsonrpcs si usa HTTPS
        "odoo_version": "17.0",
        "description": "Odoo en servidor remoto"
    },
}
```

### Opción C: Docker (como tu setup actual)

Si usas Docker como en tu PC actual:

```python
INSTANCES = {
    "mercedes": {
        "host": "localhost",
        "port": 8097,                  # ← Puerto mapeado del contenedor
        "database": "odoo_mercedes_production",  # ← Nombre real en PostgreSQL
        "login": "admin",
        "password": "admin",
        "protocol": "jsonrpc",
        "odoo_version": "19.0",
        "description": "Instancia Mercedes"
    },
}
```

---

## 🔍 Paso 4: Verificar Conectividad

Antes de ejecutar Locust, prueba que puedes llegar a Odoo:

### 1. Test de conectividad básica:
```bash
# Si Odoo está en localhost:8069
curl http://localhost:8069/web/database/selector

# Debería devolver HTML (página de selección de BD)
```

### 2. Verificar que la base de datos existe:
```bash
# Si tienes acceso a PostgreSQL
docker exec db-pg16 psql -U odoo -c "SELECT datname FROM pg_database;"

# O preguntarle a Odoo directamente
curl -X POST http://localhost:8069/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "call", "params": {"service": "db", "method": "list", "args": []}, "id": 1}'
```

### 3. Probar login manual:
```bash
# Crear un script de prueba Python
cat > test_connection.py << 'EOF'
import odoolib

connection = odoolib.get_connection(
    hostname="localhost",
    port=8069,
    database="nombre_de_tu_bd",
    login="admin",
    password="admin",
    protocol="jsonrpc"
)

print("Conexión exitosa!")
print(f"User ID: {connection.user_id}")
EOF

python3 test_connection.py
```

---

## 🚀 Paso 5: Ejecutar el Test

```bash
# Ir al directorio
cd /ruta/a/load-tests

# Hacer ejecutable el script (Linux/Mac)
chmod +x run_test.sh

# Ejecutar test
./run_test.sh test_generic_read.py

# O con Locust directamente
locust -f test_generic_read.py
```

---

## 🐛 Solución de Problemas Comunes

### Error: "locust: command not found"
```bash
# Asegurar que ~/.local/bin está en el PATH
export PATH="$HOME/.local/bin:$PATH"

# O usar ruta completa
python3 -m locust -f test_generic_read.py
```

### Error: "database 'X' does not exist"
- Verifica que el nombre en `instances_config.py` coincida exactamente
- Usa: `docker exec db-pg16 psql -U odoo -c "\l"` para ver nombres reales

### Error: "Connection refused"
- Verifica que Odoo esté corriendo: `docker ps`
- Verifica el puerto: `netstat -tlnp | grep 8069`
- Prueba con: `curl http://localhost:PUERTO`

### Error: "Authentication failed"
- Verifica usuario y contraseña en `instances_config.py`
- Prueba login manual en la interfaz web de Odoo

### Error: "No module named 'instances_config'"
- Asegúrate de ejecutar desde el directorio `load-tests/`
- Verifica que `instances_config.py` exista

---

## 📦 Checklist de Migración

- [ ] Copiar todos los archivos `.py` y `.sh`
- [ ] Instalar Python 3.8+
- [ ] Instalar dependencias con `pip3 install -r requirements.txt`
- [ ] Modificar `instances_config.py` con IPs/puertos correctos
- [ ] Verificar que nombres de BD sean correctos
- [ ] Probar conectividad con `curl` o script Python
- [ ] Ejecutar `./run_test.sh -l` para verificar configuración
- [ ] Ejecutar test básico

---

## 💾 Backup de Configuración

Guarda esta información antes de mover a nueva PC:

```bash
# Guardar configuración actual
cd ~/multi-docker-odoo/load-tests

# Ver qué instancias tienes
grep -A 10 "INSTANCES = {" instances_config.py > ~/mis_instancias_backup.txt

# Ver versiones instaladas
pip3 freeze > ~/requirements_backup.txt
```

---

## ❓ Preguntas Frecuentes

**Q: ¿Puedo usar el mismo setup para varias PCs?**
R: Sí, pero cada PC necesita su propia `instances_config.py` con las IPs correctas.

**Q: ¿Funciona en Windows?**
R: Sí, pero usa PowerShell o Git Bash. El script `run_test.sh` necesita Git Bash o WSL.

**Q: ¿Necesito instalar Docker?**
R: No, solo necesitas acceso a una instancia Odoo (local o remota).

**Q: ¿Puedo probar contra Odoo Online (odoo.com)?**
R: No, necesitas acceso JSON-RPC. Odoo Online no permite conexiones externas por RPC.

---

## 📞 Soporte

Si tienes problemas:
1. Verifica logs de Odoo: `docker logs odoo-mercedes`
2. Revisa que PostgreSQL acepte conexiones
3. Prueba con usuario "demo" si existe
4. Activa modo debug en Odoo para ver errores

# Pruebas de Estrés para Odoo con Locust

Este directorio contiene un setup completo para realizar pruebas de estrés (load testing) en tus instancias Odoo usando [Locust](https://locust.io/).

## 📋 Requisitos

- Python 3.8+
- pip o pip3
- Instancias Odoo en ejecución

## 🚀 Instalación Rápida

```bash
# 1. Ir al directorio de tests
cd load-tests

# 2. Instalar dependencias
./run_test.sh -r

# O manualmente:
pip3 install -r requirements.txt
```

## 📁 Estructura del Proyecto

```
load-tests/
├── README.md                # Este archivo
├── requirements.txt         # Dependencias de Python
├── locust.conf             # Configuración base de Locust
├── instances_config.py     # Configuración de tus instancias Odoo
├── base_test.py           # Clase base para todos los tests
├── run_test.sh            # Script helper para ejecutar tests
│
├── test_generic_read.py    # Test de lectura básica (recomendado para empezar)
├── test_crm_leads.py     # Test específico para CRM
└── test_sales_orders.py  # Test específico para Ventas
```

## 🔧 Configuración

### 1. Configurar Instancias

Edita `instances_config.py` y ajusta:
- Nombre de la base de datos (`database`)
- Credenciales (`login`, `password`)
- Puerto de la instancia (`port`)
- Protocolo (`jsonrpc` para HTTP, `jsonrpcs` para HTTPS)

### 2. Seleccionar Instancia en el Test

En cada archivo de test, modifica la línea:
```python
instance_name = "cadipa1"  # <-- Cambia esto
```

## ▶️ Ejecutar Tests

### Modo Interactivo (con UI Web)

```bash
# Ejecutar test genérico
./run_test.sh test_generic_read.py

# Se abrirá http://localhost:8089
```

### Modo Headless (sin UI, para automatización)

```bash
# 100 usuarios, spawn de 10/seg, durante 5 minutos
./run_test.sh -h test_generic_read.py --users 100 --spawn-rate 10 --run-time 5m
```

### Con Workers Distribuidos

```bash
# Usar 4 workers para mayor carga
./run_test.sh -w 4 test_generic_read.py
```

### Usando Locust Directamente

```bash
# Modo interactivo
locust -f test_generic_read.py

# Modo headless
locust -f test_generic_read.py --headless --users 50 --spawn-rate 5 --run-time 10m

# Con configuración personalizada
locust -f test_generic_read.py --config locust.conf
```

## 📊 Tests Disponibles

### `test_generic_read.py` - Recomendado para empezar
Prueba operaciones básicas de lectura:
- Leer partners (clientes/proveedores)
- Leer productos
- Leer órdenes de venta
- Buscar con dominios
- Contar registros

### `test_crm_leads.py`
Prueba específico para CRM:
- Leer leads y oportunidades
- Navegar por pipeline (kanban)
- Leer contactos
- Métricas de dashboard

### `test_sales_orders.py`
Prueba específico para Ventas:
- Leer órdenes de venta
- Filtrar por estados
- Leer líneas de órdenes
- Catálogo de productos

## 🎯 Interpretar Resultados

### Métricas Clave en la UI Web

- **RPS (Requests Per Second)**: Peticiones por segundo
- **Failure Rate**: Porcentaje de errores
- **Response Time**: Tiempo de respuesta (ms)
- **Number of Users**: Usuarios activos

### Umbrales Recomendados

| Métrica | Aceptable | Preocupante |
|---------|-----------|-------------|
| RPS | > 50 | < 20 |
| Tiempo de respuesta | < 500ms | > 2000ms |
| Failure Rate | < 1% | > 5% |

## 🛠️ Crear Nuevos Tests

1. Crea un archivo `test_mi_modulo.py`
2. Extiende `BaseOdooUser` desde `base_test.py`
3. Define tus tareas con el decorador `@task(peso)`

```python
from locust import task, between
from base_test import BaseOdooUser


class MiUsuario(BaseOdooUser):
    abstract = False
    instance_name = "cadipa1"
    wait_time = between(1, 5)

    def on_start(self):
        super().on_start()
        self.mi_modelo = self.client.get_model('mi.modelo')

    @task(10)
    def mi_tarea(self):
        try:
            ids = self.mi_modelo.search([])
            if ids:
                self.mi_modelo.read(ids[:10])
        except Exception as e:
            pass
```

## 📝 Comandos Útiles

```bash
# Listar instancias configuradas
./run_test.sh -l

# Instalar/actualizar dependencias
./run_test.sh -r

# Ver ayuda
./run_test.sh --help

# Exportar resultados a CSV
locust -f test_generic_read.py --headless --csv=resultados
```

## ⚠️ Precauciones

1. **Nunca hagas pruebas en producción**: Usa instancias de staging/testing
2. **Empieza suave**: Comienza con pocos usuarios (5-10) y aumenta gradualmente
3. **Monitorea recursos**: Observa CPU, RAM y PostgreSQL durante las pruebas
4. **Respeta límites**: Si ves errores 500/502, reduce la carga

## 🔗 Recursos

- [Documentación de Locust](https://docs.locust.io/)
- [GitHub OdooLocust](https://github.com/odoo/odoo-client-lib)
- [Odoo RPC Documentation](https://www.odoo.com/documentation/17.0/developer/reference/external_api.html)

## ❓ Solución de Problemas

### Error: "Connection refused"
- Verifica que la instancia Odoo esté ejecutándose
- Confirma el puerto en `instances_config.py`

### Error: "Authentication failed"
- Revisa usuario y contraseña en `instances_config.py`
- Verifica que la base de datos exista

### Error: "Module not found"
- Ejecuta `./run_test.sh -r` para instalar dependencias
- Verifica que estás en el directorio `load-tests/`

### Bajo rendimiento (RPS muy bajo)
- Aumenta `workers` si CPU es el cuello de botella
- Verifica índices en PostgreSQL
- Considera aumentar workers de Odoo

---

¿Preguntas? ¡Crea un issue o consulta la documentación de Locust!

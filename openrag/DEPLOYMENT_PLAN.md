# Plan de Infraestructura: OpenRAG en docker-multi

## Resumen del Estado Actual

| Recurso           | Valor                        |
| ----------------- | ---------------------------- |
| Docker            | v29.5.2                      |
| Docker Compose    | v5.1.4                       |
| RAM               | 15 GB total, ~6 GB libres    |
| CPU               | 20 cores                     |
| Disco libre       | 33 GB en `/`                 |
| Python            | 3.13.5                       |
| pip               | 25.1.1                       |
| uv                | ❌ NO INSTALADO              |
| Red Docker        | `docker-multi_odoo-multi` (172.18.0.0/16) |

### Puertos Disponibles

| Puerto | Servicio OpenRAG   | Estado |
| ------ | ------------------ | ------ |
| 3000   | Frontend (Next.js) | ✅ Libre |
| 5001   | Docling Serve      | ✅ Libre |
| 5601   | OpenSearch Dashboards | ✅ Libre |
| 7860   | Langflow           | ✅ Libre |
| 8000   | Backend (FastAPI)  | ✅ Libre |
| 9200   | OpenSearch         | ✅ Libre |

---

## Arquitectura Propuesta

```
                    ┌──────────────────────────────────────────┐
                    │           docker-multi_odoo-multi         │
                    │          (172.18.0.0/16 bridge)           │
                    │                                            │
                    │  ┌─────────────┐  ┌───────────────────┐   │
                    │  │ Odoo 19.x   │  │ Odoo 17.x         │   │
                    │  │ (:8070-8076)│  │ (:8074)           │   │
                    │  └─────────────┘  └───────────────────┘   │
                    │                                            │
                    │  ┌─────────────┐  ┌───────────────────┐   │
                    │  │ OpenRAG     │  │ OpenSearch        │   │
                    │  │ Backend     │  │ (:9200)           │   │
                    │  │ (:8000)     │  └───────────────────┘   │
                    │  └─────────────┘                           │
                    │                                            │
                    │  ┌─────────────┐  ┌───────────────────┐   │
                    │  │ OpenRAG     │  │ OpenSearch        │   │
                    │  │ Frontend    │  │ Dashboards        │   │
                    │  │ (:3000)     │  │ (:5601)           │   │
                    │  └─────────────┘  └───────────────────┘   │
                    │                                            │
                    │  ┌─────────────────────────────────────┐   │
                    │  │ Langflow (:7860)                    │   │
                    │  └─────────────────────────────────────┘   │
                    └──────────────────────────────────────────┘

                    ┌──────────────────────────────────────────┐
                    │              HOST (fuera de Docker)       │
                    │  ┌──────────────────────────────────────┐ │
                    │  │ Docling Serve (:5001)                │ │
                    │  │ (uv run python scripts/docling_ctl)  │ │
                    │  └──────────────────────────────────────┘ │
                    │                                            │
                    │  ┌──────────────────────────────────────┐ │
                    │  │ OpenCode + OpenRAG MCP               │ │
                    │  │ localhost:3000/mcp                   │ │
                    │  └──────────────────────────────────────┘ │
                    └──────────────────────────────────────────┘
```

### Servicios OpenRAG

| Servicio                | Container             | Puerto Host | Puerto Container | Imagen                    |
| ----------------------- | --------------------- | ----------- | ---------------- | ------------------------- |
| OpenRAG Backend         | openrag-backend       | 8000        | 8000             | openrag-backend:latest    |
| OpenRAG Frontend        | openrag-frontend      | 3000        | 3000             | openrag-frontend:latest   |
| Langflow                | openrag-langflow      | 7860        | 7860             | openrag-langflow:latest   |
| OpenSearch              | openrag-opensearch    | 9200        | 9200             | opensearchproject:latest  |
| OpenSearch Dashboards   | openrag-dashboards    | 5601        | 5601             | opensearch-dashboards:latest |
| Docling Serve           | (HOST, no container)  | 5001        | —                | —                         |

### Por qué Docling Serve va en el HOST

OpenRAG oficial documenta que Docling **no puede correr dentro de un contenedor Docker** debido a dependencias a nivel de sistema (librerías de OCR, procesamiento de imágenes). La documentación oficial establece:

> *"Docling cannot run inside a Docker container due to system-level dependencies, so you must manage it as a separate service on the host machine."*

Se ejecuta via:
```bash
uv run python scripts/docling_ctl.py start --port 5001
```

---

## Plan de Implementación (8 Fases)

### Fase 0: Prerequisitos

```bash
# 0.1 Instalar uv (gestor de paquetes Python requerido por OpenRAG)
pip install uv
# Verificar
uv --version

# 0.2 Verificar Python 3.13
python3 --version  # debe ser 3.13.x

# 0.3 Crear directorio de trabajo
mkdir -p /home/binlp011/sources/docker-multi/openrag
```

**Tiempo estimado**: 5 min

---

### Fase 1: Clonar y Configurar OpenRAG

```bash
# 1.1 Clonar repositorio
cd /home/binlp011/sources/docker-multi/openrag
git clone https://github.com/langflow-ai/openrag.git .
# O descargar solo lo necesario si ya hay clon:
# git init && git remote add origin https://github.com/langflow-ai/openrag.git && git fetch && git checkout main

# 1.2 Sincronizar dependencias con uv
uv sync

# 1.3 Crear archivo .env desde example
cp .env.example .env
```

**Archivo `.env` mínimo funcional**:

```bash
# === REQUERIDO ===
OPENSEARCH_PASSWORD=OpenRag2026!Secure
LANGFLOW_SUPERUSER=admin
LANGFLOW_SUPERUSER_PASSWORD=admin123
LANGFLOW_SECRET_KEY=sk-oger-secret-2024-change-me

# === MODELOS (al menos uno) ===
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-...
# OLLAMA_ENDPOINT=http://localhost:11434

# === PUERTOS (defaults) ===
FRONTEND_PORT=3000
LANGFLOW_PORT=7860
OPENRAG_BACKEND_PORT=8000

# === DOCLING ===
# DOCLING_SERVE_URL=http://host.docker.internal:5001
HOST_DOCKER_INTERNAL=host.docker.internal.rag

# === ALMACENAMIENTO ===
OPENRAG_STORAGE_MODE=rag_db

# === RED ===
# OpenRAG se conectará a la red odoo-multi
# No sobreescribir OPENSEARCH_HOST manualmente (se usará docker networking)
```

**Tiempo estimado**: 10 min

---

### Fase 2: Crear docker-compose Override para docker-multi

Crear `/home/binlp011/sources/docker-multi/openrag/docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  openrag-backend:
    container_name: openrag-backend
    networks:
      odoo-multi:
        aliases:
          - openrag-backend
    # La imagen se construye desde Dockerfile.backend

  openrag-frontend:
    container_name: openrag-frontend
    networks:
      - odoo-multi
    ports:
      - "3000:3000"
    depends_on:
      - openrag-backend

  openrag-langflow:
    container_name: openrag-langflow
    networks:
      odoo-multi:
        aliases:
          - openrag-langflow
    ports:
      - "7860:7860"

  openrag-opensearch:
    container_name: openrag-opensearch
    networks:
      odoo-multi:
        aliases:
          - openrag-opensearch
    ports:
      - "9200:9200"
      - "9600:9600"

  openrag-dashboards:
    container_name: openrag-dashboards
    networks:
      - odoo-multi
    ports:
      - "5601:5601"
    depends_on:
      - openrag-opensearch

networks:
  odoo-multi:
    external: true
    name: docker-multi_odoo-multi
```

> **Nota**: Usamos `external: true` para conectar a la red existente `docker-multi_odoo-multi`, lo que permite a los contenedores OpenRAG comunicarse con los contenedores Odoo y viceversa.

Crear también `docker-compose.yml` como archivo principal que define los servicios base:

```yaml
version: '3.8'

services:
  openrag-backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    image: openrag-backend:latest
    container_name: openrag-backend
    env_file: .env
    environment:
      - OPENSEARCH_HOST=openrag-opensearch
      - LANGFLOW_URL=http://openrag-langflow:7860
    volumes:
      - ./openrag-data:/app/data
      - ./keys:/app/keys
      - ./openrag-documents:/app/documents
    restart: unless-stopped

  openrag-frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    image: openrag-frontend:latest
    container_name: openrag-frontend
    ports:
      - "3000:3000"
    env_file: .env
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - openrag-backend
    restart: unless-stopped

  openrag-langflow:
    build:
      context: .
      dockerfile: Dockerfile.langflow
    image: openrag-langflow:latest
    container_name: openrag-langflow
    env_file: .env
    volumes:
      - ./langflow-data:/app/langflow-data
    restart: unless-stopped

  openrag-opensearch:
    image: opensearchproject/opensearch:2.19.0
    container_name: openrag-opensearch
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=${OPENSEARCH_PASSWORD}
      - OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - opensearch-data:/usr/share/opensearch/data
    restart: unless-stopped

  openrag-dashboards:
    image: opensearchproject/opensearch-dashboards:2.19.0
    container_name: openrag-dashboards
    environment:
      - OPENSEARCH_HOSTS=http://openrag-opensearch:9200
      - DISABLE_SECURITY_DASHBOARDS_PLUGIN=true
    depends_on:
      - openrag-opensearch
    restart: unless-stopped

volumes:
  opensearch-data:
    driver: local
```

> ⚠️ **Importante**: Los `Dockerfile.backend`, `Dockerfile.frontend` y `Dockerfile.langflow` ya existen en el repositorio clonado de OpenRAG. No hay que crearlos.

**Tiempo estimado**: 15 min

---

### Fase 3: Instalar uv y Docling Serve en el Host

```bash
# 3.1 Instalar uv (si no existe)
pip install uv

# 3.2 Verificar
uv --version

# 3.3 Iniciar Docling Serve
cd /home/binlp011/sources/docker-multi/openrag
uv run python scripts/docling_ctl.py start --port 5001

# 3.4 Verificar
curl http://localhost:5001/docs
# Debe responder con Swagger UI
```

> **Importante**: Docling Serve debe iniciarse **antes** que los contenedores Docker de OpenRAG, ya que el backend de OpenRAG necesita conectarse a él durante la ingestión de documentos.

**Tiempo estimado**: 10 min

---

### Fase 4: Desplegar Contenedores OpenRAG

```bash
# 4.1 Construir imágenes (solo primera vez)
cd /home/binlp011/sources/docker-multi/openrag
docker compose build

# 4.2 Iniciar servicios
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

# 4.3 Verificar estado
docker compose ps

# 4.4 Verificar logs (si hay errores)
docker compose logs --tail=50 openrag-backend
docker compose logs --tail=50 openrag-frontend
```

**Verificación de servicios**:

```bash
# Backend
curl http://localhost:8000/health

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000

# Langflow
curl -s -o /dev/null -w "%{http_code}" http://localhost:7860

# OpenSearch
curl -s http://localhost:9200 | python3 -m json.tool

# OpenSearch Dashboards
curl -s -o /dev/null -w "%{http_code}" http://localhost:5601

# Docling Serve
curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/docs
```

**Tiempo estimado**: 15 min (build) + 5 min (deploy)

---

### Fase 5: Onboarding Inicial de OpenRAG

Una vez los servicios estén funcionando:

1. Abrir `http://localhost:3000` en el navegador
2. Completar el onboarding:
   - Seleccionar proveedor de modelo LLM (OpenAI/Anthropic/Ollama)
   - Ingresar API key o usar variable de entorno
   - Seleccionar modelo de embeddings
3. Esperar a que ingeste los documentos iniciales
4. Crear una API key en **Settings → API Keys**
5. Guardar la API key (prefijo `orag_...`)

**Verificación post-onboarding**:

```bash
# Probar chat via API
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: orag_tu_api_key" \
  -d '{"message": "Hello, what documents are available?"}'

# Probar búsqueda semántica
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: orag_tu_api_key" \
  -d '{"query": "RAG document processing", "limit": 5}'
```

**Tiempo estimado**: 10 min

---

### Fase 6: Integración con OpenCode (MCP)

#### 6.1 Configurar servidor MCP en opencode

Editar `~/.config/opencode/opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode-go/qwen3.7-plus",
  "mcp": {
    // ... servidores existentes (codebase-memory-mcp, postgres-db) ...
    "openrag": {
      "enabled": true,
      "type": "http",
      "url": "http://localhost:3000/mcp",
      "headers": {
        "X-API-Key": "orag_tu_api_key_generada"
      }
    }
  }
  // ... resto de la configuración ...
}
```

> ⚠️ **Nota sobre el driver HTTP MCP**: opencode actualmente configura MCP servers con `type: "local"` + `command`. Para el caso de OpenRAG que es un servidor MCP **streamable HTTP**, se necesita verificar qué formato acepta opencode. Si no soporta `type: "http"` directamente, se puede usar un wrapper local:

```jsonc
"openrag": {
  "enabled": true,
  "type": "local",
  "command": [
    "python3",
    "-c",
    "import sys, json, httpx; ...
     # Proxy local que wrappea HTTP MCP a stdio MCP
     # (si opencode requiere stdio)"
  ]
}
```

O mejor aún, crear un **script wrapper**:

**`/home/binlp011/sources/docker-multi/scripts/mcp_servers/openrag_mcp_wrapper.py`**:

```python
#!/usr/bin/env python3
"""
OpenRAG MCP Wrapper para OpenCode.
Conecta opencode (que usa stdio MCP) con OpenRAG (que expone streamable HTTP MCP).
"""
import sys
import json
import httpx
import asyncio

OPENRAG_URL = "http://localhost:3000/mcp"
API_KEY = "orag_tu_api_key_aqui"  # O leer de variable de entorno

async def main():
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(base_url=OPENRAG_URL, headers=headers) as client:
        # Inicializar: enviar initialize request
        init_msg = json.loads(sys.stdin.readline())
        # Reenviar a OpenRAG MCP endpoint
        async with client.stream("POST", "/", json=init_msg) as resp:
            async for line in resp.aiter_lines():
                if line:
                    print(line, flush=True)
        
        # Loop principal de mensajes
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            msg = json.loads(line)
            async with client.stream("POST", "/", json=msg) as resp:
                async for chunk in resp.aiter_lines():
                    if chunk:
                        print(chunk, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
```

#### 6.2 Verificar conexión MCP

Una vez configurado, reiniciar opencode. Aparecerán herramientas como:
- `openrag_chat`
- `openrag_search`
- `openrag_ingest`
- `openrag_get_settings`
- etc.

**Tiempo estimado**: 10 min

---

### Fase 7: Crear Skills de OpenRAG para OpenCode

Crear skills específicos para que opencode pueda usar OpenRAG como knowledge base del proyecto.

#### Skill 1: `openrag-knowledge-odoo`

**`/home/binlp011/sources/docker-multi/src/.opencode/skills/openrag-knowledge-odoo/SKILL.md`**:

```markdown
---
name: openrag-knowledge-odoo
description: Usa OpenRAG como knowledge base de Odoo para búsqueda semántica de documentación, skills y código. Se activa al preguntar sobre documentación Odoo, migración 17→19, o codebase Odoo.
---

# OpenRAG Knowledge para Odoo

OpenRAG está desplegado en http://localhost:3000 y sirve como knowledge base
con capacidad RAG para todo el proyecto docker-multi.

## Documentación indexada

- Odoo 19 docs (654 archivos .md en `.opencode/docs/`)
- Todos los skills del proyecto (164 skills)
- Guías de migración 17→19
- Estándares OCA y guías de code review

## Uso con OpenCode

Cuando necesites consultar documentación:

1. Usa las herramientas MCP de OpenRAG directamente:
   - `openrag_search(query, limit=5)` — búsqueda semántica
   - `openrag_chat(message)` — chat con contexto RAG

2. Ejemplo:
   ```python
   await openrag_search("migration 17 to 19 ORM changes")
   ```

Para ingestar más documentos, usa `openrag_ingest` con rutas del proyecto.
```

#### Skill 2: `openrag-ingest-docs`

```markdown
---
name: openrag-ingest-docs
description: Ingestiona documentación Odoo y skills del proyecto en OpenRAG para búsqueda RAG. Se activa al solicitar indexar documentación.
---

# Ingesta de Documentación en OpenRAG

## Documentación de Odoo 19

```bash
# Ingestar docs de Odoo 19 (indexación masiva)
for doc in /home/binlp011/sources/docker-multi/src/.opencode/docs/*.md; do
  curl -X POST http://localhost:3000/api/ingest \
    -H "X-API-Key: $OPENRAG_API_KEY" \
    -F "file=@$doc"
done
```

## Skills del proyecto

```bash
# Ingestar skills de 19.0
find /home/binlp011/sources/docker-multi/src/.opencode/skills -name "*.md" \
  -exec curl -X POST http://localhost:3000/api/ingest \
    -H "X-API-Key: $OPENRAG_API_KEY" \
    -F "file=@{}" \;
```

## Verificación

```bash
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OPENRAG_API_KEY" \
  -d '{"query": "Odoo ORM search_fetch", "limit": 3}'
```
```

**Tiempo estimado**: 15 min

---

### Fase 8: Scripts de Gestión

Crear scripts para facilitar el manejo diario de OpenRAG.

#### `openrag/scripts/manage.sh`

```bash
#!/bin/bash
# Gestión de OpenRAG en docker-multi
# Uso: ./scripts/manage.sh {start|stop|restart|status|logs|build|docling}

OPENRAG_DIR="/home/binlp011/sources/docker-multi/openrag"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.override.yml"

case "${1:-status}" in
  start)
    echo "▶️  Iniciando Docling Serve..."
    cd "$OPENRAG_DIR" && uv run python scripts/docling_ctl.py start --port 5001
    echo "▶️  Iniciando contenedores OpenRAG..."
    cd "$OPENRAG_DIR" && docker compose $COMPOSE_FILES up -d
    echo "✅ Servicios iniciados. Frontend: http://localhost:3000"
    ;;
  stop)
    echo "⏹️  Deteniendo contenedores OpenRAG..."
    cd "$OPENRAG_DIR" && docker compose $COMPOSE_FILES down
    echo "⏹️  Deteniendo Docling Serve..."
    cd "$OPENRAG_DIR" && uv run python scripts/docling_ctl.py stop
    echo "✅ Servicios detenidos."
    ;;
  restart)
    $0 stop && $0 start
    ;;
  status)
    echo "=== Contenedores OpenRAG ==="
    cd "$OPENRAG_DIR" && docker compose $COMPOSE_FILES ps
    echo ""
    echo "=== Docling Serve ==="
    curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:5001/docs
    echo ""
    echo "=== Puertos ==="
    ss -tlnp | grep -E ':(3000|5001|5601|7860|8000|9200)\b'
    ;;
  logs)
    shift
    cd "$OPENRAG_DIR" && docker compose $COMPOSE_FILES logs "$@"
    ;;
  build)
    cd "$OPENRAG_DIR" && docker compose $COMPOSE_FILES build
    ;;
  docling)
    shift
    cd "$OPENRAG_DIR" && uv run python scripts/docling_ctl.py "$@"
    ;;
  ingest)
    echo "📄 Ingestando documentación Odoo..."
    # Usar API de OpenRAG para ingestar docs
    for doc in /home/binlp011/sources/docker-multi/src/.opencode/docs/*.md; do
      curl -X POST http://localhost:3000/api/ingest \
        -H "X-API-Key: ${OPENRAG_API_KEY}" \
        -F "file=@$doc" 2>/dev/null
    done
    echo "✅ Documentación ingestada."
    ;;
  *)
    echo "Uso: $0 {start|stop|restart|status|logs|build|docling|ingest}"
    exit 1
    ;;
esac
```

```bash
chmod +x /home/binlp011/sources/docker-multi/openrag/scripts/manage.sh
```

**Tiempo estimado**: 10 min

---

## Mapa de Puertos y Servicios

| Puerto | Servicio          | URL                           | Propósito                    |
| ------ | ----------------- | ----------------------------- | ---------------------------- |
| 3000   | OpenRAG Frontend  | http://localhost:3000          | UI principal + MCP endpoint  |
| 8000   | OpenRAG Backend   | http://localhost:8000          | API REST + FastAPI docs      |
| 7860   | Langflow          | http://localhost:7860          | Visual workflow builder RAG  |
| 9200   | OpenSearch        | http://localhost:9200          | Vector DB + Knowledge base   |
| 5601   | OpenSearch Dashboards | http://localhost:5601      | Admin de índices             |
| 5001   | Docling Serve     | http://localhost:5001/docs     | Parsing de documentos        |
| 5432   | PostgreSQL (Odoo) | localhost:5432                 | Base de datos Odoo existente |
| 5433   | PostgreSQL (Odoo 17) | localhost:5433             | BD Odoo 17                   |
| 8070-8076 | Odoo instances | localhost:8070-8076            | Instancias Odoo existentes   |

---

## Requisitos del Sistema

### Mínimos (OpenRAG)
- 8 GB RAM
- 4 CPU cores
- 20 GB disco libre
- Docker + Compose
- Python 3.13

### Actual (docker-multi)
| Recurso       | Mínimo | Actual | Estado |
| ------------- | ------ | ------ | ------ |
| RAM           | 8 GB   | 15 GB  | ✅     |
| CPU           | 4      | 20     | ✅     |
| Disco         | 20 GB  | 33 GB  | ✅     |
| Python 3.13   | ✅     | 3.13.5 | ✅     |
| Docker        | ✅     | 29.5.2 | ✅     |
| Docker Compose| ✅     | 5.1.4  | ✅     |

---

## Diagrama de Red

```
docker-multi_odoo-multi bridge (172.18.0.0/16)
│
├── odoo-qa-consultoria-19 (.2)
├── odoo-josehern19.0 (.3)
├── odoo-josehern19.0-tests (.4)
├── odoo-qa-consultoria-19-tests (.5)
├── odoo-odoo-17.0-tests (.6)
├── odoo-qa-mant-tri2-v19 (.7)
├── odoo-qa-mant-tri2-v19-tests (.8)
├── db-pg16 (.9)
├── db-odoo-17-pg16 (.10)
├── odoo-nginx (.11)
│
├── openrag-backend (.12)      ← NUEVO
├── openrag-frontend (.13)     ← NUEVO
├── openrag-langflow (.14)     ← NUEVO
├── openrag-opensearch (.15)   ← NUEVO
└── openrag-dashboards (.16)   ← NUEVO
```

---

## Cronograma Estimado

| Fase | Actividad                  | Tiempo |
| ---- | -------------------------- | ------ |
| 0    | Prerequisitos (uv, dir)    | 5 min  |
| 1    | Clonar y configurar .env   | 10 min |
| 2    | Docker Compose + Override  | 15 min |
| 3    | Docling Serve en host      | 10 min |
| 4    | Deploy contenedores        | 20 min |
| 5    | Onboarding + API Key       | 10 min |
| 6    | Integración MCP con opencode | 10 min |
| 7    | Skills para opencode       | 15 min |
| 8    | Scripts de gestión         | 10 min |
| **Total** | **Completo**          | **~105 min** |

---

## Próximos Pasos Inmediatos

1. ✅ **Fase 0**: `pip install uv && uv --version`
2. ✅ **Fase 1**: Clonar repo y crear `.env`
3. ✅ **Fase 2**: Crear docker-compose y override
4. ✅ **Fase 3**: Iniciar Docling Serve
5. ✅ **Fase 4**: `docker compose up -d`
6. ✅ **Fase 5**: Onboarding web + API key
7. ✅ **Fase 6**: Configurar MCP en opencode.jsonc
8. ✅ **Fase 7**: Crear skills
9. ✅ **Fase 8**: Script `manage.sh`

---

## Referencias

- OpenRAG GitHub: https://github.com/langflow-ai/openrag
- OpenRAG Docs: https://docs.openr.ag
- OpenRAG MCP: https://github.com/langflow-ai/openrag/tree/main/sdks/mcp
- Configuración: https://docs.openr.ag/reference/configuration
- Docker deploy: https://docs.openr.ag/docker
- OpenCode MCP config: `~/.config/opencode/opencode.jsonc`

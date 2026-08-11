#!/usr/bin/env python3
"""
OpenRAG MCP Server para OpenCode.

Conecta opencode (MCP via stdio) con OpenRAG (API REST + streamable HTTP MCP).
Usa el SDK de OpenRAG (openrag-sdk) para comunicarse con el servidor OpenRAG.

Transporte: stdio (estándar para MCP servers locales en OpenCode).
Requerimientos: pip install openrag-sdk httpx mcp
"""

import os
import json
import asyncio
from typing import Optional, Any
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
OPENRAG_URL = os.environ.get("OPENRAG_URL", "http://localhost:3000")
OPENRAG_API_KEY = os.environ.get("OPENRAG_API_KEY", "")

mcp = FastMCP(
    name="openrag-mcp",
    instructions=(
        "OpenRAG MCP server — Retrieval-Augmented Generation platform. "
        "Search documents, chat with knowledge base, ingest documents, "
        "and manage settings via OpenRAG."
    ),
)

# ---------------------------------------------------------------------------
# Cliente HTTP para OpenRAG API
# ---------------------------------------------------------------------------
import httpx


class OpenRAGClientHTTP:
    """Cliente HTTP directo a OpenRAG REST API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            self.headers["X-API-Key"] = api_key
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def _request(
        self, method: str, path: str, **kwargs
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.request(
                method, url, headers=self.headers, **kwargs
            )
            resp.raise_for_status()
            if resp.status_code == 204:
                return {"success": True}
            return resp.json()

    async def chat(self, message: str, chat_id: Optional[str] = None,
                   filter_id: Optional[str] = None) -> dict[str, Any]:
        body = {"message": message}
        if chat_id:
            body["chat_id"] = chat_id
        if filter_id:
            body["filter_id"] = filter_id
        return await self._request("POST", "/api/chat", json=body)

    async def search(self, query: str, limit: int = 10,
                     score_threshold: Optional[float] = None,
                     filter_id: Optional[str] = None) -> dict[str, Any]:
        body = {"query": query, "limit": limit}
        if score_threshold is not None:
            body["score_threshold"] = score_threshold
        if filter_id:
            body["filter_id"] = filter_id
        return await self._request("POST", "/api/search", json=body)

    async def list_chats(self) -> dict[str, Any]:
        return await self._request("GET", "/api/chats")

    async def get_chat(self, chat_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/chats/{chat_id}")

    async def delete_chat(self, chat_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/chats/{chat_id}")

    async def ingest_file(self, file_path: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/ingest"
        headers = {k: v for k, v in self.headers.items()
                   if k != "Content-Type"}
        async with httpx.AsyncClient(timeout=600.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f,
                                  "application/octet-stream")}
                resp = await client.post(url, headers=headers, files=files)
                resp.raise_for_status()
                return resp.json()

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/tasks/{task_id}")

    async def delete_document(self, filename: str) -> dict[str, Any]:
        return await self._request(
            "DELETE", "/api/documents", json={"filename": filename}
        )

    async def get_settings(self) -> dict[str, Any]:
        return await self._request("GET", "/api/settings")

    async def update_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PUT", "/api/settings", json=settings)

    async def list_models(self, provider: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/models/{provider}")

    async def health(self) -> dict[str, Any]:
        try:
            return await self._request("GET", "/health")
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Instanciar cliente
# ---------------------------------------------------------------------------
client = OpenRAGClientHTTP(OPENRAG_URL, OPENRAG_API_KEY)


# ---------------------------------------------------------------------------
# Herramientas MCP
# ---------------------------------------------------------------------------

@mcp.tool()
async def openrag_health() -> str:
    """Verificar si el servidor OpenRAG está funcionando."""
    result = await client.health()
    if result.get("status") == "ok" or "status" in result:
        return f"✅ OpenRAG saludable: {json.dumps(result, indent=2)}"
    return f"❌ OpenRAG no disponible: {result}"


@mcp.tool()
async def openrag_chat(message: str, chat_id: Optional[str] = None,
                       filter_id: Optional[str] = None) -> str:
    """Enviar un mensaje al chat RAG y obtener respuesta contextual.

    Args:
        message: Mensaje o pregunta a enviar.
        chat_id: ID de conversación existente para continuar (opcional).
        filter_id: ID de filtro de conocimiento para acotar búsqueda (opcional).
    """
    result = await client.chat(message, chat_id, filter_id)
    response = result.get("response", result.get("message", str(result)))
    sources = result.get("sources", [])
    output = response
    if sources:
        output += "\n\n📚 Fuentes:\n"
        for s in sources[:5]:
            filename = s.get("filename", s.get("name", "desconocido"))
            score = s.get("score", "")
            output += f"  • {filename} (score: {score})\n"
    return output


@mcp.tool()
async def openrag_search(query: str, limit: int = 10,
                         score_threshold: Optional[float] = None) -> str:
    """Buscar documentos en la knowledge base de OpenRAG.

    Args:
        query: Consulta de búsqueda semántica.
        limit: Número máximo de resultados (default: 10, max: 50).
        score_threshold: Umbral mínimo de similitud (0.0 a 1.0, opcional).
    """
    limit = min(limit, 50)
    result = await client.search(query, limit, score_threshold)
    results_list = result.get("results", result.get("data", []))
    if not results_list:
        return "📭 No se encontraron resultados."

    output = f"🔍 Resultados para: '{query}'\n\n"
    for i, r in enumerate(results_list[:limit], 1):
        filename = r.get("filename", r.get("name", "doc"))
        score = r.get("score", r.get("similarity", "N/A"))
        text = r.get("text", r.get("content", ""))[:200]
        output += f"{i}. **{filename}** (score: {score})\n"
        output += f"   {text}...\n\n"
    return output


@mcp.tool()
async def openrag_list_chats() -> str:
    """Listar todas las conversaciones de chat."""
    result = await client.list_chats()
    chats = result.get("conversations", result.get("chats", result.get("data", [])))
    if not chats:
        return "📭 No hay conversaciones."
    output = "💬 Conversaciones:\n\n"
    for c in chats:
        chat_id = c.get("chat_id", c.get("id", "?"))
        title = c.get("title", c.get("name", "Sin título"))
        created = c.get("created_at", c.get("created", ""))
        output += f"  • **{title}** (ID: {chat_id}) — {created}\n"
    return output


@mcp.tool()
async def openrag_get_chat(chat_id: str) -> str:
    """Obtener una conversación específica con todos sus mensajes.

    Args:
        chat_id: ID de la conversación.
    """
    result = await client.get_chat(chat_id)
    messages = result.get("messages", [])
    if not messages:
        return f"📭 Conversación {chat_id} no encontrada o vacía."

    output = f"💬 Conversación: {chat_id}\n\n"
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", msg.get("message", ""))[:300]
        output += f"**{role}**: {content}\n\n"
    return output


@mcp.tool()
async def openrag_delete_chat(chat_id: str) -> str:
    """Eliminar una conversación de chat.

    Args:
        chat_id: ID de la conversación a eliminar.
    """
    await client.delete_chat(chat_id)
    return f"🗑️ Conversación {chat_id} eliminada."


@mcp.tool()
async def openrag_ingest(file_path: str) -> str:
    """Ingestar un documento en la knowledge base de OpenRAG.

    Args:
        file_path: Ruta absoluta al archivo a ingestar (PDF, DOCX, TXT, etc.).
    """
    if not os.path.exists(file_path):
        return f"❌ Archivo no encontrado: {file_path}"
    if not os.path.isfile(file_path):
        return f"❌ No es un archivo: {file_path}"

    result = await client.ingest_file(file_path)
    task_id = result.get("task_id", result.get("id", ""))
    status = result.get("status", "processing")
    return (
        f"📄 Documento '{os.path.basename(file_path)}' enviado para ingestión.\n"
        f"  Task ID: {task_id}\n"
        f"  Estado: {status}\n"
        f"  Usa openrag_get_task_status('{task_id}') para ver progreso."
    )


@mcp.tool()
async def openrag_get_task_status(task_id: str) -> str:
    """Verificar el estado de una tarea de ingestión.

    Args:
        task_id: ID de la tarea de ingestión.
    """
    result = await client.get_task_status(task_id)
    status = result.get("status", "unknown")
    progress = result.get("progress", result.get("percentage", ""))
    files = result.get("successful_files", result.get("files", []))
    errors = result.get("errors", result.get("failed_files", []))

    output = f"📋 Tarea: {task_id}\n  Estado: {status}"
    if progress:
        output += f" ({progress})"
    output += "\n"
    if files:
        output += f"  ✅ Archivos procesados: {len(files)}\n"
    if errors:
        output += f"  ❌ Errores: {len(errors)}\n"
        for e in errors[:5]:
            output += f"     • {e}\n"
    return output


@mcp.tool()
async def openrag_delete_document(filename: str) -> str:
    """Eliminar un documento de la knowledge base.

    Args:
        filename: Nombre del archivo a eliminar.
    """
    await client.delete_document(filename)
    return f"🗑️ Documento '{filename}' eliminado."


@mcp.tool()
async def openrag_get_settings() -> str:
    """Obtener la configuración actual de OpenRAG."""
    result = await client.get_settings()
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def openrag_list_models(provider: str = "openai") -> str:
    """Listar modelos disponibles para un proveedor.

    Args:
        provider: Proveedor de modelos (openai, anthropic, ollama, watsonx).
    """
    result = await client.list_models(provider)
    models = result.get("models", result.get("data", []))
    if not models:
        return f"📭 No se encontraron modelos para {provider}."

    output = f"🤖 Modelos disponibles ({provider}):\n\n"
    for m in models:
        name = m.get("id", m.get("name", str(m)))
        output += f"  • {name}\n"
    return output


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    mcp.run()


if __name__ == "__main__":
    main()

# AI_LOG — shop_integration_api (Ejercicio 1)

## Herramientas
- Claude Code (app de escritorio), modelo Claude Opus 5.5.

## Prompts clave
1. «Arranca el ejercicio 1-A (shop_integration_api) en una rama nueva.»
   - Antes de programar, revisó en el código de Odoo 18 que `free_qty` se puede buscar (sirve para el filtro
     de stock en el dominio) y cómo responde JSON un controlador (`make_json_response`). Usó desde el tramo A
     el formato de error que pide el tramo B, para no cambiar el contrato con la tienda más adelante.
2. Pruebas `HttpCase` de cada filtro solo y combinados, más fechas inválidas, permisos y método HTTP.
3. Prueba en vivo con `curl` del flujo que hará la tienda: login, consulta y errores.

## Lo que la IA hizo mal
- **Usuario de prueba sin permisos de inventario:** las pruebas usaban un usuario interno básico y 8 de 13
  fallaron con `AccessError` sobre `stock.move` al calcular el stock. Se descartó `sudo()`: el usuario de la
  integración debe tener *Inventario › Usuario*, lo que quedó documentado para la tienda. Además, la API
  responde un 403 claro y hay una prueba de ese caso.
- **Asumió que `datetime.fromisoformat` acepta el sufijo `Z`**, pero eso llegó en Python 3.11 y el
  contenedor usa una versión anterior. Una prueba con `...Z` dio 400. Se convierte `Z` a `+00:00` a mano y se
  agregó un caso con zona `-04:00`.
- En la documentación, la llamada sin sesión parecía redirigir siempre al login. La prueba en vivo con
  `curl` mostró un 404 cuando hay varias bases sin `dbfilter`; quedó documentado.

## Lo que escribiste tú sin IA
- (Completar por Candido: qué partes decidiste o escribiste por tu cuenta y por qué.)

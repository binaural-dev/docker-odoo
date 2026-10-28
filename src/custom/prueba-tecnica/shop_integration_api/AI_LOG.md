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
4. «Sigue con el 1-B: API keys, POST /api/v1/orders y log de llamadas.»
   - Revisó en Odoo 18 `auth='bearer'` y `res.users.apikeys._check_credentials`. Descartó el `auth='bearer'`
     nativo porque acepta también la sesión del navegador y responde con su propio formato de error. Propuso
     un único punto de entrada que autentica, ejecuta en un savepoint y registra la llamada.

5. «Sigue con el 1-C: paginación, Idempotency-Key, stock eficiente, webhook y openapi.yaml.»
   - Movió la consulta paginada a un método del modelo, para que la prueba de cantidad de consultas mida lo
     mismo que ejecuta el endpoint: 17 consultas con 5 y con 60 productos.
   - Para el webhook propuso una cola: validar la entrega solo encola, y una acción planificada envía con
     tiempo de espera y reintentos. Así quien valida nunca depende de la tienda.

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

- **Tramo B: rutas ejecutadas dos veces sin que las pruebas fallaran.** Las 33 pruebas pasaron, pero el
  registro mostraba «cannot execute INSERT in a read-only transaction, retrying with a read/write cursor».
  Odoo 18 abre los `GET` con un cursor de solo lectura y, al escribir el log, repetía la petición entera. En
  el `POST`, además, la captura genérica de errores convertía ese primer intento en un «Error inesperado».
  Se detectó leyendo el registro de las pruebas, no por un fallo. Se corrigió con `readonly=False` y se agregó
  `test_each_call_runs_once`, que falla si vuelve a aparecer el reintento o un error de SQL.

- **Tramo C, formato de fecha del webhook:** el primer borrador enviaba `occurred_at` como
  `2026-10-28 15:04:05Z` (con un espacio), que no es ISO 8601 estricto, aunque `openapi.yaml` lo documentaba
  como fecha y hora. Se detectó al releer la especificación contra el código, se corrigió y se agregó una
  aserción en la prueba.
- Usó `werkzeug.urls.url_encode`, que no existe en las versiones nuevas de Werkzeug. Se cambió por
  `urllib.parse.urlencode` antes de correr las pruebas.
- Propuso validar `openapi.yaml` con `openapi-spec-validator`, pero no está instalado y no se descargó nada sin
  consultarlo. Quedó validado como YAML y revisado a mano, y así se dice en el README.

## Lo que escribiste tú sin IA
- (Completar por Candido: qué partes decidiste o escribiste por tu cuenta y por qué.)

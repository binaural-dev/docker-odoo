---
name: binaural-pdf-report
description: Genera documentos/informes en PDF con la imagen corporativa de Binaural (logo, colores y tipografia segun el manual de marca) y los guarda en ~/Documents/documentation/. Usar cuando el usuario pida "genera esto en PDF", "informe en PDF con la marca/imagen corporativa", "documentacion para el consultor/cliente en PDF", "PDF de Binaural", o pida documentar en PDF un ajuste/modulo/decision ya discutido en la conversacion.
---

# Generar documentacion en PDF con marca Binaural

Genera un PDF con el estilo corporativo de Binaural (colores aprobados, logo oficial, tipografia) a partir de
cualquier contenido que el usuario quiera documentar (un ajuste de codigo, una decision, un modulo, una guia de
validacion, etc.), y lo guarda en `~/Documents/documentation/`.

## Regla dura: todo local, nada sale de la empresa

Este skill **nunca** sube el documento a un servicio externo (no usar la herramienta Artifact, no usar
conversores de PDF online, no llamar APIs externas). Todo el proceso corre con herramientas locales
(Bash/Chrome headless) y el archivo final queda unicamente en el filesystem del usuario.

## Trigger

Cargar este skill cuando el usuario pida generar un documento/informe **en PDF** con la marca/imagen corporativa,
o pida "documentar esto" despues de haber discutido algo puntual en la conversacion (un fix, un ajuste, una
decision tecnica) y quiera un entregable para compartir con un consultor, cliente o el equipo.

Si el usuario no especifica de que quiere el documento, usar como contenido lo ultimo relevante discutido en la
conversacion (ej. un ajuste de codigo recien hecho, un analisis recien completado). Si no hay contexto claro,
preguntar brevemente: "¿sobre que quieres el informe?".

## Assets de marca (ya incluidos en este skill, no volver a extraer del PDF de estandares)

Este skill trae los logos oficiales ya extraidos (con transparencia real) del PDF "Estandares de marca _
Binaural.pdf", listos para usar sin depender de ese archivo:

- `assets/logo_color.png` — logo principal (isotipo + wordmark en azul oscuro). Usar sobre fondos **claros**.
- `assets/logo_white.png` — variante en blanco. Usar sobre fondos **oscuros/azules** (encabezados con degradado,
  pie de pagina).
- `assets/isotipo_color.png` — solo el isotipo (sin el texto "binaural"), por si se necesita un icono suelto.

**Reglas de uso del logo (del manual de marca, respetarlas siempre):**
- No cambiar su orientacion, ni estirarlo, ni cortarlo, ni subrayarlo.
- No cambiar sus colores ni usar el texto sin el isotipo.
- Debe haber contraste segun el fondo: logo principal (oscuro) sobre fondo claro, variante blanca sobre fondo
  azul/oscuro.
- El logo se usa como: encabezado superior, esquina tipo membrete, o al final tipo firma (footer). La plantilla
  de este skill ya lo hace asi (blanco en el header con degradado, blanco tambien en el footer oscuro).

**Colores aprobados** (usar tal cual, no inventar variaciones):
- `#0f4c94` azul primario
- `#018ecd` azul cian (acentos, bordes de titulo, flechas)
- `#1e2a50` azul oscuro (texto de titulos, fondos de header de tabla, footer)
- `#f6b03b` naranja — **solo para resaltar** (callouts de "importante"/"conclusion"), nunca como color base

**Tipografia:** Titulos con pila que priorice `Open Sans`, texto con `Helvetica`. Ya esta resuelto en el CSS de
la plantilla (`template.html`), no hace falta tocarlo.

## Plantilla

Este skill trae `template.html`, un documento HTML autocontenido (CSS embebido, sin dependencias externas ni
CDNs) con placeholders a reemplazar:

| Placeholder | Que va ahi |
|---|---|
| `{{TITLE}}` | Titulo del informe (aparece en `<title>` y en el encabezado) |
| `{{SUBTITLE}}` | Una linea describiendo el documento/audiencia (ej. "Guia de validacion funcional para el consultor. Modulo X.") |
| `{{META_CHIPS}}` | HTML de los chips redondeados del encabezado, ej. `<span class="meta-chip">Modulo: xxx</span>` repetido (modulo, archivo, fecha, solicitado por, etc. — los que apliquen) |
| `{{BODY}}` | El contenido real: una serie de `<section><h2><span class="num">N.</span>Titulo</h2> ... </section>`, usando los estilos ya definidos: tablas, `<div class="callout">`, `<div class="example-box">` para ejemplos numericos, `<ol class="steps">` para guias paso a paso, `<span class="badge-ok">`/`<span class="badge-warn">` para resultados, `<span class="mono">` para formulas/codigo corto |
| `{{LOGO_WHITE_B64}}` | Base64 de `assets/logo_white.png` |
| `{{LOGO_COLOR_B64}}` | Base64 de `assets/logo_color.png` (el footer lo muestra invertido a blanco via CSS `filter`, asi que este placeholder puede llevar el logo color igual) |
| `{{FOOTER_NOTE}}` | Nota de confidencialidad, por defecto: "Documento interno — uso exclusivo Binaural. No distribuir fuera de la organizacion." (ajustar si el documento es para compartir con un cliente externo, en cuyo caso quitar "uso exclusivo Binaural") |

No reinventar el CSS ni la estructura del `<header>`/`<footer>` — ya estan resueltos y validados visualmente.
Solo se completa `{{BODY}}` con las secciones especificas de cada documento (numeradas, ej. 1. Resumen ejecutivo,
2. Contexto, 3. Condiciones, etc. — adaptar la cantidad y nombres de secciones al contenido real, no hay que
usar siempre las mismas).

## Proceso

1. **Reunir el contenido.** Si el documento es sobre algo ya discutido en la conversacion (un ajuste de codigo,
   una investigacion), redactar el contenido en lenguaje claro para la audiencia indicada (funcional/no-tecnico
   por defecto, salvo que el usuario pida un informe tecnico). Si falta informacion (ej. no se sabe el modulo o
   archivo afectado), revisar el codigo/conversacion antes de inventar datos.

2. **Armar el HTML.** Leer `template.html` (ruta: `<directorio base de este skill>/template.html`), reemplazar
   los placeholders por el contenido real, y escribir el resultado a un archivo temporal (ej. en el directorio de
   scratchpad de la sesion).
   - Para los placeholders de logo, obtener el base64 con Bash: `base64 -i <directorio base>/assets/logo_white.png`
     (en macOS `base64` no necesita `-w 0`; si el comando disponible es GNU base64, usar `-w 0` para que no
     inserte saltos de linea).

3. **Convertir a PDF con Chrome headless** (sin instalar nada nuevo, ya viene instalado en el sistema):
   ```
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --headless=new --disable-gpu --no-sandbox \
     --print-to-pdf="<ruta-salida>.pdf" \
     --no-pdf-header-footer --print-to-pdf-no-header \
     "file://<ruta-absoluta-del-html-temporal>"
   ```

4. **Guardar en el destino final.** Crear `~/Documents/documentation/` si no existe (`mkdir -p`). El nombre de
   archivo es el titulo del documento en minusculas-con-guiones (slug), ej.
   `informe-recalculo-tasa-manual.pdf`. Si ya existe un archivo con ese nombre y el usuario esta actualizando el
   mismo documento, sobreescribirlo (no acumular versiones con sufijos salvo que el usuario pida conservar
   historico).

5. **Ajustar el pie de pagina con una segunda pasada (obligatorio si el documento tiene mas de 1 pagina).**
   La plantilla deja un comentario `<!-- {{FOOTER_SPACER}} -->` justo antes del `<footer>` en vez de intentar
   adivinar su posicion con CSS o JS (ver "Paginacion y pie de pagina" mas abajo, explica por que). Con
   PyMuPDF (`pip3 install --quiet pymupdf` si hace falta):
   ```python
   import fitz
   doc = fitz.open("<ruta-salida>.pdf")
   last = doc[len(doc) - 1]
   blocks = [b for b in last.get_text("blocks") if b[4].strip()]
   footer_bottom_pt = max(b[3] for b in blocks if "Documento interno" in b[4] or "organiza" in b[4])
   target_bottom_pt = last.rect.height - 56 * 0.75   # 56px = margin-bottom del @page, en puntos (0.75 = 72/96)
   gap_px = (target_bottom_pt - footer_bottom_pt) / 0.75
   spacer_px = gap_px - 26 - 60   # 26px = padding-bottom del footer; 60px de colchon de seguridad, ver nota abajo
   ```
   Si `spacer_px` es mayor a ~15px, reemplazar el comentario `<!-- {{FOOTER_SPACER}} -->` del HTML por
   `<div style="height: {spacer_px}px"></div>` y volver a correr el paso 3.

   **Por que resta 26 Y ADEMAS 60 de colchon, no solo el padding:** el texto del footer no es el borde de su caja
   (hay que descontar `padding-bottom: 26px` para llegar al borde real de la caja), pero incluso corrigiendo eso
   la medicion sigue sin coincidir exactamente con el limite real de la pagina — se probo empiricamente y un
   spacer "matematicamente exacto" (gap menos el padding, nada mas) seguia haciendo que el footer completo
   saltara a una pagina nueva en blanco (tiene `break-inside: avoid`, asi que basta pasarse por 1px para perder
   la pagina entera). El colchon de 60px deja el resultado visualmente "al final" sin arriesgarse a ese salto. Si
   tras esto el hueco se ve mas grande de lo ideal, es preferible eso a una pagina 4 en blanco — no perseguir el
   "flush" perfecto a costa de arriesgar el salto.

6. **Verificar visualmente antes de darlo por bueno.** Renderizar el PDF resultante a imagenes (mismo `fitz`,
   `doc[i].get_pixmap(dpi=110).save(...)`) y revisar con la herramienta Read al menos la primera pagina
   (encabezado/logo), una pagina intermedia si hay mas de 2 (margenes, tablas no cortadas) y la ultima (footer
   flush contra el borde inferior, sin hueco grande debajo ni cortado a la mitad). Si algo se ve mal, ajustar el
   HTML y repetir desde el paso 3.

7. **Confirmar al usuario** la ruta final del PDF (`~/Documents/documentation/<slug>.pdf`), y un resumen de 1-2
   lineas de que documento se genero.

## Notas

- El HTML intermedio no hace falta conservarlo salvo que el usuario pida tambien la version HTML/editable — en
  ese caso, guardarlo junto al PDF en la misma carpeta con el mismo nombre base.
- Reutilizar siempre `template.html` y los assets de este skill — no volver a extraer el logo del PDF de
  estandares de marca en cada ejecucion, ya quedaron guardados aqui una sola vez.
- Si el manual de marca cambia en el futuro (nuevo logo, nuevos colores), actualizar los archivos en
  `assets/` y las variables CSS en `template.html`, no crear un skill nuevo.

## Paginacion y pie de pagina (por que esta la plantilla como esta)

`template.html` ya resuelve dos problemas no obvios de imprimir HTML largo a PDF con Chrome headless. Si se toca
el CSS de `@page`/`.page` o el paso 5 del proceso, tener en cuenta esto para no reintroducir los bugs:

- **Margenes por pagina.** `@page { size: 1050px 1350px; margin: 56px 60px; }` define una pagina mas ancha que
  el contenido (`.page` tiene `max-width: 880px`) para que las tablas anchas nunca se corten en el borde derecho,
  y un margen uniforme en las 4 esquinas de **todas** las paginas (no solo la primera) para que el contenido de
  las paginas de continuacion no quede pegado al borde superior. Esto se verifico directamente contra el PDF de
  salida con PyMuPDF (`page.rect`, posicion de los bloques de texto) y coincide con lo declarado en el CSS.

- **El pie de pagina siempre al final de la pagina en la que cae, nunca cortado ni flotando con hueco debajo.**
  Chrome no tiene forma nativa (sin JS) de saber cuanto contenido cabe por pagina impresa, asi que hace falta
  empujar el `<footer>` con un espaciador cuyo alto exacto solo se puede conocer viendo donde termino cayendo en
  el PDF real — de ahi el paso 5 (medir con `fitz` y, si hace falta, regenerar una vez mas).

  **Por que no es un `<script>` que calcula esto en el propio HTML** (asi empezo la primera version de esta
  plantilla, y fallo): cualquier script inyectado mide el layout en el momento en que la pagina carga, bajo
  **screen media** — el `window.onload` se dispara antes de que Chrome pase a su modo de impresion/paginado, que
  es donde realmente se decide donde cae cada salto de pagina. Con contenido corto la diferencia no se nota, pero
  en cuanto hay tablas o cajas con `break-inside: avoid` que fuerzan un salto de pagina antes de llenarlo del
  todo, la pagina 1 y 2 dejan de tener el mismo alto de contenido "util" que asume una formula uniforme
  (`alto de pagina / numero de paginas`), y el calculo se desvia lo suficiente (decenas de px) para que el
  footer entero salte a una pagina nueva en blanco (tiene `break-inside: avoid`, asi que no se puede partir a la
  mitad: o entra completo o se va entero a la siguiente). Se intento corregir con un factor de seguridad (`EPS`)
  para no caer justo en el limite, y aun asi seguia fallando con contenido real — la unica medicion confiable es
  la del PDF ya generado, no una prediccion. Por eso el mecanismo actual son dos pasadas reales de Chrome en vez
  de una sola con JS.

  Si en el futuro hace falta automatizar esto sin intervencion manual, hacerlo como un loop en Python/Bash que
  repite el paso 3 + la medicion de fitz hasta que `gap_px` sea chico (< 15px) o se llegue a 2-3 intentos — nunca
  volver a intentarlo con JS dentro del HTML.

---
name: reporte-horas-ia
description: Genera reportes de horas con estimacion de productividad con/sin IA a partir de una hoja de horas PDF y los commits en repositorios custom. Analiza tickets TI/TA, cruza con git log para verificar autoria, y produce un HTML con columnas: Nro TI/TA, Titulo, Descripcion, Con IA, Mayor impacto sin IA, Sin IA. Usar cuando el usuario pida generar informe de horas, reporte de horas, o analizar hoja de horas con commits.
---

# reporte-horas-ia

Genera un reporte HTML de horas trabajadas con estimacion de productividad con y sin asistencia de IA, a partir de:
1. Una hoja de horas en PDF (extraida con `pdftotext -layout`)
2. Commits en los repositorios `src/custom/*/` y sus submodulos

La plantilla HTML se encuentra en `.claude/agents/reporte-horas-ia/template.html` dentro del repositorio docker-odoo.

## Flujo de trabajo

### Paso 1: Extraer la hoja de horas

Ejecutar con la tool Bash:
```bash
pdftotext -layout "ruta/al/archivo.pdf" -
```

Del texto extraido, identificar:
- **Periodo**: extraer del nombre del archivo o del contenido (ej: "15 al 30 de junio de 2026")
- **Empleado**: extraer del contenido
- **Actividades**: cada fila con fecha, tarea, descripcion y tiempo

### Paso 2: Identificar tickets TI/TA

Buscar todos los numeros de ticket/tarea mencionados en la hoja con regex:

```
(?:TI|TA)[_\s#-]*(\d{4,6})
```

Extraer tambien las horas asociadas a cada ticket y la descripcion de la hoja.

### Paso 3: Buscar commits en repositorios

Para cada ticket encontrado, buscar commits en TODOS los repositorios bajo `src/custom/` Y sus submodulos.

**Repositorios custom** (buscar con Bash):
```bash
for repo in src/custom/*/; do
  if [ -d "$repo/.git" ] || [ -f "$repo/.git" ]; then
    # buscar aqui
  fi
done
```

**Submodulos** (dentro de cada repo custom, si existen):
- `integra-addons/`
- `odoo-venezuela/`
- `third-party-addons/`

**Busqueda de commits** por ticket y periodo:
```bash
git -C "<repo>" log --all --since="<fecha_inicio>" --until="<fecha_fin>" \
  --format="%h %ad %an <%ae> %s" --date=short --grep="<numero_ticket>"
```

Para tickets no encontrados, buscar tambien en ramas locales con:
```bash
git -C "<repo>" branch -a | grep -i "<numero_ticket>"
```

### Paso 4: Cruzar tickets con commits y verificar autoria

Para cada ticket, determinar:

| Estado | Criterio | Accion |
|---|---|---|
| **Desarrollo propio** | Commit del autor del informe + mensaje contiene el numero de ticket | Incluir en el reporte |
| **Solo revision/merge** | Commit del autor pero sin cambios de codigo propios (solo merge, analisis) | Preguntar al usuario si incluir |
| **Otro autor** | Commit existe pero el autor NO es el del informe | Excluir del reporte |
| **Sin commits** | No se encontro ningun commit en el periodo | Preguntar al usuario (posiblemente testing/validacion sin codigo) |

**IMPORTANTE**: Siempre verificar la autoria con `%an <%ae>` en el formato de git log. Nunca asumir autoria sin confirmar.

Para commits encontrados, extraer la descripcion tecnica del mensaje del commit:
```bash
git -C "<repo>" log <commit_hash> -1 --format="%s%n%b"
```

### Paso 5: Clasificar complejidad para estimacion "Sin IA"

Usar la siguiente escala de multiplicadores:

| Complejidad | Multiplicador | Criterio |
|---|---|---|
| **Baja** | 1.5x | Fix puntual: 1 archivo, 1 campo, atributo faltante, ajuste simple |
| **Media** | 2.3x | Analisis multi-modulo, queries SQL, flujo entre capas, migracion de customs |
| **Alta** | 2.7x | Cambio de tipos de datos, regresiones con multiples iteraciones fix-test-fail, correccion de datos existentes via SQL |

**Señales objetivas de apoyo** (no reemplazan el criterio final, pero evitan que la clasificacion dependa solo de memoria/intuicion — ya estan disponibles de los pasos 3-4, no requieren trabajo adicional):
- **Cantidad de fechas distintas entre los commits del ticket** (`git -C "<repo>" log --grep="<numero_ticket>" --format=%ad --date=short`): mas de 1 fecha distinta sugiere iteracion fix-test-fail → empuja hacia Alta.
- **Cantidad de modulos/repos tocados** (`git -C "<repo>" show --stat <hash>` de cada commit del ticket): 1 modulo → Baja; 2+ modulos, o cruza de un custom a un submodulo (`integra-addons`/`odoo-venezuela`) → Media o Alta.
- **Dias calendario entre el primer y el ultimo commit del ticket**: mismo dia → Baja/Media; varios dias → señal de Alta.

Usar estas señales como checklist antes de asignar el tier, no como formula automatica — el criterio final sigue siendo del usuario. Si el tier elegido no coincide con lo que sugieren las señales (ej. se clasifica Baja pero hubo commits en 3 fechas distintas), preguntar o dejar constancia de por que aplica la excepcion.

### Paso 6: Preguntar al usuario sobre tickets dudosos

**ANTES de generar el HTML**, presentar una tabla con:

1. Tickets que cumplen el criterio (incluir)
2. Tickets en el rango de fecha pero sin commits del autor (preguntar)
3. Tickets con commits de otros autores (preguntar si excluir)
4. Tickets sin commits en absoluto (preguntar)

Ejemplo de formato de consulta:
```
### Tickets a incluir (6):
TI_13686, TI_13461, TI_13387, TI_13574, TI_13573, TA_73536

### Tickets dudosos en el periodo — ¿que hago con ellos?
1. TI_13577 — commits encontrados pero de otro autor (rsgg04), excluir?
2. TI_13656 — sin commits locales (pruebas con BK segun hoja), excluir?
3. TI_13159 — solo merge/revision de PR ajeno, incluir?
```

### Paso 7: Generar el HTML

Leer la plantilla con la tool Read desde `.claude/agents/reporte-horas-ia/template.html` y reemplazar los placeholders:

```
{{PERIODO}}         → "15 al 30 de junio de 2026"
{{EMPLEADO}}        → "Roger Vera"
{{FILAS}}           → bloques <tr> generados para cada ticket
{{TOTAL_CON_IA}}    → suma total de horas con IA
{{TOTAL_SIN_IA}}    → suma total de horas sin IA
```

**Formato de cada fila:**
```html
<tr>
  <td class="ti">{{NRO_TI_TA}}</td>
  <td class="tt">{{TITULO_TICKET}}</td>
  <td>{{DESCRIPCION}}</td>
  <td class="hr">{{HORAS_CON_IA}} h</td>
  <td>{{IMPACTO_SIN_IA}}</td>
  <td class="hr">{{HORAS_SIN_IA}} h</td>
</tr>
```

Donde:
- `{{NRO_TI_TA}}` = `TI_XXXXX` o `TA_XXXXX` (con underscore, sin espacio)
- `{{TITULO_TICKET}}` = titulo descriptivo corto (max ~60 chars)
- `{{DESCRIPCION}}` = basada en commit message + notas de la hoja de horas
- `{{HORAS_CON_IA}}` = horas de la hoja de horas para ese ticket
- `{{IMPACTO_SIN_IA}}` = descripcion de lo que habria costado sin asistencia de IA
- `{{HORAS_SIN_IA}}` = horas * multiplicador (redondeado a .0 o .5)

**IMPORTANTE**: La columna `Mayor impacto sin IA` debe describir concretamente que tareas especificas habrian sido mas lentas sin IA, no frases genericas. Ejemplos:
- Bien: "Navegacion y rastreo del query SQL entre modulos homologados: entender la estructura de _get_balances sin sugerencias de codigo"
- Mal: "El trabajo sin IA habria tomado mas tiempo"

Guardar el HTML generado como archivo con Write tool, con nombre sugerido:
```
reporte-horas-<periodo-corto>-<empleado>.html
```

### Reglas importantes

1. **Solo incluir tickets con desarrollo propio** (confirmado por autoria de commits)
2. **Excluir** ausencias, tiempo personal, reuniones, redaccion de informes
3. **TA_** para tareas (ej: TA_73536), **TI_** para tickets (ej: TI_13387)
4. **Horas con decimales**: usar formato `X.X h` o `X.XX h`
5. **Nunca inventar commits**: si no se encuentra, reportarlo como "sin commits"
6. **Verificar submodulos**: muchos fixes estan en `integra-addons/` u `odoo-venezuela/`, no en el repo principal
7. **Registro historico para recalibrar los multiplicadores**: ademas del HTML, appendear una fila por ticket a un CSV acumulativo `reporte-horas-historico.csv` (columnas: `fecha_reporte,ticket,complejidad,multiplicador,horas_con_ia,horas_sin_ia`) en el mismo directorio donde se guarda el HTML — crear el archivo con encabezado si no existe. Sirve para revisar cada tanto (ej. trimestral) si 1.5x/2.3x/2.7x siguen siendo realistas en vez de asumir que las constantes originales son correctas para siempre.

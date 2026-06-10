# TUI v3 Plan & Session Handoff

**Fecha:** 2026-06-10
**Sesión:** Revisión de `tui.py` → TUI v2 (PR #103) → TUI v3 (diseñado, parcialmente implementado)

---

## Estado al cerrar la sesión

### PRs abiertos
- **#103** `feat(tui): enabled toggle, fzf module picker, consolidated update flow`
  - Branch head: `feat/tui-v2-enabled-toggle-fzf-picker` (5 commits sobre `master-multi_bin-daldana`)
  - Target: `master-multi_bin-daldana`
  - Estado: OPEN, label `enhancement`
  - Ticket: none, Tarea: none
  - URL: https://github.com/binaural-dev/docker-odoo/pull/103

### Branches locales (no pusheados)
- `feat/tui-v3-external-css-optionlist` — **2 commits ya escritos por el sdd-apply** (CSS external + OptionList para ModulePicker), basados sobre `feat/tui-v2-enabled-toggle-fzf-picker`. **No pusheados, no verificados formalmente.** La base v2 tiene un merge de `feat/mcp-server` que vino del ref automático del agente; al pushear conviene rebasear sobre `feat/tui-v2-enabled-toggle-fzf-picker` limpio o master-multi_bin-daldana una vez mergeado #103.
  - `2c8b571 refactor(tui): move CSS to external odoo-tui.tcss for hot-reload via textual-dev`
  - `aad9af6 refactor(tui): use OptionList instead of ListView in ModulePicker`

### Untracked
- `mcp-server/` — directorio de trabajo local no relacionado con la TUI (tiene su propio `.venv` y `src/`). Ignorar.

---

## TUI v3 — Plan detallado

### Feature 1: CSS externo (`.tcss`)

**Por qué:** el `odoo-tui` tiene ~80 líneas de CSS inline en `CSS = """..."""` dentro de `DockerOdooApp`. Moverlo a un archivo externo habilita `textual run --dev ./odoo-tui` que da hot-reload de estilos sin reiniciar la app. Es la convención idiomática de Textual.

**Cómo:**
1. Crear `odoo-tui.tcss` en la raíz del repo (junto a `odoo-tui`).
2. Mover todo el contenido del atributo `DockerOdooApp.CSS` al archivo nuevo, sin tocar selectores ni valores.
3. En `odoo-tui`, reemplazar `CSS = """..."""` por `CSS_PATH = "odoo-tui.tcss"` como constante de clase.
4. **NO tocar** los `DEFAULT_CSS` de `InputModal`, `ConfirmModal` o `ModulePicker` — esos son per-screen y Textual los carga automáticamente. Solo `DockerOdooApp.CSS` se externaliza.

**Riesgo:** bajo. Es refactor mecánico.

### Feature 2: `OptionList` en `ModulePicker`

**Por qué:** `OptionList` es el widget idiomático de Textual para "elegí de una lista" (vs `ListView` que es más "lista navegable de items arbitrarios"). El `ModulePicker` es la pieza más usada de las nuevas features y merece el widget correcto.

**Cómo:**
1. En `ModulePicker`, reemplazar los dos `ListView` (`available_list` y `selected_list`) por `OptionList`.
2. Importar: `from textual.widgets import OptionList` y `from textual.widgets.option_list import Option`.
3. API de `OptionList` (referencia rápida, son APIs reales de Textual):
   - `list_widget.add_option(Option(text, id=module_name))` para agregar
   - `list_widget.clear_options()` para vaciar
   - `list_widget.options` → lista de `Option` con `.id` (el module_name)
   - `list_widget.highlighted` → `Option` actualmente resaltada o `None`
   - Evento: `on_option_list_option_selected(self, event: OptionList.OptionSelected)` — `event.option.id` y `event.option_list.id`
4. Reescribir el handler `on_list_view_selected` → `on_option_list_option_selected`. Usar `event.option.id` para el nombre del módulo, `event.option_list.id` para saber qué panel disparó.
5. Mantener nombres `self.available_list` y `self.selected_list` (están referenciados en CSS).
6. **Actualizar selectores en `odoo-tui.tcss`**:
   - `ListView > ListItem` → `OptionList > Option`
   - `ListView > ListItem.--highlight` → `OptionList > Option.--highlight`
   - Padding/height transfer 1:1.
7. **Marcador `✓`**: seguir renderizándolo en el `prompt` del `Option`. Ej: `Option(f"✓ {module_name}", id=module_name)` para seleccionado, `Option(f"  {module_name}", id=module_name)` para no. Mantener el patrón de rebuild-on-select.
8. **Filter logic** en `on_input_changed`: rebuild del `available_list` con options que matcheen el filtro. Los items ya en `selected_list` siguen visibles con `✓` aunque no matcheen el filtro, así el usuario siempre ve lo que seleccionó.
9. **NO tocar** otras modales ni los `ListView` de `DockerOdooApp` (instancias y acciones).

**Riesgo:** bajo-medio. Cambio de API, pero con la guía de arriba debería ser 20-30 líneas.

### Estructura de commits
- 2 commits (uno por feature)
- Conventional commits
- Sin `Co-Authored-By`
- Basado sobre `feat/tui-v2-enabled-toggle-fzf-picker` (stacked PR) — el diff de review queda limpio

### Quality gates antes de abrir PR
- [ ] `python3 -c "import ast; ast.parse(open('odoo-tui').read())"` pasa
- [ ] `grep -n "^CSS = " odoo-tui` → 0 matches
- [ ] `grep -n "CSS_PATH" odoo-tui` → 1 match
- [ ] `grep -n "OptionList" odoo-tui` → ≥ 2 matches
- [ ] `grep -n "ListView" odoo-tui` → ≥ 1 (en DockerOdooApp) pero **0 dentro de ModulePicker**
- [ ] Sin `print()` debug, sin `TODO/FIXME/XXX`
- [ ] Manual playtest del picker en TTY

---

## Issues abiertos del review original de `tui.py`

Del review de 15 puntos sobre la versión original (antes de v2):

| # | Issue | Estado |
|---|---|---|
| 1 | Dispatcher bloquea acciones sin instancia | **Resuelto en v2** (todas las acciones sin `ARG_INSTANCE` ahora pasan el guard) |
| 2 | `remove` salta confirmación destructiva | **Abierto** — `ConfirmModal` existe pero nunca se instancia |
| 3 | RichLog markup collision (stdout crudo → markup) | **Abierto** — el `module_cache` warnings pueden tener brackets; `markup=False` o escape sigue pendiente |
| 4 | No se puede cancelar comando largo | **Abierto** — no hay propagación de SIGINT al child process |
| 5-10 | Dead code (`ConfirmModal` instancia, `to_dict`, `needs_db_first`, `selected_instance` reactive, `tab` binding, `Refresh` label) | **Algunos resueltos en v2**, `ConfirmModal`/`to_dict`/`needs_db_first` siguen dead |
| 11 | Defaults hardcoded a Binaural (`/binaural_accountant`, etc.) | **Abierto** — siguen en `script:test` defaults de `_arg_defaults` |
| 12 | `_save_instances_json` revierte in-memory en `PermissionError` | **Resuelto en v2** |
| 13 | CATEGORY_BADGE padding inconsistente | **Abierto** |
| 14 | RichLog sin tope de líneas | **Abierto** |
| 15 | Mapeo `script:` → path duplica conocimiento del FS | **Abierto** |

---

## Backlog priorizado (no incluido en v2 ni v3)

| Prioridad | Item | Dónde |
|---|---|---|
| Media | Wirear `ConfirmModal` a la acción `remove` | `odoo-tui` línea ~138 (definición de Action) |
| Media | Decidir `needs_db_first` (declarado en 4 actions, nunca leído) | `odoo-tui:82` |
| Media | Test unitario de `ModulePicker.on_option_list_option_selected` (ambos paneles) | nuevo `tests/test_module_picker.py` |
| Baja | Fix `instances.example.json`: `client-b` referencia `external_pg16` no definida en `databases` | `instances.example.json:68-79` |
| Baja | RichLog `max_lines=N` para evitar degradación con outputs largos | `odoo-tui:477` |
| Baja | `_log` swallow silencioso (`except Exception: pass`) | `odoo-tui:730-731` |
| Baja | Cancelación de comando largo (Ctrl+C propaga al child) | `_run_streamed` y `_run_interactive` |
| Estratégico | Evaluar `Textualize/trogon` como alternativa arquitectónica (auto-TUI desde Click). No aplicar; requiere replantear el producto. | https://github.com/Textualize/trogon |
| DX | Documentar `textual run --dev ./odoo-tui` en el readme (cobra sentido una vez que v3 externalice el CSS) | `readme.md` |

---

## Referencias Textual (para futuras sesiones)

- **matan-h/written-in-textual** — best-of curado de 130 listas con 93K estrellas. Proyectos relevantes para nosotros:
  - `Textualize/trogon` (auto-genera TUI desde Click CLI) — alternativa arquitectónica
  - `darrenburns/textual-autocomplete` — autocomplete dropdown, podría reemplazar el filter manual del ModulePicker
  - `mitosch/textual-select` — searchable select
  - `harlequin` — SQL IDE, patrón "input + resultados"
- **realpython.com/python-textual** — tutorial oficial-style. Cubre widgets, TCSS, `textual-dev`, layouts, events/actions.
  - URL: https://realpython.com/python-textual/

---

## Quick-start para la próxima sesión

1. **Si #103 sigue abierto y querés mergearlo primero:**
   ```bash
   git checkout master-multi_bin-daldana
   gh pr view 103  # revisar el diff final antes de aprobar
   gh pr merge 103 --squash  # o el método que prefieras
   ```

2. **Si querés pushear y mergear v3 después:**
   ```bash
   git checkout feat/tui-v3-external-css-optionlist
   # Limpiar la base: rebase sobre feat/tui-v2-enabled-toggle-fzf-picker limpio
   # (sin el merge de feat/mcp-server que metió el sdd-apply)
   git rebase --onto feat/tui-v2-enabled-toggle-fzf-picker feat/tui-v2-enabled-toggle-fzf-picker
   # O, más simple, cherry-pick los 2 commits sobre master-multi_bin-daldana (post-merge de #103):
   git checkout master-multi_bin-daldana
   git cherry-pick 2c8b571 aad9af6
   # Verificar y pushear
   python3 -c "import ast; ast.parse(open('odoo-tui').read())"
   git push origin master-multi_bin-daldana
   # O abrir PR
   git checkout -b feat/tui-v3-external-css-optionlist-clean
   git push -u origin feat/tui-v3-external-css-optionlist-clean
   gh pr create --base master-multi_bin-daldana --head feat/tui-v3-external-css-optionlist-clean \
     --title "refactor(tui): external CSS + OptionList for ModulePicker" \
     --body "..."
   ```

3. **Si preferís rehacer v3 desde cero** (el sdd-apply fue cancelado, los commits existentes no fueron verificados):
   - Borrar el branch: `git branch -D feat/tui-v3-external-css-optionlist`
   - Re-delegar a `sdd-apply` con el spec de este documento (sección "TUI v3 — Plan detallado")

---

## Notas para la próxima sesión

- El usuario está iterando rápido sobre la TUI; prefiere PRs stacked sobre esperar merges.
- Los commits se basan con `git mv` para preservar historial (verificado que `git log --follow` lo rastrea).
- Convention commits lowercase (`feat`, `chore`, `docs`, `refactor`) — el repo acepta los dos formatos pero los commits nuevos van en lowercase.
- El usuario **no usa** el flujo de issues con `status:approved` (Binaural no parece enforce). El skill `branch-pr` se relaja acá: se acepta `Ticket: none, Tarea: none`.
- La label correcta para PRs de feature en este repo es `enhancement` (no `type:feature` que el skill sugiere).
- Hay tensión entre la guía de `branch-pr` (strict issue-first) y la práctica real del repo (sin issues, sin labels `type:*`). Para próximos PRs, usar la convención del repo y documentar la divergencia en el PR body.

---
name: odoo-16-to-17-migration
description: Migra módulos Odoo custom de la versión 16.0 a 17.0 - actualiza manifests, convierte atributos attrs= a expresiones inline en vistas XML, corrige typos y atributos deprecados (no_open/no_create_edit). Usar cuando el usuario pida migrar módulos custom de Odoo 16 a 17.
---

# Odoo 16 → 17 Migration Skill

## When to Use
Use this skill when the user wants to migrate Odoo modules from version 16.0 to 17.0. This skill handles:
- Manifest version updates
- View XML deprecated attribute migrations (`attrs=` → inline expressions)
- Typo fixes (`////` → `//`)
- Attribute migrations (`no_open`, `no_create_edit` → `options` dict)

## Migration Steps

### Phase 0: Identify Target Modules (ASK FIRST)
Before migrating, determine WHICH modules to target. Ask the user one of these questions:

1. **By prefix**: "Migra los modulos `bambary_`" → use glob `bambary_*/__manifest__.py`
2. **By directory**: "Migra todo lo que esta en `src/custom/`" → use that base path
3. **By version**: Auto-detect all modules with `"version": "16.0.` in their manifest
4. **By list**: User provides explicit module names

**Auto-detection method** (if user says "migra todos los custom"):
```bash
# Find all 16.0 manifests
grep -rl '"version": "16\.0\.' --include="__manifest__.py" .
```

Once modules are identified, list them to the user for confirmation before proceeding.

### Phase 1: Manifest Versions
1. Read each `__manifest__.py` found in Phase 0
2. Replace `"version": "16.0.X.X.X"` with `"version": "17.0.1.0.0"` for every module
3. Use the exact current version string found in each manifest to avoid mismatches

### Phase 2: View XML Migrations
For every XML file under the target module's `views/`, `wizard/`, and `report/` directories:

#### 2.1 Convert `attrs=` to inline expressions

**Basic field conditions:**
```
Odoo 16: attrs="{'invisible': [('field', '=', value)]}"
Odoo 17: invisible="field == value"

Odoo 16: attrs="{'invisible': [('field', '!=', value)]}"
Odoo 17: invisible="field != value"

Odoo 16: attrs="{'invisible': [('field', '=', False)]}"
Odoo 17: invisible="not field"

Odoo 16: attrs="{'invisible': [('field', '!=', False)]}"
Odoo 17: invisible="bool(field)"
```

**Readonly conditions:**
```
Odoo 16: attrs="{'readonly': [('field', '=', value)]}"
Odoo 17: readonly="field == value"

Odoo 16: attrs="{'readonly': [('field', 'in', list)]}"
Odoo 17: readonly="field in list"
```

**Required conditions:**
```
Odoo 16: attrs="{'required': [('field', '=', False)]}"
Odoo 17: required="not field"
```

**Combined conditions (split into separate attributes):**
```
Odoo 16: attrs="{'readonly': [...], 'invisible': [...]}"
Odoo 17: readonly="..." invisible="..."
```

**OR logic:**
```
Odoo 16: attrs="{'invisible': ['|', A, B]}"
Odoo 17: invisible="A or B"
```

**AND logic:**
```
Odoo 16: attrs="{'invisible': ['&', A, B]}"
Odoo 17: invisible="A and B"
```

**Complex logic with properly grouped parenthesization:**
```
Odoo 16: attrs="{'readonly': ['|', '&', A, B, C]}"
Odoo 17: readonly="(A and B) or C"
```

**HTML entities in attrs:**
```
Odoo 16: ('state', '!=', 'draft') ... ('field', '&gt;', 0)
Odoo 17: state != 'draft' ... field > 0
```
Note: `&gt;` → `>`, `&lt;` → `<`, `&amp;` → `and` (in boolean context)

**On `<div>`, `<label>`, `<button>` elements:**
```
Odoo 16: <div attrs="{'invisible': [('field', '=', False)]}">
Odoo 17: <div invisible="not field">

Odoo 16: <button ... attrs="{'invisible':[...]}" />
Odoo 17: <button ... invisible="..." />
```

#### 2.2 Convert deprecated standalone attributes

```
Odoo 16: no_open="1" no_create_edit="1"
Odoo 17: options="{'no_open': True, 'no_create_edit': True}"

Odoo 16: no_open="1"
Odoo 17: options="{'no_open': True}"
```

#### 2.3 Fix common typos
```
Odoo 16: ////expr (not valid XPath)
Odoo 17: //expr
```
Search for `////` in all XML files and replace with `//`.

#### 2.4 Fix syntax errors
Search for patterns like `/> />` (double self-closing tags) and fix them to single `/>`.

#### 2.5 Fix `id` keyword in inline expressions
Odoo 17's safe_eval blocks the Python builtin `id`. Any expression like `invisible="not id"` or `readonly="not id or ..."` will crash.
```
Odoo 16 attrs: attrs="{'invisible': [('id', '=', False)]}"
BAD conversion:  invisible="not id"          ← CRASHES
FIX:             invisible="0" (or remove the attrs entirely)
```
The `id` field is not available in view evaluation context in Odoo 17. Simply remove the condition or replace with a proper domain expression.
Search for: `not id` (without underscore) in all XML files.

### Phase 3: Verification
1. Search for remaining `attrs=` in all XML files under the target modules:
   ```
   grep -r "attrs=" --include="*.xml" <module_paths>
   ```
2. Search for remaining `////` patterns
3. Search for remaining `no_open="1"` patterns
4. Verify all manifest versions are `17.0.1.0.0`

## Important: What NOT to change
The following patterns are still valid in Odoo 17 and should NOT be modified:
- `class="oe_*"` (oe_inline, oe_highlight, oe_button_box, oe_stat_button, oe_no_button)
- `<tree>` tag (was ALWAYS `<tree>`, never `<list>`)
- `position="replace"` and `position="attributes"` in xpath
- `groups=`, `domain=`, `context=`, `widget=`, `options=`
- `force_save="1"`, `nolabel="1"`, `readonly="1"`, `invisible="1"`
- `required="1"`, `optional="hide"`, `optional="show"`
- `decoration-*` attributes
- `column_invisible=`
- `create="0"`, `edit="0"`, `delete="0"`

## Conversion Reference Table

| Odoo 16 attrs sub-expression | Odoo 17 inline |
|---|---|
| `[('field', '=', value)]` | `field == value` |
| `[('field', '!=', value)]` | `field != value` |
| `[('field', 'in', [a, b])]` | `field in [a, b]` |
| `[('field', 'not in', [a, b])]` | `field not in [a, b]` |
| `['\|', A, B]` | `A or B` |
| `['&', A, B]` | `A and B` |
| `('field', '=', False)` | `not field` |
| `('field', '!=', False)` | `bool(field)` |
| `('field', '>', N)` | `field > N` |
| `('field', '<', N)` | `field < N` |

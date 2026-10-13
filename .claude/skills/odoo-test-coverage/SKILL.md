---
name: odoo-test-coverage
description: Crea y ejecuta pruebas unitarias para módulos de Odoo en el entorno Multi-Instance Docker de Binaural (multi-docker-odoo), y mide/eleva el coverage con ./scripts/coverage. Úsala cuando el usuario pida crear tests, pruebas unitarias, subir coverage, o mencione test_tags, tests/, coverage o ./scripts/coverage para un módulo de Odoo.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, AskUserQuestion
---

## Cuándo usar esta skill

- El usuario pide crear pruebas unitarias para un módulo de Odoo.
- El usuario quiere ejecutar el script de coverage para medir cobertura.
- El usuario quiere subir el porcentaje de coverage de un módulo.
- El usuario menciona `test_tags`, `tests/`, `coverage`, o `./scripts/coverage`.

## Flujo obligatorio

Seguir siempre este orden:

1. **EXPLORAR** el módulo objetivo → entender modelos, métodos, controladores, wizards.
2. **BUSCAR REFERENCIAS** → localizar tests similares ya existentes en `integra-addons` y `odoo-venezuela`.
3. **CREAR TESTS** → escribir archivos de prueba siguiendo el patrón `TransactionCase`.
4. **MOSTRAR COMANDO** → presentar el comando `./scripts/coverage` con sus parámetros.
5. **PEDIR CONFIRMACIÓN** → usar `AskUserQuestion` antes de ejecutar nada contra Docker/DB.
6. **EJECUTAR** (solo si el usuario confirma) → correr el script y capturar el reporte de coverage.
7. **ITERAR** → si coverage < 90%, identificar líneas faltantes y agregar más tests; volver al paso 6.

**Nunca ejecutar `./scripts/coverage` sin confirmación explícita del usuario** — cambia de `--db_name` puede tardar 10–30 min al reinicializar la base de datos.

## Dónde buscar tests de referencia

| Prioridad | Ruta | Notas |
|---|---|---|
| 1 | `/home/binaural80/Documents/integra-addons/` | Módulos custom de Binaural |
| 2 | `/home/binaural80/multi-docker-odoo/src/` | Cualquier subdirectorio con módulos y tests |
| 3 | `find /home/binaural80 -path "*/tests/test_*.py"` | Fallback global |

```bash
find /home/binaural80/Documents/integra-addons -path "*/tests/test_*.py" | grep -i <termino>
grep -r "class Test.*NombreModelo" /home/binaural80/Documents/integra-addons --include="*.py"
```

## Estructura obligatoria del archivo de test

```python
from odoo.tests.common import TransactionCase, tagged
from odoo.tests import Form
from odoo.exceptions import ValidationError, UserError


@tagged('nombre_modulo', 'nombre_archivo_test', '-at_install', 'post_install')
class TestNombreClase(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})

    def test_nombre_descriptivo(self):
        """Descripción clara de lo que prueba."""
        self.assertTrue(self.partner.name)
```

### Reglas de tags (obligatorias, exactamente 4)

1. **Módulo**: nombre técnico del módulo, ej. `l10n_ve_donation`, `binaural_sale`.
2. **Archivo**: nombre del archivo de test sin el prefijo `test_` (ej. `test_account_move.py` → `account_move`).
3. `-at_install`
4. `post_install`

```python
@tagged('l10n_ve_donation', 'hr_partner_donation', '-at_install', 'post_install')
```

## Script de coverage

Carpeta base: `/home/binaural80/multi-docker-odoo`

```bash
cd /home/binaural80/multi-docker-odoo
./scripts/coverage --odoo_container=<CONTAINER> --modules="<RUTA_MODULO>" --db_name="<DB>" --test_tags="<TAGS>"
```

| Parámetro | Descripción | Ejemplo |
|---|---|---|
| `--odoo_container` | Contenedor Docker con Odoo | `odoo-thk` |
| `--modules` | Ruta relativa a `/home/odoo/src/` dentro del contenedor | `/odoo-venezuela/l10n_ve_invoice_digital` |
| `--db_name` | Base de datos de prueba | `tst1` |
| `--test_tags` | Tags a ejecutar, separados por coma | `l10n_ve_donation,hr_partner_donation` |

```bash
docker ps --filter "name=odoo" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Advertencia crítica**: cambiar `--db_name` fuerza a Odoo a inicializar una base de datos nueva (10–30 min). Reutilizar el mismo `db_name` entre iteraciones salvo que la DB quedó corrupta.

## Meta: coverage ≥ 90%

Iteración:
1. Ejecutar coverage con todos los tests del módulo.
2. Analizar el reporte: archivos con baja cobertura.
3. Ver líneas específicas no cubiertas (reporte `-m`).
4. Crear tests que ejerciten esas líneas.
5. Volver al paso 1.

Técnicas para subir coverage:
- Cubrir todas las ramas `if/else` de un método.
- Cubrir casos de error con `assertRaises`.
- Cubrir `@api.constrains`, `@api.depends`, computed fields.
- Cubrir wizards (crear, ejecutar `action_*`).
- Cubrir controladores HTTP (con `patch` para simular requests).
- Cubrir reportes/QWeb si aplica.

## Antes de ejecutar el script: presentación y confirmación

Antes de correr `./scripts/coverage`, mostrar el comando completo, explicar brevemente qué hará, y preguntar con `AskUserQuestion` si se puede proceder. Ejemplo de mensaje:

```
Voy a ejecutar el script de coverage con estos parámetros:

./scripts/coverage --odoo_container=odoo-thk --modules="/odoo-venezuela/l10n_ve_donation" --db_name="tst_donation_1" --test_tags="l10n_ve_donation"

- Contenedor: odoo-thk
- Módulo: /odoo-venezuela/l10n_ve_donation
- Base de datos: tst_donation_1 (nueva, puede tardar)
- Tags: l10n_ve_donation
```

## Ejemplos de código

Ver [assets/examples.md](assets/examples.md) para: test básico de modelo, test con `Form`, test de controlador con `mock`, y test de wizard.

# Ejemplos de fixes por código pylint_odoo

## W8301 / W8303 — Traducción no lazy

Mal:
```python
raise UserError(_("El empleado %s no existe") % employee.name)
raise ValidationError(_("El monto es %(amount)s") % {"amount": monto})
raise UserError(_(f"Error: {mensaje}"))
```

Bien (los args van como argumentos de `_()`, no con `%`/`.format()`/f-string):
```python
raise UserError(_("El empleado %s no existe", employee.name))
raise ValidationError(_("El monto es %(amount)s", amount=monto))
raise UserError(_("Error: %s", mensaje))
```

## E8103 — SQL injection

Mal:
```python
cr.execute("DELETE FROM %s WHERE id = %s" % (table_name, record_id))
```

Bien:
```python
from psycopg2.sql import SQL, Identifier

cr.execute(SQL("DELETE FROM {} WHERE id = %s").format(Identifier(table_name)), [record_id])
```

Si el linter marca un caso ya seguro (identificador validado en código, no viene de input externo):
```python
cr.execute(query)  # pylint: disable=sql-injection
```

## E8106 — request sin timeout

Mal:
```python
response = requests.post(url, json=payload, headers=headers)
```

Bien:
```python
response = requests.post(url, json=payload, headers=headers, timeout=30)
```

## W8138 — except vacío

Mal:
```python
try:
    index.drop()
except Exception:
    pass
```

Bien:
```python
try:
    index.drop()
except Exception as e:
    _logger.debug("No se pudo eliminar índice %s: %s", conname, e)
```

## W8110 — falta return con super()

Mal:
```python
def set_values(self):
    super().set_values()
    if self.dispatch_guide_digital_tfhka:
        module.button_immediate_install()
```

Bien:
```python
def set_values(self):
    res = super().set_values()
    if self.dispatch_guide_digital_tfhka:
        module.button_immediate_install()
    return res
```

## C8107 — falta `_()` en string traducible

Mal:
```python
state = fields.Selection([...], string="Estado")
```

Bien:
```python
state = fields.Selection([...], string=_("Estado"))
```

## C8108 — método compute mal nombrado

Mal:
```python
@api.depends('line_ids')
def compute_total(self):
    ...
```

Bien:
```python
@api.depends('line_ids')
def _compute_total(self):
    ...
```

## W0404 — import duplicado

Mal:
```python
from odoo.exceptions import UserError
...
from odoo.exceptions import UserError, ValidationError
```

Bien: dejar un solo import consolidado.

## W0101 — código muerto tras return

Mal:
```python
def action_confirm(self):
    return {'type': 'ir.actions.act_window_close'}
    self.write({'state': 'done'})  # nunca se ejecuta
```

Bien: eliminar el código inalcanzable o mover el `return` al final real del método.

# AI_LOG — equipment_loan

## Herramientas
- Antigravity (Google DeepMind / Gemini)

## Prompts clave (3 a 5)
1. "¿Cómo garantizar en Odoo 17 y PostgreSQL que un equipo nunca quede con dos préstamos activos al mismo tiempo, incluso si dos usuarios hacen clic en 'Entregar' en el mismo milisegundo?"
   - *Respuesta:* Recomendó una estrategia de doble barrera: a nivel de ORM/Python mediante bloqueo de fila `SELECT ... FOR UPDATE` sobre la tabla del equipo, y a nivel de base de datos con un índice parcial único (`CREATE UNIQUE INDEX ... ON equipment_loan (laptop_id) WHERE state = 'loaned'`). Implementado en `models/equipment_loan.py`.
2. "¿Cómo declarar un campo computado `is_overdue` que pueda utilizarse en filtros de búsqueda XML (`search_view`) en Odoo 17?"
   - *Respuesta:* Explicó la necesidad de definir el argumento `search='_search_is_overdue'` en el campo booleano y escribir la función que traduce el operador a una tupla de dominio compatible con SQL.
3. "¿Cómo implementar un Smart Button dinámico en el formulario de préstamo que abra el historial filtrado del equipo seleccionado?"
   - *Respuesta:* Mostró la estructura del método `action_view_laptop_history()` retornando un diccionario `ir.actions.act_window` con el dominio `[('laptop_id', '=', self.laptop_id.id)]` y su botón en la cabecera del sheet.
4. "¿Cómo restringir mediante `@api.constrains` que un registro de equipo no pueda ser asociado a más de 2 préstamos en toda su historia?"
   - *Respuesta:* Sugirió contar los registros en el modelo `equipment.loan` mediante `search_count([('laptop_id', '=', record.laptop_id.id)])` y lanzar `ValidationError` si supera 2.

## Lo que la IA hizo mal
- Usó una tupla de excepciones `self.assertRaises((UserError, ValidationError))` en las pruebas unitarias.
  - *Cómo me di cuenta:* La clase base de pruebas de Odoo 17 (`odoo.tests.common.TransactionCase`) sobreescribe `assertRaises` e implementa una verificación interna `issubclass(exception, AccessError)`, la cual lanza `TypeError: issubclass() arg 1 must be a class` si se le pasa una tupla en vez de una clase individual. Lo corregí separando cada aserción con su excepción específica (`UserError` para la acción y `ValidationError` para la restricción ORM).
- Definió un filtro en la vista de búsqueda (`equipment_laptop_views.xml`) filtrando por `overdue_loan_count > 0` siendo un campo computado no almacenado (`store=False`) sin proveer un método `search`.
  - *Cómo me di cuenta:* El runner de pruebas de Odoo 17 arrojó `odoo.tools.convert.ParseError: Unsearchable field 'overdue_loan_count' in path 'overdue_loan_count'`. Lo solucioné implementando la función `_search_overdue_loan_count` en `models/equipment_laptop.py` para traducir el dominio a SQL y resolver la búsqueda limpiamente.
- Inicialmente sugirió implementar la restricción de concurrencia únicamente con un chequeo `if self.search(...)` antes de escribir en la base de datos.
  - *Cómo me di cuenta:* Entre el `search` y el `write` existe una ventana de tiempo vulnerable a *Race Conditions* si dos hilos de Odoo atienden peticiones simultáneas. Exigí la incorporación del bloqueo transaccional `SELECT ... FOR UPDATE` y el índice parcial único en PostgreSQL.
- Intentó usar `attrs="{'invisible': [('state', '!=', 'draft')]}"` en las vistas XML.
  - *Cómo me di cuenta:* Las directrices del proyecto y Odoo 17 deprecaron completamente `attrs`. Lo corregí inmediatamente usando la sintaxis moderna directa `invisible="state != 'draft'"`.

## Lo que escribiste tú sin IA
- El diseño de la suite de pruebas unitarias (`test_equipment_loan.py`) con casos de prueba específicos para la concurrencia, el límite de 2 préstamos, el cálculo dinámico de vencimiento y el registro automático de la fecha real.
- Las preguntas de negocio y supuestos operativos reflejados en el `README.md`.


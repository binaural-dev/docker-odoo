# Préstamos de Equipos y Laptops (`equipment_loan`)

Módulo desarrollado para Odoo 17 enfocado en el registro, control de inventario y gestión de préstamos de laptops a colaboradores, incorporando prevención de condiciones de carrera (concurrencia), restricciones de límites de uso y monitoreo de vencimientos.

---

## 1. Alcance y Funcionalidades Implementadas

- **Catálogo de Laptops (`equipment.laptop`):**
  - Registro de serial único, marca, modelo, especificaciones y estado (`available`, `loaned`, `maintenance`).
  - Botón inteligente (*Smart Button*) con contador dinámico de préstamos totales y préstamos vencidos.
  - Pestaña con historial completo de préstamos vinculados.
  - Integración con Chatter (`mail.thread`, `mail.activity.mixin`) para trazabilidad de incidencias y mantenimiento.

- **Gestión de Préstamos (`equipment.loan`):**
  - Secuencia correlativa automática: `PREST/%(year)s/0001`.
  - Estados del ciclo de vida: `draft` (Borrador) → `loaned` (Prestado) → `returned` (Devuelto).
  - Campos obligatorios: Equipo (`laptop_id`), Persona que recibe (`receiver_id`), Responsable (`user_id`), Fecha de entrega (`delivery_date`), Fecha previa de devolución (`expected_return_date`).
  - Fecha real de devolución (`actual_return_date`): Campo protegido que se completa automáticamente al pulsar el botón **"Devolver"**.
  - Botón de acción **"Entregar"**:
    - Verifica disponibilidad del equipo.
    - Ejecuta bloqueo a nivel de fila en PostgreSQL (`SELECT ... FOR UPDATE`) para evitar asignaciones simultáneas (Race Conditions).
    - Actualiza el estado del equipo y la solicitud a `loaned`.
  - Botón de acción **"Devolver"**:
    - Registra la fecha real de retorno con la fecha actual del sistema.
    - Libera el equipo a estado `available`.
  - Botón en formulario **"Historial del Equipo"**:
    - Permite al operador consultar con un clic el historial de préstamos y atrasos del equipo seleccionado.

- **Validaciones e Integridad:**
  - **Préstamo Activo Exclusivo (Unicidad Simultánea):** Restricción `@api.constrains('laptop_id', 'state')` que prohíbe terminantemente que un equipo esté prestado a dos personas al mismo tiempo, ni que la misma persona tenga el mismo equipo en dos préstamos activos a la vez. No limita el historial a lo largo de la vida útil: un equipo puede prestarse infinitas veces siempre que el préstamo anterior haya sido devuelto.
  - **Cálculo de Préstamos Vencidos:** Campo computado `is_overdue` (`search='_search_is_overdue'`) activo cuando el préstamo sigue en curso y la fecha actual supera la fecha previa acordada.
  - **Coherencia de Fechas:** Validación que impide que la fecha estimada de retorno sea anterior a la fecha de entrega.
  - **Inmutabilidad Post-Entrega:** Sobreescritura del método `write()` para proteger contra edición el equipo, receptor y fechas una vez entregado.
  - **Concurrencia a nivel de Base de Datos:** Índice parcial único en PostgreSQL (`equipment_loan_unique_active_laptop`) sobre `laptop_id` donde `state = 'loaned'`.

- **Vistas y Experiencia de Usuario (Odoo 17):**
  - Uso estricto de sintaxis Odoo 17 (`invisible="..."`, `readonly="..."`, sin `attrs` ni `states`).
  - Cinta visual (Ribbon) de **"VENCIDO"** en color rojo cuando el préstamo está en mora.
  - Vista de lista con decoraciones por color: rojo para vencidos, azul para activos, gris para devueltos.
  - Vista de búsqueda con filtros por estado: *En Préstamo (Activos)*, *Préstamos Vencidos*, *Devueltos*, *Borradores* y agrupación por equipo y receptor.

---

## 2. Supuestos y Preguntas al Cliente

Al analizar los requerimientos para el módulo de préstamos, identificamos puntos clave de definición operativa:

### 1. ¿Qué le preguntaríamos al cliente / responsable de TI?
1. **Accesorios y Periféricos:**
   - *Pregunta:* "¿Al registrar la entrega de la laptop se requiere inventariar cargador, bolso, mouse o adaptador por separado, o se gestiona dentro de las observaciones del registro?"
2. **Manejo de Equipos Devueltos con Daños:**
   - *Pregunta:* "Al devolver una laptop que presenta fallas o golpes, ¿el operador debe poder marcarla directamente en estado `maintenance` desde la devolución del préstamo?"

### 2. Supuestos aplicados en el desarrollo
1. **Exclusividad de Préstamo Activo:** Se validó que el equipo jamás coexista en dos préstamos con estado `loaned`. Sin embargo, su historial de vida útil permanece abierto para préstamos futuros una vez devuelto.
2. **Registro Automático de Fecha Real:** Se asumió que la fecha real de retorno corresponde a la fecha de la transacción en Odoo (`context_today`) para evitar discrepancias manuales.
3. **Aislamiento y Concurrencia:** Se implementó doble barrera contra concurrencia: bloqueo transaccional `FOR UPDATE` en el método `action_deliver` e índice parcial único a nivel de PostgreSQL.

---

## 3. Cómo Probar el Módulo

### 1. Pruebas Automatizadas
Ejecutar la suite de tests unitarios:
```bash
./odoo test prueba-tecnica equipment_loan
```
O con el comando Python directo en Windows:
```powershell
$env:PYTHONUTF8=1; python odoo test prueba-tecnica equipment_loan
```

### 2. Verificación Manual en la Interfaz Web
1. Ir a **Préstamos de Equipos > Catálogo de Equipos > Equipos y Laptops**:
   - Crear una laptop indicando serial único, marca y modelo. Verificar que quede en estado *Disponible*.
2. Ir a **Préstamos de Equipos > Operaciones > Préstamos**:
   - Crear un nuevo préstamo seleccionando el equipo, persona que recibe y fecha previa de devolución.
   - Observar el botón inteligente **"Historial del Equipo"**.
   - Presionar **"Entregar"**: El estado pasa a *Prestado* y la laptop queda en estado *Prestado*. Los campos clave se bloquean contra edición.
   - Intentar crear y entregar otro préstamo con la misma laptop: El sistema lo impedirá por control de concurrencia.
   - En el préstamo activo, presionar **"Devolver"**: El estado pasa a *Devuelto*, se registra automáticamente la fecha del día en **Fecha Real de Devolución** y la laptop vuelve a estar *Disponible*.
   - Si se configura una fecha previa en el pasado, verificar que aparezca la cinta roja **"VENCIDO"** y el filtro en la barra de búsqueda.
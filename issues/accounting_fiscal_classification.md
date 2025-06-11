# Accounting: Fiscal Classification on Invoices

## Goal
Agregar un nuevo campo `fiscal_classification` de tipo selección en `account.move`. Los valores válidos serán A, B y C. Debe mostrarse en el formulario de factura y permitir búsquedas por esta clasificación.

## Acceptance Tests
- El valor por defecto de `fiscal_classification` debe ser A.
- El campo debe mostrarse en la vista de formulario de `account.move`.
- Debe existir un filtro de búsqueda para este campo.
- Incluir una prueba unitaria que valide el valor por defecto y la actualización del campo.

## Evaluación
El módulo debe instalarse sin errores y las pruebas deben ejecutarse correctamente en el entorno provisto.

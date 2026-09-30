# Resumen

## Correcciones
Lista de correcciones realizadas, tales como patches o fixes.
- Se corrige la compensación y deducción de anticipos multimoneda en billing_and_collection: resolución del error de moneda secundaria al cruzar facturas/anticipos en divisas (EUR/USD), tope máximo con validación en tiempo real, conversión cruzada EUR/USD, ajustes para facturas con IVA y automatización de la desconciliación de anticipos.
- Se ajusta el cálculo de tasas y redondeo en la deducción de anticipos y créditos multimoneda (USD/VES) en billing_and_collection: diferencial cambiario con tasa histórica de factura, cruce nominal 1:1 en Bolívares, redondeo techo, holgura de 10 Bs y normalización a 2 decimales para evitar diferenciales cambiarios falsos por céntimos.
- Se corrige la visibilidad del botón para cancelar la orden de pago en treasurers_office (#13510).
- Se agrega validación para evitar duplicados en las líneas de carga masiva de facturas en tools_bp (#14514).
- Se ajusta el texto del segundo párrafo de la nota importante en el reporte de bp_port_leasing.
- Se corrigen (hotfix) varios flujos de bp_credits_advices: la generación del aviso de crédito desde la acción de pago residual para que envíe el apunte contable directamente al asiento del pago, la validación del estado del aviso de crédito, el cómputo heredado del monto en el wizard de registrar cobro y la protección para no cancelar el aviso de crédito al solo romper la conciliación de su pago asociado.
- Se corrige la columna de subtotal en bp_currency_preference_proform, que ignoraba la preferencia de moneda del partner y siempre mostraba el monto en Bs (#14634).
- Se corrige la preservación de la cuenta y el diario de destino en transferencias internas al cambiar el puerto en bp_national_ports_account.
- Se corrige el override de obtención del nombre de la factura en nc_nd_prefix para que coincida con la nueva firma del método en l10n_ve_accountant y siga quitando el prefijo NC/ND (#14680).
- Se corrige la tasa de los pagos generados por aviso de crédito en bp_credits_advices y ca_client_to_client_transfer, tomando la tasa del pago original (incluyendo avisos generados por transferencias de cliente a cliente).
- Se ocultan campos en el wizard de aplicar aviso de crédito y se quita la fecha de aplicación por defecto en tools_bp.
- Se agrega validación para impedir la confirmación de cobros con Monto Afectado igual o menor a 0 en billing_and_collection (#14670).
- Se corrige la validación multimoneda y la visualización de símbolos de moneda al aplicar avisos de crédito en Bs a facturas de canon en USD en bp_cross_currency_payments.
- Se corrige la pérdida de la fecha de recepción al marcar una retención de IVA como definitiva en recargas posteriores, y se evita duplicar el asiento contable en tools_bp (#14710).
- Se corrige la generación de una línea contable huérfana ("Receivable Transfer") al romper la conciliación de documentos que no son factura de cliente en ca_remove_outstanding_invoice (#14717).
- Se corrige el reporte de Avisos de Crédito en ca_client_to_client_transfer para no mostrar en la tabla de transferencias aquellas que estén canceladas (#14597).

## Hitos
Lista de hitos alcanzados, tales como tasks o implementaciones nuevas.
- Se agrega el endpoint /api/employees/details en bp_hr_api, con carga familiar, medicamentos y patologías del empleado (#13381).
- Se agrega el campo "Observaciones" al ticket de helpdesk, visible en la vista y en el reporte "Acta de Resolución de Caso de Soporte", en custom_helpdesk (#14471).
- Se agrega el módulo ca_credit_advice_cancel_cross con un wizard para cancelar cruces de pagos de un aviso de crédito, seleccionando uno o todos.
- Se agrega el módulo ca_client_to_client_transfer para transferir (y revertir) el saldo de avisos de crédito entre clientes, con botones en la vista, wizard de transferencia, trazabilidad, traducciones y pruebas unitarias; se agrega además la tabla de transferencias al reporte de Avisos de Crédito (#79301, #79345, #79448).
- Se descentraliza el flujo de pago de anticipos en billing_and_collection para puertos regionales y Sede Central, resolviendo dinámicamente la cuenta y el diario de destino según moneda y puerto.
- Se agrega el módulo bp_retention_labels y se traducen a inglés los labels de vistas, menús, acciones y reportes de retenciones en billing_and_collection, l10n_ve_retencion_iva, l10n_ve_retention_iva_multi y l10n_ve_retencion_islr, además de un nuevo campo de detalle del tipo de retención (#14596).
- Se agrega el mapeo de cuenta de transferencia entre puertos (inter-port transfer) en billing_and_collection y bp_national_ports_account.
- Se agrega el módulo bp_sale_book_late_withholdings, que extiende el Libro de Ventas para mostrar facturas de periodos anteriores cuya retención de IVA fue recibida dentro del rango impreso (#14660).
- Se agrega el campo "Bono de contingencia" (contingency_bonus) en custom_employee y custom_payroll (#14705).
- Se agrega un nuevo valor para la carga del archivo de retenciones de Sisalma en tools_bp, que pasa la retención de IVA a definitiva al cargarse.
- Se agrega tolerancia de redondeo configurable para cruces multimoneda y se optimiza el cruce USD-USD, con absorción dinámica del diferencial cambiario (CAMBI), en bp_cross_currency_payments.
- Se agrega el módulo bp_customer_invoice_notification para notificar al cliente adjuntando la factura con marca de agua, con pruebas unitarias (#14740).

## Colaboradores
Colaboradores quienes realizaron el commit.
- @roque-binaural
- @ronald-binaural
- @leandro-binaural
- @alexander-binaural

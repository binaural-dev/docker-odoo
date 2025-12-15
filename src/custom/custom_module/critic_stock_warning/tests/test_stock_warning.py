from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class TestCriticalStockAlerts(TransactionCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()

        # Crear un usuario de prueba y asignarlo al grupo
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test@example.com',
            'groups_id': [(6, 0, [self.env.ref('critic_stock_warning.purchase_stock_group').id])]
        })      

        # Crear un producto de prueba
        self.product = self.env['product.template'].create({
            'name': 'Product Test',
            'type': 'consu',
            'minimum_stock': 10,
            'low_stock': False
        })


    def test_alert_is_generated_once(self):
        """Debe generar una alerta cuando el stock es crítico,
            pero no debe generar alertas duplicadas."""

        # Forzar una cantidad disponible
        self.product.qty_available = 8  # menor que el mínimo

        # Obtener el canal de chat entre admin y test_user (si existe)
        admin_partner = self.env.user.sudo().id
        target_partner = self.test_user.partner_id

        domain = [
            ('channel_type', '=', 'chat'),
            ('create_uid', 'in', [admin_partner]),
            ('channel_partner_ids', 'in', [target_partner.id]),
        ]
        
        # Contar mensajes iniciales en el canal (si existe)
        channel = self.env['discuss.channel'].sudo().search(domain, limit=1)
        initial_message_count = len(channel.message_ids) if channel else 1
        
        
        # 1 Ejecutar el chequeo por primera vez
        self.product.check_for_critical_qty()

        # Buscar el canal después de la primera ejecución
        channel = self.env['discuss.channel'].sudo().search(domain, limit=1)
        
        # Verificar que se creó un canal
        self.assertTrue(
            channel,
            "Debería haberse creado un canal de chat para la notificación."
        )

         # Verificar que se agregó un mensaje al canal
        messages_after_first = len(channel.message_ids)
        self.assertEqual(
            messages_after_first, initial_message_count + 1,
            "Debería haberse enviado un mensaje después de la primera verificación."
        )
        
        # Verificar que low_stock se estableció en True
        self.assertTrue(
            self.product.low_stock,
            "El campo low_stock debería ser True después de la primera verificación."
        )

         # 2. Ejecutar el chequeo nuevamente (sin cambiar el stock)
        self.product.check_for_critical_qty()

        # Buscar el canal después de la segunda ejecución
        channel = self.env['discuss.channel'].sudo().search(domain, limit=1)

        # Verificar que no se agregó un nuevo mensaje
        messages_after_second = len(channel.message_ids)
        self.assertEqual(
            messages_after_second, messages_after_first,
            "No debería generar mensajes duplicados."
        )
        
        # Verificar que low_stock sigue siendo True
        self.assertTrue(
            self.product.low_stock,
            "El campo low_stock debería seguir siendo True."
        )


    def test_no_alert_when_stock_above_minimum(self):
        """No debe generar alertas cuando el stock está por encima del mínimo."""
        
        # Configurar stock disponible mayor que el mínimo
        self.product.qty_available = 15
        
        # Obtener el canal de chat entre admin y test_user (si existe)
        admin_partner = self.env.user.partner_id
        target_partner = self.test_user.partner_id
        
        domain = [
            ('channel_type', '=', 'chat'),
            ('channel_partner_ids', 'in', [admin_partner.id]),
            ('channel_partner_ids', 'in', [target_partner.id]),
        ]
        
        # Contar mensajes iniciales
        channel = self.env['discuss.channel'].sudo().search(domain, limit=1)
        initial_message_count = len(channel.message_ids) if channel else 0

        # Ejecutar el chequeo
        self.product.check_for_critical_qty()
        
        # Verificar que low_stock es False
        self.assertFalse(
            self.product.low_stock,
            "El campo low_stock debería ser False cuando el stock está por encima del mínimo."
        )
        
        # Si existe un canal, verificar que no se agregaron mensajes
        if channel:
            self.assertEqual(
                len(channel.message_ids), initial_message_count,
                "No debería enviar mensajes cuando el stock está por encima del mínimo."
            )

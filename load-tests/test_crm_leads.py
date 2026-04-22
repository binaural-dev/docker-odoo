# -*- coding: utf-8 -*-
"""
Test específico para módulo CRM - Gestión de leads/oportunidades.

Uso:
    locust -f test_crm_leads.py --host=http://localhost:PORT
"""

from locust import task, between
from base_test import BaseOdooUser


class CRMUser(BaseOdooUser):
    """
    Simula un usuario del departamento de ventas/CRM.

    Configuración:
    - Modifica 'instance_name' para apuntar a tu instancia
    - Ajusta 'wait_time' según el comportamiento deseado
    """
    abstract = False
    instance_name = "mercedes"  # <-- CAMBIA ESTO según tu instancia
    wait_time = between(1, 5)

    def on_start(self):
        """Inicializa la conexión y obtiene modelos necesarios."""
        super().on_start()
        self.lead_model = self.client.get_model('crm.lead')
        self.partner_model = self.client.get_model('res.partner')
        self.team_model = self.client.get_model('crm.team')
        self.stage_model = self.client.get_model('crm.stage')

        # Cachear etapas disponibles
        try:
            self.stages = self.stage_model.search_read([], ['id', 'name'])
        except:
            self.stages = []

    @task(15)
    def read_leads(self):
        """
        Lee leads/oportunidades.
        Peso: 15 (muy frecuente - operación principal)
        """
        try:
            lead_ids = self.lead_model.search(
                [('type', '=', 'opportunity')],
                limit=50,
                order='create_date desc'
            )
            if lead_ids:
                self.lead_model.read(
                    lead_ids,
                    ['name', 'partner_id', 'stage_id', 'user_id',
                     'expected_revenue', 'probability', 'date_deadline']
                )
        except Exception as e:
            pass

    @task(10)
    def read_leads_pipeline(self):
        """
        Lee leads por etapa (vista pipeline).
        Peso: 10 (frecuente - uso de kanban)
        """
        try:
            # Simular lectura de pipeline por etapas
            for stage in self.stages[:3]:  # Solo las primeras 3 etapas
                lead_ids = self.lead_model.search(
                    [('stage_id', '=', stage['id'])],
                    limit=20
                )
                if lead_ids:
                    self.lead_model.read(
                        lead_ids,
                        ['name', 'contact_name', 'email_from', 'phone']
                    )
        except Exception as e:
            pass

    @task(5)
    def read_partners_for_leads(self):
        """
        Lee contactos relacionados con leads.
        Peso: 5 (moderado)
        """
        try:
            # Buscar partners que son clientes
            partner_ids = self.partner_model.search(
                [('customer_rank', '>', 0)],
                limit=30
            )
            if partner_ids:
                self.partner_model.read(
                    partner_ids,
                    ['name', 'email', 'phone', 'opportunity_count']
                )
        except Exception as e:
            pass

    @task(3)
    def search_leads_by_user(self):
        """
        Busca leads asignados a usuarios específicos.
        Peso: 3 (poco frecuente)
        """
        try:
            lead_ids = self.lead_model.search(
                [('user_id', '!=', False), ('type', '=', 'opportunity')],
                limit=40
            )
            if lead_ids:
                self.lead_model.read(
                    lead_ids,
                    ['name', 'user_id', 'stage_id', 'expected_revenue']
                )
        except Exception as e:
            pass

    @task(2)
    def count_leads_by_stage(self):
        """
        Cuenta leads por etapa (métricas de dashboard).
        Peso: 2 (raro - usado en dashboards)
        """
        try:
            for stage in self.stages:
                count = self.lead_model.search_count([
                    ('stage_id', '=', stage['id']),
                    ('type', '=', 'opportunity')
                ])
        except Exception as e:
            pass

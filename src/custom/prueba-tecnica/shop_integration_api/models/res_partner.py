import re

from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _shop_api_normalize_vat(self, vat):
        """«J-12345678-9», «j 12345678 9» y «J123456789» son el mismo RIF."""
        return re.sub(r"[^A-Za-z0-9]", "", vat or "").upper()

    @api.model
    def _shop_api_find_by_vat(self, vat):
        """Clientes (entidad comercial) con ese RIF que el usuario actual puede ver."""
        normalized = self._shop_api_normalize_vat(vat)
        if not normalized:
            return self.browse()
        self.flush_model(["vat", "active"])
        self.env.cr.execute(
            """
            SELECT id FROM res_partner
             WHERE active AND vat IS NOT NULL
               AND upper(regexp_replace(vat, '[^A-Za-z0-9]', '', 'g')) = %s
            """,
            [normalized],
        )
        ids = [row[0] for row in self.env.cr.fetchall()]
        # search() aplica las reglas de registro del usuario de la integración.
        return self.search([("id", "in", ids)]).commercial_partner_id

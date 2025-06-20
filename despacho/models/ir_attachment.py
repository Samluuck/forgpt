from odoo import models, fields, api


class Attachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        # Detectar si se está accediendo desde un modelo controlado
        modelos_despacho = [
            'despacho.documento',
            'despacho.documento_previo',
            'despacho.documento_oficializacion'
        ]
        res_model = self.env.context.get('default_res_model') or self.env.context.get('active_model')

        has_res_field = any(
            term[0] == 'res_field'
            for term in domain
            if isinstance(term, (list, tuple)) and len(term) > 1
        )

        if res_model in modelos_despacho and not has_res_field:
            domain = [('res_field', '=', False)] + domain

        return super()._search(domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)

    def _filter_access_rules(self, operation):
        if self.env.is_superuser():
            return self
        return super()._filter_access_rules(operation)

    def check(self, mode='read', **kwargs):
        if self.env.is_superuser():
            return True
        return super().check(mode, **kwargs)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('res_model') and vals.get('res_id'):
                self.check('create')
        return super().create(vals_list)

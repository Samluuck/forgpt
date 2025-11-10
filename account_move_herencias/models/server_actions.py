from odoo import models

class AccountMoveMassDraft(models.Model):
    _inherit = 'account.move'

    def action_mass_move_to_draft(self):
        valid_types = ['in_invoice', 'out_invoice']
        records_to_process = self.filtered(lambda m: m.move_type in valid_types and m.state == 'posted')

        batch_size = 50
        total = len(records_to_process)
        processed = 0

        for i in range(0, len(records_to_process), batch_size):
            batch = records_to_process[i:i+batch_size]
            for move in batch:
                for ln in move.line_ids:
                    if ln.matched_debit_ids or ln.matched_credit_ids:
                        ln.remove_move_reconcile()
                move.with_context(force_cancel=True, skip_account_move_validations=True).button_draft()
            self.env.cr.commit()
            processed += len(batch)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Proceso completado",
                "message": f"{processed} facturas pasaron a borrador correctamente.",
                "sticky": False,
            }
        }
from odoo import models

class AccountMoveMassDraft(models.Model):
    _inherit = 'account.move'

    def action_mass_move_to_draft(self):
        valid_types = ['in_invoice', 'out_invoice']
        records_to_process = self.filtered(lambda m: m.move_type in valid_types and m.state == 'posted')

        batch_size = 50
        total = len(records_to_process)
        processed = 0

        for i in range(0, len(records_to_process), batch_size):
            batch = records_to_process[i:i+batch_size]
            for move in batch:
                for ln in move.line_ids:
                    if ln.matched_debit_ids or ln.matched_credit_ids:
                        ln.remove_move_reconcile()
                move.with_context(force_cancel=True, skip_account_move_validations=True).button_draft()
            self.env.cr.commit()
            processed += len(batch)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Proceso completado",
                "message": f"{processed} facturas pasaron a borrador correctamente.",
                "sticky": False,
            }
        }

from odoo import models, api

class RecomputeSalaryServerAction(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def recompute_salary_components(self):
        """
        Recalcula el Salario diario y Salario hora para todos los contratos teniendo en cuenta el salario mensual (wage).
        Este método puede ser llamado desde una acción de servidor.
        """
        # Manejar casos donde no hay contratos
        contracts = self.search([])
        if not contracts:
            return {'type': 'ir.actions.client', 'tag': 'reload'}

        for contract in contracts:
            try:
                contract._compute_salary_components()
            except Exception as e:
                # Manejar errores en registros individuales para no interrumpir el proceso completo
                self.env.cr.rollback()  # Revertir cambios si ocurre un error
                _logger.error(f"Error al calcular componentes para contrato {contract.id}: {str(e)}")
                continue

        self.env.cr.commit()  # Confirmar cambios
        return {'type': 'ir.actions.client', 'tag': 'reload'}

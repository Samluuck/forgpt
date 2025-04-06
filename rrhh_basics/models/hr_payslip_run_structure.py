# -*- coding: utf-8 -*-
from odoo import api, fields, models

class HrPayslipEmployee(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    # Campo booleano para indicar que solo queremos empleados con la misma estructura del campo structure_id
    only_same_structure = fields.Boolean(
        string="Solo empleados con la misma estructura",
        help="Si está activo, solo se generarán nóminas para los empleados cuyos contratos tengan la estructura salarial seleccionada."
    )

    def compute_sheet(self):
        """
        Se hereda/reescribe este método para filtrar los empleados
        según la estructura salarial seleccionada, si el check está activo.
        """
        self.ensure_one()

        # Estructura seleccionada en el wizard (hr.payroll.structure)
        selected_structure = self.structure_id

        # Si el checkbox está activo y tenemos una estructura seleccionada,
        # se filtrarán solo los empleados que en su contrato tengan
        # un structure_type_id cuyo default_struct_id sea la misma estructura.
        if self.only_same_structure and selected_structure:
            filtered_employees = self.employee_ids.filtered(
                lambda emp: emp.contract_id
                and emp.contract_id.structure_type_id
                and emp.contract_id.structure_type_id.default_struct_id
                and emp.contract_id.structure_type_id.default_struct_id == selected_structure
            )
            self.employee_ids = filtered_employees

        # Llamamos a la lógica original para generar la nómina
        res = super(HrPayslipEmployee, self).compute_sheet()
        return res

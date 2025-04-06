import logging
import base64
import tempfile as tmp
from datetime import datetime
from time import mktime

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class HrPayRollTxtWizard(models.TransientModel):
    _name = "hr_payroll_txt_wizard"
    name = fields.Char('Name')
    state = fields.Selection([('view', 'View'), ('get', 'Get')], default='view')
    data = fields.Binary('File', readonly=True)

    def get_file_txt(self):
        print("########################   def get_file_txt(self):    ##################################")
        payroll_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
        buf_file = None
        if payroll_run:
            print("######################  if payroll_run:   ##########################################")
            dt = datetime.now()
            tm = mktime(dt.timetuple())
            file_name = '{0}_{1}.txt'.format(payroll_run.id, tm)
            file_with_path = '{0}/{1}'.format(tmp.gettempdir(), file_name)
            query = """
                SELECT DISTINCT ON (e.id)
                    COALESCE(rc.nro_patronal_ips, '0') as nro_patronal,
                    e.numero_de_asegurado as asegurado,
                    e.identification_id as ci,
                    e.name as nombre,
                    upper(e.categoria_de_ips) as categoria,
                    (SELECT COALESCE(SUM(hrpwd.number_of_days), 0)
                     FROM hr_payslip_worked_days hrpwd
                     INNER JOIN hr_work_entry_type hrwet ON hrwet.id = hrpwd.work_entry_type_id
                     WHERE hrwet.code IN ('LEAVE90', 'LEAVE110', 'OUT', 'VAC', 'MAT')
                     AND hrpwd.payslip_id = p.id) as dias_restar,
                    cast(round(COALESCE(FLOOR(SUM(total) OVER (PARTITION BY e.id)), 0) * (100 / 9)) as int) as total,
                    cast(extract(month from pr.date_end) as varchar) || cast(extract(year from pr.date_end) as varchar) as fecha_cierre,
                    '',
                    cast((c.wage) as int) as salario
                FROM hr_payslip_run pr
                INNER JOIN hr_payslip p ON p.payslip_run_id = pr.id
                INNER JOIN hr_employee e ON e.id = p.employee_id
                INNER JOIN hr_payslip_line pl ON p.id = pl.slip_id
                INNER JOIN res_company rc ON e.company_id = rc.id
                INNER JOIN hr_contract c ON c.id = p.contract_id
                WHERE pr.id = %s



            """

            self.env.cr.execute(query, (payroll_run.id,))
            rs = self.env.cr.fetchall()

            if rs:
                with open(file_with_path, "w") as f:
                    for line in rs:
                        print("########################## for line in rs:")

                        # Cálculo de la diferencia entre 30 y los días de ausencia
                        dias_restar = line[5] or 0  # Obtener el valor de los días de ausencia
                        print("dias a restar",dias_restar)
                        dias_trabajados = 30 - dias_restar
                        print("dias trabajados",dias_trabajados)

                        txt_value = """{0} , {1} , {2}  , {3} , {4} , {5} , {6} , {7} , {8} , {9} """.format(
                            line[0], line[1], line[2], line[3], line[4], dias_trabajados, line[6], line[7], line[8],
                            line[9]
                        )
                        f.write("{0}\n".format(txt_value.strip()))
                        print(*line)
            else:
                # Agregar un mensaje o un valor predeterminado al archivo cuando la consulta está vacía
                default_value = "No se encontraron registros."
                with open(file_with_path, "w") as f:
                    f.write(default_value)

            with open(file_with_path, "rb") as f:
                buf_file = base64.b64encode(f.read())
            name = "Archivo_IPS.txt"
            self.write({'state': 'get', 'data': buf_file, 'name': name})

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr_payroll_txt_wizard',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'views': [(False, 'form')],
                'target': 'new',
            }

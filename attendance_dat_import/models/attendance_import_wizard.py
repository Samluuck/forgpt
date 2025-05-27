from odoo import models, fields, api
from io import StringIO
import base64
from datetime import datetime, timedelta
from collections import defaultdict

class AttendanceImportWizard(models.TransientModel):
    _name = 'attendance.import.wizard'
    _description = 'Wizard para importar asistencias desde archivo .dat'

    file_data = fields.Binary(string='Archivo .dat', required=True)

    def action_import(self):
        decoded = base64.b64decode(self.file_data).decode('utf-8')
        lines = decoded.strip().split('\n')

        logs = defaultdict(list)

        for line in lines:
            parts = line.strip().split()
            if len(parts) < 4:
                continue

            emp_id = parts[0]
            type_code = parts[1]
            timestamp_str = parts[2] + ' ' + parts[3]
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except Exception:
                continue

            logs[emp_id].append((timestamp, int(type_code)))

        for emp_cedula, entries in logs.items():
            employee = self.env['hr.employee'].search([('identification_id', '=', emp_cedula)], limit=1)
            if not employee:
                continue

            entries.sort()
            sessions = []
            current = []

            for timestamp, code in entries:
                if code in [0, 1]:
                    if code == 0:
                        current = [timestamp, None]
                    elif code == 1 and current:
                        current[1] = timestamp
                        sessions.append(tuple(current))
                        current = []
                elif code == 255:
                    if not current:
                        current = [timestamp, None]
                    else:
                        current[1] = timestamp
                        sessions.append(tuple(current))
                        current = []

            # Filtrado de sesiones (separar si supera las 14h)
            for session in sessions:
                check_in, check_out = session
                if check_out and (check_out - check_in).total_seconds() > 14 * 3600:
                    continue  # ignoramos sesiones inválidas
                vals = {
                    'employee_id': employee.id,
                    'check_in': check_in,
                    'check_out': check_out or False
                }
                self.env['hr.attendance'].create(vals)

        return {'type': 'ir.actions.act_window_close'}

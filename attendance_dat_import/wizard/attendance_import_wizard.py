from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import base64

_logger = logging.getLogger(__name__)

class AttendanceImportWizard(models.TransientModel):
    _name = 'attendance.import.wizard'
    _description = 'Wizard para importar asistencias desde archivo .dat'

    file_data = fields.Binary(string='Archivo .dat', required=True)
    file_name = fields.Char(string='Nombre del archivo')
    result_message = fields.Text(string="Resultado", readonly=True)

    def _parse_dat_line(self, line):
        """Parsea una línea del archivo .dat según el formato especificado"""
        if len(line) < 65:
            return None
            
        try:
            # Extracción de datos según posición fija
            emp_cedula = line[7:14].strip()
            date_str = f"{line[16:20]}-{line[21:23]}-{line[24:26]}"
            time_str = f"{line[27:29]}:{line[30:32]}:{line[33:35]}"
            event_type = line[48]  # 0,1,4,5,255
            
            # Validación básica
            if not emp_cedula or not date_str or not time_str or not event_type:
                return None
                
            return {
                'emp_cedula': emp_cedula,
                'timestamp': f"{date_str} {time_str}",
                'event_type': event_type
            }
        except Exception:
            return None

    def _process_entries(self, logs):
        """Procesa las entradas para crear sesiones de asistencia"""
        sessions = []
        for emp_cedula, entries in logs.items():
            entries.sort(key=lambda x: x['timestamp'])
            
            current_session = None
            for entry in entries:
                if entry['event_type'] in ['0', '4']:  # Entrada
                    if current_session and current_session['check_out'] is None:
                        # Cerrar sesión anterior sin salida
                        current_session['check_out'] = entry['timestamp']
                        sessions.append(current_session)
                    current_session = {
                        'emp_cedula': emp_cedula,
                        'check_in': entry['timestamp'],
                        'check_out': None
                    }
                elif entry['event_type'] in ['1', '5']:  # Salida
                    if current_session:
                        current_session['check_out'] = entry['timestamp']
                        sessions.append(current_session)
                        current_session = None
                    else:
                        # Salida sin entrada previa, crear sesión mínima
                        sessions.append({
                            'emp_cedula': emp_cedula,
                            'check_in': entry['timestamp'],
                            'check_out': entry['timestamp']
                        })
                elif entry['event_type'] == '255':  # Indeterminado
                    if not current_session:
                        current_session = {
                            'emp_cedula': emp_cedula,
                            'check_in': entry['timestamp'],
                            'check_out': None
                        }
                    else:
                        current_session['check_out'] = entry['timestamp']
                        sessions.append(current_session)
                        current_session = None
            
            # Agregar última sesión si queda abierta
            if current_session and current_session['check_out'] is None:
                sessions.append(current_session)
                
        return sessions

    def _validate_session(self, session, employee):
        """Valida una sesión antes de crear el registro"""
        check_in = datetime.strptime(session['check_in'], '%Y-%m-%d %H:%M:%S')
        check_out = datetime.strptime(session['check_out'], '%Y-%m-%d %H:%M:%S') if session['check_out'] else None
        
        # Validar duración máxima (14 horas)
        if check_out and (check_out - check_in).total_seconds() > 14 * 3600:
            return False
            
        # Validar si ya existe un registro similar
        domain = [
            ('employee_id', '=', employee.id),
            ('check_in', '<=', check_out or check_in + timedelta(hours=24)),
            ('check_out', '>=', check_in)
        ]
        existing = self.env['hr.attendance'].search_count(domain)
        
        return existing == 0

    def action_import(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Por favor seleccione un archivo para importar"))

        try:
            decoded_data = base64.b64decode(self.file_data).decode('utf-8')
            lines = decoded_data.strip().split('\n')
        except Exception as e:
            raise UserError(_("Error al procesar el archivo: %s") % str(e))

        # Estadísticas
        stats = {
            'total_lines': len(lines),
            'processed': 0,
            'created': 0,
            'invalid_employees': 0,
            'invalid_sessions': 0,
            'invalid_lines': 0,
            'duplicated': 0
        }

        # Procesar archivo
        logs = defaultdict(list)
        for line in lines:
            parsed = self._parse_dat_line(line)
            if not parsed:
                stats['invalid_lines'] += 1
                continue
                
            logs[parsed['emp_cedula']].append(parsed)
            stats['processed'] += 1

        # Obtener todos los empleados de una vez
        employees = self.env['hr.employee'].search([])
        emp_dict = {emp.identification_id: emp for emp in employees if emp.identification_id}

        # Procesar sesiones
        sessions = self._process_entries(logs)
        attendance_vals = []
        
        for session in sessions:
            employee = emp_dict.get(session['emp_cedula'])
            if not employee:
                stats['invalid_employees'] += 1
                continue
                
            if not self._validate_session(session, employee):
                stats['duplicated'] += 1
                continue
                
            attendance_vals.append({
                'employee_id': employee.id,
                'check_in': session['check_in'],
                'check_out': session['check_out'] or False
            })

        # Crear registros masivamente
        if attendance_vals:
            self.env['hr.attendance'].create(attendance_vals)
            stats['created'] = len(attendance_vals)

        # Generar mensaje de resultado
        result_msg = _("""
        Resultado de la importación:
        - Líneas totales procesadas: %(total_lines)d
        - Líneas válidas: %(processed)d
        - Asistencias creadas: %(created)d
        - Empleados no encontrados: %(invalid_employees)d
        - Registros duplicados/omitidos: %(duplicated)d
        - Líneas inválidas: %(invalid_lines)d
        """) % stats

        self.result_message = result_msg

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
from odoo import fields, models, api


class AntuxDataHubLine(models.Model):
    _name = 'antux.datahub.line'
    _description = 'Data Hub - Registro Canónico'
    _order = 'last_name, first_name'

    # -------------------------------------------------
    # RELACIÓN CON EL LOTE
    # -------------------------------------------------
    batch_id = fields.Many2one(
        'antux.datahub.batch',
        required=True,
        ondelete='cascade'
    )

    company_id = fields.Many2one(
        'res.company',
        related='batch_id.company_id',
        store=True,
        readonly=True
    )

    period_id = fields.Many2one(
        'antux.datahub.period',
        related='batch_id.period_id',
        store=True,
        readonly=True
    )

    # -------------------------------------------------
    # IDENTIFICACIÓN CANÓNICA
    # -------------------------------------------------
    ci_number = fields.Char('Cédula', required=True)
    first_name = fields.Char('Nombres', required=True)
    last_name = fields.Char('Apellidos', required=True)
    worker_type = fields.Char('Tipo de trabajador')
    job_title = fields.Char('Cargo')

    # -------------------------------------------------
    # DATOS LABORALES
    # -------------------------------------------------
    days_worked = fields.Integer('Días trabajados')
    salary_base = fields.Float('Salario Básico')
    salary_total = fields.Float('Salario Total')
    
    # -------------------------------------------------
    # DATOS RECIBO SALARIAL
    # -------------------------------------------------
    other_income = fields.Float('Otros Ingresos')
    family_bonus = fields.Float('Bonificación Familiar')
    aguinaldo = fields.Float('Aguinaldo')
    ips_amount = fields.Float('Retención IPS')
    other_discounts = fields.Float('Otros Descuentos')

    # -------------------------------------------------
    # DATOS IPS
    # -------------------------------------------------
    insured_number = fields.Char('Nro Asegurado')
    patronal_number = fields.Char('Nro Patronal')
    payment_month_year = fields.Char('Mes/Año de Pago')   
    activity_code = fields.Char('Cod. Actividad')

    # -------------------------------------------------
    # DATOS Empleados Obreros                           
    # -------------------------------------------------
    sex = fields.Char('Sexo')
    civil_status = fields.Char('Estado Civil')
    fecha_nacimiento = fields.Date('Fecha de Nacimiento')
    nationality = fields.Char('Nacionalidad')
    domicilio   = fields.Char('Domicilio')
    fecha_menor = fields.Date('Fecha de Menor')
    hijos_menor = fields.Integer('Hijos Menor')
    profession = fields.Char('Profesión')
    entry_date = fields.Date('Fecha de Entrada')
    work_schedule = fields.Char('Horario de Trabajo')
    children_under_18 = fields.Integer('Hijos Menores')
    children_with_different_abilities = fields.Integer('Menores con Capacidad Diferente')
    children_educated = fields.Integer('Menores Escolarizados')
    exit_date = fields.Date('Fecha de Salida')
    exit_reason = fields.Text('Motivo de Salida')
    state = fields.Char('Estado')

    dias_vacaciones = fields.Integer('Días Vacaciones')
    desde_vacaciones = fields.Date('Desde Vacaciones')
    hasta_vacaciones = fields.Date('Hasta Vacaciones')
    remuneracion_vacaciones = fields.Float('Remuneración Vacaciones')
    observaciones_vacaciones = fields.Text('Observaciones Vacaciones')

    def name_get(self):
        result = []
        for record in self:
            name = "[%s] %s %s" % (record.ci_number, record.last_name, record.first_name)
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            # Search by CI number or name
            domain = ['|', '|', ('ci_number', operator, name), ('first_name', operator, name), ('last_name', operator, name)]
            return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return super(AntuxDataHubLine, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
# -*- coding: utf-8 -*-


from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

import odoo.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

# class cierre_de_anho_fiscal(models.Model):
#
#     _inherit = 'account.account.type'
#
#     close_method = fields.Selection(
#         [('none', 'Ninguno'), ('balance', 'Saldo'), ('detail', 'Detalle'), ('unreconciled', 'Sin Conciliar')],
#         'Metodo de Cierre', required=True, help="""Establezca aquí el método que se utilizará para generar las entradas de diario de fin de año para todas las cuentas de este tipo.
#         'Ninguno' significa que no se hará nada.
#   El 'saldo' generalmente se usará para cuentas de efectivo.
#   'Detalle' copiará cada elemento diario existente del año anterior, incluso los conciliados.
#   'Sin Conciliar' copiará solo los elementos del diario que no fueron conciliados en el primer día del nuevo año fiscal. """)

class move_a(models.Model):
    _inherit = 'account.move'

    apertura = fields.Boolean(default=False,string="Es asiento de apertura",copy=False)
    cierre = fields.Boolean(default=False,string="Es asiento de cierre",copy=False)
    resultado = fields.Boolean(default=False,string="Es asiento de resultado",copy=False)

    def renumerar_asientos(self, periodo):
        ## EL CAMPO FECHA DEBE SER LA FECHA DE INICIO DE BUSQUEDA YA QUE LUEGO YO LE SACO EL ANHO PARA PODER CONCATENAR CON LA FECHA DE INICIO DEL ANHO Y LA FECHA FINAL DEL ANHO, ASI QUE ES IMPORTANTE QUE LE PONGAS
        # fecha = datetime.strptime(self.date, "%Y-%m-%d")

        anio = periodo
        fecha_start = str(anio) + '-01-01'
        fecha_fin = str(anio) + '-12-31'
        # fecha_start = "'" + fecha_start + "'"
        # fecha_fin = "'" + fecha_fin + "'"
        if self._context.get('company_id'):
            company_id=self._context.get('company_id')
        else:
            company_id=self.env.company
        asientos = self.env['account.move'].search([('date','>=',fecha_start),('date','<=',fecha_fin),('company_id','=',company_id.id),('state','=','posted'),('apertura','!=',True),('cierre','!=',True),('resultado','!=',True)])
        _logger.info('renumera2 %s company %s ' % (len(asientos),company_id.name))
        # cr = self._cr
        # cr.execute(
        #     'select id, date from account_move where date >= %s and date <= %s and state = %s order by date, id' % (
        #         fecha_start, fecha_fin, "'posted'"))
        # asientos = cr.fetchall()

        as_ape = self.env['account.move'].search([('date','>=',fecha_start),('date','<=',fecha_fin),('state','=','posted'),('apertura','=',True)])
        as_cie = self.env['account.move'].search([('date','>=',fecha_start),('date','<=',fecha_fin),('state','=','posted'),('cierre','=',True)])
        as_res = self.env['account.move'].search([('date','>=',fecha_start),('date','<=',fecha_fin),('state','=','posted'),('resultado','=',True)])
        secuencia = 1
        if as_ape:
            for ape in as_ape:
		
                ape.write({'num_asiento': secuencia})
                secuencia += 1

        for asi in asientos.sorted(key=lambda x:x.date):
            if len(asi.line_ids.filtered(lambda r: r.balance != 0)) > 1:
                asi.write({'num_asiento': secuencia})
                secuencia += 1
        if as_res:
            for resu in as_res:
                resu.write({'num_asiento': secuencia})
                secuencia += 1
        if as_cie:
            for cie in as_cie:
                cie.write({'num_asiento': secuencia})
                secuencia += 1


class account_fiscalyear_close(models.TransientModel):
    """
    Closes Account Fiscalyear and Generate Opening entries for New Fiscalyear
    """
    _name = 'account.fiscalyear.close'
    _description = 'Fiscalyear Close'

    fy_id = fields.Integer( 'Año a Cerrar', required=True, help="Select a Fiscal year to close")
    fy2_id = fields.Integer( 'Año a Abrir', required=True)
    journal_id = fields.Many2one('account.journal', 'Diario de Operaciones', required=True, help='The best practice here is to use a journal dedicated to contain the opening entries of all fiscal years. Note that you should define it with default debit/credit accounts, of type \'situation\' and with a centralized counterpart.')
    # period_id = fields.Many2one('account.period', 'Opening Entries Period', required=True)
    report_name =  fields.Char('Name of new entries',size=64, help="Give name of the new entries")
    cuenta_resultado = fields.Many2one('account.account' ,string="Cuenta de Resultados del Ejercicio",required=True)
    crear_apertura = fields.Boolean(default=True,string="Crear asiento de apertura automaticamente")
    # _defaults = {
    #     'report_name': lambda self, cr, uid, context: _('End of Fiscal Year Entry'),
    # }

    @api.onchange('fy_id')
    def anio_fiscal(self):
        if self.fy_id:
            self.fy2_id = self.fy_id + 1

    # @api.multi
    def generar_asientos(self):

        resu=self.asiento_perdida_ganancia()
        # self.asiento_apertura()
        self.asiento_cierre(resu)

    # @api.multi
    def asiento_reapertura_reverso(self,move):
        for mov in move:
            # rever = mov.reverse_moves(date=mov.reverse_date, auto=True)
            rever = mov._reverse_moves()
            _logger.info('aa %s' % rever)
            for rev in rever:
                # asien = self.env['account.move'].browse(rev)
                asien=rev

                asien.write({'ref':'Apertura de Ejercicio Fiscal','num_asiento':1,'apertura':True,'cierre':False})
                for lineas in asien.line_ids:
                    lineas.write({'name':'Apertura de Ejercicio Fiscal'})
    # @api.multi
    def asiento_apertura(self):
        obj_acc_move = self.env['account.move']
        new_journal = self.journal_id
        company_id = new_journal.company_id.id

        # if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
        #     raise ValidationError('El diario debe contener cuentas de debito y credito')

        fecha_inicial = str(self.fy_id) + '-01-01'
        fecha_final = str(self.fy_id) + '-12-31'
        fecha_apertura = str(self.fy2_id) + '-01-01'

        vals = {
            'name': '/',
            'ref': 'Apertura de Ejercicio Fiscal ' + str(self.fy2_id),
            'date': fecha_apertura,
            'journal_id': new_journal.id,
        }
        move_id = obj_acc_move.create(vals)

        # Se netean las cuentas que no son A cobrar ni a pagar
        cr = self.env.cr
        cr.execute("""
                                        INSERT INTO account_move_line (
                                             name, create_uid, create_date, write_uid, write_date,
                                             statement_id, journal_id, currency_id, date_maturity,
                                             partner_id, debit,  credit,
                                             ref, account_id, date, move_id, amount_currency, company_id,balance)
                                          (select %s,%s,%s,%s,%s,
                	                        null, %s,case when aml.currency_id in (null,%s) then null else aml.currency_id end as moneda,%s,
                	                        null, case when sum(debit-credit)>0 then sum(debit-credit) else 0 end as debe ,case when sum(debit-credit)<0 then sum(credit-debit) else 0 end as haber,
                                            %s,aml.account_id,%s,%s,round(sum(amount_currency),2),%s,(sum(debit)-sum(credit))
                                        from account_account aa, account_move_line aml, account_move am, account_account_type aat
                                        where am.state='posted' and  aa.user_type_id=aat.id and aat.type not in  ('receivable','payable') and aat.include_initial_balance=True and am.company_id=%s and aml.move_id=am.id and aml.account_id=aa.id  and am.date between %s and %s
                                        group by aml.account_id,moneda,aa.code

                                        having sum(credit-debit) <> 0
                                        order by aa.code asc) """, (
            'Apertura ' + str(self.fy2_id), self.env.user.id, datetime.now(), self.env.user.id, datetime.now(),
            new_journal.id,
            self.env.company.currency_id.id, fecha_apertura,  ' ', fecha_apertura, move_id.id,
            self.env.company.id, self.env.company.id, fecha_inicial, fecha_final))

        # Se netean las cuentas A cobrar y a pagar con partner_id
        cr = self.env.cr
        cr.execute("""
                                                INSERT INTO account_move_line (
                                                     name, create_uid, create_date, write_uid, write_date,
                                                     statement_id, journal_id, currency_id, date_maturity,
                                                     partner_id, debit,  credit,
                                                     ref, account_id, date, move_id, amount_currency, company_id,balance)
                                                  (select %s,%s,%s,%s,%s,
                        	                        null, %s,case when aml.currency_id in (null,%s) then null else aml.currency_id end as moneda,%s,
                        	                        aml.partner_id, case when sum(debit-credit)>0 then sum(debit-credit) else 0 end as debe ,case when sum(debit-credit)<0 then sum(credit-debit) else 0 end as haber,
                                                    %s,aml.account_id,%s,%s,round(sum(amount_currency),2),%s,(sum(debit)-sum(credit))
                                                from account_account aa,res_partner rp, account_move_line aml, account_move am, account_account_type aat
                                                where am.state='posted' and rp.id=aml.partner_id and  aa.user_type_id=aat.id and aat.type in ('receivable','payable') and aat.include_initial_balance=True and am.company_id=%s and aml.move_id=am.id and aml.account_id=aa.id  and am.date between %s and %s
                                                group by aml.account_id,moneda,aa.code,aml.partner_id
                                                having sum(credit-debit) <> 0
                                                order by aa.code asc)""", (
            'Apertura ' + str(self.fy2_id), self.env.user.id, datetime.now(), self.env.user.id, datetime.now(),new_journal.id,
            self.env.company.currency_id.id, fecha_apertura, ' ', fecha_apertura, move_id.id,
            self.env.company.id, self.env.company.id, fecha_inicial, fecha_final))
        # Se netean las cuentas  A cobrar y a pagar que no tienen partner_id
        cr = self.env.cr
        cr.execute("""
                                                INSERT INTO account_move_line (
                                                     name, create_uid, create_date, write_uid, write_date,
                                                     statement_id, journal_id, currency_id, date_maturity,
                                                     partner_id, debit,  credit,
                                                     ref, account_id, date, move_id, amount_currency, company_id,balance)
                                                  (select %s,%s,%s,%s,%s,
                        	                        null, %s,case when aml.currency_id in (null,%s) then null else aml.currency_id end as moneda,%s,
                        	                        null, case when sum(debit-credit)>0 then sum(debit-credit) else 0 end as debe ,case when sum(debit-credit)<0 then sum(credit-debit) else 0 end as haber,
                                                    %s,aml.account_id,%s,%s,round(sum(amount_currency),2),%s,(sum(debit)-sum(credit))
                                                from account_account aa, account_move_line aml, account_move am, account_account_type aat
                                                where am.state='posted' and aml.partner_id is null and  aa.user_type_id=aat.id and aat.type in ('receivable','payable') and aat.include_initial_balance=True and am.company_id=%s and aml.move_id=am.id and aml.account_id=aa.id  and am.date between %s and %s
                                                group by aml.account_id,moneda,aa.code

                                                having sum(credit-debit) <> 0
                                                order by aa.code asc) """, (
            'Apertura ' + str(self.fy2_id), self.env.user.id, datetime.now(), self.env.user.id, datetime.now(),
            new_journal.id,
            self.env.company.currency_id.id, fecha_apertura, ' ', fecha_apertura, move_id.id,
            self.env.company.id, self.env.company.id, fecha_inicial, fecha_final))

        for move in move_id:
            total = 0.0
            for line in move.line_ids:
                total += line.debit
            move.sudo().write({'amount_total': total})

        # move_id.post()

    # @api.multi
    def asiento_cierre(self,resultado=None):
        obj_acc_move = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        new_journal = self.journal_id
        company_id = new_journal.company_id.id

        # if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
        #     raise ValidationError('El diario debe contener cuentas de debito y credito')

        fecha_inicial = str(self.fy_id) + '-01-01'
        fecha_final = str(self.fy_id) + '-12-31'
        fecha_apertura = str(self.fy2_id) + '-01-01'
        fecha_reversa = datetime.strptime(str(fecha_final), '%Y-%m-%d') + timedelta(days=1)

        vals = {
            'name': '/',
            'ref': 'Cierre de Ejercicio Fiscal '+ str(self.fy_id),
            'date': fecha_final,
            'journal_id': new_journal.id,
            'cierre':True,
            # 'reverse_date': fecha_reversa,
        }

        move_id = obj_acc_move.create(vals)

        account_obj = self.env['account.account'].search([('user_type_id', 'not in', (17, 15, 16, 14, 13))])
        account_result = account_obj.mapped('id')
        obj_move_line = self.env['account.move.line'].search(
            [('date', '>=', fecha_inicial), ('date', '<=', fecha_final), ('parent_state', '=', 'posted'),
             ('account_id', 'in', account_result),('company_id','=',self.env.company.id)])

        cuentas_eerr = obj_move_line.mapped('account_id')
        for cuentas in cuentas_eerr:
            total_cuenta_debe = sum(obj_move_line.filtered(lambda r: r.account_id == cuentas).mapped('debit'))
            total_cuenta_haber = sum(obj_move_line.filtered(lambda r: r.account_id == cuentas).mapped('credit'))
            total_cuenta=total_cuenta_debe-total_cuenta_haber
            if total_cuenta > 0:
                datos_cierre_eje = {
                    'account_id': cuentas.id,
                    'name': 'Cierre Periodo Fiscal ' + str(self.fy_id),
                    'credit': total_cuenta,
                    # 'partner_id': merchant.id,
                    'move_id': move_id.id}
                linea_cierre = move_line_obj.with_context(check_move_validity=False).create(datos_cierre_eje)
            elif total_cuenta < 0:
                datos_cierre_eje = {
                    'account_id': cuentas.id,
                    'name': 'Cierre Periodo Fiscal ' + str(self.fy_id),
                    'debit': abs(total_cuenta),
                    # 'partner_id': merchant.id,
                    'move_id': move_id.id}
                linea_cierre = move_line_obj.with_context(check_move_validity=False).create(datos_cierre_eje)


        #verificamos asientos de resultado y traemos resultados del ejercicio
        # resu_eje=resultado.line_ids.filtered(lambda r:r.account_id==self.cuenta_resultado)
        #
        # resu_debe=resu_eje.debit
        # resu_haber=resu_eje.credit
        # resultado_ejer = resu_debe - resu_haber
        #
        # if resultado_ejer > 0:
        #     datos_resultado_eje = {
        #         'account_id': self.cuenta_resultado.id,
        #         'name': 'Resultado del Ejercicio ' + str(self.fy_id),
        #         'credit': resultado_ejer,
        #         # 'partner_id': merchant.id,
        #         'move_id': move_id.id}
        #     linea_resultado = move_line_obj.with_context(check_move_validity=False).create(datos_resultado_eje)
        # elif resultado_ejer < 0:
        #     datos_resultado_eje = {
        #     'account_id': self.cuenta_resultado.id,
        #     'name': 'Resultado del Ejercicio ' + str(self.fy_id),
        #     'debit': abs(resultado_ejer),
        #     # 'partner_id': merchant.id,
        #     'move_id': move_id.id}
        #     linea_resultado = move_line_obj.with_context(check_move_validity=False).create(datos_resultado_eje)

        # Se netean las cuentas que no son A cobrar ni a pagara
        # cr = self.env.cr
        # cr.execute("""
        #                         INSERT INTO account_move_line (
        #                              name, create_uid, create_date, write_uid, write_date,
        #                              statement_id, journal_id,  date_maturity,
        #                              partner_id, debit,  credit,
        #                              ref, account_id, date, move_id, amount_currency, company_id,balance,currency_id)
        #                           (select %s,%s,%s,%s,%s,
        # 	                        null, %s,%s,
        # 	                        null,  case when sum(debit-credit)<0 then sum(credit-debit) else 0 end as debe ,case when sum(debit-credit)>0 then sum(debit-credit) else 0 end as haber,
        #                             %s,aml.account_id,%s,%s,case when aa.currency_id is null then 0 else  (round(sum(amount_currency),2))*-1  end,%s,-1*(sum(debit)-sum(credit)),aa.currency_id
        #                         from account_account aa, account_move_line aml, account_move am, account_account_type aat
        #                         where am.state='posted' and  aa.user_type_id=aat.id and aat.type not in  ('receivable','payable') and aat.include_initial_balance=True and am.company_id=%s and aml.move_id=am.id and aml.account_id=aa.id  and am.date between %s and %s
        #                         group by aml.account_id,aa.code,aa.currency_id
        #
        #                         having sum(credit-debit) <> 0
        #                         order by aa.code asc) """, (
        # 'Cierre '+str(self.fy_id), self.env.user.id, datetime.now(), self.env.user.id, datetime.now(), new_journal.id,
        #  fecha_final, ' ', fecha_final, move_id.id,
        # self.env.company.id, self.env.company.id, fecha_inicial, fecha_final))
        #
        # #Se netean las cuentas A cobrar y a pagar
        # cr = self.env.cr
        # cr.execute("""
        #                                 INSERT INTO account_move_line (
        #                                      name, create_uid, create_date, write_uid, write_date,
        #                                      statement_id, journal_id,  date_maturity,
        #                                      debit,  credit,
        #                                      ref, account_id, date, move_id, amount_currency, company_id,balance,currency_id)
        #                                   (select %s,%s,%s,%s,%s,
        #         	                        null, %s,%s,
        #         	                         case when sum(debit-credit)<0 then sum(credit-debit) else 0 end as debe ,case when sum(debit-credit)>0 then sum(debit-credit) else 0 end as haber,
        #                                     %s,aml.account_id,%s,%s,case when aa.currency_id is null then 0 else (round(sum(amount_currency),2))*-1 end,%s,-1*(sum(debit)-sum(credit)),aa.currency_id
        #                                 from account_account aa, account_move_line aml, account_move am, account_account_type aat
        #                                 where am.state='posted'  and  aa.user_type_id=aat.id and aat.type in ('receivable','payable') and aat.include_initial_balance=True and am.company_id=%s and aml.move_id=am.id and aml.account_id=aa.id  and am.date between %s and %s
        #                                 group by aml.account_id,aa.code,aa.currency_id
        #                                 having sum(credit-debit) <> 0
        #                                 order by aa.code asc)""", (
        #     'Cierre ' + str(self.fy_id), self.env.user.id, datetime.now(), self.env.user.id, datetime.now(),new_journal.id,
        #     fecha_final, ' ', fecha_final, move_id.id,
        #     self.env.company.id, self.env.company.id, fecha_inicial, fecha_final))

        # # Se netean las cuentas que  A cobrar y a pagar pero que no tienen partner_id
        # cr = self.env.cr
        # cr.execute("""
        #                                 INSERT INTO account_move_line (
        #                                      name, create_uid, create_date, write_uid, write_date,
        #                                      statement_id, journal_id, date_maturity,
        #                                      partner_id, debit,  credit,
        #                                      ref, account_id, date, move_id, amount_currency, company_id,balance,currency_id)
        #                                   (select %s,%s,%s,%s,%s,
        #         	                        null, %s,%s,
        #         	                        null,  case when sum(debit-credit)<0 then sum(credit-debit) else 0 end as debe ,case when sum(debit-credit)>0 then sum(debit-credit) else 0 end as haber,
        #                                     %s,aml.account_id,%s,%s,case when aa.currency_id is null then 0 else (round(sum(amount_currency),2))*-1 end,%s,-1*(sum(debit)-sum(credit)),aa.currency_id
        #                                 from account_account aa, account_move_line aml, account_move am, account_account_type aat
        #                                 where am.state='posted' and aml.partner_id is null and  aa.user_type_id=aat.id and aat.type in ('receivable','payable') and aat.include_initial_balance=True and am.company_id=%s and aml.move_id=am.id and aml.account_id=aa.id  and am.date between %s and %s
        #                                 group by aml.account_id,aa.code,aa.currency_id
        #
        #                                 having sum(credit-debit) <> 0
        #                                 order by aa.code asc) """, (
        #     'Cierre ' + str(self.fy_id), self.env.user.id, datetime.now(), self.env.user.id, datetime.now(),
        #     new_journal.id,
        #      fecha_final, ' ', fecha_final, move_id.id,
        #     self.env.company.id, self.env.company.id, fecha_inicial, fecha_final))

        for move in move_id:
            total = 0.0
            for line in move.line_ids:
                total += line.debit
            move.sudo().write({'amount_total': total})
        # move_id.post()
        if self.crear_apertura:
            asiento_reve = self.asiento_reapertura_reverso(move_id)

    # @api.multi
    def asiento_perdida_ganancia(self):
        obj_acc_move = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        new_journal = self.journal_id
        company_id = new_journal.company_id.id

        #if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
        #    raise ValidationError('El diario debe contener cuentas de debito y credito')
        if not self.cuenta_resultado:
            raise ValidationError('Debe asignar una cuenta de resultados del ejercicio')
        fecha_inicial = str(self.fy_id) + '-01-01'
        fecha_final = str(self.fy_id) + '-12-31'

        vals = {
            'name': '/',
            'ref': 'Resultado del Ejercicio ' + str(self.fy_id),
            'date': fecha_final,
            'resultado': True,
            'journal_id': new_journal.id,
        }

        # Se crea asiento vacio para luego agregarles las lineas
        move_id = obj_acc_move.create(vals)
        #Traer todas las lineas de asientos ingresos y gastos
        account_obj=self.env['account.account'].search([('user_type_id','in',(17,15,16,14,13))])
        account_result=account_obj.mapped('id')
        obj_move_line=self.env['account.move.line'].search([('date','>=',fecha_inicial),('date','<=',fecha_final),('parent_state','=','posted'),('account_id','in',account_result),('company_id','=',self.env.company.id)])

        ingresos_debe=sum(obj_move_line.filtered(lambda r:r.account_id.user_type_id.id in (17,13,14)).mapped('debit'))
        ingresos_haber=sum(obj_move_line.filtered(lambda r:r.account_id.user_type_id.id in (17,13,14)).mapped('credit'))
        ingresos=abs(ingresos_debe-ingresos_haber)
        gastos_debe=sum(obj_move_line.filtered(lambda r:r.account_id.user_type_id.id in (15,16)).mapped('debit'))
        gastos_haber=sum(obj_move_line.filtered(lambda r:r.account_id.user_type_id.id in (15,16)).mapped('credit'))
        gastos=abs(gastos_debe-gastos_haber)
        resultado=ingresos-gastos

        if resultado>0:
            datos_resultado_eje = {
                'account_id': self.cuenta_resultado.id,
                'name': 'Resultado del Ejercicio ' + str(self.fy_id),
                'credit': resultado,
                # 'partner_id': merchant.id,
                'move_id': move_id.id}
            linea_resultado = move_line_obj.with_context(check_move_validity=False).create(datos_resultado_eje)
        elif resultado<0:
            datos_resultado_eje = {
                'account_id': self.cuenta_resultado.id,
                'name': 'Resultado del Ejercicio ' + str(self.fy_id),
                'debit': abs(resultado),
                # 'partner_id': merchant.id,
                'move_id': move_id.id}
            linea_resultado = move_line_obj.with_context(check_move_validity=False).create(datos_resultado_eje)
        cuentas_eerr=obj_move_line.mapped('account_id')
        for cuentas in cuentas_eerr:
            total_cuenta_debe = sum(obj_move_line.filtered(lambda r: r.account_id == cuentas).mapped('debit'))
            total_cuenta_haber = sum(obj_move_line.filtered(lambda r: r.account_id == cuentas).mapped('credit'))
            total_cuenta = total_cuenta_debe - total_cuenta_haber
            if total_cuenta > 0:
                datos_cierre_eje = {
                    'account_id': cuentas.id,
                    'name': 'Cierre Periodo Fiscal ' + str(self.fy_id),
                    'credit': abs(total_cuenta),
                    # 'partner_id': merchant.id,
                    'move_id': move_id.id}
                linea_cierre = move_line_obj.with_context(check_move_validity=False).create(datos_cierre_eje)
            elif total_cuenta < 0:
                datos_cierre_eje = {
                    'account_id': cuentas.id,
                    'name': 'Cierre Periodo Fiscal ' + str(self.fy_id),
                    'debit': abs(total_cuenta),
                    # 'partner_id': merchant.id,
                    'move_id': move_id.id}
                linea_cierre = move_line_obj.with_context(check_move_validity=False).create(datos_cierre_eje)

        # obj = 'account_move_line'
        # query_line = obj + "date between '" + fecha_inicial + "' and '" + fecha_final + "'"
        # query_line2 = "date between '" + fecha_inicial + "' and '" + fecha_final + "'"
        # raise ValidationError ('qaaa %s' % query_line)
        # create the opening move
        fecha_apertura = str(self.fy2_id) + '-01-01'



        # cr = self._cr

        #Se netean las cuentas de ingresos y egresos
        # a=cr.execute("""
        #                 INSERT INTO account_move_line (
        #                      name, create_uid, create_date, write_uid, write_date,
        #                      statement_id, journal_id, date_maturity,
        #                      partner_id, debit,  credit,
        #                      ref, account_id, date, move_id, amount_currency, company_id,balance)
        #                   (select %s, %s, %s, %s, %s,
	    #                     null, %s, %s ,
	    #                     null, case when sum(debit-credit)<0 then sum(credit-debit) else 0 end as debe ,case when sum(debit-credit)>0 then sum(debit-credit) else 0 end as haber,
        #                     %s,aml.account_id,%s,%s,0,%s,-1*(sum(debit)-sum(credit))
        #                 from account_account aa, account_move_line aml, account_move am, account_account_type aat
        #                 where am.state='posted' and  aa.user_type_id=aat.id and aat.include_initial_balance=False and am.company_id=%s and aml.move_id=am.id and aml.account_id=aa.id  and am.date between %s and %s
        #                 group by aml.account_id,aa.code
        #                 having sum(credit-debit) <> 0
        #                 order by aa.code asc)""",('Resultado '+str(self.fy_id),
        #                                           self.env.user.id,
        #                                           datetime.now(),
        #                                           self.env.user.id,
        #                                           datetime.now(),
        #                                           new_journal.id,
        #                                           # self.env.company.currency_id.id,
        #                                           fecha_final,
        #                                           ' ',
        #                                           fecha_final,
        #                                           move_id.id,
        #                                           self.env.company.id,
        #                                           self.env.company.id,
        #                                           fecha_inicial,
        #                                           fecha_final))
        # # raise ValidationError(move_id)
        # #Se genera la linea de resultado del ejercicio
        # cr.execute("""
        #                         INSERT INTO account_move_line (
        #                              name, create_uid, create_date, write_uid, write_date,
        #                              statement_id, journal_id, date_maturity,
        #                              partner_id, debit,  credit,
        #                              ref, account_id, date, move_id, amount_currency, company_id,balance)
        #                           (select
        #                                 %s,%s,%s,%s,%s,
        #                                     null,%s,%s,
        #                                     null,case when sum(debit-credit)>0 then sum(debit-credit) else 0 end as debe ,case when sum(debit-credit)<0 then sum(credit-debit) else 0 end as haber,
        #                                 %s,%s,%s,%s,0,%s,(sum(debit)-sum(credit))
        #                                 from account_account aa, account_move_line aml, account_move am, account_account_type aat
        #                                 where am.state='posted' and  aa.user_type_id=aat.id and aat.include_initial_balance=False and am.company_id=%s and aml.move_id=am.id and aml.account_id=aa.id  and am.date between %s and %s
        #                                 )""" , ('Resultado del Ejercicio' +str(self.fy_id), self.env.user.id, datetime.now(), self.env.user.id, datetime.now(),
        #                 new_journal.id,  fecha_final, ' ', self.cuenta_resultado.id, fecha_final,
        #                 move_id.id, self.env.company.id, self.env.company.id, fecha_inicial, fecha_final))
        #
        #
        for move in move_id:
            total = 0.0
            for line in move.line_ids:
                total += line.debit
            move.sudo().write({'amount_total': total})
        move_id.post()
        return move_id
    # @api.multi
    def data_save(self):
        """
        This function close account fiscalyear and create entries in new fiscalyear
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Account fiscalyear close state’s IDs

        """
        # def _reconcile_fy_closing(ids):
        #     """
        #     This private function manually do the reconciliation on the account_move_line given as `ids´, and directly
        #     through psql. It's necessary to do it this way because the usual `reconcile()´ function on account.move.line
        #     object is really resource greedy (not supposed to work on reconciliation between thousands of records) and
        #     it does a lot of different computation that are useless in this particular case.
        #     """
        #     #check that the reconcilation concern journal entries from only one company
        #     self.env.cr.execute('select distinct(company_id) from account_move_line where id in %s',(tuple(ids)))
        #     if len(self.env.cr.fetchall()) > 1:
        #         raise ValidationError('The entries to reconcile should belong to the same company.')
        #     r_id = self.env['account.move.reconcile'].create({'type': 'auto', 'opening_reconciliation': True})
        #     self.env.cr.execute('update account_move_line set reconcile_id = %s where id in %s',(r_id, tuple(ids),))
        #     return r_id

        context = None
        # obj_acc_period = self.env['account.period']
        # obj_acc_fiscalyear = self.pool.get('account.fiscalyear')
        obj_acc_journal = self.env['account.journal']
        obj_acc_move = self.env['account.move']
        obj_acc_move_line = self.env['account.move.line']
        obj_acc_account = self.env['account.account']
        # obj_acc_journal_period = self.env['account.journal.period']
        currency_obj = self.env['res.currency']

        data = self

        if context is None:
            context = {}
        # fy_id = data[0].fy_id.id
        #
        # cr.execute("SELECT id FROM account_period WHERE date_stop < (SELECT date_start FROM account_fiscalyear WHERE id = %s)", (str(data[0].fy2_id.id),))
        # fy_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))
        # cr.execute("SELECT id FROM account_period WHERE date_start > (SELECT date_stop FROM account_fiscalyear WHERE id = %s)", (str(fy_id),))
        # fy2_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))
        #
        # if not fy_period_set or not fy2_period_set:
        #     raise osv.except_osv(_('User Error!'), _('The periods to generate opening entries cannot be found.'))
        #
        # period = obj_acc_period.browse(cr, uid, data[0].period_id.id, context=context)
        # new_fyear = obj_acc_fiscalyear.browse(cr, uid, data[0].fy2_id.id, context=context)
        # old_fyear = obj_acc_fiscalyear.browse(cr, uid, fy_id, context=context)

        # new_journal = data[0].journal_id.id
        new_journal = self.journal_id
        company_id = new_journal.company_id.id

        if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
            raise ValidationError('El diario debe contener cuentas de debito y credito')
        # if (not new_journal.centralisation) or new_journal.entry_posted:
        #     raise osv.except_osv(_('User Error!'),
        #             _('The journal must have centralized counterpart without the Skipping draft state option checked.'))

        #delete existing move and move lines if any
        # move_ids = obj_acc_move.search(cr, uid, [
        #     ('journal_id', '=', new_journal.id), ('date', '=', period.id)])
        # if move_ids:
        #     move_line_ids = obj_acc_move_line.search(cr, uid, [('move_id', 'in', move_ids)])
        #     obj_acc_move_line._remove_move_reconcile(cr, uid, move_line_ids, opening_reconciliation=True, context=context)
        #     obj_acc_move_line.unlink(cr, uid, move_line_ids, context=context)
        #     obj_acc_move.unlink(cr, uid, move_ids, context=context)

        # cr.execute("SELECT id FROM account_fiscalyear WHERE date_stop < %s", (str(new_fyear.date_start),))
        # result = cr.dictfetchall()
        # fy_ids = [x['id'] for x in result]
       # """           query = obj+".state <> 'draft' AND "+obj+".period_id
       #         IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s)" + where_move_state + where_move_lines_by_date"""
       #  query_line = obj_acc_move_line._query_get(cr, uid,
       #          obj='account_move_line', context={'fiscalyear': fy_ids})
        fecha_inicial = str(self.fy_id) + '-01-01'
        fecha_final = str(self.fy_id) + '-12-31'
        obj='account_move_line'
        query_line =  obj + "date between '" + fecha_inicial + "' and '" + fecha_final +"'"
        query_line2 = "date between '" + fecha_inicial + "' and '" + fecha_final + "'"
        # raise ValidationError ('qaaa %s' % query_line)
        #create the opening move
        fecha_apertura = str (self.fy2_id) + '-01-01'

        vals = {
            'name': '/',
            'ref': 'Asiento de Apertura',
            'date': fecha_apertura,
            'journal_id': new_journal.id,
        }
        move_id = obj_acc_move.create(vals)

        #1. report of the accounts with defferal method == 'unreconciled'
        cr = self.env.cr
        cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type_id = t.id)
            WHERE a.deprecated = False
              AND t.type not in ('view')
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'unreconciled', ))
        account_ids = map(lambda x: x[0], cr.fetchall())
        if account_ids:
            cr.execute("""
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, currency_id, date_maturity,
                     partner_id, blocked, credit,  debit,
                     ref, account_id, date, move_id, amount_currency,
                     quantity, product_id, company_id)
                  (SELECT name, create_uid, create_date, write_uid, write_date,
                     statement_id, %s,currency_id, date_maturity, partner_id,
                     blocked, credit, debit, ref, account_id,
                      (%s) AS date, %s, amount_currency, quantity, product_id, company_id
                   FROM account_move_line
                   WHERE account_id IN %s
                     AND date between cast('""" + str(fecha_inicial) + """' as date) and cast( '""" + str(fecha_final)+ """' as date)
                     AND full_reconcile_id IS NULL)""", (new_journal.id,  fecha_apertura, move_id.id, tuple(account_ids),))

            #We have also to consider all move_lines that were reconciled
            #on another fiscal year, and report them too
            cr.execute("""
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, currency_id, date_maturity,
                     partner_id, blocked, credit,  debit,
                     ref, account_id,  date, move_id, amount_currency,
                     quantity, product_id, company_id)
                  (SELECT
                     b.name, b.create_uid, b.create_date, b.write_uid, b.write_date,
                     b.statement_id, %s, b.currency_id, b.date_maturity,
                     b.partner_id, b.blocked, b.credit,  b.debit,
                     b.ref, b.account_id, (%s) AS date, %s, b.amount_currency,
                     b.quantity, b.product_id, b.company_id
                     FROM account_move_line b
                     WHERE b.account_id IN %s
                       AND b.full_reconcile_id IS NOT NULL
                       AND b.""" + query_line2 + """
                       AND b.full_reconcile_id IN (SELECT DISTINCT(full_reconcile_id)
                                          FROM account_move_line a
                                          WHERE a.date between '"""+ fecha_inicial +"""' and '"""+ fecha_final + """'))""", (new_journal.id,  fecha_apertura, move_id.id, tuple(account_ids),))

        #2. report of the accounts with defferal method == 'detail'
        # cr.execute('''
        #     SELECT a.id
        #     FROM account_account a
        #     LEFT JOIN account_account_type t ON (a.user_type = t.id)
        #     WHERE a.active
        #       AND a.type not in ('view', 'consolidation')
        #       AND a.company_id = %s
        #       AND t.close_method = %s''', (company_id, 'detail', ))
        # account_ids = map(lambda x: x[0], cr.fetchall())
        #
        # if account_ids:
        #     cr.execute('''
        #         INSERT INTO account_move_line (
        #              name, create_uid, create_date, write_uid, write_date,
        #              statement_id, journal_id, currency_id, date_maturity,
        #              partner_id, blocked, credit, state, debit,
        #              ref, account_id, period_id, date, move_id, amount_currency,
        #              quantity, product_id, company_id)
        #           (SELECT name, create_uid, create_date, write_uid, write_date,
        #              statement_id, %s,currency_id, date_maturity, partner_id,
        #              blocked, credit, 'draft', debit, ref, account_id,
        #              %s, (%s) AS date, %s, amount_currency, quantity, product_id, company_id
        #            FROM account_move_line
        #            WHERE account_id IN %s
        #              AND ''' + query_line + ''')
        #              ''', (new_journal.id, period.id, period.date_start, move_id, tuple(account_ids),))


        #3. report of the accounts with defferal method == 'balance'
        cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type_id = t.id)
            WHERE a.deprecated = False
              AND t.type not in ('view', 'consolidation')
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'balance', ))
        account_ids = map(lambda x: x[0], cr.fetchall())
        cuen = 0
        for account in obj_acc_account.browse(account_ids):
            cuen += 1
        if cuen > 0:

            cr.execute ( """
                    INSERT INTO account_move_line (
                         debit, credit, name, date, move_id, journal_id,
                         account_id, currency_id, amount_currency, company_id,date_maturity)
                         (select case when (sum(debit)-sum(credit)) > 0 then (sum(debit)-sum(credit)) else 0 end,case when (sum(debit)-sum(credit)) < 0 then abs(sum(debit)-sum(credit)) else 0 end , %s , %s, %s, %s ,account_id , coalesce (currency_id, null) , abs(sum(amount_currency)) ,company_id , %s

    from account_move_line where date between '""" + fecha_inicial + """'  and '""" + fecha_final + """' and account_id IN %s group by account_id,currency_id,company_id ) """, (self.report_name,fecha_apertura,move_id.id,new_journal.id,fecha_apertura,tuple(account_ids)))
        query_2nd_part = ""
        # query_2nd_part_args = []
        # for account in obj_acc_account.browse(account_ids):
        #     company_currency_id = self.env.company.currency_id
        #     if not currency_obj.is_zero( company_currency_id, abs(account.balance)):
        #         if query_2nd_part:
        #             query_2nd_part += ','
        #         query_2nd_part += "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        #         query_2nd_part_args += (account.balance > 0 and account.balance or 0.0,
        #                account.balance < 0 and -account.balance or 0.0,
        #                data[0].report_name,
        #                fecha_inicial,
        #                move_id,
        #                new_journal.id,
        #                account.id,
        #                account.currency_id and account.currency_id.id or None,
        #                account.foreign_balance if account.currency_id else 0.0,
        #                account.company_id.id)
        # if cuen > 0:
        #     cr.execute(query_1st_part + query_2nd_part, tuple(query_2nd_part_args))

        #validate and centralize the opening move
        # obj_acc_move.validate( [move_id])

        #reconcile all the move.line of the opening move
        # ids = obj_acc_move_line.search([('journal_id', '=', new_journal.id),
        #     ('date','>=',fecha_inicial),('date','<=',fecha_final)])
        # if ids:
        #     reconcile_id = _reconcile_fy_closing(ids)
        #     #set the creation date of the reconcilation at the first day of the new fiscalyear, in order to have good figures in the aged trial balance
        #     reconcile_id.write({'create_date':fecha_apertura})
        #create the journal.period object and link it to the old fiscalyear
        # new_period = data[0].period_id.id
        # ids = obj_acc_journal_period.search(cr, uid, [('journal_id', '=', new_journal.id), ('period_id', '=', new_period)])
        # if not ids:
        #     ids = [obj_acc_journal_period.create(cr, uid, {
        #            'name': (new_journal.name or '') + ':' + (period.code or ''),
        #            'journal_id': new_journal.id,
        #            'period_id': period.id
        #        })]
        # cr.execute('UPDATE account_fiscalyear ' \
        #             'SET end_journal_period_id = %s ' \
        #             'WHERE id = %s', (ids[0], old_fyear.id))

        return {'type': 'ir.actions.act_window_close'}

account_fiscalyear_close()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

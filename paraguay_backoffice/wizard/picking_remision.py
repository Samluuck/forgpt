# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError


class picking_remision(models.TransientModel):

    _name = 'picking.remision'

    picking_id=fields.Many2one('stock.picking',string="Envio")
    talonario_remision = fields.Many2one('ruc.documentos.timbrados', string="Talonario remision",domain=[('tipo_documento', '=', '2'),('activo','=',True)])
    nro_a_asignar=fields.Char(compute='obtener_nro_remision',string="Esta remision tendrá el numero:")
    agregar_numero_manual = fields.Boolean(string="Agregar Nro. Manualmente?")
    nro_manual = fields.Char(string="Esta remision tendrá el numero:")


                                           
                                           
                                           
    @api.depends('talonario_remision','talonario_remision.nro_actual')
    # @api.one
    def obtener_nro_remision(self):
        if self.talonario_remision:
            fmt = '%Y-%m-%d'

            d1 = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
            # fecha = datetime.strftime(fechas, "%Y/%m/%d")
            # d1 = datetime.strptime(str(datetime.now().date()), fmt)

            d2 = datetime.strptime(str(self.talonario_remision.fecha_final), '%Y-%m-%d')
            d3 = datetime.strptime(str(self.talonario_remision.fecha_inicio), '%Y-%m-%d')
            daysDiff = (d2 - d1).days

            dias_anti = (d3 - d1).days
            # raise ValidationError(self.talonario_remision.suc)
            # raise ValidationError('Timbrado ya se encuentra vencido %s' % daysDiff)
            if daysDiff < 0:
                if not self.agregar_numero_manual:
                    raise ValidationError('Timbrado ya se encuentra vencido.')
            elif dias_anti > 0:
                raise ValidationError('Fecha inicio de timbrado es mayor a la fecha actual')
            suc = self.talonario_remision.suc
            sec = self.talonario_remision.sec
            nro = self.talonario_remision.nro_actual + 1

            nro_s = str(nro)
            cant_nro = len(nro_s)
            if cant_nro == 1:
                nro_final = '000000' + nro_s
            elif cant_nro == 2:
                nro_final = '00000' + nro_s
            elif cant_nro == 3:
                nro_final = '0000' + nro_s
            elif cant_nro == 4:
                nro_final = '000' + nro_s
            elif cant_nro == 5:
                nro_final = '00' + nro_s
            elif cant_nro == 6:
                nro_final = '0' + nro_s
            else:
                nro_final = nro_s

            self.nro_a_asignar = str(suc) + '-' + str(sec) + '-' + str(nro_final)
            self.nro_manual = str(suc) + '-' + str(sec) + '-' + str(nro_final)
        else:
            self.nro_a_asignar = ""



    # @api.multi
    def procesar(self):
        for rec in self.picking_id:
           if self.agregar_numero_manual and self.talonario_remision:
                rec.write({'numero_remision':self.nro_manual,'timbrado_remision':self.talonario_remision.name,'talonario_remision':self.talonario_remision.id})
                                           
           elif self.talonario_remision and not self.agregar_numero_manual:
                fmt = '%Y-%m-%d'

                d1 = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
                # fecha = datetime.strftime(fechas, "%Y/%m/%d")
                # d1 = datetime.strptime(str(datetime.now().date()), fmt)

                d2 = datetime.strptime(str(self.talonario_remision.fecha_final), '%Y-%m-%d')
                d3 = datetime.strptime(str(self.talonario_remision.fecha_inicio), '%Y-%m-%d')
                daysDiff = (d2 - d1).days

                dias_anti = (d3 - d1).days
                # raise ValidationError(self.talonario_remision.suc)
                # raise ValidationError('Timbrado ya se encuentra vencido %s' % daysDiff)
                if daysDiff < 0:
                    raise ValidationError('Timbrado ya se encuentra vencido.')
                elif dias_anti > 0:
                    raise ValidationError('Fecha inicio de timbrado es may(or a la fecha actual')
                suc = self.talonario_remision.suc
                sec = self.talonario_remision.sec
                nro = self.talonario_remision.nro_actual + 1

                nro_s = str(nro)
                cant_nro = len(nro_s)
                if cant_nro == 1:
                    nro_final = '000000' + nro_s
                elif cant_nro == 2:
                    nro_final = '00000' + nro_s
                elif cant_nro == 3:
                    nro_final = '0000' + nro_s
                elif cant_nro == 4:
                    nro_final = '000' + nro_s
                elif cant_nro == 5:
                    nro_final = '00' + nro_s
                elif cant_nro == 6:
                    nro_final = '0' + nro_s
                else:
                    nro_final = nro_s
                remision=str(suc) + '-' + str(sec) + '-' + str(nro_final)
                rec.write({'numero_remision':remision,'timbrado_remision':self.talonario_remision.name,'talonario_remision':self.talonario_remision.id})
                self.talonario_remision.write({'ultimo_nro_utilizado': remision,
                                           'nro_actual': self.talonario_remision.nro_actual + 1})




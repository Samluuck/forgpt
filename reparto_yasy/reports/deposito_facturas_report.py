class ReportDepositoFacturas(models.AbstractModel):
    _name = 'report.reparto_yasy.deposito_facturas_report_template'
    _description = 'Reporte Depósito de Facturas'

    @api.model
    def _get_report_values(self, docids, data=None):
        repartos = self.env['delivery.order'].browse(docids)
        chofer = self.env['res.partner'].browse(data['chofer_id'])
        return {
            'doc_ids': docids,
            'doc_model': 'delivery.order',
            'docs': [{
                'chofer_id': chofer,
                'entregado_a': data['entregado_a'],
                'repartos': repartos,
            }],
        }

{
    "name": "Factura San Fernando",
    "summary": "Reporte de factura pre-impresa para San Fernando",
    "description": "Reporte QWeb personalizado de factura pre-impresa para San Fernando, migrado a Odoo 12.",
    "author": "Migración AI",
    "website": "",
    "category": "Accounting",
    "version": "12.0.1.0.0",
    "depends": ["account"],
    "data": [
        "reports/factura_reports.xml",
        "reports/template_factura.xml"
        # "reports/recibo_reports.xml",
        # "reports/template_recibo.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
} 
{
    'name': 'Tipo de Contratos',
    'version': '15.0.1.1.0',
    'category': 'Generic Modules/Human Resources',
    'summary': """
        Tipo de contratos en el modulo de contratos
    """,
    'description': """Tipo de contratos con menú """,
    'author': 'SATI',
    'company': 'SATI',
    'maintainer': 'SATI',
    'website': 'https://sati.com.py/',
    'depends': ['hr', 'hr_contract', 'rrhh_basics'],
    'data': [
        'security/ir.model.access.csv',
        'reports/report_contract.xml',
        'reports/contract_type_reports.xml',
        'views/contract_view.xml',
        'data/hr_contract_type_data.xml',
    ],
    'installable': True,
    'images': [''],
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}

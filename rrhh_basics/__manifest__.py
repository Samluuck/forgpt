# -*- coding: utf-8 -*-
{
    'name': "RRHH Localización",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "SATI",
    'website': "https://sati.com.py/",

    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'AGPL-3',
    'depends': ['base', 'hr_payroll', 'hr_holidays', 'hr_contract'],
    'data': [
        'views/hr_employee_inh.xml',
        'views/hr_leave_inh.xml',
        'views/hr_legajo_formularios.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'reports/boton_imprimir.xml',
        'reports/recibo_vacacional.xml',
        'security/ir.model.access.csv',
        'reports/leave_report_template.xml',
        'reports/leave_report_view.xml',
        'wizards/attendance_register_wizard.xml',
        'reports/attendance_register_report.xml',
        'reports/attendance_register.xml',
        'views/hr_payslip_run_structure.xml',
        'views/hr_leave_type_form_inh.xml',
        'views/hr_contract_views.xml',
        'views/hr_income_expense_view.xml',
        'views/hr_payslip_structure.xml',
        'data/ir_action_server_data.xml',
    ],

}

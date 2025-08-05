{
    'name': 'Pmant CheckList',
    'version': '1.0',
    'description': 'Módulo para gestionar checklist de mantenimiento - FDCCORP',
    'summary': '',
    'author': 'Yostin Palacios',
    'website': 'https://fdc-corporation.com',
    'license': 'LGPL-3',
    'category': 'service',
    'depends': [
        'base',"pmant", "web", "website", "maintenance",
    ],
    'data': [
        'security/ir.model.access.csv',
        "view/view_form_preguntas.xml",
        "view/view_inherit_equipo.xml",
        "view/web/form_pmant.xml",
        "view/web/sumit_web.xml",
        "view/view_form_plantillas.xml"
    ],
    'auto_install': False,
    'application': False,
}
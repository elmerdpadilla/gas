# -*- coding: utf-8 -*-
{	
	'name' : 'sap_integration',
	'author': 'Grupo Innova',
	'category': 'others',
	'summary': ', ',
	'description': """SAP Integration""",
	'data':[
		'data/account_fiscal_position.xml',
		'view/sap_integration.xml',
	],
	'update_xml' : [
			'security/groups.xml',
			'security/ir.model.access.csv',
	],
	'depends': ['base','hr','account','sale','stock'],
    	'installable': True,
}

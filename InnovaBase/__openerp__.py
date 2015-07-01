# -*- coding: utf-8 -*-
{
	'name'		:'Innova Base',
	'version'	:'1.0',
	'author'	:'Grupo Innova',
	'description'	:"""
Prepare Odoo whit the initial configuration,
1-Remove Few Phoning home feature effect from Core OpenERP.
2-Turns off all currencies except Lps and USD
3-Puts USD base rate change
4-Active multicurrency
5-Shows fields in the currency's change
6-Active about innova	
	""",
	'depends'	:['base','account',"mail"],
	'data'		:["views/res_currency_view.xml","views/base_view.xml","views/mail_data.xml",
"views/replace_files_view.xml","views/account_move_form_view.xml","views/account_move_line_tree_view.xml",
"views/res_partner_view.xml","views/account_invoice_view.xml"],
	'installable'	:True,
	'qweb' : [
        "static/src/xml/base.xml",
	],
}


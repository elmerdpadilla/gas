# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class log(osv.Model):
	_name = 'sap_integration.log'
	_columns = {
		'log':fields.char("message",help="message log"),
		'description': fields.text("Description", help="Description of message")
	}
	_order = 'create_date desc'

# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class product_maker(osv.Model):
	_name = 'sap_integration.product.maker'
	_columns = {
		'sap_id': fields.integer('sap_id'),
		'name' : fields.char('Name')
		
	}

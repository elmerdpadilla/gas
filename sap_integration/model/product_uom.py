# -*- coding: utf-8 -*-
from openerp.osv import fields, osv




class product_uom(osv.osv):
    _inherit = 'product.uom'

	
    _columns = {
		'sap_id': fields.integer('sap_id')
    }

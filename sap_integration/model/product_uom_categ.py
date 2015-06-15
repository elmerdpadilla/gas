# -*- coding: utf-8 -*-
from openerp.osv import fields, osv




class product_uom_categ(osv.osv):
    _inherit = 'product.uom.categ'

	
    _columns = {
		'sap_id': fields.integer('sap_id')
    }

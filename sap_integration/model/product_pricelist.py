# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.fields import Many2one



class product_pricelist(osv.osv):
    _inherit = 'product.pricelist'

    _columns = {
		'sap_id': fields.integer('sap_id'),
		'based_in': fields.char('Based In'),
		'factor': fields.float('Discount',digits=(9,4))
    }

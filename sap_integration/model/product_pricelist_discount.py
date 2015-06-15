# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.fields import Many2one



class product_pricelist_discount(osv.osv):
    _name = 'product.pricelist.discount'

    _columns = {
		'sap_id': fields.char('sap_id'),
		'pricelist_version_id':fields.many2one('product.pricelist.version', 'Price List Version'),
		'amount':   fields.float('Quantity',digits=(9,4)),
		'discount': fields.float('Discount',digits=(9,4)),
		'sequence': fields.integer('Sequence')
    }

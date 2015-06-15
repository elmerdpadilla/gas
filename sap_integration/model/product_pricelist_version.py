# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.fields import Many2one



class product_pricelist_version(osv.osv):
    _inherit = 'product.pricelist.version'
    _columns = {
		'product_pricelist_discount_ids': fields.one2many('product.pricelist.discount','pricelist_version_id',string="Discount lines"),
		'sap_id': fields.char('sap_id'),
		'product_id':fields.many2one('product.template', 'Product'),
		'price': fields.float('Price',digits=(9,4)),
		'currency_id': fields.many2one('res.currency', 'Currency'),
		'Factor': fields.float('Factor',digits=(9,4)),
		'line_num': fields.integer('Line Num'),
    }

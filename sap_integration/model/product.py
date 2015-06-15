# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.fields import Many2one



class product_template(osv.osv):
    _inherit = 'product.template'

    _columns = {
		'sap_id': fields.char('sap_id'),
		'item_code': fields.char('Item Code',select=True),
		'supplier_cat_num': fields.char('Supplier Catalog Num'),
		'property_product_maker': fields.property(
			type='many2one',
            		relation='sap_integration.product.maker',
            		string='Product Maker', 
            		help="Product Maker"),
		'discount': fields.float(string='Discount',digits=(9,4)),
		'on_hand' : fields.float(string='On Hand',digits=(9,4)),
		'is_commited': fields.float(string='Is Commited',digits=(9,4)),
		'on_order': fields.float(string='On Order',digits=(9,4)),
		'product_uom_cat_id' :fields.many2one('product.uom.categ', 'Product UoM Categ Id'),
		'product_codebars_ids' : fields.one2many('product.codebars','item_id',string="Codebars",help="Codigos de Barras"),
		'stock': fields.one2many('sap.integration.stock', 'product_id'),
     }

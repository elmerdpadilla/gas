# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.fields import Many2one



class product_codebars(osv.Model):
 	_name = 'product.codebars'
	_order = "on_hand desc"
	#_rec_name= 'description'
	def _get_name(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for codebar in self.browse(cr,uid,ids,context=context):
			result[codebar.id]=""
			if codebar.bar_code:
				result[codebar.id]+="["+codebar.bar_code+"] "
			if codebar.description:
				result[codebar.id]+=codebar.description
			if codebar.item_code:
				result[codebar.id]+=" "+codebar.item_code
		return result

	def _get_onhand(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for codebar in self.browse(cr,uid,ids,context=context):
			if codebar.item_id:
				oh = codebar.item_id.on_hand
				if oh:
					result[codebar.id]=(oh)
				else:
					result[codebar.id]=0.0
		return result
	def _get_supplier_cat_num(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for codebar in self.browse(cr,uid,ids,context=context):
			result[codebar.id]=""
			if codebar.item_id:
				scn = codebar.item_id.supplier_cat_num
				if scn:
					result[codebar.id]+=scn
		return result
	def _get_product_maker(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for codebar in self.browse(cr,uid,ids,context=context):
			result[codebar.id]=""
			if codebar.item_id:
				product_maker = codebar.item_id.property_product_maker.name
				if product_maker:
					result[codebar.id]+=product_maker
		return result
	def _get_product_price(self, cr, uid, ids, field, arg, context=None):
		result = {}
		obj_version=self.pool.get('product.pricelist.version')
		for codebar in self.browse(cr,uid,ids,context=context):
			result[codebar.id]=0.0
			if codebar.item_id:
				ids2=obj_version.search(cr,uid,[('product_id','=',codebar.item_id.id)],context=context)
				for version in obj_version.browse(cr,uid,ids2,context=context):
					result[codebar.id]=version.price
		return result

	def name_get(self, cr, uid, ids, context=None):
		res = [(r['id'], r['description'] and '[%s] %s' % (r['bar_code'], r['description']) or r['description'] ) for r in self.read(cr, uid, ids, ['bar_code', 'description'], context=context) ]
		return res
	_columns = {
		'sap_id': fields.integer('sap_id'),
		'item_id': fields.many2one('product.template', 'Product'),		
		'bar_code': fields.char('Bar Code'),
		'description': fields.char('Description'),
		'uom_id': fields.many2one('product.uom', ' UoM'),
		'item_code':fields.char('Item Code'),
		'name':fields.function(_get_name,type='char', string='name',store=True),
		'on_hand':fields.function(_get_onhand, type='float', string='on hand',store=True),
		'supplier_cat_num':fields.function(_get_supplier_cat_num, type='char', string='Supplier Cat Num'),
		'product_maker' :fields.function(_get_product_maker, type='char', string='Product maker'),
		'price':fields.function(_get_product_price, type='float', string='Precio',store=False),
		#Precio
		
     }

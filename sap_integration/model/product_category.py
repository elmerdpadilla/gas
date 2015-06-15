from openerp.osv import fields, osv


class product_category(osv.Model):
	_inherit = 'product.category'

	_columns = {
		'sap_id': fields.integer('sap_id')
		#'discount' : fields.float('Discount',digits=(9,4)),
		 	#'sap_id':fields.integer("SAP ID",help="Id en SAP")
	}


from openerp.osv import fields, osv


class stock_warehouse(osv.Model):
	_inherit = 'stock.warehouse'

	_columns = {
		#'sap_id': fields.char('Card Code', size=64, required=True),
		#'discount' : fields.float('Discount',digits=(9,4)),
		 	#'sap_id':fields.integer("SAP ID",help="Id en SAP")
	}

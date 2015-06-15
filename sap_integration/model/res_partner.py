
from openerp.osv import fields, osv


class res_partner(osv.Model):
	_inherit = 'res.partner'

	_columns = {
		'sap_id': fields.char('Card Code', size=64, required=True,select=True),
		'discount' : fields.float('Discount',digits=(9,4)),
		'change_name' : fields.boolean('Allow renaming customer quote'),
		 	#'sap_id':fields.integer("SAP ID",help="Id en SAP")
	}
	_defaults ={
		'sap_id':'new',
	}

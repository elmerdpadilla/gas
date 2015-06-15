
from openerp.osv import fields, osv
from datetime import datetime
import locale
import pytz
from openerp.tools.translate import _

class salesperson(osv.Model):
	_name = 'sap_integration.salesperson'
	_columns = {
		'sap_id':fields.integer("SAP ID",help="Id in SAP"),
		'name':fields.char(string="Name"),

		
		'status': fields.integer("Status", help="0:new, 1:updated in Destination(Odoo), 2:Updated in Source(SAP) and finish"),
		'odoo_id':fields.integer("Odoo ID",help="Id in Odoo"), 
		'error_message': fields.text(string="Error message"),
		'date_in':fields.datetime(string="date In"),
		'date_mig':fields.datetime(string="date Mig")
	}

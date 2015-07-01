from openerp import models, fields, api
from datetime import timedelta,datetime
from dateutil.relativedelta import relativedelta
import time

class res_currency(models.Model):
	_inherit = 'account.invoice'
	
#	partner_rtn = fields.Char("rtn", compute="get_rtn")
	partner_rtn = fields.Char("rtn", related="partner_id.rtn")

#	def get_rtn(self):
#		self.partner_rtn = self.partner_id.rtn



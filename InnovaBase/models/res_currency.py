from openerp import models, fields, api
from datetime import timedelta,datetime
from dateutil.relativedelta import relativedelta
import time

class res_currency(models.Model):
	_inherit = 'res.currency'

	print '___QQQ___'*15

	def add_rate_button_action(self):
#	def action_view(self, cr, uid, ids, context=None):
#		id = ids[0]
		print 'QQQQ....'*20
		return {
#			'domain': "[('currency_id','=', " + str(id) + ")]",
            'type': 'ir.actions.act_window',
			'name': 'add_currency_rate_act',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'res.currency.rate',
			'target': 'new',
        }

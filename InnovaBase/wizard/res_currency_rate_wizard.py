from openerp import models, fields, api

class res_currency_rate_wizard(models.TransientModel):
	_name = 'res.currency.rate.wizard'

	date = fields.Date('date')
	rate = fields.Float('rate')




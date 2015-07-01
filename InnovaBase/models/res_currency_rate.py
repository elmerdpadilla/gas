from openerp import models, fields, api
from datetime import timedelta,datetime
from dateutil.relativedelta import relativedelta
import time

class res_currency_rate(models.Model):
	_inherit = 'res.currency.rate'
#	name		 = fields.Datetime('date', compute='_correct_date', store=True)
	display_date = fields.Date('Display Date', compute = 'show_date')
	get_date	 = fields.Date('Get Date', required=True)

	@api.one
	@api.depends('name')
	def show_date(self):
		tmp = datetime.strptime(self.name, "%Y-%m-%d %H:%M:%S")
		self.display_date = tmp + timedelta(hours=6)
	
	@api.one
	@api.onchange('get_date')
	def odoo_date(self):
		if self.get_date:
			tmp = datetime.strptime(self.get_date, "%Y-%m-%d")
#			self.name= tmp - timedelta(hours=6)
			self.name= tmp
			
	@api.one
	@api.model		
	def save_close(self):
		if self.get_date and self.rate:
			vals = {'get_date':self.get_date,
					'name':self.name,
					'display_date':self.display_date,
					'rate':self.rate, 
					'currency_id':self.env.context['active_id']
					}
			return self.create(vals)						


# el boton Save & new puede guardar correctamente pero se cierra
# deberia mantener el formulario sin cerrar limpiar el formulario para crear un nuevo rate
#	@api.one
#	@api.model		
#	def save_new(self):
#		if self.display_date and self.rate and self.currency_id:
#			vals = {'display_date':self.display_date,'rate':self.rate, 'currency_id':self.currency_id}
#			self.env['res.currency.rate'].create(vals)
#		action ={
#			    "type": "ir.actions.act_window",
#			    "res_model": "res.currency.rate",
#			    "views": [[False, "form"]],
#				"view_type":"form",
#			    "target": "new",
#				}
#		print action
#		return action


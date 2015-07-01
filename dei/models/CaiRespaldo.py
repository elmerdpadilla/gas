# -*- coding: utf-8 -*-
from openerp import models, fields, api
import time

class ir_sequence(models.Model):
	_inherit		= "ir.sequence"
	is_fiscal_document = fields.Boolean("is fiscal document")

class Facthn_Cai(models.Model):
	_name 			= "billing_hn_cai"
	name 			= fields.Char('CAI', help='Clave de Autorización de Impresión ', required=True, select=True)
	expiration_date = fields.Date('Expiration Date', required=True, select=True)
	active			= fields.Boolean('active')
	company			= fields.Many2one('res.company', required=True)
	doc_requested 	= fields.One2many('facthn_doc_requested','facthn_cai')

	@api.model
	def create(self, values):
		print 'createCai_'*30
		print time.strftime("%Y-%m-%d")
		new_billing_hn_cai = super(Facthn_Cai, self).create(values)
		for line in self.doc_requested:
			line.journal.sequence_id.start_date=time.strftime("%Y-%m-%d")
			line.journal.sequence_id.expiration_date=self.expiration_date
		return new_billing_hn_cai

	@api.multi
	def write(self,values):
		write_cai = super(Facthn_Cai, self).write(values)
		for line in self.doc_requested:
			line.journal.sequence_id.expiration_date=self.expiration_date
		return write_cai

class Facthn_doc_requested (models.Model):
	_name 			= "facthn_doc_requested"

	facthn_cai		= fields.Many2one('billing_hn_cai')
	emission_point	= fields.Char('emission point')
	description		= fields.Char('description')
	req_quantity	= fields.Integer('requested amount')

	journal			= fields.Many2one('account.journal')

	prefix			= fields.Char('prefix',required=True, related='journal.sequence_id.prefix')
	padding			= fields.Integer('padding', default=8,related='journal.sequence_id.padding')
	start_number	= fields.Integer('start number', required=True)
	gra_quantity 	= fields.Integer(string="granted amount", default=100,required=True)
	fiscal_document = fields.Selection(selection='_code_get', size=64)
	percentage		= fields.Float('percentage used', related='journal.sequence_id.percentage')

	dis_final_num	= fields.Char('final number',readonly=True)
	dis_start_num	= fields.Char('start number',readonly=True)

	@api.model
	def create(self, values):
		#para cada doc_requested se crea una sequencia y se asigna al diario escogido
		new_doc = super(Facthn_doc_requested, self).create(values)
		
		new_sequence_values = {
			'name':new_doc.description,
			'prefix':new_doc.prefix,
			'padding':new_doc.padding,
			'number_next':new_doc.start_number,
			'number_next_actual':new_doc.start_number,
			'number_increment':1,
			'implementation':'no_gap',
			'min_value':new_doc.start_number,
			'max_value':new_doc.start_number+new_doc.gra_quantity-1,
			'code':new_doc.fiscal_document
			}
		new_sequence = self.env['ir.sequence'].create(new_sequence_values)
		new_doc.journal.sequence_id = new_sequence
		return new_doc

	@api.multi
	def write(self,values):
		write_doc = super(Facthn_doc_requested, self).write(values)
		self.display_range_number
		self.journal.sequence_id.name = self.description
		self.journal.sequence_id.prefix = self.prefix
		self.journal.sequence_id.padding = self.padding
		self.journal.sequence_id.number_increment = 1
		self.journal.sequence_id.implementation = 'no_gap'
		self.journal.sequence_id.min_value = self.start_number
		self.journal.sequence_id.max_value = self.start_number+self.gra_quantity-1
		self.journal.sequence_id.code = self.fiscal_document
		return write_doc

	def _code_get(self, cr, uid, context=None):
	    cr.execute('select code, name from ir_sequence_type')
	    return cr.fetchall()

	@api.onchange('prefix','start_number','gra_quantity','padding')
	def display_range_number(self):
		if self.prefix:
			# rellenar con ceros hasta el numero inicial con el padding especificado
			start_number_filled = str(self.start_number)
			for relleno in range(len(str(self.start_number)),self.padding):
				start_number_filled = '0'+ start_number_filled
	
			# rellenar con ceros hasta el numero final con el padding especificado
			final_number = self.start_number+self.gra_quantity-1
			final_number_filled = str(self.start_number+self.gra_quantity-1)
			for relleno in range(len(str(final_number)),self.padding):
				final_number_filled = '0'+ final_number_filled

			self.dis_start_num = self.prefix + str(start_number_filled)		
			self.dis_final_num = self.prefix + str(final_number_filled)

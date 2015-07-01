# -*- coding: utf-8 -*-
from __future__ import division
from openerp import models, fields, _, api
from openerp.osv import osv, expression
from openerp.exceptions import except_orm, Warning, RedirectWarning
import time

class ir_sequence(models.Model):
	_inherit		  = "ir.sequence"

	fiscal_regime   = fields.One2many('dei.fiscal_regime','sequence')
	cai_shot		= fields.Char("Cai", readonly=True)
	cai_expires_shot= fields.Date("expiration_date", readonly=True)
	start_date		= fields.Date('Start Date')
	expiration_date = fields.Date('Expiration Date', compute="get_expiration_date")
	min_value		= fields.Integer('min value', compute="get_min_value")
	max_value		= fields.Integer('max value', compute="get_max_value")
#	expiration_date = fields.Date('Expiration Date', readonly=True)
#	min_value		= fields.Integer('min value')
#	max_value		= fields.Integer('max value')
	dis_min_value	= fields.Char('min number',readonly=True, compute='display_min_value')
	dis_max_value	= fields.Char('max number',readonly=True, compute='display_max_value')

	percentage_alert= fields.Float('percentage alert', default=80)
#	percentage 		= fields.Float('percentage' )
	percentage 		= fields.Float('percentage', compute='compute_percentage' )

	l_prefix		= fields.Char('prefix', related='prefix')
	l_padding		= fields.Integer('Number padding', related='padding')
	l_number_next_actual=fields.Integer('Next Number', related='number_next_actual')

#	_sql_constraints = [
#('cne_unique', 'unique(cne)', 'cne already exists!')
#('valid_maxvalue', 'CHECK(max_value > number_next OR max_value=0)', 'CAI ERROR: its out of max range!!!'),
#('valid_minvalue', 'CHECK(min_value < number_next OR min_value = number_next OR min_value=0)', 'CAI ERROR: its out of min range!!!'),
#('valid_max_date', 'CHECK(expiration_date >= now() OR expiration_date IS NULL)', 'CAI DATE EXPIRE'),
#('valid_min_date', 'CHECK(start_date <= now() OR start_date IS NULL)','CAI DATE ERROR!!!'),
#   ]


#	def create(self, cr, uid, ids, vals, context=None):
	@api.model
	def create(self, values):
		new_id = super(ir_sequence, self).create(values)
		self.validar()
		return new_id

#	def write(self, cr, uid, ids, vals, context=None):
	@api.multi
	def write(self,values):
		write_id = super(ir_sequence, self).write(values)
		self.validar()
		return write_id 
		
	@api.depends('fiscal_regime')
	@api.one
	def get_expiration_date(self):
		if self.fiscal_regime:
			for regime in self.fiscal_regime:
				if regime.selected:
					self.expiration_date= regime.cai.expiration_date
					self.cai_shot=regime.cai.name
	
	@api.depends('fiscal_regime')
	@api.one
	def get_min_value(self):
		if self.fiscal_regime:
			for regime in self.fiscal_regime:
				if regime.selected:
					self.min_value= regime.desde
		else:
			self.min_value=0

	@api.depends('fiscal_regime')
	@api.one
	def get_max_value(self):
		if self.fiscal_regime:
			for regime in self.fiscal_regime:
				if regime.selected:
					self.max_value= regime.hasta
		else:
			self.max_value= 0

#	@api.onchange('prefix','min_value','max_value','padding')
	@api.depends('min_value')
	def display_min_value(self):
		if self.prefix:
			# rellenar con ceros hasta el numero inicial con el padding especificado
			start_number_filled = str(self.min_value)
			for relleno in range(len(str(self.min_value)),self.padding):
				start_number_filled = '0'+ start_number_filled
			self.dis_min_value = self.prefix + str(start_number_filled)

	@api.depends('max_value')
	def display_max_value(self):
		if self.prefix:
			# rellenar con ceros hasta el numero final con el padding especificado
			final_number = self.max_value
			final_number_filled = str(self.max_value)
			for relleno in range(len(str(final_number)),self.padding):
				final_number_filled = '0'+ final_number_filled
			self.dis_max_value = self.prefix + str(final_number_filled)

	@api.depends('number_next')
	def compute_percentage(self):
		numerador = self.number_next_actual-self.min_value
		denominador = self.max_value-self.min_value
		if denominador > 0:			
			division = (self.number_next_actual-self.min_value)/(self.max_value-self.min_value)
			self.percentage=(division*100)-1
		else:
			self.percentage=0

	def validar(self):
		""" Verify unique cai in sequence """
		already_in_list = []
		for fiscal_line in self.fiscal_regime:
			if fiscal_line.cai.name in already_in_list:
				raise Warning(_(' %s this cai is already in use ')
								%(fiscal_line.cai.name ))
			already_in_list.append(fiscal_line.cai.name)
		""" No overlap """
		for fiscal_line in self.fiscal_regime:
			for fiscal_line_compare in self.fiscal_regime:
				if fiscal_line.desde > fiscal_line_compare.desde and fiscal_line.desde < fiscal_line_compare.hasta:
					raise Warning(_('%s to %s fiscal line overlaps ' ) %(fiscal_line.desde,fiscal_line.hasta))
				if fiscal_line.hasta > fiscal_line_compare.desde and fiscal_line.hasta < fiscal_line_compare.hasta:
					raise Warning(_('%s to %s fiscal line overlaps ' ) %(fiscal_line.desde,fiscal_line.hasta))
		""" desde < hasta """
		for fiscal_line in self.fiscal_regime:
			if fiscal_line.desde > fiscal_line.hasta:
				raise Warning(_('min_value %s to max_value %s' ) %(fiscal_line.desde,fiscal_line.hasta))
		""" Next Number in Range """
#		if self.number_next_actual < self.min_value or self.number_next_actual > self.max_value:
#			raise Warning(_('Next num %s is not in range %s - %s ' ) %(self.number_next_actual,self.min_value,self.max_value))
	
	def _next(self, cr, uid, ids, context=None):
		# Esta parte hace lo mismo que hacia antes la funcion
		if not ids:
			return False
		if context is None:
			context = {}
		force_company = context.get('force_company')
		if not force_company:
			force_company = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
		sequences = self.read(cr, uid, ids, ['name','company_id','implementation','number_next','prefix','suffix','padding'])
		preferred_sequences = [s for s in sequences if s['company_id'] and s['company_id'][0] == force_company ]
		seq = preferred_sequences[0] if preferred_sequences else sequences[0]
		if seq['implementation'] == 'standard':
			cr.execute("SELECT nextval('ir_sequence_%03d')" % seq['id'])
			seq['number_next'] = cr.fetchone()
		else:
			cr.execute("SELECT number_next FROM ir_sequence WHERE id=%s FOR UPDATE NOWAIT", (seq['id'],))
			cr.execute("UPDATE ir_sequence SET number_next=number_next+number_increment WHERE id=%s ", (seq['id'],))
			self.invalidate_cache(cr, uid, ['number_next'], [seq['id']], context=context)
		d = self._interpolation_dict()
		try:
			interpolated_prefix = self._interpolate(seq['prefix'], d)
			interpolated_suffix = self._interpolate(seq['suffix'], d)
		except ValueError:
			raise osv.except_osv(_('Warning'), _('Invalid prefix or suffix for sequence \'%s\'') % (seq.get('name')))
		# nuevas funciones
		# chequea que la secuencia esta vigente 
		#self.check_limits(cr,uid,ids)
# Guarda en la factura las viarables de la secuencia para futuras consultas como el cai que se usaba en el momento, 
# los limites de la secuencia y la fecha de expiracion, todo esto es necesario para que se imprima en la factura
		return interpolated_prefix + '%%0%sd' % seq['padding'] % seq['number_next'] + interpolated_suffix

	def check_limits(self, cr, uid, ids, context=None):
		this_sequence = self.pool.get('ir.sequence').browse(cr,uid,ids,context=context)[0]
		print this_sequence.fiscal_regime
		""" Verificar si la secuencia tiene regimenes fiscales """	
		# No generar numeros si no hay secuencias activadas
		if this_sequence.fiscal_regime:
			flag_any_active = False
			for regimen in this_sequence.fiscal_regime:
				if regimen.selected:
					flag_any_active = True
					self.write(cr,uid,ids,{'cai_shot':regimen.cai.name},context=None)
					break

			if not flag_any_active:
				raise Warning(_('La secuencia no tiene ningun regimen seleccionado '))
				
		else:
# si no hay regimen fiscal agregado a esta secuencia no es necesario validar hacer mas validaciones
			return True
		
		""" Alerta de que restan pocos numeros en la secuencia """
		print "#"*50
		#if this_sequence.percentage and this_sequence.percentage_alert:
			#if this_sequence.percentage > this_sequence.percentage_alert:
				#restantes = (this_sequence.max_value - this_sequence.number_next) + 1
#				print 'restantes ' + str(restantes)
#				raise Warning(
#				                   _('You have %s numbers in this sequence'
#				                      ' This sequence expires in %s ')
#				                    % (restantes, this_sequence.expiration_date))
		print "#"*50
		"""Error Se terminaron los numeros de la secuencia seleccionada"""
		"""if this_sequence.max_value:
			this_number = this_sequence.number_next_actual - 1
			if this_number > this_sequence.max_value :
				raise Warning(_('you have no more numbers for this sequence ' 
								'this number is %s '
								'your limit is %s numbers ' )
								%(this_number,this_sequence.max_value ))
								"""

		"""Error La fecha de la factura debe ser menor """
#		if this_sequence.expiration_date:
#			if time.strftime("%d/%m/%y") > this_sequence.expiration_date :
#				print time.strftime("%d/%m/%y")
#				print this_sequence.expiration_date
#				raise Warning(
#				                   _('this sequence and cai has already expired on $s')
#				                    % (this_sequence.expiration_date))
		
		return True
ir_sequence()

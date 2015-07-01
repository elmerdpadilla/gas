# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.osv import  osv
import time
from itertools import ifilter
class account_invoice(models.Model):
	_inherit		= "account.invoice"
class account_invoice(models.Model):
	_inherit		= "account.invoice"

#	cai_shot		= fields.Char("Cai" , default = 'AB52D9-99057E-2F4F82-0518AF-B9D4DF-29')
#	cai_expires_shot= fields.Date("expiration_date", default = '16-05-15')
#	min_number_shot = fields.Integer("min_number", default = 1)
#	max_number_shot = fields.Integer("max_number", default = 2000)
	
#	cai_shot		= fields.Char("Cai", compute = 'compute_cai_shot', default='q')
#	cai_expires_shot= fields.Date("expiration_date", compute = 'compute_cai_expires_shot')
#	min_number_shot = fields.Integer("min_number", compute = 'compute_min_number_shot')
#	max_number_shot = fields.Integer("max_number", compute = 'compute_max_number_shot')

	cai_shot		= fields.Char("Cai", readonly=True)
	cai_expires_shot= fields.Date("expiration_date", readonly=True)
	min_number_shot = fields.Integer("min_number", readonly=True)
	max_number_shot = fields.Integer("max_number", readonly=True)


	amount_total_text = fields.Char("Amount Total", compute = 'get_totalt', default='Cero')
	

	_sql_constraints = [
	('number', 'unique(number)', 'the invoice number must be unique, see sequence settings in the selected journal!')
	]

	@api.multi
	def invoice_validate(self):
		""" La fecha de la factura debe estar en el rango, si se esta usando """

		if self.journal_id.sequence_id.fiscal_regime:
			if self.date_invoice > self.journal_id.sequence_id.expiration_date:
				self.journal_id.sequence_id.number_next_actual = self.journal_id.sequence_id.number_next_actual -1
				raise Warning(_('la fecha de expiración para esta secuencia es %s ') %(self.journal_id.sequence_id.expiration_date) )
			self.cai_shot=''

			for regimen in self.journal_id.sequence_id.fiscal_regime:
				if regimen.selected:
					self.cai_shot = regimen.cai.name
					self.cai_expires_shot = regimen.cai.expiration_date
					self.min_number_shot = regimen.desde
					self.max_number_shot = regimen.hasta			
	
		return self.write({'state': 'open'})


	@api.one
	@api.depends('journal_id')
	def get_totalt(self):
		self.amount_total_text=''
		if self.currency_id:
			self.amount_total_text=self.to_word(self.amount_total,self.currency_id.name)
		else:
			self.amount_total_text =self.to_word(self.amount_total,self.user_id.company_id.currency_id.name)
		return True
#	def compute_cai_shot(self):
#		self.cai_shot=''
#		for regimen in self.journal_id.sequence_id.fiscal_regime:
#			if regimen.estado:
#				self.cai_shot = regimen.cai.name
#		return True
#	@api.one
#	@api.depends('journal_id')
#	def compute_cai_expires_shot(self):
#		self.cai_expires_shot = time.strftime("%Y-%m-%d")
#		for regimen in self.journal_id.sequence_id.fiscal_regime:
#			if regimen.estado:
#				self.cai_expires_shot = regimen.cai.expiration_date
#		return True
#	@api.one
#	@api.depends('journal_id')
#	def compute_min_number_shot(self):
#		self.min_number_shot = 0
#		for regimen in self.journal_id.sequence_id.fiscal_regime:
#			if regimen.estado:
#				self.min_number_shot = regimen.desde
#		return True
#	@api.one
#	@api.depends('journal_id')
#	def compute_max_number_shot(self):
#		self.max_number_shot = 0
#		for regimen in self.journal_id.sequence_id.fiscal_regime:
#			if regimen.estado:
#				self.max_number_shot = regimen.hasta
#		return True

	def to_word(self,number, mi_moneda):
		valor= number
		number=int(number)
		centavos=int((round(valor-number,2))*100)
		UNIDADES = (
			'',
			'UN ',
			'DOS ',
			'TRES ',
			'CUATRO ',
			'CINCO ',
			'SEIS ',
			'SIETE ',
			'OCHO ',
			'NUEVE ',
			'DIEZ ',
			'ONCE ',
			'DOCE ',
			'TRECE ',
			'CATORCE ',
			'QUINCE ',
			'DIECISEIS ',
			'DIECISIETE ',
			'DIECIOCHO ',
			'DIECINUEVE ',
			'VEINTE '
		)

		DECENAS = (
			'VENTI',
			'TREINTA ',
			'CUARENTA ',
			'CINCUENTA ',
			'SESENTA ',
			'SETENTA ',
			'OCHENTA ',
			'NOVENTA ',
			'CIEN ')

		CENTENAS = (
			'CIENTO ',
			'DOSCIENTOS ',
			'TRESCIENTOS ',
			'CUATROCIENTOS ',
			'QUINIENTOS ',
			'SEISCIENTOS ',
			'SETECIENTOS ',
			'OCHOCIENTOS ',
			'NOVECIENTOS '
		)
		MONEDAS = (
			{'country': u'Colombia', 'currency': 'COP', 'singular': u'PESO COLOMBIANO', 'plural': u'PESOS COLOMBIANOS', 'symbol': u'$'},
			{'country': u'Honduras', 'currency': 'HNL', 'singular': u'Lempira', 'plural': u'Lempiras', 'symbol': u'L'},
			{'country': u'Estados Unidos', 'currency': 'USD', 'singular': u'DÓLAR', 'plural': u'DÓLARES', 'symbol': u'US$'},
			{'country': u'Europa', 'currency': 'EUR', 'singular': u'EURO', 'plural': u'EUROS', 'symbol': u'€'},
			{'country': u'México', 'currency': 'MXN', 'singular': u'PESO MEXICANO', 'plural': u'PESOS MEXICANOS', 'symbol': u'$'},
			{'country': u'Perú', 'currency': 'PEN', 'singular': u'NUEVO SOL', 'plural': u'NUEVOS SOLES', 'symbol': u'S/.'},
			{'country': u'Reino Unido', 'currency': 'GBP', 'singular': u'LIBRA', 'plural': u'LIBRAS', 'symbol': u'£'}
			)
		if mi_moneda != None:
			try:
				moneda = ifilter(lambda x: x['currency'] == mi_moneda, MONEDAS).next()
				if number < 2:
					moneda = moneda['singular']
				else:
					moneda = moneda['plural']
			except:
				return "Tipo de moneda inválida"
		else:
			moneda = ""
		converted = ''
		if not (0 < number < 999999999):
			return 'No es posible convertir el numero a letras'

		number_str = str(number).zfill(9)
		millones = number_str[:3]
		miles = number_str[3:6]
		cientos = number_str[6:]

		if(millones):
			if(millones == '001'):
				converted += 'UN MILLON '
			elif(int(millones) > 0):
				converted += '%sMILLONES ' % self.convert_group(millones)

		if(miles):
			if(miles == '001'):
				converted += 'MIL '
			elif(int(miles) > 0):
				converted += '%sMIL ' % self.convert_group(miles)

		if(cientos):
			if(cientos == '001'):
				converted += 'UN '
			elif(int(cientos) > 0):
				converted += '%s ' % self.convert_group(cientos)
		if(centavos)>0:
			converted+= "con %2i/100 "%centavos
		converted += moneda
		return converted.title()


	def convert_group(self,n):
		UNIDADES = (
			'',
			'UN ',
			'DOS ',
			'TRES ',
			'CUATRO ',
			'CINCO ',
			'SEIS ',
			'SIETE ',
			'OCHO ',
			'NUEVE ',
			'DIEZ ',
			'ONCE ',
			'DOCE ',
			'TRECE ',
			'CATORCE ',
			'QUINCE ',
			'DIECISEIS ',
			'DIECISIETE ',
			'DIECIOCHO ',
			'DIECINUEVE ',
			'VEINTE '
		)
		DECENAS = (
			'VENTI',
			'TREINTA ',
			'CUARENTA ',
			'CINCUENTA ',
			'SESENTA ',
			'SETENTA ',
			'OCHENTA ',
			'NOVENTA ',
			'CIEN '
		)

		CENTENAS = (
			'CIENTO ',
			'DOSCIENTOS ',
			'TRESCIENTOS ',
			'CUATROCIENTOS ',
			'QUINIENTOS ',
			'SEISCIENTOS ',
			'SETECIENTOS ',
			'OCHOCIENTOS ',
			'NOVECIENTOS '
		)
		MONEDAS = (
			{'country': u'Colombia', 'currency': 'COP', 'singular': u'PESO COLOMBIANO', 'plural': u'PESOS COLOMBIANOS', 'symbol': u'$'},
			{'country': u'Honduras', 'currency': 'HNL', 'singular': u'Lempira', 'plural': u'Lempiras', 'symbol': u'L'},
			{'country': u'Estados Unidos', 'currency': 'USD', 'singular': u'DÓLAR', 'plural': u'DÓLARES', 'symbol': u'US$'},
			{'country': u'Europa', 'currency': 'EUR', 'singular': u'EURO', 'plural': u'EUROS', 'symbol': u'€'},
			{'country': u'México', 'currency': 'MXN', 'singular': u'PESO MEXICANO', 'plural': u'PESOS MEXICANOS', 'symbol': u'$'},
			{'country': u'Perú', 'currency': 'PEN', 'singular': u'NUEVO SOL', 'plural': u'NUEVOS SOLES', 'symbol': u'S/.'},
			{'country': u'Reino Unido', 'currency': 'GBP', 'singular': u'LIBRA', 'plural': u'LIBRAS', 'symbol': u'£'}
		)
		output = ''

		if(n == '100'):
			output = "CIEN "
		elif(n[0] != '0'):
			output = CENTENAS[int(n[0]) - 1]

		k = int(n[1:])
		if(k <= 20):
			output += UNIDADES[k]
		else:
			if((k > 30) & (n[2] != '0')):
				output += '%sY %s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
			else:
				output += '%s%s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])

		return output

	def addComa(self, snum ):
		s = snum;
		i = s.index('.') # Se busca la posición del punto decimal
		while i > 3:
			i = i - 3
			s = s[:i] +  ',' + s[i:]
		return s

class pos_order2(osv.osv):
	_inherit		= "pos.order"
	def create(self, cr, uid, values, context=None):
		
		if values.get('session_id'):
			# set name based on the sequence specified on the config
			session = self.pool['pos.session'].browse(cr, uid, values['session_id'], context=context)
			values['cai_shot'] = session.config_id.sequence_id.cai_shot
			values['cai_expires_shot'] = session.config_id.sequence_id.expiration_date
			values['min_number_shot'] = session.config_id.sequence_id.min_value
			values['max_number_shot'] = session.config_id.sequence_id.max_value
			return super(pos_order2, self).create(cr, uid, values, context=context)
		else:
			values2={}
			order_id=super(pos_order2, self).create(cr, uid, values, context=context)
			order_obj=self.pool.get('pos.order')
			order=order_obj.browse(cr,uid,order_id,context=None)
			values2['cai_shot'] = order.session_id.config_id.sequence_id.cai_shot
			values2['cai_expires_shot'] = order.session_id.config_id.sequence_id.expiration_date
			values2['min_number_shot'] = order.session_id.config_id.sequence_id.min_value
			values2['max_number_shot'] = order.session_id.config_id.sequence_id.max_value
			order_obj.write(cr,uid,order_id,values2,context=None)
			return order_id
			
		return True
			
			
		
class pos_order(models.Model):
	_inherit		= "pos.order"
	cai_shot		= fields.Char("Cai", readonly=True)
	cai_expires_shot= fields.Date("expiration_date", readonly=True)
	min_number_shot = fields.Integer("min_number", readonly=True)
	max_number_shot = fields.Integer("max_number", readonly=True)
	amount_total_text = fields.Char("Amount Total", compute = 'get_totalt', default='Cero')

	@api.one
	def get_totalt(self):
		self.amount_total_text=''
		print "#"*4
		print self.amount_total
	
		self.amount_total_text =self.to_word(self.amount_total,self.user_id.company_id.currency_id.name)
		return True

	def to_word(self,number, mi_moneda):
		valor= number
		number=int(number)
		centavos=int((round(valor-number,2))*100)
		UNIDADES = (
			'',
			'UN ',
			'DOS ',
			'TRES ',
			'CUATRO ',
			'CINCO ',
			'SEIS ',
			'SIETE ',
			'OCHO ',
			'NUEVE ',
			'DIEZ ',
			'ONCE ',
			'DOCE ',
			'TRECE ',
			'CATORCE ',
			'QUINCE ',
			'DIECISEIS ',
			'DIECISIETE ',
			'DIECIOCHO ',
			'DIECINUEVE ',
			'VEINTE '
		)

		DECENAS = (
			'VENTI',
			'TREINTA ',
			'CUARENTA ',
			'CINCUENTA ',
			'SESENTA ',
			'SETENTA ',
			'OCHENTA ',
			'NOVENTA ',
			'CIEN ')

		CENTENAS = (
			'CIENTO ',
			'DOSCIENTOS ',
			'TRESCIENTOS ',
			'CUATROCIENTOS ',
			'QUINIENTOS ',
			'SEISCIENTOS ',
			'SETECIENTOS ',
			'OCHOCIENTOS ',
			'NOVECIENTOS '
		)
		MONEDAS = (
			{'country': u'Colombia', 'currency': 'COP', 'singular': u'PESO COLOMBIANO', 'plural': u'PESOS COLOMBIANOS', 'symbol': u'$'},
			{'country': u'Honduras', 'currency': 'HNL', 'singular': u'Lempira', 'plural': u'Lempiras', 'symbol': u'L'},
			{'country': u'Estados Unidos', 'currency': 'USD', 'singular': u'DÓLAR', 'plural': u'DÓLARES', 'symbol': u'US$'},
			{'country': u'Europa', 'currency': 'EUR', 'singular': u'EURO', 'plural': u'EUROS', 'symbol': u'€'},
			{'country': u'México', 'currency': 'MXN', 'singular': u'PESO MEXICANO', 'plural': u'PESOS MEXICANOS', 'symbol': u'$'},
			{'country': u'Perú', 'currency': 'PEN', 'singular': u'NUEVO SOL', 'plural': u'NUEVOS SOLES', 'symbol': u'S/.'},
			{'country': u'Reino Unido', 'currency': 'GBP', 'singular': u'LIBRA', 'plural': u'LIBRAS', 'symbol': u'£'}
			)
		if mi_moneda != None:
			try:
				moneda = ifilter(lambda x: x['currency'] == mi_moneda, MONEDAS).next()
				if number < 2:
					moneda = moneda['singular']
				else:
					moneda = moneda['plural']
			except:
				return "Tipo de moneda inválida"
		else:
			moneda = ""
		converted = ''
		if not (0 < number < 999999999):
			return 'No es posible convertir el numero a letras'

		number_str = str(number).zfill(9)
		millones = number_str[:3]
		miles = number_str[3:6]
		cientos = number_str[6:]

		if(millones):
			if(millones == '001'):
				converted += 'UN MILLON '
			elif(int(millones) > 0):
				converted += '%sMILLONES ' % self.convert_group(millones)

		if(miles):
			if(miles == '001'):
				converted += 'MIL '
			elif(int(miles) > 0):
				converted += '%sMIL ' % self.convert_group(miles)

		if(cientos):
			if(cientos == '001'):
				converted += 'UN '
			elif(int(cientos) > 0):
				converted += '%s ' % self.convert_group(cientos)
		if(centavos)>0:
			converted+= "con %2i/100 "%centavos
		converted += moneda
		return converted.title()


	def convert_group(self,n):
		UNIDADES = (
			'',
			'UN ',
			'DOS ',
			'TRES ',
			'CUATRO ',
			'CINCO ',
			'SEIS ',
			'SIETE ',
			'OCHO ',
			'NUEVE ',
			'DIEZ ',
			'ONCE ',
			'DOCE ',
			'TRECE ',
			'CATORCE ',
			'QUINCE ',
			'DIECISEIS ',
			'DIECISIETE ',
			'DIECIOCHO ',
			'DIECINUEVE ',
			'VEINTE '
		)
		DECENAS = (
			'VENTI',
			'TREINTA ',
			'CUARENTA ',
			'CINCUENTA ',
			'SESENTA ',
			'SETENTA ',
			'OCHENTA ',
			'NOVENTA ',
			'CIEN '
		)

		CENTENAS = (
			'CIENTO ',
			'DOSCIENTOS ',
			'TRESCIENTOS ',
			'CUATROCIENTOS ',
			'QUINIENTOS ',
			'SEISCIENTOS ',
			'SETECIENTOS ',
			'OCHOCIENTOS ',
			'NOVECIENTOS '
		)
		MONEDAS = (
			{'country': u'Colombia', 'currency': 'COP', 'singular': u'PESO COLOMBIANO', 'plural': u'PESOS COLOMBIANOS', 'symbol': u'$'},
			{'country': u'Honduras', 'currency': 'HNL', 'singular': u'Lempira', 'plural': u'Lempiras', 'symbol': u'L'},
			{'country': u'Estados Unidos', 'currency': 'USD', 'singular': u'DÓLAR', 'plural': u'DÓLARES', 'symbol': u'US$'},
			{'country': u'Europa', 'currency': 'EUR', 'singular': u'EURO', 'plural': u'EUROS', 'symbol': u'€'},
			{'country': u'México', 'currency': 'MXN', 'singular': u'PESO MEXICANO', 'plural': u'PESOS MEXICANOS', 'symbol': u'$'},
			{'country': u'Perú', 'currency': 'PEN', 'singular': u'NUEVO SOL', 'plural': u'NUEVOS SOLES', 'symbol': u'S/.'},
			{'country': u'Reino Unido', 'currency': 'GBP', 'singular': u'LIBRA', 'plural': u'LIBRAS', 'symbol': u'£'}
		)
		output = ''

		if(n == '100'):
			output = "CIEN "
		elif(n[0] != '0'):
			output = CENTENAS[int(n[0]) - 1]

		k = int(n[1:])
		if(k <= 20):
			output += UNIDADES[k]
		else:
			if((k > 30) & (n[2] != '0')):
				output += '%sY %s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
			else:
				output += '%s%s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])

		return output

	def addComa(self, snum ):
		s = snum;
		i = s.index('.') # Se busca la posición del punto decimal
		while i > 3:
			i = i - 3
			s = s[:i] +  ',' + s[i:]
		return s


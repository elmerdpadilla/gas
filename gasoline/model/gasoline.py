# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from datetime import datetime
import locale
import pytz
from openerp.tools.translate import _
class dispenser(osv.Model):
	_name = 'gasoline.dispenser'
	_columns = {
	   'name':fields.char(string="Name",help="Name of Dispenser"),
	   'status':fields.selection([('active', 'Active'),
                                   ('inactive', 'Inactive')], 'status',),
	   'product_ids':fields.one2many('gasoline.side','product_id',string="Lados"),
	   'turn_id':fields.many2many('gasoline.turn'),
}
	_defaults={
		'status':'inactive',
		}

class side(osv.Model):
	_name = 'gasoline.side'
	_columns = {
		'name':fields.char(string="Name"),
		'product_ids':fields.one2many('gasoline.side_product','side_id',string="Products"),
		'product_id':fields.many2one('gasoline.dispenser',string="Dispenser"),
		  'level':fields.float(string="Level",help="level of Dispenser"),
		
}

class side_product(osv.Model):
	_name = 'gasoline.side_product'
	def _get_name(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for side_product in self.browse(cr, uid, ids, context=context):
			result[side_product.id] = side_product.product_id.name
		return result

	def _get_value(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for side_product in self.browse(cr, uid, ids, context=context):
			if side_product.product_id:
				result[side_product.id] = True
			else:
				result[side_product.id] = False
		return result
	
	_columns = {
	        'name' :fields.function(_get_name,type='char', string='Name'),
		'side_id':fields.many2one('gasoline.side',string="side id"),
		'product_id':fields.many2one('gasoline.product',string="product "),
		'level': fields.float(string="level"),
	   	'status':fields.function(_get_value,type='boolean',string='status',store=True),
		}
	_defaults = {
	'status' :True,
		}

class turn(osv.Model):
	_name = 'gasoline.turn'
	def unlink(self, cr, uid, ids, context=None):
        	for rec in self.browse(cr, uid, ids, context=context):
            		if rec.state not in ('draft','cancel'):
                		raise osv.except_osv(_('Unable to Delete!'), _('you cannot delete a turn initiated'))
        	return super(turn, self).unlink(cr, uid, ids, context=context)
	def action_draft(self, cr, uid, ids, context=None):
		return self.write(cr, uid, ids, {'state':'draft'}, context=context)
	def action_confirm(self, cr, uid, ids, context=None):
		for dispenser in self.pool.get('gasoline.turn').browse(cr,uid,ids,context=context).dispenser_ids:
			self.pool.get('gasoline.dispenser').write(cr,uid,dispenser.id,{'status':'active'},context=context)
		for turn in self.browse(cr,uid,ids,context=context):
			self.pool.get('gasoline.user').write(cr,uid,turn.user_id.id,{'status':'active'},context=context)
		return self.write(cr, uid, ids, {'state':'progress'}, context=context)
	def action_new(self, cr, uid, ids, context=None):
		id = ids[0]
		porder_obj= self.pool.get('pos.order')
		porderline_obj= self.pool.get('pos.order.line')
		orderdata={}
		orderdata['is_gasoline']=True
		orderdata['turn_id']=id
		order_id=porder_obj.create(cr,uid,orderdata)
		array=[];
		for turn in self.browse(cr,uid,ids,context=context):
			for reading in turn.reading_init:
				if reading.levelf > 0:
					journal_ids = self.pool.get('pos.order.line').search(cr,uid,[('order_id','=',order_id),('product_id','=',reading.product_id.id)],context=context)

					if len(journal_ids)==0:
						orderlinedata={}
						orderlinedata['order_id']=order_id
						orderlinedata['product_id']=reading.product_id.id
						orderlinedata['price2']=reading.product_id.list_price
						orderlinedata['price_unit']=reading.product_id.list_price
						orderlinedata['qty']=reading.levelf
						orderline_id=porderline_obj.create(cr,uid,orderlinedata)
						array.append(orderline_id)
					else:
						ca=self.pool.get('pos.order.line').browse(cr,uid,journal_ids[0],context=context).qty+reading.levelf
						self.pool.get('pos.order.line').write(cr,uid,journal_ids[0],{'qty':ca},context=context)

			for order in turn.order_ids:
				for order_line in order.lines:
					if order_line.id not in array:
						line_ids = self.pool.get('pos.order.line').search(cr,uid,[('product_id','=',order_line.product_id.id),('order_id','=',order_line.order_id.id)],context=context)
						if len(line_ids)>0:
							line2_ids = self.pool.get('pos.order.line').search(cr,uid,[('product_id','=',order_line.product_id.id),('id','in',array)],context=context)
							if len(line2_ids)>0:
								ca=self.pool.get('pos.order.line').browse(cr,uid,line2_ids[0],context=context).qty-self.pool.get('pos.order.line').browse(cr,uid,line_ids[0],context=context).qty
								if ca>0:
									self.pool.get('pos.order.line').write(cr,uid,line2_ids[0],{'qty':ca},context=context)
								else:
									self.pool.get('pos.order.line').unlink(cr,uid,line2_ids[0],context=context)

				


		return {
	    'domain': "[('turn_id','=', " + str(id) + ")]",
            'type': 'ir.actions.act_window',
	'name': 'Create turn Invoice',
             'view_type': 'form',
             'view_mode': 'tree,form',
            'res_model': 'pos.order',
            'target': 'current',
        }
	def action_view(self, cr, uid, ids, context=None):
		id = ids[0]
		return {
	    'domain': "[('turn_id','=', " + str(id) + ")]",
            'type': 'ir.actions.act_window',
	'name': 'Create turn Invoice',
             'view_type': 'form',
             'view_mode': 'tree,form',
            'res_model': 'pos.order',
            'target': 'current',
        }
	def action_done(self, cr, uid, ids, context=None):
		return self.write(cr, uid, ids, {'state':'closed'}, context=context)
	def action_close(self, cr, uid, ids, context=None):
		obj_order=self.pool.get('pos.order')
		for turn in self.browse(cr,uid,ids,context=context):
			if not turn.maintenance:
				if turn.sold>0:
					if len(turn.order_ids)<1:
						raise osv.except_osv(_('you cannot Finish the Turn'), _('dont Exist orders'))
		for turn in self.browse(cr,uid,ids,context=context):
			for order in turn.order_ids:
				if not order.invoice_id and len(order.statement_ids)<1 and order.state not in ['cancel']:
					raise osv.except_osv(_('you cannot Finish the Turn'), _('draft orders exist'))
		for turn in self.browse(cr,uid,ids,context=context):
			for order in turn.order_ids:
				if order.invoice_id:
					obj_order.write(cr, uid, order.id, {'state':'invoiced'}, context=context)
				if len(order.statement_ids)>0 and len(order.lines)>0:
					obj_order.write(cr, uid, order.id, {'state':'paid'}, context=context)
				obj_order.create_picking(cr, uid, order.id, context=context)
		for dispenser in self.pool.get('gasoline.turn').browse(cr,uid,ids,context=context).dispenser_ids:
			self.pool.get('gasoline.dispenser').write(cr,uid,dispenser.id,{'status':'inactive'},context=context)
		for turn in self.browse(cr,uid,ids,context=context):
			self.pool.get('gasoline.user').write(cr,uid,turn.user_id.id,{'status':'inactive'},context=context)
		levelids=[]
		for turn in self.browse(cr,uid,ids,context=context):
			for reading in turn.reading_finish:
				self.pool.get('gasoline.side_product').write(cr,uid,reading.side_product_id.id,{'level':reading.levelt },context=context)	
		return self.write(cr, uid, ids, {'state':'finish'}, context=context)
	def create(self, cr, uid, values, context=None):
		reading_obj = self.pool.get('gasoline.reading')
		journal_ids = self.pool.get('account.journal').search(cr,uid,[('type','in',['cash','bank']),('combustible','=',True)],context=context)
		journal_obj = self.pool.get('gasoline.journal')	
		if values:
			turn_obj = self.pool.get('gasoline.turn')
		b =super(turn, self).create(cr, uid, values, context=context)	
		product_list = []
		turn1 = self.browse(cr, uid, b, context=context)
		
		for dispenser in turn1.dispenser_ids:
			for side in dispenser.product_ids:
				for side_product in side.product_ids:
					for product in side_product.product_id:
						des = dispenser.name+"-"+side.name
						product_list.append([product.product_id.id,dispenser.id,turn1.id,des,side_product.level,side_product.id])

		for c in journal_ids:
			journal_obj.create(cr,uid,{
			'journal_id':c,
			'turn_id':b,
			},context=context)
		for a in product_list:
			reading_obj.create(cr,uid,{
			'product_id':a[0],
			'turn_id':a[2],
			'description':a[3],
			'level':a[4],
			'levelt':a[4],
			'side_product_id':a[5],
		},context=context)
		self.action_confirm(cr,uid,b)
		return b
	def _get_name(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] = turn.user_id.name
		return result
	def _get_diff(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			totalmoney=0
			totalcash=0
			for order in turn.order_ids:
				if order.state not in ['cancel']:
					totalmoney+=order.amount_total
			for line in turn.reading_end:
				totalcash+= line.price_list
			result[turn.id] = -totalcash+totalmoney+turn.pdifference-turn.other
		return result
	def _get_diff_total(self, cr, uid, ids, field, arg, context=None):
		result = {}
		total_diff=0
		for turn in self.browse(cr, uid, ids, context=context):
			totalmoney=0
			totalcash=0
			for order in turn.order_ids:
				if order.state not in ['cancel']:
					totalmoney+=order.amount_total
			for line in turn.reading_end:
				totalcash+= line.price_list
			total_diff += -totalcash+totalmoney+turn.pdifference-turn.other
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id]=total_diff
		return result
	def _get_inv(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			totalmoney=0
			totalcash=0
			for order in turn.order_ids:
				if order.invoice_id.state != 'cancel':
					totalmoney+=order.invoice_id.amount_total
			result[turn.id] = totalmoney
		return result
	def _get_inv_total(self, cr, uid, ids, field, arg, context=None):
		result = {}
		totalmoney=0
		for turn in self.browse(cr, uid, ids, context=context):
			for order in turn.order_ids:
				if order.invoice_id.state != 'cancel':
					totalmoney+=order.invoice_id.amount_total
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] = totalmoney
		return result
	def _get_order_diff(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			totalmoney=0
			totalcash=0
			for order in turn.order_ids:
				totalmoney+=order.difference
			result[turn.id] = totalmoney
		return result
	def _get_order_diff_total(self, cr, uid, ids, field, arg, context=None):
		result = {}
		totalmoney=0
		totalcash=0
		for turn in self.browse(cr, uid, ids, context=context):
			for order in turn.order_ids:
				totalmoney+=order.difference
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] = totalmoney
		return result
	def _get_paid(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			totalmoney=0
			totalcash=0
			for order in turn.order_ids:
				if order.state != 'cancel':
					for paid in order.statement_ids:
						totalmoney+=paid.amount
			result[turn.id] = totalmoney
			
		return result
	def _get_paid_total(self, cr, uid, ids, field, arg, context=None):
		result = {}
		totalmoney=0
		for turn in self.browse(cr, uid, ids, context=context):
			for journal in turn.journal_ids:
				totalmoney+=journal.money
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] = totalmoney
		return result
	def _get_other(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			totalmoney=0
			totalcash=0
			arrayproduct = []
			idsproduct=self.pool.get('gasoline.product').search(cr,uid,[],context=context)
			for product in self.pool.get('gasoline.product').browse(cr,uid,idsproduct,context=context):
				arrayproduct.append(product.product_id.id)
			for order in turn.order_ids:
				for line in order.lines:
					if line.product_id.id not in arrayproduct:
						totalmoney+=line.price_subtotal_incl
				#totalmoney+=journal.money
			result[turn.id] = totalmoney
		return result
	def _get_other_total(self, cr, uid, ids, field, arg, context=None):
		result = {}
		totalmoney=0
		totalcash=0
		for turn in self.browse(cr, uid, ids, context=context):
			arrayproduct = []
			idsproduct=self.pool.get('gasoline.product').search(cr,uid,[],context=context)
			for product in self.pool.get('gasoline.product').browse(cr,uid,idsproduct,context=context):
				arrayproduct.append(product.product_id.id)
			for order in turn.order_ids:
				for line in order.lines:
					if line.product_id.id not in arrayproduct:
						totalmoney+=line.price_subtotal_incl
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] = totalmoney
		return result
	def _get_sold(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			totalmoney=0
			totalcash=0
			for line in turn.reading_end:
				totalcash+= line.price_list
			result[turn.id] = totalcash
		return result
	def _get_sold_total(self, cr, uid, ids, field, arg, context=None):
		result = {}
		totalmoney=0
		totalcash=0
		for turn in self.browse(cr, uid, ids, context=context):
			for line in turn.reading_end:
				totalcash+= line.price_list
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] = totalcash
		return result
	def _get_reading(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			totalcash=0
			for line in turn.reading_end:
				totalcash+= line.price_list
			result[turn.id] = totalcash
		return result
	def _get_reading_total(self, cr, uid, ids, field, arg, context=None):
		result = {}
		totalcash=0
		for turn in self.browse(cr, uid, ids, context=context):
			for line in turn.reading_end:
				totalcash+= line.price_list
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] = totalcash
		return result
	def _get_journal(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			totalmoney=0
			for journal in turn.order_ids:
				totalmoney+=journal.amount_total
			result[turn.id] =totalmoney
		return result
	def _get_journal_total(self, cr, uid, ids, field, arg, context=None):
		result = {}
		totalmoney=0
		for turn in self.browse(cr, uid, ids, context=context):
			for journal in turn.order_ids:
				totalmoney+=journal.amount_total
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] =totalmoney
		return result
	def _get_reading_total2(self, cr, uid, ids, field, arg, context=None):
		result = {}
		obj_reading=self.pool.get('gasoline.reading')
		reading_ids=obj_reading.search(cr,uid,[('turn_id','in',ids)],context=context)
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] =obj_reading.browse(cr,uid,reading_ids,context=context)
		return result
	def _get_journal_ids(self, cr, uid, ids, field, arg, context=None):
		result = {}
		obj_journal=self.pool.get('gasoline.journal')
		journal_ids=obj_journal.search(cr,uid,[('turn_id','in',ids),('money','>',0.0)],context=context)
		journals=obj_journal.browse(cr,uid,journal_ids,context=context)
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] =journals

		return result
	def _get_order_ids(self, cr, uid, ids, field, arg, context=None):
		result = {}
		obj_journal=self.pool.get('pos.order')
		journal_ids=obj_journal.search(cr,uid,[('turn_id','in',ids)],context=context)
		for turn in self.browse(cr, uid, ids, context=context):
			result[turn.id] =obj_journal.browse(cr,uid,journal_ids,context=context)
		return result
	_columns = {
	    'name' :fields.function(_get_name,type='char', string='Name'),
	    'type' :fields.selection([('A', 'A'),('B', 'B'),('C', 'C')],string="Turn", required=True),
	    'maintenance' : fields.boolean(string="turn of maintenance"),
	    'date':fields.date(string="date", required=True),
	    'user_id':fields.many2one('gasoline.user',string="Employee", required=True),
	    'dispenser_ids':fields.many2many('gasoline.dispenser',string="Dispenser"),
	    'state' :fields.selection([('draft', 'Draft'),('progress', 'Progress'),
                                   ('closed', 'Closed'),('finish','Finish')], 'state',),
            'reading_init' :fields.one2many('gasoline.reading','turn_id',string="reading Init"),
	    'reading_end' :fields.one2many('gasoline.reading','turn_id',string="reading end"),
	    'reading_finish' :fields.one2many('gasoline.reading','turn_id',string="reading Finish"),
		'reading_total2' : fields.function(_get_reading_total2, type='one2many', obj = 'gasoline.reading',  string='Reading Total'),
	    'journal_ids' : fields.one2many('gasoline.journal','turn_id',string="payment methods",domain=[('money','>',0.0)]),
	    'journal_ids_total' : fields.function(_get_journal_ids, type='one2many', obj = 'gasoline.journal',  string='journal Total'),
	    'note':fields.text(string='Note'),
	    'difference':fields.function(_get_diff,type='float', string='Difference'),
	    'difference_total':fields.function(_get_diff_total,type='float', string='Difference'),
	    'pdifference':fields.function(_get_order_diff,type='float', string='Difference of price'),
	    'pdifference_total':fields.function(_get_order_diff_total,type='float', string='Difference of price'),
	    'invoiced':fields.function(_get_inv,type='float', string='Invoiced'),
	    'invoiced_total':fields.function(_get_inv_total,type='float', string='Invoiced'),
	    'paid':fields.function(_get_paid,type='float', string='Paid'),
	    'paid_total':fields.function(_get_paid_total,type='float', string='Paid'),
	    'other':fields.function(_get_other,type='float', string='Other product'),
	    'other_total':fields.function(_get_other_total,type='float', string='Other product'),
	    'sold':fields.function(_get_sold,type='float', string='Sold'),
	    'sold_total':fields.function(_get_sold_total,type='float', string='Sold'),
	    'reading':fields.function(_get_reading,type='float', string='Reading'),
		'reading_total':fields.function(_get_reading_total,type='float', string='Reading'),
	    'journal':fields.function(_get_journal,type='float', string='Journal'),
	    'journal_total':fields.function(_get_journal_total,type='float', string='Journal'),
	    'order_ids':fields.one2many('pos.order','turn_id',string="orders"),
	    'order_ids_total' : fields.function(_get_order_ids, type='one2many', obj = 'pos.order',  string='order Total'),
}
	_order = 'date desc'
	_defaults = {
	'state' :'draft',
	'date' : datetime.now()
		}
class product(osv.Model):
	_name = 'gasoline.product'
	def action_new(self, cr, uid, ids, context=None):
		id = ids[0]
		porder_obj= self.pool.get('gasoline.reading2')
		orderdata={}
		orderdata['product_id2']=id
		#order_id=porder_obj.create(cr,uid,orderdata)
		return {
            'type': 'ir.actions.act_window',
	     'name': 'Create turn Invoice',
             'view_type': 'form',
             'view_mode': 'form',
            'res_model': 'gasoline.reading2',
            'target': 'current',
        }
	def _get_name(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for product in self.browse(cr, uid, ids, context=context):
			result[product.id] = product.product_id.name
		return result
	def _get_measure(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for product in self.browse(cr, uid, ids, context=context):
			result[product.id] = product.product_id.uom_id.name
		return result
	def _get_level(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for turn in self.browse(cr, uid, ids, context=context):
			for reading in reading_init:
				result[reading.id] = reading.product_id.uom_id.name
		return result
	_columns = {
	    'name' :fields.function(_get_name,type='char', string='name'),
	    'locale':fields.float(string="level",help="level for product"),
	    'product_id':fields.many2one('product.product',string="Productos",domain="[('is_gasoline', '=', True )]",required=True),
	    'measure':fields.function(_get_measure,type='char',string="Mesure Unit",help="Mesure Unit of Dispenser"),
	    'level':fields.function(_get_level,type='float',string="Level",help="Level for product"),
	    'side_ids':fields.one2many('gasoline.side_product','product_id'),
            'reading_init' :fields.one2many('gasoline.reading2','product_id2',string="reading Init"),
	    'reading_end' :fields.one2many('gasoline.reading2','product_id2',string="reading end"),
	    'reading_finish' :fields.one2many('gasoline.reading2','product_id2',string="reading Finish"),
	    'reading_id' : fields.integer(string="id"),
	
}
class reading(osv.Model):
	_name = 'gasoline.reading'
	def create(self, cr, uid, values, context=None):
		b =super(reading, self).create(cr, uid, values, context=context)	
		return b
	def _get_level(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for reading in self.browse(cr, uid, ids, context=context):
			result[reading.id] = reading.levelt-reading.level
		return result
	def _get_name(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for product in self.browse(cr, uid, ids, context=context):
			result[product.id] = product.product_id.name
		return result
	def _get_price(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for product in self.browse(cr, uid, ids, context=context):
			result[product.id] = product.product_id.list_price * product.levelf
		return result
	def _get_assign(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for product in self.browse(cr, uid, ids, context=context):
			flag = False
			if product.product_id:
				flag = True
			result[product.id] = flag
		return result
	_columns = {
		'name':fields.function(_get_name,type='char', string='name'),
		'date':fields.datetime(string="date Init"),
		'datef':fields.datetime(string="date end"),
		'level':fields.float(string="level Init",digits=(15,4)),
		'leveldiff':fields.float(string="level Init",digits=(15,4)),
		'levelt':fields.float(string="level end",digits=(15,4)),
		'levelf':fields.function(_get_level,type='float', string='finish levels',digits=(15,4)),
		'description':fields.text(string="Description"),
		'product_id':fields.many2one('product.product',string="Productos",domain="[('is_gasoline', '=', True )]"),
		'assign' : fields.function(_get_assign,type='boolean', string='assign'),
		'bit' : fields.boolean("bit"),
		'turn_id':fields.many2one("gasoline.turn",string="turn_id"),
		'price_list':fields.function(_get_price,type='float', string='Total',store=True),
		'side_product_id':fields.many2one('gasoline.side_product',string="level id"),
	}
	_defaults = {
	'leveldiff' : 0,
	'date' : datetime.now(),
		}
	_sql_constraints = [
        ('level_of_reading', 'CHECK (levelt >= level)', 'the final level must be greater than the initial'),
    ]
class gasoline_user(osv.Model):
	_name = 'gasoline.user'
	def _get_name(self, cr, uid, ids, field, arg, context=None):
		result = {}
		employee_obj = self.pool.get('hr.employee')
		hr_ids = employee_obj.search(cr,uid,[('is_dispenser', '=', True )],context=context)
		
		for user in self.browse(cr, uid, ids, context=context):
			employee_obj.write(cr,uid,user.employee_id.id,{'assigned':True},context=context)
			result[user.id] = user.employee_id.name
		for employee in employee_obj.browse(cr,uid,hr_ids,context=context):
			if len(employee.gasoline_user_ids) == 0 :
				employee_obj.write(cr,uid,employee.id,{'assigned':False},context=context)
		return result
	def unlink(self, cr, uid, ids, context=None):
		employee_obj = self.pool.get('hr.employee')
		for user in self.browse(cr,uid,ids,context=context):
			employee_obj.write(cr,uid,user.employee_id.id,{'assigned':False},context=context)
        	return super(gasoline_user, self).unlink(cr, uid, ids, context=context)
	def onchange_employee(self,cr,uid,ids,field,context=None):

		return {}

	_columns = {
		'name' :fields.function(_get_name,type='char', string='name'),
		'employee_id': fields.many2one('hr.employee',string="Employee",required=True),
	   	'status':fields.selection([('active', 'Active'),
                                   ('inactive', 'Inactive')], 'status',),
		}

	_defaults={
		'status':'inactive',
		}

class reading2(osv.Model):
	_order = "date desc"
	_name = 'gasoline.reading2'
	def _get_level(self, cr, uid, ids, field, arg, context=None):

		result = {}
		for reading in self.browse(cr, uid, ids, context=context):
			result[reading.id] = reading.levelt-reading.level
		return result

	def _get_name(self, cr, uid, ids, field, arg, context=None):

		result = {}
		for product in self.browse(cr, uid, ids, context=context):
			result[product.id] = product.product_id.name
		return result
	def create(self, cr, uid, values, context=None):
		id=self.pool.get('gasoline.product').browse(cr,uid,values['product_id2'],context=context).product_id.id
		product_obj=self.pool.get('product.template').browse(cr,uid,id,context=context)
		values['qty_available']=product_obj.qty_available
		values['qty_virtual']=product_obj.qty_available-values['level']
		b =super(reading2, self).create(cr, uid, values, context=context)
		#if self.pool.get('gasoline.product').browse(cr,uid,values["product_id2"],context=context).locale <= values["level"]:
		
		self.pool.get('gasoline.product').write(cr,uid,values["product_id2"],{'reading_id':b,'locale':values["level"]},context=context)
		#else:
			#raise osv.except_osv(_('Error!'), _('the level is less than the above'))
		return b
	def unlink(self, cr, uid, ids, context=None):
       		raise osv.except_osv(_('Unable to Delete!'), _('you cannot delete a reading Created'))
        	return super(reading2, self).unlink(cr, uid, ids, context=context)
	_columns = {
		'date':fields.datetime(string="date"),
		'level':fields.float(string="level"),
		'levelt':fields.float(string="level end"),
		'levelf':fields.function(_get_level,type='float', string='finish levels'),
		'description':fields.text(string="Description"),
		'bit' : fields.boolean("bit"),
		'product_id2':fields.many2one("gasoline.product",string="product"),
		'qty_available':fields.float(string="Available"),
		'qty_virtual':fields.float(string="Difference"),
		 'state' :fields.selection([('draft', 'Draft'),('finish','Finish')], 'state',),
		
	}
	_defaults = {
	'date' : datetime.now()
		} 
class journal(osv.Model):
	_name = 'gasoline.journal'
	def _get_money(self,cr,uid,ids,field,arg,context=None):
		res = {}
		for journal in self.browse(cr,uid,ids,context=context):
			total=0
			for order in journal.turn_id.order_ids:
				for stament in order.statement_ids:
					if stament.journal_id.id == journal.journal_id.id:
						total+=stament.amount	
			res[journal.id]=total
		return res
	_columns = {
		'journal_id':fields.many2one('account.journal',string="payment method",domain=[('type','in',['cash','bank']),('combustible','=',True)]),
		'money':fields.function(_get_money,type='float', string='Money'),
		'turn_id':fields.many2one('gasoline.turn',string="Turn"),

	}

class account_journal(osv.osv):
	_inherit = 'account.journal'
	_columns = {
		'combustible':fields.boolean(string="is payment of combustible?"),
	
	}

class pos_make_payment(osv.osv):
	_inherit = 'pos.make.payment'

class hr_employee(osv.osv):
	_inherit = 'hr.employee'
	def _get_value(self, cr, uid, ids, field, arg, context=None):
		result = {}
		hr_ids = self.pool.get('hr.employee').search(cr,uid,[],context=context)
		for hr_employee in self.browse(cr, uid, ids, context=context):
			if len(hr_employee.gasoline_user_ids)>0:
				result[hr_employee.id] = True
			else:
				result[hr_employee.id] = False
		return result
	_columns = {
        'is_dispenser': fields.boolean('Is dispenser?'),
	'assigned':fields.boolean(string='assigned'),
	'gasoline_user_ids':fields.one2many('gasoline.user','employee_id'),
}
	_defaults = {
	'assigned' : False,
		} 
class product_template(osv.osv):
	_inherit = 'product.template'
	_columns = {
        'is_gasoline': fields.boolean('Is Gasoline', help="Check if, this is a product is Gasoline."),
	'level': fields.float(string = "level"),
	'levelt': fields.float(string= "theorical level"),
}

class pos_order(osv.osv):
	_inherit = 'pos.order'
	def print_invoice(self, cr, uid, ids, context=None):
		'''
		This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
		'''
		assert len(ids) == 1, 'This option should only be used for a single id at a time'
		for order in self.browse(cr,uid,ids,context=context):
			if order.invoice_id:
				return self.pool['report'].get_action(cr, uid, order.invoice_id.id, 'gasoline.report_invoice', context=context)
		return self.pool['report'].get_action(cr, uid, ids, 'point_of_sale.report_receipt', context=context)

	def onchange_vehicle_id(self, cr, uid, ids, vehicle_id,  context=None):
		context = context or {}
		result={}
		values={}
		values['odometer']=None
		if not vehicle_id:
			return {'value':values}
		obj_vehicle=self.pool.get('fleet.vehicle').browse(cr,uid,vehicle_id,context=context)
		values['odometer']=obj_vehicle.odometer
		return {'value':values}
	def _get_diff(self,cr,uid,ids,field,arg,context=None):
		res = {}
		for order in self.browse(cr,uid,ids,context=context):
			total=0
			for line in order.lines:
				if line.price2:
					if line.price_unit != line.product_id.list_price:
						total+=(line.price2-line.price_unit)*line.qty
			res[order.id]=total
		return res
	def _get_type_id(self,cr,uid,ids,field,arg,context=None):
		res = {}
		for order in self.browse(cr,uid,ids,context=context):
			text="Sin Pago"
			if order.invoice_id and order.invoice_id.state != 'cancel':
				text="Factura Credito"
			elif len(order.statement_ids)>0:
				text="Factura Contado"
			res[order.id]=text
		return res
	def cancel_invoice(self, cr, uid, ids, context=None):
		self.pool.get('pos.order').write(cr,uid,ids,{'state':'cancel'},context=context)
		for order in self.pool.get('pos.order').browse(cr,uid,ids,context=context):
			if order.invoice_id:
				self.pool.get('account.invoice').signal_workflow(cr, uid, [order.invoice_id.id], 'invoice_cancel')
		return True
	def edit_invoice(self, cr, uid, ids, context=None):
		self.pool.get('pos.order').write(cr,uid,ids,{'state':'draft'},context=context)
		for order in self.pool.get('pos.order').browse(cr,uid,ids,context=context):
			if order.invoice_id:
				self.pool.get('account.invoice').action_cancel_draft(cr, uid, [order.invoice_id.id], context=context)
				#self.pool.get('account.invoice').unlink(cr,uid,[order.invoice_id.id],context=context)
		return True
		return super(pos_order, self).unlink(cr, uid, ids, context=context)
	def unlink(self, cr, uid, ids, context=None):
		for rec in self.browse(cr, uid, ids, context=context):
			if rec.state not in ('draft','cancel'):
				raise osv.except_osv(_('Unable to Delete!'), _('In order to delete a sale, it must be new or cancelled.'))
		self.pool.get('pos.order').write(cr,uid,ids,{'state':'cancel'},context=context)
		for order in self.pool.get('pos.order').browse(cr,uid,ids,context=context):
			if order.invoice_id:
				self.pool.get('account.invoice').unlink(cr,uid,[order.invoice_id.id],context=context)
		return True
		return super(pos_order, self).unlink(cr, uid, ids, context=context)
	def action_paid(self, cr, uid, ids, context=None):
		for order in self.browse(cr,uid,ids,context=context):
			if not order.turn_id:
				self.write(cr, uid, ids, {'state': 'paid'}, context=context)
				self.create_picking(cr, uid, ids, context=context)
			if order.invoice_id:
				
				if order.invoice_id.state != 'cancel':
					raise osv.except_osv(_('Error!'), _('Ya existen pagos para esta factura'))	
		
		
		return True
	def action_invoice(self, cr, uid, ids, context=None):
		inv_ref = self.pool.get('account.invoice')
		inv_line_ref = self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')
		inv_ids = []
		order_id=False
		for order in self.pool.get('pos.order').browse(cr, uid, ids, context=context):
			inv_id=0
			if not order.invoice_id:
				
				if not order.partner_id:
					raise osv.except_osv(_('Error!'), _('Please provide a partner for the sale.'))	
				tot=0
				for paid in order.statement_ids:
					tot+=paid.amount
				if tot>0:	
					raise osv.except_osv(_('Error!'), _('Ya existen pagos para esta factura'))	
				acc = order.partner_id.property_account_receivable.id
				inv = {
					'name': order.name,
		       		 	'origin': order.name,
		       			'account_id': acc,
		       		 	'journal_id': order.sale_journal.id or None,
		       		 	'type': 'out_invoice',
		       			'reference': order.name,
		       		 	'partner_id': order.partner_id.id,
				 	'comment': order.note or '',
				 	'currency_id': order.pricelist_id.currency_id.id, # considering partner's sale pricelist's currency
		    }
				inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', order.partner_id.id)['value'])
				if not inv.get('account_id', None):
					inv['account_id'] = acc
				inv_id = inv_ref.create(cr, uid, inv, context=context)
				self.write(cr, uid, [order.id], {'invoice_id': inv_id,}, context=context)
				inv_ids.append(inv_id)
			else:
				inv_id=order.invoice_id.id
				inv_ids.append(inv_id)
			inv_line_ids=inv_line_ref.search(cr,uid,[('invoice_id','=',inv_id)],context=context)
			inv_line_ref.unlink(cr,uid,inv_line_ids,context=context)
			for line in order.lines:

				inv_line = {
                    			'invoice_id': inv_id,
                    			'product_id': line.product_id.id,
                    			'quantity': line.qty,
                			}
				inv_name = product_obj.name_get(cr, uid, [line.product_id.id], context=context)[0][1]
				inv_line.update(inv_line_ref.product_id_change(cr, uid, [],
                                                               line.product_id.id,
                                                               line.product_id.uom_id.id,
                                                               line.qty, partner_id = order.partner_id.id,
                                                               fposition_id=order.partner_id.property_account_position.id)['value'])
				inv_line['price_unit'] = line.price_unit
				inv_line['discount'] = line.discount
				inv_line['name'] = inv_name
				inv_line['invoice_line_tax_id'] = [(6, 0, [x.id for x in line.product_id.taxes_id] )]
				inv_line_ref.create(cr, uid, inv_line, context=context)
			inv_ref.button_reset_taxes(cr, uid, [inv_id], context=context)
			self.signal_workflow(cr, uid, [order.id], 'invoice')
			#self.create_picking(cr, uid, [order.id], context=context)
			inv_ref.signal_workflow(cr, uid, [inv_id], 'validate')
			order_id=order.id
		if not inv_ids: return {}
		mod_obj = self.pool.get('ir.model.data')
		res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
		res_id = res and res[1] or False
		self.pool.get('account.invoice').signal_workflow(cr, uid,[inv_id], 'invoice_open')
		self.pool.get('pos.order').write(cr,uid,order_id,{'is_invoice':True},context=context)
		return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_id,
        }
	def _get_invoice(self, cr, uid, ids, field, arg, context=None):
		result = {}
		for order in self.browse(cr, uid, ids, context=context):
			flag = False
			if order.invoice_id:
				if order.invoice_id.state not in ['cancel','draft'] :
					flag = True
			result[order.id] = flag
		return result		

	_columns = {
        'is_gasoline': fields.boolean('Is Gasoline', help="Check if, this is a product is Gasoline."),
	'turn_id':fields.many2one('gasoline.turn',string="Turn"),
	'difference':fields.function(_get_diff,type='float', string='Diferencia'),
	'nreference':fields.char(string = "Reference Number"),
	'odometer': fields.float(string = "Odometer"),
	'vehicle_id':fields.many2one('fleet.vehicle',string="Vehicle"),
	'type_id2':fields.function(_get_type_id,type='char', string='Type'),
	'is_invoice':fields.function(_get_invoice,type='boolean', string='Type',store=True),
	}
class gasoline_pos_order_line(osv.osv):
	_inherit = 'pos.order.line'
	def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False, context=None):
		context = context or {}
		if not product_id:
			return {}
		if not pricelist:
			raise osv.except_osv(_('No Pricelist!'),
			_('You have to select a pricelist in the sale form !\n' \
			'Please set one before choosing a product.'))

		price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],product_id, qty or 1.0, partner_id)[pricelist]

		result = self.onchange_qty(cr, uid, ids, product_id, 0.0, qty, price, context=context)
		result['value']['price_unit'] = price
		result['value']['price2'] = price
		return result
	def create(self, cr, uid, values, context=None):
		b =super(gasoline_pos_order_line, self).create(cr, uid, values, context=context)
		price=self.pool.get('pos.order.line').browse(cr,uid,b,context=context).product_id.list_price
		self.pool.get('pos.order.line').write(cr,uid,b,{'price2':price},context=context)
		return b
	_columns = {
        'price2': fields.float('price2'),
}
	_defaults = {
	'price2' : 0,
		} 


class pos_config(osv.osv):
	_inherit = 'pos.config'
	_columns = {
        'combustible': fields.boolean('Is TPV for gasoline', help="Check if, this is a product is Gasoline."),
}
class pos_session(osv.osv):
	_inherit = 'pos.session'
	def _confirm_orders(self, cr, uid, ids, context=None):
		account_move_obj = self.pool.get('account.move')
		pos_order_obj = self.pool.get('pos.order')
		for session in self.browse(cr, uid, ids, context=context):
			local_context = dict(context or {}, force_company=session.config_id.journal_id.company_id.id)
			order_ids=[]
			for order in session.order_ids:
				if (order.state == 'paid' and len(order.lines)>0):
					order_ids.append(order.id)
			#order_ids = [order.id for order in session.order_ids if (order.state == 'paid' and len(order.lines)>0)]

			move_id = account_move_obj.create(cr, uid, {'ref' : session.name, 'journal_id' : session.config_id.journal_id.id, }, context=local_context)

			pos_order_obj._create_account_move_line(cr, uid, order_ids, session, move_id, context=local_context)

			for order in session.order_ids:
				if order.state == 'done':
					continue
				if order.state not in ('paid', 'invoiced','cancel'):
					raise osv.except_osv(
						_('Error!'),
						_("You cannot confirm all orders of this session, because they have not the 'paid' status"))
				else:
					pos_order_obj.signal_workflow(cr, uid, [order.id], 'done')

		return True
class pos_order_line(osv.osv):
	_inherit = 'pos.order.line'
class pos_account_invoice(osv.osv):
	_inherit = 'account.invoice'
	def _get_nreference(self,cr,uid,ids,field,arg,context=None):
		res = {}
		order_obj=self.pool.get('pos.order')
		for invoice in self.browse(cr,uid,ids,context=context):
			order_ids=order_obj.search(cr,uid,[('invoice_id','=',invoice.id)],context=context)
			total=""
			for order in order_obj.browse(cr,uid,order_ids,context=context):
				total=order.nreference
			res[invoice.id]=total
		return res
	def _get_odometer(self,cr,uid,ids,field,arg,context=None):
		res = {}
		order_obj=self.pool.get('pos.order')
		for invoice in self.browse(cr,uid,ids,context=context):
			order_ids=order_obj.search(cr,uid,[('invoice_id','=',invoice.id)],context=context)
			total=""
			for order in order_obj.browse(cr,uid,order_ids,context=context):
				total=order.vehicle_id.odometer
			res[invoice.id]=total
		return res
	def _get_vehicle(self,cr,uid,ids,field,arg,context=None):
		res = {}
		order_obj=self.pool.get('pos.order')
		for invoice in self.browse(cr,uid,ids,context=context):
			order_ids=order_obj.search(cr,uid,[('invoice_id','=',invoice.id)],context=context)
			total=""
			for order in order_obj.browse(cr,uid,order_ids,context=context):
				total=order.vehicle_id.model_id.modelname
			res[invoice.id]=total
		return res
	def _get_plaque(self,cr,uid,ids,field,arg,context=None):
		res = {}
		order_obj=self.pool.get('pos.order')
		for invoice in self.browse(cr,uid,ids,context=context):
			order_ids=order_obj.search(cr,uid,[('invoice_id','=',invoice.id)],context=context)
			total=""
			for order in order_obj.browse(cr,uid,order_ids,context=context):
				total=order.vehicle_id.license_plate
			res[invoice.id]=total
		return res
	_columns = {
	'nreference':fields.function(_get_nreference,type='char', string='Reference'),
	'odometer': fields.function(_get_odometer,type='float', string='odometer'),
	'vehicle':fields.function(_get_vehicle,type='char', string='vehicle'),
	'plaque':fields.function(_get_plaque,type='char', string=' plaque'),
	}
class pos_fleet_vehicle(osv.osv):
	_inherit = 'fleet.vehicle'
	_columns = {
        'partner_id': fields.many2one('res.partner',string="Partner"),
}
class pos_make_payment(osv.osv_memory):
	_inherit = 'pos.make.payment'
	def check(self, cr, uid, ids, context=None):
		context = context or {}
		order_obj = self.pool.get('pos.order')
		active_id = context and context.get('active_id', False)

		order = order_obj.browse(cr, uid, active_id, context=context)
		amount = order.amount_total - order.amount_paid
		data = self.read(cr, uid, ids, context=context)[0]
		# this is probably a problem of osv_memory as it's not compatible with normal OSV's
		data['journal'] = data['journal_id'][0]

		if amount != 0.0:
			order_obj.add_payment(cr, uid, active_id, data, context=context)

		if order_obj.test_paid(cr, uid, [active_id]):
			order_obj.signal_workflow(cr, uid, [active_id], 'paid')
			return {'type' : 'ir.actions.act_window_close' }

		return self.launch_payment(cr, uid, ids, context=context)
	def _default_amount(self, cr, uid, context=None):
		order_obj = self.pool.get('pos.order')
		active_id = context and context.get('active_id', False)
		if active_id:
			order = order_obj.browse(cr, uid, active_id, context=context)
			return order.amount_total - order.amount_paid
		return False

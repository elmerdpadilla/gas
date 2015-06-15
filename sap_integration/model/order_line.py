# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import workflow
from dateutil.relativedelta import relativedelta
from passlib.context import CryptContext
default_crypt_context = CryptContext(
	# kdf which can be verified by the context. The default encryption kdf is
	# the first of the list
	['pbkdf2_sha512', 'md5_crypt'],
	# deprecated algorithms are still verified as usual, but ``needs_update``
	# will indicate that the stored hash should be replaced by a more recent
	# algorithm. Passlib 1.6 supports an `auto` value which deprecates any
	# algorithm but the default, but Debian only provides 1.5 so...
	deprecated=['md5_crypt'],
)
class sap_user(osv.osv):
    _inherit = 'res.users'
    _columns = {
		'store_id':fields.many2one('sap_integration.stores',string="Store"),
		'discount_order': fields.boolean(string="Discount For Order"),
		'discount_order_line': fields.boolean(string="Discount For Order Line"),
		'discount_price': fields.boolean(string="price for order line"),
		}
class sap_order(osv.osv):
    _inherit = 'sale.order'
    def create(self, cr, uid, values, context=None):
	seq_obj = self.pool.get('ir.sequence')
	name = "/"
	order_obj = self.pool.get('account.journal')
	diario =self.pool.get('res.users').browse(cr,uid,uid,context=context).store_id
	if diario.sequence_id:
	    if not diario.sequence_id.active:
		raise osv.except_osv(_('Configuration Error !'),_('Please activate the sequence of selected time !'))
	    c = dict(context)
	    name = seq_obj.next_by_id(cr, uid, diario.sequence_id.id, context=c)
	values['name']=name
	b =super(sap_order, self).create(cr, uid, values, context=context)	
	return b

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        if not part:
            return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}
        part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
        addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        payment_term = part.property_payment_term and part.property_payment_term.id or False
        dedicated_salesman = part.user_id and part.user_id.id or uid
	fiscal=None
	if part.property_account_position:
	    fiscal=part.property_account_position.id
	else:
	    fiscal=None
        val = {
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'payment_term': payment_term,
            'user_id': dedicated_salesman,
	    'name_show' :part.name,
	    'is_visible' : part.change_name,
	    'disc':part.discount,
	    'codepartner':part.sap_id,
        }
        delivery_onchange = self.onchange_delivery_id(cr, uid, ids, False, part.id, addr['delivery'], False,  context=context)
        val.update(delivery_onchange['value'])
	val['fiscal_position']=fiscal
	
        if pricelist:
            val['pricelist_id'] = pricelist
	    val['tarifa']= part.property_product_pricelist.name
        sale_note = self.get_salenote(cr, uid, ids, part.id, context=context)
        if sale_note: val.update({'note': sale_note})  
        return {'value': val}
    def print_quotation(self, cr, uid, ids, context=None):
        '''
        This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        self.signal_workflow(cr, uid, ids, 'quotation_sent')
        return self.pool['report'].get_action(cr, uid, ids, 'reports.report_print', context=context)
    def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):
        """ Wrapper because of direct method passing as parameter for function fields """
        return self._amount_all(cr, uid, ids, field_name, arg, context=context)
    def _amount_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0.0)/100.0)* (1-(line.max or 0.0)/100.0), line.product_uom_qty, line.product_id, line.order_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val

    def onchange_fiscal_position(self, cr, uid, ids, fiscal_position, order_lines, context=None):
        '''Update taxes of order lines for each line where a product is defined

        :param list ids: not used
        :param int fiscal_position: sale order fiscal position
        :param list order_lines: command list for one2many write method
        '''
        order_line = []
        fiscal_obj = self.pool.get('account.fiscal.position')
        product_obj = self.pool.get('product.product')
        line_obj = self.pool.get('sale.order.line')

        fpos = False
        if fiscal_position:
            fpos = fiscal_obj.browse(cr, uid, fiscal_position, context=context)
        
        for line in order_lines:
            # create    (0, 0,  { fields })
            # update    (1, ID, { fields })
            if line[0] in [0, 1]:
                prod = None
                if line[2].get('product_id'):
                    prod = product_obj.browse(cr, uid, line[2]['product_id'], context=context)
                elif line[1]:
                    prod =  line_obj.browse(cr, uid, line[1], context=context).product_id
                if prod and prod.taxes_id:
                    line[2]['tax_id'] = [[6, 0, fiscal_obj.map_tax(cr, uid, fpos, prod.taxes_id)]]
                order_line.append(line)

            # link      (4, ID)
            # link all  (6, 0, IDS)
            elif line[0] in [4, 6]:
                line_ids = line[0] == 4 and [line[1]] or line[2]
                for line_id in line_ids:
                    prod = line_obj.browse(cr, uid, line_id, context=context).product_id
                    if prod and prod.taxes_id:
                        order_line.append([1, line_id, {'tax_id': [[6, 0, fiscal_obj.map_tax(cr, uid, fpos, prod.taxes_id)]]}])
                    else:
                        order_line.append([4, line_id])
            else:
                order_line.append(line)
        return {'value': {'order_line': order_line}}
    def action_view(self, cr, uid, ids, context=None):
	id = ids[0]
	return {
            'type': 'ir.actions.act_window',
	    'name': 'authenticate',
             'view_type': 'form',
             'view_mode': 'form',
            'res_model': 'sap_integration.password',
            'target': 'new',
	    'context': id,
	 
        }
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
		'amount_discount':0.0,
            }
            val = val1 = val2= 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.tprice_subtotal
		for tax in line.tax_id:
		    val += (line.tprice_subtotal-line.tprice_subtotal*line.max/100 )*tax.amount
		val2 += line.tprice_subtotal*line.max/100
	    self.pool.get('sale.order').write(cr,uid,order.id,{'amount_discount':val2},context=context)
            self.pool.get('sale.order').write(cr,uid,order.id,{'amount_tax':val},context=context)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
	    res[order.id]['amount_discount'] = cur_obj.round(cr, uid, cur, val2)
            #res[order.id]['amount_tax'] = val
            #res[order.id]['amount_untaxed'] = val1
	    #res[order.id]['amount_discount'] = val2
	    val3= val1+val-val2
            res[order.id]['amount_total'] = cur_obj.round(cr, uid, cur, val3) 
	    #res[order.id]['amount_total'] = val3
        return res
    def button_dummy(self, cr, uid, ids, context=None):
	for order in self.browse(cr,uid,ids,context=context):
	    tax=0.0
	    for line in order.order_line:
		dproduct=line.codebar_id.item_id.discount
		final=order.disc;
		if order.disc>dproduct:
		    final = dproduct

		self.pool.get('sale.order.line').write(cr,uid,line.id,{'max':final},context=context)
	        for taxes in line.tax_id:
		    tax+= (line.tprice_subtotal-line.tprice_subtotal*final/100 )*taxes.amount
	    self.pool.get('sale.order').write(cr,uid,order.id,{'amount_tax':tax},context=context)
	    return True
        return {'value': {'tienda':"as",'client_order_ref': 0.5},}
    def discount_sap_change(self, cr, uid, ids,discount,order_lines, partner_id=False , context=None):
	obj_line=self.pool.get('product.product')
	order_line=[]
	disc=0
	line_obj = self.pool.get('sale.order.line')
	if partner_id:
	    obj_partner=self.pool.get('res.partner').browse(cr,uid,partner_id,context=context)
	    disc=discount
	    if( obj_partner.discount)<=discount:
		price = obj_partner.discount
		disc=price
        if len(ids)==1:
	    id=ids[0]
	    sap=self.pool.get('sap_integration.password').search(cr,uid,[('order_id', '=', id )],context=context)
	    if len(sap)>0:
		obj_pass=self.pool.get('sap_integration.password').browse(cr,uid,sap[0],context=context)

		if disc<obj_pass.discount:
		    disc=obj_pass.discount
        for line in order_lines:
            if line[0] in [4, 6]:
                line_ids = line[0] == 4 and [line[1]] or line[2]
                for line_id in line_ids:
                    prod = line_obj.browse(cr, uid, line_id, context=context).product_id
                    if prod :
			if prod.discount>disc:
                            order_line.append([1, line_id, {'max':  disc}])
			else:
			    order_line.append([1, line_id, {'max':  prod.discount}])
                    else:
                        order_line.append([4, line_id])
            else:
                order_line.append(line)
	return	{'value': {'order_line':order_line},}
    def _get_dated(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for order in self.browse(cr,uid,ids,context=context):
	    dt = datetime.strptime(order.date_order, "%Y-%m-%d %H:%M:%S").date()
	    result[order.id]=dt
	return result
    def _get_discount(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for order in self.browse(cr,uid,ids,context=context):
	    dt = 0.0
	    for line in order.order_line:
		dt += line.tprice_subtotal*line.max/100
	    result[order.id]=dt
	return result
    def _get_ediscount(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for order in self.browse(cr,uid,ids,context=context):
	    dt = 0.0
	    if order.amount_untaxed:
	        dt = 100*order.amount_discount/order.amount_untaxed
	    result[order.id]=dt
	return result
    def _get_disc(self, cr, uid, ids, field, arg, context=None):
        result = {}
	sap=[]
	if len(ids)==1:
	    id=ids[0]
	    sap=self.pool.get('sap_integration.password').search(cr,uid,[('order_id', '=', id )],context=context)
	    if len(sap)>0:
		obj_pass=self.pool.get('sap_integration.password').browse(cr,uid,sap[0],context=context)
		result[id]=obj_pass.discount
	    else:
		result[id]=0
	return result
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
    def _get_isvisible(self, cr, uid, ids, field, arg, context=None):
	result = {}
	for order in self.browse(cr,uid,ids,context=context):
	    result[order.id]=order.partner_id.change_name
	return result
    def _get_tarifa(self, cr, uid, ids, field, arg, context=None):
	result = {}
	for order in self.browse(cr,uid,ids,context=context):
	    result[order.id]=order.pricelist_id.name
	return result
    def _get_leyenda(self, cr, uid, ids, field, arg, context=None):
	result = {}
	for order in self.browse(cr,uid,ids,context=context):
	    if order.fiscal_position:
		result[order.id]=order.fiscal_position.leyenda
	    elif order.state in ['draft','sent']:
		result[order.id]=_("Quotation")
	    else:
		result[order.id]=_("Order")
	return result
    def _get_codepartner(self, cr, uid, ids, field, arg, context=None):
	result = {}
	for order in self.browse(cr,uid,ids,context=context):
	    result[order.id]=order.partner_id.sap_id
	return result
    def addcode_fun(self, cr, uid, ids,addcode,order_lines, partner_id=False,discpartner=False,pricelist_id=False,fiscal_position=False, context=None):
 	context = context or {}
	id=1
	obj_codebars=self.pool.get('product.codebars')
	obj_product=self.pool.get('product.product')
	obj_ve=self.pool.get('product.pricelist.version')
	obj_sol= self.pool.get('sale.order.line')

	sol_ids=obj_sol.search(cr,uid,[('order_id','in',ids)],context=context)
	obj_stock=self.pool.get('sap.integration.stock')
	qty=1
	pdiscount=0
	value={}
	color=False
	tcolor=False
	
	if addcode:


	    array=[]
	    array=obj_codebars.search(cr,uid,[('bar_code','=',addcode)],context=context)
	    if len(array)==0:
		array=obj_codebars.search(cr,uid,[('item_code','=',addcode)],context=context)
	    if len(array)>0:
		array[0]=(array[0])
	    if len(array)>0:
		for codebar in obj_codebars.browse(cr,uid,array,context=context):
		    uom=codebar.uom_id.id
		    obj_uom=self.pool.get('product.uom').browse(cr,uid,uom,context=context)
		    ratio =obj_uom.factor
		    if codebar.uom_id.uom_type == 'smaller' and uom ==codebar.uom_id.id:
	    		ratio= 1/ratio
	    	    qtyreal=ratio*qty
		    discount=0
		    value['comment']=False
		    value['order_id']=id
		    value['codebar_id']=codebar.id
		    value['state']='draft'
		    value['product_uos']=False
		    value['product_uom']= codebar.uom_id.id
		    value['product_uom_qty']=1
		    value['product_uos_qty']=1
		    value['color']=False
		    domain = {}
		    arraysequence=[]
		    product=codebar.item_id.id
		    #domain = {'product_uom':[('category_id', '=', obj_codebars.uom_id.category_id.id)],}
		    product_tmp=self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',product)],context=context)
		    product_ids=obj_product.search(cr,uid,[('product_tmpl_id','=',product)],context=context)
		    if len(product_tmp)>0:
			value['product_id']= product_tmp[0]
		    version_ids=obj_ve.search(cr,uid,[('product_id','=',product),('pricelist_id','=',pricelist_id)],context=context)
		    for version in obj_ve.browse(cr,uid,version_ids,context=context):
			price = version.price
			value['max']=0
			value['discount']=0
			value['name']=version.product_id.name
			pdiscount=version.product_id.discount
			taxes=[]
			if not fiscal_position:
			    for tax in version.product_id.taxes_id:
			        taxes.append(tax.id)
            		else:
                	    fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
                	    tax2= self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, version.product_id.taxes_id)
			    for tax in tax2:
			       taxes.append(tax)			
			for sequence in version.product_pricelist_discount_ids:
			    arraysequence.append([sequence.amount,sequence.discount])
			inc=1
			if len(arraysequence)>0:
			    tam = len(arraysequence)
			    for inc in range(1,tam,inc*3+1):
				while inc>0:
				    for i in range(inc,tam):
					j=i
					temp=arraysequence[i]
					while j>=inc and arraysequence[j-inc][0]<temp[0]:
					    arraysequence[j]=arraysequence[j-inc]
					    j=j-inc
					arraysequence[j]=temp
				    inc=inc/2
			    for sequence in arraysequence:
				if qtyreal>=sequence[0]:
				    discount=sequence[1]
				    color=True
				    break
			price*=qtyreal
			price-=price*discount/100
			if price == 0:
			    tcolor=True
		        price2=price
			value['price_subtotal']=price
			value['tprice_subtotal']=price
			price3=price/qtyreal
			price4=price3*ratio
			value['tax_id']=[[6,False,taxes]]
			value['price_unit']=price4
			value['price_unit_fun']=price4
			value['price']=price3
			value['price_show']=price3
			value['color']=color
			value['tcolor']=tcolor
			value['nm']=len(sol_ids)+len(order_lines)
	    		if not discpartner:
		            discpartner=self.pool.get('res.partner').browse(cr,uid,partner_id,context=context).discount
			if discpartner>pdiscount:
			    value['max']=pdiscount
			else:
			    value['max']=discpartner
		    order_lines.append(value)
            	    return {'value': {'addcode': None,'order_line':order_lines},}
	    else:
	    	#raise osv.except_osv(_('Barcode No Found'),_("The Barcode or itemcode dont Exist") )
		#return self.pool.get('warning').info(cr, uid, title='Barcode No Found', message="%sThe Barcode or itemcode dont Exist")
		return {'value': {'addcode': None},}
    _columns = {
		'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line','disc'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty','max'], 10),
            },
            multi='sums', help="The tax amount."),
        	'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line','disc'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty','max'], 10),
            },
            multi='sums', help="The total amount."),
		'date_end': fields.date(string="Date End"),
		'date_orderd':fields.function(_get_dated,type='date', string='Date'),
		'amount_discount':fields.float(string='Discount',digits_compute=dp.get_precision('Account')),
		'efective_discount':fields.function(_get_ediscount,type='float', string='Discount efective',digits_compute=dp.get_precision('Account')),
		'disc':fields.float(string='Discount',digits_compute=dp.get_precision('Account')),
		'disc2':fields.function(_get_disc,type='float',string='Discount',digits_compute=dp.get_precision('Account')),
		'name_show':fields.char(string="name"),
		'is_visible':fields.function(_get_isvisible,type='boolean',string="Visible"),
		'tarifa':fields.function(_get_tarifa,type='char',string="Tarifa"),
		'tienda':fields.char(string="tienda"),
		'nstore':fields.char(string="tienda"),
		'leyenda':fields.function(_get_leyenda,type='char',string="Leyenda"),
		'addcode':fields.char(string="Barcode"),
		'codepartner':fields.function(_get_codepartner,type='char',string="codepartner",store=True),
		}

    _defaults = {
	'disc' : 0.0,
	'date_order' : lambda *a: datetime.now(),
	'date_end' :lambda *a: datetime.now()+relativedelta(days=5),
'tienda': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid,context).store_id.sequence_id.name,
'nstore': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid,context).store_id.name,
		}



class sap_order_line(osv.osv):
    _inherit = 'sale.order.line'
    def action_view(self, cr, uid, ids, context=None):
	id = ids[0]
	return {
            'type': 'ir.actions.act_window',
	    'name': 'authenticate',
             'view_type': 'form',
             'view_mode': 'form',
            'res_model': 'sap_integration.password_line',
            'target': 'new',
	    'context': id,
	    'price':12.0,
	 
        }
    def _get_priceU(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=line.price
	return result
    def _get_itemcode(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=line.product_id.item_code
	return result
    def _get_nm(self, cr, uid, ids, field, arg, context=None):
        result = {}
	val=1
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=val
	    val+=1
	return result
    def _get_mtax(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=""
	    for tax in line.tax_id:
			if tax.description:
				result[line.id]+=tax.description
	return result
    def _get_id(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=line.codebar_id.uom_id.category_id.id
	return result
    def _get_name(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=line.codebar_id.description
	return result
    def _get_ttcolor(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=False
	    if line.tprice_subtotal==0:
	    	result[line.id]=True
	return result
    def _get_maxdiscount(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=line.product_id.discount
	return result
    def _get_pricegravad(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    imp=line.price
	    for tax in line.tax_id:
		imp+=line.price*tax.amount
	    result[line.id]=imp
	return result
    def product_uom_change(self, cursor, user, ids, pricelist, codebar_id,inventory, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, tax_id=False,context=None):
        context = context or {}
        lang = lang or ('lang' in context and context['lang'])
        if not uom:
            return {'value': {'price_unit': 0.0, 'product_uom' : uom or False}}
        return self.barcode_id_change(cursor, user, ids, pricelist, codebar_id,inventory,
                qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name,
                partner_id=partner_id, lang=lang, update_tax=update_tax,
                date_order=date_order,tax_id=tax_id, context=context)

    def discount_sap_change(self, cr, uid, ids,discount, pricelist, barcode, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or ('lang' in context and context['lang'])
	obj_codebars=self.pool.get('product.codebars').browse(cr,uid,barcode,context=context)
	obj_product=self.pool.get('product.template').browse(cr,uid,obj_codebars.item_id.id,context=context)
	price= discount
	if (obj_product.discount)<discount:
	    price= obj_product.discount	
        return {'value': {'discount': price},}

    def disc_sap_change(self, cr, uid, ids,discount, pricelist, barcode, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or ('lang' in context and context['lang'])
	obj_codebars=self.pool.get('product.codebars').browse(cr,uid,barcode,context=context)
	obj_product=self.pool.get('product.template').browse(cr,uid,obj_codebars.item_id.id,context=context)
	price= discount
	if (obj_product.discount)<discount:
	    price= obj_product.discount
        return {'value': {'max': price},}

    def pn_sap_change(self, cr, uid, ids,discount, price, qty=0, context=None):
	total=0
	total=qty*price
	total-=total*discount/100
        return {'value': {'price_subtotal': total,'tprice_subtotal': total},}

    def barcode_id_change(self, cr, uid, ids, pricelist, barcode,inventory_ids, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False, discpartner=False ,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,tax_id=False, context=None):
	if not barcode:
	    return {}
	if not partner_id:
	    return {}
	obj_codebars=self.pool.get('product.codebars').browse(cr,uid,barcode,context=context)	
	    #return {'value': {'product_id': obj_codebars.item_id.id,}}
	flag=True
	ratio =1
        if not uom:
	    uom=obj_codebars.uom_id.id
	    flag=False
	    ratio = obj_codebars.uom_id.factor
	else:
	
	    obj_uom=self.pool.get('product.uom').browse(cr,uid,uom,context=context)
	    ratio =obj_uom.factor
	product=0
        domain = {}
	product=obj_codebars.item_id.id
	domain = {'product_uom':
                        [('category_id', '=', obj_codebars.uom_id.category_id.id)],}
	name=obj_codebars.description
	if obj_codebars.uom_id.uom_type == 'smaller' and uom == obj_codebars.uom_id.id:
	    ratio= 1/ratio
	equivalent_qty=ratio
	qtyreal=ratio*qty
	discount=0
	price =0
	price2=0
	price3=0
	price4=0
	discp=0
	product_tmp2=0
	color=False
	tcolor=False
	arraysequence=[]
	seq=[]
	if pricelist and barcode:
	    partner_obj = self.pool.get('res.partner')
	    partner = partner_obj.browse(cr, uid, partner_id)
	    discp=partner.discount
	    lang = partner.lang
	    context_partner = {'lang': lang, 'partner_id': partner_id}
	    product_tmp=self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',product)],context=context)
	    if len(product_tmp)==0:
		raise
	    else:
		product_tmp2=product_tmp[0]
	    obj_tarifa=self.pool.get('product.pricelist').browse(cr,uid,pricelist,context=context)
	    product_obj = self.pool.get('product.product')
	    fiscal_obj = self.pool.get('account.fiscal.position')
	    obj_stock=self.pool.get('sap.integration.stock')
            fpos = False
            product_obj = product_obj.browse(cr, uid, product_tmp, context=context_partner)
	    tax=[]
            if not fiscal_position:
                fpos = partner.property_account_position or False
            else:
                fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
	    if True: #The quantity only have changed
		if tax_id:
		    if len(tax_id[0][2])>0:
			tax=tax_id[0][2]
		    else:
			tax=self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)
	    tax_id=[(6,0,tax)]
	    obj_ve=self.pool.get('product.pricelist.version')
	    tprice_subtotal=0.0
	    for tarifa in obj_tarifa:
	        version_ids=obj_ve.search(cr,uid,[('product_id','=',product),('pricelist_id','=',tarifa.id)],context=context)
	        for version in obj_ve.browse(cr,uid,version_ids,context=context):
                    if version.product_id.id == product:
			price = version.price;
			for sequence in version.product_pricelist_discount_ids:
			    seq.append(sequence.id)
			    arraysequence.append([sequence.amount,sequence.discount])
			inc=1		
			if len(arraysequence)>0:
			    tam = len(arraysequence)
			    for inc in range(1,tam,inc*3+1):
				while inc>0:
				    for i in range(inc,tam):
					j=i
					temp=arraysequence[i]
					while j>=inc and arraysequence[j-inc][0]<temp[0]:
					    arraysequence[j]=arraysequence[j-inc]
					    j=j-inc
					arraysequence[j]=temp
				    inc=inc/2
			    for sequence in arraysequence:
				if qtyreal>=sequence[0]:
				    discount=sequence[1]
				    color=True
			price*=qtyreal
			price-=price*discount/100
			if price == 0:
			    tcolor=True
		        price2=price
			price3=price/qtyreal
			price4=price3*ratio
	    mtax=""
	    itax=1
	    pricegravad=price3
	    for product in product_obj:
		for tax in product.taxes_id:
		    itax*=(1+tax.amount)
		    mtax+=tax.description
		    pricegravad+=pricegravad*tax.amount
	    pdiscount=product_obj.discount
	    itax=itax-1
	    inventory=[]
	    dseq=[]
	    stock_ids=obj_stock.search(cr,uid,[('product_id','=',obj_codebars.item_id.id)],context=context)
	    inventory.append((6,0,stock_ids))
	    dseq.append((6,0,seq))
	    if discpartner:
		pdiscount=discpartner
	    else:
		pdiscount=self.pool.get('res.partner').browse(cr,uid,partner_id,context=context).discount
	    if flag:
	        return {'value': {'discount':0,'discount_fun':0,'sequencediscount':dseq,'tax_total':itax, 'inventory':inventory,'equivalent_qty':equivalent_qty,'tprice_subtotal':price2, 'max':pdiscount,'pricegravad':pricegravad,'discountmax':product_obj.discount,'price_unit': price4,'price_unit_fun': price4,'price': price3,'price_show':price3,'product_id':product_tmp2,'name':name,'color':color,'tcolor':tcolor,'tax_id':tax_id,'mtax':mtax},'domain':domain,}
	    else:
		return {'value': {'discount':0,'discount_fun':0, 'sequencediscount':dseq,'tax_total':itax,'inventory':inventory,'equivalent_qty':equivalent_qty,'tprice_subtotal':price2, 'max':pdiscount,'pricegravad':pricegravad,'discountmax':product_obj.discount,'price_unit': price4,'price_unit_fun': price4,'product_uom':uom,'price': price3,'price_show':price3,'product_id':product_tmp2,'name':name,'color':color,'tcolor':tcolor,'tax_id':tax_id,'mtax':mtax},'domain':domain}		
        context = context or {}
        lang = lang or context.get('lang', False)
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
        warning = False
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        partner = partner_obj.browse(cr, uid, partner_id)
        lang = partner.lang
        context_partner = {'lang': lang, 'partner_id': partner_id}
        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False

        fpos = False
        if not fiscal_position:
            fpos = partner.property_account_position or False
        else:
            fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
        if update_tax: #The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom or result.get('product_uom'),
                        'date': date_order,
                        })[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
	if pricelist:
	    product_tmp=self.pool.get('product.product').browse(cr,uid,product,context=context).product_tmpl_id
	    idproduct= product_tmp.id
	    obj_tarifa=self.pool.get('product.pricelist').browse(cr,uid,pricelist,context=context)
            precio=0
	    obj_ve=self.pool.get('product.pricelist.version')
	    version_ids=obj_ve.search(cr,uid,[('product_id','=',idproduct),('pricelist_id','=',pricelist)],context=context)
	    for version in obj_ve.browse(cr,uid,version_ids,context=context):
                if version.product_id.id == idproduct:
		    precio = version.price;
	    		
        context = context or {}
        lang = lang or context.get('lang', False)
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
        warning = False
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        partner = partner_obj.browse(cr, uid, partner_id)
        lang = partner.lang
        context_partner = {'lang': lang, 'partner_id': partner_id}
        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
	
        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)
	
        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False

        fpos = False
        if not fiscal_position:
            fpos = partner.property_account_position or False
        else:
            fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
        if update_tax: #The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)
	
        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up
	
        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }

        return {'value': result, 'domain': domain, 'warning': warning}

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.product_uom_qty * line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
	    res[line.id]=price
            #res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res

    def _get_stock(self, cr, uid, ids, field, arg, context=None):
        result = {}
	obj_stock=self.pool.get('sap.integration.stock')
        for lines in self.browse(cr,uid,ids,context=context):
	    stock_ids=obj_stock.search(cr,uid,[('product_id','=',lines.codebar_id.item_id.id)],context=context)
	    result[lines.id]=obj_stock.browse(cr,uid,stock_ids,context=context)
        return result
    def _get_ds(self, cr, uid, ids, field, arg, context=None):
        result = {}
	obj_discount=self.pool.get('product.pricelist.discount')
	obj_version=self.pool.get('product.pricelist.version')
        for lines in self.browse(cr,uid,ids,context=context):
	    version_ids=obj_version.search(cr,uid,[('product_id','=',lines.codebar_id.item_id.id),('pricelist_id','=',lines.order_id.pricelist_id.id)],context=context)
	    result[lines.id]=obj_version.browse(cr,uid,version_ids,context=context).product_pricelist_discount_ids
        return result
    def _get_sequence(self, cr, uid, ids, field, arg, context=None):
        result = {}
	obj_discount=self.pool.get('product.pricelist.discount')
	obj_version=self.pool.get('product.pricelist.version')
        for lines in self.browse(cr,uid,ids,context=context):
	    stock_ids=obj_stock.search(cr,uid,[('product_id','=',lines.codebar_id.item_id.id)],context=context)
	    result[lines.id]=obj_stock.browse(cr,uid,stock_ids,context=context)
        return result
    def button_dummy(self, cr, uid, ids, context=None):
	return True
    def _get_price_unit(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=line.price_unit
	return result
    def _get_discount_unit(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=line.discount
	return result
    def _get_discount_amount(self, cr, uid, ids, field, arg, context=None):
        result = {}
	for line in self.browse(cr,uid,ids,context=context):
	    result[line.id]=(line.discount*line.product_uom_qty*line.price_unit)/100
	return result
    _columns = {
		'codebar_id': fields.many2one('product.codebars',string="Codebars",required=True),
		'price': fields.float(string="Precio Unitario",digits_compute=dp.get_precision('Product Price')),
		'price_show':fields.function(_get_priceU,type='float', string='Price',digits_compute=dp.get_precision('Product Price')),
		'price_unit_fun':fields.function(_get_price_unit,type='float', string='Price',digits_compute=dp.get_precision('Product Price')),
		'discount_fun':fields.function(_get_discount_unit,type='float', string='Discount'),
		'discount_amount':fields.function(_get_discount_amount,type='float', string='Discount',store=True),		
		'color': fields.boolean(string="color"),
		'tcolor': fields.boolean(string="tcolor"),
		'name':fields.function(_get_name,type='char', string='name',store=True),
		'ttcolor':fields.function(_get_ttcolor,type='boolean', string='ttcolor'),
		'discountmax':fields.function(_get_maxdiscount,type='float', string='Max Discount'),
		'pricegravad':fields.function(_get_pricegravad,type='float', string='Precio Gravado Neto'),
		'comment':fields.text(string="Comentario"),
		'max':fields.integer(string="discount MAX"),
		'item_code':fields.function(_get_itemcode,type='char', string='Code',store=True),
		'category_id':fields.function(_get_id,type='integer', string='category_id'),
		'nm':fields.function(_get_nm,type='integer', string='#',store=False),
		'cr':fields.integer(string="cr",type='integer'),
		'mtax':fields.function(_get_mtax,type='char', string='Impuestos',store=True),
		#'tprice_subtotal': fields.function(_amount_line, string='Subtotal', type='float'),
		'tprice_subtotal': fields.float( string='Subtotal',digits_compute=dp.get_precision('account')),
		'price_subtotal': fields.float( string='Subtotal'),
		'stock_ids':fields.related('codebar_id',type='one2many',relation='sap.integration.stock',string="campos adicionales",store=False),
		'inventory' : fields.function(_get_stock, type='one2many', obj = 'sap.integration.stock',  string='Stock'),
		'sequencediscount' : fields.function(_get_ds, type='one2many', obj = 'product.pricelist.discount',  string='Stock'),
		'tax_total':fields.float(string="Total Tax",digits_compute=dp.get_precision('Product Price')),
		'equivalent_qty':fields.float(string="qty equivalent",digits_compute=dp.get_precision('Product Price')),
		}


    def create(self, cr, uid, values, context=None):
        if values.get('order_id') and values.get('product_id') and  any(f not in values for f in ['name', 'price_unit', 'porcentaje_price','type', 'product_uom_qty', 'product_uom']):
            order = self.pool['sale.order'].read(cr, uid, values['order_id'], ['pricelist_id', 'partner_id', 'date_order', 'fiscal_position'], context=context)
            defaults = self.product_id_change(cr, uid, [], order['pricelist_id'][0], values['product_id'],
                qty=float(values.get('product_uom_qty', False)),
                uom=values.get('product_uom', False),
                qty_uos=float(values.get('product_uos_qty', False)),
                uos=values.get('product_uos', False),
                name=values.get('name', False),
                partner_id=order['partner_id'][0],
                date_order=order['date_order'],
                fiscal_position=order['fiscal_position'][0] if order['fiscal_position'] else False,
                flag=False,  # Force name update
                context=context
            )['value']
            if defaults.get('tax_id'):
                defaults['tax_id'] = [[6, 0, defaults['tax_id']]]
            values = dict(defaults, **values)
        return super(sap_order_line, self).create(cr, uid, values, context=context)

    _defaults = {
	'color' : False,
	'cr' : 0,
	
		}
class sap_password(osv.osv):
    _name="sap_integration.password"
    _order = "id desc"
    _columns = {
		'discount':fields.float("Discount",required=True),
		'user':fields.char("Usuario"),
		'passw':fields.char("password"),
		'order_id':fields.many2one("sale.order"),
		}
    def create(self, cr, uid, values, context=None):
	obj_sale=self.pool.get('sale.order').browse(cr,uid,context['active_id'],context=context)
	obj_partner=self.pool.get('res.partner').browse(cr,uid,obj_sale.partner_id.id,context=context)
	values['order_id']= context['active_id']
	b=0
	val2 = val =0.0
	
	if(values['user']):
	    cr.execute('SELECT password, password_crypt FROM res_users WHERE login=%s AND active AND discount_order', (values['user'],))
	    if cr.rowcount:
                stored, encrypted = cr.fetchone()
	        valid_pass, replacement = self._crypt_context(cr, uid, uid).verify_and_update(values['passw'], encrypted)
	        if valid_pass:
		    b =super(sap_password, self).create(cr, uid, values, context=context)
		    obj_line=self.pool.get('sale.order.line')
		    line_ids=obj_line.search(cr,uid,[('order_id','=',values['order_id'])],context=context)
		    for line in obj_line.browse(cr,uid,line_ids,context=context):
			val2 += line.tprice_subtotal*line.max/100
			for tax in line.tax_id:
			    val += (line.tprice_subtotal-line.tprice_subtotal*line.max/100)*tax.amount
		    self.pool.get('sale.order').write(cr,uid,context['active_id'],{'amount_tax':val},context=context)
		    #self.pool.get('sale.order').write(cr,uid,context['active_id'],{'disc':val},context=context)
		    self.pool.get('sale.order').write(cr,uid,context['active_id'],{'amount_discount':val2},context=context)
	 	    self.pool.get('sale.order').write(cr,uid,context['active_id'],{'disc':values['discount']},context=context)
		    self.pool.get('sale.order').write(cr,uid,context['active_id'],{'amount_total':val2},context=context)
		    return b	
	raise osv.except_osv(_('Password Incorret!'), _('Write the Correct Password'))
    def _crypt_context(self, cr, uid, id, context=None):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return default_crypt_context

    def action_vality(self, cr, uid, ids, context=None):
	id = ids[0]
	obj_pass=self.browse(cr,uid,id,context=context)
	values['user']=obj_pass.user
	values['passw']=obj_pass.passw
	values['discount']=obj_pass.discount
        return {'value': {'disc':1}}

class sap_password_line(osv.osv):
    _name="sap_integration.password_line"
    _order = "id desc"
    _columns = {
		'discount':fields.float("Discount",),
		'price':fields.float("Price"),
		'bdiscount':fields.boolean("Discount",),
		'bprice':fields.boolean("Price"),
		'user':fields.char("Usuario"),
		'passw':fields.char("password"),
		'order_id':fields.many2one("sale.order.line"),
		}
    def create(self, cr, uid, values, context=None):
	obj_sale=self.pool.get('sale.order.line').browse(cr,uid,context['active_id'],context=context)
	values['order_id']= context['active_id']
	b=0
	val2 = val =0.0
	discount = 0
	qty=0
	price_unit=0
	if(values['user']):
	    cr.execute('SELECT password, password_crypt,discount_order_line,discount_price FROM res_users WHERE login=%s AND active  ', (values['user'],))
	    if cr.rowcount:
                stored, encrypted,bdiscount,border = cr.fetchone()
	        valid_pass, replacement = self._crypt_context(cr, uid, uid).verify_and_update(values['passw'], encrypted)
	        if valid_pass:
		    b =super(sap_password_line, self).create(cr, uid, values, context=context)
		    discount= obj_sale.discount
		    qty= obj_sale.product_uom_qty
		    price_unit=obj_sale.price_unit
		    if bdiscount:
			if values['bdiscount'] and not values['bprice']:  
			    total=qty*price_unit-(qty*price_unit)*values['discount']/100
			    self.pool.get('sale.order.line').write(cr,uid,context['active_id'],{'discount':values['discount'],'price_subtotal':total, 'tprice_subtotal':total},context=context)
		    if border:
			if values['bprice'] and not values['bdiscount']:
			    total=qty*values['price']-(qty*values['price'])*discount/100
			    self.pool.get('sale.order.line').write(cr,uid,context['active_id'],{'price_unit':values['price'],'price_subtotal':total, 'tprice_subtotal':total},context=context)
		    if border and bdiscount:
			if values['bprice'] and values['bdiscount']:
			    total=qty*values['price']-(qty*values['price'])*values['discount']/100
			    self.pool.get('sale.order.line').write(cr,uid,context['active_id'],{'discount':values['discount'],'price_unit':values['price'],'price_subtotal':total,'tprice_subtotal':total},context=context)
		    return b	
	raise osv.except_osv(_('Password Incorret!'), _('Write the Correct Password'))
    def _crypt_context(self, cr, uid, id, context=None):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return default_crypt_context

    def action_vality(self, cr, uid, ids, context=None):
	id = ids[0]
	obj_pass=self.browse(cr,uid,id,context=context)
	values['user']=obj_pass.user
	values['passw']=obj_pass.passw
	values['discount']=obj_pass.discount
        return {'value': {'disc':1}}




class sap_stores(osv.osv):
    _name="sap_integration.stores"
    _columns = {
		'code':fields.char("Code"),
		'name':fields.char("name"),
		'warehouse_id':fields.many2one('stock.warehouse',string="Warehouse id"),
		'sequence_id' :fields.many2one('ir.sequence',strins="Sq"),
		'address':fields.char("Address"),
		'print_headr':fields.char("Print Header"),
		'phone1':fields.char("Phone 1"),
		'phone2':fields.char("Phone 2"),
		'fax':fields.char("Fax"),
		'email':fields.char("Email"),
		'users_ids' :fields.one2many('res.users','store_id',string="Users"),
		'partner_id':fields.many2one('res.partner',string="Cliente Contado",domain=[('customer','=',True)]),
		}
class sap_stock(osv.osv):
    _name="sap.integration.stock"
    _columns = {
		'product_id':fields.many2one('product.template',string="product ID"),
		'warehouse_id':fields.many2one('stock.warehouse',string="Warehouse id"),
		'on_hand':fields.float("On Hand"),
		'is_commited':fields.float("Is Commited"),
		'on_order':fields.float("On Order"),
		'sap_id':fields.char(string="sap_id"),
		}



class account_fiscal_position(osv.osv):
    _inherit = 'account.fiscal.position'
    _columns = {
		'leyenda':fields.char(string="Leyenda"),
		}
WARNING_TYPES = [('warning','Warning'),('info','Information'),('error','Error')]
class warning(osv.osv_memory):
    _name = 'warning'
    _description = 'warning'
    _columns = {
    'type': fields.selection(WARNING_TYPES, string='Type', readonly=True),
    'title': fields.char(string="Title", size=100, readonly=True),
    'message': fields.text(string="Message", readonly=True),
	}
    _req_name = 'title'

    def _get_view_id(self, cr, uid):
	res = self.pool.get('ir.model.data').get_object_reference(cr, uid, 
        'osc_integ', 'warning_form')
	return res and res[1] or False

    def message(self, cr, uid, id, context):
	message = self.browse(cr, uid, id)
	message_type = [t[1]for t in WARNING_TYPES if message.type == t[0]][0]
	res = {
        'name': '%s: %s' % (_(message_type), _(message.title)),
        'view_type': 'form',
        'view_mode': 'form',
        'view_id': self._get_view_id(cr, uid),
        'res_model': 'warning',
        'domain': [],
        'context': context,
        'type': 'ir.actions.act_window',
        'target': 'new',
        'res_id': message.id
	}
	return res

    def warning(self, cr, uid, title, message, context=None):
	id = self.create(cr, uid, {'title': title, 'message': message, 'type': 'warning'})
	res = self.message(cr, uid, id, context)
	return res

    def info(self, cr, uid, title, message, context=None):
	id = self.create(cr, uid, {'title': title, 'message': message, 'type': 'info'})
	res = self.message(cr, uid, id, context)
	return res

    def error(self, cr, uid, title, message, context=None):
	id = self.create(cr, uid, {'title': title, 'message': message, 'type': 'error'})
	res = self.message(cr, uid, id, context)
	return res

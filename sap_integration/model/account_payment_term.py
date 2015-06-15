# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class account_paymnet_term(osv.Model):
	_inherit = 'account.payment.term'

	_columns = {
		'sap_id':fields.integer("SAP ID",help="Id en SAP")
	}

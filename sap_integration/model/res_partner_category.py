# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class res_partner_category(osv.Model):
	_inherit = 'res.partner.category'

	_columns = {
		'sap_id': fields.integer('Sap Id'),
	}


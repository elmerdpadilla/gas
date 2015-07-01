from openerp.osv import fields, osv

class res_partner(osv.Model):
	_inherit = 'res.partner'
	_columns = {
       'rtn' : fields.char('RTN',translate=True),
	}
	_default = {
        'lang': 'es_HN',
    }

	_sql_constraints = [('rtn_uniq','unique(rtn)', 'rtn1 must be unique!')]




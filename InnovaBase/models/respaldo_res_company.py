from openerp.osv import fields, osv

class res_company(osv.Model):
	_inherit = 'res.company'
	_columns = {
       'cai' : fields.char('CAI',translate=True),
	}




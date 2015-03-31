from openerp.osv import osv
class reporte(osv.AbstractModel):
	_name = 'report.gasoline.report_closing'
	def render_html(self, cr, uid, ids, data=None, context=None):
		report_obj = self.pool['report']
		report = report_obj._get_report_from_name(cr, uid, 'gasoline.report_closing')
		docargs = {
			'doc_ids': ids,
			'doc_model': report.model,
			'docs': self.pool[report.model].browse(cr, uid, ids, context=context),
			}
		return report_obj.render(cr, uid, ids, 'gasoline.report_closing',docargs, context=context)

class reporte2(osv.AbstractModel):
	_name = 'report.gasoline.report_invoice'
	def render_html(self, cr, uid, ids, data=None, context=None):
		report_obj = self.pool['report']
		report = report_obj._get_report_from_name(cr, uid, 'gasoline.report_invoice')
		docargs = {
			'doc_ids': ids,
			'doc_model': report.model,
			'docs': self.pool[report.model].browse(cr, uid, ids, context=context),
			}
		return report_obj.render(cr, uid, ids, 'gasoline.report_invoice',docargs, context=context)


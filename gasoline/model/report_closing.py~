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
class reporte3(osv.AbstractModel):
	_name = 'report.gasoline.report_closing_total'
	def render_html(self, cr, uid, ids, data=None, context=None):
		report_obj = self.pool['report']
		report = report_obj._get_report_from_name(cr, uid, 'gasoline.report_closing_total')
		printer=self.pool[report.model].browse(cr, uid, ids, context=context)
		a=[]
		print "#"*50
		if len(printer)==1:
			a=printer
		if len(printer)>1:
			a=printer[0]
		if len(printer)<1:
			a=printer
		docargs = {
			'doc_ids': ids,
			'doc_model': report.model,
			'docs': self.pool[report.model].browse(cr, uid, ids, context=context),
			'o':a,
			'p':self._get_payment(a),
			'q':self._get_reading(a),
			}
		return report_obj.render(cr, uid, ids, 'gasoline.report_closing_total',docargs, context=context)
	def _get_payment(self,printer=None):
		res=[]
		ides=[]
		for journal in printer.journal_ids_total:
			if journal.journal_id.id not in ides:
				ides.append(journal.journal_id.id)
				res.append({'money':journal.money,'id':journal.journal_id.id,'name':journal.journal_id.name})
			else:
				a=ides.index(journal.journal_id.id)
				res[a]['money']+=journal.money
		return res
	def _get_reading(self,printer=None):
		res=[]
		ides=[]
		for reading in printer.reading_total2:
			comp=reading.description+"-"+reading.name
			if comp not in ides:
				ides.append(comp)
				res.append({'price_list':reading.price_list,'id':reading.id,'name':reading.name,'levelt':reading.levelt,'levelf':reading.levelf,'description':reading.description})
			else:
				a=ides.index(comp)
				res[a]['price_list']+=reading.price_list
				res[a]['levelf']+=reading.levelf
				if res[a]['levelt']<reading.levelt:
					res[a]['levelt']=reading.levelt
		return res







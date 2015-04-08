from openerp.osv import osv,fields
from openerp.tools.translate import _
class PrintReportWizard(osv.TransientModel):
	_name = 'gasoline.print.report.order'
	_columns = {
		'date1': fields.date('Date Start',required=True),
		'date2': fields.date('Date End'),
				}
	def action_print_report(self, cr, uid, ids, context=None):
		obj_turn= self.pool.get('gasoline.turn')
		turn_ids=[]
		if context['date1'] and not context['date2']:
			turn_ids=obj_turn.search(cr,uid,[('date','=',context['date1'])],context=context)
		if context['date1'] and context['date2']:
			turn_ids=obj_turn.search(cr,uid,[('date','>=',context['date1']),('date','<=',context['date2'])],context=context)
		if len( turn_ids)>0:
			return self.pool['report'].get_action(cr, uid, turn_ids, 'gasoline.report_closing_total', context=context)
		else:
			raise osv.except_osv(_('Error!'), _('dont exist turn in the date'))

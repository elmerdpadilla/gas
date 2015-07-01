# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################



from openerp.osv import fields, osv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import datetime,timedelta
import time
import base64
import xlsxwriter
import StringIO
class accounting_report(osv.osv_memory):
    _name = "accounting.report"
    _inherit = "account.common.report"
    _description = "Accounting Report"

    _columns = {
        'pr_lo':fields.boolean('Perdida y Ganacia'),
        'enable_filter': fields.boolean('Enable Comparison'),
        'account_report_id': fields.many2one('account.financial.report', 'Account Reports', required=True),
        'label_filter': fields.char('Column Label', help="This label will be displayed on report to show the balance computed for the given comparison filter."),
        'fiscalyear_id_cmp': fields.many2one('account.fiscalyear', 'Fiscal Year', help='Keep empty for all open fiscal year'),
        'filter_cmp': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by", required=True),
        'period_from_cmp': fields.many2one('account.period', 'Start Period'),
        'period_to_cmp': fields.many2one('account.period', 'End Period'),
        'date_from_cmp': fields.date("Start Date"),
        'date_to_cmp': fields.date("End Date"),
        'debit_credit': fields.boolean('Display Debit/Credit Columns', help="This option allows you to get more details about the way your balances are computed. Because it is space consuming, we do not allow to use it while doing a comparison."),
    }

    def _get_account_report(self, cr, uid, context=None):
        # TODO deprecate this it doesnt work in web
        menu_obj = self.pool.get('ir.ui.menu')
        report_obj = self.pool.get('account.financial.report')
        report_ids = []
        if context.get('active_id'):
            menu = menu_obj.browse(cr, uid, context.get('active_id')).name
            report_ids = report_obj.search(cr, uid, [('name','ilike',menu)])
        return report_ids and report_ids[0] or False

    _defaults = {
            'filter_cmp': 'filter_no',
            'target_move': 'posted',
            'account_report_id': _get_account_report,
    }

    def excel(self, cr, uid,ids, fields,done=None, context=None):
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context)
        res = super(accounting_report, self).check_report(cr, uid, ids, context=context)
        data = {}
        data['form'] = self.read(cr, uid, ids, ['account_report_id', 'date_from_cmp','pr_lo','date_to_cmp',  'fiscalyear_id_cmp', 'journal_ids', 'period_from_cmp', 'period_to_cmp',  'filter_cmp',  'chart_account_id', 'target_move'], context=context)[0]
        for field in ['fiscalyear_id_cmp', 'chart_account_id', 'period_from_cmp', 'period_to_cmp', 'account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(cr, uid, ids, data, context=context)
        res['data']['form']['comparison_context'] = comparison_context

        #data['form'].update(self.read(cr, uid, ids, ['date_from_cmp',  'debit_credit', 'date_to_cmp','pr_lo', 'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',  'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter','target_move'], context=context)[0])
        contexto={}
        contexto['journal_ids']=data['form']['journal_ids']
        contexto['fiscalyear']=wizard.fiscalyear_id.id
        contexto['chart_account_id']=data['form']['chart_account_id']
        contexto['lang']=context.get('lang', 'es_HN')
        contexto['state']=data['form']['target_move']
        if wizard.filter=='filter_date':
            contexto['date_from']=wizard.date_from
            contexto['date_to']=wizard.date_to
        elif wizard.filter=='filter_period':
            contexto['period_from']=wizard.period_from
            contexto['period_to']=wizard.period_to
        data['form']['used_context'] = contexto
        self.usuario=self.pool.get('res.users').browse(cr,uid,uid,context=context).name
        self.fecha=(datetime.today()-relativedelta(hours=6)).strftime("%Y-%m-%d %H:%M")
        




        lines = []
        account_obj = self.pool.get('account.account')
        currency_obj = self.pool.get('res.currency')
        ids2 = self.pool.get('account.financial.report')._get_children_by_order(cr,uid, [data['form']['account_report_id']], context=context)
      

        for report in self.pool.get('account.financial.report').browse(cr,uid, ids2, context=data['form']['used_context']):
         
            vals = {
                'name': report.name,
                'balance': report.balance * report.sign or 0.0,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'format':bool(report.style_overwrite) and report.style_overwrite or 0,
                'account_type': report.type =='sum' and 'view' or False, #used to underline the financial report balances,
                'mostrar':False,
                'underline':False,
            }
            if report.underline:
                vals['underline']=True
            if report.mostrar_saldo:
                vals['mostrar']=True

            if wizard.debit_credit:
                vals['debit'] = report.debit
                vals['credit'] = report.credit
            if wizard.enable_filter:
                vals['balance_cmp'] = self.pool.get('account.financial.report').browse(cr,uid, report.id, context=data['form']['comparison_context']).balance * report.sign or 0.0
            lines.append(vals)
            account_ids = []
            if report.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if report.type == 'accounts' and report.account_ids:
                account_ids = account_obj._get_children_and_consol(cr,uid, [x.id for x in report.account_ids])
            elif report.type == 'account_type' and report.account_type_ids:
                account_ids = account_obj.search(cr,uid, [('user_type','in', [x.id for x in report.account_type_ids])])
            if account_ids:
                for account in account_obj.browse(cr,uid, account_ids, context=data['form']['used_context']):
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    if report.display_detail == 'detail_flat' and account.type == 'view':
                        continue
                    flag = False
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance':  account.balance != 0 and account.balance * report.sign or account.balance,
                        'type': 'account',
                        'format':bool(report.style_overwrite) and report.style_overwrite or 0,
                        'level': report.display_detail == 'detail_with_hierarchy' and min(account.level + 1,6) or 6, #account.level + 1
                        'account_type': account.type,
                        'mostrar':True,
                    }
                   
                       
                    if wizard.debit_credit:
                        vals['debit'] = account.debit
                        vals['credit'] = account.credit
                    if not currency_obj.is_zero(cr,uid, account.company_id.currency_id, vals['balance']):
                        flag = True
                    if wizard.enable_filter:
                        vals['balance_cmp'] = account_obj.browse(cr, uid, account.id, context=data['form']['comparison_context']).balance * report.sign or 0.0
                        if not currency_obj.is_zero(cr,uid, account.company_id.currency_id, vals['balance_cmp']):
                            flag = True
                    if flag:
                        lines.append(vals)

        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        bold = workbook.add_format({'bold': True})
        bold2= workbook.add_format({'bold': True,'num_format': 'L#,##0.00'})
        money = workbook.add_format({'num_format': 'L#,##0.00'})
        format = workbook.add_format({'bold': True, 'font_color': 'red'})
        format = workbook.add_format()
        format.set_center_across()
        usuario=self.pool.get('res.users').browse(cr,uid,uid,context=context)
        company=usuario.company_id.name
        worksheet.write('A1',company,format)
        worksheet.write('A2','Balance General',bold)
        worksheet.write('A3',self.fecha,bold)
        worksheet.write('A4',self.usuario,bold)
        row = 10
        col = 0
        if wizard.filter == 'filter_date':
            worksheet.write('A5','Flitrado Por Fechas',bold)
            worksheet.write('A6','Fecha desde :',bold)
            worksheet.write('B6',wizard.date_from)
            worksheet.write('A7','Fecha hasta :',bold)
            worksheet.write('B7',wizard.date_to)
        if wizard.fiscalyear_id and wizard.filter=='filter_no':
            worksheet.write('A5','Ejercicio Fiscal',bold)
            worksheet.write('B5',str(wizard.fiscalyear_id.name))
        for cuenta in lines:
                if cuenta['format']:
                    if cuenta['format']==1:
                        style= workbook.add_format({'bold': True,'font_size':14,'underline':1})
                        style2= workbook.add_format({'bold': True,'font_size':14,'underline':1,'num_format': 'L#,##0.00'})
                    if cuenta['format']==2:                        
                        style= workbook.add_format({'bold': True,'font_size':14})
                        style2= workbook.add_format({'bold': True,'font_size':14,'num_format': 'L#,##0.00'})
                    if cuenta['format']==3:                        
                        style= workbook.add_format({'bold': True,'font_size':12})
                        style2= workbook.add_format({'bold': True,'font_size':12,'num_format': 'L#,##0.00'})
                    if cuenta['format']==4:                        
                        style= workbook.add_format({'font_size':12})
                        style2= workbook.add_format({'font_size':12,'num_format': 'L#,##0.00'})
                    if cuenta['format']==5:                        
                        style= workbook.add_format({'font_size':11,'italic':1})
                        style2= workbook.add_format({'font_size':11,'italic':1,'num_format': 'L#,##0.00'})
                    if cuenta['format']==6:                        
                        style= workbook.add_format({'font_size':11})
                        style2= workbook.add_format({'font_size':11,'num_format': 'L#,##0.00'})
                else:
                        style = workbook.add_format({'bold': True,'font_size':12})
                        style2 = workbook.add_format({'bold': True,'font_size':12,'num_format': 'L#,##0.00'})
                
                worksheet.write(row,col,cuenta['name'],style)
                if cuenta['mostrar']:
                    worksheet.write(row,col+1,cuenta['balance'],style2)
                row+=1
        workbook.close()

        output.seek(0)
        vals = {
                    'name': 'reporte de balance general',
                    'datas_fname': 'balance_general.xlsx',
                    'description': 'Balance General en Excel',
                    'type': 'binary',
                    'db_datas': base64.encodestring(output.read()),
        }
           
        file_id = self.pool.get('ir.attachment').create(cr,uid,vals,context)
        return {
        'domain': "[('id','=', " + str(file_id) + ")]",
        'type': 'ir.actions.act_window',
        'name': 'Guardar Excel',
         'view_type': 'form',
         'view_mode': 'tree,form',
        'res_model': 'ir.attachment',
        'target': 'new',
        }
       
    
    def _build_comparison_context(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        result = {}
        result['fiscalyear'] = 'fiscalyear_id_cmp' in data['form'] and data['form']['fiscalyear_id_cmp'] or False
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        if data['form']['filter_cmp'] == 'filter_date':
            result['date_from'] = data['form']['date_from_cmp']
            result['date_to'] = data['form']['date_to_cmp']
        elif data['form']['filter_cmp'] == 'filter_period':
            if not data['form']['period_from_cmp'] or not data['form']['period_to_cmp']:
                raise osv.except_osv(_('Error!'),_('Select a starting and an ending period'))
            result['period_from'] = data['form']['period_from_cmp']
            result['period_to'] = data['form']['period_to_cmp']
        return result

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = super(accounting_report, self).check_report(cr, uid, ids, context=context)
        data = {}
        data['form'] = self.read(cr, uid, ids, ['account_report_id', 'date_from_cmp',  'date_to_cmp',  'fiscalyear_id_cmp', 'journal_ids', 'period_from_cmp', 'period_to_cmp',  'filter_cmp',  'chart_account_id', 'target_move'], context=context)[0]
        for field in ['fiscalyear_id_cmp', 'chart_account_id', 'period_from_cmp', 'period_to_cmp', 'account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(cr, uid, ids, data, context=context)
        res['data']['form']['comparison_context'] = comparison_context
        return res

    def _print_report(self, cr, uid, ids, data, context=None):
        data['form'].update(self.read(cr, uid, ids, ['date_from_cmp',  'debit_credit', 'date_to_cmp','pr_lo', 'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',  'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter','target_move'], context=context)[0])
        return self.pool['report'].get_action(cr, uid, [], 'account.report_financial', data=data, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
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
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import xlsxwriter
import StringIO
import base64

class account_balance_report(osv.osv_memory):
    _inherit = "account.common.account.report"
    _name = 'account.balance.report'
    _description = 'Trial Balance Report'

    _columns = {
        'filtrar_cuenta':fields.boolean('Filtrar Por Cuenta'),
        'cuenta_inicial':fields.char('Cuenta Inicial'),
        'cuenta_final':fields.char('Cuenta Final'),
        'journal_ids': fields.many2many('account.journal', 'account_balance_report_journal_rel', 'account_id', 'journal_id', 'Journals', required=True),
    }

    _defaults = {
        'journal_ids': [],
    }

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id','filtrar_cuenta','cuenta_inicial','cuenta_final', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move'], context=context)[0]
        for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        used_context = self._build_contexts(cr, uid, ids, data, context=context)
        data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
        return self._print_report(cr, uid, ids, data, context=context)
    
    def _print_report(self, cr, uid, ids, data, context=None):
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        return self.pool['report'].get_action(cr, uid, [], 'account.report_trialbalance', data=data, context=context)


    def excel(self, cr, uid,ids, fields,done=None, context=None):
        if context is None:
            context = {}
        data = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id','filtrar_cuenta','cuenta_inicial','cuenta_final', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move'], context=context)[0]
        for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        used_context = self._build_contexts(cr, uid, ids, data, context=context)
        data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
        

        self.sum_debit = 0.00
        self.sum_credit = 0.00
        self.date_lst = []
        self.date_lst_string = ''
        self.result_acc = []
        self.result_acc2=[]
        self.usuario=self.pool.get('res.users').browse(cr,uid,uid,context=context).name
        self.fechar=(datetime.today()-relativedelta(hours=6)).strftime("%Y-%m-%d %H:%M")
        
        def _process_child(accounts, disp_acc, parent,result_acc2,flag2):
                account_rec = [acct for acct in accounts if acct['id']==parent][0]
                currency_obj = self.pool.get('res.currency')
                acc_id = self.pool.get('account.account').browse(cr,uid, account_rec['id'])
                currency = acc_id.currency_id and acc_id.currency_id or acc_id.company_id.currency_id
                res = {
                    'id': account_rec['id'],
                    'type': account_rec['type'],
                    'code': account_rec['code'],
                    'name': account_rec['name'],
                    'level': account_rec['level'],
                    'debit': account_rec['debit'],
                    'credit': account_rec['credit'],
                    'balance': account_rec['balance'],
                    'parent_id': account_rec['parent_id'],
                    'bal_type': '',
                    'saldo_ini':0.00,
                }
                self.sum_debit += account_rec['debit']
                self.sum_credit += account_rec['credit']
                flag=False
                if disp_acc == 'movement':
                    for dic in result_acc2:
                        if res['code']==dic['code']:
                            if not currency_obj.is_zero(cr,uid, currency, dic['balance']):
                                flag=True
                                break
                    if wizard.filtrar_cuenta:
                        if res['code']==wizard.cuenta_inicial:
                            flag2=True
                        if flag2 or res['code']==wizard.cuenta_final:
                            if not currency_obj.is_zero(cr,uid, currency, res['credit']) or not currency_obj.is_zero(cr,uid, currency, res['debit']) or not currency_obj.is_zero(cr,uid, currency, res['balance']) or flag:
                                self.result_acc.append(res)
                        if res['code']==wizard.cuenta_final:                      
                            flag2=False
                    else:
                        if not currency_obj.is_zero(cr,uid, currency, res['credit']) or not currency_obj.is_zero(cr,uid, currency, res['debit']) or not currency_obj.is_zero(cr,uid, currency, res['balance']) or flag:
                                self.result_acc.append(res)

                elif disp_acc == 'not_zero':
                    if not currency_obj.is_zero(cr,uid, currency, res['balance']):
                        self.result_acc.append(res)
                else:
                    self.result_acc.append(res)

                if res['code']==wizard.cuenta_final:
                    flag2=False
                if account_rec['child_id']:
                    for child in account_rec['child_id']:
                        _process_child(accounts,disp_acc,child,result_acc2,flag2)
        def _process_child2(accounts, disp_acc, parent):
                account_rec = [acct for acct in accounts if acct['id']==parent][0]
                currency_obj = self.pool.get('res.currency')
                acc_id = self.pool.get('account.account').browse(cr,uid, account_rec['id'])
                currency = acc_id.currency_id and acc_id.currency_id or acc_id.company_id.currency_id
                res = {
                    'id': account_rec['id'],
                    'type': account_rec['type'],
                    'code': account_rec['code'],
                    'name': account_rec['name'],
                    'level': account_rec['level'],
                    'debit': account_rec['debit'],
                    'credit': account_rec['credit'],
                    'balance': account_rec['balance'],
                    'parent_id': account_rec['parent_id'],
                    'bal_type': '',
                }
                self.sum_debit += account_rec['debit']
                self.sum_credit += account_rec['credit']
                self.result_acc2.append(res)
                if account_rec['child_id']:
                    for child in account_rec['child_id']:
                        _process_child2(accounts,disp_acc,child)

        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context)
        obj_account = self.pool.get('account.account')
        if not ids:
            ids = ids
        if not ids:
            return []
        if not done:
            done={}
        ctx = context.copy()
        ctx2=context.copy()
        fiscal_ids=self.pool.get('account.fiscalyear').search(cr,uid,[])
        obj_fiscal=self.pool.get('account.fiscalyear').browse(cr,uid,fiscal_ids,ctx)
        obj_periodo_fiscal=self.pool.get('account.period').search(cr,uid,[('fiscalyear_id','=',wizard.fiscalyear_id.id),('special','=',True)])

        if len(obj_periodo_fiscal)>1:
            raise osv.except_osv(_('Data Incorrecta'),
                    _('Existe mas de un periodo fiscal como periodo de apertura'))
        date_start=''
        for mfecha in obj_fiscal:
            date_start=mfecha.date_start
            for mfecha2 in obj_fiscal:
                if mfecha.date_start>mfecha2.date_start:
                    date_start=mfecha2.date_start
            break
        if wizard.filter == 'filter_date':
            fecha=datetime.strptime(wizard.date_from, "%Y-%m-%d")
            fecha= fecha+timedelta(days=-1)
            fecha=datetime.strftime(fecha,"%Y-%m-%d")
        #ctx['fiscalyear'] = form['fiscalyear_id']
        if wizard.filter == 'filter_period':
            ctx['period_from'] = wizard.period_from.id
            ctx['period_to'] = wizard.period_to.id
        
        elif wizard.filter == 'filter_date':
            ctx['date_from'] = wizard.date_from
            ctx['date_to'] =  wizard.date_to
        ctx['state'] = wizard.target_move
#-----------------------------------------------------------------------------------------------------------------
 
        if wizard.filter=='filter_no':
             ctx2['fiscalyear'] = wizard.fiscalyear_id.id
             ctx2['period_from'] = obj_periodo_fiscal[0]
             ctx2['period_to'] = obj_periodo_fiscal[0]
             ctx2['state'] = wizard.target_move
        else:
            ctx2['fiscalyear'] = wizard.fiscalyear_id.id
            
            if wizard.filter == 'filter_period':
                array=[]
                obj_fiscal=self.pool.get('account.fiscalyear').browse(cr,uid,wizard.fiscalyear_id.id,ctx)
                for fiscal in obj_fiscal:
                    for periodos in fiscal.period_ids:
                        array.append(periodos.date_start)
                for periodo in self.pool.get('account.period').browse(cr,uid,wizard.period_from.id,ctx):
                    periodo_final_fecha=periodo.date_start                

                date_p=datetime.strptime(periodo_final_fecha, "%Y-%m-%d") - timedelta(days=1)
                ctx2['date_from'] = array[0]
                ctx2['date_to'] = datetime.strftime(date_p,"%Y-%m-%d")
            
            elif wizard.filter == 'filter_date':
                obj_fiscal=self.pool.get('account.fiscalyear').browse(cr,uid,wizard.fiscalyear_id.id,ctx)
            
                ctx2['date_from'] = obj_fiscal.date_start
                date_a=datetime.strptime(wizard.date_from, "%Y-%m-%d") - timedelta(days=1)
                ctx2['date_to'] =  datetime.strftime(date_a,"%Y-%m-%d")
            ctx2['state'] = wizard.target_move

        parents = [data['form']['chart_account_id']]
        child_ids = obj_account._get_children_and_consol(cr,uid, [data['form']['chart_account_id']], ctx)
        
        if child_ids:
            ids = child_ids
        
        accounts = obj_account.read(cr,uid, ids, ['type','code','name','debit','credit','balance','parent_id','level','child_id'], ctx)
        accounts2 = obj_account.read(cr,uid, ids, ['type','code','name','debit','credit','balance','parent_id','level','child_id'], ctx2)
        for parent in parents:
                if parent in done:
                    continue
                done[parent] = 1
#------------------------------------------------------------------------------------------------------------------
                _process_child2(accounts2,wizard.display_account,parent)
#-------------------------------------------------------------------------------------------------------------------
                _process_child(accounts,wizard.display_account,parent,self.result_acc2,flag2=False)

        for x in self.result_acc:
            for y in self.result_acc2:

                if x['code']==y['code']:
                    x['saldo_ini']=y['balance']
                    if y['balance']:
                        x['balance']=y['balance']+x['debit']-x['credit']
                    else:
                        x['balance']=x['debit']-x['credit']
                    break
                else:
                    x['saldo_ini']=0.00
        
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
        worksheet.write('A2','Balance de Comprobacion',bold)
        worksheet.write('A3',self.fechar,bold)
        worksheet.write('A4',self.usuario,bold)
        if wizard.filtrar_cuenta:
            worksheet.write('A5','Flitrado Por Cuenta',bold)
            worksheet.write('A6','Cuenta desde :',bold)
            worksheet.write('B6',wizard.cuenta_inicial)
            worksheet.write('A7','Cuenta hasta :')
            worksheet.write('B7',wizard.cuenta_final)
        if wizard.filter == 'filter_date':
            worksheet.write('A5','Flitrado Por Fechas',bold)
            worksheet.write('A6','Fecha desde :',bold)
            worksheet.write('B6',wizard.date_from)
            worksheet.write('A7','Fecha hasta :',bold)
            worksheet.write('B7',wizard.date_to)
        row = 10
        col = 0            
        
        worksheet.write('A9','Codigo',bold)
        worksheet.write('B9','Cuenta',bold)
        worksheet.write('C9','Saldo Inicial',bold)
        worksheet.write('D9','Debe',bold)
        worksheet.write('E9','Haber',bold)
        worksheet.write('F9','Saldo',bold)
        
        for cuenta in self.result_acc:
            if cuenta['type']!='view':
                worksheet.write(row,col,cuenta['code'],money)
                worksheet.write(row,col+1,cuenta['name'],money)
                worksheet.write(row,col+2,cuenta['saldo_ini'],money)
                worksheet.write(row,col+3,cuenta['debit'],money)
                worksheet.write(row,col+4,cuenta['credit'],money)
                worksheet.write(row,col+5,cuenta['balance'],money)
            else:
                worksheet.write(row,col,cuenta['code'],bold2)
                worksheet.write(row,col+1,cuenta['name'],bold2)
                worksheet.write(row,col+2,cuenta['saldo_ini'],bold2)
                worksheet.write(row,col+3,cuenta['debit'],bold2)
                worksheet.write(row,col+4,cuenta['credit'],bold2)
                worksheet.write(row,col+5,cuenta['balance'],bold2)
    
            row+=1	
            
        workbook.close()

        output.seek(0)
        vals = {
                    'name': 'reporte de balance de comprobacion',
                    'datas_fname': 'balance_comprobacion.xlsx',
                    'description': 'Balance de Comprobacion en Excel',
                    'type': 'binary',
                    'db_datas': base64.encodestring(output.read()),
        }
           
        file_id = self.pool.get('ir.attachment').create(cr,uid,vals,ctx)
        return {
        'domain': "[('id','=', " + str(file_id) + ")]",
        'type': 'ir.actions.act_window',
        'name': 'Guardar Excel',
         'view_type': 'form',
         'view_mode': 'tree,form',
        'res_model': 'ir.attachment',
        'target': 'new',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

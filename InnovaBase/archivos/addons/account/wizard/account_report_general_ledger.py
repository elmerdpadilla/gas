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
import time
from lxml import etree

from openerp.osv import fields, osv
from openerp.osv.orm import setup_modifiers
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import datetime,timedelta
import StringIO
import base64
import xlsxwriter
class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.common.account.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    _columns = {
        'landscape': fields.boolean("Landscape Mode"),
        'initial_balance': fields.boolean('Include Initial Balances',
                                    help='If you selected to filter by date or period, this field allow you to add a row to display the amount of debit/credit/balance that precedes the filter you\'ve set.'),
        'amount_currency': fields.boolean("With Currency", help="It adds the currency column on report if the currency differs from the company currency."),
        'sortby': fields.selection([('sort_date', 'Date'),('sort_number', 'Number'), ('sort_journal_partner', 'Journal & Partner')], 'Sort by', required=True),
        'journal_ids': fields.many2many('account.journal', 'account_report_general_ledger_journal_rel', 'account_id', 'journal_id', 'Journals', required=True),
        'exist':fields.boolean(string="exist"),
    }

    def _get_exist(self,cr,uid,context=None):
        data= context.get('active_ids',[])
        if len(data)>0 :
            for id in data:
                if not self.pool.get('account.account').browse(cr,uid,id,context=context).currency_id:
                    return False
            return True
        else:
            return False

    _defaults = {
        'landscape': True,
        'amount_currency': False,
        'sortby': 'sort_date',
        'initial_balance': False,
        'exist':_get_exist,
    }

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear=False, context=None):
        res = {}
        if not fiscalyear:
            res['value'] = {'initial_balance': False}
        return res
    def check_report3(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}

        self.sortby2=""
        self.target_move2=""
        data['ids'] = context.get('active_ids', [])

            
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id','filtrar_cuenta','cuenta_inicial','cuenta_final', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move'], context=context)[0]
        for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        used_context = self._build_contexts(cr, uid, ids, data, context=context)
        if len(data['ids'])<1:
            data['ids']=[data['form'].get('chart_account_id')]
        data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
        data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby','display_account'])[0])
        if context is None:
            context = {}
        self.query = ""
        self.target_move2 = data['form'].get('target_move')
        fiscal_year=data['form'].get('fiscalyear_id')
        if fiscal_year:
            fiscal_year=self.pool.get('account.fiscalyear').browse(cr,uid,fiscal_year,context=context).name
        filter_type=data['form'].get('filter')
        filter_label=''
        if filter_type:
            if filter_type == 'filter_no':
                filter_label='Not filtered'
            elif filter_type == 'filter_period':
                filter_label='Filtered by period'   
            elif filter_type == 'filter_date':
                filter_label='Filtered by date' 
                
        self.amount_currency2=data['form'].get('amount_currency')
        self.tot_currency = 0.0
        self.period_sql = ""
        self.sold_accounts = {}
        ctx2 = data['form'].get('used_context',{}).copy()
        self.init_balance2 = data['form'].get('initial_balance', True)
        if self.init_balance2:
            ctx2.update({'initial_bal': True})
        self.display_account2 = data['form']['display_account']
        obj_move = self.pool.get('account.move.line')
        self.query2 = obj_move._query_get(cr, uid, obj='l', context=data['form'].get('used_context',{}))
        self.init_query2 = obj_move._query_get(cr, uid, obj='l', context=ctx2)
        self.sortby2 = data['form'].get('sortby', 'sort_date')
        array=[]
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        bold = workbook.add_format({'bold': True})
        normal = workbook.add_format({'bold': False})
        bold2= workbook.add_format({'bold': True,'num_format': 'L#,##0.00'})
        bold3= workbook.add_format({'bold': True,'num_format': '$#,##0.00'})
        money = workbook.add_format({'num_format': 'L#,##0.00'})
        format = workbook.add_format({'bold': True, 'font_color': 'red'})
        format = workbook.add_format()
        format.set_center_across()
        res_company=''
        row = 10
        col = 0
        debit_total=0
        credit_total=0
        progres_total=0
        if len(data['ids'])>1:
            row = 12
        for a in data['ids']:
            worksheet.write(9,0,_('date'),bold)
            worksheet.write(9,1,_('move'),bold)
            worksheet.write(9,2,_('partner name'),bold)
            worksheet.write(9,3,_('ref'),bold)
            worksheet.write(9,4,_('name'),bold)
            worksheet.write(9,5,_('debit'),bold)
            worksheet.write(9,6,_('credit'),bold)
            worksheet.write(9,7,_('progress'),bold)
            account=self.pool.get('account.account').browse(cr,uid,a,context=context)
            if len(self.get_children_accounts(cr, uid, ids,account,context))>1:
                row += 2
            res_company=account.company_id.name
            if not self.amount_currency2:
                for account2 in self.get_children_accounts(cr, uid, ids,account,context):
                    scredit=self._sum_credit_account(cr, uid, ids,account2,context)
                    sdebit=self._sum_debit_account(cr, uid, ids,account2,context)
                    sprogres=self._sum_balance_account(cr, uid, ids,account2,context)
                    debit_total+=sdebit
                    credit_total+=scredit
                    progres_total+=sprogres
                    res = {
                            'ldate': '',
                            'partner_name': '',
                            'lref': '',
                            'lname': '',
                            'move': str(account2.code)+"-"+account2.name,
                            'debit': sdebit,
                            'credit': scredit,
                            'progress': sprogres,
                        }
                    row+=1
                    worksheet.write(row,col,res['ldate'],bold)
                    worksheet.write(row,col+1,res['move'],bold)
                    worksheet.write(row,col+2,res['partner_name'],bold)
                    worksheet.write(row,col+3,res['lref'],bold)
                    worksheet.write(row,col+4,res['lname'],bold)
                    worksheet.write(row,col+5,res['debit'],bold2)
                    worksheet.write(row,col+6,res['credit'],bold2)
                    worksheet.write(row,col+7,res['progress'],bold2)
                    row+=1
                    array.append(res)
                    for line in  self.lines(cr, uid, ids,account2,context):
                        res = {
                            'ldate': line['ldate'],
                            'move': line['move'],
                            'partner_name': line['partner_name'],
                            'lref': line['lref'],
                            'lname': line['lname'],
                            'debit': line['debit'],
                            'credit': line['credit'],
                            'progress': line['progress'],
                        }
                        worksheet.write(row,col,res['ldate'],money)
                        worksheet.write(row,col+1,res['move'],money)
                        worksheet.write(row,col+2,res['partner_name'],money)
                        worksheet.write(row,col+3,res['lref'],money)
                        worksheet.write(row,col+4,res['lname'],money)
                        worksheet.write(row,col+5,res['debit'],money)
                        worksheet.write(row,col+6,res['credit'],money)
                        worksheet.write(row,col+7,res['progress'],money)
                        row+=1
                        array.append(res)
            else:
                money = workbook.add_format({'num_format': '$#,##0.00'})
                bold2= workbook.add_format({'bold': True,'num_format': '$#,##0.00'})
                for account2 in self.get_children_accounts(cr, uid, ids,account,context):
                    scredit=self._sum_credit_account_currency(cr, uid, ids,account2,context)
                    sdebit=self._sum_debit_account_currency(cr, uid, ids,account2,context)
                    sprogres=self._sum_balance_account_currency(cr, uid, ids,account2,context)
                    debit_total+=sdebit
                    credit_total+=scredit
                    progres_total+=sprogres
                    res = {
                            'ldate': '',
                            'partner_name': '',
                            'lref': '',
                            'lname': '',
                            'move': str(account2.code)+"-"+account2.name,
                            'debit': sdebit,
                            'credit': scredit,
                            'progress': sprogres,
                        }
                    row+=1
                    worksheet.write(row,col,res['ldate'],bold)
                    worksheet.write(row,col+1,res['move'],bold)
                    worksheet.write(row,col+2,res['partner_name'],bold)
                    worksheet.write(row,col+3,res['lref'],bold)
                    worksheet.write(row,col+4,res['lname'],bold)
                    worksheet.write(row,col+5,res['debit'],bold3)
                    worksheet.write(row,col+6,res['credit'],bold3)
                    worksheet.write(row,col+7,res['progress'],bold3)
                    row+=1
                    array.append(res)
                    for line in  self.lines2(cr, uid, ids,account2,context):
                        res = {
                            'ldate': line['ldate'],
                            'move': line['move'],
                            'partner_name': line['partner_name'],
                            'lref': line['lref'],
                            'lname': line['lname'],
                            'debit': line['debit'],
                            'credit': line['credit'],
                            'progress': line['progress'],
                        }
                        worksheet.write(row,col,res['ldate'],money)
                        worksheet.write(row,col+1,res['move'],money)
                        worksheet.write(row,col+2,res['partner_name'],money)
                        worksheet.write(row,col+3,res['lref'],money)
                        worksheet.write(row,col+4,res['lname'],money)
                        worksheet.write(row,col+5,res['debit'],money)
                        worksheet.write(row,col+6,res['credit'],money)
                        worksheet.write(row,col+7,res['progress'],money)
                        row+=1
                        array.append(res)
            if len(self.get_children_accounts(cr, uid, ids,account,context))>1 or len(data['ids'])>1 :
                worksheet.write(11,1,"Total",bold)
                worksheet.write(11,5,debit_total,bold2)
                worksheet.write(11,6,credit_total,bold2)
                worksheet.write(11,7,progres_total,bold2)
                

        display_account="All accounts"
        if self.display_account2 == 'movement':
            display_account="With movements"
        if self.display_account2 == 'not_zero':
            display_account="With balance not equal to zero"
        worksheet.write(2,0,_('Chart of Accounts'),bold)
        worksheet.write(3,0,res_company,normal)
        worksheet.write(2,3,_('Fiscal Year'),bold)
        worksheet.write(3,3,fiscal_year,normal)
        worksheet.write(2,6,_('Display Account'),bold)
        worksheet.write(3,6,_(display_account),normal)
        worksheet.write(5,0,_('Filter By'),bold)
        worksheet.write(6,0,_(filter_label),normal)
        worksheet.write(5,3,_('Sorted By'),bold)
        worksheet.write(6,3,self._get_sortby(data),normal)
        #worksheet.write(5,6,_('Target Moves'),bold)
        #worksheet.write(6,6,_(display_account),normal)
        worksheet.write(0,2,res_company,bold)
        worksheet.write(0,4,_('General Ledger'),bold)


        row = 10
        col = 0 
        """for cuenta in array:
            worksheet.write(row,col,cuenta['ldate'],money)
            worksheet.write(row,col+1,cuenta['move'],money)
            worksheet.write(row,col+2,cuenta['partner_name'],money)
            worksheet.write(row,col+3,cuenta['lref'],money)
            worksheet.write(row,col+4,cuenta['lname'],money)
            worksheet.write(row,col+5,cuenta['debit'],money)
            worksheet.write(row,col+6,cuenta['credit'],money)
            worksheet.write(row,col+7,cuenta['progress'],money)
            row+=1"""
        workbook.close()
        output.seek(0)
        vals = {
                    'name': 'General Ledger',
                    'datas_fname': 'general_Ledger.xlsx',
                    'description': 'General Ledger en Excel',
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

        return True

    def _sum_credit_account_currency(self,cr, uid, ids,account,context):
        if account.type == 'view':
            return account.credit
        move_state = ['draft','posted']
        if self.target_move2 == 'posted':
            move_state = ['posted','']
        cr.execute('SELECT sum(amount_currency) \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s) \
                AND l.credit > 0 \
                AND '+ self.query2 +' '
                ,(account.id, tuple(move_state)))
        sum_credit = cr.fetchone()[0] or 0.0
        if self.init_balance2:
            cr.execute('SELECT sum(amount_currency) \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s) \
                    AND l.credit > 0 \
                    AND '+ self.init_query2 +' '
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_credit += cr.fetchone()[0] or 0.0
        return abs(sum_credit)
    def _sum_debit_account_currency(self,cr, uid, ids,account,context):
        if account.type == 'view':
            return account.debit
        move_state = ['draft','posted']
        if self.target_move2 == 'posted':
            move_state = ['posted','']
        cr.execute('SELECT sum(amount_currency) \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND l.debit > 0 \
                AND (am.state IN %s) \
                AND '+ self.query2 +' '
                ,(account.id, tuple(move_state)))
        sum_debit = cr.fetchone()[0] or 0.0
        if self.init_balance2:
            cr.execute('SELECT sum(amount_currency) \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND l.debit > 0 \
                    AND (am.state IN %s) \
                    AND '+ self.init_query2 +' '
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_debit += cr.fetchone()[0] or 0.0
        return sum_debit
    def _get_sortby(self,data):
        if self.sortby2 == 'sort_date':
            return _('Date')
        elif self.sortby2 == 'sort_journal_partner':
            return _('Journal & Partner')
        elif self.sortby2 == 'sort_number':
            return _('Number')
        return _('Date')
    def _sum_debit_account(self, cr, uid, ids,account,context):
        if account.type == 'view':
            return account.debit
        move_state = ['draft','posted']
        if self.target_move2 == 'posted':
            move_state = ['posted','']
        cr.execute('SELECT sum(debit) \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s) \
                AND '+ self.query2 +' '
                ,(account.id, tuple(move_state)))
        sum_debit = cr.fetchone()[0] or 0.0
        if self.init_balance2:
            cr.execute('SELECT sum(debit) \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s) \
                    AND '+ self.init_query2 +' '
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_debit += cr.fetchone()[0] or 0.0
        return sum_debit
    def _sum_credit_account(self, cr, uid, ids,account,context):
        if account.type == 'view':
            return account.credit
        move_state = ['draft','posted']
        if self.target_move2 == 'posted':
            move_state = ['posted','']
        cr.execute('SELECT sum(credit) \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s) \
                AND '+ self.query2 +' '
                ,(account.id, tuple(move_state)))
        sum_credit = cr.fetchone()[0] or 0.0
        if self.init_balance2:
            cr.execute('SELECT sum(credit) \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s) \
                    AND '+ self.init_query2 +' '
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_credit += cr.fetchone()[0] or 0.0
        return sum_credit
    def _sum_balance_account(self, cr, uid, ids,account,context):
        if account.type == 'view':
            return account.balance
        move_state = ['draft','posted']
        if self.target_move2 == 'posted':
            move_state = ['posted','']
        cr.execute('SELECT (sum(debit) - sum(credit)) as tot_balance \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s) \
                AND '+ self.query2 +' '
                ,(account.id, tuple(move_state)))
        sum_balance = cr.fetchone()[0] or 0.0
        if self.init_balance2:
            cr.execute('SELECT (sum(debit) - sum(credit)) as tot_balance \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s) \
                    AND '+ self.init_query2 +' '
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_balance += cr.fetchone()[0] or 0.0
        return sum_balance
    def get_children_accounts(self, cr, uid, ids,account,context):
        res = []
        currency_obj = self.pool.get('res.currency')
        ids_acc = self.pool.get('account.account')._get_children_and_consol(cr, uid, account.id)
        currency = account.currency_id and account.currency_id or account.company_id.currency_id
        for child_account in self.pool.get('account.account').browse(cr, uid, ids_acc, context=context):
            sql = """
                SELECT count(id)
                FROM account_move_line AS l
                WHERE %s AND l.account_id = %%s
            """ % (self.query2)
            cr.execute(sql, (child_account.id,))
            num_entry = cr.fetchone()[0] or 0
            sold_account = self._sum_balance_account(cr,uid,ids,child_account,context)
            self.sold_accounts[child_account.id] = sold_account
            if self.display_account2 == 'movement':
                if child_account.type != 'view' and num_entry <> 0:
                    res.append(child_account)
            elif self.display_account2 == 'not_zero':
                if child_account.type != 'view' and num_entry <> 0:
                    if not currency_obj.is_zero(cr, uid, currency, sold_account):
                        res.append(child_account)
            else:
                res.append(child_account)
        if not res:
            return [account]
        return res
    def _sum_balance_account_currency(self, cr, uid, ids,account,context):
        if account.type == 'view':
            return account.balance
        move_state = ['draft','posted']
        if self.target_move2 == 'posted':
            move_state = ['posted','']
        cr.execute('SELECT (sum(amount_currency)) as tot_balance \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s) \
                AND '+ self.query2 +' '
                ,(account.id, tuple(move_state)))
        sum_balance = cr.fetchone()[0] or 0.0
        if self.init_balance2:
            cr.execute('SELECT (sum(amount_currency)) as tot_balance \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s) \
                    AND '+ self.init_query2 +' '
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_balance += cr.fetchone()[0] or 0.0
        return sum_balance
    def lines2(self, cr, uid, ids,account,context):
        """ Return all the account_move_line of account with their account code counterparts """
        move_state = ['draft','posted']
        if self.target_move2 == 'posted':
            move_state = ['posted', '']
        # First compute all counterpart strings for every move_id where this account appear.
        # Currently, the counterpart info is used only in landscape mode
        sql = """
            SELECT m1.move_id,
                array_to_string(ARRAY(SELECT DISTINCT a.code
                                          FROM account_move_line m2
                                          LEFT JOIN account_account a ON (m2.account_id=a.id)
                                          WHERE m2.move_id = m1.move_id
                                          AND m2.account_id<>%%s), ', ') AS counterpart
                FROM (SELECT move_id
                        FROM account_move_line l
                        LEFT JOIN account_move am ON (am.id = l.move_id)
                        WHERE am.state IN %s and %s AND l.account_id = %%s GROUP BY move_id) m1
        """% (tuple(move_state), self.query2)
        cr.execute(sql, (account.id, account.id))
        counterpart_res = cr.dictfetchall()
        counterpart_accounts = {}
        for i in counterpart_res:
            counterpart_accounts[i['move_id']] = i['counterpart']
        del counterpart_res

        # Then select all account_move_line of this account
        if self.sortby2 == 'sort_journal_partner':
            sql_sort='j.code, p.name, l.move_id'
        elif self.sortby2 == 'sort_number':
            sql_sort='m.name'
        else:
            sql_sort='l.date, l.move_id'
        sql = """
            SELECT l.id AS lid, l.date AS ldate, j.code AS lcode, l.currency_id,l.amount_currency,l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, l.period_id AS lperiod_id, l.partner_id AS lpartner_id,
            m.name AS move_name, m.id AS mmove_id,per.code as period_code,
            c.symbol AS currency_code,
            c.id AS currency_id,
            i.id AS invoice_id, i.type AS invoice_type, i.number AS invoice_number,
            p.name AS partner_name
            FROM account_move_line l
            JOIN account_move m on (l.move_id=m.id)
            LEFT JOIN res_currency c on (l.currency_id=c.id)
            LEFT JOIN res_partner p on (l.partner_id=p.id)
            LEFT JOIN account_invoice i on (m.id =i.move_id)
            LEFT JOIN account_period per on (per.id=l.period_id)
            JOIN account_journal j on (l.journal_id=j.id)
            WHERE %s AND m.state IN %s AND l.account_id = %%s ORDER by %s
        """ %(self.query2, tuple(move_state), sql_sort)
        cr.execute(sql, (account.id,))
        res_lines = cr.dictfetchall()
        res_init = []
        if res_lines and self.init_balance2:
            #FIXME: replace the label of lname with a string translatable
            sql = """
                SELECT 0 AS lid, '' AS ldate, '' AS lcode, COALESCE(SUM(l.amount_currency),0.0) AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(CASE WHEN l.debit > 0 THEN l.amount_currency ELSE 0 END),0.0) AS debit, COALESCE(SUM(CASE WHEN l.credit > 0 THEN l.amount_currency ELSE 0 END),0.0) AS credit, '' AS lperiod_id, '' AS lpartner_id,
                '' AS move_name, '' AS mmove_id, '' AS period_code,
                '' AS currency_code,
                NULL AS currency_id,
                '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,
                '' AS partner_name
                FROM account_move_line l
                LEFT JOIN account_move m on (l.move_id=m.id)
                LEFT JOIN res_currency c on (l.currency_id=c.id)
                LEFT JOIN res_partner p on (l.partner_id=p.id)
                LEFT JOIN account_invoice i on (m.id =i.move_id)
                JOIN account_journal j on (l.journal_id=j.id)
                WHERE %s AND m.state IN %s AND l.account_id = %%s
            """ %(self.init_query2, tuple(move_state))
            cr.execute(sql, (account.id,))
            res_init = cr.dictfetchall()
        res = res_init + res_lines
        account_sum = 0.0
        for l in res:
            l['move'] = l['move_name'] != '/' and l['move_name'] or ('*'+str(l['mmove_id']))
            l['partner'] = l['partner_name'] or ''
            account_sum += l['debit'] - l['credit']
            l['progress'] = account_sum
            l['line_corresp'] = l['mmove_id'] == '' and ' ' or counterpart_accounts[l['mmove_id']].replace(', ',',')
            # Modification of amount Currency
            if l['credit'] > 0 and l['debit'] ==0:
                if l['amount_currency'] != None:
                    l['amount_currency'] = abs(l['amount_currency']) * -1
                    l['credit']=abs(l['amount_currency'])
                    l['progress']=self.tot_currency 
                    l['debit']=0
            if l['credit'] > 0 and l['debit'] >0:
                if l['amount_currency'] != None:
                    l['amount_currency'] = abs(l['amount_currency']) * -1
                    l['progress']=self.tot_currency 
            if l['credit'] < 0 and l['debit'] >0:
                if l['amount_currency'] != None:
                    l['credit']=abs(l['credit'])
                    l['amount_currency'] = abs(l['amount_currency']) * -1
                    l['progress']=self.tot_currency 
            if l['amount_currency'] != None:
                self.tot_currency = self.tot_currency + l['amount_currency']
                if l['debit']>0 and l['credit']==0:
                    l['debit']=l['amount_currency']
                l['progress']=self.tot_currency
            l['currency_id']=self.pool.get('res.currency').browse(cr,uid, l['currency_id'],context=None)
        return res
    def lines(self, cr, uid, ids,account,context):
        """ Return all the account_move_line of account with their account code counterparts """
        move_state = ['draft','posted']
        if self.target_move2 == 'posted':
            move_state = ['posted', '']
        # First compute all counterpart strings for every move_id where this account appear.
        # Currently, the counterpart info is used only in landscape mode
        sql = """
            SELECT m1.move_id,
                array_to_string(ARRAY(SELECT DISTINCT a.code
                                          FROM account_move_line m2
                                          LEFT JOIN account_account a ON (m2.account_id=a.id)
                                          WHERE m2.move_id = m1.move_id
                                          AND m2.account_id<>%%s), ', ') AS counterpart
                FROM (SELECT move_id
                        FROM account_move_line l
                        LEFT JOIN account_move am ON (am.id = l.move_id)
                        WHERE am.state IN %s and %s AND l.account_id = %%s GROUP BY move_id) m1
        """% (tuple(move_state), self.query2)
        cr.execute(sql, (account.id, account.id))
        counterpart_res = cr.dictfetchall()
        counterpart_accounts = {}
        for i in counterpart_res:
            counterpart_accounts[i['move_id']] = i['counterpart']
        del counterpart_res

        # Then select all account_move_line of this account
        if self.sortby2 == 'sort_journal_partner':
            sql_sort='j.code, p.name, l.move_id'
        elif self.sortby2 == 'sort_number':
            sql_sort='m.name'
        else:
            sql_sort='l.date, l.move_id'
        sql = """
            SELECT l.id AS lid, l.date AS ldate, j.code AS lcode, l.currency_id,l.amount_currency,l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, l.period_id AS lperiod_id, l.partner_id AS lpartner_id,
            m.name AS move_name, m.id AS mmove_id,per.code as period_code,
            c.symbol AS currency_code,
            i.id AS invoice_id, i.type AS invoice_type, i.number AS invoice_number,
            p.name AS partner_name
            FROM account_move_line l
            JOIN account_move m on (l.move_id=m.id)
            LEFT JOIN res_currency c on (l.currency_id=c.id)
            LEFT JOIN res_partner p on (l.partner_id=p.id)
            LEFT JOIN account_invoice i on (m.id =i.move_id)
            LEFT JOIN account_period per on (per.id=l.period_id)
            JOIN account_journal j on (l.journal_id=j.id)
            WHERE %s AND m.state IN %s AND l.account_id = %%s ORDER by %s
        """ %(self.query2, tuple(move_state), sql_sort)
        cr.execute(sql, (account.id,))
        res_lines = cr.dictfetchall()
        res_init = []
        if res_lines and self.init_balance2:
            #FIXME: replace the label of lname with a string translatable
            sql = """
                SELECT 0 AS lid, '' AS ldate, '' AS lcode, COALESCE(SUM(l.amount_currency),0.0) AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, '' AS lperiod_id, '' AS lpartner_id,
                '' AS move_name, '' AS mmove_id, '' AS period_code,
                '' AS currency_code,
                NULL AS currency_id,
                '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,
                '' AS partner_name
                FROM account_move_line l
                LEFT JOIN account_move m on (l.move_id=m.id)
                LEFT JOIN res_currency c on (l.currency_id=c.id)
                LEFT JOIN res_partner p on (l.partner_id=p.id)
                LEFT JOIN account_invoice i on (m.id =i.move_id)
                JOIN account_journal j on (l.journal_id=j.id)
                WHERE %s AND m.state IN %s AND l.account_id = %%s
            """ %(self.init_query2, tuple(move_state))
            cr.execute(sql, (account.id,))
            res_init = cr.dictfetchall()
        res = res_init + res_lines
        account_sum = 0.0
        for l in res:
            l['move'] = l['move_name'] != '/' and l['move_name'] or ('*'+str(l['mmove_id']))
            l['partner'] = l['partner_name'] or ''
            account_sum += l['debit'] - l['credit']
            l['progress'] = account_sum
            l['line_corresp'] = l['mmove_id'] == '' and ' ' or counterpart_accounts[l['mmove_id']].replace(', ',',')
            # Modification of amount Currency
            if l['credit'] > 0:
                if l['amount_currency'] != None:
                    l['amount_currency'] = abs(l['amount_currency']) * -1
            if l['amount_currency'] != None:
                self.tot_currency = self.tot_currency + l['amount_currency']
        return res
    def _print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)

        data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby'])[0])
        if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
            data['form'].update({'initial_balance': False})

        if data['form']['landscape'] is False:
            data['form'].pop('landscape')
        else:
            context['landscape'] = data['form']['landscape']
        return self.pool['report'].get_action(cr, uid, [], 'account.report_generalledger', data=data, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from datetime import datetime
import locale
import pytz
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
class account_account(osv.osv):
	_inherit = 'account.account'
	def _compute2(self, cr, uid, ids, field_names, arg=None, context=None,query='', query_params=()):
		mapping = {
            'balance_currency': "COALESCE(SUM(CASE WHEN l.debit > 0 THEN l.amount_currency ELSE 0 END),0.0) + COALESCE(SUM(CASE WHEN l.credit > 0 THEN l.amount_currency ELSE 0 END),0.0) as balance_currency",
            'debit_currency': "COALESCE(SUM(CASE WHEN l.debit > 0 THEN l.amount_currency ELSE 0 END),0.0) as debit_currency",
            'credit_currency': "abs(COALESCE(SUM(CASE WHEN l.credit > 0 THEN l.amount_currency ELSE 0 END),0.0)) as credit_currency",
            # by convention, foreign_balance is 0 when the account has no secondary currency, because the amounts may be in different currencies
        }
        #get all the necessary accounts
		children_and_consolidated = self._get_children_and_consol(cr, uid, ids, context=context)
        #compute for each account the balance/debit/credit from the move lines
		accounts = {}
		res = {}
		null_result = dict((fn, 0.0) for fn in field_names)
		if children_and_consolidated:
			aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
			wheres = [""]
			if query.strip():
				wheres.append(query.strip())
			if aml_query.strip():
				wheres.append(aml_query.strip())
			filters = " AND ".join(wheres)
            # IN might not work ideally in case there are too many
            # children_and_consolidated, in that case join on a
            # values() e.g.:
            # SELECT l.account_id as id FROM account_move_line l
            # INNER JOIN (VALUES (id1), (id2), (id3), ...) AS tmp (id)
            # ON l.account_id = tmp.id
            # or make _get_children_and_consol return a query and join on that
			request = ("SELECT l.account_id as id, " +\
                       ', '.join(mapping.values()) +
                       " FROM account_move_line l" \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id")
			params = (tuple(children_and_consolidated),) + query_params
			cr.execute(request, params)

			for row in cr.dictfetchall():
				accounts[row['id']] = row

            # consolidate accounts with direct children
			children_and_consolidated.reverse()
			brs = list(self.browse(cr, uid, children_and_consolidated, context=context))
			sums = {}
			currency_obj = self.pool.get('res.currency')
			while brs:
				current = brs.pop(0)
#                can_compute = True
#                for child in current.child_id:
#                    if child.id not in sums:
#                        can_compute = False
#                        try:
#                            brs.insert(0, brs.pop(brs.index(child)))
#                        except ValueError:
#                            brs.insert(0, child)
#                if can_compute:
				for fn in field_names:
					sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
					for child in current.child_id:
						if child.company_id.currency_id.id == current.company_id.currency_id.id:
							sums[current.id][fn] += sums[child.id][fn]
						else:
							sums[current.id][fn] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child.id][fn], context=context)

                # as we have to relay on values computed before this is calculated separately than previous fields
				if current.currency_id and current.exchange_rate and \
                            ('adjusted_balance' in field_names or 'unrealized_gain_loss' in field_names):
                    # Computing Adjusted Balance and Unrealized Gains and losses
                    # Adjusted Balance = Foreign Balance / Exchange Rate
                    # Unrealized Gains and losses = Adjusted Balance - Balance
					adj_bal = sums[current.id].get('foreign_balance', 0.0) / current.exchange_rate
					sums[current.id].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current.id].get('balance', 0.0)})

			for id in ids:
				res[id] = sums.get(id, null_result)
		else:
			for id in ids:
				res[id] = null_result
		return res
	_columns = {
		'balance_currency': fields.function(_compute2, digits_compute=dp.get_precision('Account'), string='Balance', multi='balance_currency'),
		'credit_currency': fields.function(_compute2, digits_compute=dp.get_precision('Account'), string='Credit', multi='balance_currency'),
        'debit_currency': fields.function(_compute2, digits_compute=dp.get_precision('Account'), string='Debit', multi='balance_currency'),
		
	}

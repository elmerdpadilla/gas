# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import workflow
from dateutil.relativedelta import relativedelta
class wizard_with_step(osv.osv_memory):
   _name = 'wizard_with_report'
   _description = 'Wizard with report'    
   _columns = { 
              'dateini': fields.date('Date 1',),
              'dateend': fields.date('Name 2',),
              } 

   def action_next(self, cr, uid, ids, context=None):
      #your treatment to click  button next 
      #...
      # update state to  step2
      #return view
      return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard_with_report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': this.id,
            'views': [(False, 'form')],
            'target': 'new',
             }


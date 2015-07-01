# -*- coding: utf-8 -*-

from openerp.osv import osv
#from datetime import *
#INSERT INTO account_config_settings(date_stop,period,date_start,company_id,group_multi_currency) values (now(),'month','2015-01-01',1,True)
class Currency_Historial(osv.osv):
	_name = "currency.historial"

	def init(self,cr):
		# Desactiva todas las monedas excepto dolares y lempiras
		cr.execute("""UPDATE res_currency SET active=False        WHERE (name<>'USD') and (name<>'HNL');""")

		#Posición del símbolo antes de la cantidad
		cr.execute("""UPDATE res_currency SET position = 'before' WHERE  name ='USD'  or   name ='HNL' ;""")
		
		#elimina el menuitem Account/JournalEntries/JournalItem, No se pierde la accion ni la vista a la que apuntaba el menú
		cr.execute("""DELETE FROM ir_ui_menu WHERE id = 622 and name like '%Journal Items%'""")



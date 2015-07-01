from openerp import models, fields, api, osv
from openerp.exceptions import except_orm, Warning, RedirectWarning
import os
import shutil
import time
from os import walk 

class innovabase_replace_files_line(models.Model):
	_name = 'innovabase.replace.files.line'
	
	name 				= fields.Char('path')
	owner				= fields.Char('owner')
#	replacement_file 	= fields.Char('replacement file')
	enable				= fields.Boolean('enable')
	description 		= fields.Text('description')
	replace_files		= fields.Many2one('innovabase.replace.files')

	

class innovabase_replace_files(models.Model):
	_name = 'innovabase.replace.files'
	
	name  = fields.Char(string='path',help='ruta de la carpeta que contiene el archivo de configuracion de sustitucion de archivos,ejemplo: /home/innova/carpeta_addons/InovaBase/archivos', default='/home/USER/CARPETA_ADDONS/InnovaBase/archivos')
	line  = fields.One2many('innovabase.replace.files.line','replace_files')

	@api.onchange('name')
	def path_change(self):
		print 'onchange name___'*10
		ids = []
		path = self.name
		for (path, ficheros, archivos) in walk(path):
			for archivo in archivos:
				if not archivo.endswith('~'):
					full_file_path 	= path + '/' + archivo									
					name = ''

					if 'InnovaBase/archivos/' in full_file_path:
						name 		= full_file_path.split('InnovaBase/archivos/')[1]
					elif 'InnovaBase/archivos_personalizados/' in full_file_path:
						name 		= full_file_path.split('InnovaBase/archivos_personalizados/')[1]
					else:
						raise except_orm('El directorio existe pero no es valido','escriba la ruta de la carpeta de archivos dentro de InnovaBase')

#					name 			= full_file_path.split('InnovaBase/archivos/')[1]
					description 	= ''
					owner			= ''
					openfile = open(full_file_path, 'r')
					for line in openfile:
						if '#$#description' in line:
							description = description + line.split('#$#description')[1]
						if '#$#owner' in line:
							owner = line.split('#$#owner')[1]
					create_id = self.env['innovabase.replace.files.line'].create({'name':name,'enable':True,'description':description, 'owner':owner}).id
					ids.append(create_id)
		self.line = ids

	def execute(self, cr, uid,vals, context=None):
		manager = self.browse(cr,uid,vals[0],context=context)
        # recorremos el archivo linea por linea
		for file_path in manager.line:
				if file_path.enable:
		            #si se va a sustituir un archivo sacamos un respaldo del archivo
					if os.path.exists(os.getcwd()+'/'+file_path.name):
						os.rename(os.getcwd()+'/'+file_path.name,os.getcwd()+'/'+file_path.name+time.strftime('%d %b %Y'))
		    	    #copia el archivo rutas[1] en la ubicacion rutas[2]
					print '#'*20
					print manager.name+'/'+file_path.name
					print os.getcwd()+'/'+file_path.name
					shutil.copyfile(manager.name+'/'+file_path.name,os.getcwd()+'/'+file_path.name)
		raise except_orm('Cambios Aplicados','Actualice completamente odoo (-u all)')
#		raise Warning('Cambios Aplicados: debe actualizar odoo (-u all)')

		return True




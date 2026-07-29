PROJECT_DATA_TEMPLATE = {
	'ConstructionSite':'...',
	'Verifier':{
		'Name':'...',
		'Position':'ГИП'
		},
	'Code':'...',
	'Description':'...'
	}

WORK_MODES_TEMPLATE = {
	'position_mode':True, # включить нумерацию позиций с подпунктами;
	'transportation_mode':True, # включить режим транспортировки с делением на тип покрытия;
	'ground_complementation_mode':False, # режим сопоставления плотности грунтов с нормативными значениями
	'position_types' : ('работа','материал','перевозка','оборудование', 'машина', 'прочее'), # Возможные типы позиций
	'packed_files_for_BoQ' : False	# Упаковка файлов обоснования для раздела ВОР 
}

UNITS_TEMPLATE = {
	'-':{
		'label':'-',
		'round':None
		},
	'meter':{
		'label':'м',
		'round':2
		},
	'p_m':{
		'label':'п.м',
		'round':2
		},
	'km':{
		'label':'км',
		'round':3
		},
	'square_meter':{
		'label':'м²',
		'round':0
		},
	'cubic_meter':{
		'label':'м³',
		'round':1
		},
	'cubic_meter_profile':{
		'label':'м³ (проф)',
		'round':1
		},
	'cubic_meter_constr':{
		'label':'м³ (констр)',
		'round':2
		},
	'cubic_meter_material':{
		'label':'м³ (матер)',
		'round':0
		},
	'cubic_meter_soil':{
		'label':'м³ (грунт)',
		'round':0
		},
	'hectare':{
		'label':'га',
		'round':3
		},
	'count':{
		'label':'шт.',
		'round':0
		},
	'kg':{
		'label':'кг',
		'round':2
		},
	'ton':{
		'label':'т',
		'round':3
		},
	'liter':{
		'label':'л',
		'round':2
		},
	'milliliter':{
		'label':'мл',
		'round':0
		},
	'package':{
		'label':'уп.',
		'round':0
		},
	'machine_hours':{
		'label':'маш.-ч',
		'round':2
		}

}

POSTS_TEMPLATE = (
		'Директор',
		'ГИП',
		'Руководитель группы',
		'Ведущий инженер',
		'Инженер 1 категории',
		'Инженер 2 категории',
		'Инженер 3 категории'
)

CHIEFS = tuple(['Иванов И.И.'])

PERFORMERS_TEMPLATE=tuple(['Иванов И.И.'])
# Copyright © 2026 OldNestling
# License: GPLv3 (GNU General Public License Version 3)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from dataclasses import dataclass
import json, copy
from .Utilities import convert_value
from .DataLib import DataLibraryManager

# TODO Переработать по типу остальных библиотек с коллекцией-списком

class Soils_Manager(DataLibraryManager):
	""" Управляет процессом создания и настройки библиотеки грунтов """
	FILE = 'Soils' # Файл с данными

	# Наименование фалов баз данных
	GESN_1_FILE = 'ГЭСН_1.json' 
	GESN_4_FILE = 'ГЭСН_4.json'
	GESN_5_FILE = 'ГЭСН_5.json'

	def __init__(self, project):
		super().__init__()
		self.project = project # Единый глобальный объект, хранящий настройки и артубты для всех модулей
		self.library = {}  #  словарь всех созданных объектов Soil
		self.load_lib()
		# Устанавливка режима сопоставления
		Soil._compare_mode = self.project.work_modes.get('ground_complementation_mode',False) if self.project else False 
	

	# ------------------------------- Загрузка и сохранение БД -----------------------------
	def load_lib(self):
		if not self.project or self._file_path is None or self._file_path is None:
			return
		try:
			with open(self._file_path, "r", encoding="utf-8") as f:
				data = json.load(f)
				data.sort(key= lambda dct: dct.get('local_num'))
				for soil in data:
					self.soil_deserializer(soil)
		except FileNotFoundError:
			self.library = {}
		except json.JSONDecodeError:
			pass
		except Exception as e:
			raise RuntimeError(f'{"-"*40}\nОшибка загрузки файла {self._file_path}: {e}')

	def save_lib(self):
		if not self.project or not self.lock_owned:
			return False
		try:
			tmp_path = self._file_path.with_suffix(".tmp")
			with open(tmp_path, 'w', encoding='utf-8') as f:
				data = []
				for value in self.library.values():
					data.append(self.soil_serializer(value))
				json.dump(data, f, indent=4, ensure_ascii=False)
			tmp_path.replace(self._file_path)
			self.unlock()
			return True
		except Exception as e:
			print(f'{"-"*40}\nПроизошла ошибка: {e}')
			if tmp_path.exists():
				tmp_path.unlink(missing_ok=True)
			return False

	def reload_lib(self):
		""" Обновляет список грунтов, а также данные по ГЭСН для каждого """
		self.library = {}
		self.load_lib()
		# загрузка данных для применения в цикле без повторного вызова
		gesn_1_data=self.gesn_1_data
		gesn_4_data=self.gesn_4_data
		gesn_5_data=self.gesn_5_data

		for obj in self.library.values():
			# обновление данных по ГЭСН 1 
			if obj.gesn_1_obj:
				num = obj.gesn_1_obj.num
				obj.gesn_1_obj = self.get_gesn_1_obj(num, gesn_1_data)

			# обновление данных по ГЭСН 4
			if obj.gesn_4_obj:
				num = obj.gesn_4_obj.num
				obj.gesn_4_obj = self.get_gesn_4_obj(num, gesn_4_data)

			# обновление данных по ГЭСН 5
			if obj.gesn_5_obj:
				num = obj.gesn_5_obj.num
				obj.gesn_5_obj = self.get_gesn_5_obj(num, gesn_5_data)
		self.unlock()

	# ------------------------------ Загрузка и сохранение JSON ----------------------------

	@staticmethod
	def soil_serializer(obj_soil):
		""" Создаеn словарь Python для экземляра объекта класса Soil для сериализации в json """
		if isinstance(obj_soil,Soil):
			json_soil = {
				"local_num": obj_soil.local_num,
				"local_name": obj_soil.local_name,
				"local_density": obj_soil.local_density,
				"gesn_1_obj": obj_soil.gesn_1_obj.json_serializer() if obj_soil.gesn_1_obj else None,
				"gesn_4_obj": obj_soil.gesn_4_obj.json_serializer() if obj_soil.gesn_4_obj else None,
				"gesn_5_obj": obj_soil.gesn_5_obj.json_serializer() if obj_soil.gesn_5_obj else None,
				"note1": obj_soil.note1,
				"note2": obj_soil.note2,
				"comment": obj_soil.comment
			}
			return json_soil
		
	def soil_deserializer(self, dict_soil):
		""" Распознаёт еденичный объект класса Soil из предоставленного словаря json и 
		добавляет его в общий словарь грунтов
		:dict_soil: одна пара словаря ключ-значение, где значение это атрибуты класса
		"""
		if isinstance(dict_soil, dict):
			key = dict_soil.get('local_num') # например "ИГЭ_1"
			gesn_1_obj = dict_soil.get('gesn_1_obj')
			gesn_4_obj = dict_soil.get('gesn_4_obj')
			gesn_5_obj = dict_soil.get('gesn_5_obj')

			soil = Soil(
				key,
				dict_soil.get('local_name',''),
				dict_soil.get('local_density'),
				Gesn1.json_deserializer(gesn_1_obj),
				Gesn4.json_deserializer(gesn_4_obj),
				Gesn5.json_deserializer(gesn_5_obj),
				dict_soil.get('note1'),
				dict_soil.get('note2'),
				dict_soil.get('comment')				
			)
			
			if key not in self.library and key is not None:
				self.library[key] = soil
		else:
			print('Предоставленные данные не подлежат десериализации')

	def save_gesn1_data(self, data):
		""" Сохраняет изменения в базе данных по ГЭСН 1 """
		gesn1_data = {}
		gesn1_data['short_names'] = Gesn1.short_names
		gesn1_data['data'] = data
		try:
			file = self.project.base_dir / self.DATA / self.GESN_1_FILE
			with open(file, 'w', encoding='utf-8') as f:
				json.dump(gesn1_data, f, indent=4, ensure_ascii=False)
		except Exception as e:
			print(f'{"-"*40}\nПроизошла ошибка: {e}')
	
	def save_gesn5_data(self, data):
		""" Сохраняет изменения в базе данных по ГЭСН 5 """
		gesn5_data = {}
		gesn5_data['short_names'] = Gesn5.short_names
		gesn5_data['data'] = data
		try:
			file = self.project.base_dir / self.DATA / self.GESN_5_FILE
			with open(file, 'w', encoding='utf-8') as f:
				json.dump(gesn5_data, f, indent=4, ensure_ascii=False)
		except Exception as e:
			print(f'{"-"*40}\nПроизошла ошибка: {e}')

	# --------------------------------- Данные ГЭСН -------------------------------------

	@property
	def gesn_1_data(self):
		""" Получает БД ГЭСН 1 """
		if self.project:
			file = self.project.base_dir / self.DATA / self.GESN_1_FILE
			try:
				with open(file, "r", encoding="utf-8") as f:
						data = json.load(f)
						return data['data']
			except FileNotFoundError:
				from Templates.GESN_1 import GESN_DATA
				return GESN_DATA['data']
			except Exception as e:
				print(f'{"-"*40}\Произошла ошибка: {e}')

	
	@property
	def gesn_4_data(self):
		""" Получает БД ГЭСН 4 """
		if self.project:
			file = self.project.base_dir / self.DATA / self.GESN_4_FILE
			try:
				with open(file, "r", encoding="utf-8") as f:
						data = json.load(f)
						return data['data']
			except FileNotFoundError:
				from Templates.GESN_4 import GESN_DATA
				return GESN_DATA['data']
			except Exception as e:
				print(f'{"-"*40}\Произошла ошибка: {e}')

	
	@property
	def gesn_5_data(self):
		""" Получает БД ГЭСН 5 """
		if self.project:
			file = self.project.base_dir / self.DATA / self.GESN_5_FILE
			try:
				with open(file, "r", encoding="utf-8") as f:
						data = json.load(f)
						return data['data']
			except FileNotFoundError:
				from Templates.GESN_5 import GESN_DATA
				return GESN_DATA['data']
			except Exception as e:
				print(f'{"-"*40}\Произошла ошибка: {e}')
	
	
	def get_gesn1_headers(self):
		""" Получает заголвки по столбцов для таблицы по ГЭСН 1 """
		headers = ['№', 'Наименование и краткая характеристика грунтов']
		headers.extend(list(Gesn1.short_names.values()))
		return headers
	
	def get_gesn4_headers(self):
		""" Получает заголвки по столбцов для таблицы по ГЭСН 4 """
		return list(Gesn4.short_names.values())
	
	def get_gesn5_headers(self):
		""" Получает заголвки по столбцов для таблицы по ГЭСН 5 """
		return list(Gesn5.short_names.values())



	# ----------------------- Передача данных ----------------------------------
	
	def get_soils_gesn1_data(self) -> list:
		""" Собирает данные для диалога земляных работ
		Возвращает список с кортежами внутри которых: номер грунта, доступные работы
		Доступные работы содержат в себе: Наименование работы, ссылку, индекс
		"""

		soils: dict = self.library
		soils_list = []
		for key, soil in soils.items():
			soil: Soil
			gesn_1_obj: Gesn1 = soil.gesn_1_obj 
			if gesn_1_obj is None:
				continue
			works_list = []
			short_names = gesn_1_obj.short_names
			for i in range(1, 14):
				work = f'work_{i}'
				name = short_names[work]
				value = getattr(gesn_1_obj, work)
				if value is None:
					continue
				works_list.append((name, f'ВГ.{key}.ГЭСН1.{i}', i-1))
			soils_list.append((key, works_list))
		return soils_list
	
	def get_soils_gesn5_data(self) -> list:
		soils: dict = self.library
		soils_list = []
		for soil in soils.values():
			soil: Soil
			gesn_5_obj: Gesn5 = soil.gesn_5_obj 
			if gesn_5_obj is None:
				continue
			soils_list.append(soil)
		return soils_list


	# ------------------------- Работа с ИГЭ -----------------------------------

	def show_soils(self):
		print('Текущий список ИГЭ в базе:')
		for key, value in self.library.items():
			print(f"	— {key}: {value}")
	

	def get_gesn_1_obj(self, key, gesn_data = None):
		""" Преобразует выбранный словарь из файла JSON в объект dataclass Gesn1
		 :key: Ключ (номер грунта по ГЭСН 1) для поиска словаря с данными
		 :gesn_data: загруженные данные из файоа JSON. На случай, если функция применятся многократно, чтобы не читать файл каждый раз
		   """
		if not self.project:
			return None
		data = gesn_data if gesn_data else self.gesn_1_data
		if isinstance(data, dict) and  key in data:
			soil = data[key]
			soil['num'] = key
			return Gesn1.json_deserializer(soil)
	
	def get_gesn_4_obj(self, key : str, gesn_data = None):
		""" Преобразует выбранный словарь из файла JSON в объект dataclass Gesn1
		 :key: Ключ из раздела и группы грунта по типу 'раздел-группа'
		 :gesn_data: загруженные данные из файоа JSON. На случай, если функция применятся многократно, чтобы не читать файл каждый раз
		   """
		if not self.project:
			return None
		if key is None or key == '-':
			return None
		data = gesn_data if gesn_data else self.gesn_4_data
		try:
			section, group = key.split('-')
			group= int(group)
		except (ValueError, AttributeError):
			return None
		
		if isinstance(data, dict) and  section in data:
			lst = data[section]
			for obj in lst:
				if obj.get('soil_group') == group:
					description = obj.get('description')
					soil = {
						'drillability_type' : section,
						'soil_group' :  group,
						'description' : description
					}
					return Gesn4.json_deserializer(soil)
		return None

		
	def get_gesn_5_obj(self, key, gesn_data = None):
		""" Преобразует выбранный словарь из файла JSON в объект dataclass Gesn1
		 :key: Ключ (номер грунта по ГЭСН 1) для поиска словаря с данными
		 :gesn_data: загруженные данные из файоа JSON. На случай, если функция применятся многократно, чтобы не читать файл каждый раз
		   """
		if not self.project:
			return None
		data = gesn_data if gesn_data else self.gesn_5_data
		if isinstance(data, dict) and  key in data:
			soil = data[key]
			soil['num'] = key
			return Gesn5.json_deserializer(soil)


	def create_soil(
			self, 
			local_num, 
			local_name, 
			local_density, 
			gesn_1_num=None, 
			gesn_4_num=None, 
			gesn_5_num=None, 
			note1=None, 
			note2=None, 
			comment=None
	):
		""" Создать слой ИГЭ и добавить коллекцию """
		gesn_1_obj = self.get_gesn_1_obj(gesn_1_num) if gesn_1_num else None
		gesn_4_obj = self.get_gesn_4_obj(gesn_4_num) if gesn_4_num else None
		gesn_5_obj = self.get_gesn_5_obj(gesn_5_num) if gesn_5_num else None
		soil = Soil(local_num, local_name, local_density, gesn_1_obj, gesn_4_obj, gesn_5_obj, note1, note2, comment)
		self.library[local_num] = soil

	# удалить слой ИГИ из коллекцию

	def edit_soil(self, data):
		old_soil_num = data.get('old_soil_num')
		local_num = data.get('local_num')
		local_name = data.get('local_name')
		local_density = data.get('local_density')
		gesn_1_num = data.get('gesn_1_num')
		gesn_4_num = data.get('gesn_4_num')
		gesn_5_num = data.get('gesn_5_num')
		note1 = data.get('note1')
		note2 = data.get('note2')
		comment = data.get('comment')

		gesn_1_obj = self.get_gesn_1_obj(gesn_1_num) if gesn_1_num else None
		gesn_4_obj = self.get_gesn_4_obj(gesn_4_num) if gesn_4_num else None
		gesn_5_obj = self.get_gesn_5_obj(gesn_5_num) if gesn_5_num else None

		if old_soil_num == local_num:
			soil = self.library.get(old_soil_num)

			soil.set_local_num(local_num)
			soil.set_local_name(local_name)
			soil.set_local_density(local_density)
			soil.set_gesn_1_obj(gesn_1_obj)
			soil.set_gesn_4_obj(gesn_4_obj)
			soil.set_gesn_5_obj(gesn_5_obj)
			soil.set_note1(note1)
			soil.set_note2(note2)
			soil.set_comment(comment)
		
		else:
			del self.library[old_soil_num]

			soil = Soil(
				local_num,
				local_name,
				local_density,
				gesn_1_obj,
				gesn_4_obj,
				gesn_5_obj,
				note1,
				note2,
				comment
			)

			self.library[soil.local_num] = soil

	
	def remove_soil(self, key):
		try:
			del self.library[key]
		except KeyError:
			self.reload_lib()

	def copy_soil(self, key):
		""" 
		Создаёт коипю ИГЭ с временным именем-заглушкой

		Ars:
			:key: Ключ выбранного ИГЭ
		
		Returns:
			:new_key: Новый временный ключ
		"""
		if key:
			new_obj = copy.deepcopy(self.library[key])
			new_key = 'ИГЭ_'
			new_obj.set_local_num(new_key)
			self.library[new_obj.local_num] = new_obj
			return new_key

	
#-------------------------------------------------------------------------------------------

@dataclass
class Gesn1:
	""" класс объекта для импорта данных из ГЭСН_1.json """

	# Атрибуты класса
	short_names = {
		"name": "Наименование и краткая характеристика грунтов",
		"density": "Средняя плотность в естественном залегании кг/м³",
        "work_1": "Механизированная разработка грунтов экскаваторами одноковшовыми",
        "work_2": "Механизированная разработка грунтов экскаваторами траншейными цепными",
        "work_3": "Механизированная разработка грунтов экскаваторами траншейными роторными",
        "work_4": "Механизированная разработка грунтов скреперами",
        "work_5": "Механизированная разработка грунтов бульдозерами",
        "work_6": "Механизированная разработка грунтов грейдерами",
        "work_7": "Механизированная разработка грунтов грейдер-элеваторами",
        "work_8": "Механизированная разработка грунтов бурильнокрановыми машинами",
        "work_9": "Разработка грунтов вручную",
        "work_10": "Разрыхление мерзлых грунтов",
        "work_11": "Нарезка прорезей в мерзлых грунтах баровыми машинами",
        "work_12": "Рыхление грунта бульдозерами рыхлителями",
        "work_13": "Рыхление мерзлых грунтов бульдозерами-рыхлителями"
	}

	# Атрибуты экземпляра
	num: str | int = None
	name: str = None
	density: int | str | None = None
	work_1: int | str | None = None
	work_2: int | str | None = None
	work_3: int | str | None = None
	work_4: int | str | None = None
	work_5: int | str | None = None
	work_6: int | str | None = None
	work_7: int | str | None = None
	work_8: int | str | None = None
	work_9: int | str | None = None
	work_10: int | str | None = None
	work_11: int | str | None = None
	work_12: int | str | None = None
	work_13: int | str | None = None

	# ===================================== Методы =====================================

	def __str__(self):
		return f'Грунт по ГЭСН 1: {self.num} ({self.name}), плотность {self.density} кг/м³ [{self.work_1}|{self.work_2}|{self.work_3}|{self.work_4}|{self.work_5}|{self.work_6}|{self.work_7}|{self.work_8}|{self.work_9}|{self.work_10}|{self.work_11}|{self.work_12}|{self.work_13}]'

	def json_serializer(self):
		gesn_1_dict = {
			'num' : self.num,
			'name' : self.name,
			'density' : self.density,
			'work_1' : self.work_1,
			'work_2' : self.work_2,
			'work_3' : self.work_3,
			'work_4' : self.work_4,
			'work_5' : self.work_5,
			'work_6' : self.work_6,
			'work_7' : self.work_7,
			'work_8' : self.work_8,
			'work_9' : self.work_9,
			'work_10' : self.work_10,
			'work_11' : self.work_11,
			'work_12' : self.work_12,
			'work_13' : self.work_13
		}
		return gesn_1_dict

	@classmethod
	def json_deserializer(cls, data: dict | None):
		if data is None:
			return None
		return cls(**data)

@dataclass
class Gesn4:
	""" класс объекта для импорта данных из ГЭСН_4.json """
	
	# Атрибуты класса
	short_names = {
		"I":"Роторное бурение. Направленное бурение с применением винтовых забойных двигателей",
        "II":"Колонковое бурение",
        "III":"Ударно-вращательное, перфораторное бурение",
        "IV":"Шнековое бурение",
        "V":"Ударно-канатное бурение"
	}

	# Атрибуты объекта
	drillability_type: str = None # Распределение грунтов по буримости
	soil_group: int | None = None # Группа грунтов
	description: str = None # Наименование и характеристика грунтов

	@property
	def num(self):
		return f'{self.drillability_type}-{self.soil_group}'

	# ===================================== Методы =====================================

	def json_serializer(self):
		gesn_4_dict = {
			'drillability_type' : self.drillability_type,
			'soil_group' : self.soil_group,
			'description' : self.description
		}
		return gesn_4_dict

	@classmethod
	def json_deserializer(cls, data: dict | None):
		if data is None:
			return None
		return cls(**data)


@dataclass
class Gesn5:
	""" класс объекта для импорта данных из ГЭСН_5.json """
	#  Атрибуты класса
	short_names = {
		"name": "Наименование и характеристика грунтов и пород",
		"soil_group_1": "Группа грунтов и пород по способам бурения: Вращательное бурение",
        "soil_group_2": "Группа грунтов и пород по способам бурения: Ударно-канатное бурение",
        "expenditure_1": "Расход бетона на 1 м³ конструктивного объема сваи при диаметре, мм, до 630",
        "expenditure_2": "Расход бетона на 1 м³ конструктивного объема сваи при диаметре, мм, до 720",
        "expenditure_3": "Расход бетона на 1 м³ конструктивного объема сваи при диаметре, мм, до 830",
        "expenditure_4": "Расход бетона на 1 м³ конструктивного объема сваи при диаметре, мм, до 1020"
	}
	# Атрибуты объекта
	num: str | int = None
	name: str = None
	soil_group_1: int | None = None
	soil_group_2: int | None = None
	expenditure_1: float | None = None
	expenditure_2: float | None = None
	expenditure_3: float | None = None
	expenditure_4: float | None = None

	# ===================================== Методы =====================================

	def __str__(self):
		return f'Грунт по ГЭСН 5: {self.num} ({self.name}), [{self.expenditure_1}|{self.expenditure_2}|{self.expenditure_3}|{self.expenditure_4}]'

	def json_serializer(self):
		gesn_5_dict = {
			'num' : self.num,
			'name' : self.name,
			'soil_group_1' : self.soil_group_1,
			'soil_group_2' : self.soil_group_2,
			'expenditure_1' : self.expenditure_1,
			'expenditure_2' : self.expenditure_2,
			'expenditure_3' : self.expenditure_3,
			'expenditure_4' : self.expenditure_4
		}
		return gesn_5_dict

	@classmethod
	def json_deserializer(cls, data: dict | None):
		if data is None:
			return None
		return cls(**data)

#-------------------------------------------------------------------------------------------

class Soil:
	"""Класс для создания объектов, представляющих собой инженерно-геологические слои по результат изысканий. 
	Настройка выполняется в полуавтоматическом режиме
	Atr:

	:local_num: номер ИГЭ
	:local_name: наименование по результатом ИГИ
	:local_density: плотность по результатом ИГИ т/м³
	:gesn_1_num: данные по ГЭСН 1
	:gesn_4_num: данные по ГЭСН 4
	:gesn_5_num: данные по ГЭСН 5
	:comment: пользовательское примечание
	"""

	_compare_mode = None 
	

	def __init__(self, local_num, local_name, local_density, gesn_1_obj = None, gesn_4_obj = None, gesn_5_obj = None,  note1=None, note2=None, comment = None):
		self.local_num: str = local_num # номер ИГЭ
		self.local_name: str = local_name.strip() # наименование по результатом ИГИ
		self.local_density: float = convert_value(local_density) # плотность по результатом ИГИ т/м³
		self.gesn_1_obj: object | None = gesn_1_obj # данные по ГЭСН 1
		self.gesn_4_obj: object | None = gesn_4_obj # данные по ГЭСН 4
		self.gesn_5_obj: object | None = gesn_5_obj # данные по ГЭСН 5
		self.note1: str | None =  note1 # Примечание №1 (замещает автовычисление)
		self.note2: str | None =  note2 # Примечание №2 (замещает автовычисление)
		self.comment: str | None = comment # пользовательское примечание

	def __str__(self):
		return f"Грунт № {self.local_num}: {self.local_name}, принятая плотность - {self.accepted_density} т/м³"

	@property
	def accepted_density(self):
		if self.gesn_1_obj and self._compare_mode:
			return self.get_density(self.local_density, self.gesn_1_obj.density)
		elif self._compare_mode:
			return '[НЕТ ДАННЫХ ПО ГЭСН 1]'
		else:
			return self.local_density
			
	
	@property
	def _note1(self):
		'''Итоговое примечание №1'''
		none_data = {None, 'None', '-', '', ' '}
		if self.note1 in none_data:
			if self.gesn_1_obj:
				text = f'{self.local_name} ({self.gesn_1_obj.num} по ГЭСН 1) γ=({self.accepted_density} т/м³)' 
			else:
				text = f'{self.local_name} γ=({self.accepted_density} т/м³)' 
		else:
			if self.gesn_1_obj:
				text = f'{self.note1} ({self.gesn_1_obj.num} по ГЭСН 1) γ=({self.accepted_density} т/м³)' 
			else:
				text = f'{self.note1} γ=({self.accepted_density} т/м³)' 
		return text

	@property
	def _note2(self):
		'''Итоговое примечание №2'''
		none_data = {None, 'None', '-', '', ' '}
		if self.note2 in none_data:
			if self.gesn_5_obj:
				text = f'{self.local_name} ({self.gesn_5_obj.num} по ГЭСН 5) γ=({self.accepted_density} т/м³)' 
			else:
				text = f'{self.local_name} γ=({self.accepted_density} т/м³)' 
		else:
			if self.gesn_5_obj:
				text = f'{self.note2} ({self.gesn_5_obj.num} по ГЭСН 5) γ=({self.accepted_density} т/м³)' 
			else:
				text = f'{self.note2} γ=({self.accepted_density} т/м³)' 
		return text

	# ===================================== Методы =====================================

	def get_density(self, local_density, gesn_density):
		""" Определение плотности грунта по ГЭСН или по ИГИ """		
		deviation = lambda n1, n2: abs(1-n1/n2) # Подфункция для вычисления отклонения двух чисел

		if self.__class__._compare_mode: # режим работы с сопастовлением ИГИ и ГЭСН
			if type(gesn_density) is str: # проверка на наличия диапазона в данных по ГЭСН
				value_list = [] # контейнер для значений диаппазона

				# преобразование в список и т/м³
				gesn_list = gesn_density.split('-')
				for i in range(len(gesn_list)):
					value_list.append(float(gesn_list[i])/1000)
				value_list = sorted(value_list)

				# проверка на нахождения в диапазаное плотности по ГЭСН
				if value_list[0] <= local_density <= value_list[1]:
					res = local_density

				# проверка на отклонение, если плотность по ИГИ ниже дипазона по ГЭСН
				elif local_density < value_list[0]:
					if deviation(local_density,value_list[0]) > 0.05:
						res = local_density
					else:
						res = value_list[0]
				
				# проверка на отклонение, если плотность по ИГИ выше дипазона по ГЭСН
				elif local_density > value_list[1]:
					if deviation(local_density,value_list[1]) > 0.05:
						res = local_density
					else:
						res = value_list[1]
				else:
					print(f"Ошибка! Не удалось посчитать отколение для {local_density} т/м³ и диапазона {gesn_density}  кг/м³")

			# Если плотность по ГЭСН не указана
			elif gesn_density is None:
				res = local_density

			# Если плотность по ГЭСН это одно число
			else:
				gesn_density = gesn_density/1000 # преобразование в т/м³
				if deviation(local_density,gesn_density) > 0.05:
					res = local_density
				else:
					res = gesn_density
		else:
			res = local_density
		return res
	
	def set_local_num(self,local_num):
		self.local_num = local_num

	def set_local_name(self, local_name):
		self.local_name = local_name.strip()

	def set_local_density(self, local_density):
		self.local_density = convert_value(local_density)

	def set_gesn_1_obj(self, gesn_1_obj):
		self.gesn_1_obj = gesn_1_obj

	def set_gesn_4_obj(self, gesn_4_obj):
		self.gesn_4_obj = gesn_4_obj

	def set_gesn_5_obj(self, gesn_5_obj):
		self.gesn_5_obj = gesn_5_obj

	def set_note1(self, note1):
		""" Задать примечания №1 """
		self.note1 = note1

	def set_note2(self, note2):
		""" Задать примечания №2 """
		self.note2 = note2
	
	def set_comment(self, comment):
		""" Задать локальное примечание """
		self.comment = comment
	

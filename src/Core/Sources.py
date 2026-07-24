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

import json
from .Utilities import convert_value
from .DataLib import DataLibraryManager

# Данный модуль организует работу с базой источников проетка, данными о транспортировки до них
# Содержит класс Source_Manager для управления БД и класс Source как основной элемент БД


class Sources_Manager(DataLibraryManager):
	"""
	Управялет процессом создания и настройки библиотеки источников и транспортировки

	Args:
		:project: объект управления проектом
	"""

	FILE = 'Sources' # Файл с данными

	LIB_ALIASES = (
		'ТБО',
		'Металл',
		'КОГ',
		'БазаПод',
		'ПлощСкладГрунт',
		'ПлощСкладДерево',
		'АБЗ',
		'Песок',
		'Гранулят',
		'ВЗиС',
		'ЩПС'
	)
	
	def __init__(self, project):
		super().__init__()
		self.project = project # Единый глобальный объект, хранящий настройки и артубты для всех модулей
		self.library = []
		self.load_lib()
		Source._transportation_mode = self.project.work_modes.get('transportation_mode',False) if self.project else False

	# ---------------------------- Загрузка / Сохранение --------------------------------
	def load_lib(self):
		if self.project:
			try:
				with open(self._file_path, "r", encoding="utf-8") as f:
					data = json.load(f)
					for source in data:
						obj = Source.deserialization(source)
						self.library.append(obj)
			except FileNotFoundError:
				self.library = []
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
				for source in self.library:
					data.append(source.serialization())
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
		self.library = []
		self.load_lib()
		self.unlock()

	# ----------------------------------- Работа с БД -----------------------------------
	def set_work_mode(self):
		Source._transportation_mode = self.project.work_modes.get('transportation_mode',False) if self.project else False
	
	def get_sources_data(self) -> list:
		""" Собирает данные для диалога земляных работ.
		Возвращает список с кортежами внутри которых: Наименование перевозки, Основной псевдоним"""
		sources: dict = self.library
		sources_list = []
		for source in sources:
			source: Source
			sources_list.append((source.name, source.alias))
		return sources_list

	def get_aliases(self) -> list:
		output = []
		current_aliases = []
		for source in self.library:
			source: Source
			current_aliases.append(source._alias)
		for alias in self.LIB_ALIASES:
			if alias not in current_aliases:
				output.append(alias)
		return sorted(output)

	# ---------------------------- Взаимодействии с источниками ----------------------------

	def create_source(self, data):
		"""
		Создаёт объект источник и добавляет в коллекцию 
		
		Args:
			:data: Сводный словарь с данными для объекта, включает в себя:
				name: Полное наименование источника ресурса
				alias: Псевдоним для обращения в среде ВОР
				advanced_coating: Усоверш. тип покрытия
				transitional_coating: Переходный тип покрытия
				ground_coating: Грунтовый тип покрытия
				tonnage: Тоннаж перевозки
				work_text: Описание работы. Предполагается как самовычисляемый атрибут с возможностью переопределеняи
				note: Примечание
				comment: Локальный комментарий

		"""
		if self.project and data:
			name = data.get('name')
			alias = data.get('alias')
			advanced_coating = data.get('advanced_coating', 0)
			transitional_coating = data.get('transitional_coating', 0)
			ground_coating = data.get('ground_coating', 0)
			tonnage = data.get('tonnage', 15)
			transport = data.get('transport', 'автосамосвалами')
			work_text = data.get('work_text')
			note = data.get('note')
			comment = data.get('comment')

			obj = Source(
				name,
				alias,
				advanced_coating, 
				transitional_coating, 
				ground_coating,
				tonnage,
				transport,
				work_text,
				note,
				comment
			)
			self.library.append(obj)
	
	def edit_source(self, index, data):
		""" Редактирует данные объекта-источника"""
		if self.project and data and index in list(range(len(self.library))):
			name = data.get('name')
			alias = data.get('alias')
			advanced_coating = data.get('advanced_coating')
			transitional_coating = data.get('transitional_coating')
			ground_coating = data.get('ground_coating')
			tonnage = data.get('tonnage')
			transport = data.get('transport')
			work_text = data.get('work_text')
			note = data.get('note')
			comment = data.get('comment')

			obj: Source = self.library[index]

			obj.name = name
			obj.alias = alias
			obj.advanced_coating = convert_value(advanced_coating)
			obj.transitional_coating = convert_value(transitional_coating)
			obj.ground_coating = convert_value(ground_coating)
			obj.tonnage = convert_value(tonnage)
			obj.transport = transport
			obj.work_text = work_text
			obj.note = note
			obj.comment = comment

	def move_obj(self, index: int, moving: int):
		"""
		Передвигает объект-источник в списке и возвращает новый индекс
		
		Args:
			:index: Текущий индекс выбранного объекта
			:moving: Направление перемещения элемента в спискею 
				-1 — переместить вверх
				 1  — переместить вниз
		Returns: new_index
		"""
		if self.project:
			if moving == 1 and index == len(self.library)-1:
				return index # Случай перемещения вниз первого элемента игнорируется
			if moving == -1 and index == 0:
				return index # Случай перемещения вверх последнего элемента игнорируется
			
			new_index = index + moving
			obj = self.library.pop(index)
			self.library.insert(new_index, obj)
			return new_index
	
	def remove_sorce(self, index):
		""" Удаляет элемент из списка """
		if self.project:
			del self.library[index]

	def show_sources(self):
		""" Функция для отладки. Выводит информацию о объектах-источников """
		print('БД источников в проекте:')
		for source in self.library:
			print(source)

			

class Source:
	"""
	Описывает источник ресурса и условия транспортировки до него

	Args:
		:name: Полное наименование источника ресурса
		:alias: Псевдоним для обращения в среде ВОР
		:advanced_coating: Усоверш. тип покрытия
		:transitional_coating: Переходный тип покрытия
		:ground_coating: Грунтовый тип покрытия
		:tonnage: Тоннаж перевозки
		:work_text: Описание работы. Предполагается как самовычисляемый атрибут с возможностью переопределеняи
		:note: Примечание
		:comment: Локальный комментарий
	"""

	_transportation_mode = False # Режим подробного вывыда транспортировки

	def __init__(
			self,
			name: str,
			alias: str,
			advanced_coating: int = 0, 
			transitional_coating: int = 0, 
			ground_coating: int = 0,
			tonnage: int | str = 15,
			transport: str = 'автосамосвалами',
			work_text: str | None = None,
			note: str | None = None,
			comment: str | None = None
	):
		self.name = name										# Наименование
		self._alias = alias if alias else 'ВИ.'					# Псевдоним для обращения в среде ВОР
		self.advanced_coating = advanced_coating				# Усоверш. тип покрытия
		self.transitional_coating = transitional_coating		# Переходный тип покрытия
		self.ground_coating = ground_coating					# Грунтовый тип покрытия
		self.tonnage = tonnage									# Тоннаж перевозки (по умолччанию 15)
		self.transport = transport								# Техника, осуществляющая перевозку
		self.work_text = work_text								# Замещение текста работы при необходимости
		self.note = note 										# Примечание
		self.comment = comment 									# Локальный комментарий
	
	@property
	def alias(self):
		if self._alias:
			return f'ВИ.{self._alias}'
		else:
			return 'Отсутствует псевданим'
	
	@alias.setter
	def alias(self, string: str):
		self._alias = string.strip().replace(' ','')
		
	@property
	def alias_work(self):
		return f'{self.alias}.Работа'
	
	@property
	def alias_transportation(self):
		return f'{self.alias}.Перевозка'
	
	@property
	def alias_note(self):
		return f'{self.alias}.Прим'


	@property
	def _total_length(self):	# Общее расстояние
		return self.advanced_coating+self.transitional_coating+self.ground_coating
	
	@property
	def _tonnage(self):
		return self.tonnage if self.tonnage else 15
	@property
	def _work_text(self):
		if self.work_text:
			return self.work_text
		else:
			return f'Транспортировка {self.transport} грузоподъёмностью до {self._tonnage} т'

	
	@property
	def transportation_text(self):
		""" Выводит работу по транспортировке с указанием расстояния и типа покрытия """
		if self._transportation_mode:
			couting_text_list = []
			
			if self.advanced_coating > 0:
				advanced_coating_text =  f'до {self.advanced_coating} км по дорогам с усоврешенствованным покрытием'
				couting_text_list.append(advanced_coating_text)
			if 	self.transitional_coating > 0:
				transitional_coating_text = f'до {self.transitional_coating} км по дорогам с переходным покрытием'
				couting_text_list.append(transitional_coating_text)
			if self.ground_coating > 0:
				ground_coating_text = f'до {self.ground_coating} км по дорогам с грунтовым покрытием'
				couting_text_list.append(ground_coating_text)
			if len(couting_text_list) > 1:
				strat_text = f' на расстояние до {self._total_length} км, в том числе:\n'
				union_text = strat_text + ';\n'.join(couting_text_list)+'.'
			elif len(couting_text_list) == 1:
				union_text = f' на расстояние {couting_text_list[0]}'
			else:
				union_text = ''
			return self._work_text + union_text
		else:
			if self._total_length > 0:
				return f'{self._work_text} на расстояние до {self._total_length} км'
			else:
				return f'{self._work_text}'
		
	def __str__(self):
		return f'{self.name}: {self.transportation_text} {"("+self.note+")" if self.note else ""}'

	# ======================================= Методы =======================================

	def serialization(self):
		"Преобразует объект в словарь для сохранения в JSON"
		data = {
			'name': self.name,
			'alias': self._alias,
			'advanced_coating': self.advanced_coating,
			'transitional_coating': self.transitional_coating,
			'ground_coating': self.ground_coating,
			'tonnage': self.tonnage,
			'transport': self.transport,
			'work_text': self.work_text,
			'note': self.note,
			'comment': self.comment
		}
		return data
	
	@classmethod
	def deserialization(cls, data: dict | None = None):
		""" Преобразует словарь в объект класса"""
		if data:
			obj = cls(
				name = data.get('name'),
				alias = data.get('alias'),
				advanced_coating = data.get('advanced_coating', 0),
				transitional_coating = data.get('transitional_coating', 0),
				ground_coating = data.get('ground_coating', 0),
				tonnage = data.get('tonnage', 15),
				transport = data.get('transport','автосамосвалами'),
				work_text = data.get('work_text'),
				note = data.get('note'),
				comment = data.get('comment')
			)
			return  obj
		
	def set_comment(self, text):
		self.comment = text
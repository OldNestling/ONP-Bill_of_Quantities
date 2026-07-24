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
from .Utilities import clearing_string
from .DataLib import DataLibraryManager

# Данный модуль организует работу с пользовательскими библиотеками данных

class LibManager(DataLibraryManager):
	"""
	Управялет процессом создания и настройки библиотек

	Args:
		:project: объект управления проектом
	"""
			
	FILE = 'UserLibs' 						# Файл с данными	

	def __init__(self, project):
		super().__init__()
		self.project = project				# Единый глобальный объект проекта
		self.libraries: list[Library] = []
		self.load_libs()
	
	# ---------------------------- Загрузка / Сохранение --------------------------------
	def load_libs(self):
		if not self.project or self._file_path is None or self._file_path is None:
			return
		try:
			with open(self._file_path, "r", encoding="utf-8") as f:
				data = json.load(f)
				self.libraries = [Library.deserialization(lib) for lib in data]
		except FileNotFoundError:
			self.libraries = []
		except Exception as e:
			print(f'{"-"*40}\nПроизошла ошибка: {e}')

	def save_libs(self):
		if not self.project or not self.lock_owned:
			return False
		try:
			tmp_path = self._file_path.with_suffix(".tmp")
			with open(tmp_path, 'w', encoding='utf-8') as f:
				data = [lib.serialization() for lib in self.libraries]
				json.dump(data, f, indent=4, ensure_ascii=False)
			tmp_path.replace(self._file_path)
			self.unlock()
			return True
		except Exception as e:
			print(f'{"-"*40}\nПроизошла ошибка: {e}')
			if tmp_path.exists():
				tmp_path.unlink(missing_ok=True)
			return False

	# --------------------------- Взаимодействие с БД -----------------------------------

	def get_libs_list(self) -> list[dict]:
		output = []
		for lib in self.libraries:
			output.append(
				{
					'name': lib.name,
					'alias': lib.alias_key,
					'lib': lib
				}
			)
		return output

	def create_lib(self):
		if not self.project:
			return
		obj = Library()
		self.libraries.append(obj)
	
	def remove_lib(self, index):
		if not  self.project:
			return
		try:
			del self.libraries[index]
		except IndexError:
			return
		
	def create_group(self, lib_idx):
		if not self.project:
			return
		if lib_idx < len(self.libraries):
			lib = self.libraries[lib_idx]
			lib.create_group()

	def move_lib(self, from_index: int, to_index: int) -> bool:
		"""Перемещает библиотеку с from_index на позицию to_index.
		Возвращает True при успехе, иначе False."""
		if not self.project:
			return False
		if 0 <= from_index < len(self.libraries) and 0 <= to_index < len(self.libraries):
			self.libraries.insert(to_index, self.libraries.pop(from_index))
			return True
		return False

	def build_library(self) -> dict:
		dictionary = {}
		for lib in self.libraries:
			lib_content = {}
			for group in lib.groups:
				group_content = {}
				for main_el in group.main_elements:
					main_element = {
						'работа': main_el.work_text,
						'ресурс': main_el.resource_text,
						'расход': main_el.factor,
						'прим1': main_el.note1,
						'прим2': main_el.note2,
					}
					for sub in main_el.sub_elements:
						sub_element = {
							'ресурс': sub.resource_text,
							'расход': sub.factor,
							'прим1': sub.note1,
							'прим2': sub.note2,
						}
						main_element[sub.alias_key.lower()] = sub_element
					group_content[main_el.alias_key.lower()] = main_element
				lib_content[group.alias_key.lower()] = group_content
			dictionary[lib.alias_key.lower()] = lib_content
		return dictionary

	

class Library:
	"""
	Объект библиотеки
	Args:
		:name: Полное наименование группы данных
		:alias: Псевдоним для обращения в среде ВОР
		:description: Описание конструкции
		:elements: Список дочерних объектов
		:comment: Локальный комментарий
	"""
	def __init__(self, name = 'Укажите имя библиотеки', alias = 'Укажите_псевдоним', groups = None):
		self.name: str = name
		self.alias_key: str = alias
		self.groups: list[Group] = groups if groups else []
	
	def __str__(self):
		return f'{self.name} ({self.alias_key})'

	# ---------------------------- Редактирование БД ------------------------------------
	def create_group(self):
		self.groups.append(Group(parent= self))
	
	def remove_group(self, idx):
		try:
			del self.groups[idx]
		except IndexError:
			return
	
	def move_group(self, from_index: int, to_index: int) -> bool:
		"""Перемещает группу внутри списка groups."""
		if 0 <= from_index < len(self.groups) and 0 <= to_index < len(self.groups):
			self.groups.insert(to_index, self.groups.pop(from_index))
			return True
		return False

	# ---------------------------- Загрузка / Сохранение --------------------------------
	def serialization(self) -> dict:
		"Преобразует объект в словарь для сохранения в JSON"
		groups = [group.serialization() for group in self.groups]

		data = {
			'name': self.name,
			'alias': self.alias_key,
			'groups': groups
		}
		return data
	
	@classmethod
	def deserialization(cls, data: dict | None = None):
		if data is None:
			return cls()
		
		obj = cls(
			name = data.get('name', ''),
			alias = data.get('alias', ''),
		)

		raw_groups = data.get('groups', [])

		if raw_groups:
			obj.groups = [Group.deserialization(group, obj) for group in raw_groups]
		
		return obj
	


class Group:
	""" Накопитель сгруппированных элементов """
	def __init__(self, name = 'Новая группа', alias = 'Новый_Псевдоним', main_el = None, parent = None):
		self.name: str = name
		self.alias_key: str = alias
		self.main_elements: list[MainElement] = main_el if main_el else []
		self.parent: Library = parent
	
	@property
	def alias(self):
		""" Возвращает полный путь в библиотеке """
		return f'{self.parent.alias_key}.{self.alias_key}'

	# ---------------------------- Редактирование БД ------------------------------------

	def create_main_element(self, name='', alias='', work_text='', resource_text='',
							factor='', note1='', note2='') -> MainElement:
		"""Создаёт и добавляет новый основной элемент в группу."""
		elem = MainElement(
			name=name, alias=alias, work_text=work_text, resource_text=resource_text,
			factor=factor, note1=note1, note2=note2, parent=self
		)
		self.main_elements.append(elem)
		return elem

	def remove_main_element(self, index: int) -> bool:
		"""Удаляет основной элемент по индексу."""
		if 0 <= index < len(self.main_elements):
			del self.main_elements[index]
			return True
		return False

	def move_main_element(self, from_index: int, to_index: int) -> bool:
		"""Перемещает основной элемент внутри списка works."""
		if 0 <= from_index < len(self.main_elements) and 0 <= to_index < len(self.main_elements):
			self.main_elements.insert(to_index, self.main_elements.pop(from_index))
			return True
		return False
	
	# ---------------------------- Загрузка / Сохранение --------------------------------
	def serialization(self) -> dict:
		"Преобразует объект в словарь для сохранения в JSON"
		raw_main_elements = [me.serialization() for me in self.main_elements]
		data = {
		'name': self.name,
		'alias': self.alias_key,
		'main_elements': raw_main_elements
		}
		return data
	
	@classmethod
	def deserialization(cls, data: dict | None = None, parent: Library = None):
		if data is None:
			return cls(parent = parent)
		
		obj = cls(
			name = data.get('name', ''),
			alias = data.get('alias', ''),
			parent = parent
		)

		raw_works = data.get('main_elements', [])

		if raw_works:
			obj.main_elements = [MainElement.deserialization(work, obj) for work in raw_works]

		return obj
	


class MainElement:
	"""
	Основной объект библиотеки, с работой и 1 материалом
		Args:
		:name: Полное наименование объекта
		:alias: Псевдоним для обращения в среде ВОР
		:work_text: Описание позиции работы
		:resource_text: Описание позиции ресурса
		:factor: Множитель для получения потребного значения материала из исходного значения (объёма, площади) 
		:note1: Примечание 1
		:note2: Примечание 2
	
	"""
	def __init__(
		self,
		name = '',
		alias= '',
		work_text = '',
		resource_text = '',
		factor = '',
		note1 = '',
		note2 = '',
		parent = None,
		sub_el = None
	):
		self.name: str = name					# Наименование позиции
		self.alias_key: str = alias				# Псевдоним позиции
		self.work_text: str = work_text			# Текст позиции работы
		self.resource_text: str = resource_text	# Текст позиции ресурса
		self._factor: str = factor				# Фактор расхода
		self.note1: str = note1					# Примечание 1					
		self.note2: str = note2					# Примечание 2
		self.parent: Group = parent				# Объект-родитель ресурса
		self.sub_elements: list[SubElement] = sub_el if sub_el else []	# Накопитель ресурсов
	
	@property
	def factor(self):
		return self._factor
	
	@factor.setter
	def factor(self, value):
		self._factor = clearing_string(value).replace('\n','')

	# --------------------------------- Псевдонимы --------------------------------------
	@property
	def alias(self):
		""" Возвращает полный путь в библиотеке """
		return f'{self.parent.alias}.{self.alias_key}'
	
	@property
	def alias_work(self):
		return f'{self.alias}.Работа'

	@property
	def alias_resource(self):
		return f'{self.alias}.Ресурс'
	
	@property
	def alias_factor(self):
		return f'{self.alias}.Расход'
	
	@property
	def alias_note1(self):
		return f'{self.alias}.Прим1'
	
	@property
	def alias_note2(self):
		return f'{self.alias}.Прим2'
	
	# ---------------------------- Редактирование БД ------------------------------------

	def create_sub_element(self, name='', alias='', resource_text='',
						factor='', note1='', note2='') -> SubElement:
		"""Создаёт и добавляет новый подчинённый элемент."""
		sub = SubElement(
			name=name, alias=alias, resource_text=resource_text,
			factor=factor, note1=note1, note2=note2, parent=self
		)
		self.sub_elements.append(sub)
		return sub

	def remove_sub_element(self, index: int) -> bool:
		"""Удаляет подчинённый элемент по индексу."""
		if 0 <= index < len(self.sub_elements):
			del self.sub_elements[index]
			return True
		return False

	def move_sub_element(self, from_index: int, to_index: int) -> bool:
		"""Перемещает подчинённый элемент внутри списка resources."""
		if 0 <= from_index < len(self.sub_elements) and 0 <= to_index < len(self.sub_elements):
			self.sub_elements.insert(to_index, self.sub_elements.pop(from_index))
			return True
		return False
	
	# ---------------------------- Загрузка / Сохранение --------------------------------
	def serialization(self) -> dict:
		"Преобразует объект в словарь для сохранения в JSON"
		sub_elements = [res.serialization() for res in self.sub_elements]
		data = {
		'name': self.name,
		'alias': self.alias_key,
		'work_text': self.work_text,
		'resource_text': self.resource_text,
		'factor': self.factor,
		'note1': self.note1,				
		'note2': self.note2,
		'sub_elements': sub_elements
		}
		return data
	
	@classmethod
	def deserialization(cls, data: dict | None = None, parent: MainElement = None):
		if data is None:
			return cls(parent = parent)
		

		obj = cls(
			name = data.get('name', ''),
			alias = data.get('alias', ''),
			work_text = data.get('work_text', ''),
			resource_text = data.get('resource_text', ''),
			factor = data.get('factor', ''),
 			note1 = data.get('note1', ''),
			note2 = data.get('note2', ''),
			parent = parent
		)

		raw_resources = data.get('sub_elements', [])

		if raw_resources:
			obj.sub_elements = [SubElement.deserialization(rs, obj) for rs in raw_resources]

		return obj



class SubElement:
	""" 
	Дочерний элемент, подчинённый основному в библиотеки 
		Args:
		:name: Полное наименование объекта
		:alias: Псевдоним для обращения в среде ВОР
		:resource_text: Описание позиции ресурса
		:factor: Множитель для получения потребного значения материала из исходного значения (объёма, площади) 
		:note1: Примечание 1
		:note2: Примечание 2
	"""
	def __init__(
		self,
		name: str = '',
		alias: str = '',
		resource_text: str = '',
		factor: str = '',
		note1: str = '',
		note2: str = '',
		parent: MainElement = None
	):
		self.name = name					# Наименование позиции
		self.alias_key = alias				# Псевдоним позиции
		self.resource_text = resource_text	# Текст позиции
		self._factor = factor				# Фактор расхода
		self.note1 = note1					# Примечание 1					
		self.note2 = note2					# Примечание 2
		self.parent = parent				# Объект-родитель ресурса

	def __str__(self):
		return f'{self.name}: {self.resource_text}'

	# --------------------------------- Псевдонимы --------------------------------------
	@property
	def factor(self):
		return self._factor
	
	@factor.setter
	def factor(self, value):
		self._factor = clearing_string(value)
	
	@property
	def alias(self):
		""" Возвращает полный путь в библиотеке """
		return f'{self.parent.alias}.{self.alias_key}'
	
	@property
	def alias_resource(self):
		return f'{self.alias}.Ресурс'
	
	@property
	def alias_factor(self):
		return f'{self.alias}.Расход'
	
	@property
	def alias_note1(self):
		return f'{self.alias}.Прим1'
	
	@property
	def alias_note2(self):
		return f'{self.alias}.Прим2'
	
	# ---------------------------- Загрузка / Сохранение --------------------------------
	def serialization(self) -> dict:
		"Преобразует объект в словарь для сохранения в JSON"
		data = {
		'name': self.name,
		'alias': self.alias_key,
		'resource_text': self.resource_text,
		'factor': self.factor,
		'note1': self.note1,				
		'note2': self.note2,
		}
		return data
	
	@classmethod
	def deserialization(cls, data: dict | None = None, parent: MainElement = None):
		if data is None:
			return cls(parent = parent)
		
		obj = cls(
			name = data.get('name', ''),
			alias = data.get('alias', ''),
			resource_text = data.get('resource_text', ''),
			factor = data.get('factor', ''),
 			note1 = data.get('note1', ''),
			note2 = data.get('note2', ''),
			parent = parent
		)
		return obj

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
from .Utilities import fixing_decimals
from .DataLib import DataLibraryManager


# Данный модуль организует работу со средствами механизации в проекте
# Содержит класс Machinery_Manager для управления БД и класс Machine как основной элемент БД


class Machinery_Manager(DataLibraryManager):
	"""
	Управялет процессом создания и настройки машин в проекте

	Args:
		:project: объект управления проектом
	"""

	FILE = 'Machinery' 				# Файл с данными

	def __init__(self, project):
		super().__init__()
		self.project = project
		self.library = []  			#  список всех созданных объектов
		self.MACHINES = (
			'-',
			'Экскаватор', 
			'Бульдозер',
			'Бульдозер-рыхлитель',
			'Грейдер',
			'Грейдер-элеватор',
			'Скрепер',
			'Бурильнокрановая машина',
			'Баровая машина',
			'Буровая установка',
			'Автосамосвал',
			'Бортовая машина',
			'Инструмент'
		)
		self.load_lib()
		if self.library:
			self.library.sort(key= lambda obj: obj.category)
		

	# ----------------------------------- Работа с БД -----------------------------------
	def load_lib(self):
		if self.project:
			try:
				with open(self._file_path, "r", encoding="utf-8") as f:
					data = json.load(f)
					for machine in data:
						obj = Machine.deserialization(machine)
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
				for obj in self.library:
					obj: Machine
					data.append(obj.serialization())
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

	# --------------------------- Взаимодействие с БД -----------------------------------
	def get_machines_data(self)-> dict:
		""" Собирает данные для диалога земляных работ
		Возвращает словарь со списком кортежей внутри которых: наименование механизации, ссылка"""
		machines: dict = self.library
		data = {}
		for m in machines:
			m: Machine
			if m.category not in data:
				data[m.category] = [m]
			else:
				data[m.category].append(m)
		return data
		
	
	# ---------------------------- Взаимодействии с объектами ----------------------------
	def create_object(self):
		"""
		Создаёт объект и добавляет в коллекцию 
		"""
		if self.project:
			obj = Machine()
			self.library.append(obj)
	
	def restore_lib(self, data):
		""" Редактирует данные объекта"""
		if self.project:
			self.library = []
			if len(data) >= 1:
				for dct in data:
					obj = Machine.deserialization(dct)
					self.library.append(obj)

	def move_object(self, index: int, moving: int):
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
	
	def remove_object(self, index):
		""" Удаляет элемент из списка """
		if self.project:
			del self.library[index]
	


	def show_lib(self):
		""" Функция для отладки. Выводит информацию о объектах """
		print('БД материалов в проекте:')
		for object in self.library:
			print(object)

			

class Machine:
	""" класс объекта данных о средстве механизации в строительстве """
	def __init__(self, name = None, alias = None, work = None):
		self._name: str = name if name else ''		# Область механизации для контекста
		self.alias: str = alias if alias else ''	# Псевдоним для ДБ
		self._work: str = work if work else ''		# Текст работы с применением средства механизации
		self.category = '-'
	
	@property
	def alias_work(self):
		if self.alias:
			return f'ВСМ.{self.alias}'
		else:
			return 'псевдоним не указан'
	
	@property
	def name(self):
		return self._name
	
	@name.setter
	def name(self, text: str):
		self._name = text.strip().replace('\n', ' ').replace('  ', ' ')

	
	@property
	def work(self):
		return self._work
	
	@work.setter
	def work(self, text: str):
		fix_text  = text.strip().replace('\n', ' ').replace('  ', ' ')
		self._work = fixing_decimals(fix_text)


	# ===================================== Методы ======================================

	def serialization(self):
		"Преобразует объект в словарь для сохранения в JSON"
		data = {
			'category': self.category,
			'name': self.name,
			'alias': self.alias,
			'work': self.work
		}
		return data
	
	@classmethod
	def deserialization(cls, data: dict | None = None):
		""" Преобразует словарь в объект класса"""
		if data is None:
			return cls()
		obj = cls(
			data.get('name'),
			data.get('alias'),
			data.get('work')
		)
		obj.category = data.get('category', '-')

		return obj
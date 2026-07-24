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

import re, json, copy, math
from pathlib import Path
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from Core.Documentation import Book, Document
from Core.Utilities import clearing_string, get_user_log, get_hash_text, fixing_decimals, fixing_spaces
from abc import ABC
from Core.Soils import Soil
from Core.Computing_Module import eval_functions, get_all_alias_request, get_from_library
from .UserLibs import Group, MainElement, SubElement


class BoQ_manager:
	""" 
	### Менеджер ведомости объемов работ (Bill of Quantities)
	Отвечает за управление открытым разделом работ (по одному менеджеру на каждый открытый файл)
	Раздел представляет собой иерархическую трёхуровневую структуру, с основными рабочими элементами на уровне 2 и 3
	
	#### Args:
		- :project: единый объект с данными, настройками и библиотеками проекта
		- :file: ссылка на открываемый файл
	"""

	def __init__(self, project = None, file = None, read_mode = False):
		self._is_loaded = False
		self.project = project		# единый объект с данными, настройками и библиотеками проекта
		self.position_mode = self.project.work_modes['position_mode'] if project else False
		self.read_mode = read_mode			# Режим чтения
		self.file: Path = file				# Объект для доступа к файлу
		self.is_modified = False			# Маркер изменения данных

		# Атрибуты ведомости
		self.construction_site: str = self.project.project_data.get('ConstructionSite', '') if project else ''
		self.object_name: str = ''			# Наименование раздела ВОР
		self.num: str = ''					# Номер раздела ВОР
		self.local_estimate = ''			# № Локальной сметы
		self.date = ''						# Последняя принятая дата изменения
		# Исполнитель и должность
		self.signatures: dict = {
			'Composer': '',
			'Composer_Position': 'Инженер 3 категории'
		}
		self.verifier: dict | None = None	# Заверитель. Если None, то по глобальному параметру проекта
		self.note = ''						# Пользовательские заметки к разделу ВОР. Взаимодействие через модель фронтэнда
		self.log_list: list = None			# список со словарями с ключами Date, Event, содержащими информацию о изменениях

		self.sections: list[Work] = None	# Накопитель подразделов ВОР. Подразделы содержат позиции, те могут содержать ценообразующие ресурсы 
		self.archive: list = None			# Накопитель исключённых позиций ВОР для удобства сметчика
		self.links: set = None				# Хранит все существующие ссылки на документы для ускоренной работы с ними
		self.load_file(file)
		self._is_loaded = True
	
	@property
	def is_loaded(self):
		return self._is_loaded

	def __str__(self):
		text_1 = f'{self.num}: «{self.object_name}» от {self.date}'
		text_2 = f'[{self.signatures.get("Composer")} | {self.signatures.get("Composer_Position")}]'
		text_3 = 'готово' if self.status else 'не готово'
		return f'{text_1}\n{text_2}\n{text_3}'

	@property
	def status(self) -> bool:
		""" Проверяет и возвращает готовность ведомости """
		sections = self.sections
		if not sections:
			return False
		for section in sections:
			section: Section
			if not section.status:
				return False
		return True
	
	@property
	def reason(self) -> str:
		"""
		Собирает список всех уникальных разделов ПД, используемых в ведомости 
		и возвращает отсортированным в виде строки для QPlaneText
		"""
		if not self.sections:
			return ''
		books = set()
		for link in self.links:
			books.add(str(link.book))
		books = list(books)
		books.sort()
		return ';\n'.join(books)
	
	# ==================================== Методы =======================================

	def cleanup(self, del_project = True):
		"""
		Разрывает циклические ссылки между manager и всеми вложенными объектами.
		Вызывается перед удалением менеджера (например, в BoQ_View.shutdown).
		"""
		# 1. Обнуляем обратные ссылки на manager во всех разделах и их содержимом
		for section in self.sections:
			section.manager = None
			for work in section.works:
				work.manager = None
				for resource in work.resources:
					resource.manager = None
		# 2. Очищаем коллекции, чтобы они не держали объекты
		self.sections.clear()
		self.archive.clear()
		self.links.clear()
		# 3. Сбрасываем ссылку на проект (не обязательно, но для чистоты)
		if del_project:	self.project = None
	
	def set_position_mode(self):
		self.position_mode = self.project.work_modes['position_mode']

	# --------------------------------- Работа с файлом ---------------------------------

	def save_file(self, save_as: str | None = None) -> bool:
		"""Сохраняет данные в файл. Если """
		if not self.project:
			return False
		if not self.is_modified and save_as is None: # Изменений не было -> сохранять не зачем
			return False
		
		old_path = self.file        # запоминаем старый путь
		save_path = self.file		# Пусть сохранения

		if self.read_mode and save_as is None:
			return False			# Нельзя перезаписать файл в режиме чтения
		if save_as:
			save_path =  self.file.parent / f'{save_as}.json'	# новый путь
			self.file = save_path
		data = self.serialization()
		if not data:
			if save_as: self.file = old_path # откатываем путь к файлу
			return False
		try:
			with open(save_path, "w", encoding="utf-8") as f:
				json.dump(data, f, indent=4, ensure_ascii=False)
				print(f'Файл {save_path.name} сохранён')
				self.is_modified = False   # Сбрасываем флаг после успешного сохранения
				return True
		except Exception as e:
			print(f'{"-"*40}\nПроизошла ошибка при сохранении:\n{e}')
			if save_as: self.file = old_path # откатываем путь к файлу
			return False
			

	def load_file(self, file):
		# На всякий случай для избежания ссылки на один пустой объект для разных менеджеров
		self.log_list = list() if self.log_list is None else self.log_list
		self.sections = list() if self.sections is None else self.sections
		self.archive = list() if self.archive is None else self.archive
		self.links = set() if self.links is None else self.links

		with open(file, "r", encoding="utf-8") as f:
			data = json.load(f)
			self.deserialization(data)
		# После воссоздания структуры нужно восстановить множества зависимостей
		self.__clean_init_dependencies()
		#self.restore_addresses_in_collection(self.sections)
		self.calculate_pos_nums()
		self.check_changes()
	
	def reload_file(self):
		""" Для переоткрытия файла без сохранения данных """
		mode = self.read_mode	#TODO
		file = self.file
		self.cleanup(False)

		self.sections = None
		self.archive = None
		self.links = None
		self.load_file(file)


	def serialization(self) -> dict:
		metadata = {
			'ObjectName': self.object_name,
			'Num': self.num,
			'local_estimate': self.local_estimate,
			'Date': self.date,
			'Signatures': {
				'Composer': self.signatures.get('Composer', ''),
				'Composer_Position': self.signatures.get('Composer_Position', '')
			},
			'Verifier': self.verifier,
			'Status_Done': self.status,
			'log_list': self.log_list,	# список со словарями. Должен корректно обработаться сам
			'note': self.note
		}
		if self.sections:
			sections = [section.serialization() for section in self.sections]
		else:
			sections = []
		
		if self.archive:
			obj: Work | Resource
			archive = [obj.serialization() for obj in self.archive]
		else:
			archive = []

		data = {
			'sections': sections,
			'archive': archive
		}

		result = {
			'data_scheme': 1,	# На будущее для валидации устаревшей схемы данных
			'metadata': metadata,
			'data': data
		}
		return result

	def deserialization(self, data: dict | None = None):
		if data is None or self.project is None:
			return
		data_scheme = data.get('data_scheme')	# TODO Валидация данных в будующем при изменении структуры
		metadata = data.get('metadata')
		if metadata:
			self.object_name = metadata.get('ObjectName')
			self.num = metadata.get('Num')
			self.local_estimate = metadata.get('local_estimate')
			self.date = metadata.get('Date', self.project.now.strftime("%d.%m.%Y"))
			sig = metadata.get('Signatures', {})
			self.signatures['Composer'] = sig.get('Composer','')
			self.signatures['Composer_Position'] = sig.get('Composer_Position','')
			self.verifier = metadata.get('Verifier')
			self.note = metadata.get('note', '')
			self.log_list = metadata.get('log_list',[])
		data_content = data.get('data', {})
		raw_sections =  data_content.get('sections')
		raw_archive = data_content.get('archive')
		if raw_sections:
			for i, rs in enumerate(raw_sections):
				self.sections.append(Section.deserialization(data=rs, manager=self, index= i))

		if raw_archive:
			for i, ra in enumerate(raw_archive):
				self.archive.append(Section.deserialization(data=ra, manager=None, index= i))
			self._sort_archive()

	def unlock(self):
		"""	Удаляет файл блокировки	"""
		username = get_user_log('get_name')
		filename: Path = self.file.parent / f'{self.file.stem}__{username}.lock'
		if filename.exists(): filename.unlink()
	

	# --------------------------------- Работа с файлами -----------------------------------

	def get_links_files(self) -> dict:
		""" Возвращает информацию о упомянутой документации в виде данных для xml  """
		if not self.sections or self.project is None:
			return {}
		books_key = set()
		for link in self.links:
			link: Link
			books_key.add(link.book_num)
		
		books_key = list(books_key)
		books_key.sort()

		docs = self.project.documentation_manager.library
		files = dict()
		for i, key in enumerate(books_key, 1):
			book_obj: Book = docs.get(key)
			if book_obj is None:
				continue
			file = {
				'FileID': i,
				'FileName': str(book_obj),
				'FullLink' : Path(book_obj.link) if book_obj.link is not None else None
			}
			files[key] = file

		# TODO Проверка на существование файлов. М.Б. стоит вынести в отдельную функцию
		#if self.project.work_modes.get('packed_files_for_BoQ', False):
		#	for file_data in files.values():
		#		if file
		return files
	
	def set_links_file_id(self, files = None):
		""" Назначает ссылкам на документы параметр file_id во время xml/gge экспорта"""
		files = self.get_links_files() if files is None else files
		for link in self.links:
			link: Link
			id = files[link.book_num].get('FileID')
			link.file_id = id

	# ----------------------- Взаимодействие с объектами структуры -------------------------
		
	def get_object(self, indexes: tuple, is_get_links = False) -> object:
		"""
		Ищет определённую позицию (работу или ресурс) или атрибут ссылок по координатам и возвращает объект
		:indexes: кортеж с позициями (координатами) искомого объекта 
		:is_get_links: режим получения ссылок
		"""
		
		solution = self._check_access_to_obj(indexes)
		if not solution:
			return
		section_index, work_index, resource_index = indexes

		if section_index is not None and work_index is None and resource_index is None:
			return self.sections[section_index]
		elif resource_index is None:
			section: Section = self.sections[section_index]
			work = section.works[work_index]
			return work.links if is_get_links else work
		else:
			section: Section = self.sections[section_index]
			work: Work = section.works[work_index]
			resource = work.resources[resource_index]
			return resource.links if is_get_links else resource
	
	def calculate_pos_nums(self):
		""" Создаёт порядковые номера для позиций """
		if not self.sections:
			return
		pos_num = 1
		for section in self.sections:
			section: Section
			for work in section.works:
				work: Work
				work.num = pos_num
				if self.position_mode:
					for i, resource in enumerate(work.resources, 1):
						resource: Resource
						resource.num = f'{pos_num}.{i}'
				else:
					for resource in work.resources:
						pos_num += 1
						resource: Resource
						resource.num = pos_num
				pos_num += 1
	
	def recalculate_resources_nums(self, work):
		""" Пересчитывает порядковый номер ресурсов"""
		work: Work
		num = work.num
		if self.position_mode:
			for i, resource in enumerate(work.resources, 1):
				resource: Resource
				resource.num = f'{num}.{i}'
		else:
			self.calculate_pos_nums()
	
	def move_obj(self, 	direction: int, indexes: tuple) -> tuple:
		"""
		Передвигает объект в списке и возвращает кортеж новых индексов
		
		### Args:
			- :direction: Направление перемещения элемента в списке 
				 -1 — переместить вверх (в начало списка)
				 1  — переместить вниз (в конец списка)
			- :indexes: кортеж с позициями (координатами) искомого объекта 
		Returns: 
			tuple: (int, int | None, int | None) Результат перемещения для выделения строки
		"""
		def __check_movement(collection: list, element_index: int, direct: int) -> bool:
			""" 
			Проверяет, доступно ли перемещение в списке для выбранного элемента

			### Args:
				- :collection: Список, в котором происходит перемещение
				- :element_index: Индекс перемещаемого элемента
				- :dir: (direction) направление перемещения
			"""
			if not collection:
				return False
			if direct == 1 and element_index == len(collection)-1:
				return False	# Случай перемещения вниз первого элемента игнорируется
			if direct == -1 and element_index == 0:
				return False	# Случай перемещения вверх последнего элемента игнорируется
			return True
		
		def __move_element(collection: list, element_index: int, direct: int) -> int:
			""" 
			Перемещает в списке выбранный элемент

			### Args:
				- :collection: Список, в котором происходит перемещение
				- :element_index: Индекс перемещаемого элемента
				- :dir: (direction) направление перемещения
			"""
			new_index = element_index + direct
			obj = collection.pop(element_index)
			collection.insert(new_index, obj)
			return new_index
		
		solution = self._check_access_to_obj(indexes)
		if not solution:
			return indexes
		
		index_section, index_work, index_resource = indexes
		
		# Перемещение раздела
		if index_work is None and index_resource is None:
			move_solution = __check_movement(self.sections, index_section, direction)
			if not move_solution:
				return indexes
			new_section_index = __move_element(self.sections, index_section, direction)
			start = index_section - 1 if direction < 0 else index_section
			self.restore_addresses_in_collection(self.sections, start)
			self.calculate_pos_nums()
			self.is_modified = True
			return (new_section_index, None, None)
		elif index_resource is None:
			section: Section = self.sections[index_section]
			move_solution = __check_movement(section.works, index_work, direction)
			if not move_solution:
				return indexes
			new_work_index = __move_element(section.works, index_work, direction)
			start = index_work - 1 if direction < 0 else index_work
			self.restore_addresses_in_collection(section, start)
			self.calculate_pos_nums()
			self.is_modified = True
			return (index_section, new_work_index, None)
		else:
			section: Section = self.sections[index_section]
			work: Work = section.works[index_work]
			resources = work.resources
			move_solution = __check_movement(resources, index_resource, direction)
			if not move_solution:
				return indexes
			new_resource_index = __move_element(resources, index_resource, direction)
			start = index_resource - 1 if direction < 0 else index_resource
			work.restore_resources_addresses(start)
			self.recalculate_resources_nums(work)
			self.is_modified = True
			return (index_section, index_work, new_resource_index)
	
	@property
	def data_validation(self):
		""" Проверяет структуру данных на соответствие схеме xml и готовность к экспорту"""
		invalid_quantities = []	# Format addresses
		incorrect_positions = []
		error_link_positions = []
		nonlink_positions = []
		for section in self.sections:
			section: Section
			for work in section.works:
				work: Work
				if not work.quantity or work.quantity in ('#ОШИБКА', '#ПУСТО'):
					invalid_quantities.append(work.format_address)
				if not work.status:
					incorrect_positions.append(work.format_address)
				if not work.links:
					nonlink_positions.append(work.format_address)
				if 'None' in work.planned_links:
					error_link_positions.append(work.format_address)
				for resource in work.resources:
					resource: Resource
					if not resource.quantity or resource.quantity in ('#ОШИБКА', '#ПУСТО'):
						invalid_quantities.append(resource.format_address)
					if not resource.status:
						incorrect_positions.append(resource.format_address)
					if not resource.links:
						nonlink_positions.append(resource.format_address)
					if 'None' in resource.planned_links:
						error_link_positions.append(resource.format_address)
		data = {
			'invalid_quantities': invalid_quantities,
			'incorrect_positions': incorrect_positions,
			'error_link_positions': error_link_positions,
			'nonlink_positions': nonlink_positions
		}
		return data
	
	def check_changes(self):
		""" Проверяет изменение в позициях и сбрасывает статус "осметчено" """
		is_changed = False
		for section in self.sections:
			section: Section
			for work in section.works:
				
				if not work.compare_name(): is_changed = True
				work.qnt_check()
				if not work.compare_comment(): is_changed = True

				for resource in work.resources:
					if resource.compare_name(): is_changed = True
					resource.qnt_check()
					if not resource.compare_comment(): is_changed = True
		if is_changed:
			self.is_modified = True


	# ------------------------------- Зависимости ----------------------------------------
	def __clean_init_dependencies(self):
		""" Воссоздаёт зависимости между позициями. Применять только при пустых множествах """
		for section in self.sections:
			section: Section
			for work in section.works:
				work: Work
				work.add_self_to_dependents()
				for resource in work.resources:
					resource: Resource
					resource.add_self_to_dependents() 

	def restore_dependencies(self):
		""" Перестраивает взаимосвязи между позициями """
		for section in self.sections:
			section: Section
			if not section.works:
				continue
			for work in section.works:
				work: Work
				work.dependents = set()
				if not work.resources:
					continue
				for resource in work.resources:
					resource: Resource
					resource.dependents = set()
		self.__clean_init_dependencies()

	# --------------------------------- Адреса -------------------------------------------

	def restore_addresses_in_collection(
			self, 
			collection: Section | Work | Resource  = None, 
			start: int | None = None
	):
		""" 
		Перестраивает адреса и вызывает корректировку ссылоки у объектов при
		 при изменении порядка в коллекциях
		### Args:
			- :collection: коллекция, в которой произошло изменение иерархии
			- :start: начало изменения в коллекции
		"""
		# Обновление адресов внутри раздела
		if isinstance(collection, Section):
			collection: Section
			if not collection.works:
				return
			collection.restore_addresses(start)
		# Обновление адресов внутри позиции работы
		elif isinstance(collection, Work):
			collection: Work
			collection.restore_resources_addresses(start)
		# обновление адрессов для разделов
		else:
			sections = collection if start is None else collection[start:]
			for section in sections:
				section: Section
				section.restore_addresses()
	


	# ------------------------------------- Создание -------------------------------------

	def add_section(self, index = None) -> bool:
		"""
		Добавляет новый объект типа Section в конец списка или перед определённой разделом
		:index: Выбранная позиция вставки
		"""
		if index is not None and self._check_access_to_obj((index, None, None)):
			self.sections.insert(index, Section(manager=self))
			self.restore_addresses_in_collection(self.sections, index+1)
		else:
			self.sections.append(Section(manager=self))
		self.is_modified = True
		return True
	
	def add_work(self, index_section, index = None) -> bool:
		"""
		Добавляет новый объект типа Work в конец списка объекта Section 
		или перед определённым объектом в коллекции
		### Args:
			- :index_section: выбранный раздел
			- :index: выбранная позиция вставки
		"""
		indexes = (index_section, index, None)
		solution = self._check_access_to_obj(indexes)
		section_solution = self._check_access_to_obj((index_section, None, None))
		if not section_solution:
			return False
		section: Section = self.sections[index_section]
		if not solution and index != len(section.works):
			return False
		if index is None or index == len(section.works):
			new_work = Work(manager=self, address= [index_section, len(section.works), None])
			section.works.append(new_work)
			self.calculate_pos_nums()
			self.is_modified = True
			return True
		else:
			work = Work(manager=self, address= [index_section, index, None])
			section.works.insert(index, work)
			self.restore_addresses_in_collection(section, index+1)
			self.calculate_pos_nums()
			self.is_modified = True
			return True

	def add_resource(
			self, 
			index_section, 
			index_work, 
			index = None
	) -> bool:
		""" Добавляет новый объект типа Resource в конец списка объекта Work 
		или перед определённым объектом в коллекции
		### Args:
			- :index_section: выбранный раздел
			- :index_work:	выбранная позиция работы
			- :index: выбранная позиция вставки
		"""
		indexes = (index_section, index_work, index)
		solution = self._check_access_to_obj(indexes)
		#work_solution = self._check_access_to_obj((index_section, index_work, None))
		#if not solution and not work_solution:
		#	return False
		if index is None:
			section: Section = self.sections[index_section]
			work: Work = section.works[index_work]
			work.resources.append(Resource(self, [index_section, index_work, len(work.resources)]))
			self.recalculate_resources_nums(work)
			self.is_modified = True
			return True
		else:
			section: Section = self.sections[index_section]
			work: Work = section.works[index_work]
			if index == len(work.resources):
				work.resources.append(Resource(self, [index_section, index_work, len(work.resources)]))
			else:
				work.resources.insert(index, Resource(self, [index_section, index_work, index]))
			self.restore_addresses_in_collection(work, index)
			self.recalculate_resources_nums(work)
			self.is_modified = True
			return True

	def add_link(self, indexes: tuple, index = None) -> bool:
		"""
		Добавляет новый объект типа Link в конец списка ссылок объекта PositionLine 
		или перед определённым объектом в коллекции. В том числе и для ресурса
		### Args:
			- :indexes: координаты позиции
			- :index: выбранная позиция вставки
		"""
		solution = self._check_access_to_obj(indexes)
		if not solution:
			return False
		obj: Work | Resource = self.get_object(indexes)
		link = Link(self.project)
		self.links.add(link)
		if index is None:
			obj.links.append(link)
		else:
			obj.links.insert(index, link)
		return True
	
	def convert_work_to_resource(self, indexes: list) -> bool:
		""" Преобразует указанную основную позицю в ресурс для работы выше """
		if indexes[1] == 0:
			return False   # нужна позиция работы над указанной

		s, w, _ = indexes
		section: Section = self.sections[s]
		old_work: Work = section.works[w]
		target_work: Work = section.works[w - 1]

		# 1. Сохраняем данные старой работы и её ресурсов
		old_work_data = old_work.serialization()
		old_resources = old_work.resources[:]   # копия списка
		old_work.resources = []                 # очищаем, чтобы не было побочных эффектов

		# 2. Создаём новый ресурс из данных старой работы
		new_resource = Resource.deserialization(self, old_work_data, [s, w, None])
		# временно не добавляем в систему, чтобы избежать автоматических обновлений адресов

		# 3. Сохраняем старые адреса для маппинга
		old_work_addr = old_work.format_address
		old_res_addrs = [res.format_address for res in old_resources]

		# 4. Определяем новую позицию для вставки
		new_res_index = len(target_work.resources)

		# 5. Добавляем новый ресурс и старые ресурсы в target_work
		target_work.resources.append(new_resource)
		target_work.resources.extend(old_resources)

		# 6. Пересчитываем адреса всех ресурсов, начиная с new_res_index
		self.restore_addresses_in_collection(target_work, new_res_index)

		# 7. Получаем реальные новые адреса после пересчёта
		moved_resources = target_work.resources[new_res_index:]
		actual_new_addrs = [res.format_address for res in moved_resources]

		# 8. Строим маппинг старых адресов на новые
		mapping = {}
		# старая работа -> первый новый ресурс
		mapping.update(zip(
			PositionLine.generate_address_variants(old_work_addr),
			PositionLine.generate_address_variants(actual_new_addrs[0])
		))
		# старые ресурсы -> соответствующие новые адреса
		for old_addr, new_addr in zip(old_res_addrs, actual_new_addrs[1:]):
			mapping.update(zip(
				PositionLine.generate_address_variants(old_addr),
				PositionLine.generate_address_variants(new_addr)
			))

		# 9. Применяем маппинг ко всем перемещённым объектам
		for obj in moved_resources:
			obj.updating_related_addresses(mapping)

		# 10. Удаляем старую работу (она больше не нужна)
		self.remove_obj(indexes)

		# 11. Пересчитываем номера позиций и помечаем изменения
		self.calculate_pos_nums()
		self.is_modified = True
		return True


	def convert_resource_to_work(self, indexes: list) -> bool:
		""" Преобразует указанную позицию ресурса в основную позицю работы ниже """
		obj = self.get_object(indexes)
		if not isinstance(obj, Resource):
			return
		s, w, i = indexes
		data = obj.serialization()
		new_work = Work.deserialization(self, data, [s, w, i])
		new_work.type = 'работа'
		new_work.dependents, obj.dependents = obj.dependents, None
		new_work.init_self_in_system(self)
		new_work.address = [s, w+1, None]

		self.remove_obj((s,w,i))

		self.add_filled_object(new_work)
		self.is_modified = True
		return True


	def add_filled_object(self, obj: PositionLine | Section):
		""" Добавляет новую позицию работы или ресурса, с уже заполненными данными """
		index_section, index_work, index_resource = obj.address
		if isinstance(obj, Section):
			if 0 <= obj.address < len(self.sections):
				self.sections.insert(obj.address, obj)
				obj.init_works_in_system()
				self.restore_addresses_in_collection(None, obj.address+1)
				self.calculate_pos_nums()
			else:
				self.sections.append(obj)
				obj.init_works_in_system()
				self.calculate_pos_nums()
		elif isinstance(obj, Work):
			section: Section =  self.get_object((index_section, None, None))
			if not section:
				return
			if index_work is None or index_work == len(section.works): # Вставка в конец коллекции
				section.works.append(obj)
			else:
				solution = self._check_access_to_obj((index_section, index_work, None))
				if not solution:
					return
				section.works.insert(index_work, obj)
			self.restore_addresses_in_collection(section, index_work)
			self.calculate_pos_nums()
		elif isinstance(obj, Resource):
			work: Work = self.get_object((index_section, index_work, None))
			if not work:
				return
			if index_resource is None or index_resource == len(work.resources):
				work.resources.append(obj)
			else:
				solution = self._check_access_to_obj((index_section, index_work, index_resource))
				if not solution:
					return
				work.resources.insert(index_resource, obj)
			self.restore_addresses_in_collection(work, index_resource)
			self.recalculate_resources_nums(work)
		

	def add_excavation(self, data: dict, indexes: tuple):
		""" 
		Добавляет позиции с разработкой грунта и его перевозкой (опционально) для режима "excavation"
		### Args:
			- :data: Словарь с данными для создания позиций
			- :indexes: текущий адрес для вставки новых данных
		"""
		if not self.project:
			return
		# Новый адрес для позиции
		s, w, _ = indexes
		section: Section = self.sections[s]
		if w is None:
			if section.works:
				work_index = len(section.works)
			else:
				work_index = 0
			new_address = (s, work_index, None)
		else:
			new_address = (s, w+1, None)

		# Получение грунта
		soil_key = data.get('soil_key')

		# Получение ссылки на трудоёмкость для грунта
		laboriousness = data.get('laboriousness', f'@ВГ.{soil_key}.ГЭСН1.0')
		
		# Получение метода разработки
		method = data.get('method')	# Если разработка вручную, то текст, иначе ссылка на механизуцию

		work_text = f'Разработка в выемке грунта @{laboriousness} группы {method}'
		transportation = data.get('transportation', True)
		if transportation:
			work_text = f'{work_text} с погрузкой в автосамосвалы'
		quantity = data.get('quantity')
		comment = f'@ВГ.{soil_key}.Прим1'

		work = Work(self, new_address)
		work.raw_name = f'={work_text}'
		work.unit = 'cubic_meter'
		work.raw_quantity_formula = quantity
		work.raw_comment = f'={comment}'

		if transportation:
			resource = Resource(self, (new_address[0], new_address[1], 0))
			resource.type = 'перевозка'

			resource_alias = data.get('source', True)	# Ссылка по типу ВИ.Ключ
			into_embankment = data.get('into_embankment', False)
			if into_embankment:
				distance = data.get('distance', 0)
				resource_text = f'=@{resource_alias}.Работа на расстояние до {distance} км по дорогам с переходным типом покрытия' 
			else:
				resource_text = f'=@{resource_alias}.Перевозка'

			resource.raw_name = resource_text
			resource.unit = 'ton'
			resource.raw_quantity_formula = f'={work.format_address}*@ВГ.{soil_key}.Y'
			resource.raw_comment = f'=γ= @ВГ.{soil_key}.Y т/м³'
			work.resources.append(resource)
			work.dependents.add(resource)
		
		if section.works:
			section.works.insert(new_address[1], work)
		else:
			section.works.append(work)

		self.restore_addresses_in_collection(section, new_address[1])
		self.calculate_pos_nums()

	def add_drilling_piles(self, data: dict, indexes: tuple):
		""" 
		Добавляет позиции устройства буронабивных свай для режима "drilling_piles"
		### Args:
			- :data: Словарь с данными для создания позиций
			- :indexes: текущий адрес для вставки новых данных
		"""
		if not self.project:
			return
		# Новый адрес для позиции
		s, w, _ = indexes
		section: Section = self.sections[s]
		if w is None:
			if section.works:
				work_index = len(section.works)
			else:
				work_index = 0
			new_address = (s, work_index, None)
		else:
			new_address = (s, w+1, None)
		
		diameter: float = data.get('diametr')
		area = round((math.pi*diameter**2)/4,3)
		lenght = data.get('lenght', 0)

		formula = f'{lenght}*{area}'
		note1 = f'Общая длина — {lenght} м\nПлощадь скважины — {area} м²'
		note2 = f'Общая длина заполнения — {lenght} м\nПлощадь заполнения — {area} м²'
		work_text = data.get('text_mechanization')
		material_text = data.get('concrete', 'Бетон B25 W6')

		drilling_method = data.get('drilling_method', 0)+1
		group = f'Группа{drilling_method}'
		
		soil: Soil = data.get('soil')
		if soil is None or not isinstance(soil, Soil):
			return
		soil_num = soil.local_num

		work_text = f'{work_text} в грунтах @ВГ.{soil_num}.ГЭСН5.{group} группы:'

		other_soils = data.get('other_soils')

		if other_soils:
			soils = []
			soils.append(f'@ВГ.{soil_num}.Прим2')
			for other_soil_num in other_soils:
				other_soil_num: str
				soils.append(f'@ВГ.{other_soil_num}.Прим2')
			work_text = work_text + '\n' + ';\n'.join(soils)
		else:
			work_text = f'{work_text} @ВГ.{soil_num}.Прим2'

		work = Work(self, new_address)
		work.raw_name = f'={work_text}'
		work.unit = 'cubic_meter_soil'
		work.raw_quantity_formula = formula
		work.raw_comment = note1

		resource = Resource(self, (new_address[0], new_address[1], 0))

		resource.raw_name = material_text
		resource.unit = 'cubic_meter_material'
		resource.raw_quantity_formula = formula
		resource.raw_comment = note2
		work.resources.append(resource)
		work.dependents.add(resource)

		self.add_filled_object(work)
		self.is_modified = True

	def add_user_lib_elements(self, data: dict, indexes: tuple):
		"""
		Создаёт позиции для всех элементов выбранной группы из пользовательской библиотеки
		со ссылками на базу данных
		### Args:
			- :data: словарь с целеуказаниями
			- :indexes: индексы (координаты) вставки новых позиций 
		"""
		group: Group = data.get('group')
		main_element: MainElement = data.get('main_element')
		sub_element: SubElement = data.get('sub_element')

		print(f'[DEBUG: SELECTED INDEXES] {indexes=}')
		index_section, index_work, index_resource = indexes
		section: Section = self.sections[index_section]
		if not self._check_access_to_obj((index_section, index_work, None)):
			return
		if sub_element is None:
			new_index_work = len(section.works) if index_work is None else index_work + 1
		else:
			new_index_work = len(section.works) if index_work is None else index_work
		
		# ===== Создание всей группы ===== 
		if main_element is None:
			for main_el in group.main_elements:
				main_el: MainElement
				new_work = Work(self, [index_section, new_index_work, None])
				# вставляем сейчас, чтобы не повредить текстовую ссылку ресурса после смещения позиций
				self.add_filled_object(new_work)	
				new_work.name = f'=@{main_el.alias_work}'
				new_work.raw_quantity_formula = f'0'
				new_work.raw_comment = f'=@{main_el.alias_note1}'

				# ----- Создаем основной ресурс элемента -----
				main_resource = Resource(self, [index_section, new_index_work, 0])  # индекс 0 — первый ресурс
				self.add_filled_object(main_resource)	
				main_resource.name = f'=@{main_el.alias_resource}'
				main_resource.raw_quantity_formula = f'=@{main_el.alias_factor}*{new_work.format_address}'
				main_resource.raw_comment = f'=@{main_el.alias_note2}'
				new_work.dependents.add(main_resource)
				new_work.resources.append(main_resource)			

				# ----- Добавляем дополнительные ресурсы -----
				for i, res in enumerate(main_el.sub_elements, start=1):
					res: SubElement
					new_resource = Resource(self, [index_section, new_index_work, i])
					self.add_filled_object(new_resource)	
					new_resource.name = f'=@{res.alias_resource}'
					new_resource.raw_quantity_formula = f'=@{res.alias_factor}*{new_work.format_address}'
					new_resource.raw_comment = f'=@{res.alias_note2}'
					new_work.dependents.add(new_resource)
					new_work.resources.append(new_resource)
				new_index_work += 1
		
		# -------- Создание основного элемента и потомков ---------
		elif sub_element is None:
			main_el: MainElement = main_element
			new_work = Work(self, [index_section, new_index_work, None])
			self.add_filled_object(new_work)	
			print(f'[DEBUG: NEW OJB INDEXES] indexes={new_work.address}')
			new_work.name = f'=@{main_el.alias_work}'
			new_work.raw_quantity_formula = f'0'
			new_work.raw_comment = f'=@{main_el.alias_note1}'

			# ----- Создаем основной ресурс элемента -----
			main_resource = Resource(self, [index_section, new_index_work, 0])
			main_resource.name = f'=@{main_el.alias_resource}'
			print(f'[DEBUG: NEW OJB LINK] indexes={new_work.format_address}')
			main_resource.raw_quantity_formula = f'=@{main_el.alias_factor}*{new_work.format_address}'
			main_resource.raw_comment = f'=@{main_el.alias_note2}'
			new_work.dependents.add(main_resource)
			new_work.resources.append(main_resource)

			for i, res in enumerate(main_el.sub_elements, start=1):
				res: SubElement
				new_resource = Resource(self, [index_section, new_index_work, i])
				self.add_filled_object(new_resource)
				new_resource.name = f'=@{res.alias_resource}'
				new_resource.raw_quantity_formula = f'=@{res.alias_factor}*{new_work.format_address}'
				new_resource.raw_comment = f'=@{res.alias_note2}'
				new_work.dependents.add(new_resource)
				new_work.resources.append(new_resource)

		# ------ Создание  только ресурса  ------  
		else:
			if index_work is None:
				return
			new_resource = Resource(self, [index_section, new_index_work, index_resource])
			self.add_filled_object(new_resource)
			new_resource.name = f'=@{sub_element.alias_resource}'
			work: Work = self.get_object((index_section, index_work, None))
			new_resource.raw_quantity_formula = f'=@{sub_element.alias_factor}*{work.format_address}'
			new_resource.raw_comment = f'=@{sub_element.alias_note2}'
			work.dependents.add(new_resource)


	# ------------------------------------ Удаление --------------------------------------

	def clear_all(self):
		self.sections.clear()
		self.links = set()
	
	def clear_works(self, index) -> bool:
		if not self.sections:
			return False
		solution = self._check_access_to_obj(tuple(index, None, None))
		if not solution:
			return False
		section: Section = self.sections[index]
		section.prepare_to_works_remove()
		section.works.clear()
		return True
	
	def clear_resources(self, index_section, index_work) -> bool:
		if not self.sections:
			return False
		solution = self._check_access_to_obj(index_section, index_work)
		if not solution:
			return False
		section: Section = self.sections[index_section]
		work: Work = section.works[index_work]
		for resource in work.resources:
			resource: Resource
			resource.prepare_to_remove()
		work.resources.clear()
		return True
	
	def clear_links(self, indexes: tuple) -> bool:
		"""
		Удаляет все объекты-ссылки у указанной позиции
		:indexes: кортеж с координатами объекта
		"""		
		obj: PositionLine = self.get_object(indexes)
		if obj is None:
			return False
		if isinstance(obj, Work) or isinstance(obj, Resource):
			obj.remove_links_from_manager()
			obj.links.clear()

	def remove_obj(self, indexes: tuple, index_link: int | None = None, in_archive = False) -> bool:
		"""
		Удаляет раздел, позицию работы или вложенный в неё ресурс из основного накопителя или из архива

		### Args:
			- :indexes: кортеж с координатами объекта
			- :index_link: Индекс ссылки
		### Returins:
			- :bool: Результат успешности удаления
		"""

		solution = self._check_access_to_obj(indexes, in_archive)

		if not solution:
			return False
		
		index_section, index_work, index_resource = indexes
		# Удаление раздела
		if index_section is not None and index_work is None and index_resource is None:
			sections = self.sections if not in_archive else self.archive
			obj: Section = sections.pop(index_section)
			if not in_archive:
				obj.prepare_to_works_remove()
				self.restore_addresses_in_collection(sections, index_section)
				self.calculate_pos_nums()
			return True
		# Удаление позиции
		elif  index_resource is None and index_link is None:
			sections = self.sections if not in_archive else self.archive
			section: Section = sections[index_section]
			obj: Work = section.works.pop(index_work)
			if not in_archive:
				obj.prepare_to_remove()
				self.restore_addresses_in_collection(section, index_work)
				self.calculate_pos_nums()
			return True
		# Удаление ресурса
		elif index_resource is not None and index_link is None:
			sections = self.sections if not in_archive else self.archive
			section: Section = sections[index_section]
			work: Work = section.works[index_work]
			obj: Resource = work.resources.pop(index_resource)
			if not in_archive:
				obj.prepare_to_remove()
				self.restore_addresses_in_collection(work, index_resource)
				self.recalculate_resources_nums(work)
			return True
		# Удаление ссылки у позиции
		elif index_resource is None and index_link is not None:
			section: Section = self.sections[index_section]
			work: Work = section.works[index_work]
			try:
				obj: Link = work.links.pop(index_link)
				self.links.remove(obj)
			except KeyError:
				pass
			return True
		elif index_link is not None:
			section: Section = self.sections[index_section]
			work: Work = section.works[index_work]
			resource: Resource = work.resources[index_resource]
			try:
				obj: Link = resource.links.pop(index_link)
				self.links.remove(obj)
			except KeyError:
				pass
			return True
		else:
			return False

	def drop_to_archive(self, indexes: tuple) -> bool:
		"""
		Вырезает (не в буфер проекта) выбранные данные (только еденичный объект) 
		и переводит его в архив
		### Args:
			- :indexes: кортеж с данными вырезки: индексы раздела, работы и ресурса, 
			- :is_get_links: дополнительный параметр для вырезания атрибута ссылок
		"""
		solution = self._check_access_to_obj(indexes)

		if not solution:
			return False
		
		obj = copy.deepcopy(self.get_object(indexes))
		
		index_section, index_work, index_resource = indexes

		if isinstance(obj, Section):						# Раздел в архив
			obj.make_static(f'Р{index_section+1}')
			self.archive.append(obj)
		elif isinstance(obj, Work):
			obj.make_static()			# работа
			# необходимо воссоздать фиктивный раздел, в котором была ранее позиция работы
			#  или найти уже существующий в архиве
			real_section: Section = self.sections[index_section]
			check_section = False
			for section in self.archive:
				section: Section
				if section.name == real_section.name:
					check_section = True
					section.works.append(obj)
			if not check_section:
				fictional_section = Section(None, real_section.name)
				fictional_section.format_address_cache = real_section.format_address

				fictional_section.works.append(obj)
				self.archive.append(copy.deepcopy(fictional_section))
		else:
			obj.make_static()			# Ресурс
			real_section: Section = self.sections[index_section]
			real_work: Work = real_section.works[index_work]
			
			check_section = False
			check_work = False

			section_obj = None
			work_obj = None

			for section in self.archive:
				section: Section
				if section.name == real_section.name:
					check_section = True
					section_obj = section
					break
			if check_section:
				for work in section_obj.works:
					work: Work
					if work.name == real_work.name and work.format_address_cache == real_work.format_address:
						check_work = True
						work_obj = work
						break
			if check_section and check_work and work_obj is not None:
				work_obj.resources.append(obj)
			elif check_section and section_obj is not None:
				fictional_work = copy.deepcopy(real_work)
				fictional_work.make_static()
				fictional_work.resources.clear()
				fictional_work.resources.append(obj)

				section_obj.works.append(fictional_work)
			else:
				fictional_work = copy.deepcopy(real_work)
				fictional_work.make_static()
				fictional_work.resources.clear()
				fictional_work.resources.append(obj)

				fictional_section = Section(None, real_section.name)
				fictional_section.format_address_cache = real_section.format_address
				fictional_section.works.append(fictional_work)

				self.archive.append(fictional_section)
		self._sort_archive()
		self.remove_obj(indexes)
		self.is_modified = True
		return True

	def _sort_archive(self):
		"""
		Сортирует элементы архива. Так как их ожидается не много, не должно быть ресурсоёмким
		"""
		section: Section
		self.archive.sort(key= lambda section: section.format_address_cache or section.name or '')
		for section in self.archive:
			section: Section
			section.works.sort(key= lambda work: work.format_address_cache or '')
			for work in section.works:
				work: Work
				work.resources.sort(key= lambda resource: resource.format_address_cache or '')
		for idxs, section in enumerate(self.archive):
			section: Section
			for idxw, work in enumerate(section.works):
				work: Work
				work.address = [idxs, idxw, None]
				for idxr, resource in enumerate(work.resources):
					resource.address = [idxs, idxw, idxr]

	# ---------------------------------- Буфер обмена -----------------------------------

	def copy_obj(self, indexes: tuple, is_get_links = False) -> bool:
		"""
		копирует в буфер обмена проекта выбранные данные (только еденичный объект или его атрибут)
		:indexes: кортеж с данными копирования: индексы раздела, работы и ресурса, 
		:is_get_links: дополнительный параметр для копирования атрибута ссылок
 		"""
		obj = self.get_object(indexes, is_get_links)
		if obj is None:
			return False
		self.project.clipboard = (obj, indexes, type(obj))
		return True

	def cut_obj(self, indexes: tuple, is_get_links = False) -> bool:
		"""
		Вырезает в буфер обмена проекта выбранные данные (только еденичный объект или его атрибут)
		### Args:
			- :indexes: кортеж с данными вырезки: индексы раздела, работы и ресурса, 
			- :is_get_links: дополнительный параметр для вырезания атрибута ссылок
		"""
		solution = self._check_access_to_obj(indexes)

		if not solution:
			return False
		
		obj = None
		old_address = None

		index_section, index_work, index_resource = indexes

		if index_work is None and index_resource is None:
			obj: Section = self.sections.pop(index_section)
			obj.prepare_to_works_remove()
			self.project.clipboard = (obj, indexes, type(obj))
			self.restore_addresses_in_collection(self.sections, index_section)
			self.calculate_pos_nums()
			old_address = indexes
		elif index_resource is None:
			section: Section = self.sections[index_section]
			if is_get_links:
				work: Work = section.works[index_work]
				work.remove_links_from_manager()
				obj = copy.deepcopy(work.links)
				work.links = []
			else:
				obj: Work = section.works.pop(index_work)
				obj.prepare_to_remove()
				self.restore_addresses_in_collection(section, index_work)
				self.calculate_pos_nums()
				old_address = indexes
		else:
			section: Section = self.sections[index_section]
			work: Work = section.works[index_work]
			if is_get_links:
				resource: Resource = work.resources[index_resource]
				resource.remove_links_from_manager()
				obj = copy.deepcopy(resource.links)
				resource.links = []
			else:
				obj: Resource = work.resources.pop(index_resource)
				obj.prepare_to_remove()
				old_address = indexes
				self.restore_addresses_in_collection(work, index_resource)
		self.project.clipboard = (obj, old_address, type(obj))
		self.is_modified = True
		return True
	
	def paste_object(self, indexes: tuple, is_links = False) -> bool:
		"""
		Вставляет из буфера обмена проекта ранее скопированные (вырезанные) данные 
		(только еденичный объект или его атрибут)
		### Args:
			- :indexes: кортеж с данными вставки: индексы раздела, работы и ресурса, 
			- :is_links: дополнительный параметр для вставки атрибута ссылок
		"""
		if not self.project.clipboard:
			return False
		obj, old_addr, obj_type = self.project.clipboard

		index_section, index_work, index_resource = indexes

		# ---------- Вставка ссылок ----------
		if obj_type is list and obj and is_links:
			targ_obj: PositionLine = self.get_object(indexes)
			targ_obj.remove_links_from_manager()
			targ_obj.links = copy.deepcopy(obj)
			targ_obj.add_links_to_manager()
			self.is_modified = True
			return True

		# ---------- Вставка раздела ----------
		elif obj_type is Section:
			old_section_index = old_addr[0]
			new_obj: Section = copy.deepcopy(obj)
			new_obj.manager = self
			if index_section is None:
				new_section_index = len(self.sections)
				self.sections.append(new_obj)
			else:
				new_section_index = index_section + 1
				self.sections.insert(new_section_index, new_obj)

			delta_section = new_section_index - old_section_index
			new_obj.shift_references(delta_section, 0, 0)

			# Обновляем адреса всех разделов, начиная с нового индекса
			self.restore_addresses_in_collection(self.sections, new_section_index)

			new_obj.init_works_in_system(self)
			self.calculate_pos_nums()
			self.is_modified = True
			return True

		# ---------- Вставка работы ----------
		elif obj_type is Work:
			section: Section = self.sections[index_section]
			old_section_index, old_work_index, _ = old_addr
			new_obj: Work = copy.deepcopy(obj)
			if index_work is None:
				new_work_index = len(section.works)
				section.works.append(new_obj)
			else:
				new_work_index = index_work + 1
				section.works.insert(new_work_index, new_obj)

			delta_section = index_section - old_section_index
			delta_work = new_work_index - old_work_index
			new_obj.shift_references(delta_section, delta_work, 0)

			self.restore_addresses_in_collection(section, new_work_index)

			new_obj.clear_dependets()
			new_obj.init_self_in_system(self)
			self.calculate_pos_nums()
			self.is_modified = True
			return True

		# ---------- Вставка ресурса ----------
		elif obj_type is Resource:
			section = self.sections[index_section]
			work: Work = section.works[index_work]
			old_section_index, old_work_index, old_resource_index = old_addr
			new_obj: Resource = copy.deepcopy(obj)
			if index_resource is None:
				new_resource_index = len(work.resources)
				work.resources.append(new_obj)
			else:
				new_resource_index = index_resource + 1
				work.resources.insert(new_resource_index, new_obj)

			delta_section = index_section - old_section_index
			delta_work = index_work - old_work_index
			delta_resource = new_resource_index - old_resource_index
			new_obj.shift_references(delta_section, delta_work, delta_resource)

			self.restore_addresses_in_collection(work, new_resource_index)

			new_obj.init_self_in_system(self)
			self.recalculate_resources_nums(work)
			self.is_modified = True
			return True

		return False

	# -------------------------------- Вспомогательное ------------------------------------


	def _check_access_to_obj(self, indexes: tuple, in_archive = False) -> bool:
		"""
		Проверяет корректность обращения к объекту в основной коллекции или в архиве
		### Args:
			- :index_section: Текущий индекс выбранной секции
			- :index_work: Текущий индекс выбранной позиции
			- :index_resource: Текущий индекс выбранного ресурса
		"""
		sections = self.sections if not in_archive else self.archive
		if not sections:
			return False
		
		index_section, index_work, index_resource = indexes

		if index_section is not None and index_work is None and index_resource is None:
			if not 0 <= index_section < len(sections):
				return False
			return True
		elif index_section is not None and index_work is not None and index_resource is None:
			try:
				section: Section = sections[index_section]
				work: Work = section.works[index_work]
				return True
			except (IndexError, TypeError, AttributeError):
				return False
		elif index_section is not None and index_work is not None and index_resource is not None:
			try:
				section: Section = sections[index_section]
				work: Work = section.works[index_work]
				resource = work.resources[index_resource]
				return True
			except (IndexError, TypeError, AttributeError):
				return False
		else:
			return False
	
	def __reset_links_set(self):
		""" Пересобирает множество с ссылками после массового удаления ссылок """
		self.links.clear()
		if not self.sections:
			return
		for section in self.sections:
			section: Section
			if not section.works:
				continue
			for work in section.works:
				work: PositionLine
				if work.links:
					for link in work.links:
						self.links.add(link)
				if not work.resources:
					continue
				for resource in work.resources:
					resource: PositionLine
					if not resource.links:
						continue
					for link in resource.links:
						self.links.add(link)
	
class Section:
	""" 
	Накопитель позиций ведомости, который в свою очередь находится внутри накопителя менеджера 
	
	### Args:
		- :name: Наименование раздела
		- :content: Содержимое (объекты PositionLine)
	"""
	def __init__(self, manager, name = '', works = None):
		self.format_address_cache = None							# Для перевода объекта в архив
		self.raw_name: str = name										# Наименование раздела
		self.works: list[Work] = works if works is not None else list()	# Позиции раздела
		self.manager: BoQ_manager = manager

	@property
	def status(self) -> bool:
		""" Отслеживает готовность позиций и подпозиций в разделе"""
		for work in self.works:
			work: Work
			if not work.full_status:
				return False
		return True
	
	def __str__(self):
		status = 'готово' if self.status else 'не готово'
		return f'{self.name} - содержит {len(self.works)} позиции(ий), статус: {status}'

	@property
	def name(self):
		if self.manager is None:
			return self.raw_name
		return f'Раздел {self.address+1}. {self.raw_name}'
	
	@name.setter
	def name(self, value):
		self.raw_name = value

	# ---------------------------------- Работа с адресами ----------------------------------
	@property
	def address(self):
		if self.manager is None:
			# Для архивного раздела адрес можно извлечь из format_address_cache
			if self.format_address_cache and self.format_address_cache.startswith('Р'):
				try:
					# format_address_cache вида "Р1" -> 0
					return int(self.format_address_cache[1:]) - 1
				except (ValueError, IndexError):
					pass
			return None
		try:
			return self.manager.sections.index(self)
		except ValueError:
			return None

	@property
	def format_address(self):
		return f'Р{self.address+1}'

	def restore_addresses(self, start = None):
		""" 
		Перестраивает адреса и вызывает корректировку ссылоки у объектов при
		 при изменении порядка раздела в иерархии
		### Args:
			- :start: начало изменения в коллекции
		"""
		if not self.works:
			return
		sec_idx = self.address

		works = self.works if start is None else self.works[start:]
		work_index = 0 if start is None else start
		for work_idx, work in enumerate(works, work_index):
			work: Work
			work.address = (sec_idx, work_idx, None)
			work.restore_resources_addresses()
	
	def shift_references(self, delta_section: int, delta_work: int, delta_resource: int):
		for work in self.works:
			work: Work
			work.shift_references(delta_section, delta_work, delta_resource)

	# ------------------------------- Работа с зависимостями -------------------------------

	def add_works_to_dependents(self):
		for work in self.works:
			work: Work
			work.add_self_to_dependents()

	def remove_works_from_dependents(self):
		for work in self.works:
			work: Work
			work.remove_self_from_dependents()

	# -------------------------------- Работа со ссылками -----------------------------------

	def remove_links_from_manager(self):
		""" Удаляет все ссылки позиции и ресурсов из множества менеджера """
		for work in self.works:
			work: Work
			work.remove_links_from_manager()
			work.remove_resources_links_from_manager()
	
	def add_links_to_manager(self):
		""" Добавляет все имеющиеся ссылки в позициях во множество в менеджере """
		for work in self.works:
			work: Work
			work.add_links_to_manager()
			work.add_resources_links_to_manager()

	# ------------------------------ Комбинированные методы ---------------------------------

	def prepare_to_works_remove(self):
		""" Сбрасывает связи ссылок, адресов и зависимостей """
		# TODO Если по итогу отдельные методы не будут использованы, то их стоит исключить
		for work in self.works:
			work: Work
			work.prepare_to_remove()
	
	def make_static(self, format_address):
		""" Преобразует все позиции в статичные элементы для переноса их в архив """
		self.format_address_cache = format_address
		for work in self.works:
			work: Work
			work.make_static()
	
	
	def init_works_in_system(self, manager):
		""" Устанавливает связи и зависимости для работ и ресурсов после вставки раздела из буфера обмена """
		self.manager = manager
		for work in self.works:
			work: Work
			work.clear_dependets()
		for work in self.works:
			work: Work
			work.init_self_in_system(manager)

	# ------------------------------ Загрузка и сохранение ---------------------------------

	def serialization(self) -> dict:
		""" Преобразует раздел и всё его содержимое в JSON-объект """
		if not self.works:
			data = {
				'format_address_cache': self.format_address_cache,
				'name': self.raw_name,
				'works': []
			}
		ser_works = []
		for work in self.works:
			work: Work
			ser_works.append(work.serialization())
		data = {
			'format_address_cache': self.format_address_cache,
			'name': self.raw_name,
			'works': ser_works
		}
		return data

	@classmethod
	def deserialization(cls, data: dict, manager, index):
		""" Преобразует JSON-объект в объекты проекта (Section, Work, Resource, Link, Style_Manager) """
		if data is None:
			return cls(manager)
		format_address_cache = data.get('format_address_cache')
		name = data.get('name', 'Раздел')
		works_data = data.get('works',[])
	
		if not works_data:
			obj: Section = cls(manager, name, works_data)
			obj.format_address_cache = format_address_cache
			return obj
		
		works_objs = []
		for i, work in enumerate(works_data):
			obj = Work.deserialization(manager, work, [index, i, None])
			obj.format_address_cache = format_address_cache
			works_objs.append(obj)
		return cls(manager, name, works_objs)


class Link:
	"""
	### Объект отвечающий за ссылку на один конкретный документ
	
	#### Args:
		- :project: Объект данных проекта
		- :book_num: Номер раздела ПД
		- :tag: Тег для поиска документа
	"""
	def __init__(self, project):
		self.project = project						# Объект проекта с настройками
		self.book_num: float | int = 0				# Номер раздела ПД
		self.tag: int = 0							# Тег для поиска страницы и документа
		self.user_pages: str | None = None			# Замещение пользователем страницы по тегу
		self.file_id = None 						# Проставляется во время экспорта

	@property
	def book(self):
		""" Возвращает объект тома ПД """
		if self.project is None:
			return None
		documentation: dict = self.project.documentation_manager.library
		key = self.book_num
		if isinstance(key, float) and key.is_integer():
			key = int(key)
		return documentation.get(key, None)

	@property
	def document(self):
		if self.project is None:
			return
		if self.book is None:
			return None
		book: Book = self.book
		return book.content.get(self.tag, None)

	@property
	def pages(self) -> list | int:
		""" Програмно определяемый атрибут страницы документа """
		user_pages: str = self.user_pages
		if user_pages:
			if ',' in user_pages:
				user_pages: list = user_pages.replace(' ','').split(',')
				try:
					return [int(x) for x in user_pages]
				except ValueError:
					return None
			else:
				try:
					return int(user_pages.strip())
				except Exception:
					return None
		else:
			if self.project is None:
				return None
			if self.document is None:
				return None
			return self.document.page

	@property
	def book_link(self) -> Path | None:
		""" Возвращает строку со ссылкой на файл """
		book = self.book
		if book and book.link:
			return Path(book.link)
		else:
			return None

	@property
	def doc_link(self) -> Path | None:
		""" Возвращает строку со ссылкой на файл """
		doc = self.document
		if doc and doc.link:
			return Path(doc.link)
		return None
	
	def __str__(self):
		doc: Document = self.document
		if doc is None:
			doc_code = None
			doc_name = None
		else:
			doc_code = doc.code
			doc_name = doc.name
		pages = self.pages
		if isinstance(pages, list):
			pages = ', '.join(map(lambda p: str(p), pages))
		return f'{doc_code} (Том {self.book_num}) {doc_name}, стр. {pages}'


	def serialization(self):
		data = {
			'book_num': self.book_num,
			'tag': self.tag,
			'user_pages': self.user_pages
		}
		return data

	@classmethod
	def deserialization(cls, data: dict | None = None, project_obj = None,):
		if data is None:
			return None
		link = cls(project_obj)
		link.book_num = data.get('book_num')
		link.tag = data.get('tag')
		link.user_pages = data.get('user_pages')
		return link



@dataclass
class Style_Manager:
	"""	Хранит настройки отображения, переопределённые пользователем для позиции"""
	col_2: dict | None = None			# Индекс 2: Столбец «Наименование работ, ресурсов, затрат по проекту»
	col_5: dict | None = None			# Индекс 5: Столбец «Формула расчета объемов работ и расхода материалов, потребности ресурсов»
	col_6: dict | None = None			# Индекс 6: Столбец «Ссылка на чертежи, спецификации в проектной документации»
	col_7: dict | None = None			# Индекс 7: Столбец «Дополнительная информация (комментарий)»
	col_9: dict | None = None 			# Индекс 9: Столбец «Локальный комментарий»

	def set_background_color(self, col: int, color: str | None):
		self._set_color_attr(col, 'background_color', color)

	def set_text_color(self, col: int, color: str | None):
		self._set_color_attr(col, 'text_color', color)

	def _set_color_attr(self, col: int, key: str, color: str | None):
		columns = {2: 'col_2', 5: 'col_5', 6: 'col_6', 7: 'col_7', 9: 'col_9'}
		if col not in columns:
			return

		# Если цвет None — удаляем ключ из словаря
		if color is None:
			col_dict = getattr(self, columns[col])
			if isinstance(col_dict, dict) and key in col_dict:
				del col_dict[key]
				# Если словарь стал пустым, можно обнулить атрибут
				if not col_dict:
					setattr(self, columns[col], None)
			return

		# Проверяем, что цвет — корректный HEX
		if not isinstance(color, str) or not self._is_HEXA_color(color):
			return

		# Получаем текущий словарь или создаём новый
		col_dict = getattr(self, columns[col])
		if not isinstance(col_dict, dict):
			col_dict = {}
			setattr(self, columns[col], col_dict)
		col_dict[key] = color

	@staticmethod
	def _is_HEXA_color(text: str) -> bool:
		""" Проверяет на соответствие переданной строки палитре HEXA """
		pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$'
		return bool(re.fullmatch(pattern, text))
	
	def select_column(self, num: int):
		columns = {2:self.col_2, 5: self.col_5, 6: self.col_6, 7:self.col_7, 9: self.col_9}
		return columns.get(num, 'None')
	
	def get_column_data(self, num: int) -> tuple:
		""" Возвращает пару ключ-значение для сериализации данных"""
		column = self.select_column(num)
		if column == 'None':
			return
		name = f'col_{num}'
		return (name, column)
		

	def serialization(self):
		data = dict()
		columns = (2, 5, 6, 7, 9)
		for col in columns:
			key, value = self.get_column_data(col)
			data[key] = value
		return data

	def deserialization(self, data):
		if not data:
			return
		self.col_2 = data.get('col_2')
		self.col_5 = data.get('col_5')
		self.col_6 = data.get('col_6')
		self.col_7 = data.get('col_7')
		self.col_9 = data.get('col_9')



class PositionLine(ABC):
	""" Объект позии в ведомости объёмов работ """
	PATTERN = r'(\$?)Р(\d+)\.(\$?)П(\d+)(?:\.(\$?)(\d+))?(_Прим)?'	# паттерн человекочитаемой ссылки на позицию/ресурс (например Р3.П4.1 или $Р3.$П4.1)
	
	# ===================================================================================

	def __init__(self, manager, address = None):
		self.manager: BoQ_manager = manager				# менеджер раздела для получения глобальных данных
		self.style_manager = Style_Manager()			# Управляет данными о пользовательском переопределении представления
		self._address = address	if address is not None else []	# Текущий адрес в иерархии ведомости (section_index, work_inedx, resource index | None)
		self.format_address_cache = None				# Статичный форматированный аддрес для архива 
		self.num: int | str| None = None				# Номер позиции. Определяется менеджером
		self.num_cache = None							# Статичный номер для архивной позиции 
		self.raw_name: str = ''							# Описание позиции (столбец ведомости 3), видимое в редакторе
		self._name_cache = None 						# хеш для определения изменения статуса
		self.raw_unit: str = '-'						# Ключ-строка еденицы измерения (столбец 4)
		self._raw_quantity_formula: str = '0'			# Формула вычисления позиции (столбец 5), видимая в редакторе
		self.quantity_cache = None						# Статичный результат вычисления для архива
		#self.quantity_data: None | list = None			# Для кооректировки статуса "Осметчино" после изменения данных. Вынужденная мера из-за проблем с custom_round
		self.links: list[Link] = []						# Ссылки на обосновывающие документы. Содержит объекты класса Link
		self.links_cache = None							# Статичные данные для архивных позиций
		self._raw_comment: str = ''						# Примечание (столбец 8)
		self._comment_cache = None
		self.local_comment = ''							# Локальный комментарий в среде разработки ведомости
		self.type = 'работа'							# Тип позиции из списка возможных ['работа','материал','перевозка','оборудование', 'машина', 'прочее']
		self.custom_round: int | None = None			# Замещение округления с системного на пользовательское
		self.status_correct = False						# Подтверждено готовым разработчиком
		self.status_calculated = False					# Подтверждено готовым сметчиком
		self.dependents: set[PositionLine] = set()							# Зависимые от этой позиции элементы (требуют пересчёта при изменении объекта)
	

	@property
	def status(self):
		if self.status_correct and self.status_calculated:
			return True
		else:
			return False
	
	def reset_status(self):
		self.status_correct = False
		self.status_calculated = False
		self.manager.is_modified = True


	def make_is_correct(self):
		self.status_correct = True
		self.status_calculated = False
		self.manager.is_modified = True

	def make_is_calculated(self):
		self.quantity_cache = self.quantity
		self.status_correct = True
		self.status_calculated = True
		self.manager.is_modified = True


	# ============================= Методы и атрибуты данных  ===========================

	# ------------------------------- Наименование позиции  -----------------------------

	@property
	def name(self):
		if self.raw_name.startswith('='):
			val = self.process_library_requests(self.raw_name)[1:]
			val = self.get_objects_values(val)
			return eval_functions(val)
		else:
			return self.raw_name
		
	@name.setter
	def name(self, string: str):
		text = fixing_spaces(string.strip())
		if text.endswith('\n'):
			text[:-1]
		text = fixing_decimals(text)
		if not text.startswith('=') and '@' in text:
			text = '=' + text

		self.raw_name = text

		hash = get_hash_text(self.process_library_requests(text))
		if self.status_calculated and self._name_cache != hash:
			self.status_calculated = False
		self._name_cache = hash
	
	def compare_name(self):
		""" Проверяет изменение в наименовании позиции и сбрасывает статус "осметчено" """
		hash_name = get_hash_text(self.name)
		if self._name_cache != hash_name:
			self.status_calculated = False
			self._name_cache = hash_name
			return False
		else: return True

	# -------------------------------- Единицы измерения --------------------------------

	@property
	def unit(self) -> str:
		""" Возвращает лейбл единицы измерения """
		if self.manager is None:
			return self.raw_unit
		project = self.manager.project
		if not project:
			return '-'
		data = project.units.get(self.raw_unit)
		if isinstance(data, dict):
			return data.get('label', self.raw_unit)
		return '-'
	
	@unit.setter
	def unit(self, key):
		self.raw_unit = key
		self.manager.is_modified = True
	
	@property
	def unit_round(self) -> int:
		""" Возвращает параметр округления """
		project = self.manager.project
		if not project:
			return 0
		if self.custom_round is None:
			data = project.units.get(self.raw_unit)
			if isinstance(data, dict):
				return data.get('round', 0)
			else:
				return 0
		else:
			return self.custom_round
		
	# ------------------------------------- Формула -------------------------------------

	@property
	def raw_quantity_formula(self):
		return self._raw_quantity_formula
	
	@raw_quantity_formula.setter
	def raw_quantity_formula(self, formula):
		""" Назначачает новую формулу с контролем зависимостей """
		old_formula = self.raw_quantity_formula
		clr_text = clearing_string(formula)
		self.compare_and_process_relations(old_formula, clr_text, self._raw_comment)
		if not clr_text.startswith('=') and ('@' in clr_text or re.match(self.PATTERN, clr_text)):
			clr_text = '=' + clr_text
		self._raw_quantity_formula = clr_text
		self.qnt_check()


	@property
	def quantity_formula(self) -> str:
		""" Видимая формула позиции с обработанными ссылками на библиотеку проекта и позиции, 
		а также вычисленными результатами внутренних пользовательских формул, которые не должны быть видны """
		raw_formula = self.raw_quantity_formula
		if not raw_formula:
			return None
		if not raw_formula.startswith('='):				# Без внешних данных и обработки
			return raw_formula
		else:
			# получаем данные из библиотеки проекта
			with_alias_data = self.process_library_requests(raw_formula) 	
			# получаем данные из ссылок на позиции
			whith_links_data = self.get_objects_values(with_alias_data)		
			calculated = eval_functions(whith_links_data[1:])
			return calculated
	
	# ---------------------------------- Количество -------------------------------------

	@property
	def quantity(self) -> str:
		""" Вычисляет результат чистой текстовой формулы из quantity_formula, 
		уже не содержащей вспомогательного синтаксиса"""

		def __decimal_round(number, precision=2):
			# Преобразуем число в строку, чтобы Decimal точно его понял
			# Формируем строку для указания точности, например '0.01' для 2 знаков
			quantize_str = '0.' + '0' * precision
			# Выполняем округление с нужным правилом
			return Decimal(str(number)).quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
		
		raw_quantity_formula = self.raw_quantity_formula
		if not raw_quantity_formula:
			return "#ПУСТО"
		try:
			expr = self.quantity_formula
			expr = expr.replace('^', '**') 
			result = eval(expr, {"__builtins__": None})
			round_property = self.unit_round
			#self.compare_qnt(result, round_property)
			rounded_result = __decimal_round(result, round_property)
			calc = f"{rounded_result:.{round_property}f}"
			return calc

		except Exception as e:
			# print(f"Ошибка вычисления формулы: {e}")
			return "#ОШИБКА"

	def compare_qnt(self, res: str | None = None) -> bool:
		""" Сопоставляет изменения с прошлым вычислением и сбрасывает статус status_calculated при необходимости """
		""" 
		TODO Не получается просто сделать сравнение прошлого и нового итогового
		результата, так как при сравнении проскакивают результаты с применением
		custom_round и без него, что приводит к ложномоу сбросу статуса.
		"""
		
		if res is None:
			res = self.quantity

		if not self.quantity_cache:
			self.quantity_cache = res
			self.status_calculated = False
			return False

		if self.status_calculated and res != self.quantity_cache:
			print(f'[DEBUG qnt: {self}] {res=} != {self.quantity_cache=}')
			self.status_calculated = False
			self.quantity_cache = res
			return False
		return True

	def qnt_check(self, res: str | None = None):
		check = self.compare_qnt(res)
		if not check:
			for depend in self.dependents:
				depend.qnt_check()


	# ---------------------------------- Примечание -------------------------------------

	@property
	def raw_comment(self) -> str:
		return self._raw_comment
	
	@raw_comment.setter
	def raw_comment(self, text:str):
		old_text = self._raw_comment
		text = fixing_decimals(text)
		text = fixing_spaces(text).strip()
		if text.endswith('\n'):
			text = text[:-1]
		self.compare_and_process_relations(old_text, text, self._raw_quantity_formula)
		if not text.startswith('=') and '@' in text:
			text = '=' + text
		self._raw_comment = text

		# Проверка на изменения
		text = self.process_library_requests(text)
		text = self.get_objects_values(text)
		text = eval_functions(text)
		hash = get_hash_text(text)
		if self.status_calculated and self._comment_cache != hash:
			self.status_calculated = False
		self._comment_cache = hash
	
	@property
	def comment(self):
		""" Выводит вычисленный результат формулы примечания """
		raw_comment = self.raw_comment 
		if not raw_comment:
			return ''
		if not raw_comment.startswith('='):		# Без внешних данных и обработки
			return raw_comment
		else:
			with_alias_data = self.process_library_requests(raw_comment)	# получаем данные из библиотеки проекта
			whith_links_data = self.get_objects_values(with_alias_data)		# получаем данные из ссылок на позиции
			calculated = eval_functions(whith_links_data[1:])
			return calculated
		
	def compare_comment(self):
		""" Проверяет изменение в комментарии позиции и сбрасывает статус "осметчено" """
		hash_comment = get_hash_text(self.comment)
		if self._comment_cache != hash_comment:
			self.status_calculated = False
			self._comment_cache = hash_comment
			return False
		else: return True

	# ------------------------------- Ссылки на ПД --------------------------------------

	@property
	def planned_links(self):
		""" Выводит строку с абзацами из имеющихся ссылок на документы """
		if not self.links and self.links_cache:
			return self.links_cache
		elif not self.links:
			return ''
		self._safe_sort_links()
		references = []
		for link in self.links:
			references.append(str(link))
		references.sort()
		return f'\n{"—"*12}\n'.join(references)
	
	def _safe_sort_links(self):
		"""Сортирует self.links по book_num (числа перед строками) и tag."""
		def sort_key(link):
			try:
				book_num_key = (0, float(link.book_num))
			except (ValueError, TypeError):
				book_num_key = (1, str(link.book_num))
			return (book_num_key, link.tag)
		self.links.sort(key=sort_key)
	
	# ========================== Методы и атрибуты системы ==============================
	# ------------------------------ Работа с адресами ----------------------------------

	@property
	def format_address(self):
		""" Возвращет человекочитаемый адрес объекта для пользовательских ссылок """
		if not self._address or len(self._address) != 3:
			return
		section_index = self._address[0] + 1
		work_index = self._address[1] + 1
		if self._address[2] is None:
			return f'Р{section_index}.П{work_index}'
		else:
			resource_index = self._address[2] + 1
			return f'Р{section_index}.П{work_index}.{resource_index}'
		
	@property
	def address(self):
		""" Возвращает машиночитаемые индексы адеса """
		return self._address
	
	@address.setter
	def address(self, indexes: list):
		"""
		Задаёт новый адресс и уведомляет зависимые объекты.
		Зависимые - объекты имеющие человекочитаемые ссылки (адреса) на изменяемые объект, которые небходимо пересчитать
		:indexes: новая позициция объекта 
		"""
		if len(indexes) != 3:
			return
		if tuple(self.address) == tuple(indexes): # не было изменений
			return
		
		old_base = self.format_address

		section_id, work_id, resource_id = indexes
		new_base = f'Р{section_id+1}.П{work_id+1}' + (f'.{resource_id+1}' if resource_id is not None else '')

		old_variants = self.generate_address_variants(old_base)
		new_variants = self.generate_address_variants(new_base)
		instruction = dict(zip(old_variants, new_variants))
		if self.dependents:
			for dependent in self.dependents:
				dependent: PositionLine
				dependent.updating_related_addresses(instruction)
		self._address = indexes

	def updating_related_addresses(self, data: dict):
		"""
		Заменяет в _raw_quantity_formula и _raw_comment устаревшие форматированные адреса
		:data: словарь с ключами из старых форматированных адресов и значениями с новыми 
		"""
		if self._raw_quantity_formula:
			self._raw_quantity_formula = self._replace_addresses(self._raw_quantity_formula, data)
		if self._raw_comment:
			self._raw_comment = self._replace_addresses(self._raw_comment, data)

	def _replace_addresses(self, text: str, data: dict) -> str:
		""" Заменяет все устаревшие адреса в строке """
		matches = self.__find_all_addresses(text)
		# Сортируем по убыванию длины
		matches.sort(key=len, reverse=True)
		if not matches:
			return text
		matches.reverse() # для исключения коллизий (например, Р1.П2 и Р1.П20)
		for old_addr in matches:
			new_addr = data.get(old_addr)
			if new_addr:
				text = text.replace(old_addr, new_addr)
		return text
	
	def __find_all_addresses(self, string = None)-> list:
		"""Возвращает список найденных адресов (с $)"""
		pattern = self.__class__.PATTERN
		if string is not None:
			return [m.group(0) for m in re.finditer(pattern, string)]
		else:
			matches = []
			for s in (self._raw_quantity_formula, self._raw_comment):
				if s:
					matches.extend(m.group(0) for m in re.finditer(pattern, s))
			return matches
	
	def __get_indexes_from_addresses(self, input_data=None) -> list:
		"""
		Возвращает список с кортежами координат из пользовательских ссылок
		:input_data: строка с сырым текстом или список уже извлечённых адресов
		"""
		if isinstance(input_data, list):
			addr_list = input_data
		else:
			addr_list = self.__find_all_addresses(input_data) if input_data else []
		pattern = self.__class__.PATTERN
		indexes = []
		for addr in addr_list:
			m = re.fullmatch(pattern, addr)
			if not m:
				continue
			# Группы: 1=$Р,2=Р,3=$П,4=П,5=$рес,6=рес
			sec_num = int(m.group(2)) - 1	  # в коде индексы с 0
			work_num = int(m.group(4)) - 1
			res_num = int(m.group(6)) - 1 if m.group(6) is not None else None
			indexes.append((sec_num, work_num, res_num))
		return indexes

	def shift_references(self, delta_section: int, delta_work: int, delta_resource: int):
		""" 
		Сдвигает все ссылки на позиции внутри raw_quantity_formula и raw_comment
		на заданные дельты (относительное смещение), с учётом символов $ (фиксации).
		"""
		pattern = self.__class__.PATTERN

		def __shift_one_address(addr: str) -> str:
			m = re.fullmatch(pattern, addr)
			if not m:
				return addr

			dollar_sec = m.group(1) or ''
			sec_str = m.group(2)
			dollar_work = m.group(3) or ''
			work_str = m.group(4)
			dollar_res = m.group(5) or ''
			res_str = m.group(6)
			prim = m.group(7) or ''		  # сохраняем суффикс

			new_sec = int(sec_str)
			if not dollar_sec:
				new_sec += delta_section

			new_work = int(work_str)
			if not dollar_work:
				new_work += delta_work

			new_res = None
			if res_str is not None:
				new_res = int(res_str)
				if not dollar_res:
					new_res += delta_resource

			if new_res is None:
				result = f"{dollar_sec}Р{new_sec}.{dollar_work}П{new_work}"
			else:
				result = f"{dollar_sec}Р{new_sec}.{dollar_work}П{new_work}.{dollar_res}{new_res}"
			result += prim				# восстанавливаем суффикс _Прим
			return result
			
		if self._raw_quantity_formula:
			addresses = self.__find_all_addresses(self._raw_quantity_formula)
			data = {addr: __shift_one_address(addr) for addr in addresses}
			self._raw_quantity_formula = self._replace_addresses(self._raw_quantity_formula, data)
		if self._raw_comment:
			addresses = self.__find_all_addresses(self._raw_comment)
			data = {addr: __shift_one_address(addr) for addr in addresses}
			self._raw_comment = self._replace_addresses(self._raw_comment, data)

	@staticmethod
	def generate_address_variants(base_address: str):
		"""
		Генерирует все возможные варианты адреса с опциональными $ перед каждым сегментом.
		base_address: строка вида "Р1.П2" или "Р1.П2.3", а также те же варианты с суффиксом _Прим.
		Возвращает список строк.
		"""
		parts = base_address.split('.')
		variants = ['']
		for i, part in enumerate(parts):
			new_variants = []
			for var in variants:
				# Вариант без $
				new_variants.append(var + ('.' if i > 0 else '') + part)
				# Вариант с $ перед этой частью
				new_variants.append(var + ('.' if i > 0 else '') + '$' + part)
			variants = new_variants
		# Добавляем все те же варианты, но с _Прим
		prim_variants = [v + '_Прим' for v in variants]
		return variants + prim_variants

	# ---------------------------- Работа с зависимостями ---------------------------------

	def remove_self_from_dependents(self):
		""" Удаляет ссылки из множеств на текущий объект. Нужно при удалении текущего объекта """
		if self.manager is None:
			return
		addresses_list = self.__find_all_addresses()
		indexes_list = self.__get_indexes_from_addresses(addresses_list)
		for indexes in indexes_list:
			self._remove_dependency(indexes)
	
	def break_addresses(self):
		""" Ломает пользовательские ссылки на текущий объект у всех зависимых объектов. 
		Нужно при удалении текущего объекта """
		if self.dependents is None:
			return
		old_base = self.format_address
		variants = self.generate_address_variants(old_base)
		instruction = {variant: '#Ссылка!' for variant in variants}
		for obj in self.dependents:
			# Удаляем из формулы и примечания
			obj: PositionLine
			obj.updating_related_addresses(instruction)

	def _remove_dependency(self, indexes: tuple):
		""" Удаляет текущий объект из множества "зависимых" у указанно по координатам (индексам) объекта """
		if self.manager is None:
			return
		obj: PositionLine = self.manager.get_object(indexes)
		if obj is None:
			return
		try:
			obj.dependents.remove(self)
		except Exception as e:
			print(f'Не удалось удалить удалить объект {e}')
	
	def add_self_to_dependents(self):
		""" Добавляет объект во множество "зависимых" у объектов из пользовательских ссылок """
		attributes = (self._raw_quantity_formula, self._raw_comment)
		for attribute in attributes:
			if not attribute:
				continue
			indexes = self.__get_indexes_from_addresses(attribute)
			if not indexes:
				continue
			for coordinate in indexes:
				if not coordinate:
					continue
				obj: PositionLine = self.manager.get_object(coordinate)
				if obj is None:
					continue
				if obj.dependents is None:
					obj.dependents = set()
				obj.dependents.add(self)
	
	def append_to_dependency(self, indexes: tuple):
		""" Добавляет текущий объект ко множеству "зависимых" у указанно по координатам (индексам) объекта """
		obj: PositionLine = self.manager.get_object(indexes)
		if obj is None:
			return
		obj.dependents.add(self)

	def compare_and_process_relations(self, old: str, new: str, non_editable_attribute):
		""" Проверяет, какие зависимости нужно создать, а какие удалить для сеттеров формулы и примечания. 
		### Args:
			- :old: текст с пользовательскими ссылками до редактирования
			- :new: текст с пользовательскими ссылками после редактирования
			- :non_editable_attribute: текстовый параметр, не учавстовавший в редактировании, но имеющий ссылки
		"""
		# Нормализуем адреса: убираем _Прим для сравнения
		def normalize(addr_list):
			return {a.replace('_Прим', '') for a in addr_list}

		old_addresses = normalize(self.__find_all_addresses(old))
		new_addresses = normalize(self.__find_all_addresses(new))
		# Объединяем с неизменяемым атрибутом (второй параметр)
		new_addresses = new_addresses.union(normalize(self.__find_all_addresses(non_editable_attribute)))

		to_delete = old_addresses - new_addresses
		to_append = new_addresses - old_addresses

		if to_delete:
			to_delete = self.__get_indexes_from_addresses(list(to_delete))
			for coord in to_delete:
				self._remove_dependency(coord)
		if to_append:
			to_append = self.__get_indexes_from_addresses(list(to_append))
			for coord in to_append:
				self.append_to_dependency(coord)
	
	# ----------------------------- Работа со ссылками ------------------------------------

	def add_links_to_manager(self):
		""" Добавляет все  ссылки позиции и ресурсов во множество менеджера """
		if self.links:
			for link in self.links:
				self.manager.links.add(link)
	
	def remove_links_from_manager(self):
		""" Удаляет все ссылки позиции и ресурсов из множества менеджера """
		if self.links:
			for link in self.links:
				try:
					self.manager.links.remove(link)
				except (KeyError, AttributeError):
					continue


	# ----------------------------------- Прочее ------------------------------------------
	
	def __str__(self):
		return f'{self.format_address} №{self.num}: {self.name} ({self.quantity}[{self.unit}])'
	
	def prepare_to_remove(self):
		""" Зачищает связи объекта перед его удалением """
		self.break_addresses()
		self.remove_self_from_dependents()
		self.remove_links_from_manager()
		self.manager = None
		self.dependents = None

	def init_self_in_system(self, manager):
		""" Инициирует необходимые связи в системе ВОР """
		self.manager = manager
		self.add_links_to_manager()
		self.add_self_to_dependents()

	
	def make_static(self):
		""" Используется до перемещения объекта в архив, 
		где он становится полностью не зависимым от базы и других позиций """
		self.raw_name = self.name
		self.raw_unit = self.unit				# Преобразуем в статичный лейбл
		self.quantity_cache = self.quantity
		self.raw_quantity_formula = str(self.quantity_formula)
		self.links_cache = self.planned_links
		self.raw_comment = self.comment
		self.format_address_cache = self.format_address
		self.num_cache = self.num

		self.style_manager.col_2 = None
		self.style_manager.col_5 = None
		self.style_manager.col_6 = None
		self.style_manager.col_7 = None
		self.style_manager.col_9 = None
		self.manager = None
		self.dependents = None
		self.links = []

	# ------------------------------- Вычисление данных -----------------------------------
	def process_library_requests(self, text):
		""" Возвращает текст с обработанными запросами к библиотеке """
		library = self.manager.project.library
		if not library:
			return text
		aliases: list = get_all_alias_request(text)
		view_text: str = text
		for alias in aliases:
			alias: str
			value = get_from_library(alias.lower(), library)
			view_text = view_text.replace(alias, str(value))
		return view_text

	def get_objects_values(self, text: str) -> str:
		"""
		Вычисляет значение объектов PositionLine (quantity или comment)
		и заменяет исходные адреса на результаты.
		Суффикс '_Прим' указывает на подстановку comment вместо quantity.
		"""
		lines_addresses = self.__find_all_addresses(text)
		# Сортируем по длине в убывающем порядке
		lines_addresses.sort(key=len, reverse=True)
		new_text = text
		for address in lines_addresses:
			m = re.fullmatch(self.__class__.PATTERN, address)
			if not m:
				continue
			sec_num = int(m.group(2)) - 1
			work_num = int(m.group(4)) - 1
			res_num = int(m.group(6)) - 1 if m.group(6) is not None else None
			is_prim = m.group(7) is not None

			obj: PositionLine = self.manager.get_object((sec_num, work_num, res_num))
			if obj is None:
				continue
			# Выбираем нужный атрибут в зависимости от наличия _Прим
			value = obj.comment if is_prim else obj.quantity
			try:
				new_text = new_text.replace(address, str(value))
			except TypeError:
				new_text = new_text.replace(address, '#ОШИБКА')
		return new_text
		
	# ------------------------------ Загрузка и сохранение ---------------------------------

	def serialization(self) -> dict:
		""" Преобразует объект в словарь для JSON """
		ser_links = []
		for link in (self.links or []):
			ser_links.append(link.serialization())

		data = {
			'format_address_cache': self.format_address_cache,
			'num_cache': self.num_cache,
			'raw_name': self.raw_name,
			'name_cache': self._name_cache,
			'raw_unit': self.raw_unit,
			'raw_quantity_formula': self._raw_quantity_formula,
			'quantity_cache': self.quantity_cache,
			'raw_comment': self._raw_comment,
			'comment_cache': self._comment_cache,
			'local_comment': self.local_comment,
			'type': self.type,
			'custom_round': self.custom_round,
			'style_manager': self.style_manager.serialization(),
			'status_correct': self.status_correct,
			'status_calculated': self.status_calculated,
			'links': ser_links,
			'links_cache': self.links_cache
		}
		return data

	@classmethod
	def deserialization(cls, manager: BoQ_manager, data: dict, address = [None, None, None]) -> Work | Resource:
		obj = cls(manager, address)
		if not data:
			return obj
		
		obj.format_address_cache = data.get('format_address_cache')
		obj.num_cache = data.get('num_cache')
		obj.raw_name = data.get('raw_name', '')
		obj._name_cache = data.get('name_cache')
		obj.raw_unit = data.get('raw_unit', '-')
		obj._raw_quantity_formula = data.get('raw_quantity_formula', '0') 
		obj.quantity_cache = data.get('quantity_cache')
		obj._raw_comment = data.get('raw_comment', '')
		obj._comment_cache = data.get('comment_cache')

		obj.local_comment = data.get('local_comment')
		obj.type = data.get('type')
		obj.custom_round = data.get('custom_round')
		obj.status_correct = data.get('status_correct', False)
		obj.status_calculated = data.get('status_calculated', False)
		
		raw_links = data.get('links')
		links = raw_links if isinstance(raw_links, list) else []
		if links:
			links = [Link.deserialization(obj, manager.project) for obj in links]
			links = [link for link in links if link is not None]
			for link in links:
				manager.links.add(link)

		obj.links = links
		obj.links_cache = data.get('links_cache')

		obj.style_manager.deserialization(data.get('style_manager'))

		return obj




class Work(PositionLine):
	""" Главная позиция (зачастую работа в ВОР). Может содержать ресурсы"""
	def __init__(self, manager: BoQ_manager,  address = [None, None, None], resources = None):
		super().__init__(manager, address)				
		# Список ценообразующих вложенных объектов PositionLine
		self.resources: list[Resource] = resources if resources is not None else []					
		self.type = 'работа'
	
	# ----------------------------- Работа с адресами -----------------------------------

	def restore_resources_addresses(self, start=None):
		""" Пересчитывает адреса ресурсов 
		:start: Начальная позиция пересчёта"""
		sec_idx, work_idx, _ = self.address
		start = 0 if start is None else start
		collection = self.resources if start is None else self.resources[start:]
		for i, resource in enumerate(collection, start):
			resource: Resource
			resource.address = [sec_idx, work_idx, i]

	# ------------------------- Работа с зависимостями ----------------------------------

	def remove_self_from_dependents(self):
		for resource in self.resources:
			resource: Resource
			resource.remove_self_from_dependents()
		return super().remove_self_from_dependents()

	
	def add_self_to_dependents(self):
		for resource in self.resources:
			resource: Resource
			resource.add_self_to_dependents()
		return super().add_self_to_dependents()
	
	def shift_references(self, delta_section, delta_work, delta_resource):
		for resource in self.resources:
			resource: Resource
			resource.shift_references(delta_section, delta_work, delta_resource)
		return super().shift_references(delta_section, delta_work, delta_resource)

	# ---------------------------- Работа со ссылками -----------------------------------

	def add_links_to_manager(self):
		for resource in self.resources:
			resource: Resource
			resource.add_links_to_manager()
		return super().add_links_to_manager()
	
	def remove_links_from_manager(self):
		for resource in self.resources:
			resource: Resource
			resource.remove_links_from_manager()
		return super().remove_links_from_manager()


	# --------------------------------- Прочее ------------------------------------------
	@property
	def full_status(self):
		""" Проверяет себя и ресурсы на общую готовность """
		if not self.status:
			return False
		for resource in self.resources:
			resource: Resource
			if not resource.status:
				return False
		return True

	def prepare_to_remove(self):
		""" Сбрасывает связи у ценообразующих ресурсов, после у себя """
		for resource in self.resources:
			resource: Resource
			resource.prepare_to_remove()
		return super().prepare_to_remove()

	def init_self_in_system(self, manager: BoQ_manager):
		for resource in self.resources:
			resource: Resource
			resource.init_self_in_system(manager)
		return super().init_self_in_system(manager)
	
	def clear_dependets(self):
		# Сброс зависимостей перед тем, как установить связи 
		self.dependents = set()
		for resource in self.resources:
			resource: Resource
			resource.dependents = set()
	
	def make_static(self):
		for resource in self.resources:
			resource: Resource
			resource.make_static()
		return super().make_static()
	
	# --------------------------- Загрузка и сохранение ---------------------------------

	def serialization(self) -> dict:
		""" Преобразует объект в словарь для JSON """
		ser_resources = []
		for resource in self.resources:
			resource: Resource
			ser_resources.append(resource.serialization())

		data = super().serialization()
		data['resources'] = ser_resources
		return data
		
	@classmethod
	def deserialization(cls, manager: BoQ_manager, data: dict, address = [None, None, None]) -> Work:
		work = super().deserialization(manager, data, address)
	
		resources = data.get('resources', [])
		if not resources:
			return work

		resources_objs = []
		section_index, work_index, _ = address
		for i, resource in enumerate(resources):
			indexes = [section_index, work_index, i]
			resource = Resource.deserialization(manager, resource, indexes)
			resources_objs.append(resource)
		work.resources = resources_objs
		return work
	
	
class Resource(PositionLine):
	""" Ценообразующая позиция. Содержится в накопителе класса Work"""
	def __init__(self, manager: BoQ_manager, address = [None, None, None]):
		super().__init__(manager, address)
		self.type = 'материал'
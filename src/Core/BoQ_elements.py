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

import re
from pathlib import Path
from dataclasses import dataclass

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from .BoQ import BoQ_manager 

from Core.Documentation import Book, Document
from Core.Utilities import (
	clearing_string, get_user_log, get_hash_text, fixing_decimals, fixing_spaces, decimal_round
)
from abc import ABC
from Core.Computing_Module import eval_functions, get_all_alias_request, get_from_library


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
		self.dependents: set[PositionLine] = set()		# Зависимые от этой позиции элементы (требуют пересчёта при изменении объекта)
	

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
		
		raw_quantity_formula = self.raw_quantity_formula
		if not raw_quantity_formula:
			return "#ПУСТО"
		try:
			expr = self.quantity_formula
			expr = expr.replace('^', '**') 
			result = eval(expr, {"__builtins__": None})
			round_property = self.unit_round
			#self.compare_qnt(result, round_property)
			rounded_result = decimal_round(result, round_property)
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
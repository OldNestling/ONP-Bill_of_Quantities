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
from math import ceil
from Core.Utilities import convert_value, text_before
from .DataLib import DataLibraryManager


# Данный модуль организует работу с перечнем проектной документации для создания ссылок на неё
# Содержит класс DOCs_Manager для управления БД и класс Book и Document как основной элемент БД


class DOCs_Manager(DataLibraryManager):
	"""
	Управялет процессом создания и настройки библиотеки документов

	Args:
		:project: объект управления проектом
	"""

	FILE = 'Documentation' 			# Файл с данными
	
	def __init__(self, project):
		super().__init__()
		self.project = project
		self.library = {}  			# Словарь всех созданных объектов
		self.load_lib()

	# ---------------------------- Загрузка / Сохранение --------------------------------
	def load_lib(self):
		if self.project:
			try:
				with open(self._file_path, "r", encoding="utf-8") as f:
					data = json.load(f)
					for book in data.values():
						obj = Book.deserialization(book)
						self.library[convert_value(obj.num)]=(obj)
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
			self.restore_library()
			tmp_path = self._file_path.with_suffix(".tmp")
			with open(tmp_path, 'w', encoding='utf-8') as f:
				data = {}
				for num, book in self.library.items():
					data[str(num)] = book.serialization()
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
		self.library = {}
		self.load_lib()
		self.unlock()
				
	# -------------------------------- Взаимодействии с БД ------------------------------
	def restore_library(self):
		new_lib = {}
		books = list(self.library.values())

		books.sort(key = Book.sort_key)
		for book in books:
			new_lib[book.num] = book
		self.library = new_lib

	def add_book(self):
		if not self.project:
			return
		code = self.project.code if self.project.code else 'Шифр'
		BOOK_TYPE = {1:'ПЗ', 2:'ППО', 3:'ТКР', 4:'ИЛО', 5:'ПОС', 6:'ООС', 7:'ПБ', 8:'ТБЭ'}
		BOOK_NAME = {
			1: 'Раздел 1. Пояснительная записка',
			2: 'Раздел 2. Проект полосы отвода',
			3: 'Раздел 3. Технологические и конструктивные решения линейного объекта. Искусственные сооружения',
			4: 'Раздел 4. Здания, строения и сооружения, входящие в инфраструктуру линейного объекта', 
			5: 'Раздел 5. Проект организации строительства',
			6: 'Раздел 6. Мероприятия по охране окружающей среды',
			7: 'Раздел 7. Мероприятия по обеспечению пожарной безопасности',
			8: 'Раздел 8. Требования к обеспечению безопасной эксплуатации линейного объекта'
		}
		if not self.library:
			self.library[1] = Book(1,f'{code}-ПЗ', 'Раздел 1. Пояснительная записка')
		else:
			# Собираем все ключи, которые можно преобразовать в число
			numeric_keys = []
			for key in self.library.keys():
				try:
					numeric_keys.append(float(key))
				except (ValueError, TypeError):
					# Игнорируем строковые ключи, которые не являются числами
					pass
			if numeric_keys:
				highest = max(numeric_keys)
				next_num = int(ceil(highest)) + 1
			else:
				# Если нет ни одного числового ключа, начинаем с 1
				next_num = 1
			typ = BOOK_TYPE.get(next_num,'')
			name = BOOK_NAME.get(next_num,'Новый раздел')
			self.library[next_num] = Book(next_num, f'{code}-{typ}', name)

	def remove_book(self, num):
		if self.project:
			del self.library[num]

	def sort_books(self):
		""" Сбрасывает существующие ключи, заново их присваивает, сортирует по порядку """
		if not self.library:
			return
		new_lib = {}
		books = list(self.library.values())

		books.sort(key=Book.sort_key)
		for book in books:
			book.sort_content()
			new_lib[book.num] = book
		self.library = new_lib

class Book:
	""" Представляет собой один том, с документами внутри """

	IN_BOOK_CODES= ['С', 'СП', 'ПЗ', 'В', 'Ч', 'СО','ТРИ', 'ВИ']

	def __init__(self, num, code = '', name = '', content = None):
		self.num: int | float | str = num # str на случай добавления изыскательских томов. Был опыт
		# TODO добавление строкового типа данных привело ко множеству ошибок в (BoQ.py, work_tab_sidebar,
		#  documentation_tab связанных с сортировкой), которые я уставший залатал на скорую руку. 
		# 	Нужно унифицировать и связать с этим модулем
		self.code: str = code
		self.name: str = name
		self.content: dict = content if content is not None else {}
		self.link: str | None = None

	@property
	def current_tag(self):
		"""
		Возвращает новое уникальное значение для ключей содержимого. 
		Нужно для привязки ссылки к простому ключу с возможностью изменения содержимого ключа в последствии,
		без повреждения существующих ссылок 
		"""
		if self.content:
			nums = list(self.content.keys())
			map(lambda x: convert_value(x), nums)
			highest_value = max(nums)
			return highest_value+1
		else:
			return 1

	@property
	def full_name(self):
		return f'{self.code} {self.name}'
	
	def __str__(self):
		""" Для вставки в ячейки ВОР """
		return f'{self.code} {self.name}'


	def set_link(self, path):
		self.link = path
	
	def add_document(self, row):
		new_tag = self.current_tag
		data = {
			'tag': new_tag,
			'code': f'{self.code}-',
			'name': '',
			'page': 0
		}
		documents = {}
		new_items = [(new_tag, Document.deserialization(data))]
		
		items = list(self.content.items())
		prefix = items[:row]
		suffix = items[row:]
		merged = prefix + new_items + suffix
		self.content = dict(merged)
		
	
	def remove_document(self, key):
		del self.content[key]

	def sort_content(self):
		""" Сортирует содержимое тома по порядку документации """
		sorted_content: dict = dict(sorted(self.content.items(), key = lambda item: item[1].page))
		self.content = sorted_content
	
	def resetting_tags(self):
		""" Сбрасывает существующие теги и заново присваивает """
		if self.content:
			new_content = {}
			self.sort_content()
			new_tag = 1
			for doc in self.content.values():
				doc.tag = new_tag
				new_content[new_tag] = doc
				new_tag += 1

	def fill_by_template(self, template: tuple, start = None):
		"""
		Создаёт заготовки для документов по указанному шаблону
		
		Args:
			:template: коллекция кортежей, где первый элемент - тип документа, второй - количество документов данного типа
			:start: начальный индекс для всавки документов в промежуток
		"""
		new_tag = self.current_tag
		documents = {}
		for temp in template:
			code, count = temp
			for i in range(count):
				num = f'0{i+1}' if len(str(i+1)) == 1 else i+1
				data = {
					'tag': new_tag,
					'code': f'{self.code}-{code}{num}',
					'name': '',
					'page': 0
				}
				documents[new_tag] = Document.deserialization(data)
				new_tag += 1

		if start is None:
			self.content.update(documents)
		else:
			items = list(self.content.items())
			prefix = items[:start]
			suffix = items[start:]
			new_items  = list(documents.items())
			merged = prefix + new_items + suffix
			self.content = dict(merged)

	def fill_from_files(self, files: list, start = None):
		""" Добавляет в том документы на основе файлов """
		#TODO Доработь в будущем систему паттернов
		new_tag = self.current_tag
		documents = {}
		for file in files:
			try:
				parts = file[0].split('_')
				if len(parts) != 3:
					raise FileNameFormatError(f"Некорректный формат имени файла: {file[0]}")
				page, typ, name = parts
				if '-' in page:
					page = text_before(page,'-')
				page_int = int(page)
			except ValueError as e:
				raise FileNameFormatError(f"Некорректное значение страницы в файле {file[0]}: {e}")
			except Exception as e:
				raise FileNameFormatError(f"Ошибка при разборе файла {file[0]}: {e}")
			data = {
					'tag': new_tag,
					'code': f'{self.code}-{typ}',
					'name': name,
					'page': page_int
				}
			doc = Document.deserialization(data)
			doc.link = file[1]
			documents[new_tag] = doc
			new_tag += 1  # <- добавлено увеличение тега
			
		if start == len(self.content):
			self.content.update(documents)
		else:
			items = list(self.content.items())
			prefix = items[:start]
			suffix = items[start:]
			new_items  = list(documents.items())
			merged = prefix + new_items + suffix
			self.content = dict(merged)

	def include(self, page: int):
		"""
		Находит соответствующий документ в томе по странице
		:page: Искомая страница документа. Может находиться в интервале известных страниц
		"""
		if not self.content:
			return None
		
		# Создаём словарь с ключами-страницами из словаря с ключами тэгами
		docs = list(self.content.values())
		docs.sort(key= lambda obj: obj.page)
		dct = {}
		for doc in docs:
			dct[doc.page] = doc
		if page in dct:
			return dct.get(page)
		if docs[0] > page:
			return None
		if docs[-1] < page:
			return dct.get(docs[-1])
		i = 0
		while not docs[i] < page < docs[i+1]:
			i += 1
		return dct.get(docs[i])

	@staticmethod
	def sort_key(book):
		try:
			return (0, float(book.num))
		except (ValueError, TypeError):
			return (1, str(book.num))
	
	# ------------------------------------- Работа с БД ------------------------------------
	
	@classmethod
	def deserialization(cls, data: dict | None = None):
		if data:
			obj = cls(
				num = data.get('num'),
				code = data.get('code'),
				name = data.get('name'),
				content = {}
			)
			obj.link = data.get('link')
			content = data.get('content')
			if content:
				for raw_doc in content.values():
					doc = Document.deserialization(raw_doc)
					obj.content[doc.tag] = doc
			return obj
	
	def serialization(self):
		content = {}
		if self.content:
			for tag, doc in self.content.items():
				content[tag] = doc.serialization()
		data = {
			'num': self.num,
			'code': self.code,
			'name': self.name,
			'content': content,
			'link': self.link
		}
		return data


class Document:
	""" Представляет собой один документ в томе """
	def __init__(self, tag, code = '', name = '', page = 0):
		self.tag: int = tag			# Уникальный тег. Соответствует ключу в томе
		self.code: str = code		# Шифр
		self.name: str = name		# Наименование
		self.page: int = page		# Страница в томе
		self.link = None			# Ссылка на файл. Опционально, реализация не в приоритете

	@property
	def full_name(self):
		return f'{self.code} {self.name}'
	
	@property
	def formated_page(self):
		text_page = str(self.page)
		numb_count = len(text_page)
		if numb_count == 1:
			return f'00{text_page}'
		elif numb_count == 2:
			return f'0{text_page}'
		elif numb_count == 3:
			return text_page
		else:
			return 'Страница некорректна'
	
	# ======================================= Методы =======================================

	@classmethod
	def deserialization(cls, data: dict | None = None):
		if data:
			obj = cls(
				tag = data.get('tag'),
				code = data.get('code', ''),
				name = data.get('name', ''),
				page = data.get('page', 0)
			)
			obj.link = data.get('link')

			return obj
	
	def serialization(self):
		data = {
			'tag': self.tag,
			'code': self.code,
			'name': self.name,
			'page': self.page,
			'link': self.link
		}

		return data
	
class FileNameFormatError(Exception):
	pass
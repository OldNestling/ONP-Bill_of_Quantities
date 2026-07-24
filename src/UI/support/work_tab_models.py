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

from PyQt6.QtCore import Qt, QAbstractItemModel, QModelIndex
from Core.BoQ import BoQ_manager, Section, Work, Resource


class Model(QAbstractItemModel):
	"""
	Кастомная модель для отображения иерархической структуры Ведомости объёмов работ:
	- Корневые элементы: разделы (Section)
	- Дочерние элементы: позиции работы (Work)
	- Субдочерние элементы: позиции ресурсов (Resource)
	"""
	HEADERS = (
		'Адрес' ,																			# 0
		'№\nп/п' ,																			# 1
		'Наименование работ,\nресурсов,\nзатрат по проекту' ,								# 2
		'Ед.\nизм.' ,																		# 3
		'Объем работ/\nКоличество' ,														# 4
		'Формула расчета\nобъемов работ\nи расхода материалов,\nпотребности ресурсов' ,		# 5
		'Ссылка на чертежи,\nспецификации в\nпроектной документации' ,						# 6
		'Дополнительная\nинформация\n(комментарий)',										# 7
		'Тип\nпозиции',																		# 8
		'Локальный\nкомментарий'															# 9
	)

	COL_ADDRESS = 0
	COL_NUM = 1
	COL_NAME = 2
	COL_UNIT = 3
	COL_QUANITY = 4
	COL_FORMULA = 5
	COL_LINKS = 6
	COL_COMMENT = 7
	COL_TYPE = 8
	COL_LOCAL_COMMENT = 9

	def __init__(self, manager: BoQ_manager, parent = None):
		super().__init__(parent)
		self.manager = manager
	
	# ========== Обязательные методы QAbstractItemModel ==========

	def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
		"""Количество детей у родительского индекса"""
		if self.manager is None:
			return 0
		if not parent.isValid():
			# Корневой уровень: количество разделов
			return len(self.manager.sections)
		else:
			obj = parent.internalPointer()
			if isinstance(obj, Section):		# Узел-раздел: количество основных позиций работы
				return len(obj.works)
			elif isinstance(obj, Work):			# Узел-позиция: количество ценообразующих ресурсов
				return len(obj.resources)
			else:
				return 0
	
	def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
		return len(self.HEADERS)
	
	def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
		"""Создаёт индекс для элемента по строке, столбцу и родителю"""
		if not self.manager:
			return QModelIndex()
		if not parent.isValid():
			# Корневой уровень: раздел
			sections = self.manager.sections
			if row < len(sections):
				section = sections[row]
				return self.createIndex(row, column, section)
		else:
			parent_item: Work = parent.internalPointer()
			# Уровень основных позиций: родитель – раздел
			if isinstance(parent_item, Section):
				works = parent_item.works
				if row < len(works):
					work = works[row]
					return self.createIndex(row, column, work)
			# Уровень ценообразующих позиций: родитель – работа
			elif isinstance(parent_item, Work):
				resources = parent_item.resources
				if row < len(resources):
					resource = resources[row]
					return self.createIndex(row, column, resource)
		return QModelIndex()
	
	def parent(self, index: QModelIndex) -> QModelIndex:
		"""Возвращает индекс родителя для данного индекса"""
		if not index.isValid():
			return QModelIndex()
		item = index.internalPointer()
		if item is None or isinstance(item, Section): 
			return QModelIndex()
		if isinstance(item, Work):	# Работа: нужно найти раздел, к которому он принадлежит
			for section in self.manager.sections:
				if item in section.works:
					# возвращаем индекс
					row = self.manager.sections.index(section)
					return self.createIndex(row, 0, section)
			return QModelIndex()
		if isinstance(item, Resource):
			for section in self.manager.sections:
				for work in section.works:
					if item in work.resources:
						row = section.works.index(work)
						return self.createIndex(row, 0, work)
			return QModelIndex()
		return QModelIndex()
		
	def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
		"""Возвращает данные для указанной роли"""
		if not index.isValid():
			return None
		item = index.internalPointer()
		if item is None: 
			return None
		col = index.column()
		if role == Qt.ItemDataRole.DisplayRole:
			if isinstance(item, Section):
				if col == self.COL_ADDRESS:
					return item.format_address
				elif col == self.COL_NUM:
					return ''
				elif col == self.COL_NAME:
					return item.name
				else: # Столбцы с 3 по 9 пусты для раздела
					return ''
			elif isinstance(item, (Work, Resource)):
				if col == self.COL_ADDRESS: return item.format_address
				elif col == self.COL_NUM: return item.num
				elif col == self.COL_NAME: return item.name
				elif col == self.COL_UNIT: return item.unit
				elif col == self.COL_QUANITY: return item.quantity
				elif col == self.COL_FORMULA: return item.quantity_formula
				elif col == self.COL_LINKS: return item.planned_links
				elif col == self.COL_COMMENT: return item.comment
				elif col == self.COL_TYPE: return item.type
				elif col == self.COL_LOCAL_COMMENT: return item.local_comment
		elif role == Qt.ItemDataRole.EditRole:
			if isinstance(item, Section):
				if col == self.COL_NAME: return item.raw_name
				else: return ''
			elif isinstance(item, (Work, Resource)):
				if col == self.COL_NAME: return item.raw_name 
				elif col == self.COL_UNIT: return item.raw_unit		
				elif col == self.COL_QUANITY: return item.raw_quantity_formula
				elif col == self.COL_FORMULA: return item.raw_quantity_formula
				elif col == self.COL_COMMENT: return item.raw_comment
				elif col == self.COL_TYPE: return item.type
				elif col == self.COL_LOCAL_COMMENT: return item.local_comment
		elif role == Qt.ItemDataRole.TextAlignmentRole:
			if col in (self.COL_ADDRESS, self.COL_NUM, self.COL_UNIT, self.COL_QUANITY, self.COL_FORMULA):
				return Qt.AlignmentFlag.AlignCenter
			return None
		return None
	
	def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
		"""Обновляет данные в менеджере и возвращает True, если успешно"""
		if not index.isValid() or role != Qt.ItemDataRole.EditRole:
			return False
		item = index.internalPointer()
		col = index.column()
		old_value = self.data(index, role)

		if value == old_value:
			return False
		try:
			if isinstance(item, Section):
				if col == self.COL_NAME: item.name = value
				else: return False
			elif isinstance(item, (Work, Resource)):
				if col == self.COL_NAME: item.name = value
				elif col == self.COL_UNIT: item.raw_unit = value
				elif col == self.COL_FORMULA: item.raw_quantity_formula = value
				elif col == self.COL_COMMENT: item.raw_comment = value 
				elif col == self.COL_TYPE: item.type = value
				elif col == self.COL_LOCAL_COMMENT: item.local_comment = value
				else: return False
			else:
				return False
			# Уведомляем представление об изменении данных
			self.manager.is_modified = True
			self.dataChanged.emit(index, index, [role])

			#if col in (self.COL_FORMULA, self.COL_UNIT):
			#	self.layoutChanged.emit()

			return True
		except Exception as e:
			print(f'Ошибка обновления данных ведомости: {e}')
			return False

	def flags(self, index: QModelIndex) -> Qt.ItemFlag:
		"""Определяет флаги элемента: можно ли редактировать, выбирать и т.д."""
		if not index.isValid():
			return Qt.ItemFlag.NoItemFlags
		base_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
		item = index.internalPointer()
		if item is None: 
			return None
		col = index.column()
		if isinstance(item, Section):
			# Разделы: редактируется только наименование
			if col == self.COL_NAME:
				base_flags |= Qt.ItemFlag.ItemIsEditable
		elif isinstance(item, (Work, Resource)):
			# Позиции: редактируем всё, кроме адреса, номера, quanity (генерируется автоматически)
			# и ссылок - редактируются только во внешнем виджете.
			if col not in (self.COL_ADDRESS, self.COL_NUM, self.COL_QUANITY, self.COL_LINKS):
				base_flags |= Qt.ItemFlag.ItemIsEditable
		return base_flags
	
	def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
		"""Возвращает заголовки столбцов"""
		if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
			if section <  len(self.HEADERS):
				return self.HEADERS[section]
		elif role == Qt.ItemDataRole.TextAlignmentRole:
			return Qt.AlignmentFlag.AlignCenter
		return None
	
	def deleteLater(self):
		"""Переопределяем, чтобы разорвать связи до удаления"""
		self.manager = None
		super().deleteLater()



class ArchiveModel(Model):
	"""
	Модель для отображения архива (статичных объектов без связей).
	Данные берутся из manager.archive.
	Редактирование запрещено (кроме операций удаления/восстановления через отдельные методы).
	"""
	def __init__(self, manager: BoQ_manager, parent=None):
		# Вызываем конструктор родителя, но переопределяем источник данных
		super().__init__(manager, parent)
		self.is_archive = True

	def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
		"""Количество детей у родительского индекса — из архива."""
		if self.manager is None:
			return 0
		if not parent.isValid():
			return len(self.manager.archive)
		else:
			obj = parent.internalPointer()
			if isinstance(obj, Section):
				return len(obj.works)
			elif isinstance(obj, Work):
				return len(obj.resources)
			else:
				return 0

	def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
		"""Создаёт индекс из архива."""
		if not self.manager:
			return QModelIndex()
		if not parent.isValid():
			sections = self.manager.archive
			if row < len(sections):
				section = sections[row]
				return self.createIndex(row, column, section)
		else:
			parent_item = parent.internalPointer()
			if isinstance(parent_item, Section):
				works = parent_item.works
				if row < len(works):
					work = works[row]
					return self.createIndex(row, column, work)
			elif isinstance(parent_item, Work):
				resources = parent_item.resources
				if row < len(resources):
					resource = resources[row]
					return self.createIndex(row, column, resource)
		return QModelIndex()

	def parent(self, index: QModelIndex) -> QModelIndex:
		"""Родительский индекс для архива."""
		if not index.isValid():
			return QModelIndex()
		item = index.internalPointer()
		if item is None or isinstance(item, Section):
			return QModelIndex()
		if isinstance(item, Work):
			# Ищем раздел, содержащий эту работу
			for section in self.manager.archive:
				if item in section.works:
					row = self.manager.archive.index(section)
					return self.createIndex(row, 0, section)
			return QModelIndex()
		if isinstance(item, Resource):
			for section in self.manager.archive:
				for work in section.works:
					if item in work.resources:
						row = section.works.index(work)
						return self.createIndex(row, 0, work)
			return QModelIndex()
		return QModelIndex()

	def flags(self, index: QModelIndex) -> Qt.ItemFlag:
		"""Архивные данные только для чтения (выделение и копирование разрешены)."""
		if not index.isValid():
			return Qt.ItemFlag.NoItemFlags
		base_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
		# Редактирование запрещено всегда
		return base_flags

	def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
		"""Запрещаем редактирование архива."""
		return False

	def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
		"""Отображение данных из архива (статические кэшированные значения)."""
		if not index.isValid():
			return None
		item = index.internalPointer()
		if item is None:
			return None
		col = index.column()
		if role == Qt.ItemDataRole.DisplayRole:
			# Для архивных объектов используем сохранённые кэшированные значения
			if isinstance(item, Section):
				if col == self.COL_ADDRESS:
					return item.format_address_cache or ''
				elif col == self.COL_NAME:
					return item.name
				else:
					return ''
			elif isinstance(item, Work):
				if col == self.COL_ADDRESS:
					return item.format_address_cache or item.format_address
				elif col == self.COL_NUM:
					return item.num_cache or ''
				elif col == self.COL_NAME:
					return item.name
				elif col == self.COL_UNIT:
					return item.unit  # unit уже возвращает метку
				elif col == self.COL_QUANITY:
					return item.quantity_cache or ''
				elif col == self.COL_FORMULA:
					return item.quantity_formula  # формула может быть вычислена, но для архива она статична
				elif col == self.COL_LINKS:
					return item.links_cache or ''
				elif col == self.COL_COMMENT:
					return item.comment
				elif col == self.COL_TYPE:
					return item.type
				elif col == self.COL_LOCAL_COMMENT:
					return item.local_comment
			elif isinstance(item, Resource):
				# аналогично
				if col == self.COL_ADDRESS:
					return item.format_address_cache or ''
				elif col == self.COL_NUM:
					return item.num_cache or ''
				elif col == self.COL_NAME:
					return item.name
				elif col == self.COL_UNIT:
					return item.unit
				elif col == self.COL_QUANITY:
					return item.quantity_cache or ''
				elif col == self.COL_FORMULA:
					return item.quantity_formula
				elif col == self.COL_LINKS:
					return item.links_cache or ''
				elif col == self.COL_COMMENT:
					return item.comment
				elif col == self.COL_TYPE:
					return item.type
				elif col == self.COL_LOCAL_COMMENT:
					return item.local_comment
		elif role == Qt.ItemDataRole.TextAlignmentRole:
			if col in (self.COL_ADDRESS, self.COL_NUM, self.COL_UNIT, self.COL_QUANITY, self.COL_FORMULA):
				return Qt.AlignmentFlag.AlignCenter
			return None
		return None

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

from PyQt6.QtWidgets import (
	QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton, QTextEdit, QTableWidget,
	QMenu, QMessageBox, QDialog, QLineEdit, QStyle, QItemDelegate, QAbstractItemView, QFrame,
	QTreeView, QHeaderView, QFileDialog
)
from PyQt6.QtCore import Qt, QSize, QAbstractItemModel, QModelIndex, QUrl
from PyQt6.QtGui import QColor, QTextDocument, QIntValidator, QTextOption, QDesktopServices
from Core.Documentation import DOCs_Manager, Document, Book
from ..ui_utilities import (
	WordWrapDelegate, IntDelegate, create_ok_cancel_buttons, Requestion, create_separator
)
from ..icons import Icons
from Core.Utilities import convert_value
from pathlib import Path

class Documentation_Tab(QWidget):
	"""Вкладка управления документацией проекта."""
	def __init__(self, project):
		super().__init__()
		self.project = project
		self.manager: DOCs_Manager = self.project.documentation_manager if project else None
		self.setup_ui()
		self.update_ui()
	
	def setup_ui(self):
		self.main_layout = QHBoxLayout(self)

		# ---------------------------------- Дерево ---------------------------------------

		self.tree_view = QTreeView()
		self.model = DocumentationModel(manager=self.manager, parent= self)
		self.tree_view.setModel(self.model)
		
		# Настройка заголовков
		header = self.tree_view.header()
		font = header.font()
		font.setBold(True)
		header.setFont(font)
		header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

		# Настройка ширины столбцов
		fixed_columns = {0: 150, 1: 200, 3: 100, 4: 200}
		stretch_columns = [2]
		header = self.tree_view.header()
		for col, width in fixed_columns.items():
			self.tree_view.setColumnWidth(col, width)
			header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
		for col in stretch_columns:
			header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
		header.resizeSections()
		

		header.sectionResized.connect(self.on_section_resized)
		self.tree_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		self.tree_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
		# Устанавливаем делегат
		delegate = DocumentationDelegate(
			self.tree_view,
			centered_columns=[self.model.COL_TAG, self.model.COL_PAGE],
			page_column=self.model.COL_PAGE
			) 
		self.tree_view.setItemDelegate(delegate)
		self.tree_view.setWordWrap(True)
		self.tree_view.setUniformRowHeights(False)

		self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.tree_view.customContextMenuRequested.connect(self.show_context_menu)

		self.tree_view.setStyleSheet("""
			QTreeView {
				outline: none;					  /* убираем пунктирную рамку фокуса */
			}
			QTreeView::item {
				border-bottom: 1px solid #d0d0d0;   /* горизонтальные линии */
				border-right: 1px solid #d0d0d0;	/* вертикальные линии */
			}
			QTreeView::item:first {
				border-top: 1px solid #d0d0d0;	  /* верхняя граница для первого элемента */
			}
			QTreeView::item:last {
				border-bottom: 1px solid #d0d0d0;   /* нижняя граница для последнего */
			}
		""")

		self.tree_view.expandAll()
		self.main_layout.addWidget(self.tree_view)

		# -------------------------------- Кнопки -----------------------------------------

		buttons_layout = QVBoxLayout()
		buttons_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

		self.btn_edit_lib = QPushButton('Редактировать\nбиблиотеку')
		self.btn_edit_lib.setIcon(Icons.unlock)
		self.btn_edit_lib.clicked.connect(self.toggle_edit_mode)

		self.btn_add_book = QPushButton("Добавить том")
		self.btn_add_book.clicked.connect(self.add_book)
		self.btn_add_doc = QPushButton("Добавить документ")
		self.btn_add_doc.clicked.connect(self.add_document)
		self.btn_fill_from_files = QPushButton("Заполнить из файлов")
		self.btn_fill_from_files.clicked.connect(self.fill_from_files)
		self.btn_fill_template = QPushButton("Заполнить по шаблону")
		self.btn_fill_template.clicked.connect(self.fill_by_template)
		self.btn_remove_doc = QPushButton("Удалить")
		self.btn_remove_doc.clicked.connect(self.remove)
		self.btn_save = QPushButton("Сохранить")
		self.btn_save.clicked.connect(self.save_documentation)
		self.btn_reload = QPushButton("Перезагрузить")
		self.btn_reload.clicked.connect(self.reload_documentation)
		self.btn_sort = QPushButton("Сортировать")
		self.btn_sort.clicked.connect(self.sort_lib)
		self.btn_reset_tags = QPushButton("Сбросить теги")
		self.btn_reset_tags.clicked.connect(self.reset_tags)

		buttons_layout.addWidget(QLabel('Статус:'))
		self.status_label  = QLabel('Чтение')
		buttons_layout.addWidget(self.status_label)
		buttons_layout.addWidget(self.btn_edit_lib)

		buttons_layout.addWidget(create_separator())	# ---

		buttons_layout.addWidget(self.btn_add_book)
		buttons_layout.addWidget(self.btn_add_doc)
		buttons_layout.addWidget(self.btn_fill_from_files)
		buttons_layout.addWidget(self.btn_fill_template)
		buttons_layout.addWidget(self.btn_remove_doc)
		buttons_layout.addWidget(self.btn_save)
		buttons_layout.addWidget(self.btn_reload)
		buttons_layout.addWidget(self.btn_sort)
		buttons_layout.addWidget(self.btn_reset_tags)

		self.main_layout.addLayout(buttons_layout)

		# Изначально отключаем кнопки манипуляции
		self.set_manipulation_buttons_enabled(False)

	def set_manipulation_buttons_enabled(self, enabled):
		"""Включает/отключает кнопки добавления/удаления/перемещения."""
		
		for btn in (self.btn_add_book, self.btn_add_doc, self.btn_fill_from_files, 
			  self.btn_fill_template, self.btn_remove_doc, self.btn_save, self.btn_sort,
			  self.btn_reset_tags):
			btn.setEnabled(enabled)
		self.btn_edit_lib.setEnabled(not enabled)
		self.btn_edit_lib.setIcon(Icons.unlock if enabled else Icons.lock)

	def update_status(self):
		""" Обновляет статус доступности """
		if not self.project:
			return
		data = self.manager.lock_owner
		if data is None:
			self.status_label.setText('Чтение')
		elif self.manager.lock_owned:
			self.status_label.setText('Редактирование')
		elif isinstance(data, dict):
			user = data.get('user', 'неизвестен')
			self.status_label.setText(f'Занято пользователем\n{user}')

	def toggle_edit_mode(self):
		"""Включает режим редактирования (блокировка)."""
		if not self.manager:
			return
		data = self.manager.lock_owner
		if data:
			user = data.get('user', 'неизвестно') if isinstance(data, dict) else 'неизвестно'
			QMessageBox.warning(self, 'Редактирование',
									f'Пользовательские библиотеки заблокированы пользователем {user}')
			self.update_ui()
			return
		lock_res = self.manager.lock_libs()
		self.update_status()
		if lock_res:
			if self.model is not None:
				self.model.togle_acces(True)
			self.set_manipulation_buttons_enabled(True)
		else:
			if self.model is not None:
				self.model.togle_acces(False)
			self.set_manipulation_buttons_enabled(False)
			QMessageBox.warning(self, 'Редактирование',
									'Не удалось заблокировать файл для других пользователей')
			
	def update_ui(self):
		if self.manager:
			self.tree_view.expandAll()
			self.update_status()

	def set_project(self, project):
		self.project = project
		self.manager = self.project.documentation_manager if project else None
		self.model.set_manager(self.manager)
		self.update_ui()

	def on_section_resized(self, logical_index, old_size, new_size):
		self.tree_view.scheduleDelayedItemsLayout()
		self.tree_view.viewport().update()

	def show_context_menu(self, pos):
		index = self.tree_view.indexAt(pos)
		if not index.isValid():
			return
		# Проверяем, что это столбец ссылок и ячейка редактируема
		if index.column() == self.model.COL_LINK and (index.flags() & Qt.ItemFlag.ItemIsEditable):
			menu = QMenu()
			action_select = menu.addAction("Выбрать файл...")
			action_open = None
			link = index.data(Qt.ItemDataRole.DisplayRole)
			if link and isinstance(link, str) and link.strip():
				action_open = menu.addAction("Открыть файл")
			chosen = menu.exec(self.tree_view.viewport().mapToGlobal(pos))
			if chosen == action_select:
				file_path, _ = QFileDialog.getOpenFileName(
					self,
					"Выберите файл",
					"",
					"Все файлы (*.*)"
				)
				if file_path:
					self.model.setData(index, file_path, Qt.ItemDataRole.EditRole)
			elif chosen == action_open:
				if not Path(link).is_file():
					QMessageBox.warning(self, 'Внимание', 'Ссылка не корректа')
					return
				QDesktopServices.openUrl(QUrl.fromLocalFile(link))

	# ----------------------------- Обработка кнопок ------------------------------------

	def add_book(self):
		if not self.manager:
			return
		self.model.add_book()
		self.tree_view.scheduleDelayedItemsLayout()

	def add_document(self):
		if not self.manager:
			return
		index = self.tree_view.currentIndex()
		if not index.isValid():
			QMessageBox.warning(self, "Добавление документа", "Выберите том, в который хотите добавить документ.")
			return
		# Проверяем, что выбрано. Если документ, то вставка осуществится после него
		if index.parent().isValid():
			parent_index = index.parent()
			self.model.add_document(parent_index, index)
		else:
			self.model.add_document(index)
			self.tree_view.expand(index)
		self.tree_view.scheduleDelayedItemsLayout()
			
	def remove(self):
		if not self.manager:
			return
		
		# Получаем все выделенные индексы (ячейки)
		selected_indexes = self.tree_view.selectionModel().selectedIndexes()
		if not selected_indexes:
			return
		# Собираем уникальные строки (индексы для столбца 0, чтобы получить элементы)
		rows = set()
		for idx in selected_indexes:
			# Получаем индекс для первого столбца этой же строки
			row_idx = self.model.index(idx.row(), 0, idx.parent())
			rows.add(row_idx)
		rows = list(rows)

		# Собираем выбранные элементы: (индекс, тип)
		items_to_delete = []
		for idx in rows:
			if idx.parent().isValid():
				items_to_delete.append((idx, 'doc'))
			else:
				items_to_delete.append((idx, 'book'))

		# Проверяем, есть ли тома среди выбранных
		books = [t for t in items_to_delete if t[1] == 'book']
		docs = [t for t in items_to_delete if t[1] == 'doc']

		if books:
			reply = Requestion.ask(
				self,
				'Удаление томов',
				f'Вы действительно хотите удалить {len(books)} том(ов)?\n'
				'Все документы внутри будут удалены.\n'
				'Это может повредить ссылки в ВОР.',
				with_cancel = False
			)
			if reply != QMessageBox.StandardButton.Yes:
				return
		if docs and not books:
			reply = Requestion.ask(
				self,
				'Удаление документов',
				f'ы действительно хотите удалить {len(docs)} документ(ов)?\n'
				'Это может повредить ссылки в ВОР.',
				with_cancel = False
			)
			if reply != QMessageBox.StandardButton.Yes:
				return
		
		# Сортируем для удаления с конца
		# Тома: сортируем по убыванию строки
		books_sorted = sorted(books, key=lambda x: x[0].row(), reverse=True)
		# Документы: сортируем по (родительская строка, собственная строка) по убыванию
		docs_sorted = sorted(docs, key=lambda x: (x[0].parent().row(), x[0].row()), reverse=True)

		# Удаляем документы
		for idx, typ in docs_sorted:
			parent_idx = idx.parent()
			if parent_idx.isValid():
				self.model.remove_document(parent_idx, idx.row())
		
		# Удаляем тома
		for idx, typ in books_sorted:
			self.model.remove_book(idx.row())
		
		self.tree_view.scheduleDelayedItemsLayout()


	def fill_from_files(self):
		""" Заполняет том документами на основе файлов """
		if not self.manager:
			return
		"""Открывает диалог выбора файла и обновляет список листов."""
		files_path, _ = QFileDialog.getOpenFileNames(
			self, "Выберите файлы", "",
			"Документы (*.txt *.doc *.docx *.xlsx *.xlsm *pdf);;Чертежи (*.dwg *.dfx);;Все файлы (*.*)",
			"Все файлы (*.*)"
		)
		files = []
		if files_path:
			files = [(Path(x).stem, x) for x in files_path]
		if not files:
			print('Файлы не определены')
			return
		for file in files:
			if file[0].count('_') != 2:
				QMessageBox.information(self,'Ошибка', 'Наименование файлов не соответсвует паттерну:\n###(###-###)_###_Наименование')
				return
		index = self.tree_view.currentIndex()
		if not index.isValid():
			QMessageBox.warning(self, "Заполнение из файлов", "Выберите том или позицию документа, куда будут добавлены документы.")
			return
		# Проверяем, что выбрано. Если документ, то вставка осуществится после него
		parent_index = None
		if index.parent().isValid():
			parent_index = index.parent()
		self.model.fill_book_from_files(parent_index, index, files)
		self.tree_view.scheduleDelayedItemsLayout()


	def fill_by_template(self):
		if not self.manager:
			return
		index = self.tree_view.currentIndex()
		if not index.isValid():
			QMessageBox.warning(self, "Создание шаблона", "Выберите том, в который хотите добавить документы.")
			return
		dialog = Template_Dialog(self)
		if dialog.exec() == QDialog.DialogCode.Accepted:
			data = dialog.get_data()
		else:
			return

		# Проверяем, что выбрано. Если документ, то вставка осуществится после него
		parent_index = None
		if index.parent().isValid():
			parent_index = index.parent()
			self.model.fill_book_by_template(parent_index, index, data)
		else:
			self.model.fill_book_by_template(index, None, data)
		
		self.tree_view.scheduleDelayedItemsLayout()

	
	def save_documentation(self):
		if not self.manager:
			return
		res = self.model.save_lib()
		if not res:
			QMessageBox.warning(self, 'Сохранение',
									f'Не удалось сохранить данные')
		self.set_manipulation_buttons_enabled(False)
		self.model.togle_acces(False)
		self.update_ui()
	
	def reload_documentation(self):
		if not self.manager:
			return
		self.model.reload_documentation()
		self.set_manipulation_buttons_enabled(False)
		self.model.togle_acces(False)
		self.update_ui()
	
	def sort_lib(self):
		""" Сбрасывает все ключи томов, сортирует том и документы """
		if not self.manager:
			return
		self.model.sort_lib()
		self.update_ui()
	
	def reset_tags(self):
		""" Вызывает сброс тегов для тома """
		if not self.manager:
			return
		index = self.tree_view.currentIndex()
		if not index.isValid():
			QMessageBox.warning(self, "Сброс тегов", "Выберите том, в который хотите сбросить теги.")
			return
		reply = Requestion.ask(
			self,
			'Сброс тегов',
			'Вы действительно хотите сбросить все теги в томе?\n'
			'Это может повредить ссылки в ВОР.',
			with_cancel = False
		)
		if reply == QMessageBox.StandardButton.Yes:
			# Проверяем, что выбрано 
			if index.parent().isValid():
				index = index.parent()
			self.model.reset_tags(index)
			self.tree_view.expand(index)


class DocumentationModel(QAbstractItemModel):
	"""
	Кастомная модель для отображения иерархической структуры документации:
	- Корневые элементы: тома (Book)
	- Дочерние элементы: документы (Document)
	"""
	# Столбцы модели
	COL_TAG = 0		# Тэг документа или номер тома
	COL_CODE = 1	# Обозначение документа или тома (шифр)
	COL_NAME = 2	# Наименование документа или том
	COL_PAGE = 3	# Страница документа
	COL_LINK = 4	# Ссылка на документ или том

	HEADERS = ['Номер тома\n(Тег)', 'Обозначение', 'Наименование', 'Страница', 'Ссылка']
	
	def __init__(self, manager: DOCs_Manager, parent = None):
		super().__init__(parent)
		self.manager =manager
		self.access = False
		
	# ========== Обязательные методы QAbstractItemModel ==========

	def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
		"""Количество детей у родительского индекса"""
		if self.manager is None:
			return 0
		if not parent.isValid():
			# Корневой уровень: количество томов
			return len(self.manager.library)
		else:
			# Узел-том: количество документов в томе
			book : Book = parent.internalPointer()
			if isinstance(book, Book) and book.content:
				return len(book.content)
			else:
				return 0
	
	def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
		return len(self.HEADERS)
	
	def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
		"""Создаёт индекс для элемента по строке, столбцу и родителю"""
		if not self.manager:
			return QModelIndex()
		if not parent.isValid():
			# Корневой уровень: том
			books = list(self.manager.library.values())
			if row < len(books):
				book = books[row]
				return self.createIndex(row, column, book)
		else:
			# Уровень документа: родитель – том
			parent_item = parent.internalPointer()
			if isinstance(parent_item, Book):
				docs = list(parent_item.content.values())
				if row < len(docs):
					doc = docs[row]
					return self.createIndex(row, column, doc)
		return QModelIndex()

	def parent(self, index: QModelIndex) -> QModelIndex:
		"""Возвращает индекс родителя для данного индекса"""
		if not index.isValid:
			return QModelIndex()
		item = index.internalPointer()
		if item is None or not isinstance(item, Document): 
			return QModelIndex()
		# Документ: нужно найти книгу, которой он принадлежит
		for book in self.manager.library.values():
			if book is None or not hasattr(book, 'content'):
				continue
			if any(doc is item for doc in book.content.values()):
				# возвращаем индекс
				row = list(self.manager.library.values()).index(book)
				return self.createIndex(row, 0, book)
		return QModelIndex()
	
	def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
		"""Возвращает данные для указанной роли"""
		if not index.isValid():
			return None
		
		item = index.internalPointer()
		if item is None: 
			return None
		col = index.column()
		if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
			if isinstance(item, Book):
				if col == self.COL_TAG:
					return str(item.num)
				elif col == self.COL_CODE:
					return item.code
				elif col == self.COL_NAME:
					return item.name
				elif col == self.COL_PAGE:
					return ''
				elif col == self.COL_LINK:
					return item.link or ''
			elif isinstance(item, Document):
				if col == self.COL_TAG:
					return str(item.tag)
				elif col == self.COL_CODE:
					return item.code
				elif col == self.COL_NAME:
					return item.name
				elif col == self.COL_PAGE:
					return str(item.page)
				elif col == self.COL_LINK:
					return item.link or ''
		elif role == Qt.ItemDataRole.ToolTipRole:
			if isinstance(item, Book):
				if col == self.COL_CODE:
					return "Шифр тома"
				elif col == self.COL_NAME:
					return "Наименование тома"
			elif isinstance(item, Document):
				if col == self.COL_TAG:
					return "Уникальный тег документа (не редактируется)"
				elif col == self.COL_PAGE:
					return "Номер страницы в томе"
		elif role == Qt.ItemDataRole.TextAlignmentRole:
			if col in (self.COL_TAG, self.COL_PAGE):
				return Qt.AlignmentFlag.AlignCenter
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
			if isinstance(item, Book):
				if col == self.COL_TAG:
					item.num = convert_value(value)
				elif col == self.COL_CODE:
					item.code = value
				elif col == self.COL_NAME:
					item.name = value
				elif col == self.COL_LINK:
					item.link = value
				else:
					return False
			elif isinstance(item, Document):
				if col == self.COL_CODE:
					item.code = value
				elif col == self.COL_NAME:
					item.name = value
				elif col == self.COL_PAGE:
					item.page = int(value) if value else 0
				elif col == self.COL_LINK:
					item.link = value
				else:
					return False
			else:
				return False
			
			# Уведомляем представление об изменении данных
			self.dataChanged.emit(index, index, [role])
			return True
		except Exception as e:
			print(f'Ошибка обновления данных состава ПД: {e}')
			return False
		
	def flags(self, index: QModelIndex) -> Qt.ItemFlag:
		"""Определяет флаги элемента: можно ли редактировать, выбирать и т.д."""
		if not index.isValid() or not self.access:
			return Qt.ItemFlag.NoItemFlags
		base_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
		item = index.internalPointer()
		if item is None: 
			return None
		col = index.column()
		if isinstance(item, Book):
			# Тома: редактируем шифр, наименование, ссылку (страницу – нет)
			if col != self.COL_PAGE:
				base_flags |= Qt.ItemFlag.ItemIsEditable
		elif isinstance(item, Document):
			# Документы: редактируем всё, кроме тега (генерируется автоматически)
			if col != self.COL_TAG:
				base_flags |= Qt.ItemFlag.ItemIsEditable
		return base_flags
	
	def togle_acces(self, editable):
		""" Переключает доступность модели для редактирования """
		self.access = editable
	
	def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
		"""Возвращает заголовки столбцов"""
		if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
			if section <  len(self.HEADERS):
				return self.HEADERS[section]
		elif role == Qt.ItemDataRole.TextAlignmentRole:
			return Qt.AlignmentFlag.AlignCenter
		return None
	
	# ========== Методы для модификации структуры ==========
	def add_book(self) -> bool:
		"""Добавляет новый том"""
		if not self.manager:
			return
		# Получаем позицию вставки (в конец)
		row = len(self.manager.library)
		self.beginInsertRows(QModelIndex(), row, row)
		self.manager.add_book()
		self.endInsertRows()
		return True
	
	def remove_book(self, row: int) -> bool:
		"""Удаляет том по индексу строки"""
		books = list(self.manager.library.values())
		if row < 0 or row >= len(books):
			return False
		self.beginRemoveRows(QModelIndex(), row, row)
		book: Book = books[row]
		# Удаляем из словаря по ключу
		self.manager.remove_book(book.num)
		self.endRemoveRows()
	
	def add_document(self, parent_index: QModelIndex, row_index = None) -> bool:
		"""Добавляет документ в том, соответствующий parent_index"""
		if not parent_index.isValid():
			return False
		book: Book = parent_index.internalPointer()
		if not isinstance(book, Book):
			return False
		if row_index is None:
			row = len(book.content)
		else:
			doc = row_index.internalPointer()
			if not isinstance(doc, Document):
				return False
			docs = list(book.content.values())
			pos = docs.index(doc) if doc in docs else -1
			if pos == -1:
				return False
			row = pos +1
		self.beginInsertRows(parent_index, row, row)
		book.add_document(row)
		self.endInsertRows()
		return True
	
	def remove_document(self, parent_index: QModelIndex, row: int) -> bool:
		"""Удаляет документ из тома"""
		if not parent_index.isValid():
			return False
		book: Book = parent_index.internalPointer()
		if not isinstance(book, Book) or not book.content:
			return False
		docs = list(book.content.keys())
		if row < 0 or row >= len(docs):
			return False
		self.beginRemoveRows(parent_index, row, row)
		doc_key: Document = docs[row]
		# Удаляем из словаря по тегу
		book.remove_document(doc_key)
		self.endRemoveRows()
		return True
	
	def fill_book_by_template(self, parent_index: QModelIndex, row_index: QModelIndex, template: tuple) -> bool:
		""" Заполняет содержимое тома по шаблону """
		if not parent_index.isValid():
			return False
		book: Book = parent_index.internalPointer()
		if not isinstance(book, Book):
			return False
		if row_index is None:
			row_start = len(book.content)
			rows = sum(count for _, count in template)
			self.beginInsertRows(parent_index, row_start, row_start + rows - 1)
			book.fill_by_template(template)
			self.endInsertRows()
		else:
			doc = row_index.internalPointer()
			if not isinstance(doc, Document):
				return False
			docs = list(book.content.values())
			pos = docs.index(doc) if doc in docs else -1
			if pos == -1:
				return False
			row_start = pos +1
			rows = sum(count for _, count in template)
			self.beginInsertRows(parent_index, row_start, row_start + rows - 1)
			book.fill_by_template(template, row_start)
			self.endInsertRows()
		return True

	def fill_book_from_files(self, parent_index: QModelIndex, row_index: QModelIndex, files: list) -> bool:
		""" Заполняет содержимое тома на основании файлов """
		if parent_index is None and row_index is None:
			return False
		if parent_index is None:
			# Если parent_index не передан, значит row_index - это том (выбран том)
			book_index = row_index
			book: Book = book_index.internalPointer()
			if not isinstance(book, Book):
				return False
			row_start = len(book.content)
			parent = book_index
		else:
			book: Book = parent_index.internalPointer()
			if not isinstance(book, Book):
				return False
			doc = row_index.internalPointer()
			if not isinstance(doc, Document):
				return False
			docs = list(book.content.values())
			pos = docs.index(doc) if doc in docs else -1
			if pos == -1:
				return False
			row_start = pos +1
			parent = parent_index
		rows = len(files)
		self.beginInsertRows(parent, row_start, row_start + rows -1)
		book.fill_from_files(files, row_start)
		self.endInsertRows()

	def sort_lib(self):
		""" Сортирует тома и документацию по порядку, обновляет данные"""
		self.beginResetModel()
		self.manager.sort_books()
		self.endResetModel()
	
	def reset_tags(self, parent_index: QModelIndex) -> bool:
		""" Сбрасывает теги для документов в томе"""
		if not parent_index.isValid():
			return False
		book: Book = parent_index.internalPointer()
		if not isinstance(book, Book):
			return False
		self.beginResetModel()
		book.resetting_tags()
		self.endResetModel()
		
	def set_manager(self, manager):
		self.beginResetModel()
		self.manager = manager
		self.endResetModel()

	def save_lib(self):
		self.beginResetModel()
		self.modelReset.emit()
		result = self.manager.save_lib()
		self.endResetModel()
		return result
	
	def reload_documentation(self):
		self.beginResetModel()
		self.modelReset.emit()
		self.manager.reload_lib()
		self.endResetModel()

class Template_Dialog(QDialog):
	""" Вызывает диалоговое окно для создания шаблона заполнения """
	def __init__(self, parent):
		super().__init__(parent)
		window_name = 'Создания шаблона'
		self.setWindowTitle(window_name)
		self.setModal(True)

		layout = QVBoxLayout(self)
		
		# Таблица
		self.table = QTableWidget() 
		self.table.setColumnCount(2)
		self.table.setRowCount(20)
		self.table.setHorizontalHeaderLabels(['Тип документа', 'Количество'])
		self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
		self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
		delegate = EditableComboBoxDelegate(self.table)
		self.table.setItemDelegateForColumn(0, delegate)
		self.table.setItemDelegateForColumn(1, IntDelegate())
		layout.addWidget(self.table)
		
		# Кнопки
		btns = create_ok_cancel_buttons(self, False)
		layout.addWidget(btns)
		

	def get_data(self):
		none_list = {'-','', ' ', '.', None, 'None'}
		data = []
		for row in range(self.table.rowCount()):
			suffix_item = self.table.item(row, 0)
			if suffix_item is None:
				continue
			suffix_match_item = self.table.item(row, 1)
			suffix = suffix_item.text()
			matchs = int(suffix_match_item.text())
			if suffix not in none_list:
				data.append((suffix, matchs))
		return tuple(data)

		
class EditableComboBoxDelegate(QItemDelegate):
	def createEditor(self, parent, option, index):
		editor = QComboBox(parent)
		editor.setEditable(True)
		IN_BOOK_CODES= ['С', 'СП', 'ПЗ', 'В', 'Ч', 'СО','ТРИ', 'ВИ']
		editor.addItems(IN_BOOK_CODES)
		editor.setCurrentText('С')
		return editor
	
	def setEditorData(self, editor, index):
		value = index.data()
		if value:
			editor.setCurrentText(value)
	
	def setModelData(self, editor, model, index):
		model.setData(index, editor.currentText())


class DocumentationDelegate(WordWrapDelegate):
	"""
	Делегат для вкладки документации:
	- Перенос текста во всех ячейках.
	- Светло-серый фон для строк томов, при выделении — стандартный цвет.
	- Центрирование указанных столбцов.
	- Для столбца страницы — редактор QLineEdit с валидатором целых чисел.
	"""
	def __init__(self, parent=None, centered_columns=None, page_column=None):
		super().__init__(parent)
		self.centered_columns = centered_columns or []
		self.page_column = page_column
		self.grid_color = QColor(0xd0, 0xd0, 0xd0)   # цвет границ

	def paint(self, painter, option, index):
		painter.save()

		# Определяем, является ли элемент томом (корневым)
		item = index.internalPointer()
		is_book = isinstance(item, Book)

		# Определяем фон
		if is_book:
			if option.state & QStyle.StateFlag.State_Selected:
				painter.fillRect(option.rect, option.palette.highlight())
			else:
				painter.fillRect(option.rect, QColor('#5FADC0'))
		else:
			bg_brush = index.data(Qt.ItemDataRole.BackgroundRole)
			if bg_brush is not None:
				painter.fillRect(option.rect, bg_brush)
			else:
				if option.state & QStyle.StateFlag.State_Selected:
					painter.fillRect(option.rect, option.palette.highlight())
				else:
					painter.fillRect(option.rect, option.palette.base())

		text = index.data(Qt.ItemDataRole.DisplayRole) or ""
		if text:
			doc = QTextDocument()
			doc.setPlainText(text)
			text_width = option.rect.width() - 2 * self.margin
			doc.setTextWidth(max(text_width, 1))

			# Цвет текста
			if option.state & QStyle.StateFlag.State_Selected:
				color = option.palette.highlightedText().color()
			else:
				color = option.palette.text().color()
			doc.setDefaultStyleSheet(f"body {{ color: {color.name()}; }}")

			# Устанавливаем выравнивание, если столбец в списке центрируемых
			if index.column() in self.centered_columns:
				doc.setDefaultTextOption(QTextOption(Qt.AlignmentFlag.AlignCenter))

			painter.translate(option.rect.x() + self.margin, option.rect.y() + self.margin)
			doc.drawContents(painter)
			painter.translate(-option.rect.x() - self.margin, -option.rect.y() - self.margin)

		# Рисуем границы ячеек
		self._draw_grid(painter, option, index)

		painter.restore()

	def _draw_grid(self, painter, option, index):
		"""Рисует границы ячейки."""
		painter.setPen(self.grid_color)
		rect = option.rect
		painter.drawRect(rect)

	def sizeHint(self, option, index):
		text = index.data(Qt.ItemDataRole.DisplayRole) or ""
		if not text:
			return QSize(0, 0)

		# Вычисляем ширину
		width = option.rect.width()
		if width <= 0:
			tree_view = self.parent()
			if tree_view:
				width = tree_view.columnWidth(index.column())
			else:
				width = 100

		text_width = width - 2 * self.margin
		if text_width <= 0:
			text_width = 1

		doc = QTextDocument()
		doc.setPlainText(text)
		doc.setTextWidth(text_width)
		size = doc.size().toSize()
		size.setHeight(size.height() + 2 * self.margin)
		return size

	def createEditor(self, parent, option, index):
		if not (index.flags() & Qt.ItemFlag.ItemIsEditable):
			return None

		if index.column() == self.page_column:
			editor = QLineEdit(parent)
			editor.setValidator(QIntValidator())
			return editor
		else:
			editor = QTextEdit(parent)
			editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
			editor.setFrameStyle(QFrame.Shape.NoFrame)
			return editor

	def setEditorData(self, editor, index):
		text = index.data(Qt.ItemDataRole.EditRole) or ""
		if isinstance(editor, QLineEdit):
			editor.setText(str(text))
		else:
			editor.setPlainText(text)

	def setModelData(self, editor, model, index):
		if isinstance(editor, QLineEdit):
			value = editor.text()
			model.setData(index, value, Qt.ItemDataRole.DisplayRole)
			model.setData(index, value, Qt.ItemDataRole.EditRole)
		else:
			text = editor.toPlainText()
			model.setData(index, text, Qt.ItemDataRole.DisplayRole)
			model.setData(index, text, Qt.ItemDataRole.EditRole)

		tree_view = self.parent()
		if tree_view and isinstance(tree_view, QTreeView):
			tree_view.scheduleDelayedItemsLayout()
			tree_view.viewport().update()

	def updateEditorGeometry(self, editor, option, index):
		editor.setGeometry(option.rect)
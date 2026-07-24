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
	QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QPlainTextEdit,
	QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QApplication, QTreeView,
	QStackedWidget, QScrollArea, QFrame, QGroupBox, QDateEdit, QListWidget, QListWidgetItem, 
	QToolBox
	)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex, QDate
from ..ui_utilities import create_separator
from ..icons import Icons
from ..support.Calculator import CalculatorWidget 
from Core.BoQ import BoQ_manager, Section, Link
from Core.Utilities import convert_value
from Core.Project import Project


class SideBar_Right(QWidget):
	"""Правая боковая панель с инструментами."""
	navigate_to_address = pyqtSignal(tuple)   # для передачи адреса в основное окно
	def __init__(self, project, parent=None):
		super().__init__(parent)
		self.project = project
		self.current_tree_view = None  # будет хранить QTreeView активной вкладки

		layout = QVBoxLayout(self)
		layout.setContentsMargins(5, 5, 5, 5)

		# Переключатель инструментов
		self.tool_selector = QComboBox()
		self.tool_selector.setStyleSheet(""" 
			QComboBox  {
	 		background-color: #45464F;
	 		color: white;
	 		border-radius: 4px;
	 		padding: 6px;
			}
			QComboBox QListView {
				background-color: #45464F;
				border-radius: 10px;
			}
			QComboBox QListView::item {
				background-color: #51525C;
				color: white;
				border-radius: 4px;
			}
		""")
		self.tool_selector.addItems([
			"Ведомость",  "Содержание", "Редактор ссылок", 
			"Калькулятор", "Журнал изменений", "Заметки", "Анализ"
		])
		self.tool_selector.setItemIcon(0, Icons.edit_document)
		self.tool_selector.setItemIcon(1, Icons.data_table)
		self.tool_selector.setItemIcon(2, Icons.attach)
		self.tool_selector.setItemIcon(3, Icons.calculate)
		self.tool_selector.setItemIcon(4, Icons.log_list)
		self.tool_selector.setItemIcon(5, Icons.edit_note)
		self.tool_selector.setItemIcon(6, Icons.checklist)

		self.tool_selector.currentIndexChanged.connect(self.on_tool_changed)
		label = QLabel("<b>Боковая панель:</b>")
		font = label.font()
		font.setPixelSize(14)
		label.setFont(font)
		layout.addWidget(label)
		layout.addWidget(self.tool_selector)

		# Стек для инструментов
		self.tool_stack = QStackedWidget()
		layout.addWidget(self.tool_stack)

		# ------- Основные данные ------
		self.data_file = DataFile(self, None)
		self.tool_stack.addWidget(self.data_file)

		# ------- Содержание
		self.content_navigator = ContentNavigator(self)
		self.content_navigator.sectionSelected.connect(self.navigate_to_section)
		self.tool_stack.addWidget(self.content_navigator)

		# ------- Редактор ссылок ------
		self.links_editor = Links_Editor(project=self.project, parent=self)
		self.tool_stack.addWidget(self.links_editor)

		# ------- Калькулятор ------
		self.calculator = CalculatorWidget()
		self.tool_stack.addWidget(self.calculator)

		# ----- Журнал изменений -----
		self.logs_table = Logs_Table(self)
		self.tool_stack.addWidget(self.logs_table)

		# --------- Заметки --------- 
		self.note = Note_BoQ(None, self)
		self.tool_stack.addWidget(self.note)

		# ---------- Анализ ---------
		self.analysator = Analysator(self)
		self.tool_stack.addWidget(self.analysator)


	def set_project(self, project):
			"""Обновляет проект во всех дочерних инструментах."""
			self.project = project
			self.links_editor.set_project(project)

	def set_active_model(self, model, index: QModelIndex, tree_view: QTreeView = None):
		"""Передаёт активную модель и текущий индекс в инструменты."""
		if tree_view is not None:
			self.current_tree_view = tree_view
		manager = model.manager if model else None
		self.data_file.set_manager(manager)
	
		# Всегда обновляем компоненты, не зависящие от выделения
		self.logs_table.set_manager(manager)
		self.note.set_manager(manager)
		self.data_file.set_manager(manager)
		self.content_navigator.set_manager(manager)
		self.analysator.set_manager(manager)
		
		# Редактор ссылок зависит от выделения
		if index.isValid():
			self.links_editor.setModel(model)
			self.links_editor.setCurrentIndex(index)
		else:
			self.links_editor.clear()

	def on_tool_changed(self, index):
		self.tool_stack.setCurrentIndex(index)
		if index == 0:  # Ведомость
			self.data_file.refresh()
			if self.data_file.manager:
				self.data_file.set_data()  # принудительно обновить
		elif index == 1:  # Содержание
			self.content_navigator.refresh()
		# Если выбран редактор ссылок (индекс 2), обновить его данные
		if index == 2:
			self.links_editor.refresh()
	
	def clear(self):
		"""Очищает все редакторы боковой панели."""
		self.logs_table.clear()
		self.note.clear()
		self.links_editor.clear()
		self.data_file.clear()
		self.content_navigator.clear()
		self.analysator.clear()
		self.current_tree_view = None


	def navigate_to_section(self, section_idx):
		"""Переходит к указанному разделу в основном представлении."""
		if not self.current_tree_view:
			return
		model = self.current_tree_view.model()
		if model is None:
			return

		# Получаем индекс раздела (корневой элемент)
		section_index = model.index(section_idx, 0, QModelIndex())
		if not section_index.isValid():
			return

		# Устанавливаем текущий индекс и раскрываем ветку
		self.current_tree_view.setCurrentIndex(section_index)
		self.current_tree_view.scrollTo(section_index, QTreeView.ScrollHint.PositionAtCenter)
		self.current_tree_view.expand(section_index)

	def set_navigation_target(self, target_widget):
		"""Устанавливает внешний виджет для навигации (обычно BoQ_Tab)."""
		self.navigate_to_address.connect(target_widget.navigate_to_address)
	
	def get_current_manager(self):
		"""Возвращает менеджера из текущего tree_view или None."""
		if self.current_tree_view:
			model = self.current_tree_view.model()
			if model and hasattr(model, 'manager'):
				return model.manager
		return None

class Links_Editor(QWidget):
	"""Редактор для колонки 6: динамический список строк с тремя полями."""
	dataChanged = pyqtSignal()
	
	def __init__(self, project, parent=None):
		super().__init__(parent)
		self.project = project
		self.model = None
		self.current_index = QModelIndex()
		self.items = []  # список объектов Link
		self.setup_ui()
		
	def setup_ui(self):
		main_layout = QVBoxLayout(self)
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.setSpacing(0)
		
		# Контейнер для списка (заголовки + scroll)
		list_container = QWidget()
		list_layout = QVBoxLayout(list_container)
		list_layout.setContentsMargins(0, 0, 0, 0)
		list_layout.setSpacing(2)

		# Заголовки
		header_layout = QHBoxLayout()
		header1 = QLabel("<b>Том</b>")
		header1.setContentsMargins(15, 0, 18, 0)
		header_layout.addWidget(header1)
		header_layout.addWidget(create_separator(QFrame.Shape.VLine)) # ---
		header2 = QLabel("<b>Тег</b>")
		header2.setContentsMargins(12, 0, 18, 0)
		header_layout.addWidget(header2)
		header_layout.addWidget(create_separator(QFrame.Shape.VLine)) # ---
		header3 = QLabel("<b>Переопределить<br>страницы</b>")
		header3.setContentsMargins(10, 0, 0, 0)
		header_layout.addWidget(header3)
		header_layout.addStretch()
		list_layout.addLayout(header_layout)
		
		# Область прокрутки для списка
		scroll = QScrollArea(self)
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.Panel)
		scroll.setProperty("class", "panel")   # добавляем динамическое свойство для глобального стиля
		#scroll.setMaximumWidth(500)

		# Внутренний контейнер для строк
		self.list_container = QWidget()
		self.list_layout = QVBoxLayout(self.list_container)
		self.list_layout.setContentsMargins(0, 0, 0, 0)
		self.list_layout.setSpacing(2)
		self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
		scroll.setWidget(self.list_container)

		list_layout.addWidget(scroll)
		main_layout.addWidget(list_container)
		
		# Кнопки управления
		btn_layout = QHBoxLayout()
		btn_layout.setContentsMargins(5, 5, 5, 5)
		btn_layout.setSpacing(2)
		
		self.add_btn = QPushButton()
		self.add_btn.setIcon(Icons.add)
		self.add_btn.setToolTip('Добавить')
		self.add_btn.clicked.connect(self.add_row)
		
		self.remove_btn = QPushButton()
		self.remove_btn.setIcon(Icons.remove)
		self.remove_btn.setToolTip('Удалить последний')
		self.remove_btn.clicked.connect(self.remove_row)
		
		btn_layout.addWidget(self.add_btn)
		btn_layout.addWidget(self.remove_btn)

		# Добавляем btn_widget с вертикальным выравниванием по центру
		main_layout.addLayout(btn_layout)
	
	def set_project(self, project):
		self.project = project
		self.update_books_in_rows()
		# Убедимся, что библиотека документации загружена
		if self.project and self.project.documentation_manager:
			if not self.project.documentation_manager.library:
				self.project.documentation_manager.load_lib()
		self.update_books_in_rows()
		# Обновить текущее отображение, если есть активная строка
		if self.model and self.current_index.isValid():
			self.setCurrentIndex(self.current_index)
	
	def setModel(self, model):
		self.model = model
	
	def setCurrentIndex(self, index: QModelIndex):
		"""Принимает QModelIndex текущей ячейки и загружает ссылки строки."""
		self.current_index = index
		if not self.model or not index.isValid():
			self.clear_rows()
			self.setEnabled(False)
			return
		item = index.internalPointer()
		# Редактор доступен только для Work и Resource
		if isinstance(item, Section) or not hasattr(item, 'links'):
			self.clear_rows()
			self.setEnabled(False)
			return
		self.setEnabled(True)
		# Перед загрузкой убедимся, что библиотека готова
		if self.project and self.project.documentation_manager:
			if not self.project.documentation_manager.library:
				self.project.documentation_manager.load_lib()
		self.load_data(item.links)

	def refresh(self):
		"""Обновить отображение для текущего индекса."""
		if self.current_index.isValid():
			self.setCurrentIndex(self.current_index)

	def update_books_in_rows(self):
		"""Обновляет список томов во всех существующих QComboBox."""
		if not self.project or not self.project.documentation_manager:
			return
		books = self._get_sorted_books()
		for i in range(self.list_layout.count()):
			row_widget = self.list_layout.itemAt(i).widget()
			if row_widget:
				combo = row_widget.property("combo")
				if combo:
					current_data = combo.currentData()
					combo.blockSignals(True)
					combo.clear()
					if not books:
						combo.addItem("Пусто", None)
						combo.setEnabled(False)
					else:
						combo.setEnabled(True)
						for book_num in books:
							combo.addItem(str(book_num), book_num)
					# Восстанавливаем выбранное значение
					if current_data is not None:
						idx = combo.findData(current_data)
						if idx >= 0:
							combo.setCurrentIndex(idx)
					combo.blockSignals(False)

	def _get_sorted_books(self):
		books = []
		if self.project and self.project.documentation_manager:
			if not self.project.documentation_manager.library:
				self.project.documentation_manager.load_lib()
			for book_num in self.project.documentation_manager.library.keys():
				books.append(book_num)
			# Безопасная сортировка: числа по возрастанию, затем строки
			def sort_key(val):
				try:
					return (0, float(val))
				except (ValueError, TypeError):
					return (1, str(val))
			books.sort(key=sort_key)
		return books

	def load_data(self, links):
		"""Загружает список элементов и создает строки редактора."""
		self.clear_rows()
		self.items = links.copy() if links else []
		for link in self.items:
			self.add_row_widgets(link)
	
	def clear_rows(self):
		while self.list_layout.count():
			child = self.list_layout.takeAt(0)
			if child.widget():
				child.widget().deleteLater()

	def _sort_items(self):
		"""Сортирует self.items по book_num (числа перед строками) и tag."""
		def sort_key(link):
			try:
				book_num_key = (0, float(link.book_num))
			except (ValueError, TypeError):
				book_num_key = (1, str(link.book_num))
			return (book_num_key, link.tag)
		self.items.sort(key=sort_key)
	
	def add_row_widgets(self, link=None):
		"""Создает виджеты для одной строки списка."""
		row_widget = QWidget()
		row_layout = QHBoxLayout(row_widget)
		row_layout.setContentsMargins(0, 0, 0, 0)
		
		combo = QComboBox()
		combo.setEditable(False)
		books = self._get_sorted_books()
		# Если список книг пуст, показываем заглушку
		if not books:
			combo.addItem("Пусто", None)
			combo.setEnabled(False)
		else:
			combo.setEnabled(True)
			for book_num in books:
				combo.addItem(str(book_num), book_num)
		if link:
			idx = combo.findData(link.book_num)
			if idx >= 0:
				combo.setCurrentIndex(idx)
			elif combo.count() > 0:
				combo.setCurrentIndex(0)
		combo.currentIndexChanged.connect(self.on_item_changed)
		
		# Поле ввода целого числа (тег)
		tag_edit = QLineEdit()
		tag_edit.setPlaceholderText("тег")
		tag_edit.setValidator(QIntValidator(0, 9999))
		if link:
			tag_edit.setText(str(link.tag))
		tag_edit.textChanged.connect(self.on_item_changed)
		tag_edit.setMaximumWidth(50)
		
		# Строка ввода "Переопределить страницы"
		pages_edit = QLineEdit()
		pages_edit.setPlaceholderText("Переопределить страницы")
		if link and link.user_pages:
			pages_edit.setText(link.user_pages)
		pages_edit.textChanged.connect(self.on_item_changed)

		# Кнопка удаления строки
		delete_btn = QPushButton()
		delete_btn.setIcon(Icons.delete)
		delete_btn.setToolTip("Удалить строку")
		delete_btn.setFixedSize(24, 24)
		delete_btn.clicked.connect(lambda checked, w=row_widget: self.delete_row_widget(w))
		
		row_layout.addWidget(combo)
		row_layout.addWidget(tag_edit)
		row_layout.addWidget(pages_edit, stretch=1)
		row_layout.addWidget(delete_btn)
		
		# Сохраняем ссылки на виджеты в свойствах
		row_widget.setProperty("combo", combo)
		row_widget.setProperty("tag_edit", tag_edit)
		row_widget.setProperty("pages_edit", pages_edit)
		self.list_layout.addWidget(row_widget)
		
	
	def add_row(self):
		"""Добавляет новую строку с пустыми значениями."""
		if not self.project:
			return
		new_link = Link(self.project)
		if self.project.documentation_manager.library:
			first_book_num = next(iter(self.project.documentation_manager.library.keys()))
			new_link.book_num = first_book_num
		else:
			new_link.book_num = 0
		new_link.tag = 0
		# Вставляем в отсортированном порядке
		self.items.append(new_link)
		self._sort_items()
		# Перестраиваем весь список, чтобы сохранить порядок
		self.load_data(self.items)
		self.dataChanged.emit()
		self.save_to_model()
	
	def remove_row(self):
		"""Удаляет последнюю строку."""
		if self.items:
			removed_link = self.items.pop()
			self._remove_link_from_manager(removed_link)
			# Перестраиваем список
			self.load_data(self.items)
			self.dataChanged.emit()
			self.save_to_model()
	
	def delete_row_widget(self, row_widget):
		"""Удаляет переданный виджет строки и соответствующие данные."""
		# Находим индекс виджета в list_layout
		index = self.list_layout.indexOf(row_widget)
		if index == -1:
			return
		# Удаляем соответствующий элемент из self.items
		if index < len(self.items):
			removed_link = self.items.pop(index)
			self._remove_link_from_manager(removed_link)
		self.load_data(self.items)
		self.dataChanged.emit()
		self.save_to_model()

	def _remove_link_from_manager(self, link):
			item = self.current_index.internalPointer()
			if hasattr(item, 'manager') and item.manager:
				try:
					item.manager.links.remove(link)
				except KeyError:
					pass	

	def on_item_changed(self):
		"""Собирает данные из всех строк и обновляет self.items."""
		new_items = []
		for i in range(self.list_layout.count()):
			row_widget = self.list_layout.itemAt(i).widget()
			if row_widget:
				combo = row_widget.property("combo")
				tag_edit = row_widget.property("tag_edit")
				pages_edit = row_widget.property("pages_edit")
				if i < len(self.items):
					link = self.items[i]
				else:
					link = Link(self.project)
					self.items.append(link)

				book_num_data = combo.currentData()
				if book_num_data is not None:
					# convert_value уже импортирован из Core.Utilities
					link.book_num = convert_value(book_num_data)
				else:
					link.book_num = 0

				tag_text = tag_edit.text()
				link.tag = int(tag_text) if tag_text else 0
				link.user_pages = pages_edit.text().strip() or None
				new_items.append(link)

		self.items = new_items
		self.dataChanged.emit()
		self.save_to_model()

	def save_to_model(self):
		if self.model and self.current_index.isValid():
			item = self.current_index.internalPointer()
			if hasattr(item, 'links'):
				# Удаляем старые ссылки из менеджера (если есть)
				if hasattr(item, 'manager') and item.manager:
					for link in item.links:
						try:
							item.manager.links.remove(link)
						except KeyError:
							pass
				# Сортируем self.items безопасно
				self._sort_items()
				# Присваиваем отсортированный список
				item.links = self.items
				if hasattr(item, 'manager') and item.manager:
					item.manager.links.update(self.items)
				# Обновляем представление
				self.model.dataChanged.emit(self.current_index, self.current_index, [Qt.ItemDataRole.DisplayRole])
				item.manager.is_modified = True

	def clear(self):
		self.model = None
		self.current_index = QModelIndex()
		self.clear_rows()
		self.items = []
		self.setEnabled(False)

class Logs_Table(QWidget):
	"""
	Редактор журнала изменений ведомости объемов работ
	Принимает   """
	dataChanged = pyqtSignal()
	def __init__(self, parent = None):
		super().__init__(parent)
		self.manager: BoQ_manager = None
		self.setup_ui()
	
	def setup_ui(self):
		layout = QVBoxLayout(self)

		#-------------- Таблица ---------------
		self.table = QTableWidget()

		self.table.setColumnCount(2)
		self.table.setHorizontalHeaderLabels(["Дата", "Событие"])
		self.table.setColumnWidth(0, 100)
		self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
		self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
		self.table.setWordWrap(True)
		self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)

		layout.addWidget(self.table)

		#-------------- Кнопки ---------------
		btns_container = QVBoxLayout()
		btns_edit_container = QHBoxLayout()

		add_row_button = QPushButton('Добавить')
		add_row_button.clicked.connect(self.add_row)
		btns_edit_container.addWidget(add_row_button)

		del_button = QPushButton('Удалить')
		del_button.setToolTip('Удалить выбранню строку')
		del_button.clicked.connect(self.remove_row)
		btns_edit_container.addWidget(del_button)

		btns_container.addLayout(btns_edit_container)

		save_button = QPushButton('Сохранить')
		save_button.clicked.connect(self.save_data)
		btns_container.addWidget(save_button)
		layout.addLayout(btns_container)

	
	def load_data(self):
		if not self.manager or not self.manager.log_list:
			while self.table.rowCount() > 0:
				self.table.removeRow(0)
			return
		log_list = self.manager.log_list
		if not log_list:
			return
		self.table.setRowCount(len(log_list))
		for row, entry in enumerate(log_list):
			self.table.setItem(row, 0, QTableWidgetItem(entry.get('Date')))
			self.table.setItem(row, 1, QTableWidgetItem(entry.get('Event')))
		self.table.resizeRowsToContents()
	
	def set_manager(self, manager):
		"""Устанавливает менеджер и загружает данные."""
		self.manager = manager
		self.load_data()
	
	def clear(self):
		"""Очищает таблицу и сбрасывает менеджер."""
		self.manager = None
		self.table.setRowCount(0)
	
	def save_data(self):
		if not self.manager:
			return
		log_list = []
		for row in range(self.table.rowCount()):
			date_item = self.table.item(row, 0)
			event_item = self.table.item(row, 1)
			log_list.append({
				'Date': date_item.text() if date_item else '',
				'Event': event_item.text() if event_item else ''
			})
		if log_list:
			log_list.sort(key=lambda row: row.get('Date'))
		self.manager.log_list = log_list
		self.manager.is_modified = True
		self.load_data()

	def add_row(self):
		row = self.table.rowCount()
		self.table.insertRow(row)
		self.table.setItem(row, 0, QTableWidgetItem(self.manager.project.now.strftime("%d.%m.%Y")))
		self.table.setItem(row, 1, QTableWidgetItem(''))

	def remove_row(self):
		current_row = self.table.currentRow()
		if current_row >= 0:
			self.table.removeRow(current_row)
			self.save_data()



class DataFile(QWidget):
	"""
	Служит для работы с данными о ведомости. Работает с данными Projct и текущего Manager.
	Динамическая связь данных
	"""
	dataChanged = pyqtSignal()
	def __init__(self, parent, manager: BoQ_manager):
		super().__init__(parent)
		self._updating = False  # флаг, что идёт программное обновление
		self.project: Project = manager.project if manager else None
		self.manager: BoQ_manager = manager
		self.setup_ui()
	
	def setup_ui(self):
		layout = QVBoxLayout(self)

		# ------------------- Наименование стройки -------------------
		construction_site_group = QGroupBox(' Наименование стройки ')
		construction_site_layout = QHBoxLayout()
		self.construction_site = QLabel()
		self.construction_site.setWordWrap(True)
		construction_site_layout.addWidget(self.construction_site)
		construction_site_group.setLayout(construction_site_layout)
		layout.addWidget(construction_site_group)

		# ----------------- Наименование объекта КС ------------------
		object_name_group = QGroupBox(' Наименование объекта ')
		object_name_layout = QHBoxLayout()
		object_name_layout.setAlignment(Qt.AlignmentFlag.AlignTop)		  # ← прижать к верху
		self.object_name_plane_text = QPlainTextEdit()
		self.object_name_plane_text.setMaximumHeight(50)
		self.object_name_plane_text.textChanged.connect(self._on_text_changed)
		object_name_layout.addWidget(self.object_name_plane_text)
		object_name_group.setLayout(object_name_layout)
		object_name_group.setMaximumHeight(100)
		layout.addWidget(object_name_group)

		# --------------------- Номер ведомости ----------------------
		num_group = QGroupBox(' Номер ведомости ')
		num_layout = QHBoxLayout()
		self.num_edit = QLineEdit()
		self.num_edit.textChanged.connect(self._on_text_changed)
		num_layout.addWidget(self.num_edit)
		num_group.setLayout(num_layout)
		layout.addWidget(num_group)

		# ------------------- Перечень документов --------------------
		reason_group = QGroupBox(' Основание ')
		reason_container = QHBoxLayout()
		self.reason_text = QLabel()
		self.reason_text.setWordWrap(True)
		reason_container.addWidget(self.reason_text)
		reason_group.setLayout(reason_container)
		layout.addWidget(reason_group)

		# -------------------- Дата составления ----------------------
		date_group = QGroupBox(' Дата составления ')
		date_layout = QHBoxLayout()
		self.doc_date = QDateEdit()
		self.doc_date.setCalendarPopup(True)
		self.doc_date.setDisplayFormat("dd.MM.yyyy")
		self.doc_date.dateChanged.connect(self._on_date_changed)		  # новый слот
		date_layout.addWidget(self.doc_date)
		date_group.setLayout(date_layout)
		layout.addWidget(date_group)

		# ------------------------ Составил --------------------------
		composer_group = QGroupBox(' Составитель ')
		composer_layout = QVBoxLayout()
		composer_name_container = QHBoxLayout()
		composer_name_container.addWidget(QLabel('Составил:   '))
		self.composer = QComboBox()
		self.composer.setEditable(True)
		self.composer.currentTextChanged.connect(self._on_text_changed)
		self.composer.setMinimumWidth(180)
		composer_name_container.addWidget(self.composer)
		composer_name_container.addStretch()
		composer_layout.addLayout(composer_name_container)

		composer_post_container = QHBoxLayout()
		composer_post_container.addWidget(QLabel('Должность:'))
		self.composer_post = QComboBox()
		self.composer_post.setEditable(True)
		self.composer_post.currentTextChanged.connect(self._on_text_changed)
		self.composer_post.setMinimumWidth(180)
		composer_post_container.addWidget(self.composer_post)
		composer_post_container.addStretch()
		composer_layout.addLayout(composer_post_container)

		composer_group.setLayout(composer_layout)
		layout.addWidget(composer_group)

		# ------------------------ Проверил --------------------------
		verifier_group = QGroupBox('Проверил')
		verifier_layout = QVBoxLayout()
		verifier_name_container = QHBoxLayout()
		verifier_name_container.addWidget(QLabel('Проверил:  '))
		self.verifier_name = QComboBox()
		self.verifier_name.setEditable(False)
		self.verifier_name.currentTextChanged.connect(self._on_text_changed)
		self.verifier_name.setMinimumWidth(180)
		verifier_name_container.addWidget(self.verifier_name)
		verifier_name_container.addStretch()
		verifier_layout.addLayout(verifier_name_container)

		verifier_post_container = QHBoxLayout()
		verifier_post_container.addWidget(QLabel('Должность:'))
		self.verifier_post = QComboBox()
		self.verifier_post.setEditable(False)
		self.verifier_post.currentTextChanged.connect(self._on_text_changed)
		self.verifier_post.setMinimumWidth(180)
		verifier_post_container.addWidget(self.verifier_post)
		verifier_post_container.addStretch()
		verifier_layout.addLayout(verifier_post_container)

		verifier_group.setLayout(verifier_layout)
		layout.addWidget(verifier_group)

		layout.addStretch()
		
	def set_manager(self, manager):
		if self.manager is manager:
			return # тот же объект, пропускаем
		self.manager = manager
		if manager:
			self.project = self.manager.project
			self.set_data()
		else:
			self.clear()

	def set_data(self):
		if not self.manager:
			return
		self._updating = True

		# Блокируем сигналы у всех виджетов
		widgets_to_block = [
			self.object_name_plane_text,
			self.num_edit,
			self.doc_date,
			self.composer,
			self.composer_post,
			self.verifier_name,
			self.verifier_post 
		]
		for w in widgets_to_block:
			w.blockSignals(True)

		# Устанавливаем текстовые поля
		self.object_name_plane_text.setPlainText(self.manager.object_name or '')
		self.num_edit.setText(self.manager.num or '')
		# Дата: из строки в QDate
		date_str = self.manager.date
		if date_str:
			date = QDate.fromString(date_str, "dd.MM.yyyy")
			if date.isValid():
				self.doc_date.setDate(date)
		else:
			self.doc_date.setDate(QDate.currentDate())
		# --- Работа с комбобоксами ---
		if self.project:
			constr_site = self.project.construction_site
			self.construction_site.setText(constr_site)

			signatures = self.manager.signatures

			# Комбобокс "Составил"
			self.composer.clear()
			self.composer.addItems(self.project.performers or [])
			composer_name = signatures.get('Composer', '')
			if composer_name:
				idx = self.composer.findText(composer_name)
				if idx >= 0:
					self.composer.setCurrentIndex(idx)
				else:
					self.composer.addItem(composer_name)
					self.composer.setCurrentIndex(self.composer.count() - 1)
			# Комбобокс "Должность"
			self.composer_post.clear()
			self.composer_post.addItems(self.project.posts or [])
			composer_post = signatures.get('Composer_Position', '')
			if composer_post:
				idx = self.composer_post.findText(composer_post)
				if idx >= 0:
					self.composer_post.setCurrentIndex(idx)
				else:
					self.composer_post.addItem(composer_post)
					self.composer_post.setCurrentIndex(self.composer_post.count() - 1)

			# --- Проверил ---

			self.verifier_name.clear()
			self.verifier_post.clear()

			chiefs_list = self.project.chiefs if self.project.chiefs else []
			posts_list = self.project.posts if self.project.posts else []

			self.verifier_name.addItems(chiefs_list)
			self.verifier_post.addItems(posts_list)

			# Определяем, какие данные использовать: переопределённые в manager или глобальные
			if isinstance(self.manager.verifier, dict):
				verifier = self.manager.verifier
				name = verifier.get('Name', '')
				pos = verifier.get('Position', '')
				self.verifier_name.setCurrentText(name) if name else self.verifier_name.setCurrentIndex(0)
				self.verifier_post.setCurrentText(pos) if pos else self.verifier_post.setCurrentIndex(0)
			else:
				verifier = self.project.verifier if self.project else {}
				name = verifier.get('Name', '')
				pos = verifier.get('Position', '')
				self.verifier_name.setPlaceholderText(name)
				self.verifier_post.setPlaceholderText(pos)
				# Сбрасываем выбор, чтобы отображался placeholder
				self.verifier_name.setCurrentText(name)
				self.verifier_post.setCurrentText(pos)

		# Основание
		reason = getattr(self.manager, 'reason', '')
		self.reason_text.setText(reason.replace('\n', '<br>') if reason else '')
		
		# Принудительно обрабатываем очередь событий (на случай отложенных изменений)
		QApplication.processEvents()

		# Разблокируем сигналы
		for w in widgets_to_block:
			w.blockSignals(False)
		
		self._updating = False


	def refresh(self):
		if self.manager:
			self.set_data()


	def clear(self):
		self.manager = None
		self.construction_site.clear()
		self.composer.clear()
		self.composer_post.clear()
		self.verifier_name.clear()
		self.verifier_post.clear()
		self.object_name_plane_text.clear()
		self.reason_text.clear()
		self.doc_date.clear()
		self.composer.clear()
		self.composer_post.clear()
		self.verifier_name.clear()
		self.verifier_post.clear()

	def _on_text_changed(self):
		if self._updating or not self.manager:
			return
		
		object_name = self.object_name_plane_text.toPlainText()
		if self.manager.object_name != object_name:
			self.manager.object_name = object_name
			self._signal()
		num = self.num_edit.text()
		if self.manager.num != num:
			self.manager.num = num
			self._signal()
		date = self.doc_date.text()
		if self.manager.date != date:
			self.manager.date = date
			self._signal()
		composer = self.composer.currentText()
		if self.manager.signatures['Composer'] != composer:
			self.manager.signatures['Composer'] = composer
			self._signal()
		composer_post = self.composer_post.currentText()
		if self.manager.signatures['Composer_Position'] != composer_post:
			self.manager.signatures['Composer_Position'] = composer_post
			self._signal()
		
		verifier_name = self.verifier_name.currentText()
		verifier_post = self.verifier_post.currentText()
		if verifier_name:
			if verifier_name == self.project.verifier.get('Name', ''):
				self.manager.verifier = None
			else:
				self.manager.verifier = {
					'Name': verifier_name,
					'Position': verifier_post	
				}
		else:
			self.manager.verifier = None
			
	def _signal(self):
		self.manager.is_modified = True
		self.dataChanged.emit()	

	def _on_date_changed(self, date):
		if self._updating or not self.manager:
			return
		date_str = date.toString("dd.MM.yyyy")
		if self.manager.date != date_str:
			self.manager.date = date_str
			self.manager.is_modified = True
			self.dataChanged.emit()



class Note_BoQ(QWidget):
	"""
	Работаем с заметками о текущей вкладке виде просто текстового редактора. 
	Берет и возвращает данные из manager.note;	Динамическая связь данных
	"""
	dataChanged = pyqtSignal()

	def __init__(self, manager, parent=None):
		super().__init__(parent)
		self.manager = manager
		self.setup_ui()

	def setup_ui(self):
		layout = QVBoxLayout(self)
		self.text_editor = QPlainTextEdit(self)
		self.text_editor.setPlaceholderText("Заметки о документе")
		self.text_editor.textChanged.connect(self._on_text_changed)
		layout.addWidget(self.text_editor)

	def setPlaceholderText(self, text):
		self.text_editor.setPlaceholderText(text)

	def set_manager(self, manager):
		self.manager = manager
		if manager:
			self.text_editor.setPlainText(manager.note if manager.note else "")
		else:
			self.text_editor.clear()

	def clear(self):
		self.manager = None
		self.text_editor.clear()

	def _on_text_changed(self):
		if self.manager:
			new_text = self.text_editor.toPlainText()
			if self.manager.note != new_text:
				self.manager.note = new_text
				self.manager.is_modified = True
				self.dataChanged.emit()

class ContentNavigator(QWidget):
	"""Отображает список разделов текущей ведомости с возможностью перехода по клику."""
	sectionSelected = pyqtSignal(int)  # сигнал: индекс раздела в менеджере

	def __init__(self, parent=None):
		super().__init__(parent)
		self.manager = None
		self.setup_ui()

	def setup_ui(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)

		self.list_widget = QListWidget()
		self.list_widget.setAlternatingRowColors(True)
		self.list_widget.setWordWrap(True)
		self.list_widget.itemClicked.connect(self.on_item_clicked)
		layout.addWidget(self.list_widget)

	def set_manager(self, manager):
		"""Загружает разделы из менеджера."""
		self.manager = manager
		self.refresh()

	def refresh(self):
		"""Обновляет список разделов."""
		self.list_widget.clear()
		if not self.manager:
			return
		for idx, section in enumerate(self.manager.sections):
			item = QListWidgetItem(section.name or f"Раздел {idx+1}")
			item.setData(Qt.ItemDataRole.UserRole, idx)  # сохраняем индекс раздела
			self.list_widget.addItem(item)

	def on_item_clicked(self, item):
		"""Обрабатывает клик по разделу."""
		section_idx = item.data(Qt.ItemDataRole.UserRole)
		if section_idx is not None:
			self.sectionSelected.emit(section_idx)

	def clear(self):
		"""Очищает список."""
		self.manager = None
		self.list_widget.clear()



class Analysator(QWidget):
	""" Собирает информацию при ручном запуске для текущей ведомости """
	def __init__(self, manager = None, parent=None):
		super().__init__(parent)
		self.manager: BoQ_manager = manager
		self.setup_ui()

	def setup_ui(self):
		layout = QVBoxLayout(self)

		btn = QPushButton('Анализировать')
		btn.clicked.connect(self.start_analyses)
		layout.addWidget(btn)

		self.toolbox = QToolBox()

		self.invalid_quantities_list = QListWidget()
		self.toolbox.addItem(self.invalid_quantities_list, 'Невалидные значения')

		self.incorrect_positions_list = QListWidget()
		self.toolbox.addItem(self.incorrect_positions_list, 'Не осметченные позиции')

		self.error_link_positions_list = QListWidget()
		self.toolbox.addItem(self.error_link_positions_list, 'Невалидные ссылки')

		self.nonlink_positions_list = QListWidget()
		self.toolbox.addItem(self.nonlink_positions_list, 'Пустые ссылки')

		layout.addWidget(self.toolbox)


	def set_manager(self, manager):
		self.manager = manager
		# чтобы не терять данные при каждом действии с представлением
		# self.invalid_quantities_list.clear()
		# self.incorrect_positions_list.clear()
		# self.error_link_positions_list.clear()
		# self.nonlink_positions_list.clear()

	def clear(self):
		self.manager = None
		
		self.invalid_quantities_list.clear()
		self.incorrect_positions_list.clear()
		self.error_link_positions_list.clear()
		self.nonlink_positions_list.clear()

	def start_analyses(self):
		""" Заполняет адресами вкладки тулбокса """
		if not self.manager:
			return
		
		self.invalid_quantities_list.clear()
		self.incorrect_positions_list.clear()
		self.error_link_positions_list.clear()
		self.nonlink_positions_list.clear()

		data = self.manager.data_validation
		invalid_quantities = data.get('invalid_quantities')
		incorrect_positions = data.get('incorrect_positions')
		error_link_positions = data.get('error_link_positions')
		nonlink_positions = data.get('nonlink_positions')

		if invalid_quantities:
			self.toolbox.setItemText(0, f'Невалидные значения: {len(invalid_quantities)} шт.')
			for adr in invalid_quantities:
				self.invalid_quantities_list.addItem(QListWidgetItem(adr))
		else:
			self.toolbox.setItemText(0, 'Невалидные значения')
		if incorrect_positions:
			self.toolbox.setItemText(1, f'Не осметченные позиции: {len(incorrect_positions)} шт.')
			for adr in incorrect_positions:
				self.incorrect_positions_list.addItem(QListWidgetItem(adr))
		else:
			self.toolbox.setItemText(1, 'Не осметченные позиции')
		if error_link_positions:
			self.toolbox.setItemText(2, f'Невалидные ссылки: {len(error_link_positions)} шт.')
			for adr in error_link_positions:
				self.error_link_positions_list.addItem(QListWidgetItem(adr))
		else:
			self.toolbox.setItemText(2, 'Невалидные ссылки')
		if nonlink_positions:
			self.toolbox.setItemText(3, f'Пустые ссылки: {len(nonlink_positions)} шт.')
			for adr in nonlink_positions:
				self.nonlink_positions_list.addItem(QListWidgetItem(adr))
		else:
			self.toolbox.setItemText(3, 'Пустые ссылки')
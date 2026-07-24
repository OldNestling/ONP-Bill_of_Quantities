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
	QWidget, QVBoxLayout, QHBoxLayout, QStyledItemDelegate, QMenu, QApplication,
	QPushButton, QTextEdit,	QStyle, QTreeView, QMessageBox,QComboBox, QLineEdit, 
	QLabel, QSplitter, QAbstractItemDelegate
)
from PyQt6.QtCore import Qt, QSize, QItemSelectionModel, QEvent
from PyQt6.QtGui import (
	QStandardItemModel, QStandardItem, QColor, QTextDocument, QTextCursor, 
	QTextCharFormat, QTextBlockFormat, QBrush
)

from Core.UserLibs import Library, Group, MainElement, SubElement
from Core.Project import Project
from ..ui_utilities import create_separator, Requestion
from ..icons import Icons

class User_Libs_Tab(QWidget):
	""" Вкладка управления пользовательскими данными """
	def __init__(self, project: Project):
		super().__init__()
		self.project = project
		self.manager = project.libraries_manager if project else None
		self.current_lib_index = None
		self.non_set = {'',' ','-', None, 'None','...', '.'}
		self.setup_ui()
		self.update_ui()

	def setup_ui(self):
		self.main_layout = QHBoxLayout(self)

		# -------------------------- Левая бокова панель --------------------------------

		# Левая панель с инструментами управления библиотеками
		self.control_panel = QVBoxLayout()

		# Селектор выбора текущей пользовательской библиотеки
		self.lib_selector = QComboBox()
		self.lib_selector.setStyleSheet(""" 
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
		self.lib_selector.currentIndexChanged.connect(self.on_lib_selected)
		self.control_panel.addWidget(self.lib_selector)	

		# --- Элементы взаимодействия с библиотеками ---

		libs_buttons = QHBoxLayout()
		self.btn_add_lib = QPushButton('Создать\nбиблиотеку')
		self.btn_add_lib.clicked.connect(self.add_lib)

		self.btn_remove_lib = QPushButton('Удалить\nбиблиотеку')
		self.btn_remove_lib.clicked.connect(self.remove_lib)

		libs_buttons.addWidget(self.btn_add_lib)
		libs_buttons.addWidget(self.btn_remove_lib)
		self.control_panel.addLayout(libs_buttons)

		# Поле ввода (редактирования) имени библиотеки
		self.control_panel.addWidget(QLabel('Наименование библиотеки:'))
		self.lib_name_edit = QLineEdit()
		self.lib_name_edit.textChanged.connect(self.set_lib_name)
		self.control_panel.addWidget(self.lib_name_edit)

		# Поле ввода (редактирования) псевдонима библиотеки
		self.control_panel.addWidget(QLabel('Псевдоним библиотеки:'))
		self.lib_alias_edit = QLineEdit()
		self.lib_alias_edit.textChanged.connect(self.set_lib_alias)
		self.control_panel.addWidget(self.lib_alias_edit)

		self.control_panel.addWidget(create_separator())	# ---

		self.control_panel.addWidget(QLabel('Статус:'))
		self.status_label  = QLabel('Чтение')
		self.control_panel.addWidget(self.status_label)

		self.btn_edit_libs = QPushButton('Редактировать')
		self.btn_edit_libs.setIcon(Icons.unlock)
		self.btn_edit_libs.clicked.connect(self.toggle_edit_mode)
		self.control_panel.addWidget(self.btn_edit_libs)

		self.control_panel.addWidget(create_separator())	# ---

		# --- Кнопки манипуляции элементами ---

		#self.control_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
		self.btn_create_group = QPushButton("Создать группу")
		self.btn_create_group.clicked.connect(self.add_group)

		self.btn_create_main = QPushButton("Создать позицию")
		self.btn_create_main.clicked.connect(self.add_main_position)

		self.btn_create_sub = QPushButton("Добавить подпозицию")
		self.btn_create_sub.clicked.connect(self.add_subposition)

		self.btn_save = QPushButton("Сохранить")
		self.btn_save.clicked.connect(self.save_library)

		btn_reload = QPushButton("Перезагрузить")
		btn_reload.clicked.connect(self.reload_library)

		self.btn_delete = QPushButton("Удалить")
		self.btn_delete.clicked.connect(self.remove_position)

		self.btn_move_up = QPushButton('⮝')
		self.btn_move_up.setMaximumWidth(25)
		self.btn_move_up.clicked.connect(self.move_up_obj)

		self.btn_move_down = QPushButton('⮟')
		self.btn_move_down.setMaximumWidth(25)
		self.btn_move_down.clicked.connect(self.move_down_obj)

		self.control_panel.addWidget(self.btn_create_group)
		self.control_panel.addWidget(self.btn_create_main)
		self.control_panel.addWidget(self.btn_create_sub)
		self.control_panel.addWidget(self.btn_save)
		self.control_panel.addWidget(btn_reload)
		self.control_panel.addWidget(self.btn_delete)
		self.control_panel.addWidget(self.btn_move_up)
		self.control_panel.addWidget(self.btn_move_down)
		self.control_panel.setAlignment(self.btn_move_up, Qt.AlignmentFlag.AlignCenter)
		self.control_panel.setAlignment(self.btn_move_down, Qt.AlignmentFlag.AlignCenter)

		self.control_panel.addStretch()

		# --------------------------------- Таблица -------------------------------------
		self.tree_view = QTreeView()

		self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.tree_view.customContextMenuRequested.connect(self.on_tree_context_menu)
		self.tree_view.setWordWrap(True)
		self.tree_view.setUniformRowHeights(False)
		self.tree_view.setSelectionBehavior(QTreeView.SelectionBehavior.SelectItems)
		self.tree_view.setEditTriggers(QTreeView.EditTrigger.DoubleClicked |
										QTreeView.EditTrigger.EditKeyPressed)
		self.tree_view.setItemDelegate(UserLibsItemDelegate(self.tree_view))
		
		# Настройка заголовков
		header = self.tree_view.header()
		font = header.font()
		font.setBold(True)
		header.setFont(font)
		header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
		header.sectionResized.connect(self.on_section_resized)

		# Ширина столбцов
		self.apply_column_widths()


		header.setStretchLastSection(False)
		
		# Библиотека будет задана позже
		self.model = User_Libs_Model(self, None)
		self.tree_view.setModel(self.model)

		control_widget = QWidget()
		control_widget.setLayout(self.control_panel)
		v_splitter = QSplitter(Qt.Orientation.Horizontal)
		v_splitter.addWidget(control_widget)
		v_splitter.addWidget(self.tree_view)
		v_splitter.setSizes([300, 600])
		v_splitter.setStretchFactor(0, 0)		# редактор не растягивается
		v_splitter.setStretchFactor(1, 1)		# таблица забирают всё свободное место
		self.main_layout.addWidget(v_splitter)

		# Изначально отключаем кнопки манипуляции
		self.set_manipulation_buttons_enabled(False)

	# ------------------------------ Обновление UI ------------------------------------

	def apply_column_widths(self):
		"""Применяет заданные ширины столбцов."""
		columns_width = {0: 150, 1: 200, 2: 100, 3: 250, 4: 250, 5: 100, 6: 200, 7: 200}
		for col, width in columns_width.items():
			self.tree_view.setColumnWidth(col, width)
		# Чтобы последний столбец не растягивался, можно установить stretchLastSection(False)
		self.tree_view.header().setStretchLastSection(False)

	def set_manipulation_buttons_enabled(self, enabled):
		"""Включает/отключает кнопки добавления/удаления/перемещения."""
		for btn in (self.btn_create_group, self.btn_create_main, self.btn_create_sub,
					self.btn_delete, self.btn_move_up, self.btn_move_down,
					self.btn_save, self.btn_add_lib, self.btn_remove_lib):
			btn.setEnabled(enabled)
		self.btn_edit_libs.setEnabled(not enabled)
		self.btn_edit_libs.setIcon(Icons.unlock if enabled else Icons.lock)

	def on_section_resized(self, logical_index, old_size, new_size):
		# Принудительно пересчитываем геометрию всех строк
		self.tree_view.scheduleDelayedItemsLayout()
		self.tree_view.viewport().update()
				

	def update_ui(self):
		"""Обновляет интерфейс: комбобокс и дерево."""
		self.update_lib_selector()
		self.update_status()
		self.update_tree_view()
		self.update_lib_editor_fields()
		self.model.populate_model()
		self.tree_view.expandAll()
		self.apply_column_widths()
		self.tree_view.scheduleDelayedItemsLayout()
		self.tree_view.viewport().update()

	def update_lib_selector(self):
		"""Заполняет комбобокс списком библиотек."""
		self.lib_selector.blockSignals(True)
		self.lib_selector.clear()
		if self.manager:
			libs_data = self.manager.get_libs_list() 
			for lib in libs_data:
				self.lib_selector.addItem(lib.get('name', ''), lib.get('lib'))
		self.lib_selector.blockSignals(False)
		if self.manager and self.manager.libraries:
			if isinstance(self.current_lib_index, int):
				self.lib_selector.setCurrentIndex(self.current_lib_index)
			else:	
				self.lib_selector.setCurrentIndex(0)

	def update_tree_view(self):
		"""Пересоздаёт модель для текущей библиотеки."""
		if self.manager and self.manager.libraries:
			current_lib = self.lib_selector.currentData()
			if current_lib:
				self.model.set_lib(current_lib)
			else:
				self.model.library = None
				self.model.populate_model()
		else:
			self.model.populate_model()


	def update_lib_editor_fields(self):
		"""Обновляет поля ввода имени и псевдонима текущей библиотеки."""
		lib: Library = self.lib_selector.currentData()
		if lib:
			self.lib_name_edit.setText(lib.name)
			self.lib_alias_edit.setText(lib.alias_key)
		else:
			self.lib_name_edit.clear()
			self.lib_alias_edit.clear()

	def set_project(self, project: Project):
			self.project = project
			self.manager = self.project.libraries_manager if project else None
			if self.manager.libraries:
				self.model.set_lib(self.manager.libraries[0])
			self.update_ui()

	def _get_selected_item_path(self) -> tuple | None:
		"""Возвращает кортеж (type, group_index, main_index, sub_index) или None."""
		selected = self.tree_view.selectionModel().selectedIndexes()
		if not selected:
			return None
		index = selected[0]
		model = index.model()
		if model is None:
			return None
		item = model.itemFromIndex(index)
		if item is None:
			return None
		parent = item.parent()
		if parent is None:
			return ('Group', item.row(), None, None)
		grand = parent.parent()
		if grand is None:
			return ('MainElement', parent.row(), item.row(), None)
		else:
			return ('SubElement', grand.row(), parent.row(), item.row())

	def _select_tree_row_by_path(self, path):
		"""Выделяет строку в дереве по пути (type, group_index, main_index, sub_index)."""
		typ, group_idx, main_idx, sub_idx = path
		model = self.tree_view.model()
		if model is None:
			return
		if typ == 'Group':
			index = model.index(group_idx, 0)
			if index.isValid():
				self.tree_view.setCurrentIndex(index)
				self.tree_view.selectionModel().select(index, QItemSelectionModel.SelectionFlag.ClearAndSelect)
		elif typ == 'MainElement':
			group_item = model.item(group_idx, 0)
			if group_item:
				main_item = group_item.child(main_idx, 0)
				if main_item:
					idx = model.indexFromItem(main_item)
					self.tree_view.setCurrentIndex(idx)
					self.tree_view.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)
		elif typ == 'SubElement':
			group_item = model.item(group_idx, 0)
			if group_item:
				main_item = group_item.child(main_idx, 0)
				if main_item:
					sub_item = main_item.child(sub_idx, 0)
					if sub_item:
						idx = model.indexFromItem(sub_item)
						self.tree_view.setCurrentIndex(idx)
						self.tree_view.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)

	# ---------------------------- Обработчики комбобокса ----------------------------

	def on_lib_selected(self, index):
		"""Срабатывает при выборе другой библиотеки."""
		self.current_lib_index = index
		self.update_tree_view()
		self.update_lib_editor_fields()
		self.apply_column_widths()
		self.tree_view.scheduleDelayedItemsLayout()
		self.tree_view.viewport().update()

	# ---------------------------- Редактирование библиотеки -------------------------
	def set_lib_name(self):
		"""Обновляет имя текущей библиотеки."""
		lib: Library = self.lib_selector.currentData()
		if not lib:
			return
		new_name = self.lib_name_edit.text().strip()
		if new_name and new_name not in self.non_set:
			lib.name = new_name
			# Обновляем элемент в комбобоксе
			idx = self.lib_selector.currentIndex()
			self.lib_selector.setItemText(idx, new_name)


	def set_lib_alias(self):
		"""Обновляет псевдоним текущей библиотеки."""
		lib = self.lib_selector.currentData()
		if not lib:
			return
		new_alias = self.lib_alias_edit.text().strip()
		if new_alias and new_alias not in self.non_set:
			lib.alias_key = new_alias
	
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

	# --------------------------------- Слоты -------------------------------------------

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

	def add_lib(self):
		"""Создаёт новую библиотеку."""
		if not self.manager:
			return
		self.manager.create_lib()
		new_lib = self.manager.libraries[-1]

		# Выбираем новую библиотеку
		self.lib_selector.addItem(new_lib.name, new_lib)
		self.lib_selector.setCurrentIndex(-1)
		self.model.set_lib(new_lib)
		self.update_ui()
		# Включаем редактирование для переименования
		self.lib_name_edit.setFocus()
		self.lib_name_edit.selectAll()
	
	def remove_lib(self):
		"""Удаляет текущую библиотеку с подтверждением."""
		if not self.manager:
			print(f'[DEBUG: not self.manager]')
			return
		
		lib: Library = self.lib_selector.currentData()

		if not lib:
			print(f'[DEBUG: not lib]')
			return
		
		reply = Requestion.ask(
			self,
			'Удаление библиотеки',
			f'Вы уверены, что хотите удалить библиотеку "{lib.name}"?',
			with_cancel= False
		)

		if reply == QMessageBox.StandardButton.Yes:
			idx = self.lib_selector.currentIndex()
			if self.current_lib_index == idx:
				if self.current_lib_index > 0:
					self.current_lib_index -= 1	# селектор обновится в своём методе
				else:
					self.current_lib_index = None
			self.manager.remove_lib(idx)
			self.update_ui()

	def add_group(self):
		"""Создаёт новую группу в текущей библиотеке."""
		if not self.manager:
			return
		lib = self.lib_selector.currentData()
		if not lib:
			return
		lib.create_group()
		self.update_ui()
		new_idx = len(lib.groups) - 1
		self._select_tree_row_by_path(('Group', new_idx, None, None))


	def add_main_position(self):
		"""Создаёт новую основную позицию в текущей группе."""
		if not self.manager:
			return
		path = self._get_selected_item_path()
		if not path:
			return
		typ, group_idx, main_idx, sub_idx = path
		lib = self.lib_selector.currentData()
		if not lib:
			return
		if typ == 'Group':
			group = lib.groups[group_idx]
		elif typ in ('MainElement', 'SubElement'):
			group = lib.groups[group_idx]
		else:
			return
		group.create_main_element(name='Новая позиция', alias='Новый_Псевдоним', work_text='', resource_text='', factor='', note1='', note2='')
		self.update_ui()
		new_idx = len(group.main_elements) - 1
		self._select_tree_row_by_path(('MainElement', group_idx, new_idx, None))

	def add_subposition(self):
		"""Добавляет подпозицию к текущему основному элементу."""
		if not self.manager:
			return
		path = self._get_selected_item_path()
		if not path:
			return
		typ, group_idx, main_idx, sub_idx = path
		lib = self.lib_selector.currentData()
		if not lib:
			return
		if typ == 'MainElement':
			main_el = lib.groups[group_idx].main_elements[main_idx]
		elif typ == 'SubElement':
			main_el = lib.groups[group_idx].main_elements[main_idx]
		else:
			QMessageBox.information(self, 'Добавление подпозиции', 'Выберите основную позицию или подпозицию.')
			return
		main_el.create_sub_element(name='Новая подпозиция', alias='new_sub', resource_text='', factor='', note1='', note2='')
		self.update_ui()
		new_idx = len(main_el.sub_elements) - 1
		self._select_tree_row_by_path(('SubElement', group_idx, main_idx, new_idx))

	def remove_position(self):
			"""Удаляет выбранный элемент (группу, основную позицию или подпозицию)."""
			if not self.manager:
				return
			path = self._get_selected_item_path()
			if not path:
				return
			typ, group_idx, main_idx, sub_idx = path
			lib = self.lib_selector.currentData()
			if not lib:
				return
			reply = Requestion.ask(
				self,
				'Удаление элемента',
				'Вы уверены, что хотите удалить выбранный элемент?',
				with_cancel=False
			)
			if reply != QMessageBox.StandardButton.Yes:
				return
			if typ == 'Group':
				if 0 <= group_idx < len(lib.groups):
					lib.remove_group(group_idx)
			elif typ == 'MainElement':
				if 0 <= group_idx < len(lib.groups):
					group = lib.groups[group_idx]
					if 0 <= main_idx < len(group.main_elements):
						group.remove_main_element(main_idx)
			elif typ == 'SubElement':
				if 0 <= group_idx < len(lib.groups):
					group = lib.groups[group_idx]
					if 0 <= main_idx < len(group.main_elements):
						main_el = group.main_elements[main_idx]
						if 0 <= sub_idx < len(main_el.sub_elements):
							main_el.remove_sub_element(sub_idx)
			self.update_ui()

	def save_library(self):
		""" Сохраняет данные пользовательских библиотек и снимает блокировку """
		if not self.manager:
			return
		res = self.manager.save_libs()
		if not res:
			QMessageBox.warning(self, 'Сохранение',
									f'Не удалось сохранить данные')
		self.set_manipulation_buttons_enabled(False)
		self.model.togle_acces(False)
		self.manager.load_libs()
		self.update_ui()
	
	def reload_library(self):
		""" Перезагружает данные из файла без сохранения """
		self.set_manipulation_buttons_enabled(False)
		self.model.togle_acces(False)
		self.manager.load_libs()
		self.manager.unlock()
		self.update_ui()

	def _move_obj(self, direction):
		"""Перемещает выбранный объект на direction позиций (1 или -1)."""
		if not self.manager:
			return
		path = self._get_selected_item_path()
		if not path:
			return
		typ, group_idx, main_idx, sub_idx = path
		lib: Library = self.lib_selector.currentData()
		if not lib:
			return
		if typ == 'Group':
			new_index = group_idx + direction
			if 0 <= new_index < len(lib.groups):
				lib.move_group(group_idx, new_index)
				self.update_ui()
				self._select_tree_row_by_path(('Group', new_index, None, None))
		elif typ == 'MainElement':
			group = lib.groups[group_idx]
			new_index = main_idx + direction
			if 0 <= new_index < len(group.main_elements):
				group.move_main_element(main_idx, new_index)
				self.update_ui()
				self._select_tree_row_by_path(('MainElement', group_idx, new_index, None))
		elif typ == 'SubElement':
			group = lib.groups[group_idx]
			main_el = group.main_elements[main_idx]
			new_index = sub_idx + direction
			if 0 <= new_index < len(main_el.sub_elements):
				main_el.move_sub_element(sub_idx, new_index)
				self.update_ui()
				self._select_tree_row_by_path(('SubElement', group_idx, main_idx, new_index))

	def move_up_obj(self):
		self._move_obj(-1)

	def move_down_obj(self):
		self._move_obj(1)
	# ----------------------------- Контекстное меню ------------------------------------

	def on_tree_context_menu(self, pos):
		"""Обработчик контекстного меню для дерева."""
		index = self.tree_view.indexAt(pos)
		if not index.isValid():
			return
		col = index.column()
		if col < 3 or col > 7:
			return
		cell_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
		tooltip = index.data(Qt.ItemDataRole.ToolTipRole)
		menu = QMenu(self)
		action_copy_value = menu.addAction('Копировать')
		action_copy_value.triggered.connect(lambda: self._copy_to_clipboard(cell_text))
		action_copy_link = menu.addAction("Копировать ссылку")
		if tooltip:
			action_copy_link.triggered.connect(lambda: self._copy_to_clipboard(f'@{tooltip}'))
		else:
			action_copy_link.setEnabled(False)
		menu.exec(self.tree_view.viewport().mapToGlobal(pos))

	def _copy_to_clipboard(self, text):
		clipboard = QApplication.clipboard()
		clipboard.setText(text)



class User_Libs_Model(QStandardItemModel):
	""" Модель данных с иерархической структурой """
	HEADERS = [
		'№',																#0
		'Наименование группы/\nосновной позиции/\nдопонительной позиции',	#1
		'Псевдоним',														#2
		'Описание позиции\nработы',											#3
		'Описание позиции\nресурса',										#4
		'Расход\nресурса',													#5
		'Примечание №1',													#6
		'Примечание №2',													#7
	]
	def __init__(self, parent, library):
		super().__init__(parent)
		self.library: Library = library
		self.access = False

		self.setColumnCount(len(self.HEADERS))
		self.setHorizontalHeaderLabels(self.HEADERS)
		if self.library:
			self.populate_model()
		
		self.dataChanged.connect(self.on_data_changed)

	def set_lib(self, library: Library):
		self.library = library
		self.populate_model()
	
	def togle_acces(self, editable):
		""" Переключает доступность модели для редактирования """
		self.access = editable

	def flags(self, index):
		default_flags = super().flags(index)
		if not self.access:
			default_flags &= ~Qt.ItemFlag.ItemIsEditable
		return default_flags

	def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
		if not self.access:
			return False
		return super().setData(index, value, role)

	def populate_model(self):
		if not isinstance(self.library, Library):
			self.clear()
			return
		
		self.clear()
		self.setHorizontalHeaderLabels(self.HEADERS)

		for i, group in enumerate(self.library.groups, 1):
			row_items = [QStandardItem() for _ in range(len(self.HEADERS))]
			row_items[0] = QStandardItem(str(i))
			row_items[1] = QStandardItem(group.name)
			row_items[2] = QStandardItem(group.alias_key)
			self.appendRow(row_items)

			# Для родительской строки: фон и отключение редактирования в столбцах 3..7
			for col in range(3, 8):
				row_items[col].setFlags(
					row_items[col].flags() & ~Qt.ItemFlag.ItemIsEditable
				)
			
			for col in range(0, 8):
				row_items[col].setBackground(QColor('#5FADC0'))
			
			# Дочерние слои
			for n, main_element in enumerate(group.main_elements, 1):
				main_element: MainElement
				main_element_items = [
					QStandardItem(str(n)),						# 0
					QStandardItem(main_element.name), 			# 1
					QStandardItem(main_element.alias_key),		# 2
					QStandardItem(main_element.work_text),		# 3
					QStandardItem(main_element.resource_text),	# 4
					QStandardItem(main_element.factor),			# 5
					QStandardItem(main_element.note1),			# 6
					QStandardItem(main_element.note2)			# 7
				]
				# Подсказки для обращения
				main_element_items[3].setToolTip(main_element.alias_work)
				main_element_items[4].setToolTip(main_element.alias_resource)
				main_element_items[5].setToolTip(main_element.alias_factor)
				main_element_items[6].setToolTip(main_element.alias_note1)
				main_element_items[7].setToolTip(main_element.alias_note2)

				row_items[0].appendRow(main_element_items)

				# Дополнительные ресурсы (если есть)
				for s, sub_el in enumerate(main_element.sub_elements, 1):
					sub_elements_items = [
						QStandardItem(f'{n}.{s}'),					# 0
						QStandardItem(sub_el.name), 				# 1
						QStandardItem(sub_el.alias_key),			# 2
						QStandardItem(),							# 3
						QStandardItem(sub_el.resource_text),		# 4
						QStandardItem(sub_el.factor),				# 5
						QStandardItem(sub_el.note1),				# 6
						QStandardItem(sub_el.note2)					# 7
					]
					sub_elements_items[3].setFlags(
						row_items[3].flags() & ~Qt.ItemFlag.ItemIsEditable
					)
				# Подсказки для обращения
					sub_elements_items[4].setToolTip(sub_el.alias_resource)
					sub_elements_items[5].setToolTip(sub_el.alias_factor)
					sub_elements_items[6].setToolTip(sub_el.alias_note1)
					sub_elements_items[7].setToolTip(sub_el.alias_note2)

					main_element_items[0].appendRow(sub_elements_items)
	
	def on_data_changed(self,  topLeft, bottomRight, roles):
		if not self.library:
			return
		
		if not self.access:
			return
		
		def __compare_column(
				obj: Group | MainElement | SubElement, 
				col: int, 
				new_text: str
			):
			""" Сопоставляет столбец и атрибут переданного объекта """
			if col == 1:
				obj.name = new_text
			elif col == 2:
				obj.alias_key = new_text
			elif col == 3 and not isinstance(obj, Group):
				if hasattr(obj, 'work_text'):
					obj.work_text = new_text
			elif col == 4 and not isinstance(obj, Group):
				obj.resource_text = new_text
			elif col == 5 and not isinstance(obj, Group):
				obj.factor = new_text
			elif col == 6 and not isinstance(obj, Group):
				obj.note1 = new_text
			elif col == 7 and not isinstance(obj, Group):
				obj.note2 = new_text

		for row in range(topLeft.row(), bottomRight.row()+1):
			for col in range(topLeft.column(), bottomRight.column()+1):
				index = self.index(row, col, topLeft.parent())
				if not index.isValid():
					continue
				item = self.itemFromIndex(index)
				if not item:
					continue
				new_text = item.text()
				path = self._get_path_from_item(item)
				if not path:
					continue
				typ, group_index, main_element_index, sub_element_index = path

				match typ:			# Обновляем в зависимости от типа и колонки
					case 'Group':
						group: Group = self.library.groups[group_index]
						__compare_column(group, col, new_text)
					case 'MainElement':
						group: Group = self.library.groups[group_index]
						main_element: MainElement = group.main_elements[main_element_index]
						__compare_column(main_element, col, new_text)
					case 'SubElement':
						group: Group = self.library.groups[group_index]
						main_element: MainElement = group.main_elements[main_element_index]
						sub_element: SubElement = main_element.sub_elements[sub_element_index]
						__compare_column(sub_element, col, new_text)	
				if col == 2:
					self._update_tooltips(group_index)			

	def _get_path_from_item(self, item):
		if item is None:
			return None
		parent = item.parent()
		if parent is None:
			return ('Group', item.row(), None, None)
		else:
			grand = parent.parent()
			if grand is None:
				return ('MainElement', parent.row(), item.row(), None)
			else:
				return ('SubElement', grand.row(), parent.row(), item.row())
			
	def _update_tooltips(self, group_index):
		""" Обновить tooltips для всех элементов указанной группы """
		group_item = self.item(group_index, 0)
		if not group_item:
			return
		group: Group = self.library.groups[group_index]
		for n, main_element in enumerate(group.main_elements):
			main_element_item = group_item.child(n, 0)
			if not main_element_item:
				continue
			self._set_element_tooltips(main_element_item, main_element)
			for s, sub_el in enumerate(main_element.sub_elements):
				sub_item = main_element_item.child(s, 0)
				if sub_item: self._set_element_tooltips(sub_item, sub_el)

	def _set_element_tooltips(self, item: QStandardItem, element: MainElement):
		""" Установить tooltips для всех столбцов строки основного элемента """
		parent = item.parent()
		row = item.row()
		for col in range(3, 8):
			col_item = parent.child(row, col)
			if not col_item:
				continue
			tip = '#ОШИБКА'
			if col == 3:
				if isinstance(element, SubElement):
					tip = ""
				else:
					tip = element.alias_work
			elif col == 4:
				tip = element.alias_resource
			elif col == 5:
				tip = element.alias_factor
			elif col == 6:
				tip = element.alias_note1
			elif col == 7:
				tip = element.alias_note2

			col_item.setToolTip(tip)



class UserLibsItemDelegate(QStyledItemDelegate):
	"""
	Делегат для QTreeView с моделью User_Libs_Model.
	Поддерживает:
	  - Перенос текста по словам и автоматическую высоту строки.
	  - Редактирование через QTextEdit (многострочный ввод).
	  - Жирный шрифт для групп (столбец 1).
	  - Выравнивание по центру для столбца 0 (№).
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.margin = 4

	# ----------------------------------------------------------------------
	# Отрисовка и размер
	# ----------------------------------------------------------------------

	def paint(self, painter, option, index):
		if not index.isValid():
			return

		# ------ Фон ------
		selected = option.state & QStyle.StateFlag.State_Selected
		if selected:
			bg_color = option.palette.highlight().color()
		else:
			bg_variant = index.data(Qt.ItemDataRole.BackgroundRole)
			if bg_variant is not None:
				if isinstance(bg_variant, QBrush):
					bg_color = bg_variant.color()
				elif isinstance(bg_variant, QColor):
					bg_color = bg_variant
				else:
					bg_color = option.palette.base().color()
			else:
				bg_color = option.palette.base().color()
		painter.fillRect(option.rect, bg_color)

		# ------ Текст ------
		value = index.data(Qt.ItemDataRole.DisplayRole)
		text = str(value) if value is not None else ""

		doc = QTextDocument()
		# Шрифт: жирный для групп в столбце 1 (наименование)
		font = option.font
		if index.column() == 1 and not index.parent().isValid():
			font.setBold(True)
		doc.setDefaultFont(font)

		doc.setPlainText(text)

		# Ширина документа с учётом отступов
		text_width = option.rect.width() - 2 * self.margin
		if text_width < 1:
			text_width = 1
		doc.setTextWidth(text_width)

		# Цвет текста: для выделения используем highlightText, иначе стандартный
		if selected:
			color = option.palette.highlightedText().color()
		else:
			color = option.palette.text().color()

		cursor = QTextCursor(doc)
		cursor.select(QTextCursor.SelectionType.Document)
		fmt = QTextCharFormat()
		fmt.setForeground(color)
		cursor.mergeCharFormat(fmt)

		# Выравнивание по центру для столбца 0 (№)
		if index.column() in (0, 2, 5):
			block_fmt = QTextBlockFormat()
			block_fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
			cursor = QTextCursor(doc)
			cursor.select(QTextCursor.SelectionType.Document)
			cursor.mergeBlockFormat(block_fmt)

		# Рисуем текст
		painter.translate(option.rect.x() + self.margin, option.rect.y() + self.margin)
		doc.drawContents(painter)
		painter.translate(-option.rect.x() - self.margin, -option.rect.y() - self.margin)

		# ------ Тонкая сетка ------
		painter.setPen(QColor("#d0d0d0"))
		painter.drawRect(option.rect)

	def sizeHint(self, option, index):
		if not index.isValid():
			return QSize()

		value = index.data(Qt.ItemDataRole.DisplayRole)
		text = str(value) if value is not None else ""

		doc = QTextDocument()
		font = option.font
		if index.column() == 1 and not index.parent().isValid():
			font.setBold(True)
		doc.setDefaultFont(font)
		doc.setPlainText(text)

		# Получаем ширину колонки из представления, если option.rect.width() == 0
		width = option.rect.width()
		if width <= 0:
			tree_view = self.parent()
			if tree_view and isinstance(tree_view, QTreeView):
				width = tree_view.columnWidth(index.column())
			else:
				width = 100
		text_width = width - 2 * self.margin
		if text_width < 1:
			text_width = 1
		doc.setTextWidth(text_width)

		size = doc.size().toSize()
		size.setHeight(size.height() + 2 * self.margin)
		# Добавляем небольшой запас, чтобы текст не обрезался
		size.setHeight(size.height() + 2)
		return size

	# ----------------------------------------------------------------------
	# Редактирование
	# ----------------------------------------------------------------------

	def createEditor(self, parent, option, index):
		# Столбец 0 не редактируется
		if index.column() == 0:
			return None
		# Проверяем флаги модели
		if not (index.flags() & Qt.ItemFlag.ItemIsEditable):
			return None

		editor = QTextEdit(parent)
		editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
		editor.setFrameStyle(0)  # без рамки
		editor.installEventFilter(self)
		return editor

	def setEditorData(self, editor, index):
		value = index.data(Qt.ItemDataRole.EditRole)
		editor.setPlainText(str(value) if value is not None else "")

	def setModelData(self, editor, model, index):
		text = editor.toPlainText()
		model.setData(index, text, Qt.ItemDataRole.EditRole)
		# Принудительно обновляем геометрию строк
		tree_view = self.parent()
		if tree_view and isinstance(tree_view, QTreeView):
			tree_view.scheduleDelayedItemsLayout()
			tree_view.viewport().update()

	def updateEditorGeometry(self, editor, option, index):
		editor.setGeometry(option.rect)

	def eventFilter(self, obj, event):
		if isinstance(obj, QTextEdit) and event.type() == QEvent.Type.KeyPress:
			key = event.key()
			modifiers = event.modifiers()
			if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
				if modifiers == Qt.KeyboardModifier.AltModifier:
					# Alt+Enter — вставка новой строки (стандартное поведение)
					obj.insertPlainText('\n')
					return True
				else:
					# Enter без модификаторов — подтверждение и закрытие редактора
					self.commitData.emit(obj)
					self.closeEditor.emit(obj, QAbstractItemDelegate.EndEditHint.SubmitModelCache)
					return True
			elif key == Qt.Key.Key_Tab or key == Qt.Key.Key_Backtab:
				# Tab/Shift+Tab — передаём фокус следующему/предыдущему виджету
				return False
		return super().eventFilter(obj, event)
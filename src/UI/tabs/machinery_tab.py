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
	QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QTableWidget, QLabel,
	QTableWidgetItem, QHeaderView, QMenu, QApplication, QStyledItemDelegate, QComboBox)
from PyQt6.QtCore import Qt
from ..ui_utilities import create_separator
from ..icons import Icons
from Core.Machinery import Machinery_Manager, Machine

class Machinery_Tab(QWidget):
	""" Представление вкладки работы с материалами """
	def __init__(self, project):
		super().__init__()
		self.project = project
		self.manager: Machinery_Manager = project.machinery_manager if project else None    # еденичный экземпляр менеджера
		self.setup_ui()
		self.update_ui()
	
	def setup_ui(self):
		main_layout = QVBoxLayout(self) # Основной лейаут
		tbl_and_btns = QHBoxLayout() # Область таблицы и кнопок управления

		# -------------------------------------- Таблица -------------------------------------

		self.machinery_table = QTableWidget()
		self.machinery_table.verticalHeader().setVisible(False)
		self.machinery_table.setWordWrap(True) # Включение переноса текста в ячейках данных


		# Заполняем строки подзаголовков
		headers = (
			'Категория',									#0
			'Область механизации', 							#1
			'Псевдоним\n(без префикса)',					#2
			'Текст работы с использованием механизации'		#3
		)
		
		self.machinery_table.setColumnCount(len(headers))
		self.machinery_table.setHorizontalHeaderLabels(headers)

		# Установка жирного шрифта для заголовков
		header = self.machinery_table.horizontalHeader()
		font = header.font()
		font.setBold(True)
		header.setFont(font)

		column_widths = (50, 300, 100, 300) # Фиксированная ширина столбцов
		for col, width in enumerate(column_widths):
			self.machinery_table.setColumnWidth(col, width)
			# if col in (0, 1, 2):
			# 	self.machinery_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
			# else:
			self.machinery_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

		if self.manager is not None:
			self.machinery_table.setItemDelegateForColumn(0, CategoryDelegate(self.manager, self.machinery_table))

		self.machinery_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		self.machinery_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
		self.machinery_table.itemChanged.connect(self.on_table_item_changed)
		self.machinery_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.machinery_table.customContextMenuRequested.connect(self.on_table_context_menu)

		tbl_and_btns.addWidget(self.machinery_table)

	# ------------------------------------ Кнопки управления ------------------------------
		# Вертикальный layout для кнопок
		buttons_layout = QVBoxLayout()
		buttons_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

		self.btn_edit_lib = QPushButton('Редактировать\nбиблиотеку')
		self.btn_edit_lib.setIcon(Icons.unlock)
		self.btn_edit_lib.clicked.connect(self.toggle_edit_mode)

		self.btn_create = QPushButton("Создать")
		self.btn_create.clicked.connect(self.create_object)
		self.btn_save = QPushButton("Сохранить")
		self.btn_save.clicked.connect(self.save)
		self.btn_reload = QPushButton("Перезагрузить")
		self.btn_reload.clicked.connect(self.reload)
		self.btn_delete = QPushButton("Удалить")
		self.btn_delete.clicked.connect(self.remove)
		self.btn_move_up  = QPushButton('⮝')
		self.btn_move_up.setMaximumWidth(25)
		self.btn_move_up.clicked.connect(self.move_up_obj)
		self.btn_move_down  = QPushButton('⮟')
		self.btn_move_down.setMaximumWidth(25)
		self.btn_move_down.clicked.connect(self.move_down_obj)

		buttons_layout.addWidget(QLabel('Статус:'))
		self.status_label  = QLabel('Чтение')
		buttons_layout.addWidget(self.status_label)
		
		buttons_layout.addWidget(self.btn_edit_lib)

		buttons_layout.addWidget(create_separator())	# ---
		
		buttons_layout.addWidget(self.btn_create)
		buttons_layout.addWidget(self.btn_save)
		buttons_layout.addWidget(self.btn_reload)
		buttons_layout.addWidget(self.btn_delete)
		buttons_layout.addWidget(self.btn_move_up)
		buttons_layout.addWidget(self.btn_move_down)

		buttons_layout.setAlignment(self.btn_move_up, Qt.AlignmentFlag.AlignCenter)
		buttons_layout.setAlignment(self.btn_move_down, Qt.AlignmentFlag.AlignCenter)

		tbl_and_btns.addLayout(buttons_layout)
		main_layout.addLayout(tbl_and_btns)

		# Изначально отключаем кнопки манипуляции
		self.set_manipulation_buttons_enabled(False)
		self.set_table_editable(False)

	def set_manipulation_buttons_enabled(self, enabled):
		"""Включает/отключает кнопки редактирования"""
		for btn in (
			self.btn_create, self.btn_save, self.btn_delete,
			self.btn_move_up, self.btn_move_down
		):
			btn.setEnabled(enabled)
		self.btn_edit_lib.setEnabled(not enabled)
		self.btn_edit_lib.setIcon(Icons.unlock if enabled else Icons.lock)

	
	def update_status(self):
		""" Обновляет статус доступности """
		if not self.manager or not self.manager.project:
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
									f'Библиотека грунтов заблокирована пользователем {user}')
			self.update_ui()
			return
		lock_res = self.manager.lock_libs()
		self.update_status()
		if lock_res:
			self.set_manipulation_buttons_enabled(True)
			self.set_table_editable(True)
		else:
			self.set_table_editable(False)
			self.set_manipulation_buttons_enabled(False)
			QMessageBox.warning(self, 'Редактирование',
									'Не удалось заблокировать файл для других пользователей')
			
	def set_table_editable(self, editable: bool):
		if editable:
			# Разрешить редактирование
			self.machinery_table.setEditTriggers(
				QTableWidget.EditTrigger.DoubleClicked |
				QTableWidget.EditTrigger.EditKeyPressed |
				QTableWidget.EditTrigger.AnyKeyPressed 
			)
		else:
			# Запретить любое редактирование
			self.machinery_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

	def update_ui(self):
		# Обновление таблицы
		self.machinery_table.blockSignals(True)
		

		if self.manager is None:
			self.machinery_table.blockSignals(False)
			return
		
		objects = self.manager.library

		if not objects or len(objects) == 0:
			self.machinery_table.blockSignals(False)
			return
		
		self.machinery_table.setRowCount(len(objects))

		for row, obj in enumerate(objects):
			obj: Machine
			# Заполняем ячейки
			category_item = QTableWidgetItem(str(obj.category))
			category_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.machinery_table.setItem(row, 0, category_item)
			# Наименование
			name_item = QTableWidgetItem(obj.name)
			self.machinery_table.setItem(row, 1, name_item)
			# Псевдоним для обращения в среде ВОР
			alias_item = QTableWidgetItem(obj.alias)
			alias_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.machinery_table.setItem(row, 2, alias_item)
			# Работа
			work_item = QTableWidgetItem(str(obj.work))
			work_item.setToolTip(obj.alias_work)
			self.machinery_table.setItem(row, 3, work_item)

		self.machinery_table.blockSignals(False)
		self.update_status()

	def on_table_item_changed(self, item: QTableWidgetItem):
		if self.project is None:
			return
		row = item.row()
		col = item.column()

		obj: Machine = self.manager.library[row]

		if col == 0:
			obj.category = item.text()
		elif col == 1:
			obj.name = item.text()
		elif col == 2:
			obj.alias = item.text()
			self.machinery_table.item(row, 3).setToolTip(obj.alias_work)
		elif col == 3:
			obj.work = item.text()
			item.setText(obj.work)
		
	def set_project(self, project):
		"""Обновляет проект во вкладке и во всех дочерних виджетах."""
		self.project = project
		self.manager = project.machinery_manager
		if self.manager is not None:
			self.machinery_table.setItemDelegateForColumn(0, CategoryDelegate(self.manager, self.machinery_table))
		else:
			self.machinery_table.setItemDelegateForColumn(0, None)
		self.update_ui()

	def tab_selected(self):
		"""Вызывается при активации вкладки."""
		self.update_ui()
	
	# --------------------------------- Работа кнопок -----------------------------------

	def preliminary_check(self, action:str):
		"""
		Предварительная проверка корректности запроса.

		Args:
			:action (str): Описание события для окна предупреждения

		Returns:
			:False: Проверка не пройдена
			:row (int): Номер выбранной строки в таблице
		"""
		if self.manager is None:
			return None
		rows = self.machinery_table.rowCount()
		if rows == 0 or rows == None:
			return None
		
		current_row = self.machinery_table.currentRow()
		if current_row == -1:
			if action == '':
				return None
			QMessageBox.warning(self, action, "Сначала выберите строку в таблице.")
			return None
		row = current_row
		return row

	def create_object(self):
		if self.manager is not None:
			self.manager.create_object()
			self.update_ui()
	
	def save(self):
		if self.manager is not None:
			res = self.manager.save_lib()
			self.set_manipulation_buttons_enabled(False)
			if not res:
				QMessageBox.warning(self, 'Сохранение', f'Не удалось сохранить данные')
		else:
			print("Невозможно сохранить: менеджер механизации или проект не назначены")
		self.set_table_editable(False)
		self.update_ui()


	def reload(self):
		if self.manager is None:
			return
		self.manager.reload_lib()
		self.set_manipulation_buttons_enabled(False)
		self.set_table_editable(False)
		self.update_ui()

	def remove(self):
		if self.manager is None:
			return
		
		object_num = self.preliminary_check('Удаление')
		if object_num is None:
			return
		self.manager.remove_object(object_num)
		self.update_ui()

	def move_up_obj(self):
		if self.manager is None:
			return
		object_num = self.preliminary_check('')
		if object_num is not None:
			index = self.manager.move_object(object_num, -1)
		if index == object_num:
			return
		self.update_ui()
		self.machinery_table.selectRow(index)

	def move_down_obj(self):
		if self.manager is None:
			return
		object_num = self.preliminary_check('')
		if object_num is None:
			return
		index = self.manager.move_object(object_num, 1)
		if index == object_num:
			return
		self.update_ui()
		self.machinery_table.selectRow(index)

	def on_table_context_menu(self, pos):
		"""Обрабатывает контекстное меню для таблицы."""
		index = self.machinery_table.indexAt(pos)
		if not index.isValid():
			return
		row = index.row()
		col = index.column()

		menu = QMenu()
		# Для столбца примечаний (col == 3) создаём своё меню
		if col == 3:
			obj: Machine = self.manager.library[row]
			
			copy_action = menu.addAction('Копировать')
			copy_action.triggered.connect(lambda: self._copy_to_clipboard(obj.work))
			copy_link_action = menu.addAction('Копировать ссылку')
			copy_link_action.triggered.connect(lambda: self._copy_to_clipboard(f'@{obj.alias_work}'))
			
			menu.exec(self.machinery_table.viewport().mapToGlobal(pos))

	def _copy_to_clipboard(self, text):
		clipboard = QApplication.clipboard()
		clipboard.setText(text)


class CategoryDelegate(QStyledItemDelegate):
	def __init__(self, manager, parent=None):
		super().__init__(parent)
		self.manager = manager

	def createEditor(self, parent, option, index):
		combo = QComboBox(parent)
		combo.addItems(self.manager.MACHINES)
		return combo

	def setEditorData(self, editor, index):
		value = index.model().data(index, Qt.ItemDataRole.EditRole)
		if value is not None:
			editor.setCurrentText(str(value))

	def setModelData(self, editor, model, index):
		value = editor.currentText()
		model.setData(index, value, Qt.ItemDataRole.EditRole)

	def updateEditorGeometry(self, editor, option, index):
		editor.setGeometry(option.rect)

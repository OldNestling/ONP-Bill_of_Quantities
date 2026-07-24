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
	QWidget, QLabel, QPushButton, QDialog, QVBoxLayout, QHBoxLayout, 
	QPlainTextEdit, QMessageBox, QTableWidget, QTableWidgetItem, 
	QHeaderView, QComboBox, QSpinBox, QDialogButtonBox, QMenu, QApplication)
from PyQt6.QtCore import Qt
from ..ui_utilities import TableWithNotes, create_ok_cancel_buttons, Switch, create_separator
from ..icons import Icons
from Core.Sources import Sources_Manager

class Sources_Tab(QWidget):
	""" Представление вкладки работы с источниками проекта """
	def __init__(self, project):
		super().__init__()
		self.project = project
		self.manager: Sources_Manager = project.sources_manager if project else None    # еденичный экземпляр менеджера взаимодействия с источниками проекта 
		self.setup_ui()
		self.update_ui()
	
	def setup_ui(self):
		main_layout = QVBoxLayout(self) # Основной лейаут
		tbl_and_btns = QHBoxLayout() # Область таблицы и кнопок управления

		# Информация о режиме работы
		mode_layuot = QHBoxLayout()

		init_transportation = self.project.work_modes.get('transportation_mode') if self.project else False
		self.transportation_toggle = Switch(checked=init_transportation)
		self.transportation_toggle.toggled.connect(self.on_transportation_mode_toggled)

		self.work_mode_label = QLabel('<b>Режим сложного покрытия отключён</b>')
		self.work_mode_label.setMaximumWidth(300)
		mode_layuot.addWidget(self.work_mode_label)
		mode_layuot.addWidget(self.transportation_toggle)
		mode_layuot.setAlignment(self.transportation_toggle, Qt.AlignmentFlag.AlignLeft)
		main_layout.addLayout(mode_layuot)

		# -------------------------------------- Таблица -------------------------------------

		self.sources_table = TableWithNotes(self.manager, lib_type='sources_list')
		self.sources_table.setWordWrap(True) # Включение переноса текста в ячейках данных
		self.sources_table.verticalHeader().setVisible(False)

		# Скрываем стандартный горизонтальный заголовок
		self.sources_table.horizontalHeader().setVisible(False)		
		# Автоматическая высота строк (подстраивается под текст)
		self.sources_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		

		# Фиксированная ширина столбцов
		column_widths = (30, 250, 150, 100, 100, 100, 60, 200, 300, 100)
		self.sources_table.setColumnCount(len(column_widths))
		for col, width in enumerate(column_widths):
			self.sources_table.setColumnWidth(col, width)
			if col in (0, 2, 3, 4, 5, 6, 9):
				self.sources_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
			else:
				self.sources_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
		
		# Вставляем две строки для многоуровневого заголовка
		self.sources_table.insertRow(0)  # строка 0 – объединённые группы
		self.sources_table.insertRow(1)  # строка 1 – подзаголовки

		# Заполняем строку 0
		self.sources_table.setSpan(0, 3, 1, 4)  # объединяем столбцы 3–6
		item_group = self.create_bold_item("Расстояние по типу покрытия")
		self.sources_table.setItem(0, 3, item_group)

		# Заполняем строки подзаголовков
		headers = (
			'№',
			'Наименование',
			'Псевдоним',
			'Усоверш.тип покрытия',
			'Переходный тип покрытия',
			'Грунтовый тип покрытия',
			'Общее',
			'Работа',
			'Работ с учётом расстояния',
			'Примечание'
		)

		for col, text in enumerate(headers):
			item = self.create_bold_item(text)
			if col in (0, 1, 2, 7, 8, 9):
				self.sources_table.setItem(0, col, item)
				self.sources_table.setSpan(0, col, 2, 1)
			else:
				self.sources_table.setItem(1, col, item)

		self.sources_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
		self.sources_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.sources_table.customContextMenuRequested.connect(self.on_table_context_menu)
	
		tbl_and_btns.addWidget(self.sources_table)

	# ------------------------------------ Кнопки управления ------------------------------
		# Вертикальный layout для кнопок
		buttons_layout = QVBoxLayout()
		buttons_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

		self.btn_edit_lib = QPushButton('Редактировать\nбиблиотеку')
		self.btn_edit_lib.setIcon(Icons.unlock)
		self.btn_edit_lib.clicked.connect(self.toggle_edit_mode)

		self.btn_create = QPushButton("Создать")
		self.btn_create.clicked.connect(self.open_source_macker_dialog)
		self.btn_edit = QPushButton("Редактировать\nэлемент")
		self.btn_edit.clicked.connect(self.open_source_edit_dialog)
		self.btn_save = QPushButton("Сохранить")
		self.btn_save.clicked.connect(self.save_sources)
		self.btn_reload = QPushButton("Перезагрузить")
		self.btn_reload.clicked.connect(self.reload_sources)
		self.btn_delete = QPushButton("Удалить")
		self.btn_delete.clicked.connect(self.remove_source)
		self.btn_move_up  = QPushButton('⮝')
		self.btn_move_up.setMaximumWidth(25)
		self.btn_move_up.clicked.connect(self.move_up_source)
		self.btn_move_down  = QPushButton('⮟')
		self.btn_move_down.setMaximumWidth(25)
		self.btn_move_down.clicked.connect(self.move_down_source)
		
		buttons_layout.addWidget(QLabel('Статус:'))
		self.status_label  = QLabel('Чтение')
		buttons_layout.addWidget(self.status_label)
		
		buttons_layout.addWidget(self.btn_edit_lib)

		buttons_layout.addWidget(create_separator())	# ---

		buttons_layout.addWidget(self.btn_create)
		buttons_layout.addWidget(self.btn_edit)
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
	
	def set_manipulation_buttons_enabled(self, enabled):
		"""Включает/отключает кнопки редактирования"""
		for btn in (
			self.btn_create, self.btn_edit,	self.btn_save, 
			self.btn_delete, self.btn_move_up, self.btn_move_down
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

	def update_ui(self):
		# Обновление лейбла режима
		if self.project:
			self.transportation_toggle.blockSignals(True)
			work_mode = self.project.work_modes.get('transportation_mode')
			if work_mode:
				self.work_mode_label.setText('<b>Режим сложного покрытия активирован</b>')
				self.transportation_toggle.setChecked(True)
			else:
				self.work_mode_label.setText('<b>Режим сложного покрытия отключён</b>')
				self.transportation_toggle.setChecked(False)
			self.transportation_toggle.blockSignals(False)
		# Обновление таблицы
		self.sources_table.blockSignals(True)
		# Удаляем все старые строки данных (оставляем только две заголовочные)
		while self.sources_table.rowCount() > 2:
			self.sources_table.removeRow(2)
		if self.manager is None:
			self.sources_table.blockSignals(False)
			return
		
		data = self.manager.library

		if not data:
			self.sources_table.blockSignals(False)
			return
		
		line = 1
		for row, source in enumerate(data):
			self.sources_table.insertRow(2+row)   # добавляем строку на позицию 2+row
			# Заполняем ячейки
			num_source = line
			num_item = QTableWidgetItem(str(num_source))
			num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # убираем флаг редактирования
			self.sources_table.setItem(2+row, 0, num_item)
			# Наименование
			name_item = QTableWidgetItem(str(source.name))
			name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			self.sources_table.setItem(2+row, 1, name_item)
			# Псевдоним для обращения в среде ВОР
			alias_item = QTableWidgetItem(f'{source._alias}')
			alias_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			alias_item.setFlags(alias_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			self.sources_table.setItem(2+row, 2, alias_item)
			# Усоверш. тип покрытия
			advanced_coating_item = QTableWidgetItem(str(source.advanced_coating))
			advanced_coating_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			advanced_coating_item.setFlags(advanced_coating_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			self.sources_table.setItem(2+row, 3, advanced_coating_item)
			# Переходный тип покрытия
			transitional_coating_item = QTableWidgetItem(str(source.transitional_coating))
			transitional_coating_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			transitional_coating_item.setFlags(transitional_coating_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			self.sources_table.setItem(2+row, 4, transitional_coating_item)
			# Грунтовый тип покрытия
			ground_coating_item = QTableWidgetItem(str(source.ground_coating))
			ground_coating_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			ground_coating_item.setFlags(ground_coating_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			self.sources_table.setItem(2+row, 5, ground_coating_item)
			# Общее расстояние
			total_length_item = QTableWidgetItem(str(source._total_length))
			total_length_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			total_length_item.setFlags(total_length_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			self.sources_table.setItem(2+row, 6, total_length_item)
			# Работа
			work_text_item = QTableWidgetItem(source._work_text)
			work_text_item.setFlags(work_text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			work_tooltip = source.alias_work
			work_text_item.setToolTip(work_tooltip)
			self.sources_table.setItem(2+row, 7, work_text_item)
			# Работа и расстояние
			transportation_text_item = QTableWidgetItem(source.transportation_text)
			transportation_text_item.setFlags(transportation_text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			transportation_text_tooltip = source.alias_transportation
			transportation_text_item.setToolTip(transportation_text_tooltip)
			self.sources_table.setItem(2+row, 8, transportation_text_item)
			# Примечание
			note_item = QTableWidgetItem(source.note)
			note_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			note_item.setFlags(note_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			note_tooltip = source.alias_note
			note_item.setToolTip(note_tooltip)
			self.sources_table.setItem(2+row, 9, note_item)

			line += 1

		self.sources_table.blockSignals(False)
		self.update_status()

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
		self.update_ui()
		if lock_res:
			self.set_manipulation_buttons_enabled(True)
		else:
			self.set_manipulation_buttons_enabled(False)
			QMessageBox.warning(self, 'Редактирование',
									'Не удалось заблокировать файл для других пользователей')
			
	def on_table_context_menu(self, pos):
		# Получаем позицию и индекс ячейки
		index = self.sources_table.indexAt(pos)
		if not index.isValid():
			return
		row = index.row()
		col = index.column()

		# Получаем объект
		source = self.manager.library[row-2]
		if source is None:
			return
		# Для столбца с комментариями передаём обработку в TableWithNotes
		if col == 0:
			self._show_note_menu(source, pos)
			return
		
		# Текст ячейки для копирования
		cell_item = self.sources_table.item(row, col)
		cell_text = cell_item.text() if cell_item else ""

		# Создаём меню
		menu = QMenu(self)
		# Действие "Копировать значение"
		action_copy_value = menu.addAction("Копировать")
		action_copy_value.triggered.connect(lambda: self._copy_to_clipboard(cell_text))

		# Обработка колонки работы (индекс 7)
		if col in (7, 8, 9):
			if source:
				text_dict = {
					7: source.alias_work,
					8: source.alias_transportation,
					9: source.alias_note
				}
				action = menu.addAction("Копировать ссылку")
				action.triggered.connect(lambda checked, txt=text_dict[col]: self._copy_to_clipboard(f'@{txt}'))
			else:
				action = menu.addAction("Копировать ссылку")
				action.setDisabled(True)

		# Показываем меню в глобальных координатах
		menu.exec(self.sources_table.viewport().mapToGlobal(pos))

	def _copy_to_clipboard(self, text):
		clipboard = QApplication.clipboard()
		clipboard.setText(text)

	def _show_note_menu(self, source, pos):
		"""Показывает меню заметок для грунта"""
		menu = QMenu(self)
		if source.comment:
			action_edit = menu.addAction("Изменить заметку...")
			action_remove = menu.addAction("Удалить заметку")
		else:
			action_add = menu.addAction("Добавить заметку...")
		action = menu.exec(self.sources_table.viewport().mapToGlobal(pos))
		if source.comment:
			if action == action_edit:
				self._edit_comment(source)
			elif action == action_remove:
				self._set_comment(source, None)
		else:
			if action == action_add:
				self._edit_comment(source)

	def _edit_comment(self, obj):
		"""Открывает диалог редактирования примечания"""
		dialog = QDialog(self)
		dialog.setWindowTitle("Заметка")
		layout = QVBoxLayout(dialog)
		text_edit = QPlainTextEdit()
		text_edit.setPlainText(obj.comment or "")
		layout.addWidget(text_edit)
		button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
		button_box.accepted.connect(dialog.accept)
		button_box.rejected.connect(dialog.reject)
		layout.addWidget(button_box)
		if dialog.exec() == QDialog.DialogCode.Accepted:
			new_note = text_edit.toPlainText().strip()
			self._set_comment(obj, new_note if new_note else None)

	def _set_comment(self, obj, comment):
		"""Сохраняет комментарий и обновляет таблицу"""
		obj.set_comment(comment)
		self.update_ui()  # обновляем таблицу для перерисовки треугольника

	@staticmethod
	def create_bold_item(text, alignment=Qt.AlignmentFlag.AlignCenter):
		'''Создаёт ячейку заголовка с жирным текстом и выравниванием
		:text: Содержимое ячейки
		:alignment: Выравнивание
		'''
		item = QTableWidgetItem(text)
		font = item.font()
		font.setBold(True)
		item.setFont(font)
		item.setTextAlignment(alignment)
		item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
		return item

	# ----------------------------------------- Обновление проекта  -----------------------------------------
	
	def set_project(self, project):
		"""Обновляет проект во вкладке и во всех дочерних виджетах."""
		self.project = project
		self.manager = project.sources_manager
		self.sources_table.set_manager(self.manager)
		self.update_ui()

	def tab_selected(self):
		"""Вызывается при активации вкладки."""
		self.update_ui()
	
	def settings_changed(self):
		"""Вызывается при изменении настроек проекта"""
		if self.project:
			self.manager.set_work_mode()
			init_transportation = self.project.work_modes.get('transportation_mode') if self.project else False
			self.transportation_toggle.setChecked(init_transportation)
			self.update_ui
	
	# --------------------------------- Переключатель режима  ---------------------------

	def on_transportation_mode_toggled(self, checked):
		"""Обрабатывает переключение режима представления транспортировки по типу покрытия."""
		if self.project is not None:
			self.project.work_modes['transportation_mode'] = checked
			self.settings_changed()
			self.update_ui()
			print(f"Режим подробного маршрута транспортировки: {checked}")
		else:
			pass
	# ------------------------------------ Работа кнопок --------------------------------

	def preliminary_source_check(self, action:str):
		"""
		Предварительная проверка корректности запроса.

		Args:
			:action (str): Описание события для окна предупреждения

		Returns:
			:False: Проверка не пройдена
			:source_num (int): Номер ИГЭ для выбранной строки в таблице
		"""
		if self.manager is None:
			return None
		current_row = self.sources_table.currentRow()
		if current_row == -1:
			if action == '':
				return None
			QMessageBox.warning(self, action, "Сначала выберите строку в таблице.")
			return None
		if current_row == 0 or current_row == 1:
			if action != '':
				QMessageBox.warning(self, action, "Сначала выберите строку в таблице.")
			return None # Так как две первые строки это заголовок 
		row = current_row-2
		return row

	def open_source_macker_dialog(self):
		""" Создать новый объект-источник """
		if self.manager is None:
			return
		dialog = Source_Dialog(self, sources_manager=self.manager)

		if dialog.exec() == QDialog.DialogCode.Accepted:
			data = dialog.get_data()
			
			self.manager.create_source(data)
			self.update_ui()

	def open_source_edit_dialog(self):
		if self.manager is None:
			return
		
		source_num = self.preliminary_source_check('Редактирование')
		if source_num is None:
			return
		
		dialog = Source_Dialog(self, sources_manager=self.manager, edit_mode=True, num=source_num)

		if dialog.exec() == QDialog.DialogCode.Accepted:
			data = dialog.get_data()
			self.manager.edit_source(source_num, data)
			self.update_ui()

	def save_sources(self):
		if self.manager is not None:
			res = self.manager.save_lib()
			self.project.saving_settings()
			if not res:
				QMessageBox.warning(self, 'Сохранение', f'Не удалось сохранить данные')
			self.set_manipulation_buttons_enabled(False)
		else:
			print("Невозможно сохранить: менеджер источников или проект не назначены")
		self.update_ui()

	def reload_sources(self):
		if self.manager is None:
			return
		self.manager.reload_lib()
		self.set_manipulation_buttons_enabled(False)
		self.update_ui()

	def remove_source(self):
		if self.manager is None:
			return
		
		source_num = self.preliminary_source_check('Удаление')
		if source_num is None:
			return
		self.manager.remove_sorce(source_num)
		self.update_ui()

	def move_up_source(self):
		if self.manager is None:
			return
		source_num = self.preliminary_source_check('')
		if source_num is not None:
			index = self.manager.move_obj(source_num, -1)
		if index == source_num:
			return
		self.update_ui()
		self.sources_table.selectRow(index+2)

	def move_down_source(self):
		if self.manager is None:
			return
		source_num = self.preliminary_source_check('')
		if source_num is None:
			return
		index = self.manager.move_obj(source_num, 1)
		if index == source_num:
			return
		self.update_ui()
		self.sources_table.selectRow(index+2)

class Source_Dialog(QDialog):
	"""Окно создания/редактирования источника"""
	def __init__(self, parent, sources_manager, edit_mode=False, num=None):
		super().__init__(parent)
		window_name = 'Редактирования источника' if edit_mode else 'Создание источника'
		self.setWindowTitle(window_name)
		self.setModal(True)
		self.sources_manager = sources_manager # объект управления грунтами
		self.source_num = num # Данные текущего грунта для режима редактирования

		self.edit_mode = edit_mode

		self.setup_ui()

	@property
	def source(self):
		""" Возвращает объект Source """
		if self.edit_mode:
			return self.sources_manager.library[self.source_num]
		return None
	
	def setup_ui(self):
		main_layout = QVBoxLayout(self)

		# ----------------------- Поля ввода и редактирования данных --------------------
		# Наименование
		main_layout.addWidget(QLabel('Наименование источника:'))
		__name = self.source.name if self.edit_mode else ''
		self._name_edit_plane = QPlainTextEdit(__name)
		self._name_edit_plane.setMinimumHeight(100)
		self._name_edit_plane.setPlaceholderText('Укажите наименование источника')
		main_layout.addWidget(self._name_edit_plane)
		# Псевдоним
		main_layout.addWidget(QLabel('Псевдоним:'))

		self._alias_combobox = QComboBox()
		self._alias_combobox.addItems(self.sources_manager.get_aliases())
		self._alias_combobox.setEditable(True)
		
		__alias = self.source._alias if self.edit_mode else ''
		
		self._alias_combobox.setCurrentText(__alias)
		self._alias_combobox.setPlaceholderText('Укажите псевданим. Например: металл')
		main_layout.addWidget(self._alias_combobox)
		# Усоверш. тип покрытия
		main_layout.addWidget(QLabel('Протяжение усовершенствованного типа покрытия:'))
		__advanced_coating = self.source.advanced_coating if self.edit_mode else 0
		self._advanced_coating_spine_box = QSpinBox()
		self._advanced_coating_spine_box.setMinimum(0)
		self._advanced_coating_spine_box.setValue(__advanced_coating)
		main_layout.addWidget(self._advanced_coating_spine_box)
		# Переходный тип покрытия
		main_layout.addWidget(QLabel('Протяжение переходного типа покрытия:'))
		__transitional_coating = self.source.transitional_coating if self.edit_mode else 0
		self._transitional_coating_spine_box = QSpinBox()
		self._transitional_coating_spine_box.setMinimum(0)
		self._transitional_coating_spine_box.setValue(__transitional_coating)
		main_layout.addWidget(self._transitional_coating_spine_box)
		# Грунтовый тип покрытия
		main_layout.addWidget(QLabel('Протяжение грунтового типа покрытия:'))
		__ground_coating = self.source.ground_coating if self.edit_mode else 0
		self._ground_coating_spine_box = QSpinBox()
		self._ground_coating_spine_box.setMinimum(0)
		self._ground_coating_spine_box.setValue(__ground_coating)
		main_layout.addWidget(self._ground_coating_spine_box)
		# Тоннаж перевозки
		main_layout.addWidget(QLabel('Грузоподъёмность до, т:'))
		__tonnage = self.source._tonnage if self.edit_mode else 15
		self._tonnage_spine_box = QSpinBox()
		self._tonnage_spine_box.setMinimum(0)
		self._tonnage_spine_box.setValue(__tonnage)
		main_layout.addWidget(self._tonnage_spine_box)
		# Транспорт
		main_layout.addWidget(QLabel('Транспорт для перевозки:'))
		__transports_list = ['автосамосвалами', 'бортовыми автомобилями']
		__current_transport = self.source.transport if self.edit_mode else 'автосамосвалами'
		self._tranport_combo_box = QComboBox()
		self._tranport_combo_box.addItems(__transports_list)
		self._tranport_combo_box.setEditable(True)
		self._tranport_combo_box.setCurrentText(__current_transport)
		main_layout.addWidget(self._tranport_combo_box)
		# Замещение текста работы при необходимости
		main_layout.addWidget(QLabel('Замещение текста работы. (Опционально)'))
		__work_text = self.source.work_text if self.edit_mode else None
		if __work_text is None and self.source is None:
			self._work_text_edit_plane = QPlainTextEdit()
			text = f'Транспортировка {self._tranport_combo_box.currentText()} грузоподъёмностью до {self._tonnage_spine_box.value()} т'
			self._work_text_edit_plane.setPlaceholderText(text)
			self._work_text_edit_plane.setMinimumHeight(100)
		else:
			self._work_text_edit_plane = QPlainTextEdit(__work_text)
			self._work_text_edit_plane.setPlaceholderText(self.source._work_text)
			self._work_text_edit_plane.setMinimumHeight(100)
		main_layout.addWidget(self._work_text_edit_plane)
		# Подключаем обновление placeholder при изменении тонажа
		self._tonnage_spine_box.valueChanged.connect(self.update_work_text_placeholder)
		self._tranport_combo_box.currentTextChanged.connect(self.update_work_text_placeholder)
		# Примечание
		main_layout.addWidget(QLabel('Текст примечания:'))
		__note = self.source.note if self.edit_mode else ''
		self._note_edit_plane = QPlainTextEdit(__note)
		self._note_edit_plane.setPlaceholderText('Укажите текст примечания')
		self._note_edit_plane.setMinimumHeight(50)
		main_layout.addWidget(self._note_edit_plane)
		# Локальный комментарий
		main_layout.addWidget(QLabel('Локальный комментарий:'))
		__comment = self.source.comment if self.edit_mode else ''
		self._comment_edit_plane = QPlainTextEdit(__comment)
		self._comment_edit_plane.setPlaceholderText('Укажите текст локального комментария')
		self._comment_edit_plane.setMinimumHeight(50)
		main_layout.addWidget(self._comment_edit_plane)

		# ---------------------------- Кнопки взаимодействия ----------------------------

		btns = create_ok_cancel_buttons(self, self.edit_mode)
		main_layout.addWidget(btns)

	# ====================================== Методы =====================================
	def update_work_text_placeholder(self):
		tonnage = self._tonnage_spine_box.value()
		tranport = self._tranport_combo_box.currentText()
		default_text = f"Транспортировка {tranport} грузоподъёмностью до {tonnage} т"
		self._work_text_edit_plane.setPlaceholderText(default_text)
		


	def accept(self):
		none_list = {None, 'None', ' ', '', '-'}
		solution = True
		checed_items = (
			self._name_edit_plane.toPlainText(),
			self._alias_combobox.currentText(),
			self._note_edit_plane.toPlainText()
		)

		for i in checed_items:
			if i in none_list:
				solution = False
				break

		if solution is False:
			QMessageBox.warning(self, "Ошибка", "Наименование, псевдоним и примечания должны быть заполнены.")
			return
		
		return super().accept()
	
	def get_data(self):
		none_list = {None, 'None', ' ', '', '-'}

		name = self._name_edit_plane.toPlainText()
		alias = self._alias_combobox.currentText()
		advanced_coating = self._advanced_coating_spine_box.value()
		transitional_coating = self._transitional_coating_spine_box.value()
		ground_coating = self._ground_coating_spine_box.value()
		tonnage = self._tonnage_spine_box.value()
		transport = self._tranport_combo_box.currentText()
		work_text = self._work_text_edit_plane.toPlainText()
		if work_text in none_list:
			work_text = None
		note = self._note_edit_plane.toPlainText()
		comment = self._comment_edit_plane.toPlainText()
		if comment in none_list:
			comment = None

		data = {
			'name': name,
			'alias': alias,
			'advanced_coating': advanced_coating,
			'transitional_coating': transitional_coating,
			'ground_coating': ground_coating,
			'tonnage': tonnage,
			'transport': transport,
			'work_text': work_text,
			'note': note,
			'comment': comment
		}
		return data
		

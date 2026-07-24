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
	QGroupBox, QLineEdit, QPlainTextEdit, QMessageBox, QDoubleSpinBox,
	QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
	QTabWidget, QStackedWidget, QMenu, QApplication, QDialogButtonBox)
from PyQt6.QtCore import Qt, QLocale
from PyQt6.QtGui import QColor
from Core.Soils import Soil, Gesn1, Gesn4, Gesn5, Soils_Manager
from Core.Utilities import text_after, text_before, convert_value
from ..ui_utilities import (
	TableWithNotes, create_ok_cancel_buttons, Switch, Requestion, create_separator
)
from ..icons import Icons

class Soils_Tab(QWidget):
	""" Представление пространства работы с грунтами проекта """
	def __init__(self, project):
		super().__init__()
		self.project = project

		# единичный экземпляр менеджера взаимодействия с грунтами
		self.manager = project.soils_manager if project else None	

		self.current_non_permanent_view = None  # имя текущего непостоянного представления
		self.views = {}  # словарь созданных виджетов: {'project': widget, ...}
		self.view_indices = {}  # индексы в стеке
		self.setup_ui()

	def setup_ui(self):
		main_layout = QVBoxLayout(self)

		# Панель переключения представлений
		btn_soils_view_subbox = QHBoxLayout()
		self.project_button = QPushButton('ИГЭ') # Сменить пространство вкладки на область редактирования ИГЭ
		# Сменить пространство вкладки на область просмотра и редактирования БД по ГЭСН 1
		self.gesn_1_button = QPushButton('ГЭСН 1') 
		# Сменить пространство вкладки на область просмотра и редактирования БД по ГЭСН 4
		self.gesn_4_button = QPushButton('ГЭСН 4') 
		# Сменить пространство вкладки на область просмотра и редактирования БД по ГЭСН 5
		self.gesn_5_button = QPushButton('ГЭСН 5') 
			
		self.project_button.clicked.connect(lambda: self.switch_view('project'))
		self.project_button.setEnabled(False)
		self.gesn_1_button.clicked.connect(lambda: self.switch_view('gesn1'))
		self.gesn_4_button.clicked.connect(lambda: self.switch_view('gesn4'))
		self.gesn_5_button.clicked.connect(lambda: self.switch_view('gesn5'))
			
		btn_soils_view_subbox.addWidget(self.project_button)
		btn_soils_view_subbox.addWidget(self.gesn_1_button)
		btn_soils_view_subbox.addWidget(self.gesn_4_button)
		btn_soils_view_subbox.addWidget(self.gesn_5_button)
		main_layout.addLayout(btn_soils_view_subbox)

		# Информация о режиме работы
		mode_layuot = QHBoxLayout()

		init_soils_compare = self.project.work_modes.get('ground_complementation_mode') if self.project else False
		self.soils_compare_toggle = Switch(checked=init_soils_compare)
		self.soils_compare_toggle.toggled.connect(self.on_soils_compare_mode_toggled)

		self.work_mode_label = QLabel('<b>Режим сопоставления грунтов отключён</b>')
		self.work_mode_label.setMaximumWidth(300)
		mode_layuot.addWidget(self.work_mode_label)
		mode_layuot.addWidget(self.soils_compare_toggle)
		mode_layuot.setAlignment(self.soils_compare_toggle, Qt.AlignmentFlag.AlignLeft)
		main_layout.addLayout(mode_layuot)

		# Стек представлений
		self.stacked = QStackedWidget() # позволяет отображать только один виджет из набора
		main_layout.addWidget(self.stacked)

		# Создаём постоянное представление (грунты проекта)
		project_widget = ProjectSoilsWidget(self.manager)
		self.stacked.addWidget(project_widget)
		self.views['project'] = project_widget
		self.view_indices['project'] = 0

		# Остальные представления пока не созданы
		self.views['gesn1'] = None
		self.views['gesn4'] = None
		self.views['gesn5'] = None

		# Устанавливаем начальное представление
		self.stacked.setCurrentIndex(0)
		self.current_non_permanent_view = None

	# ------------------------------ Метод режима работы --------------------------------
	def on_soils_compare_mode_toggled(self, checked):
		"""Обрабатывает переключение режима сопоставления грунтов"""
		if self.project is not None:
			self.project.work_modes['ground_complementation_mode'] = checked
			self.settings_changed()
			self.update_ui()
			print(f"Режим сопоставления грунтов: {checked}")
		else:
			pass
	
	# ------------------------------- Методы интерфейса ---------------------------------

	def set_project(self, project):
		"""Обновляет проект во вкладке и во всех дочерних виджетах."""
		self.project = project
		self.manager = project.soils_manager
		# Обновляем все уже созданные виджеты
		for view_name, widget in self.views.items():
			if widget is not None and hasattr(widget, 'set_project'):
				widget.set_project(project)
		# Обновляем текущий виджет
		current = self.stacked.currentWidget()
		if hasattr(current, 'update_ui'):
			current.update_ui()

	
	def update_ui(self):
		"""Обновляет отображение текущего виджета."""
		current = self.stacked.currentWidget()
		if self.project:
			work_mode = self.project.work_modes.get('ground_complementation_mode')
			self.soils_compare_toggle.blockSignals(True)
			if work_mode:
				self.work_mode_label.setText('<b>Режим сопоставления грунтов активирован</b>')
				self.soils_compare_toggle.setChecked(True)
			else:
				self.work_mode_label.setText('<b>Режим сопоставления грунтов отключён</b>')
				self.soils_compare_toggle.setChecked(False)
			self.soils_compare_toggle.blockSignals(False)
		if hasattr(current, 'update_ui'):
			current.update_ui()


	def tab_selected(self):
		"""Вызывается при активации вкладки."""
		self.update_ui()
	
	def settings_changed(self):
		"""Вызывается при изменении настроек проекта (например, режима сопоставления грунтов)."""
		if self.project:
			# Обновляем режим сопоставления в классе Soil
			if self.project.work_modes.get('ground_complementation_mode', False):
				self.work_mode_label.setText('<b>Режим сопоставления грунтов активирован</b>')
			else:
				self.work_mode_label.setText('<b>Режим сопоставления грунтов отключён</b>')
			mode = self.project.work_modes.get('ground_complementation_mode', False)
			self.soils_compare_toggle.setChecked(mode)
			Soil._compare_mode = mode
			# Обновляем все созданные виджеты
			for widget in self.views.values():
				if widget is not None and hasattr(widget, 'update_ui'):
					widget.update_ui()

	def switch_view(self, view_name):
		"""Переключает представление по имени. Удаляет предыдущее непостоянное."""
		if view_name == 'project':
			# Постоянное представление – просто переключаемся
			self.stacked.setCurrentIndex(self.view_indices['project'])
			self.current_non_permanent_view = None
			current_widget = self.stacked.currentWidget()
			if hasattr(current_widget, 'update_ui'):
				current_widget.update_ui()
			self.disable_btn(view_name)
			return
		
		# Если это непостоянное представление
		# Если предыдущее непостоянное существует и не равно новому, удаляем его
		if self.current_non_permanent_view is not None and self.current_non_permanent_view != view_name:
			old_name = self.current_non_permanent_view
			old_widget = self.views.get(old_name)
			if old_widget is not None:
				# Удаляем из стека и из словаря
				self.stacked.removeWidget(old_widget)
				old_widget.deleteLater()
				self.views[old_name] = None
				if old_name in self.view_indices:
					del self.view_indices[old_name]

		# Проверяем, создан ли уже нужный виджет
		if self.views.get(view_name) is None:
			# Создаём
			if view_name == 'gesn1':
				widget = Gesn1Widget(self.manager)
			elif view_name == 'gesn4':
				widget = Gesn4Widget(self.manager)
			elif view_name == 'gesn5':
				widget = Gesn5Widget(self.manager)
			else:
				return
			# Добавляем в стек
			index = self.stacked.addWidget(widget)
			self.views[view_name] = widget
			self.view_indices[view_name] = index
		else:
			index = self.view_indices[view_name]

		# Переключаемся
		self.stacked.setCurrentIndex(index)
		self.current_non_permanent_view = view_name
		self.disable_btn(view_name)


	def disable_btn(self, btn):
		""" Отключает кнопку текущего представления, включает все остальные """
		buttons_dict = {
			'project' : self.project_button,
			'gesn1' : self.gesn_1_button,
			'gesn4' : self.gesn_4_button,
			'gesn5' : self.gesn_5_button
		}
		disebled_button = buttons_dict.pop(btn)
		enebled_buttons = list(buttons_dict.values())

		disebled_button.setEnabled(False)
		for button in enebled_buttons:
			button.setEnabled(True)



				


class ProjectSoilsWidget(QWidget):
	"""Представление для работы с грунтами проекта (ИГЭ)"""
	def __init__(self, soil_manager):
		super().__init__()
		self.manager: Soils_Manager = soil_manager
		self.setup_ui()
		self.soils_table.itemSelectionChanged.connect(self.on_soil_selected)

	
	def setup_ui(self):
		# ----------------------------------- Таблица -----------------------------------
		self.soils_table = TableWithNotes(self.manager)
		self.soils_table.verticalHeader().setVisible(False)
		self.soils_table.setWordWrap(True)
		self.soils_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		self.soils_table.setColumnCount(9)
		self.soils_table.setHorizontalHeaderLabels([
			'№\nИГЭ', 
			'Описание грунта', 
			'Плотность\nпо ИГИ,\nγ, т/м³', 
			'Принятая\nплотность,\nγ, т/м³', 
			'№ по\nГЭСН 1', 
			'№ по\nГЭСН 4', 
			'№ по\nГЭСН 5',
			'Примечание №1',
			'Примечание №2'
			])
		column_widths = (100, 400, 100, 100, 100, 100, 100, 250, 250)
		for col, width in enumerate(column_widths):
			self.soils_table.setColumnWidth(col, width)
			self.soils_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
		header = self.soils_table.horizontalHeader()
		font = header.font()
		font.setBold(True)
		header.setFont(font)
		self.soils_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.soils_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
		self.soils_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.soils_table.customContextMenuRequested.connect(self.on_table_context_menu)

		# ------------------------------ Кнопки управления ------------------------------
		# Вертикальный layout для кнопок
		button_layout = QVBoxLayout()
		button_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

		self.btn_edit_lib = QPushButton('Редактировать\nбиблиотеку')
		self.btn_edit_lib.setIcon(Icons.unlock)
		self.btn_edit_lib.clicked.connect(self.toggle_edit_mode)

		self.btn_create = QPushButton("Создать")
		self.btn_create.clicked.connect(self.open_soil_macker_dialog)
		self.btn_copy = QPushButton("Копировать")
		self.btn_copy.clicked.connect(self.copy_soil)
		self.btn_edit = QPushButton("Редактировать\nэлемент")
		self.btn_edit.clicked.connect(self.open_soil_edit_dialog)
		self.btn_save = QPushButton("Сохранить")
		self.btn_save.clicked.connect(self.save_soils)
		self.btn_reload = QPushButton("Перезагрузить")
		self.btn_reload.clicked.connect(self.reload_soils)
		self.btn_delete = QPushButton("Удалить")
		self.btn_delete.clicked.connect(self.remove_soil)

		button_layout.addWidget(QLabel('Статус:'))
		self.status_label  = QLabel('Чтение')
		button_layout.addWidget(self.status_label)
		
		button_layout.addWidget(self.btn_edit_lib)

		button_layout.addWidget(create_separator())	# ---
		
		button_layout.addWidget(self.btn_create)
		button_layout.addWidget(self.btn_copy)
		button_layout.addWidget(self.btn_edit)
		button_layout.addWidget(self.btn_save)
		button_layout.addWidget(self.btn_reload)
		button_layout.addWidget(self.btn_delete)
		
		# ---------------------------- Вкладки данных ГЭСН ------------------------------
	
		self.gesn_tabs = QTabWidget()
		# Создаём виджеты для вкладок (передаём менеджер, данные будут установлены позже)
		self.gesn1_widget = Gesn1Widget(self.manager, obj_data=None, on_main_view=True)
		self.gesn4_widget = Gesn4Widget(self.manager, obj_data=None, on_main_view=True)
		self.gesn5_widget = Gesn5Widget(self.manager, obj_data=None, on_main_view=True)

		self.gesn_tabs.addTab(self.gesn1_widget, "ГЭСН 1")
		self.gesn_tabs.addTab(self.gesn4_widget, "ГЭСН 4")
		self.gesn_tabs.addTab(self.gesn5_widget, "ГЭСН 5")

		# Группа "Данные ГЭСН для текущего грунта"
		current_soil_info_group = QGroupBox(' Данные ГЭСН для текущего ИГЭ ')
		group_layout = QVBoxLayout()
		group_layout.addWidget(self.gesn_tabs)
		current_soil_info_group.setLayout(group_layout)
		current_soil_info_group.setMaximumHeight(300)

		# --------------------------------- Компоновка ----------------------------------
		main_layout = QVBoxLayout(self)

		project_soils_group = QGroupBox(' Инженерно-геологические элементы ')
		soils_view = QHBoxLayout()
		soils_view.addWidget(self.soils_table)
		soils_view.addLayout(button_layout)  # кнопки справа
		project_soils_group.setLayout(soils_view)

		main_layout.addWidget(project_soils_group)
		main_layout.addWidget(current_soil_info_group)

		# Изначально отключаем кнопки манипуляции
		self.set_manipulation_buttons_enabled(False)
	
	def set_manipulation_buttons_enabled(self, enabled):
		"""Включает/отключает кнопки редактирования"""
		for btn in (
			self.btn_create, self.btn_copy, self.btn_edit,
			self.btn_save, self.btn_delete
		):
			btn.setEnabled(enabled)
		self.btn_edit_lib.setEnabled(not enabled)
		self.btn_edit_lib.setIcon(Icons.unlock if enabled else Icons.lock)


	def on_soil_selected(self):
		"""Обновляет вкладки ГЭСН при изменении выделения в таблице."""
		current_row = self.soils_table.currentRow()
		if current_row < 0:
			# Ничего не выбрано – очищаем вкладки
			self.gesn1_widget.set_data(None)
			self.gesn4_widget.set_data(None)
			self.gesn5_widget.set_data(None)
			return
		num_item = self.soils_table.item(current_row, 0)
		if num_item is None:
			return
		num = num_item.text()
		soil = self.manager.library.get(num)
		if soil:
			self.gesn1_widget.set_data(soil.gesn_1_obj)
			self.gesn4_widget.set_data(soil.gesn_4_obj)
			self.gesn5_widget.set_data(soil.gesn_5_obj)
		else:
			self.gesn1_widget.set_data(None)
			self.gesn4_widget.set_data(None)
			self.gesn5_widget.set_data(None)
	
	def set_project(self, project):
		self.manager = project.soils_manager
		# Обновляем менеджер в дочерних виджетах ГЭСН
		self.gesn1_widget.set_project(project)
		self.gesn4_widget.set_project(project)
		self.gesn5_widget.set_project(project)
		# Обновляем менеджер в таблице
		self.soils_table.set_manager(self.manager)
		self.update_ui()


	def update_ui(self):
		"""Обновляет таблицу ИГЭ и вкладки ГЭСН."""
		if self.manager is None:
			self.soils_table.setRowCount(0)
			self.gesn1_widget.set_data(None)
			self.gesn4_widget.set_data(None)
			self.gesn5_widget.set_data(None)
			return
		sotred_soils = dict(sorted(self.manager.library.items()))
		self.soils_table.setRowCount(len(sotred_soils))
		for row, (num, soil) in enumerate(sotred_soils.items()):
			num_item = QTableWidgetItem(num)
			num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.soils_table.setItem(row, 0, num_item)
			self.soils_table.setItem(row, 1, QTableWidgetItem(soil.local_name))
			local_density_item = QTableWidgetItem(str(soil.local_density))
			local_density_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.soils_table.setItem(row, 2, local_density_item)
			accepted_density_item = QTableWidgetItem(str(soil.accepted_density))
			accepted_density_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			accepted_density_item.setToolTip(f'ВГ.{num}.Y')
			self.soils_table.setItem(row, 3, accepted_density_item)
			gesn_1_num = soil.gesn_1_obj.num if soil.gesn_1_obj else '-'
			gesn_1_num_item = QTableWidgetItem(gesn_1_num)
			gesn_1_num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.soils_table.setItem(row, 4, gesn_1_num_item)
			gesn_4_num = soil.gesn_4_obj.num if soil.gesn_4_obj else '-'
			gesn_4_num_item = QTableWidgetItem(gesn_4_num)
			gesn_4_num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.soils_table.setItem(row, 5, gesn_4_num_item)
			gesn_5_num = soil.gesn_5_obj.num if soil.gesn_5_obj else '-'
			gesn_5_num_item = QTableWidgetItem(gesn_5_num)
			gesn_5_num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.soils_table.setItem(row, 6, gesn_5_num_item)
			note1_item = QTableWidgetItem(soil._note1)
			note1_item.setToolTip(f'ВГ.{num}.прим1')
			self.soils_table.setItem(row, 7, note1_item)
			note2_item = QTableWidgetItem(soil._note2)
			note2_item.setToolTip(f'ВГ.{num}.прим2')
			self.soils_table.setItem(row, 8, note2_item)

			if self.soils_table.rowCount() > 0:
				self.soils_table.selectRow(0)
		# Обновляем вкладки в соответствии с текущим выделением
		self.update_status()
		self.on_soil_selected()

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
		else:
			self.set_manipulation_buttons_enabled(False)
			QMessageBox.warning(self, 'Редактирование',
									'Не удалось заблокировать файл для других пользователей')

	def on_table_context_menu(self, pos):
		# Получаем позицию и индекс ячейки
		index = self.soils_table.indexAt(pos)
		if not index.isValid():
			return
		row = index.row()
		col = index.column()
		
		# Получаем номер ИГЭ и объект грунта
		num_item = self.soils_table.item(row, 0)
		if not num_item:
			return
		num = num_item.text()
		soil = self.manager.library.get(num) if self.manager else None
		if soil is None:  
			return

		# Для столбца с комментариями (№ ИГЭ) передаём обработку в TableWithNotes
		if col == 0:
			self._show_note_menu(soil, pos)
			return
		
		# Текст ячейки для копирования
		cell_item = self.soils_table.item(row, col)
		cell_text = cell_item.text() if cell_item else ""

		# Создаём меню
		menu = QMenu(self)
		# Действие "Копировать значение"
		action_copy_value = menu.addAction("Копировать")
		action_copy_value.triggered.connect(lambda: self._copy_to_clipboard(cell_text))

		# Сохраняем local_num один раз, чтобы использовать в лямбдах
		local_num = soil.local_num

		# Обработка колонки принятой плотности (индекс 3)
		if col == 3:
			if soil:
				action = menu.addAction("Копировать ссылку")
				action.triggered.connect(lambda checked, ln=local_num: self._copy_to_clipboard(f'@ВГ.{ln}.Y'))
			else:
				action = menu.addAction("Копировать ссылку")
				action.setDisabled(True)

		# Обработка колонки ГЭСН 1 (индекс 4)
		if col == 4:
			if soil and soil.gesn_1_obj:
				submenu = menu.addMenu('Копировать ссылку на трудоёмкость разработки...')
				works = [
					"Экскаваторами одноковшовыми",								# 0
					"Экскаваторами траншейными цепными",						# 1
					"Экскаваторами траншейными роторными",						# 2
					"Скреперами",												# 3
					"Бульдозерами",												# 4
					"Грейдерами",												# 5
					"Грейдер-элеваторами",										# 6
					"Бурильнокрановыми машинами",								# 7
					"Разработка грунтов вручную",								# 8
					"Разрыхление мерзлых грунтов",								# 9
					"Нарезка прорезей в мерзлых грунтах баровыми машинами",		# 10
					"Рыхление грунта бульдозерами рыхлителями",					# 11
					"Рыхление мерзлых грунтов бульдозерами-рыхлителями"			# 12
				] 
				for i, work_text in enumerate(works, start=1):
					action = submenu.addAction(work_text)
					# Передаём i и local_num как аргументы по умолчанию
					action.triggered.connect(lambda checked, n=i, ln=local_num: self._copy_to_clipboard(f"@ВГ.{ln}.ГЭСН1.{n}"))
			else:
				action_copy_link = menu.addAction("Копировать ссылку...")
				action_copy_link.setEnabled(False)

		# Обработка колонки ГЭСН 4 (индекс 5)
		elif col == 5:
			if soil and soil.gesn_4_obj:
				submenu = menu.addMenu("Копировать ссылку...")
				action = submenu.addAction("Группа грунта")
				action.triggered.connect(lambda checked, ln=local_num: self._copy_to_clipboard(f"@ВГ.{ln}.ГЭСН4.Группа"))
			else:
				action_copy_link = menu.addAction("Копировать ссылку...")
				action_copy_link.setEnabled(False)

		# Обработка колонки ГЭСН 5 (индекс 6)
		elif col == 6:
			if soil and soil.gesn_5_obj:
				submenu = menu.addMenu("Копировать ссылку...")
				# Подменю для групп грунта по трудоёмкости
				groups_sub = submenu.addMenu("Группа грунта по трудоёмкости:")
				action1 = groups_sub.addAction("Вращательное бурение")
				action1.triggered.connect(lambda checked, ln=local_num: self._copy_to_clipboard(f"@ВГ.{ln}.ГЭСН5.Группа1"))
				action2 = groups_sub.addAction("Ударно-канатное бурение")
				action2.triggered.connect(lambda checked, ln=local_num: self._copy_to_clipboard(f"@ВГ.{ln}.ГЭСН5.Группа2"))
				# Подменю для расхода бетона по диаметрам
				exp_sub = submenu.addMenu("Расход бетона при диаметре до:")
				diameters = ["630", "720", "830", "1020"]
				for diam in diameters:
					action = exp_sub.addAction(diam)
					action.triggered.connect(
						lambda checked, d=diam, ln=local_num: self._copy_to_clipboard(f"@ВГ.{ln}.ГЭСН5.Расход_{d}")
					)
			else:
				action_copy_link = menu.addAction("Копировать ссылку...")
				action_copy_link.setEnabled(False)
		# Обработка колонкок Примечание 1 и 2 (индекс 8)
		elif col == 7 or col == 8:
			note_num = {7:'Прим1',8:'Прим2'}
			if soil:
				action = menu.addAction("Копировать ссылку")
				action.triggered.connect(lambda checked, ln=local_num: self._copy_to_clipboard(f'@ВГ.{ln}.{note_num[col]}'))
			else:
				action = menu.addAction("Копировать ссылку")
				action.setDisabled(True)
		# Показываем меню в глобальных координатах
		menu.exec(self.soils_table.viewport().mapToGlobal(pos))
	
	def _show_note_menu(self, soil, pos):
		"""Показывает меню заметок для грунта"""
		menu = QMenu(self)
		if soil.comment:
			action_edit = menu.addAction("Изменить заметку...")
			action_remove = menu.addAction("Удалить заметку")
		else:
			action_add = menu.addAction("Добавить заметку...")
		action = menu.exec(self.soils_table.viewport().mapToGlobal(pos))
		if soil.comment:
			if action == action_edit:
				self._edit_comment(soil)
			elif action == action_remove:
				self._set_comment(soil, None)
		else:
			if action == action_add:
				self._edit_comment(soil)

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
		
	# ---------------------------------- Работа с ИГЭ -----------------------------------

	def open_soil_macker_dialog(self):
		""" Создать новый грунт """
		if self.manager is None:
			return
		dialog = Soil_Dialog(self, soils_manager=self.manager)

		if dialog.exec() == QDialog.DialogCode.Accepted:
			data = dialog.get_data()
			
			self.manager.create_soil(
				local_num = data.get('local_num'),
				local_name = data.get('local_name'),
				local_density = data.get('local_density'),
				gesn_1_num = data.get('gesn_1_num'),
				gesn_4_num = data.get('gesn_4_num'),
				gesn_5_num = data.get('gesn_5_num'),
				note1 = data.get('note1'),
				note2 = data.get('note2'),
				comment = data.get('comment')
			)
			self.update_ui()

	def open_soil_edit_dialog(self, num_from_copy : str | bool = False):
		""" Редактировать текущий грунт """
		if num_from_copy is False:
			soil_num = self.preliminary_soil_check('Редактирование ИГЭ')
		else:
			soil_num = num_from_copy
		
		if soil_num is False:
			return
		
		dialog = Soil_Dialog(self, soils_manager=self.manager, edit_mode=True, soil_num= soil_num)

		if dialog.exec() == QDialog.DialogCode.Accepted:
			data = dialog.get_data()
			self.manager.edit_soil(data)
			self.update_ui()

	def preliminary_soil_check(self, action:str):
		"""
		Предварительная проверка корректности запроса.

		Args:
			:action (str): Описание события для окна предупреждения

		Returns:
			:False: Проверка не пройдена
			:soil_num (str): Номер ИГЭ для выбранной строки в таблице
		"""
		if self.manager is None:
			return False
		row = self.soils_table.currentRow()
		if row == -1:
			QMessageBox.warning(self, action, "Сначала выберите ИГЭ в таблице.")
			return False
		soil_num = self.soils_table.item(row,0).text()

		return soil_num
	
	def save_soils(self):
		""" Сохраняет библиотку ИГЭ """
		if self.manager is not None:
			res = self.manager.save_lib()
			self.manager.project.saving_settings()
			self.set_manipulation_buttons_enabled(False)
			if not res:
				QMessageBox.warning(self, 'Сохранение', f'Не удалось сохранить данные')
		else:
			print("Невозможно сохранить: менеджер грунтов или проект не назначены")
		self.update_ui()

	def reload_soils(self):
		""" Обновляет список ИГЭ и их объекты ГЭСН """
		if self.manager is not None:
			self.manager.reload_lib()
			self.update_ui()
			self.set_manipulation_buttons_enabled(False)
		else:
			print("Не удалось актуализировать ИГЭ")
	
	def remove_soil(self):
		""" Удаляет выбранный ИГЭ """
		soil_num = self.preliminary_soil_check('Удаление ИГЭ')
		reply = Requestion.ask(
			self,
			'Подтверждение удаления ИГЭ',
			f'Вы действительно хотите удалить {soil_num}?',
			with_cancel = False
		)
		if reply == QMessageBox.StandardButton.Yes:
			self.manager.remove_soil(soil_num)
			self.update_ui()
	
	def copy_soil(self):
		""" Создают копию текущего грунта и вызывает окно редактирования """
		soil_num = self.preliminary_soil_check('Дублирование ИГЭ')
		key =self.manager.copy_soil(soil_num)
		self.update_ui()
		self.open_soil_edit_dialog(key)
	
	# ------------------------------------
	
	def _copy_to_clipboard(self, text):
		clipboard = QApplication.clipboard()
		clipboard.setText(text)



class Gesn1Widget(QWidget):
	"""Представление для просмотра/редактирования БД ГЭСН 1"""
	def __init__(self, soil_manager, obj_data = None, on_main_view=False):
		super().__init__()
		self.soil_manager = soil_manager
		self.obj_data = obj_data
		self.on_main_view = on_main_view
		self.setup_ui()
		self.update_ui()

	def setup_ui(self):
		# ------------------ Таблица взаимодействия с данными ГЭСН 1 ------------------
		self.gesn1_table = QTableWidget()
		self.gesn1_table.setWordWrap(True) # Включение переноса текста в ячейках данных
		self.gesn1_table.verticalHeader().setVisible(False)

		# Скрываем стандартный горизонтальный заголовок
		self.gesn1_table.horizontalHeader().setVisible(False)

		# Автоматическая высота строк (подстраивается под текст)
		self.gesn1_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

		# Фиксированная ширина столбцов
		column_widths = (400, 100, 110, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100)
		self.gesn1_table.setColumnCount(len(column_widths))
		for col, width in enumerate(column_widths):
			self.gesn1_table.setColumnWidth(col, width)
			self.gesn1_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
		
		# Вставляем две строки для многоуровневого заголовка
		self.gesn1_table.insertRow(0)  # строка 0 – объединённые группы
		self.gesn1_table.insertRow(1)  # строка 1 – подзаголовки

		# Заполняем строку 0 (общий заголовок для работ)
		self.gesn1_table.setSpan(0, 2, 1, 8)  # объединяем столбцы 3–8
		item_group = self.create_bold_item("Механизированная разработка грунтов")
		self.gesn1_table.setItem(0, 2, item_group)

		
		# Заполняем строку 1 (подзаголовки)

		# Столбец 0 – Наименование
		item = self.create_bold_item("Наименование и краткая характеристика грунтов")
		self.gesn1_table.setItem(0, 0, item)
		self.gesn1_table.setSpan(0, 0, 2, 1)

		# Столбец 1 – Плотность
		item = self.create_bold_item("Средняя плотность в естественном залегании,\nкг/м³")
		self.gesn1_table.setItem(0, 1, item)
		self.gesn1_table.setSpan(0, 1, 2, 1)

		# Подзаголовки для работ (столбцы 2–14)
		work_headers = [
			"Экскаваторами одноковшовыми",
			"Экскаваторами траншейными цепными",
			"Экскаваторами траншейными роторными",
			"Скреперами",
			"Бульдозерами",
			"Грейдерами",
			"Грейдер-элеваторами",
			"Бурильнокрановыми машинами",
			"Разработка грунтов вручную",
			"Разрыхление мерзлых грунтов",
			"Нарезка прорезей в мерзлых грунтах баровыми машинами",
			"Рыхление грунта бульдозерами рыхлителями",
			"Рыхление мерзлых грунтов бульдозерами-рыхлителями"
		]
		for col, text in enumerate(work_headers, start=2):
			if col < 10:
				item = self.create_bold_item(text)
				self.gesn1_table.setItem(1, col, item)
			else:
				item = self.create_bold_item(text)
				self.gesn1_table.setItem(0, col, item)
				self.gesn1_table.setSpan(0, col, 2, 1)

		# Разрешаем редактирование данных (для остальных строк)
		self.gesn1_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
		self.gesn1_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)

		# ------------------------------- Кнопка сохранения -----------------------------
		if self.obj_data is None and self.on_main_view is False:
			save_btn = QPushButton('Применить изменения')
			save_btn.clicked.connect(self.saving_change)
			save_btn.setMaximumWidth(250)
			button_box = QVBoxLayout()
			button_box.addWidget(save_btn)
			button_box.setAlignment(save_btn, Qt.AlignmentFlag.AlignCenter)
		
		# --------------------------------- Компоновка ----------------------------------

		layout = QVBoxLayout(self)
		layout.addWidget(self.gesn1_table)
		if self.obj_data is None and self.on_main_view is False:
			layout.addLayout(button_box)

	def set_project(self, project,):
		self.soil_manager = project.soils_manager
		self.update_ui()
	
	def update_ui(self):
		self.update_table()

	def update_table(self):
		'''Обновляет таблицу в двух режимах: полная таблица ГЭСН 1 или информация по текущему грунту
		:obj_data: данные по выделенному грунту в основном представлении
		'''
		self.gesn1_table.blockSignals(True)
		# Удаляем все старые строки данных (оставляем только две заголовочные)
		while self.gesn1_table.rowCount() > 2:
			self.gesn1_table.removeRow(2)

		if self.soil_manager is None:
			self.gesn1_table.blockSignals(False)
			return
		
		if self.on_main_view:
			# Режим показа данных текущего ИГЭ
			if self.obj_data is None:
				self.gesn1_table.blockSignals(False)
				return
			# Преобразуем объект в словарь для одной строки
			data = {self.obj_data.num: self.obj_data.json_serializer()}
		else:
			data = self.soil_manager.gesn_1_data

		if not data:
			self.gesn1_table.blockSignals(False)
			return
		
		# Вставляем новые строки данных
		for row, item in enumerate(data.values()):
			self.gesn1_table.insertRow(2 + row)  # добавляем строку на позицию 2+row
			# Заполняем ячейки
			name_item = QTableWidgetItem(str(item.get('name', '')))
			name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # убираем флаг редактирования
			self.gesn1_table.setItem(2 + row, 0, name_item)
			density = str(item.get('density', ''))
			if density in {'', None, 'None'}:
				density = '-'
			density_item = QTableWidgetItem(density)
			density_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.gesn1_table.setItem(2 + row, 1, density_item)
			for i in range(1, 14):
				col = i + 1  # work_1 → столбец 3
				value = item.get(f'work_{i}', '')
				if value in {'', None}:
					value = '-'
				work_item = QTableWidgetItem(str(value))
				work_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				self.gesn1_table.setItem(2 + row, col, work_item)
		self.gesn1_table.blockSignals(False)

	def set_data(self, obj):
		"""Устанавливает объект для отображения и обновляет таблицу."""
		self.obj_data = obj
		self.update_ui()

	def saving_change(self):
		reply = Requestion.ask(
			self,
			'Подтверждение изменений',
			'Вы действительно хотите применить изменения к данным по ГЭСН 1?',
			with_cancel = False
		)
		if reply == QMessageBox.StandardButton.Yes:
			export_dict = {}
			for row in range(self.gesn1_table.rowCount()-2):
				key = text_before(self.gesn1_table.item(row+2,0).text(),'.')
				row_data = {}
				sub_keys = list(Gesn1.short_names.keys())
				column = 0
				for sub_key in sub_keys:
					item = self.gesn1_table.item(row+2,column).text()
					if item in {'-', None, 'None'}:
						value =None
					else:
						try:
							if '.' in item:
								value = float(item)
							elif ',' in item:
								value = float(item.replace(',','.'))
							else:
								value = int(item)
						except ValueError:
							value = item
					row_data[sub_key] = value
					column += 1
				export_dict[key] = row_data
			self.soil_manager.save_gesn1_data(export_dict)
	
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



class Gesn4Widget(QWidget):
	"""Представление для ГЭСН 4"""
	def __init__(self, soil_manager, obj_data = None, on_main_view=False):
		super().__init__()
		self.soil_manager = soil_manager
		self.obj_data = obj_data
		self.on_main_view = on_main_view
		self.setup_ui()
		self.update_ui()

	def setup_ui(self):
		layout = QVBoxLayout(self)
		info_label = QLabel('<b>Приложение IV. Приложение 4.1<br>Распределение грунтов по буримости</b>')
		info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		layout.addWidget(info_label)

		# ------------------------------ Таблица ГЭСН 4 ------------------------------
		self.gesn4_table = QTableWidget()
		self.gesn4_table.setWordWrap(True)
		self.gesn4_table.verticalHeader().setVisible(False)
		self.gesn4_table.setColumnCount(2)
		self.gesn4_table.setHorizontalHeaderLabels(('Группа\nгрунтов', 'Наименование и характеристика грунтов'))
		self.gesn4_table.setColumnWidth(0, 75)
		self.gesn4_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		self.gesn4_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
		self.gesn4_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.gesn4_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

		layout.addWidget(self.gesn4_table)

	def set_project(self, project):
		self.soil_manager = project.soils_manager
		self.update_ui()

	def update_ui(self):
		self.update_table()
	
	def set_data(self, obj):
		"""Устанавливает объект для отображения и обновляет таблицу."""
		self.obj_data = obj
		self.update_ui()

	def update_table(self):
		self.gesn4_table.blockSignals(True)
		self.gesn4_table.setRowCount(0)  # очищаем таблицу

		if self.soil_manager is None:
			self.gesn4_table.blockSignals(False)
			return
	
		sections_names = Gesn4.short_names

		if self.on_main_view:
			if self.obj_data is None:
				self.gesn4_table.blockSignals(False)
				return

			# Отображение одного объекта (текущий ИГЭ)
			self.gesn4_table.setRowCount(2)

			# Заголовок раздела
			header_text = sections_names.get(self.obj_data.drillability_type, "-")
			header_item = QTableWidgetItem(header_text)
			header_item.setBackground(QColor("#5FADC0"))
			font = header_item.font()
			font.setBold(True)
			header_item.setFont(font)
			self.gesn4_table.setItem(0, 0, header_item)
			self.gesn4_table.setSpan(0, 0, 1, 2)

			# Группа грунта
			item_group = QTableWidgetItem(str(self.obj_data.soil_group))
			item_group.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.gesn4_table.setItem(1, 0, item_group)

			# Описание
			item_desc = QTableWidgetItem(self.obj_data.description)
			self.gesn4_table.setItem(1, 1, item_desc)

		else:
			# Отображение полной таблицы ГЭСН 4
			data = self.soil_manager.gesn_4_data

			if not data:
				self.gesn4_table.blockSignals(False)
				return

			# Подсчёт общего количества строк
			row_count = sum(1 + len(lst) for lst in data.values())
			self.gesn4_table.setRowCount(row_count)
			cur_row = 0
			for key, lst in data.items():
				# Заголовок раздела
				header_text = f'{key}. {sections_names.get(key, "-")}'
				header_item = QTableWidgetItem(header_text)
				header_item.setBackground(QColor("#5FADC0"))
				font = header_item.font()
				font.setBold(True)
				header_item.setFont(font)
				self.gesn4_table.setItem(cur_row, 0, header_item)
				self.gesn4_table.setSpan(cur_row, 0, 1, 2)
				cur_row += 1

				# Строки грунтов в разделе
				for soil_dict in lst:
					if isinstance(soil_dict, dict):
						soil_group = soil_dict.get('soil_group', '-')
						description = soil_dict.get('description', '-')
					else:
						soil_group = '-'
						description = str(soil_dict)
					item_group = QTableWidgetItem(str(soil_group))
					item_group.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
					self.gesn4_table.setItem(cur_row, 0, item_group)
					item_desc = QTableWidgetItem(description)
					self.gesn4_table.setItem(cur_row, 1, item_desc)
					cur_row += 1

		self.gesn4_table.blockSignals(False)


class Gesn5Widget(QWidget):
	"""Представление для ГЭСН 5"""
	def __init__(self, soil_manager, obj_data = None, on_main_view = False):
		super().__init__()
		self.soil_manager = soil_manager
		self.obj_data = obj_data
		self.on_main_view = on_main_view
		self.setup_ui()
		self.update_ui()

	def setup_ui(self):
		layout = QVBoxLayout(self)

		# ------------------------------ Таблица ГЭСН 5 ------------------------------
		self.gesn5_table = QTableWidget()
		self.gesn5_table.setWordWrap(True)
		self.gesn5_table.verticalHeader().setVisible(False)

		# Скрываем стандартный горизонтальный заголовок
		self.gesn5_table.horizontalHeader().setVisible(False)

		# Автоматическая высота строк
		self.gesn5_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

		# Фиксированная ширина столбцов (7 столбцов)
		column_widths = (500, 100, 110, 100, 100, 100, 100)
		self.gesn5_table.setColumnCount(len(column_widths))
		for col, width in enumerate(column_widths):
			self.gesn5_table.setColumnWidth(col, width)
			if col == 0:
				self.gesn5_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
			else:
				self.gesn5_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

		# Вставляем две строки для многоуровневого заголовка
		self.gesn5_table.insertRow(0)  # строка 0 – объединённые группы
		self.gesn5_table.insertRow(1)  # строка 1 – подзаголовки

		# Заполняем строку 0 (общие заголовки групп)
		# Объединяем ячейки для блока "Группа грунтов..." (столбцы 1-2)
		self.gesn5_table.setSpan(0, 1, 1, 2)
		item_group = self.create_bold_item("Группа грунтов и пород по способам бурения")
		self.gesn5_table.setItem(0, 1, item_group)

		# Объединяем ячейки для блока "Расход бетона..." (столбцы 3-6)
		self.gesn5_table.setSpan(0, 3, 1, 4)
		item_concrete = self.create_bold_item("Расход бетона на 1 м3 конструктивного объема сваи при диаметре, мм, до")
		self.gesn5_table.setItem(0, 3, item_concrete)

		# Заполняем строку 1 (подзаголовки)
		# Столбец 0 – Наименование
		item_name = self.create_bold_item("Наименование и характеристика грунтов и пород")
		self.gesn5_table.setItem(0, 0, item_name)
		self.gesn5_table.setSpan(0,0,2,1)

		# Столбец 1 – Вращательное бурение
		item_rotary = self.create_bold_item("Вращательное бурение")
		self.gesn5_table.setItem(1, 1, item_rotary)

		# Столбец 2 – Ударно-канатное бурение
		item_percussion = self.create_bold_item("Ударно-канатное бурение")
		self.gesn5_table.setItem(1, 2, item_percussion)

		# Столбцы 3-6 – Диаметры
		diameters = ["630", "720", "830", "1020"]
		for col, diam in enumerate(diameters, start=3):
			item_diam = self.create_bold_item(diam)
			self.gesn5_table.setItem(1, col, item_diam)

		# Разрешаем редактирование данных (для остальных строк)
		self.gesn5_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
		self.gesn5_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)

		layout.addWidget(self.gesn5_table)

		# ----------------------------- Кнопка сохранения -------------------------------
		if self.obj_data is None and self.on_main_view is False:
			save_btn = QPushButton('Применить изменения')
			save_btn.clicked.connect(self.saving_change)
			save_btn.setMaximumWidth(250)
			button_box = QVBoxLayout()
			button_box.addWidget(save_btn)
			button_box.setAlignment(save_btn, Qt.AlignmentFlag.AlignCenter)

			layout.addLayout(button_box)

	def set_project(self, project):
		self.soil_manager = project.soils_manager
		self.update_ui()

	def update_ui(self):
		self.update_table()

	def update_table(self):
		'''Обновляет таблицу в двух режимах: полная таблица ГЭСН 5 или информация по текущему грунту
		:obj_data: данные по выделенному грунту в основном представлении
		'''
		self.gesn5_table.blockSignals(True)
		# Удаляем все старые строки данных (оставляем только две заголовочные)
		while self.gesn5_table.rowCount() > 2:
			self.gesn5_table.removeRow(2)

		if self.soil_manager is None:
			self.gesn5_table.blockSignals(False)
			return
		
		if self.on_main_view:
			if self.obj_data is None:
				self.gesn5_table.blockSignals(False)
				return
			data = {self.obj_data.num: self.obj_data.json_serializer()}
		else:
			data = self.soil_manager.gesn_5_data

		if not data:
			self.gesn5_table.blockSignals(False)
			return

		columns = tuple(Gesn5.short_names.keys())  # ожидаемый порядок: name, rotary, percussion, diam1, diam2, diam3, diam4

		for row, item in enumerate(data.values()):
			self.gesn5_table.insertRow(2 + row)
			for col, key in enumerate(columns):
				value = str(item.get(key, '-'))
				table_item = QTableWidgetItem(value)
				# Для первого столбца (наименование) выравнивание влево, остальные по центру
				if col == 0:
					table_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
				else:
					table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				self.gesn5_table.setItem(2 + row, col, table_item)

		self.gesn5_table.blockSignals(False)
	
	def set_data(self, obj):
		"""Устанавливает объект для отображения и обновляет таблицу."""
		self.obj_data = obj
		self.update_ui()

	def saving_change(self):
		reply = Requestion.ask(
			self,
			'Подтверждение изменений',
			'Вы действительно хотите применить изменения к данным по ГЭСН 5?',
			with_cancel = False
		)
		if reply == QMessageBox.StandardButton.Yes:
			# Сбор изменённых данных и сохранение
			export_dict = {}
			for row in range(self.gesn5_table.rowCount() - 2):
				# Предполагаем, что ключ (идентификатор) находится в первом столбце (name)
				key = text_before(self.gesn5_table.item(row+2,0).text(),'_')
				row_data = {}
				sub_keys = list(Gesn5.short_names.keys())
				column = 0
				for sub_key in sub_keys:
					item = self.gesn5_table.item(row + 2, column).text()
					if item in {'-', None, 'None'}:
						value =None
					else:
						try:
							if '.' in item:
								value = float(item)
							elif ',' in item:
								value = float(item.replace(',','.'))
							else:
								value = int(item)
						except ValueError:
							value = item
					row_data[sub_key] = value
					column += 1
				export_dict[key] = row_data
			self.soil_manager.save_gesn5_data(export_dict)
	
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

class Soil_Dialog(QDialog):
	"""Окно создания/редактирования ИГЭ"""
	def __init__(self, parent, soils_manager, edit_mode=False, soil_num=None):
		super().__init__(parent)
		window_name = 'Редактирование ИГЭ' if edit_mode else 'Создание ИГЭ'
		self.setWindowTitle(window_name)
		self.setModal(True)
		self.setMaximumWidth(800)
		self.soils_manager = soils_manager # объект управления грунтами
		self.soil_num = soil_num # Данные текущего грунта для режима редактирования

		self.edit_mode = edit_mode

		self.setup_ui()

	@property
	def soil(self):
		""" Возвращает объект Soil """
		if self.edit_mode:
			return self.soils_manager.library.get(self.soil_num)
		return None
	
	@property
	def gesn1_tuple(self):
		data = self.soils_manager.gesn_1_data
		nums = ['-'] 
		names = ['-']
		for num, diction in data.items():
			nums.append(num)
			names.append(diction.get('name'))
		nums = tuple(nums)
		names = tuple(names)
		return (nums, names)
	
	@property
	def gesn4_tuple(self):
		data = self.soils_manager.gesn_4_data
		gesn_4_list = ['-']
		for sect, lst in data.items():
			for soil in lst:
				text = f'{sect}-{soil.get('soil_group')}'
				gesn_4_list.append(text)
		return tuple(gesn_4_list)
	
	@property
	def gesn5_tuple(self):
		data = self.soils_manager.gesn_5_data
		nums = ['-'] 
		names = ['-']
		for num, diction in data.items():
			nums.append(num)
			names.append(diction.get('name'))
		nums = tuple(nums)
		names = tuple(names)
		return (nums, names)

	def setup_ui(self):
		main_layout = QVBoxLayout(self)

		# --------------------- Поля ввода и редактирования данных ----------------------
		# Номер ИГЭ
		main_layout.addWidget(QLabel('Номер грунта <i>(Цифробуквенное обозначение, без ИГЭ)</i>'))
		__num = text_after(self.soil_num, 'ИГЭ_') if self.edit_mode else ''
		self._num_edit_line = QLineEdit(__num)
		self._num_edit_line.setPlaceholderText('Укажите номер ИГЭ')
		main_layout.addWidget(self._num_edit_line)
		# Наименование ИГЭ
		main_layout.addWidget(QLabel('Наименование грунта по ИГИ:'))
		__name = self.soil.local_name if self.edit_mode else ''
		self._name_edit_plane = QPlainTextEdit(__name)
		self._name_edit_plane.setPlaceholderText('Укажите имя ИГЭ')
		self._name_edit_plane.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
		self._name_edit_plane.setMaximumHeight(45)
		main_layout.addWidget(self._name_edit_plane)
		# Плотность грунта
		main_layout.addWidget(QLabel('Плотность грунта по ИГИ (т/м³):'))
		__density = self.soil.local_density if self.edit_mode else 0
		self._density_spine_box = QDoubleSpinBox() # QLineEdit(str(__density))
		self._density_spine_box.setMinimum(0.00)
		self._density_spine_box.setDecimals(2)
		self._density_spine_box.setSingleStep(0.1)
		self._density_spine_box.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
		self._density_spine_box.setValue(__density)
		self._density_spine_box.setMaximumWidth(120)
		main_layout.addWidget(self._density_spine_box)
		# Сопоставление с ГЭСН 1
		main_layout.addWidget(QLabel('Соответствует ГЭСН 1:'))
		__gesn_1_names = self.gesn1_tuple[1]
		self._gesn_1_num_combbox = QComboBox()
		self._gesn_1_num_combbox.addItems(__gesn_1_names)
		__gesn_1_num = self.soil.gesn_1_obj.name if self.edit_mode and self.soil.gesn_1_obj  else '-'
		self._gesn_1_num_combbox.setCurrentText(__gesn_1_num)
		main_layout.addWidget(self._gesn_1_num_combbox)
		# Сопоставление с ГЭСН 4
		main_layout.addWidget(QLabel('Соответствует ГЭСН 4:'))
		self._gesn_4_num_combbox = QComboBox()
		self._gesn_4_num_combbox.addItems(self.gesn4_tuple)
		__gesn_4_num = self.soil.gesn_4_obj.num if self.edit_mode and self.soil.gesn_4_obj else '-'
		self._gesn_4_num_combbox.setCurrentText(__gesn_4_num)
		main_layout.addWidget(self._gesn_4_num_combbox)
		# Сопоставление с ГЭСН 5
		main_layout.addWidget(QLabel('Соответствует ГЭСН 5:'))
		self._gesn_5_num_combbox = QComboBox()
		__gesn_5_names = self.gesn5_tuple[1]
		self._gesn_5_num_combbox.addItems(__gesn_5_names)
		__gesn_5_num = self.soil.gesn_5_obj.name if self.edit_mode and self.soil.gesn_5_obj else '-'
		self._gesn_5_num_combbox.setCurrentText(__gesn_5_num)
		main_layout.addWidget(self._gesn_5_num_combbox)
		# Краткое наименование для примечания 1
		main_layout.addWidget(QLabel('Краткое имя для примечания 1 <i>(необязательно)</i>:'))
		__note1 = self.soil.note1 if self.edit_mode else ''
		self._note1_edit_plane = QPlainTextEdit(__note1)
		self._note1_edit_plane.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
		self._note1_edit_plane.setMaximumHeight(45)
		self._note1_edit_plane.setPlaceholderText('Заменяет полное наименование на указанный вариант')
		main_layout.addWidget(self._note1_edit_plane)
		# Краткое наименование для примечания 2
		main_layout.addWidget(QLabel('Краткое имя для примечания 2 <i>(необязательно)</i>:'))
		__note2 = self.soil.note2 if self.edit_mode else ''
		self._note2_edit_plane = QPlainTextEdit(__note2)
		self._note2_edit_plane.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
		self._note2_edit_plane.setPlaceholderText('Заменяет полное наименование на указанный вариант')
		self._note2_edit_plane.setMaximumHeight(45)
		main_layout.addWidget(self._note2_edit_plane)
		# Локальный комментарий
		main_layout.addWidget(QLabel('Локальный комментарий по грунту <i>(необязательно)</i>:'))
		__comment = self.soil.comment if self.edit_mode else ''
		self._comment_edit_plane = QPlainTextEdit(__comment)
		self._comment_edit_plane.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
		main_layout.addWidget(self._comment_edit_plane)
		
		# --------------------------- Кнопки взаимодействия -----------------------------

		btns = create_ok_cancel_buttons(self, self.edit_mode)
		main_layout.addWidget(btns)

	def accept(self):
		none_list = {None, 'None', ' ', '', '-', 0, 0.00}
		solution = True
		checed_items = (
			self._num_edit_line.text(),
			self._name_edit_plane.toPlainText(),
			self._density_spine_box.value()
		)

		for i in checed_items:
			if i in none_list:
				solution = False
				break

		if solution is False:
			QMessageBox.warning(self, "Ошибка", "Номер ИГЭ, наименование и плотность должны быть заполнены.")
			return

		if f'ИГЭ_{self._num_edit_line.text()}' in self.soils_manager.library and not self.edit_mode:
			QMessageBox.warning(self, "Внимание", "Грунт с таким номером  ИГЭ уже существует")
			return
		elif f'ИГЭ_{self._num_edit_line.text()}' in self.soils_manager.library and (
			self.edit_mode and f'ИГЭ_{self._num_edit_line.text()}' != self.soil_num
		):
			QMessageBox.warning(
				self, "Внимание", "Изменения номера текущего грунта невозможно, так как новый номер уже существует"
			)
			return
		
		if isinstance(convert_value(checed_items[2]), str):
			QMessageBox.warning(self, "Внимание", "Плотность указана не корректно")
			return
		
		return super().accept()

	def get_data(self):

		none_list = {None, 'None', ' ', '', '-'}

		if self._gesn_1_num_combbox.currentText() in none_list:
			gesn_1_num = None
		else:
			gesn_1_num = self.gesn1_tuple[0][self._gesn_1_num_combbox.currentIndex()]
		
		if self._gesn_4_num_combbox.currentText() in none_list:
			gesn_4_num = None
		else:
			gesn_4_num = self.gesn4_tuple[self._gesn_4_num_combbox.currentIndex()]
		
		if self._gesn_5_num_combbox.currentText() in none_list:
			gesn_5_num = None
		else:
			gesn_5_num = self.gesn5_tuple[0][self._gesn_5_num_combbox.currentIndex()]

		note1 = None if self._note1_edit_plane.toPlainText() in none_list else self._note1_edit_plane.toPlainText()
		note2 = None if self._note2_edit_plane.toPlainText() in none_list else self._note2_edit_plane.toPlainText()
		comment = None if self._comment_edit_plane.toPlainText() in none_list else self._comment_edit_plane.toPlainText()

		data = {
			'old_soil_num': self.soil_num,
			'local_num': f'ИГЭ_{self._num_edit_line.text()}',
			'local_name': self._name_edit_plane.toPlainText(),
			'local_density': round(self._density_spine_box.value(), 2),
			'gesn_1_num': gesn_1_num,
			'gesn_4_num': gesn_4_num,
			'gesn_5_num': gesn_5_num,
			'note1': note1,
			'note2': note2,
			'comment': comment
		}
		return data
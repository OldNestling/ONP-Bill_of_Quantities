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
	QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget, 
	QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from ..ui_utilities import Switch
from ..ui_utilities import IntDelegate
from ..icons import Icons
from Core.Project import Project



# ---------------------------------------------------------------------------------------
# ================================ ВКЛАДКА: НАСТРОЙКИ ===================================
# ---------------------------------------------------------------------------------------

class SettingsTab(QWidget):
	''' Отвечает за содержимоек вкладки "Настройки" '''

	def __init__(self, project, main_window):
		super().__init__()
		self.project: Project = project
		self.main_window = main_window

		self.setup_ui()
		self.update_ui()

	def setup_ui(self):
		# ======================= Переключатели режимов =================================
		# -------------------------- Режим нумерации ------------------------------------

		# Начальное состояние – из проекта (если проект есть)
		initial_state = self.project.work_modes.get('position_mode', False) if self.project else False
		self.position_toggle = Switch(checked=initial_state)
		self.position_toggle.toggled.connect(self.on_position_mode_toggled)

		position_mode_subbox = QHBoxLayout()
		position_mode_subbox.addWidget(QLabel('Использовать нумерацию позиций с подпунктами:'))
		position_mode_subbox.addWidget(self.position_toggle)

		# ----------------------- Режим подробного маршрута  ---------------------------
		init_transportation = self.project.work_modes.get('transportation_mode') if self.project else False
		self.transportation_toggle = Switch(checked=init_transportation)
		self.transportation_toggle.toggled.connect(self.on_transportation_mode_toggled)

		transportation_mode_subbox = QHBoxLayout()
		transportation_mode_subbox.addWidget(QLabel('Делить покрытие маршрута транспортировки на типы:'))
		transportation_mode_subbox.addWidget(self.transportation_toggle)

		# ---------------------- Режим сопоставления грунтов ----------------------------
		init_soils_compare = self.project.work_modes.get('ground_complementation_mode') if self.project else False
		self.soils_compare_toggle = Switch(checked=init_soils_compare)
		self.soils_compare_toggle.toggled.connect(self.on_soils_compare_mode_toggled)

		soils_compare_mode_subbox = QHBoxLayout()
		soils_compare_mode_subbox.addWidget(QLabel('Сопоставлять грунты с ГЭСН:'))
		soils_compare_mode_subbox.addWidget(self.soils_compare_toggle)

		# ================== Таблица настройки единиц измерения =========================

		self.units_table = QTableWidget()
		self.units_table.setColumnCount(3)
		self.units_table.setHorizontalHeaderLabels(['Ключ', 'Отображение', 'Точность округления'])
		for i in range(self.units_table.columnCount()):
			self.units_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
		self.units_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
		self.units_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)

		self.units_table.setItemDelegateForColumn(2, IntDelegate())
		self.units_table.itemChanged.connect(self.on_units_table_item_changed)

		# =========================== Таблица ГИПов =====================================

		self.chiefs_table = QTableWidget()
		self.chiefs_table.setColumnCount(1)
		self.chiefs_table.setHorizontalHeaderLabels(['ГИП'])
		self.chiefs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
		self.chiefs_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
		self.chiefs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.chiefs_table.itemChanged.connect(self.on_chiefs_table_item_changed)

		btn_add_chiefs = QPushButton('Добавить')
		btn_add_chiefs.clicked.connect(self.add_chiefs_row)
		btn_remove_chiefs = QPushButton('Удалить')
		btn_remove_chiefs.clicked.connect(self.remove_chiefs_row)

		## ================== Таблица Исполнителей ==========================
		self.performers_table = QTableWidget()
		self.performers_table.setColumnCount(1)
		self.performers_table.setHorizontalHeaderLabels(['Исполнитель'])
		self.performers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
		self.performers_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
		self.performers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.performers_table.itemChanged.connect(self.on_performers_table_item_changed)

		btn_add_performer = QPushButton('Добавить')
		btn_add_performer.clicked.connect(self.add_performer_row)
		btn_remove_performer = QPushButton('Удалить')
		btn_remove_performer.clicked.connect(self.remove_performer_row)

		## ================== Таблица Должностей ============================
		self.posts_table = QTableWidget()
		self.posts_table.setColumnCount(1)
		self.posts_table.setHorizontalHeaderLabels(['Должность'])
		self.posts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
		self.posts_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
		self.posts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.posts_table.itemChanged.connect(self.on_posts_table_item_changed)

		btn_add_post = QPushButton('Добавить')
		btn_add_post.clicked.connect(self.add_post_row)
		btn_remove_post = QPushButton('Удалить')
		btn_remove_post.clicked.connect(self.remove_post_row)

		posts_buttons = QHBoxLayout()
		posts_buttons.addWidget(btn_add_post)
		posts_buttons.addWidget(btn_remove_post)

		# ============================ Сборка окна ======================================
		# ------ Первая колонка ------
		# Сборка переключателей
		settings_box = QVBoxLayout()

		settings_box.addLayout(position_mode_subbox)
		settings_box.addLayout(transportation_mode_subbox)
		settings_box.addLayout(soils_compare_mode_subbox)
		setting_group = QGroupBox(' Настройки режимов работы проекта ') # Группа переключателей режимов
		
		setting_group.setLayout(settings_box)
		setting_group.setMaximumHeight(100)
		setting_group.setMaximumWidth(450)


		units_group = QGroupBox(' Настройки единиц измерения ')
		units_table_subbox = QHBoxLayout()
		units_table_subbox.addWidget(self.units_table)
		units_group.setLayout(units_table_subbox)
		units_group.setMaximumWidth(450)
		
		#  Кнопка сохранения 
		self.btn_save = QPushButton('Сохранить настройки')
		self.btn_save.setIcon(Icons.save)
		self.btn_save.setMaximumWidth(450)

		
		column_1 = QVBoxLayout()
		column_1.addWidget(setting_group)
		column_1.addWidget(units_group)

		# ------ Вторая колонка ------
		# ГИПы
		chiefs_buttons = QHBoxLayout()
		chiefs_buttons.addWidget(btn_add_chiefs)
		chiefs_buttons.addWidget(btn_remove_chiefs)

		chiefs_group = QGroupBox(' Список ГИПов ')
		chiefs_layout = QVBoxLayout()
		chiefs_layout.addWidget(self.chiefs_table)
		chiefs_layout.addLayout(chiefs_buttons)
		chiefs_group.setLayout(chiefs_layout)
		chiefs_group.setMaximumWidth(250)

		posts_group = QGroupBox(' Список должностей ')
		posts_layout = QVBoxLayout()
		posts_layout.addWidget(self.posts_table)
		posts_layout.addLayout(posts_buttons)
		posts_group.setLayout(posts_layout)
		posts_group.setMaximumWidth(250)

		column_2 = QVBoxLayout()
		column_2.addWidget(chiefs_group)
		column_2.addWidget(posts_group)

		# ------ Третья колонка ------
		# Исполнители
		performers_buttons = QHBoxLayout()
		performers_buttons.addWidget(btn_add_performer)
		performers_buttons.addWidget(btn_remove_performer)

		performers_group = QGroupBox(' Список исполнителей ')
		performers_layout = QVBoxLayout()
		performers_layout.addWidget(self.performers_table)
		performers_layout.addLayout(performers_buttons)
		performers_group.setLayout(performers_layout)	
		performers_group.setMaximumWidth(250)

		column_3 = QVBoxLayout()
		column_3.addWidget(performers_group)

		groups_layout = QHBoxLayout() # Главный слой вкладки
		groups_layout.addLayout(column_1)
		groups_layout.addLayout(column_2)
		groups_layout.addLayout(column_3)
		groups_layout.addStretch()

		main_layout = QVBoxLayout(self)
		main_layout.addLayout(groups_layout)
		main_layout.addWidget(self.btn_save)


	def update_ui(self):
		if not self.project:
			return
		# Блокируем сигналы, чтобы избежать циклического вызова при программной установке
		self.position_toggle.blockSignals(True)
		self.transportation_toggle.blockSignals(True)
		self.soils_compare_toggle.blockSignals(True)
		self.position_toggle.setChecked(self.project.work_modes.get('position_mode', False))
		self.transportation_toggle.setChecked(self.project.work_modes.get('transportation_mode', False))
		self.soils_compare_toggle.setChecked(self.project.work_modes.get('ground_complementation_mode', False))
		self.position_toggle.blockSignals(False)
		self.transportation_toggle.blockSignals(False)
		self.soils_compare_toggle.blockSignals(False)
		self.btn_save.clicked.connect(self.project.saving_settings)
		# Обновляем таблицы
		self.update_units_table()
		self.update_chiefs_table()
		self.update_performers_table()
		self.update_posts_table()
	
	def set_project(self, project):
		"""Вызывается главным окном при изменении проекта"""
		self.project = project
		self.update_ui()
	
	def tab_selected(self):
		"""Вызывается при активации вкладки"""
		self.update_ui()

	#---------------------------------- Переключатели -----------------------------------

	def on_position_mode_toggled(self, checked):
		"""Обрабатывает переключение режима нумерации позиций."""
		if self.project is not None:
			self.project.work_modes['position_mode'] = checked
			self.main_window.notify_settings_changed()
			print(f"Режим нумерации позиций установлен: {checked}")
		else:
			pass
	
	def on_transportation_mode_toggled(self, checked):
		"""Обрабатывает переключение режима представления транспортировки по типу покрытия."""
		if self.project is not None:
			self.project.work_modes['transportation_mode'] = checked
			self.main_window.notify_settings_changed()
			print(f"Режим подробного маршрута транспортировки: {checked}")
		else:
			pass

	def on_soils_compare_mode_toggled(self, checked):
		"""Обрабатывает переключение режима сопоставления грунтов"""
		if self.project is not None:
			self.project.work_modes['ground_complementation_mode'] = checked
			self.main_window.notify_settings_changed()
			print(f"Режим сопоставления грунтов: {checked}")
		else:
			pass
	
	#-------------------------------- Таблица ед.изм. -----------------------------------

	def update_units_table(self):
			if not self.project:
				return
			self.units_table.blockSignals(True)   # отключаем сигналы
			units_dict = self.project.units
			self.units_table.setRowCount(len(units_dict))
			for row, (unit, data) in enumerate(units_dict.items()):
				# Ключ (строка)
				item_key = QTableWidgetItem(unit)
				item_key.setFlags(item_key.flags() & ~Qt.ItemFlag.ItemIsEditable)  # убираем флаг редактирования
				""" 
				item_key.flags() возвращает текущие флаги.
				~Qt.ItemFlag.ItemIsEditable — побитовое НЕ, т.е. маска, где все биты, кроме ItemIsEditable, равны 1.
				& (побитовое И) убирает флаг ItemIsEditable, оставляя остальные без изменений. 
				"""
				self.units_table.setItem(row, 0, item_key)
				# Лейбл (строка)
				item_label = QTableWidgetItem(data.get('label', ''))
				item_label.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				self.units_table.setItem(row, 1, item_label)
				# Округление (число → строка)
				round_val = str(data.get('round', '')) if data.get('round') is not None else ''
				item_round = QTableWidgetItem(round_val)
				item_round.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				self.units_table.setItem(row, 2, item_round)

			self.units_table.resizeColumnsToContents()  # на всякий случай
			self.units_table.blockSignals(False)  # включаем обратно

	def on_units_table_item_changed(self, item):
		if self.project is None or item.column() == 0:
			return  # игнорируем изменения ключа
		row = item.row()
		key_item = self.units_table.item(row, 0)
		if key_item is None:
			return
		key = key_item.text()
		if key not in self.project.units:
			return
		# Получаем новые значения
		label_item = self.units_table.item(row, 1)
		round_item = self.units_table.item(row, 2)
		label = label_item.text() if label_item else ''
		round_str = round_item.text() if round_item else ''
		try:
			round_val = int(round_str) if round_str else 0
		except ValueError:
			round_val = 0
		# Обновляем словарь
		self.project.units[key]['label'] = label
		self.project.units[key]['round'] = round_val

	#--------------------------------
	def _update_table(self, table: QTableWidget, collection: list):
		""" Обновляет таблицу с единственной колонкой """
		if not self.project:
			return
		if collection is None:
			collection = []
			return
		table.blockSignals(True)
		table.setRowCount(len(collection))
		for row, obj in  enumerate(collection):
			item = QTableWidgetItem(obj)
			item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			table.setItem(row, 0, item)
		#table.resizeColumnsToContents()
		table.blockSignals(False)

	def _add_row(self, table: QTableWidget, collection: list):
		if self.project is None:
			return
		collection.append('')
		new_row = table.rowCount()
		table.insertRow(new_row)
		table.editItem(table.item(new_row, 0))

	def _remove_row(self, table: QTableWidget, collection: list):
		current_row = table.currentRow()
		if current_row < 0:
			return
		del collection[current_row]
		self._update_table(table, collection)

	def _on_table_item_changed(self, table: QTableWidget, collection: list, item: QTableWidgetItem):
		if self.project is None:
			return
		row = item.row()
		value = item.text()
		collection[row] = value
		collection.sort()
		self._update_table(table, collection)

	#-------------------------------- Таблица ГИПов -----------------------------------

	def update_chiefs_table(self):
		self._update_table(self.chiefs_table, self.project.chiefs)

	def on_chiefs_table_item_changed(self, item: QTableWidgetItem):
		self._on_table_item_changed(self.chiefs_table, self.project.chiefs, item)

	def add_chiefs_row(self):
		self._add_row(self.chiefs_table, self.project.chiefs)

	def remove_chiefs_row(self):
		self._remove_row(self.chiefs_table, self.project.chiefs)

	#--------------------------- Таблица должностей -----------------------------------
	def update_posts_table(self):
		self._update_table(self.posts_table, self.project.posts)

	def on_posts_table_item_changed(self, item: QTableWidgetItem):
		self._on_table_item_changed(self.posts_table, self.project.posts, item)

	def add_post_row(self):
		self._add_row(self.posts_table, self.project.posts)

	def remove_post_row(self):
		self._remove_row(self.posts_table, self.project.posts)

	#--------------------------- Таблица исполнителей -----------------------------------
	def update_performers_table(self):
		self._update_table(self.performers_table, self.project.performers)
	
	def on_performers_table_item_changed(self, item: QTableWidgetItem):
		self._on_table_item_changed(self.performers_table, self.project.performers, item)

	def add_performer_row(self):
		self._add_row(self.performers_table, self.project.performers)

	def remove_performer_row(self):
		self._remove_row(self.performers_table, self.project.performers)
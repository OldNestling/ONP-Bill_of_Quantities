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
	QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox,  QCheckBox, QDialog, 
	QLineEdit, QFileDialog, QMessageBox, QGridLayout, QListWidget, QAbstractItemView
	)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QColor
from ..ui_utilities import create_separator, create_ok_cancel_buttons
from ..resources.icons import Icons

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from Core.Project import Project

# ---------------------------------------------------------------------------------------
# ================= Модуль импорта библиотек данных из других проектов ==================
# ---------------------------------------------------------------------------------------

class ProjectDataImporter(QDialog):
	""" Диалоговое окно импорта данных  из другого проекта """
	LIB_KEYS = ('performers_lib', 'chiefs_lib', 'posts_lib', 'units_settings',
		'soils_lib', 'sources_lib', 'user_libs', 'machinery_lib')	
	def __init__(self, parent, project):
		super().__init__(parent)
		self.setWindowTitle('Импорт библиотек данных из другого проекта')
		self.setModal(True)
		self.setMinimumWidth(700)
		self.project: Project = project

		# Словарь со всеми библиотеками для импорта
		self.data_from_import: dict | None = None	

		# Словарь с выбором данных для импорта
		self.instructions = {k: False for k in self.LIB_KEYS} 
		self.instructions.update(
            {f'{k}_selection': [] for k in self.LIB_KEYS[4:]}
        )

		self.checkboxes: list[QCheckBox] = []
		self.status_labels: list[QLabel] = []
		self.property_btns: list[QPushButton] = []
		self.setup_ui()

	def setup_ui(self):
		# --- строка пути ---
		self.path_edit = QLineEdit()
		self.path_edit.setPlaceholderText("Путь...")
		self.path_edit.editingFinished.connect(self.__turn_off_import_widgets)

		# Создаём действие с иконкой
		icon = Icons.recolor_icon(Icons.folder_open, QColor('#000000'))
		open_action = QAction(icon, "Обзор...", self)
		open_action.triggered.connect(self.browse_path)

		# Добавляем действие в конец поля ввода
		self.path_edit.addAction(open_action, QLineEdit.ActionPosition.TrailingPosition)

		# кнопка импорта из шаблона
		btn_use_template = QPushButton('Использовать шаблон')
		btn_use_template.setToolTip('Использовать шаблонный проект для импорта')
		btn_use_template.clicked.connect(self.set_template_path)
		# --- // ---

		# --- Кнопка анализа ---
		btn_start_analise = QPushButton('Анализ')
		btn_start_analise.clicked.connect(self.__init__import_data)
		# --- // ---

		# --- Параметры импорта ---
		self.imports_layout = QGridLayout()

		# Заголовок
		headers = (
			'Библиотека<br>данных', 'Наличие данных<br>для импорта',
			'Дополнительные<br>параметры', 'Выбрать библиотеку<br>для импорта'
		)
		for col, head in enumerate(headers):
			text = f'<p align="center"><strong>{head}</strong></p>'
			self.imports_layout.addWidget(QLabel(text), 0, col, Qt.AlignmentFlag.AlignCenter)
		
		self.imports_layout.addWidget(create_separator(), 1, 0, 1, 4)

		# Наименование библиотек
		library_names = (
			'Исполнители', 'ГИПы', 'Должности', 'Еденицы измерения', 
			'Грунты', 'Источники и транспортировка', 'Пользовательские библиотеки', 'Механизация'
		)

		icon_property = Icons.recolor_icon(
			Icons.settings_tab, 
			QColor('#ffffff'),
			QSize(16, 16)
		)
		for row, name in enumerate(library_names, start=2):
			self.imports_layout.addWidget(QLabel(name), row, 0, Qt.AlignmentFlag.AlignLeft)

			# чекбоксы
			checkbox = QCheckBox()
			checkbox.setEnabled(False)
			self.checkboxes.append(checkbox)
			self.imports_layout.addWidget(checkbox, row, 3, Qt.AlignmentFlag.AlignHCenter)

			# индикатор наличия данных
			status_label = QLabel()
			status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			self.status_labels.append(status_label)
			self.imports_layout.addWidget(status_label, row, 1, Qt.AlignmentFlag.AlignCenter)

			# кнопки доп настроек
			if row in range(6, 10):
				property_idx = row - 6	
				btn_property = QPushButton()
				btn_property.setEnabled(False)
				btn_property.setIcon(icon_property)
				btn_property.clicked.connect(
					# idx=property_idx вычисляется в момент создания lambda
					# и «замораживает» нужное значение для каждой кнопки.
					lambda checked=False, idx=property_idx:
						self.open_lib_elements_selector(idx)
				)
				self.property_btns.append(btn_property)
				self.imports_layout.addWidget(btn_property, row, 2, Qt.AlignmentFlag.AlignCenter)
		# --- // ---

		# --- Кнопка импорта ---
		self.btn_import = QPushButton('Импортировать')
		self.btn_import.setEnabled(False)
		self.btn_import.clicked.connect(self.start_import)
		# --- // ---

		# --- Компановка ---
		layout = QVBoxLayout(self)
		path_layout = QHBoxLayout()
		path_layout.addWidget(self.path_edit)
		path_layout.addWidget(btn_use_template)
		layout.addLayout(path_layout)

		layout.addWidget(create_separator())
		layout.addWidget(btn_start_analise)
		layout.setAlignment(btn_start_analise, Qt.AlignmentFlag.AlignHCenter)

		imports_group = QGroupBox(' Параметры импорта ')
		imports_group.setLayout(self.imports_layout)

		layout.addWidget(imports_group)

		layout.addWidget(self.btn_import)
		layout.setAlignment(self.btn_import, Qt.AlignmentFlag.AlignHCenter)
		# --- // ---

	def browse_path(self):
		""" Открывает проводник для выбора каталога """
		directory = QFileDialog.getExistingDirectory(self, "Выберите папку")
		if directory:
			self.path_edit.setText(directory)
		

	def set_template_path(self):
		""" Устанавливает путь проекту-донору из данных о шаблоне """
		if self.project is None:
			return
		path = self.project.get_path_to_template()
		if not path:
			QMessageBox.warning(self, 'Нет данных', 'Отсутсвуют данные о шаблоне')
			return
		self.path_edit.setText(str(path))


	def __turn_off_import_widgets(self):
		""" Отключает и очищаяет все виджеты выбора при отсутсвии данных для импорта """
		for checkbox in self.checkboxes:
			checkbox.setChecked(False)
			checkbox.setEnabled(False)
		for row in range(len(self.status_labels)):
			self.__turn_status_lib(row, False)
		for property_btn in self.property_btns:
			property_btn.setEnabled(False)
		self.btn_import.setEnabled(False)
		self.instructions['user_libs_selection'] = []

	def __turn_status_lib(self, index: int, mod: bool):
		""" Устанавливает иконку о наличии данных для импорта для одной строки """
		if mod:
			icon = Icons.recolor_icon(Icons.status, QColor("#22AD16"))
			self.status_labels[index].setPixmap(icon.pixmap(16, 16))
			self.status_labels[index].setToolTip('Данные доступны для импорта')
		else:
			self.status_labels[index].setPixmap(Icons.close.pixmap(16, 16))
			self.status_labels[index].setToolTip('Данные отсутствуют')
		
	def __init__import_data(self):
		""" Создаёт виджеты с данными о импорте """
		path_to_other_project = self.path_edit.text()
		data = self.project.get_data_from_other_project(path_to_other_project)
		self.data_from_import = data

		if data is None:
			self.__turn_off_import_widgets()
			QMessageBox.warning(
				self, 'Нет данных', 
				'Отсутсвуют данные для импорта.' \
				'Проверьте корректность ссылки на проект или наличие в нем данных для импорта.'
			)
			return
		
		# Берём только те ключи, для которых есть индикатор-лейбл.
		# 'user_libs_selection' — служебное поле (список), а не библиотека,
		# поэтому исключаем его из прохода по status_labels.
		library_keys = [
			key for key in self.instructions.keys()
			if not key.endswith('_selection')
		]
		is_have_data = [bool(data.get(key)) for key in library_keys]

		# отмечаем доступность для импорта
		for r, import_solution in enumerate(is_have_data):
			self.__turn_status_lib(r, import_solution)

			self.checkboxes[r].setEnabled(import_solution)
			if not import_solution:
				self.checkboxes[r].setChecked(False)

		self.btn_import.setEnabled(any(is_have_data))

		# проверяем статус для кнопок параметров импорта бибилиотек
		keys = tuple(self.instructions.keys())
		keys = keys[4:8]
		for i, btn in enumerate(self.property_btns):
			btn.setEnabled(bool(data.get(keys[i], False)))

	def open_lib_elements_selector(self, idx: int):
		""" Открывает окно выбора элементов библиотеки для импорта """
		# получаем ключ выбранной библиотеки
		key = self.LIB_KEYS[4:][idx]	# soils_lib, sources_lib, user_libs, machinery_lib
		# получаем данные для библиотеки
		libs: list[dict] = self.data_from_import.get(key, [])
		if not libs:
			return
		dialog = SelectUserlibsDialog(self, libs, key)
		if dialog.exec() == QDialog.DialogCode.Accepted:
			self.instructions[f'{key}_selection'] = dialog.get_data()
			self.checkboxes[self.LIB_KEYS.index(key)].setChecked(True)

	def __get_instructions(self):
		selections = [checkbox.isChecked() for checkbox in self.checkboxes]
		keys = [key for key in self.instructions.keys() if not key.endswith('_selection')]

		for is_sel, key in enumerate(keys):
			self.instructions[key] = selections[is_sel]

	def start_import(self):
		if not any([cb.isChecked() for cb in self.checkboxes]):
			QMessageBox.warning(
				self, 'Не выбраны библиотеки', 
				'Ни одна библиотека не выбрана для импорта'
			)
			return
		self.__get_instructions()
		results: dict[str, bool|None] = self.project.import_data_from_other_project(
			instructions= self.instructions,
			data = self.data_from_import
		)

		report = []

		for lib, res in results.items():
			if res is None:
				continue
			match lib:
				case 'performers_lib':
					label = 'пользователей'
				case 'chiefs_lib':
					label = 'ГИПов'
				case 'posts_lib': 
					label = 'должностей'
				case 'units_settings': 
					label = 'едениц измерения'
				case 'soils_lib': 
					label = 'грунтов'
				case 'sources_lib': 
					label = 'источников'
				case 'user_libs': 
					label = 'пользовательских библиотек'
				case 'machinery_lib': 
					label = 'механизации'
				case _:
					label = '<неизвестная>'
			color = "#009b2e" if res else "#9b0000"
			res_text = 'Успешно' if res else 'Не удалось'
			line = f'Библиотека {label}: <font color="{color}">{res_text}</font>'
			report.append(line)

		text = 'Импорт завершён со следующими результатами:<br><br>' + '<br>'.join(report)
		msg = QMessageBox(self)
		msg.setWindowTitle('Результаты импорта')
		msg.setIcon(QMessageBox.Icon.Information)
		msg.setTextFormat(Qt.TextFormat.RichText)
		msg.setText(text)
		msg.exec()
		self.accept()


class SelectUserlibsDialog(QDialog):
	""" Открывает окно селектара пользовательских библиотек для импорта """
	def __init__(self, parent, libs_data: dict, key: str):
		super().__init__(parent)
		self.libs_data: list[dict] = libs_data
		self.libname_key = self.get_libname_key(key)
		self.setWindowTitle('Выбор элементов библиотеки')

		self.setup_ui()

	@staticmethod
	def get_libname_key(key):
		""" Получает ключ к наименованию элемента библиотеки """
		match key:
			case 'soils_lib':
				return 'local_name'
			case 'sources_lib' |  'user_libs':
				return 'name'
			case 'machinery_lib':
				return 'work'
			case _:
				return ''

	def setup_ui(self):
		layout = QVBoxLayout(self)

		self.libs_list = QListWidget()
		self.libs_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
		self.fill_libs_list()

		btns = create_ok_cancel_buttons(self, False)

		layout.addWidget(self.libs_list)
		layout.addWidget(btns)

	def fill_libs_list(self):
		self.libs_list.clear()
		if not self.libs_data or not isinstance(self.libs_data, list):
			return
		for lib in self.libs_data:
			lib_name = lib.get(self.libname_key)
			if not lib_name:
				continue
			self.libs_list.addItem(lib_name)

	def get_data(self) -> list[int]:
		indexes = self.libs_list.selectedIndexes()
		selected_libs = [index.row() for index in indexes]
		return selected_libs

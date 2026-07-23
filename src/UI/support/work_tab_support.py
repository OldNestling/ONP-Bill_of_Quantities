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

import re
from PyQt6.QtWidgets import (
	QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,	QLineEdit, QPlainTextEdit, 
	QTextEdit, QComboBox, QTreeView, QFrame, QStyledItemDelegate, QStyle, QAbstractItemDelegate,
	QCompleter, QCheckBox, QFrame
	)
from PyQt6.QtGui import (QColor, QTextCursor, QTextCharFormat, QIntValidator, QFont,
						QTextDocument, QTextBlockFormat, QSyntaxHighlighter)
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex, QEvent, QTimer
from ..ui_utilities import create_separator
from ..icons import Icons
from Core.BoQ import Section
from Core.Computing_Module import FUNCTIONS

class DataEditorWidget(QWidget):
	"""Виджет редактирования: строка формул + редактор колонки 3."""
	def __init__(self, project, parent=None):
		super().__init__(parent)
		self.project = project
		self.model = None
		self.current_index = QModelIndex()
		self._updating = False		# Флаг, чтобы избежать рекурсивных обновлений
		self.highlighter = None		# для подсветки в default_editor

		self.setup_ui()
		self.set_project(project)

	def setup_ui(self):
		main_layout = QHBoxLayout(self)
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.setSpacing(5)

		# --- Левая панель с псевдонимами и функциями ---
		left_panel = QWidget()
		left_layout = QVBoxLayout(left_panel)
		left_layout.setContentsMargins(0, 0, 0, 0)
		left_layout.setSpacing(3)

		# 1. Строка для псевдонимов проекта
		alias_row = QWidget()
		alias_layout = QHBoxLayout(alias_row)
		alias_layout.setContentsMargins(0, 0, 0, 0)
		alias_layout.setSpacing(2)

		self.alias_edit = QLineEdit()
		self.alias_edit.setPlaceholderText("Псевдоним данных")
		self.alias_edit.setFixedWidth(200)
		alias_layout.addWidget(self.alias_edit)

		alias_btn = QPushButton()
		alias_btn.setIcon(Icons.move_right)
		alias_btn.setFixedWidth(25)
		alias_btn.setToolTip("Добавить псевдоним в конец формулы")
		alias_btn.clicked.connect(self.insert_alias)
		alias_layout.addWidget(alias_btn)

		left_layout.addWidget(alias_row)

		# 2. Строка для выбора функций
		func_row = QWidget()
		func_layout = QHBoxLayout(func_row)
		func_layout.setContentsMargins(0, 0, 0, 0)
		func_layout.setSpacing(2)

		self.func_combo = QComboBox()
		self.func_combo.setEditable(False)
		self.func_combo.setToolTip("Выберите функцию для вставки")
		self.func_combo.setFixedWidth(200)
		self.populate_functions()
		func_layout.addWidget(self.func_combo)

		func_btn = QPushButton()
		func_btn.setIcon(Icons.move_right)
		func_btn.setFixedWidth(25)
		func_btn.setToolTip("Добавить функцию в конец формулы")
		func_btn.clicked.connect(self.insert_function)
		func_layout.addWidget(func_btn)

		left_layout.addWidget(func_row)
		left_layout.addStretch()

		main_layout.addWidget(left_panel)

		# 3. Строка формул (для любой колонки)
		self.default_editor = QPlainTextEdit(self)
		self.default_editor.setMinimumWidth(300)
		self.default_editor.setContentsMargins(5,1,5,1)
		self.default_editor.textChanged.connect(self.on_default_editor_changed)
		main_layout.addWidget(self.default_editor, stretch=1)

		# 4. Редактор для колонки 3
		self.col3_editor = UnitEditor(project=self.project, parent=self)
		self.col3_editor.dataChanged.connect(self.on_col3_data_changed)
		main_layout.addWidget(self.col3_editor)

		main_layout.addStretch()

	
	def populate_functions(self):
		"""Заполняет комбобокс функциями """
		functions_dict = FUNCTIONS
		self.func_combo.clear()
		for func_name in functions_dict.keys():
			self.func_combo.addItem(func_name)

	def insert_alias(self):
		text = self.alias_edit.text().strip()
		if text:
			self._insert_at_end(f'@{text}')

	def insert_function(self):
		func_name = self.func_combo.currentText()
		if func_name:
			self._insert_at_end(f"{func_name}()")

	def _insert_at_end(self, text):
		cursor = self.default_editor.textCursor()
		cursor.movePosition(QTextCursor.MoveOperation.End)
		self.default_editor.setTextCursor(cursor)
		self.default_editor.insertPlainText(text)
		self.default_editor.setFocus()

	def set_project(self, project):
		self.project = project
		self.col3_editor.set_project(project)
		if self.project:
			all_alias = project.get_all_library_paths()
			alias_completer = QCompleter(all_alias)
			alias_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
			alias_completer.setFilterMode(Qt.MatchFlag.MatchContains)
			self.alias_edit.setCompleter(alias_completer)

	def setModel(self, model):
		"""Устанавливает модель данных и подключается к её сигналам."""
		if self.model == model:
			return
		# Отключаем сигналы от старой модели
		if self.model:
			try:
				self.model.dataChanged.disconnect(self._on_model_data_changed)
				self.model.modelReset.disconnect(self._on_model_reset)
				self.model.layoutChanged.disconnect(self._on_model_layout_changed)
			except TypeError:
				pass			# если сигнал не был подключён

		self.model = model

		# Подключаем сигналы новой модели
		if self.model:
			self.model.dataChanged.connect(self._on_model_data_changed)
			self.model.modelReset.connect(self._on_model_reset)
			self.model.layoutChanged.connect(self._on_model_layout_changed)	
		self.col3_editor.setModel(model)
		self.update_editors()

	def setCurrentIndex(self, index: QModelIndex):
		"""Принимает QModelIndex текущей ячейки."""
		if self.current_index == index:
			return
		self.current_index = index
		self.update_editors()

	def update_editors(self):
		"""Обновляет оба редактора данными из self.current_index."""
		if self._updating:
			return
		self._updating = True
		try:
			if not self.model or not self.current_index.isValid():
				self.default_editor.setEnabled(False)
				self.default_editor.clear()
				self._remove_highlighter()
				self.col3_editor.setEnabled(False)
				self.col3_editor.setCurrentIndex(QModelIndex())
				return

			flags = self.model.flags(self.current_index)
			editable = bool(flags & Qt.ItemFlag.ItemIsEditable)
			# --- Редактор для текущей колонки ---
			self.default_editor.setEnabled(editable)
			if editable:
				data = self.model.data(self.current_index, Qt.ItemDataRole.EditRole)
				self.default_editor.setPlainText(str(data) if data is not None else "")
			else:
				self.default_editor.clear()
			
			# --- Управление подсветкой для столбцов 2, 5, 7 ---
			col = self.current_index.column()
			if editable and col in (2, 5, 7):
				self._ensure_highlighter()
			else:
				self._remove_highlighter()

			# --- Редактор колонки 3 ---
			self.col3_editor.setEnabled(True)  # внутри будет проверка Section
			self.col3_editor.setCurrentIndex(self.current_index)
		finally:
			self._updating = False
	
	def _ensure_highlighter(self):
		"""Создаёт highlighter для default_editor, если его нет."""
		if self.highlighter is None:
			self.highlighter = FormulaHighlighter(self.default_editor.document())

	def _remove_highlighter(self):
		"""Удаляет highlighter, если он существует."""
		if self.highlighter is not None:
			self.highlighter.deleteLater()
			self.highlighter = None

	def on_default_editor_changed(self):
		"""Сохраняет изменения из default_editor в модель."""
		if self._updating:
			return
		if not self.model or not self.current_index.isValid():
			return
		if not (self.model.flags(self.current_index) & Qt.ItemFlag.ItemIsEditable):
			return

		new_text = self.default_editor.toPlainText()
		old_data = self.model.data(self.current_index, Qt.ItemDataRole.EditRole)
		if new_text == str(old_data) if old_data is not None else "":
			return

		# Блокируем сигналы модели, чтобы избежать циклического обновления
		self._updating = True
		try:
			self.model.setData(self.current_index, new_text, Qt.ItemDataRole.EditRole)
		finally:
			self._updating = False

	def on_col3_data_changed(self):
		"""Слот для сигнала от Column3Editor (данные уже сохранены в модель)."""
		if not self._updating and self.model and self.current_index.isValid():
			self.model.dataChanged.emit(self.current_index, self.current_index, [Qt.ItemDataRole.DisplayRole])
			self.model.layoutChanged.emit()

	def clear(self):
		self.model = None
		self.current_index = QModelIndex()
		self.default_editor.clear()
		self.default_editor.setEnabled(False)
		self.col3_editor.clear()
		self._remove_highlighter()

	def _on_model_data_changed(self, top_left, bottom_right, roles):
		"""Слот для сигнала dataChanged модели."""
		if self._updating:
			return
		# Если текущий индекс валиден и попадает в диапазон изменённых, обновляем редакторы
		if self.current_index.isValid() and self.current_index.model() == self.model:
			# Проверяем, находится ли current_index в интервале [top_left, bottom_right]
			if top_left <= self.current_index <= bottom_right:
				self.update_editors()
			# Можно также обновлять всегда, если текущий индекс валиден, но это менее эффективно
			# self.update_editors()

	def _on_model_reset(self):
		"""Слот для сигнала modelReset модели."""
		if self._updating:
			return
		# Модель сброшена – текущий индекс стал невалидным
		self.current_index = QModelIndex()
		self.update_editors()

	def _on_model_layout_changed(self):
		"""Слот для сигнала layoutChanged модели."""
		if self._updating:
			return
		# Структура изменилась – возможно, индекс стал невалидным
		if self.current_index.isValid() and self.current_index.model() == self.model:
			# Проверяем, остался ли индекс валидным после изменения layout
			# (некоторые индексы могли стать недействительными)
			if not self.current_index.isValid():
				self.current_index = QModelIndex()
		else:
			self.current_index = QModelIndex()
		self.update_editors()



class UnitEditor(QWidget):
	"""Редактор для колонки 3: выпадающий список + поле ввода целого числа (точность)."""
	dataChanged = pyqtSignal()
	
	def __init__(self, project, parent=None):
		super().__init__(parent)
		self.project = project
		self.model = None
		self.current_index = QModelIndex()
		self.setup_ui()
		
	def setup_ui(self):
		main_layout = QVBoxLayout(self)
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.setSpacing(5)

		# --------- Лейблы ---------

		headers_layout = QHBoxLayout()

		header1 = QLabel('<b>Еденица<br>измерения</b>')
		header1.setContentsMargins(8, 5, 8, 0)
		header1.setAlignment(Qt.AlignmentFlag.AlignCenter)
		headers_layout.addWidget(header1)

		headers_layout.addWidget(create_separator(QFrame.Shape.VLine)) # ---

		header2 = QLabel('<b>Переопределение<br>округления</b>')

		header2.setContentsMargins(5, 5, 5, 0)
		header2.setAlignment(Qt.AlignmentFlag.AlignCenter)
		headers_layout.addWidget(header2)
		headers_layout.addStretch()

		main_layout.addLayout(headers_layout)
		#main_layout.addStretch()

		# --------- Виджеты --------

		widgets_layout = QHBoxLayout()
		widgets_layout.setContentsMargins(0, 0, 0, 0)
		widgets_layout.setSpacing(5)
		
		# Выпадающий список (нередактируемый)
		self.combo = QComboBox(self)
		self.combo.setEditable(False)

		# загрузка библиотеки едениц измерения
		self.units_keys = []
		self.units_labels = []
		if self.project:
			units_dict: dict = self.project.units
			for key, data in units_dict.items():
				self.units_keys.append(key)
				self.units_labels.append(data['label'])
		
		self.combo.addItems(self.units_labels)
		self.combo.currentIndexChanged.connect(self.on_data_changed)
		widgets_layout.addWidget(self.combo)
		
		# Поле ввода с валидацией целых чисел
		self.custom_round_edit = QLineEdit(self)
		self.custom_round_edit.setPlaceholderText("Задать точность")
		self.custom_round_edit.setValidator(QIntValidator(0, 100, self))
		self.custom_round_edit.setMaximumWidth(150)
		self.custom_round_edit.textChanged.connect(self.on_data_changed)
		widgets_layout.addWidget(self.custom_round_edit)

		#widgets_layout.addStretch()
		main_layout.addLayout(widgets_layout)
		main_layout.addStretch()

	def load_units(self):
		"""Загружает единицы измерения из проекта в комбобокс."""
		if not self.project:
			return
		self.combo.clear()
		units_dict = self.project.units
		self.units_keys = []
		self.units_labels = []
		for key, data in units_dict.items():
			self.units_keys.append(key)
			self.units_labels.append(data['label'])
		self.combo.addItems(self.units_labels)
	
	def set_project(self, project):
		self.project = project
		self.load_units()
		# Если есть текущая строка, обновить отображение
		if self.model and self.current_index >= 0:
			self.setCurrentIndex(self.current_index)


	def setModel(self, model):
		self.model = model
	
	def setCurrentIndex(self, index: QModelIndex):
		"""Принимает QModelIndex любой колонки, но работает с колонкой 3 той же строки."""
		self.current_index = index
		self.update_display()
	
	def update_display(self):
		"""Загружает данные из модели для колонки 3."""
		if not self.model or not self.current_index.isValid():
			self.setEnabled(False)
			return
		# Запрещаем редактирование архивных данных
		#if isinstance(self.model, ArchiveModel):
		#	self.setEnabled(False)
		#	return

		# Проверяем, является ли элемент Section
		item = self.current_index.internalPointer()
		if isinstance(item, Section):
			self.setEnabled(False)
			self.combo.setCurrentIndex(-1)
			self.custom_round_edit.clear()
			return

		self.setEnabled(True)

		# Получаем индекс для колонки 3 той же строки
		col3_index = self.model.index(self.current_index.row(), 3, self.current_index.parent())
		if not col3_index.isValid():
			return

		# Считываем данные
		raw_unit = self.model.data(col3_index, Qt.ItemDataRole.EditRole)
		custom_round = item.custom_round if hasattr(item, 'custom_round') else None

		# Устанавливаем комбобокс
		if raw_unit in self.units_keys:
			self.combo.setCurrentIndex(self.units_keys.index(raw_unit))
		else:
			self.combo.setCurrentIndex(0)

		# Устанавливаем поле точности
		self.custom_round_edit.setText(str(custom_round) if custom_round is not None else "")

	def on_data_changed(self):
		"""Сохраняет изменения в модель для колонки 3."""
		if not self.model or not self.current_index.isValid():
			return

		item = self.current_index.internalPointer()
		if isinstance(item, Section):
			return

		col3_index = self.model.index(self.current_index.row(), 3, self.current_index.parent())
		if not col3_index.isValid():
			return

		# Получаем новые значения
		unit_key = self.units_keys[self.combo.currentIndex()]
		custom_round_text = self.custom_round_edit.text().strip()
		custom_round = int(custom_round_text) if custom_round_text else None

		# Обновляем модель
		self.model.setData(col3_index, unit_key, Qt.ItemDataRole.EditRole)
		if hasattr(item, 'custom_round'):
			item.custom_round = custom_round
			self.model.dataChanged.emit(col3_index, col3_index, [Qt.ItemDataRole.DisplayRole])

		if self.model.manager:
			self.model.manager.is_modified = True
		self.dataChanged.emit()
	
	def clear(self):
		self.model = None
		self.current_index = QModelIndex()
		self.setEnabled(False)
		self.combo.setCurrentIndex(-1)
		self.custom_round_edit.clear()



class FormulaHighlighter(QSyntaxHighlighter):
	"""Подсветка ссылок на позиции/ресурсы и библиотечные пути."""

	# Паттерны для поиска
	PATTERN_POS = re.compile(
		r'(\$?)Р(\d+)\.(\$?)П(\d+)(?:\.(\$?)(\d+))?(_Прим)?'
	)
	PATTERN_LIB = re.compile(
		r'@[^\s.,+\-*/()]+(?:\.[^\s.,+\-*/()]+)+'
	)

	def __init__(self, document):
		super().__init__(document)
		# Список паттернов с базовым смещением оттенка для каждого типа
		self.patterns = [
			(self.PATTERN_POS, 0),   # ссылки на позиции — оттенок от 0
			(self.PATTERN_LIB, 180)  # библиотечные ссылки — оттенок от 180°
		]

	def highlightBlock(self, text: str):
		"""Обрабатывает один блок текста."""
		for pattern, hue_offset in self.patterns:
			for match in pattern.finditer(text):
				start = match.start()
				length = match.end() - start
				matched_text = match.group(0)
				color = self._color_for_text(matched_text, hue_offset)
				fmt = QTextCharFormat()
				fmt.setForeground(color)
				self.setFormat(start, length, fmt)

	@staticmethod
	def _color_for_text(text: str, hue_offset: int = 0) -> QColor:
		"""Генерирует цвет на основе хеша строки."""
		# Берём хеш, ограничиваем до 32 бит
		h = hash(text) & 0xFFFFFFFF
		# Оттенок равномерно распределяем с помощью золотого сечения
		hue = (h * 0.618033988749895) % 1.0
		hue = int(hue * 360) + hue_offset
		hue %= 360
		# Насыщенность и яркость фиксированы для читаемости
		return QColor.fromHsv(hue, 255, 150)



class BoQItemDelegate(QStyledItemDelegate):
	"""
	Делегат для отображения и редактирования данных в QTreeView с моделью BoQ.
	Особенности:
	  - Автоматическая высота строки с переносом по словам.
	  - Жирный шрифт для разделов в столбце «Наименование».
	  - Поддержка пользовательских стилей (цвет фона / текста) для столбцов 2,5,6,7.
	  - Выпадающий список для столбца «Ед. изм.» (ключи -> метки).
	  - Редактор QTextEdit для остальных редактируемых столбцов.
	"""

	# Индексы столбцов, содержимое которых выравнивается по центру
	CENTERED_COLUMNS = {0, 1, 3, 4, 5, 8}

	def __init__(self, units_dict: dict, positions_type: tuple, parent=None):
		"""
		:param units_dict: словарь единиц измерения вида {'meter': {'label': 'м', 'round': 2}, ...}
		"""
		super().__init__(parent)
		self.units_dict = units_dict
		self.position_types = positions_type
		self.margin = 4
		self.grid_color = QColor('#d0d0d0')

	# ----------------------------------------------------------------------
	# Вспомогательные методы
	# ----------------------------------------------------------------------

	def is_section_item(self, index: QModelIndex) -> bool:
		"""Возвращает True, если элемент является разделом (Section)."""
		item = index.internalPointer()
		return isinstance(item, Section)

	def get_cell_style(self, index: QModelIndex):
		"""
		Извлекает цвета фона и текста из style_manager элемента (если заданы).
		Возвращает кортеж (background_color, text_color) в виде строк HEX или None.
		"""
		item = index.internalPointer()
		col = index.column()

		if not hasattr(item, 'style_manager') or item.style_manager is None:
			return None, None

		style_dict = None
		if col == 0:
			if item.status:
				style_dict = {'background_color': "#68be5d"}
			elif item.status_correct:
				style_dict = {'background_color': "#7b92df"}
			else:
				style_dict = {'background_color': "#f05353"}
		elif col == 2:
			style_dict = item.style_manager.col_2
		elif col == 5:
			style_dict = item.style_manager.col_5
		elif col == 6:
			style_dict = item.style_manager.col_6
		elif col == 7:
			style_dict = item.style_manager.col_7
		elif col == 9:
			style_dict = item.style_manager.col_9

		if style_dict:
			bg = style_dict.get('background_color')
			fg = style_dict.get('text_color')
			return bg, fg
		return None, None

	# ----------------------------------------------------------------------
	# Отрисовка и размер
	# ----------------------------------------------------------------------

	def _draw_grid(self, painter, option, index):
		"""Рисует тонкие границы ячейки."""
		painter.save()
		painter.setPen(self.grid_color)
		painter.drawRect(option.rect)
		painter.restore()

	def paint(self, painter, option, index):
		item = index.internalPointer()
		if item is None:
			return
		
		painter.save()
		selected = option.state & QStyle.StateFlag.State_Selected
		bg_color, text_color = self.get_cell_style(index) # Получаем кастомные стили (если есть)

		# Приоритет фона: выделение > кастомный > стандартный (с учётом раздела)
		if selected:
			bg_color = option.palette.highlight().color().name()
		elif bg_color is None and self.is_section_item(index):
			bg_color = "#f5f5f5"  # нейтральный фон для невыделенных разделов

		if bg_color:
			painter.fillRect(option.rect, QColor(bg_color))
		elif index.column() == 9:
			painter.fillRect(option.rect, QColor("#f5f5f5"))
		else:
			painter.fillRect(option.rect, option.palette.base())

		# --- Текст ---
		raw_value = index.data(Qt.ItemDataRole.DisplayRole)
		text = str(raw_value) if raw_value is not None else ""
		doc = QTextDocument()

		# Шрифт (жирный для разделов в столбце "Наименование")
		if self.is_section_item(index) and index.column() == 2:
			font = QFont(option.font)
			font.setBold(True)
			doc.setDefaultFont(font)
	
		else:
			doc.setDefaultFont(option.font)
		
		doc.setPlainText(text)
		text_width = option.rect.width() - 2 * self.margin
		doc.setTextWidth(max(text_width, 1))

		# Приоритет цвета текста: выделение -> кастомный -> стандартный
		if selected:
			color = option.palette.highlightedText().color()
		elif text_color:
			color = QColor(text_color)
		else:
			color = option.palette.text().color()

		cursor = QTextCursor(doc)
		cursor.select(QTextCursor.SelectionType.Document)
		fmt = QTextCharFormat()
		fmt.setForeground(color)
		cursor.mergeCharFormat(fmt)

		# Ширина и перенос
		text_width = option.rect.width() - 2 * self.margin
		doc.setTextWidth(max(text_width, 1))

		# Выравнивание по центру для нужных столбцов
		if index.column() in self.CENTERED_COLUMNS:
			block_fmt = QTextBlockFormat()
			block_fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
			cursor = QTextCursor(doc)
			cursor.select(QTextCursor.SelectionType.Document)
			cursor.mergeBlockFormat(block_fmt)


		painter.translate(option.rect.x() + self.margin, option.rect.y() + self.margin)
		doc.drawContents(painter)
		painter.translate(-option.rect.x() - self.margin, -option.rect.y() - self.margin)

		# Границы ячейки
		self._draw_grid(painter, option, index)

		painter.restore()

	def sizeHint(self, option, index):
		raw_value = index.data(Qt.ItemDataRole.DisplayRole)
		text = str(raw_value) if raw_value is not None else ""
		doc = QTextDocument()

		if self.is_section_item(index) and index.column() == 2:
			font = QFont(option.font)
			font.setBold(True)
			doc.setDefaultFont(font)
		else:
			doc.setDefaultFont(option.font)

		doc.setPlainText(text)

		width = option.rect.width()
		if width <= 0:
			tree_view = self.parent()
			if tree_view and isinstance(tree_view, QTreeView):
				width = tree_view.columnWidth(index.column())
			else:
				width = 100
		text_width = width - 2 * self.margin
		doc.setTextWidth(max(text_width, 1))

		size = doc.size().toSize()
		size.setHeight(size.height() + 2 * self.margin)
		return size

	# ----------------------------------------------------------------------
	# ========================== Редактирование ============================
	# ----------------------------------------------------------------------

	def createEditor(self, parent, option, index):
		if not (index.flags() & Qt.ItemFlag.ItemIsEditable):
			return None

		col = index.column()
		# Столбец «Ед. изм.» (3) или «Тип позиции» (8) — выпадающий список
		if not self.is_section_item(index) and  (col == 3 or col ==8):
			editor = QComboBox(parent)
			if col == 3:
				for key, data in self.units_dict.items():
					editor.addItem(data['label'], key)
			else:
				for type_name in self.position_types:
					editor.addItem(type_name)
			return editor

		# Остальные редактируемые столбцы — многострочное текстовое поле
		editor = QTextEdit(parent)
		editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
		editor.setFrameStyle(0)  # без рамки

		# Для столбцов 2, 5, 7 подключаем подсветку
		if col in (2, 5, 7):
			editor.highlighter = FormulaHighlighter(editor.document())

		editor.installEventFilter(self)
		return editor
	
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
			elif key == Qt.Key.Key_Tab:
				# Tab — передаём фокус следующему виджету (не обрабатываем сами)
				return False
			elif key == Qt.Key.Key_Backtab:
				# Shift+Tab — предыдущий фокус
				return False
		# Для остальных событий вызываем базовый обработчик
		return super().eventFilter(obj, event)

	def setEditorData(self, editor, index):
		value = index.data(Qt.ItemDataRole.EditRole)
		if isinstance(editor, QComboBox):
			if index.column() == 3:
				# value может быть ключом (например, 'meter')
				idx = editor.findData(value)
				if idx >= 0:
					editor.setCurrentIndex(idx)
				else:
					editor.setCurrentIndex(0)
			else:
				item = index.internalPointer()
				editor.setCurrentText(item.type)
		else:
			# Преобразуем в строку, даже если None или число
			editor.setPlainText(str(value) if value is not None else "")

	def setModelData(self, editor, model, index):
		if isinstance(editor, QComboBox):
			if index.column() == 3:
				key = editor.currentData()
				model.setData(index, key, Qt.ItemDataRole.EditRole)
			else:
				text = editor.currentText()
				model.setData(index, text, Qt.ItemDataRole.EditRole)
		else:
			text = editor.toPlainText()
			model.setData(index, text, Qt.ItemDataRole.EditRole)

		# Принудительное обновление геометрии строк после изменения данных
		tree_view = self.parent()
		if tree_view and isinstance(tree_view, QTreeView):
			tree_view.scheduleDelayedItemsLayout()
			tree_view.viewport().update()

	def updateEditorGeometry(self, editor, option, index):
		editor.setGeometry(option.rect)

class SearchBar(QWidget):
	search_requested = pyqtSignal(str, bool, bool)
	next_requested = pyqtSignal()
	prev_requested = pyqtSignal()
	closed = pyqtSignal()

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setFixedHeight(35)
		layout = QHBoxLayout(self)
		layout.setContentsMargins(4, 4, 4, 4)
		layout.setSpacing(8)

		self.label = QLabel("Найти:")
		layout.addWidget(self.label)

		self.line_edit = QLineEdit()
		self.line_edit.setPlaceholderText("Поиск...")
		self.line_edit.returnPressed.connect(self._on_return_pressed)
		layout.addWidget(self.line_edit, 1)

		self.next_btn = QPushButton("Далее")
		self.next_btn.clicked.connect(self.next_requested)
		layout.addWidget(self.next_btn)

		self.prev_btn = QPushButton("Назад")
		self.prev_btn.clicked.connect(self.prev_requested)
		layout.addWidget(self.prev_btn)

		self.case_check = QCheckBox("Учитывать регистр")
		layout.addWidget(self.case_check)

		self.all_columns_check = QCheckBox("Все столбцы")
		self.all_columns_check.setChecked(True)
		layout.addWidget(self.all_columns_check)

		close_btn = QPushButton("✕")
		close_btn.setFixedSize(20, 20)
		close_btn.clicked.connect(self.hide)
		layout.addWidget(close_btn)

		self._timer = QTimer()
		self._timer.setSingleShot(True)
		self._timer.setInterval(300)
		self._timer.timeout.connect(self._emit_search)
		self.line_edit.textChanged.connect(self._timer.start)

	def _on_return_pressed(self):
		self._emit_search()
		self.next_requested.emit()

	def _emit_search(self):
		text = self.line_edit.text()
		if text:
			self.search_requested.emit(
				text,
				self.case_check.isChecked(),
				self.all_columns_check.isChecked()
			)
		else:
			self.search_requested.emit("", False, False)

	def focusInEvent(self, event):
		self.line_edit.setFocus()
		super().focusInEvent(event)

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Escape:
			self.hide()
		else:
			super().keyPressEvent(event)
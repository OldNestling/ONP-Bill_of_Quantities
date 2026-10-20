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
	QWidget,QVBoxLayout, QMessageBox, QHeaderView, QMenu, QApplication, 
	QSplitter, QAbstractItemView, QLineEdit, QTextEdit
	)
from PyQt6.QtGui import QAction, QColor, QTextCursor
from PyQt6.QtCore import Qt, QModelIndex, QEvent, QTimer

from ..resources.icons import Icons
from Core.BoQ import BoQ_manager, Section, Work, Resource, PositionLine
from Core.Utilities import convert_value
from ..support.work_tab_support import BoQItemDelegate
from ..support.work_tab_models import Model, ArchiveModel
from .treeview import SmoothTreeView


class BoQ_View(QWidget):
	def __init__(self, parent, project, file_manager: BoQ_manager):
		super().__init__(parent)
		self.project = project
		self.manager = file_manager			# Класс управления данными файла (ведомости)
		self._shutdown_called = False
		self.setup_ui()
		self._init_actions()

		self._search_results = []
		self._search_current = -1
		self._search_text = ""
		self._search_case = False
		self._search_all_cols = True

	def setup_ui(self):
		layout = QVBoxLayout(self)
		splitter = QSplitter(Qt.Orientation.Vertical)
		splitter.setChildrenCollapsible(True)
	
		# ---------------------------- Основная таблица данных --------------------------

		self.view = SmoothTreeView()
		self.view.installEventFilter(self)
		self.model = Model(manager=self.manager, parent= self)
		self.view.setModel(self.model)

		# Настройка заголовков
		header = self.view.header()
		font = header.font()
		font.setBold(True)
		header.setFont(font)
		header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

		# --- Настройка ширины столбцов и режимов изменения размера ---
		# Устанавливаем интерактивный режим для всех столбцов по умолчанию
		for col in range(self.model.columnCount()):
			header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)

		# Фиксируем ширину столбцов ( № п/п)
		header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)

		# Начальные ширины для остальных столбцов
		self.view.setColumnWidth(0, 180)
		self.view.setColumnWidth(1, 50)
		self.view.setColumnWidth(2, 300)	# Наименование
		self.view.setColumnWidth(3, 65)		# Ед. изм.
		self.view.setColumnWidth(4, 100)   	# Количество
		self.view.setColumnWidth(5, 200)   	# Формула
		self.view.setColumnWidth(6, 200)   	# Ссылки
		self.view.setColumnWidth(7, 150)   	# Комментарий
		self.view.setColumnWidth(8, 90)   	# Тип позиции
		self.view.setColumnWidth(9, 150)   	# Локальный комментарий

		# Отключаем автоматическое растяжение последней секции,
		# чтобы при необходимости появлялась горизонтальная прокрутка
		header.setStretchLastSection(False)

		# Подключаем сигнал изменения ширины столбца для пересчёта высоты строк
		header.sectionResized.connect(self.on_section_resized)

		position_types = self.project.work_modes.get('position_types', None)
		position_types = tuple(position_types) if position_types else tuple()
		delegate = BoQItemDelegate(self.project.units, position_types, self.view)
		self.view.setItemDelegate(delegate)

		# header.sectionResized.connect(self.on_section_resized)
		self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
		self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.view.customContextMenuRequested.connect(self.show_context_menu)

		self.view.expandAll()

		splitter.addWidget(self.view)

		# -------------------------- Таблица архивных данных ----------------------------

		self.archive_view = SmoothTreeView()
		self.archive_model = ArchiveModel(self.manager, self)
		self.archive_view.setModel(self.archive_model)

		# Настройки архива: без редактирования, но с возможностью выделения
		self.archive_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		self.archive_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.archive_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.archive_view.customContextMenuRequested.connect(self.show_archive_context_menu)

		# Можно использовать того же делегата (он не редактирует, если флаги запрещают)
		delegate = BoQItemDelegate(self.project.units, self.project.work_modes.get('position_types', ()), self.archive_view)
		self.archive_view.setItemDelegate(delegate)

		# Настройка ширины столбцов (повторяем настройки основной таблицы)
		header = self.archive_view.header()
		for col in range(self.archive_model.columnCount()):
			header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
		header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
		header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
		self.archive_view.setColumnWidth(0, 150)
		self.archive_view.setColumnWidth(1, 50)
		self.archive_view.setColumnWidth(2, 300)
		self.archive_view.setColumnWidth(3, 60)
		self.archive_view.setColumnWidth(4, 100)
		self.archive_view.setColumnWidth(5, 200)
		self.archive_view.setColumnWidth(6, 200)
		self.archive_view.setColumnWidth(7, 150)
		self.archive_view.setColumnWidth(8, 90)
		self.archive_view.setColumnWidth(9, 150)
		header.setStretchLastSection(False)

		self.archive_view.expandAll()
		splitter.addWidget(self.archive_view)
		# -------------------------------------------------------------------------------
		# Настройка вертикального сплиттера
		splitter.setSizes([500, 100])			# начальные высоты
		splitter.setStretchFactor(0, 1)			# основная таблица забирает всё свободное место
		splitter.setStretchFactor(1, 0)			# архив не растягивается
		layout.addWidget(splitter)

	def _init_actions(self):
		""" Создаёт действия с шорткатами для контекстного окна """
		self.copy_address_action = QAction('Копировать ссылку на позицию', self)
		self.copy_address_action.setShortcut('Ctrl+`')
		self.copy_address_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
		self.copy_address_action.triggered.connect(self._copy_current_address)
		self.view.addAction(self.copy_address_action)   # регистрируем на view

	
	def eventFilter(self, obj, event):
		if obj is self.view and event.type() == QEvent.Type.KeyPress:
			# --- Delete ---
			if event.key() == Qt.Key.Key_Delete:
				self.clear_selected_cells()
				self.view.viewport().update()
				return True
			# --- Ctrl+V (вставка текста) ---
			elif (event.key() == Qt.Key.Key_V and 
		 		event.modifiers() & Qt.KeyboardModifier.ControlModifier):
				self._paste_text()
				return True
			# --- Печатный символ (запуск редактирования) ---
			# Проверяем, что нажата обычная клавиша без Ctrl/Alt/Meta,
			# и что текст символа печатный.
			mods = event.modifiers()
			if (not (mods & Qt.KeyboardModifier.ControlModifier) and
				not (mods & Qt.KeyboardModifier.AltModifier) and
				not (mods & Qt.KeyboardModifier.MetaModifier) and
				event.text() and event.text().isprintable()):
				# Запускаем редактирование с подстановкой символа
				self.start_editing_with_char(event.text())
				return True
		return super().eventFilter(obj, event)

	def on_section_resized(self, logicalIndex, oldSize, newSize):
		"""Вызывается при изменении ширины столбца. Пересчитываем высоту строк."""
		self.view.scheduleDelayedItemsLayout()

	def shutdown(self):
		"""Явное освобождение ресурсов перед удалением виджета"""
		if self._shutdown_called:
			return
		self._shutdown_called = True

		# Отключаем модель от view
		if self.view.model() is self.model:
			self.view.setModel(None)
		if self.archive_view.model() is self.archive_model:
			self.archive_view.setModel(None)

		# Удаляем делегаты
		self.view.setItemDelegate(None)
		self.archive_view.setItemDelegate(None)

		# Разрываем ссылки на manager, но не вызываем beginResetModel/deleteLater вручную:
		# вручную: модели — дети BoQ_View и будут удалены вместе с ним.
		if self.model:
			self.model.manager = None
		
		if self.archive_model:
			self.archive_model.manager = None

		# Удаляем менеджер (если на него нет других ссылок)
		if self.manager:
			# Если в менеджере есть циклические ссылки – разорвать их
			if hasattr(self.manager, 'cleanup'):
				self.manager.cleanup()
			self.manager = None
		
		sel_model1 = self.view.selectionModel()
		# Блокируем selectionModel, чтобы не возникало сигналов после удаления
		if sel_model1:
			sel_model1.blockSignals(True)
		sel_mode2 = self.archive_view.selectionModel()
		if sel_mode2:
			sel_mode2.blockSignals(True)

	# ------------------------- Поиск -------------------------------

	def perform_search(self, text, case_sensitive, all_columns):
		self._clear_search()
		if not text:
			return
		self._search_text = text
		self._search_case = case_sensitive
		self._search_all_cols = all_columns

		model = self.model
		if not model:
			return

		results = []
		self._collect_matches(model, QModelIndex(), results)

		self._search_results = results
		if results:
			self._search_current = 0
			self._goto_current_match()
		else:
			QMessageBox.information(self, "Поиск", "Ничего не найдено.")
			self._search_current = -1

	def _collect_matches(self, model, parent_index, results):
		rows = model.rowCount(parent_index)
		cols = model.columnCount(parent_index)
		for row in range(rows):
			for col in range(cols):
				if not self._search_all_cols and col != Model.COL_NAME:
					continue
				index = model.index(row, col, parent_index)
				if index.isValid():
					data = model.data(index, Qt.ItemDataRole.DisplayRole)
					if data is not None:
						text = str(data)
						if not self._search_case:
							text = text.lower()
							search_text = self._search_text.lower()
						else:
							search_text = self._search_text
						if search_text in text:
							results.append(index)
			child_index = model.index(row, 0, parent_index)
			if model.hasChildren(child_index):
				self._collect_matches(model, child_index, results)

	def _goto_current_match(self):
		if 0 <= self._search_current < len(self._search_results):
			idx = self._search_results[self._search_current]
			self.view.setCurrentIndex(idx)
			self.view.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)

	def search_next(self):
		if not self._search_results:
			if self._search_text:
				self.perform_search(self._search_text, self._search_case, self._search_all_cols)
			return
		self._search_current = (self._search_current + 1) % len(self._search_results)
		self._goto_current_match()

	def search_prev(self):
		if not self._search_results:
			if self._search_text:
				self.perform_search(self._search_text, self._search_case, self._search_all_cols)
			return
		self._search_current = (self._search_current - 1) % len(self._search_results)
		self._goto_current_match()

	def _clear_search(self):
		self._search_results.clear()
		self._search_current = -1	

	# ------------------------- Контекстное меню основное -------------------------------

	def show_context_menu(self, pos):
		index = self.view.indexAt(pos)
		if not index.isValid():
			return
		selected_indexes = self.view.selectionModel().selectedIndexes()
		selected_count = len(selected_indexes)

		col = index.column()

		item = index.internalPointer()
		menu = QMenu()

		work_icon = Icons.recolor_icon(Icons.add_box, QColor('#000000'))
		up_arrow_icon = Icons.recolor_icon(Icons.up_arrow, QColor('#000000'))
		down_arrow_icon = Icons.recolor_icon(Icons.down_arrow, QColor('#000000'))
		paste_icon = Icons.recolor_icon(Icons.paste, QColor('#000000'))

		if isinstance(item, Section):
			section_submenu = menu.addMenu('Добавить раздел...')
			section_icon = Icons.recolor_icon(Icons.add_ad, QColor('#000000'))
			section_submenu.setIcon(section_icon)
			add_section_up = section_submenu.addAction('Сверху')
			add_section_up.setIcon(up_arrow_icon)
			add_section_up.triggered.connect(lambda: self.add_section(item, True))
			add_section_down = section_submenu.addAction('Снизу')
			add_section_down.setIcon(down_arrow_icon)
			add_section_down.triggered.connect(lambda: self.add_section(item, False))

			add_work_action = menu.addAction('Добавить работу')
			add_work_action.setIcon(work_icon)
			add_work_action.triggered.connect(lambda: self.add_work(item))
		else:
			item: Work
			copy_submenu = menu.addMenu('Копировать...')
			copy_icon = Icons.recolor_icon(Icons.copy, QColor('#000000'))
			copy_submenu.setIcon(copy_icon)
			copy_submenu.addAction(self.copy_address_action)


			if selected_count > 1:
				copy_action = copy_submenu.addAction(f'Копировать {selected_count} ячеек')
				copy_action.triggered.connect(self.copy_selected_cells)
			else:
				copy_action = copy_submenu.addAction('Копировать текст ячейки')
				copy_action.triggered.connect(lambda: self._copy_cell_text(index))
			# Копирование ключа едениц измерения и округления
			if col == 3:
				copy_unit_action = copy_submenu.addAction('Копировать ед.изм.')
				copy_unit_action.triggered.connect(lambda: self._copy_unit_to_clipboard(item))
				paste_unit_action = menu.addAction('Вставить ед.изм.')
				paste_unit_action.triggered.connect(self._paste_unit)
			elif col in (2, 5, 7, 8, 9):
				paste_text_action = menu.addAction('Вставить текст')
				paste_text_action.setIcon(paste_icon)
				paste_text_action.setShortcut('Ctrl+V')
			# копирование объектов ссылок
			if col == 6: 
				copy_links_action = copy_submenu.addAction('Копировать набор ссылок')
				copy_links_action.triggered.connect(lambda: self._copy_links(item))
				remove_links_action = menu.addAction('Удалить набор ссылок')
				remove_links_action.triggered.connect(self._remove_links)
				if (self.project.clipboard and isinstance(self.project.clipboard[0], list) and 
					self.project.clipboard[2] is list):
					paste_links_action = menu.addAction('Вставить набор ссылок')
					paste_links_action.triggered.connect(self._paste_links)

			menu.addSeparator()

			resource_icon = Icons.recolor_icon(Icons.add_triangle, QColor('#000000'))

			if isinstance(item, Work):
				convert_to_resource_action = menu.addAction('Преобразовать в ресурс')
				convert_to_resource_action.triggered.connect(lambda: self.convert_to_resource(index, item))

				menu.addSeparator()

				work_submenu = menu.addMenu('Добавить работу...')
				work_submenu.setIcon(work_icon)

				add_work_up = work_submenu.addAction('Сверху')
				add_work_up.setIcon(up_arrow_icon)
				add_work_up.triggered.connect(lambda: self.add_work(item, True))

				add_work_down = work_submenu.addAction('Снизу')
				add_work_down.setIcon(down_arrow_icon)
				add_work_down.triggered.connect(lambda: self.add_work(item, False))

				add_resource_action = menu.addAction('Добавить ресурс')
				add_resource_action.setIcon(resource_icon)
				add_resource_action.triggered.connect(lambda: self.add_resource(item))

				menu.addSeparator()

			else:
				like_work_action = menu.addAction('Применить значения работы')
				like_work_action.triggered.connect(lambda: self.resource_like_work(index, item))

				conver_to_work_action = menu.addAction('Преобразовать в работу')
				conver_to_work_action.triggered.connect(lambda: self.convert_to_work(index, item))

				resource_submenu = menu.addMenu('Добавить ресурс...')
				resource_submenu.setIcon(resource_icon)

				add_resource_up = resource_submenu.addAction('Сверху')
				add_resource_up.setIcon(up_arrow_icon)
				add_resource_up.triggered.connect(lambda: self.add_resource(item, True))

				add_resource_up = resource_submenu.addAction('Снизу')
				add_resource_up.setIcon(down_arrow_icon)
				add_resource_up.triggered.connect(lambda: self.add_resource(item, False))

			# Действия для статусов
			status_submenu = menu.addMenu('Статус...')
			status_icon = Icons.recolor_icon(Icons.status, QColor('#000000'))
			status_submenu.setIcon(status_icon)

			action_status_correct = status_submenu.addAction('Отметить корректным')
			correct_icon = Icons.recolor_icon(Icons.done, QColor("#7b92df"))
			action_status_correct.setIcon(correct_icon)
			action_status_correct.triggered.connect(lambda: self.set_status(selected_indexes, 1))
			action_status_calculated = status_submenu.addAction('Отметить осмеченным')
			calculated_icon = Icons.recolor_icon(Icons.done_all, QColor("#0fcc38"))
			action_status_calculated.setIcon(calculated_icon)
			action_status_calculated.triggered.connect(lambda: self.set_status(selected_indexes, 2))
			action_status_nonvalid = status_submenu.addAction('Отметить недействительным')
			nonvalid_icon = Icons.recolor_icon(Icons.reset_status, QColor("#ff0000"))
			action_status_nonvalid.setIcon(nonvalid_icon)
			action_status_nonvalid.triggered.connect(lambda: self.set_status(selected_indexes, 0))
		
		menu.addSeparator()

		remove_action = menu.addAction('Удалить элемент')
		remove_icon = Icons.recolor_icon(Icons.delete, QColor('#000000'))
		remove_action.setIcon(remove_icon)
		remove_action.triggered.connect(self.remove_pos)
			
		# Очистка содержимого (доступна всегда)
		if selected_count > 0:
			menu.addSeparator()
			clear_action = menu.addAction('Очистить содержимое ячеек')
			clear_action.triggered.connect(self.clear_selected_cells)

		menu.exec(self.view.viewport().mapToGlobal(pos))

	# ------------------------------ Добавление элементов -------------------------------

	def add_section(self, item: Section | Work | Resource | None, insert: bool):
		""" Добавляет раздел выше или ниже выбранного раздела 
		:item: None — добавляет раздел в конец (в т.ч. в пустую ведомость).
		:insert: Вставка на место текущего раздела"""
		manager = self.model.manager
		address = None

		if item is None:
			address = manager.add_section()
		elif isinstance(item, Section):
			if insert:
				address = manager.add_section(item.address)
			else:
				address = manager.add_section(item.address+1)
		elif isinstance(item, (Work, Resource)):
			address = manager.add_section(item.address[0]+1)

		if not address:
			return

		self.model.layoutChanged.emit()
		self.select_item_by_address(address)

	
	def add_work(self, item: Section | Work | Resource, insert: bool|None = None):
		"""Добавляет работу в выбранный раздел. 
		insert=None — в конец раздела; 
		True/False — до/после указанной работы."""
		manager = self.model.manager
		address = None

		if isinstance(item, Section):
			address = manager.add_work(item.address)

		elif isinstance(item, Work):
			sec_idx, wrk_idx, _ = item.address
			if insert is False:
				address = manager.add_work(sec_idx, wrk_idx+1)
			elif insert is True:
				address = manager.add_work(sec_idx, wrk_idx)
			else:
				address = manager.add_work(sec_idx)

		elif isinstance(item, Resource):
			address = manager.add_work(item.address[0])

		if address is None:
			return
		
		self.model.layoutChanged.emit()
		self.select_item_by_address(address)


	def add_resource(self, item: Section | Work | Resource, insert: bool | None = None):
		""" Добавляет ресурс к работе через контекстное меню 
		insert=None — в конец списка; 
		True/False — до/после указанного ресурса."""
		manager = self.model.manager
		sec_idx, wrk_idx, rsc_idx = item.address 
		address = None

		if isinstance(item, Work):
			address = manager.add_resource(sec_idx, wrk_idx)
		elif insert is False and isinstance(item, Resource):
			address = manager.add_resource(sec_idx, wrk_idx, rsc_idx+1)
		elif insert is True and isinstance(item, Resource):
			address = manager.add_resource(sec_idx, wrk_idx, rsc_idx)

		if address is None:
			return
		
		self.model.layoutChanged.emit()
		self.select_item_by_address(address)
		

	def resource_like_work(self, index: QModelIndex, item: Resource):
		""" Применяет к ресурсу еденицу измерения и ссылку на значение родителя-работы 
		Проверки уже проведены в контекстном меню
		"""
		work: Work = index.parent().internalPointer()

		item.unit = work.raw_unit
		item.raw_quantity_formula = f'={work.format_address}' 
		self.model.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
	
	def convert_to_resource(self, index: QModelIndex, item: Work):
		manager = self.model.manager
		self.model.beginResetModel()
		res = manager.convert_work_to_resource(item.address)
		if res is False:
			QMessageBox.warning(self, 'Ошибка преобразования', 'Преобразуемая позиция не должна быть первой в разделе')
			self.model.endResetModel()
			self.view.expandAll()
			return
		self.model.endResetModel()
		self.view.expandAll()

	def convert_to_work(self, index: QModelIndex, item: Resource):
		manager = self.model.manager
		self.model.beginResetModel()
		res = manager.convert_resource_to_work(item.address)
		if res is False:
			self.model.endResetModel()
			return
		self.model.endResetModel()
		self.view.expandAll()

	# ------------------------------- Копирование текста --------------------------------
	def _copy_cell_text(self, index):
		"""Копирует чистый текст одной ячейки."""
		raw_text = index.data(Qt.ItemDataRole.DisplayRole)
		if raw_text is None:
			raw_text = ""
		# Очищаем от лишних пробелов и переносов строк
		clean_text = self._clean_text(str(raw_text))
		QApplication.clipboard().setText(clean_text)

	def copy_selected_cells(self):
		"""Копирует каждую выделенную ячейку с новой строки (без табличного форматирования)."""
		indexes = self.view.selectionModel().selectedIndexes()
		if not indexes:
			return

		lines = []
		for idx in indexes:
			raw_text = idx.data(Qt.ItemDataRole.DisplayRole) or ""
			clean_text = self._clean_text(str(raw_text))
			lines.append(clean_text)

		QApplication.clipboard().setText("\n".join(lines))

	def _clean_text(self, text: str) -> str:
		"""Очищает текст от лишних пробелов, переводов строк, табуляций и управляющих символов."""
		import re
		# Удаляем управляющие символы, кроме пробелов, табуляции, перевода строк (но их заменим)
		text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
		# Заменяем все разделители на пробелы
		text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
		# Схлопываем множественные пробелы
		text = re.sub(r' +', ' ', text)
		# Убираем пробелы в начале и конце
		return text.strip()


	def set_status(self, indexes: list[QModelIndex], mode):
		""" Назначаяет статус для позиций """
		for idx in indexes:
			item = idx.internalPointer()
			if not isinstance(item, (Work, Resource)):
				continue
			if mode == 0:
				item.status_correct = False
				item.status_calculated = False
			elif mode == 1:
				item.status_correct = True
				item.status_calculated = False
			elif mode == 2:
				item.status_correct = True
				item.status_calculated = True
			self.model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole])
		self.view.viewport().update()
		self.manager.is_modified = True


	def _copy_to_clipboard(self, text):
		"""Копирует текст в буфер обмена."""
		clipboard = QApplication.clipboard()
		clipboard.setText(text)
	
	def _get_selected_units_indexes(self):
		"""Возвращает список QModelIndex выделенных ячеек в колонке 3."""
		indexes = self.view.selectionModel().selectedIndexes()
		return [idx for idx in indexes if idx.column() == 3]
	
	def _copy_unit_to_clipboard(self, item: PositionLine):
		"""Копирует ключ и округление в буфер обмена."""
		key = item.raw_unit
		rnd = item.custom_round
		crm = item.custom_round_mode
		clipboard = QApplication.clipboard()
		clipboard.setText(f'{key}|{rnd}|{crm}')


	def _copy_current_address(self):
		idx = self.view.currentIndex()
		if not idx.isValid():
			return
		item = idx.internalPointer()
		self._copy_to_clipboard(item.format_address)
		
	# ------------------------------- Вставка текста --------------------------------
	def _paste_unit(self):
		"""Вставляет данные о ед.изм. из буфера обмена во все выделенные ячейки в колонке 3."""
		# Проверяем, что в буфере лежит корректый ключ еденицы измерения
		clipboard = QApplication.clipboard()
		text = clipboard.text()
		if not '|' in text:
			return
		key, rnd, crm = text.split('|')
		if rnd == 'None':
			rnd = None
		else:
			rnd = convert_value(rnd)
		if crm == 'None':
			crm = None
		else:
			crm = convert_value(crm)
		if isinstance(rnd, (str, float)):
			return 											# Не подходящий формат данных 
		if isinstance(crm, (str, float)):
			return 											# Не подходящий формат данных 		
		if not key in self.project.units:
			return
		indexes = self._get_selected_units_indexes()
		if not indexes:
			return
		for idx in indexes:
			item = idx.internalPointer()
			if isinstance(item, (Work, Resource)):
				item.unit = key
				item.custom_round = rnd
				item.custom_round_mode = crm
		for idx in indexes:
			self.model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole])
	
	def _paste_text(self):
		""" Вставляет в ячейку текст из буфера обмена """
		EDITABLE_COLS = {2, 5, 7, 8, 9}

		clipboard = QApplication.clipboard()
		text = clipboard.text()

		indexes = self.view.selectionModel().selectedIndexes()
		if not indexes:
			return
		
		pasted = False
		for idx in indexes:
			#item = idx.internalPointer()
			col = idx.column()

			if col not in EDITABLE_COLS:
				continue
			
			if self.model.setData(idx, text, Qt.ItemDataRole.EditRole):
				pasted = True

		if pasted:
			self.manager.is_modified = True
			# Обновление происходит автоматически через signal из модели	

	def start_editing_with_char(self, char: str):
		"""Начинает редактирование текущей ячейки и вставляет переданный символ (заменяя содержимое)."""
		index = self.view.currentIndex()
		if not index.isValid():
			return
		if not (index.flags() & Qt.ItemFlag.ItemIsEditable):
			return

		# Запускаем редактирование
		self.view.edit(index)

		# Даём время на создание редактора (100 мс достаточно)
		QTimer.singleShot(100, lambda: self._insert_char_into_editor(char))

	def _insert_char_into_editor(self, char: str):
		"""Находит активный редактор (QTextEdit или QLineEdit) и вставляет символ, заменяя всё содержимое."""
		index = self.view.currentIndex()
		if not index.isValid():
			return

		# Пробуем получить редактор через indexWidget
		editor = self.view.indexWidget(index)

		# Если не получилось, ищем дочерний виджет с фокусом, который является QTextEdit или QLineEdit
		if editor is None:
			for child in self.view.findChildren((QTextEdit, QLineEdit)):
				if child.hasFocus():
					editor = child
					break

		if editor is None:
			# Если редактор всё ещё не найден, попробуем ещё раз через 50 мс
			QTimer.singleShot(50, lambda: self._insert_char_into_editor(char))
			return

		# Заменяем текст в зависимости от типа редактора
		if isinstance(editor, QTextEdit):
			editor.setPlainText(char)
			# Перемещаем курсор в конец
			cursor = editor.textCursor()
			cursor.movePosition(QTextCursor.MoveOperation.End)
			editor.setTextCursor(cursor)
		elif isinstance(editor, QLineEdit):
			editor.setText(char)
			editor.setCursorPosition(len(char))
		# Для QComboBox и других типов ничего не делаем (они не поддерживают ввод с клавиатуры)

	# ------------------------ Взаимодействие со ссылками -------------------------------
	def _get_selected_links_indexes(self):
		"""Возвращает список QModelIndex выделенных ячеек в колонке 6."""
		indexes = self.view.selectionModel().selectedIndexes()
		return [idx for idx in indexes if idx.column() == 6]

	def _copy_links(self, item: PositionLine):
		""" Копирует в буфер проекта список объектов Link """
		self.manager.copy_obj(item.address, True)

	def _paste_links(self):
		"""Вставляет набор ссылок из буфера проекта во все выделенные ячейки в колонке 6."""
		# Проверяем, что в буфере лежит список ссылок
		if not (self.project.clipboard and 
				isinstance(self.project.clipboard[0], list) and 
				self.project.clipboard[2] is list):
			return
		indexes = self._get_selected_links_indexes()
		if not indexes:
			return
		for idx in indexes:
			item = idx.internalPointer()
			if isinstance(item, (Work, Resource)):
				self.manager.paste_object(item.address, True)
		for idx in indexes:
			self.model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole])

 
	def _remove_links(self):
		"""Удаляет наборы ссылок для всех выделенных ячеек в колонке 6."""
		indexes = self._get_selected_links_indexes()
		if not indexes:
			return
		for idx in indexes:
			item = idx.internalPointer()
			if isinstance(item, (Work, Resource)):
				item.remove_links()
				
		for idx in indexes:
			self.model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole])
	
	
	def remove_pos(self):
		"""Удаляет одну или несколько выделенных позиций (разделы, работы, ресурсы).

		Множественное выделение:
		* один дерево-элемент = один раз (selectedIndexes даёт по индексу
			на каждую ячейку строки);
		* если выделен раздел и его потомки — потомки пропускаются;
		* удаление идёт снизу вверх, чтобы индексы оставшихся не съезжали.
		"""
		selection = self.view.selectionModel()
		if selection is None:
			return

		# --- 1. Уникальные элементы ---
		selected_items = {}
		for idx in selection.selectedIndexes():
			item = idx.internalPointer()
			if isinstance(item, (Section, Work, Resource)):
				selected_items[id(item)] = item

		if not selected_items:
			return

		# --- 2. Отсев потомков уже выбранных родителей ---
		items = list(selected_items.values())
		sel_sections = {it.address for it in items if isinstance(it, Section)}          # int
		sel_works    = {tuple(it.address[:2]) for it in items if isinstance(it, Work)}  # (sec, wrk)

		roots = []
		for it in items:
			if isinstance(it, Section):
				roots.append(it)
			elif isinstance(it, Work):
				if it.address[0] in sel_sections:
					continue
				roots.append(it)
			else:  # Resource
				sec_i, wrk_i = it.address[0], it.address[1]
				if sec_i in sel_sections:
					continue
				if (sec_i, wrk_i) in sel_works:
					continue
				roots.append(it)

		if not roots:
			return

		# --- 3. Адресные ключи (ВСЕГДА 3-кортеж — иначе sorted упадёт) ---
		def addr_key(it):
			if isinstance(it, Section):
				return (it.address, -1, -1)
			if isinstance(it, Work):
				return (it.address[0], it.address[1], -1)
			return (it.address[0], it.address[1], it.address[2])   # Resource

		def remove_arg(it):
			if isinstance(it, Section):
				return (it.address, None, None)
			return tuple(it.address)   # формат, который принимает manager.remove_obj

		sorted_roots = sorted(roots, key=addr_key, reverse=True)

		# «Верхний» (минимальный) удаляемый адрес — якорь для выбора после операции
		top_sec, top_wrk, top_res = addr_key(sorted_roots[-1])
		target = (
			top_sec,
			None if top_wrk == -1 else top_wrk,
			None if top_res == -1 else top_res,
		)

		self.view.clearSelection()
		self.view.setCurrentIndex(QModelIndex())

		self.model.beginResetModel()
		try:
			for it in sorted_roots:
				self.manager.remove_obj(remove_arg(it))
		finally:
			self.model.endResetModel()

		self.view.expandAll()

		# --- 4. Подбираем ближайший допустимый адрес для выделения ---
		sec_idx, work_idx, res_idx = target
		sections = self.manager.sections
		if not sections:
			return

		if sec_idx >= len(sections):
			sec_idx = len(sections) - 1
		if sec_idx < 0:
			sec_idx = 0
		section = sections[sec_idx]

		if work_idx is not None:
			if work_idx >= len(section.works):
				work_idx = len(section.works) - 1
			if work_idx < 0:
				self.select_item_by_address((sec_idx, None, None))
				return
			work = section.works[work_idx]

			if res_idx is not None:
				if res_idx >= len(work.resources):
					res_idx = len(work.resources) - 1
				if res_idx < 0:
					self.select_item_by_address((sec_idx, work_idx, None))
					return

		self.select_item_by_address((sec_idx, work_idx, res_idx))

	# --------------------------------- Удаление ----------------------------------------
	def clear_selected_cells(self):
		"""Очищает содержимое всех выделенных ячеек в редактируемых столбцах."""
		indexes = self.view.selectionModel().selectedIndexes()
		if not indexes:
			return

		# Список столбцов, которые можно очищать (те, что имеют флаг ItemIsEditable)
		# Согласно методу flags() в модели:
		# - COL_ADDRESS (0) — нет
		# - COL_NUM (1) — нет
		# - COL_NAME (2) — да (разделы и позиции)
		# - COL_UNIT (3) — да (позиции)
		# - COL_QUANITY (4) — нет (автоматически вычисляется)
		# - COL_FORMULA (5) — да
		# - COL_LINKS (6) — нет (отдельный виджет, не редактируется в ячейке)
		# - COL_COMMENT (7) — да
		# - COL_TYPE (8) — да
		# - COL_LOCAL_COMMENT (9) — да
		EDITABLE_COLS = {2, 3, 5, 7, 8, 9}

		cleared = False
		for idx in indexes:
			col = idx.column()
			if col not in EDITABLE_COLS:
				continue
			# Очищаем данные (устанавливаем пустую строку)
			if self.model.setData(idx, "", Qt.ItemDataRole.EditRole):
				cleared = True

		if cleared:
			self.manager.is_modified = True
			# self.view.viewport().update()
			# Обновление происходит автоматически через signal из модели	

	# ----------------------------- Вспомогательное -------------------------------------
	def select_item_by_address(self, address: tuple[int, int|None, int|None] | None):
		"""Выделяет элемент в tree view по адресу (section_idx, work_idx, res_idx)."""
		self.view.clearSelection()
		if not address:
			return
		model = self.model
		sec_idx, work_idx, res_idx = address
		parent = QModelIndex()
		if sec_idx is None:
			return
		sec_index = model.index(sec_idx, 0, parent)
		if not sec_index.isValid():
			return
		if work_idx is None:
			self.view.setCurrentIndex(sec_index)
			self.view.scrollTo(sec_index)
			return
		work_index = model.index(work_idx, 0, sec_index)
		if not work_index.isValid():
			return
		if res_idx is None:
			self.view.setCurrentIndex(work_index)
			self.view.scrollTo(work_index)
			return
		res_index = model.index(res_idx, 0, work_index)
		if not res_index.isValid():
			return
		self.view.setCurrentIndex(res_index)
		self.view.scrollTo(res_index)

	# ======================== Контекстное меню для архива ==============================
	def show_archive_context_menu(self, pos):
		menu = QMenu()
		#restore_action = QAction("Восстановить из архива", self)
		#restore_action.triggered.connect(self.restore_from_archive)
		delete_action = QAction("Удалить навсегда", self)
		delete_action.triggered.connect(self.delete_from_archive)
		#menu.addAction(restore_action)
		menu.addAction(delete_action)
		menu.exec(self.archive_view.mapToGlobal(pos))

	def restore_from_archive(self):
		indexes = self.archive_view.selectedIndexes()
		if not indexes:
			return
		# Получаем уникальные объекты (по строкам)
		rows = set(idx.row() for idx in indexes)
		# Восстанавливаем в основную коллекцию (потребуется метод в менеджере)
		# Например, self.manager.restore_from_archive(row) — реализуйте в BoQ_manager
		# После восстановления обновить обе модели
		self.model.beginResetModel()
		self.archive_model.beginResetModel()
		# ... вызов manager.restore...
		self.model.endResetModel()
		self.archive_model.endResetModel()

	def refresh_views(self):
		"""Обновляет основную и архивную модели после изменения данных."""
		if self.model:
			self.model.layoutChanged.emit()
			self.view.expandAll()
		if self.archive_model:
			self.archive_model.layoutChanged.emit()
			self.archive_view.expandAll()
		
	def delete_from_archive(self):
		view = self.archive_view
		if not view:
			return

		current_index = view.currentIndex()
		if not current_index.isValid():
			return

		model = view.model()
		item = current_index.internalPointer()

		# Сбросить выделение и текущий индекс до удаления
		view.clearSelection()
		view.setCurrentIndex(QModelIndex())

		model.beginResetModel()
		try:
			if isinstance(item, Section):
				idx_section = self.manager.archive.index(item)
				self.manager.remove_obj((idx_section, None, None), None, True)
			elif isinstance(item, (Work, Resource)):
				self.manager.remove_obj(item.address, None, True)
		finally:
			model.endResetModel()
		view.expandAll()

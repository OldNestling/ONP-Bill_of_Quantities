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
	QWidget, QLabel, QPushButton, QDialog, QVBoxLayout, QToolBar, QMessageBox, QHeaderView,
	QComboBox, QDialogButtonBox, QMenu, QApplication, QTreeView, QSplitter, QTabWidget,
	QAbstractItemView, QWidgetAction, QGridLayout, QColorDialog, QToolButton, QLineEdit,
	QTextEdit, QSpinBox, QHBoxLayout
	)
from PyQt6.QtGui import QAction, QColor, QCursor, QTextCursor
from PyQt6.QtCore import Qt, QSize, QModelIndex, QEvent, QTimer
from ..ui_utilities import create_ok_cancel_buttons
from ..icons import Icons

from Core.BoQ import BoQ_manager, Section, Work, Resource, PositionLine
from Core.Project import Project
from Core.Convertor_BoQ import Convertor
from Core.Utilities import convert_value
from ..support.work_tab_support import DataEditorWidget, BoQItemDelegate, SearchBar
from ..support.work_tab_sidebar import SideBar_Right
from ..support.work_tab_models import Model, ArchiveModel
from ..support.work_tab_lib_actions import Earth_Work_Dialog, User_Libs_Dialog
from ..ui_utilities import create_ok_cancel_buttons, Requestion

class BoQ_Tab(QWidget):
	""" Представление вкладки работы с открытыми файлами ВОР """
	def __init__(self, project, main_window=None):
		super().__init__()
		self.main_window = main_window
		self.project: Project = project
		self.opened_files = {}  			# путь_файла -> индекс_вкладки
		self._recoloring = False			# флаг для предотвращения рекурсии
		self._original_icons = {}   		# словарь для хранения исходных иконок действий
		self.setup_ui()

	# ---------------------------------- Интерфейс -----------------------------------

	def setup_ui(self):
		""" Собирает интерфейс вкладки """
		layout = QVBoxLayout(self)
		layout.setSpacing(0)
		layout.setContentsMargins(0, 0, 0, 0)

		toolbar = self.setup_toolbar()
		layout.addWidget(toolbar)

		self.search_bar = SearchBar(self)
		self.search_bar.hide()
		self.search_bar.search_requested.connect(self.on_search_requested)
		self.search_bar.next_requested.connect(self.on_search_next)
		self.search_bar.prev_requested.connect(self.on_search_prev)
		layout.addWidget(self.search_bar)

		# --- Горизонтальный сплиттер: левая область (редактор + вкладки) | правая панель ---
		h_splitter = QSplitter(Qt.Orientation.Horizontal)
		h_splitter.setChildrenCollapsible(True)

		# --- Левая часть: вертикальный сплиттер для редактора данных и вкладок ---
		v_splitter = QSplitter(Qt.Orientation.Vertical)
		v_splitter.setChildrenCollapsible(True)

		self.data_editor = DataEditorWidget(project=self.project, parent=self)
		self.data_editor.setContentsMargins(2,1,1,2)
		v_splitter.addWidget(self.data_editor)

		self.boq_views_container = QTabWidget()
		self.boq_views_container.setTabsClosable(True)
		self.boq_views_container.tabCloseRequested.connect(self.close_boq_tab)
		self.boq_views_container.currentChanged.connect(self.on_tab_changed)
		# Применяем стиль к кнопкам закрытия этой вкладки
		close_icon_path = Icons.resource_path('UI/icons/icon_close.svg').replace('\\', '/')
		self.boq_views_container.tabBar().setStyleSheet(f"""
			QTabBar::close-button {{
				image: url({close_icon_path});
				margin-right: 3px;
			}}
		""")

		v_splitter.addWidget(self.boq_views_container)

		# Настройка вертикального сплиттера
		v_splitter.setSizes([70, 600])			# начальные высоты
		v_splitter.setStretchFactor(0, 0)		# редактор не растягивается
		v_splitter.setStretchFactor(1, 1)		# вкладки забирают всё свободное место

		h_splitter.addWidget(v_splitter)

		# --- Правая боковая панель ---
		self.right_sidebar = SideBar_Right(self.project)
		self.right_sidebar.set_navigation_target(self)   # передаём ссылку на себя
		h_splitter.addWidget(self.right_sidebar)

		# Настройка горизонтального сплиттера
		h_splitter.setSizes([800, 200])	   # левая часть шире, правая — уже
		h_splitter.setStretchFactor(0, 1)	 # левая растягивается при ресайзе окна
		h_splitter.setStretchFactor(1, 0)	 # правая сохраняет предпочтительный размер

		layout.addWidget(h_splitter)

	def setup_toolbar(self):
		toolbar = QToolBar("Основная панель")
		toolbar.setIconSize(QSize(24,24))

		# --- Группа "Сохранение и загрузка" ---
		save_action = QAction(Icons.save, 'Сохранить', self)
		save_action.setShortcut('Ctrl+S')
		save_action.setToolTip(f"Сохранить ({save_action.shortcut().toString()})")
		save_action.triggered.connect(self.save_current_tab)
		toolbar.addAction(save_action)

		save_as_action = QAction(Icons.save_as, 'Сохранить как', self)
		save_as_action.setShortcut('Ctrl+Shift+S')
		save_as_action.setToolTip(f"Сохранить как ({save_as_action.shortcut().toString()})")
		save_as_action.triggered.connect(self._save_as)
		toolbar.addAction(save_as_action)

		toolbar.addSeparator()		  # ---

		reopen_action = QAction(Icons.reopen, 'Перезагрузить', self)
		reopen_action.setShortcut('Ctrl+Alt+O')
		reopen_action.setToolTip(f"Перезагрузить ({reopen_action.shortcut().toString()})")
		reopen_action.triggered.connect(self.reopen_file)
		toolbar.addAction(reopen_action)
		close_action = QAction(Icons.close_tab, 'Закрыть вкладку', self)
		close_action.setShortcut('Ctrl+W')
		close_action.setToolTip(f"Закрыть вкладку ({close_action.shortcut().toString()})")
		close_action.triggered.connect(self.close_tab)
		toolbar.addAction(close_action)

		toolbar.addSeparator()		  # ---

		# --- Группа "Буфер обмена" ---
		copy_action = QAction(Icons.copy, 'Копировать позицию', self)
		copy_action.setShortcut('Ctrl+Shift+C')		# Работает с буфером проекта, а не ОС
		copy_action.setToolTip(f"Копировать позицию ({copy_action.shortcut().toString()})")
		copy_action.triggered.connect(self.copy_selected)
		toolbar.addAction(copy_action)
		cut_action = QAction(Icons.cut, 'Вырезать позицию', self)
		cut_action.setShortcut('Ctrl+Shift+X')		# Работает с буфером проекта, а не ОС
		cut_action.setToolTip(f"Вырезать позицию ({cut_action.shortcut().toString()})")
		cut_action.triggered.connect(self.cut_selected)
		toolbar.addAction(cut_action)
		paste_action = QAction(Icons.paste, 'Вставить позицию', self)
		paste_action.setShortcut('Ctrl+Shift+V')		# Работает с буфером проекта, а не ОС
		paste_action.setToolTip(f"Вставить позицию ({paste_action.shortcut().toString()})")
		paste_action.triggered.connect(self.paste_selected)
		toolbar.addAction(paste_action)

		toolbar.addSeparator()		# ---

		# --- Группа "Редактирование" ---
		undo_action = QAction(Icons.undo, 'Отменить', self)
		undo_action.setShortcut('Ctrl+Z')
		undo_action.setToolTip(f"Отменить ({undo_action.shortcut().toString()})")
		undo_action.setEnabled(False)
		toolbar.addAction(undo_action)
		redo_action = QAction(Icons.redo, 'Вернуть', self)
		redo_action.setShortcut('Ctrl+Y')
		redo_action.setToolTip(f"Вернуть ({redo_action.shortcut().toString()})")
		redo_action.setEnabled(False)
		toolbar.addAction(redo_action)

		toolbar.addSeparator()		  # ---

		add_section_action = QAction(Icons.add_ad, 'Добавить раздел', self)
		add_section_action.setShortcut('Ctrl+1')
		add_section_action.setToolTip(f"Добавить раздел ({add_section_action.shortcut().toString()})")
		add_section_action.triggered.connect(self.add_section)
		toolbar.addAction(add_section_action)
		add_work_action = QAction(Icons.add_box, 'Добавить работу', self)
		add_work_action.setShortcut('Ctrl+2')
		add_work_action.setToolTip(f"Добавить работу ({add_work_action.shortcut().toString()})")
		add_work_action.triggered.connect(self.add_work)
		toolbar.addAction(add_work_action)
		add_resource_action = QAction(Icons.add_triangle, 'Добавить ресурс', self)
		add_resource_action.setShortcut('Ctrl+3')
		add_resource_action.setToolTip(f"Добавить ресурс ({add_resource_action.shortcut().toString()})")
		add_resource_action.triggered.connect(self.add_resource)
		toolbar.addAction(add_resource_action)
		remove_action = QAction(Icons.delete, 'Удалить', self)
		remove_action.setShortcut('Alt+Del')
		remove_action.setToolTip(f"Удалить ({remove_action.shortcut().toString()})")
		remove_action.triggered.connect(self.remove_selected)
		toolbar.addAction(remove_action)

		toolbar.addSeparator()		  # ---
		earth_work_action = QAction(Icons.excavator, 'Добавить земляную работу', self)
		earth_work_action.triggered.connect(self.create_earth_work)
		toolbar.addAction(earth_work_action)

		add_from_user_lib = QAction(Icons.template, 'Добавить из пользовательской библиотеки', self)
		add_from_user_lib.triggered.connect(self.create_from_user_lib)
		toolbar.addAction(add_from_user_lib)

		toolbar.addSeparator()		  # ---

		# --- Группа "Перемещение" ---
		move_up_action = QAction(Icons.move_up, 'Переместить вверх', self)
		move_up_action.setShortcut('Alt+Up')
		move_up_action.setToolTip(f"Переместить вверх ({move_up_action.shortcut().toString()})")
		move_up_action.triggered.connect(lambda: self.move_selected(-1))
		toolbar.addAction(move_up_action)
		move_down_action = QAction(Icons.move_down, 'Переместить вниз', self)
		move_down_action.setShortcut('Alt+Down')
		move_down_action.setToolTip(f"Переместить вниз ({move_down_action.shortcut().toString()})")
		move_down_action.triggered.connect(lambda: self.move_selected(1))
		toolbar.addAction(move_down_action)

		toolbar.addSeparator()		  # ---

		icon = Icons.move_item
		rotated_icon = Icons.rotate_icon(icon, 90)
		drop_to_archive_action = QAction(rotated_icon, 'Сбросить в архив', self)
		drop_to_archive_action.triggered.connect(self.drop_to_archive)
		toolbar.addAction(drop_to_archive_action)

		toolbar.addSeparator()		  # ---

		# --- Группа "Стили" ---
		fill_color_action = QAction(Icons.fill_color, 'Задать фон текста', self)
		fill_color_action.triggered.connect(self.show_background_color_menu)
		toolbar.addAction(fill_color_action)
		set_text_color_action = QAction(Icons.color_text, 'Задать цвет текста', self)
		set_text_color_action.triggered.connect(self.show_text_color_menu)
		toolbar.addAction(set_text_color_action)
		clear_format_action = QAction(Icons.eraser_off, 'Очистка форматирования', self)
		clear_format_action.triggered.connect(self.clear_formatting)
		toolbar.addAction(clear_format_action)
		
		toolbar.addSeparator()		  # ---

		# --- Группа "Вид" ---
		expande_all_action = QAction(Icons.expande, 'Развернуть всё', self)
		expande_all_action.setShortcut('Ctrl+Alt+H')
		expande_all_action.setToolTip(f"Развернуть всё ({expande_all_action.shortcut().toString()})")
		expande_all_action.triggered.connect(lambda: self.switch_collapse_expand(True)
)
		toolbar.addAction(expande_all_action)
		compress_action = QAction(Icons.compress, 'Свернуть всё', self)
		compress_action.setShortcut('Ctrl+H')
		compress_action.setToolTip(f"Свернуть всё ({compress_action.shortcut().toString()})")
		compress_action.triggered.connect(lambda: self.switch_collapse_expand(False))
		toolbar.addAction(compress_action)
		toolbar.addSeparator()		  # ---
		status_correct_action = QAction(Icons.done, 'Корректно', self)
		status_correct_action.setShortcut('Ctrl+=')
		status_correct_action.setToolTip(f"Корректно ({status_correct_action.shortcut().toString()})")
		status_correct_action.triggered.connect(lambda: self.change_status(1))
		toolbar.addAction(status_correct_action)
		status_calculated_action = QAction(Icons.done_all,'Осмечено', self)
		status_calculated_action.setShortcut('Ctrl+Shift+=')
		status_calculated_action.setToolTip(f"Осмечено ({status_calculated_action.shortcut().toString()})")
		status_calculated_action.triggered.connect(lambda: self.change_status(2))
		toolbar.addAction(status_calculated_action)
		reset_status_action = QAction(Icons.reset_status, 'Сбросить статусы', self)
		reset_status_action.setShortcut('Ctrl+-')
		reset_status_action.setToolTip(f"Сбросить статусы ({reset_status_action.shortcut().toString()})")
		reset_status_action.triggered.connect(lambda: self.change_status(0))
		toolbar.addAction(reset_status_action)

		toolbar.addSeparator()		  # ---

		reload_action = QAction(Icons.refresh, 'Освежить', self)
		reload_action.setShortcut('Ctrl+Alt+F9')
		reload_action.setToolTip(f"Освежить ({reload_action.shortcut().toString()})")
		reload_action.triggered.connect(self.reload_data)
		toolbar.addAction(reload_action)

		toolbar.addSeparator()		  # ---
		
		# --- Группа "прочее" ---
		export_action = QAction(Icons.upload, 'Экспортировать', self)
		export_action.triggered.connect(self.open_export_dialog)
		toolbar.addAction(export_action)

		search_action = QAction(Icons.find, 'Поиск', self)  # или использовать стандартную иконку
		search_action.setShortcut('Ctrl+F')
		search_action.setToolTip(f"Поиск ({search_action.shortcut().toString()})")
		search_action.triggered.connect(self.toggle_search_bar)
		toolbar.addAction(search_action)

		self.fix_toolbar_icons(toolbar)
		return toolbar	

	def fix_toolbar_icons(self, toolbar):
		extension_button = toolbar.findChild(QToolButton, "qt_toolbar_ext_button")
		if extension_button:
			menu = extension_button.menu()
			if menu:
				# Отключаем предыдущие соединения, чтобы не накапливать
				try:
					menu.aboutToShow.disconnect()
					menu.aboutToHide.disconnect()
				except TypeError:
					pass
				menu.aboutToShow.connect(self._on_extension_menu_about_to_show)
				menu.aboutToHide.connect(self._on_extension_menu_about_to_hide)

	def _on_extension_menu_about_to_show(self):
		menu = self.sender()
		if menu and not self._recoloring:
			self._recolor_menu_icons(menu, to_black=True)

	def _on_extension_menu_about_to_hide(self):
		menu = self.sender()
		if menu and not self._recoloring:
			self._recolor_menu_icons(menu, to_black=False)

	def _recolor_menu_icons(self, menu: QMenu, to_black: bool):
		"""Перекрашивает иконки действий в меню в чёрный (to_black=True) или восстанавливает исходные (False)."""
		if self._recoloring:
			return
		self._recoloring = True
		try:
			for action in menu.actions():
				icon = action.icon()
				if icon.isNull():
					continue
				if to_black:
					# Сохраняем исходную иконку, если ещё не сохранили
					if action not in self._original_icons:
						self._original_icons[action] = icon
					# Перекрашиваем в чёрный
					new_icon = Icons.recolor_icon(icon, QColor(0, 0, 0))
					action.setIcon(new_icon)
				else:
					# Восстанавливаем исходную иконку, если она была сохранена
					if action in self._original_icons:
						action.setIcon(self._original_icons[action])
		finally:
			self._recoloring = False

	# ========================= Базовая методы вкладки =========================

	def set_project(self, project):
		self.project = project
		if hasattr(self, 'data_editor'):
			self.data_editor.set_project(project)
		if hasattr(self, 'right_sidebar'):
			self.right_sidebar.set_project(project)

	def add_BoQ_subtab(self, file_manager: BoQ_manager):
		file_path = str(file_manager.file.resolve())  # абсолютный путь для надёжности
		if file_path in self.opened_files:
			index = self.opened_files[file_path]
			self.boq_views_container.setCurrentIndex(index)
			return
		tab_name = file_manager.file.stem
		file_manager.check_changes()
		view = BoQ_View(self, self.project, file_manager)
		# Подключаем сигнал выбора ячейки
		view.view.selectionModel().currentChanged.connect(self.on_boq_selection_changed)
		
		index = self.boq_views_container.addTab(view, tab_name)
		self.boq_views_container.setCurrentIndex(index)
		self.opened_files[file_path] = index
		self.on_tab_changed(index)

		# ---- мигание вкладки "Ведомости" ----
		if self.main_window:
			tab_widget = self.main_window.tab_widget
			# Ищем индекс внешней вкладки "Ведомости"
			for i in range(tab_widget.count()):
				if tab_widget.tabText(i) == "Ведомости":
					tab_widget.setCurrentIndex(i)          # переключиться
					break

	def close_boq_tab(self, index):
		widget = self.boq_views_container.widget(index)
		if isinstance(widget, BoQ_View):
			# Проверяем, была ли эта вкладка активной
			was_current = (self.boq_views_container.currentIndex() == index)
			if widget.manager.is_modified:
				reply = Requestion.ask(
					self,
					'Несохранённые изменения',
					f'Раздел "{widget.manager.file.stem}" был изменён. Сохранить перед закрытием?',
				)
				if reply == QMessageBox.StandardButton.Cancel:
					return
				elif reply == QMessageBox.StandardButton.Yes:
					if widget.manager.read_mode:
						if not self._save_as_dialog(widget.manager, self):
							return
					else:
						widget.manager.save_file()

			# Снимаем блокировку (если не режим чтения)
			if not widget.manager.read_mode:
				widget.manager.unlock()

			# Удаляем из словаря
			file_path = str(widget.manager.file.resolve())
			if file_path in self.opened_files:
				del self.opened_files[file_path]

			# Отключаем сигналы выбора, чтобы избежать лишних вызовов после удаления
			if hasattr(widget, 'view') and widget.view.selectionModel():
				widget.view.selectionModel().blockSignals(True)

			# Очистка и завершение работы виджета
			widget._clear_search()
			widget.shutdown()

			# Удаляем вкладку и виджет (только один раз!)
			self.boq_views_container.removeTab(index)
			widget.deleteLater()

			# Если закрываемая вкладка была активной – сбрасываем редактор и правую панель
			if was_current:
				if hasattr(self.data_editor, 'clear'):
					self.data_editor.clear()
				if hasattr(self.right_sidebar, 'clear'):
					self.right_sidebar.clear()

			# Обновляем индексы в словаре opened_files
			for path, idx in list(self.opened_files.items()):
				if idx > index:
					self.opened_files[path] = idx - 1


	def has_unsaved_changes(self) -> bool:
			"""Возвращает True, если хотя бы один открытый раздел изменён."""
			for i in range(self.boq_views_container.count()):
				widget = self.boq_views_container.widget(i)
				if isinstance(widget, BoQ_View) and widget.manager.is_modified:
					if widget.manager.is_modified:
						return True
			return False	

	def close_all_tabs(self, ask_for_save=True, parent_dialog=None) -> bool:
		"""
		Закрывает все открытые вкладки.
		Если ask_for_save=True, для каждого изменённого файла будет запрошено сохранение.
		parent_dialog используется как родитель для диалоговых окон.
		Возвращает True, если все вкладки успешно закрыты, иначе False (если пользователь отменил).
		"""
		if parent_dialog is None:
			parent_dialog = self

		if ask_for_save:
			for i in range(self.boq_views_container.count()):
				widget = self.boq_views_container.widget(i)
				if isinstance(widget, BoQ_View) and widget.manager.is_modified:
					reply = Requestion.ask(
						parent_dialog,
						'Несохранённые изменения',
						f'Раздел "{widget.manager.file.stem}" был изменён. Сохранить перед закрытием?',
					)
					if reply == QMessageBox.StandardButton.Cancel:
						return False  # отмена закрытия
					elif reply == QMessageBox.StandardButton.Yes:
						if widget.manager.read_mode:
							# Для read_mode вызываем диалог "Сохранить как"
							if not self._save_as_dialog(widget.manager, parent_dialog):
								return False
						else:
							widget.manager.save_file()
			# После диалогов сохранения закрываем все вкладки без дополнительных запросов
			self._close_all_tabs_without_dialogs()
		else:
			self._close_all_tabs_without_dialogs()
		return True

	def _close_all_tabs_without_dialogs(self):
		"""Закрывает все вкладки без запросов, снимая блокировки."""
		for i in reversed(range(self.boq_views_container.count())):
			widget = self.boq_views_container.widget(i)
			if isinstance(widget, BoQ_View):
				if not widget.manager.read_mode:
					widget.manager.unlock()
				file_path = str(widget.manager.file.resolve())
				if file_path in self.opened_files:
					del self.opened_files[file_path]
			self.boq_views_container.removeTab(i)
		self.opened_files.clear()

	def _save_as_dialog(self, manager: BoQ_manager, parent) -> bool:
		"""Диалог сохранения для read_mode файла."""
		from PyQt6.QtWidgets import QInputDialog
		new_name, ok = QInputDialog.getText(
			parent,
			"Сохранить как",
			"Введите имя нового файла (без расширения):",
			text=manager.file.stem + "_копия"
		)
		if ok and new_name:
			if not new_name.strip():
				QMessageBox.warning(parent, "Ошибка", "Имя файла не может быть пустым.")
				return False
			new_path = manager.file.parent / f"{new_name}.json"
			if new_path.exists():
				reply = Requestion.ask(
					parent,
					'Файл существует',
					f'Файл {new_name}.json уже существует. Перезаписать?',
				)
				if reply != QMessageBox.StandardButton.Yes:
					return False
			manager.save_file(save_as=new_name)
			return True
		return False

	def force_close_all(self):
		"""Принудительное закрытие всех вкладок без запросов (используется при отказе от сохранения)."""
		self._close_all_tabs_without_dialogs()
		self.right_sidebar.clear()

	def on_boq_selection_changed(self, current, previous):
		if not current.isValid():
			return
		model = current.model()
		if model is None or model.manager is None:   # модель уже в процессе удаления
			return
		self.data_editor.setModel(model)
		self.data_editor.setCurrentIndex(current)
		# Передаём tree_view активной вкладки
		view = self.current_boq_view().view if self.current_boq_view() else None
		# Обновляем правую панель
		self.right_sidebar.set_active_model(model, current, view)

	def on_tab_changed(self, index):
		if self.search_bar.isVisible():
			self.search_bar.hide()
		widget = self.boq_views_container.widget(index)
		if isinstance(widget, BoQ_View):
			current = widget.view.currentIndex()
			if current.isValid():
				model = current.model()
				self.right_sidebar.set_active_model(model, current, widget.view)
			else:
				# Нет выделения – очищаем правую панель и редактор
				self.right_sidebar.clear()
				self.data_editor.clear()
			widget._clear_search()

	# =========================== Работа с данными ===========================
	def current_boq_view(self):
		"""Возвращает активную вкладку с BoQ_View или None."""
		widget = self.boq_views_container.currentWidget()
		if isinstance(widget, BoQ_View):
			return widget
		return None

	def current_selection(self):
		"""Возвращает кортеж (model, indexes) для текущего выделения.
		indexes – список QModelIndex выделенных элементов."""
		view = self.current_boq_view()
		if not view:
			return None, []
		selection_model = view.view.selectionModel()
		if not selection_model:
			return view.model, []
		indexes = selection_model.selectedRows()  # или selectedIndexes(), зависит от задачи
		return view.model, indexes	
	
	def get_insert_address_from_current(self):
		"""Возвращает кортеж (section_idx, work_idx, resource_idx) для вставки
		относительно текущего выделения или текущей ячейки."""
		view = self.current_boq_view()
		if not view:
			return None, None, None

		current_index = view.view.currentIndex()
		if not current_index.isValid():
			return None, None, None

		item = current_index.internalPointer()
		if isinstance(item, Section):
			return item.address, None, None
		elif isinstance(item, Work):
			return item.address[0], item.address[1], None
		elif isinstance(item, Resource):
			return item.address[0], item.address[1], item.address[2]
		return None, None, None
	
	def select_item_by_address(self, view, address):
		"""Выделяет элемент в tree view по адресу (section_idx, work_idx, res_idx)."""
		model = view.model
		sec_idx, work_idx, res_idx = address
		parent = QModelIndex()
		if sec_idx is not None:
			sec_index = model.index(sec_idx, 0, parent)
			if work_idx is None:
				view.view.setCurrentIndex(sec_index)
				return
			work_index = model.index(work_idx, 0, sec_index)
			if res_idx is None:
				view.view.setCurrentIndex(work_index)
				return
			res_index = model.index(res_idx, 0, work_index)
			view.view.setCurrentIndex(res_index)
	
	def toggle_search_bar(self):
		if self.search_bar.isVisible():
			self.search_bar.hide()
		else:
			self.search_bar.show()
			self.search_bar.line_edit.setFocus()

	def on_search_requested(self, text, case_sensitive, all_columns):
		view = self.current_boq_view()
		if view:
			view.perform_search(text, case_sensitive, all_columns)

	def on_search_next(self):
		view = self.current_boq_view()
		if view:
			view.search_next()

	def on_search_prev(self):
		view = self.current_boq_view()
		if view:
			view.search_prev()

	def navigate_to_address(self, address):
		"""Принимает кортеж (section_idx, work_idx, resource_idx) и переходит к позиции."""
		view = self.current_boq_view()
		if not view:
			return
		section_idx, work_idx, resource_idx = address
		model = view.model
		if not model:
			return

		# Строим индекс
		parent = QModelIndex()
		if section_idx is not None:
			section_index = model.index(section_idx, 0, parent)
			if work_idx is None:
				view.view.setCurrentIndex(section_index)
				view.view.scrollTo(section_index)
				return
			work_index = model.index(work_idx, 0, section_index)
			if resource_idx is None:
				view.view.setCurrentIndex(work_index)
				view.view.scrollTo(work_index)
				return
			resource_index = model.index(resource_idx, 0, work_index)
			view.view.setCurrentIndex(resource_index)
			view.view.scrollTo(resource_index)

	# -------------------------------- Слоты ----------------------------------
	# ----------- Вспомогательное ----------

	def _show_color_menu(self, is_background=True):
		"""Показывает меню с палитрой цветов и кнопкой сброса."""
		menu = QMenu(self)
		menu.setTitle("Цвет фона" if is_background else "Цвет текста")

		# Виджет с палитрой
		color_widget = QWidget()
		grid = QGridLayout(color_widget)
		grid.setSpacing(2)

		# Предустановленные цвета
		colors = (
			"#D61A1A",
			"#ff6666",
			"#B565B2",
			"#BDAAAA",
			"#99B887",
			"#66A07A",
			"#7EA50A",
			"#33ffff",
			"#9999ff",
			"#3333ff"
		)

		row, col = 0, 0
		max_cols = 5
		for hex_color in colors:
			btn = QPushButton()
			btn.setFixedSize(20, 20)
			btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #aaa;")
			btn.clicked.connect(lambda checked, c=hex_color: self._apply_color(c, is_background))
			grid.addWidget(btn, row, col)
			col += 1
			if col >= max_cols:
				col = 0
				row += 1

		# Кнопка "Другой..."
		custom_btn = QPushButton("Другой...")
		custom_btn.clicked.connect(lambda: self._pick_custom_color(is_background))
		grid.addWidget(custom_btn, row + 1, 0, 1, max_cols)

		# Кнопка "Сбросить"
		reset_btn = QPushButton("Сбросить")
		reset_btn.clicked.connect(lambda: self._reset_color(is_background))
		grid.addWidget(reset_btn, row + 2, 0, 1, max_cols)

		# Добавляем виджет в меню
		action = QWidgetAction(menu)
		action.setDefaultWidget(color_widget)
		menu.addAction(action)

		# Показываем меню в позиции курсора
		menu.exec(QCursor.pos())

	def _pick_custom_color(self, is_background):
		"""Открывает QColorDialog для выбора произвольного цвета."""
		color = QColorDialog.getColor(options=QColorDialog.ColorDialogOption.DontUseNativeDialog)
		if color.isValid():
			self._apply_color(color.name(), is_background)

	def _apply_color(self, hex_color, is_background):
		"""Применяет цвет ко всем выделенным ячейкам в допустимых столбцах."""
		view = self.current_boq_view()
		if not view:
			return
		model = view.model
		selection = view.view.selectionModel()
		if not selection:
			return

		allowed_cols = {2, 5, 6, 7, 9}
		for index in selection.selectedIndexes():
			col = index.column()
			if col not in allowed_cols:
				continue
			item = index.internalPointer()
			if not hasattr(item, 'style_manager'):
				continue

			if is_background:
				item.style_manager.set_background_color(col, hex_color)
			else:
				item.style_manager.set_text_color(col, hex_color)

			model.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])

		view.manager.is_modified = True
		view.view.viewport().update()

	def _reset_color(self, is_background):
		"""Сбрасывает цвет для выделенных ячеек."""
		view = self.current_boq_view()
		if not view:
			return
		model = view.model
		selection = view.view.selectionModel()
		if not selection:
			return

		allowed_cols = {2, 5, 6, 7, 9}
		for index in selection.selectedIndexes():
			col = index.column()
			if col not in allowed_cols:
				continue
			item = index.internalPointer()
			if not hasattr(item, 'style_manager'):
				continue

			if is_background:
				item.style_manager.set_background_color(col, None)
			else:
				item.style_manager.set_text_color(col, None)

			model.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])

		view.manager.is_modified = True
		view.view.viewport().update()

	# ------------- Сохранение -------------
	def save_current_tab(self):
		view = self.current_boq_view()
		if not view:
			return
		if view.manager.read_mode:
			self._save_as_dialog(view.manager, self)
		else:
			view.manager.save_file()
	
	def _save_as(self):
		view = self.current_boq_view()
		if not view:
			return
		self._save_as_dialog(view.manager, self)

	def reopen_file(self):
		view = self.current_boq_view()
		if not view:
			return
		manager = view.manager
		model = view.model
		archive_model = view.archive_model

		reply = QDialog(self)
		reply.setMinimumWidth(400)
		reply.setWindowTitle('Перезагрузка файла')
		reply.setModal(True)

		layout = QVBoxLayout(reply)
		request = 'Вы уверены что хотите сбросить и перезагрузить данные ведомости'
		text = QLabel(f'<p align="center">{request}<br><b>{manager.object_name}</b>?</p>')
		text.setWordWrap(True)
		layout.addWidget(text)

		btns = create_ok_cancel_buttons(reply, False, 'Подтвердить')
		layout.addWidget(btns)

		if reply.exec() == QDialog.DialogCode.Accepted:
			view.view.clearSelection()
			view.view.setCurrentIndex(QModelIndex())
			view.archive_view.clearSelection()
			view.archive_view.setCurrentIndex(QModelIndex())

			model.beginResetModel()
			archive_model.beginResetModel()
			manager.reload_file()
			model.endResetModel()
			archive_model.endResetModel()
			view.view.expandAll()
	
	def close_tab(self):
		index = self.boq_views_container.currentIndex()
		self.close_boq_tab(index)

	# ------------- Копирование ------------
	def copy_selected(self):
		view = self.current_boq_view()
		if not view:
			return
		model = view.model
		manager: BoQ_manager = model.manager

		index = view.view.currentIndex()

		if not index.isValid():
			return
		
		item = index.internalPointer()
		if isinstance(item, Section):
			manager.copy_obj((item.address, None, None))
		elif isinstance(item, (Work, Resource)):
			manager.copy_obj(item.address)


	def cut_selected(self):
		view = self.current_boq_view()
		if not view:
			return
		model = view.model
		manager: BoQ_manager = model.manager

		index = view.view.currentIndex()

		if not index.isValid():
			return
		
		item = index.internalPointer()
		is_cut = False
		if isinstance(item, Section):
			is_cut = manager.cut_obj((item.address, None, None))
		elif isinstance(item, (Work, Resource)):
			is_cut = manager.cut_obj(item.address)

		if is_cut:
			model.layoutChanged.emit()
			view.view.expandAll()

	def paste_selected(self):
		view = self.current_boq_view()
		if not view:
			return
		manager = view.manager
		model = view.model

		current_index = view.view.currentIndex()
		if not current_index.isValid():
			# Вставка в корень (добавить раздел)
			manager.paste_object((None, None, None))
			return
		item = current_index.internalPointer()

		if isinstance(item, Section):
			is_paste = manager.paste_object((item.address, None, None)) 
		elif isinstance(item, (Work, Resource)):
			is_paste = manager.paste_object(item.address) 

		if is_paste:
			model.layoutChanged.emit()
			view.view.expandAll()	
		

	# ------------- Добавление -------------
	def add_section(self):
		view = self.current_boq_view()
		if not view:
			return
		manager = view.manager
		model = view.model

		row = len(manager.sections)
		model.beginInsertRows(QModelIndex(), row, row)
		manager.add_section()
		model.endInsertRows()
		#view.view.expandAll()

	def add_work(self):
		view = self.current_boq_view()
		if not view:
			return
		manager = view.manager
		model = view.model

		current_index = view.view.currentIndex()
		if not current_index.isValid():
			return # Некуда вставлять
		
		item = current_index.internalPointer()

		if isinstance(item, Section):
			section_index = item.address
		else:
			section_index, _, _ = item.address
		
		if section_index is not None:
			manager.add_work(section_index)
			model.layoutChanged.emit()
			view.view.expandAll()

	def add_resource(self):
		view = self.current_boq_view()
		if not view:
			return
		manager = view.manager
		model = view.model

		current_index = view.view.currentIndex()
		if not current_index.isValid():
			return
		if not current_index.parent():
			return
		item = current_index.internalPointer()

		if isinstance(item, (Work, Resource)):
			section_index, work_index, _  = item.address
		#if section_index is not None and work_index is not None:
			manager.add_resource(section_index, work_index)
			model.layoutChanged.emit()
			view.view.expandAll()

	# ------------- Удаление -------------	
	def remove_selected(self):

		view = self.current_boq_view()
		if not view:
			return

		current_index = view.view.currentIndex()
		if not current_index.isValid():
			return

		manager = view.manager
		model = view.model
		item = current_index.internalPointer()

		# Сбросить выделение и текущий индекс до удаления
		view.view.clearSelection()
		view.view.setCurrentIndex(QModelIndex())

		model.beginResetModel()
		try:
			if isinstance(item, Section):
				manager.remove_obj((item.address, None, None))
			elif isinstance(item, (Work, Resource)):
				manager.remove_obj(item.address)
		finally:
			model.endResetModel()
		view.view.expandAll()

	
	def drop_to_archive(self):
		"""Переносит выбранную позицию (раздел, работу или ресурс) в архив."""
		view = self.current_boq_view()
		if not view:
			return
		current_index = view.view.currentIndex()
		if not current_index.isValid():
			QMessageBox.information(self, "Нет выделения", "Выберите позицию для переноса в архив.")
			return
		# Проверяем, что выделена ровно одна позиция (не несколько ячеек)
		selection = view.view.selectionModel()
		if selection and len(selection.selectedIndexes()) > 1:
			reply = Requestion.ask(
				self,
				'Несколько позиций',
				'Выделено несколько ячеек. Перенести в архив можно только одну позицию.\n'
				'Продолжить с текущей активной позицией?',
				with_cancel= False
			)
			if reply != QMessageBox.StandardButton.Yes:
				return
		item = current_index.internalPointer()
		if item is None:
			return
		 # Получаем адрес
		if isinstance(item, Section):
			address = (item.address, None, None)
		elif isinstance(item, (Work, Resource)):
			address = item.address
		else:
			return	
		manager = view.manager
		model = view.model
		archive_model = view.archive_model	

		# Сброс выделения перед операцией
		view.view.clearSelection()
		view.view.setCurrentIndex(QModelIndex())

		# Выполняем перенос
		model.beginResetModel()
		archive_model.beginResetModel()
		success = manager.drop_to_archive(address)
		if not success:
			model.endResetModel()
			archive_model.endResetModel()
			QMessageBox.warning(self, "Ошибка", "Не удалось перенести позицию в архив.")
			return
		model.endResetModel()
		archive_model.endResetModel()

		# Обновляем отображение
		view.view.expandAll()
		view.archive_view.expandAll()

	# ------------- Генерация позиций -------------	

	def create_earth_work(self):
		""" Вызывает диалоговое окно для создания земляных работ """
		if not self.project.soils_manager.library:
			QMessageBox.warning(
				self,
				'Отсутствуют данные',
				'В бибиотеке проекта отсутсвуют данные о грунтах'
			)
			return

		view = self.current_boq_view()
		if not view:
			return

		current_index = view.view.currentIndex()
		if not current_index.isValid():
			return

		manager = view.manager
		model = view.model
		item = current_index.internalPointer()

		if isinstance(item, Section):
			section_index = item.address
			indexes = (section_index, None, None)
		else:
			indexes = item.address

		dialog = Earth_Work_Dialog(self, manager)

		if dialog.exec() == dialog.DialogCode.Accepted:
			data: dict = dialog.get_data()
			mode = data.pop('mode')

			model.beginResetModel()

			if mode == 'excavation':
				manager.add_excavation(data, indexes)
			elif mode == 'drilling_piles':
				manager.add_drilling_piles(data, indexes)

			model.endResetModel()
			view.view.expandAll()
	def create_from_user_lib(self):
		"""
		Вызывает диалоговое окно для создания позиций на основании пользовательских библиотек
		"""
		if not self.project.libraries_manager.libraries:
			QMessageBox.warning(
				self,
				'Отсутствуют данные',
				'В бибиотеке проекта отсутсвуют пользовательские данные'
			)
			return
		view = self.current_boq_view()
		if not view:
			return
		current_index = view.view.currentIndex()
		if not current_index.isValid():
			return
		manager = view.manager
		model = view.model
		item = current_index.internalPointer()
		if isinstance(item, Section):
			section_index = item.address
			indexes = (section_index, None, None)
		else:
			indexes = item.address

		dialog = User_Libs_Dialog(self, manager)
		if dialog.exec() == dialog.DialogCode.Accepted:
			data: dict = dialog.get_data()
			model.beginResetModel()
			manager.add_user_lib_elements(data, indexes)
			model.endResetModel()
			view.view.expandAll()


	#def create_road_constr(self):
	#	""" Вызывает диалоговое окно для создания позиций дорожной конструкции
	#	 или её элементов """
	#	if not self.project.road_constr_manager.library:
	#		QMessageBox.warning(
	#			self,
	#			'Отсутствуют данные',
	#			'В бибиотеке проекта отсутсвуют данные о дорожных конструкциях'
	#		)
	#		return

	#	view = self.current_boq_view()
	#	if not view:
	#		return
	#	current_index = view.view.currentIndex()
	#	if not current_index.isValid():
	#		return

	#	manager = view.manager
	#	model = view.model
	#	item = current_index.internalPointer()

	#	if isinstance(item, Section):
	#		section_index = item.address
	#		indexes = (section_index, None, None)
	#	else:
	#		indexes = item.address

	#	dialog = Road_Constr_Dialog(self, manager)
	#	if dialog.exec() == dialog.DialogCode.Accepted:
	#		data: dict = dialog.get_data()
	#		model.beginResetModel()
	#		manager.add_road_constr(data, indexes)
	#		model.endResetModel()
	#		view.view.expandAll()

	#def create_material(self):
	#	""" Вызывает диалоговое окно для создания позиций материала """
	#	if not self.project.materials_manager.library:
	#		QMessageBox.warning(
	#			self,
	#			'Отсутствуют данные',
	#			'В бибиотеке проекта отсутсвуют данные о материалах'
	#		)
	#		return

	#	view = self.current_boq_view()
	#	if not view:
	#		return
	#	current_index = view.view.currentIndex()
	#	if not current_index.isValid():
	#		return

	#	manager = view.manager
	#	model = view.model
	#	item = current_index.internalPointer()

	#	if isinstance(item, Section):
	#		section_index = item.address
	#		indexes = (section_index, None, None)
	#	else:
	#		indexes = item.address

	#	dialog = Material_Dialog(self, manager)
	#	if dialog.exec() == dialog.DialogCode.Accepted:
	#		data: dict = dialog.get_data()
	#		model.beginResetModel()
	#		manager.add_material(data, indexes)
	#		model.endResetModel()
	#		view.view.expandAll()


	# ------------- Перемещение -------------

	def move_selected(self, direction):
		"""direction: -1 (вверх), 1 (вниз)"""
		view = self.current_boq_view()
		if not view:
			return

		current_index = view.view.currentIndex()
		if not current_index.isValid():
			return

		manager = view.manager
		model = view.model
		item = current_index.internalPointer()
		if isinstance(item, Section):
			indexes = (item.address, None, None)
		else:
			indexes = item.address
		new_addr = manager.move_obj(direction, indexes)


		model.layoutChanged.emit()
		view.view.expandAll()

		self.select_item_by_address(view, new_addr)
	
	# ---------- Свёртывание / Развёртывание -----------

	def switch_collapse_expand(self, mode):
		view = self.current_boq_view()
		if not view:
			return
		if mode: view.view.expandAll()
		else: view.view.collapseAll()
	
	# -------------------- Статусы ---------------------

	def change_status(self, mode):
		""" Переключает статус позиции 0 -> сброс, 1 -> корректно, 2 -> осмечено """
		view = self.current_boq_view()
		if not view:
			return
		model = view.model
		selection = view.view.selectionModel()
		if not selection:
			return
		
		for index in selection.selectedIndexes():
			item = index.internalPointer()
			if not isinstance(item, (Work, Resource)):
				continue
			if mode == 0: item.reset_status()
			elif mode == 1: item.make_is_correct()
			else: item.make_is_calculated()
			model.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
		view.view.viewport().update()
	
	# -------------------- Стили ---------------------

	def show_background_color_menu(self):
		self._show_color_menu(is_background=True)

	def show_text_color_menu(self):
		self._show_color_menu(is_background=False)
	
	def clear_formatting(self):
		"""Сбрасывает и фон, и цвет текста для выделенных ячеек."""
		view = self.current_boq_view()
		if not view:
			return
		model = view.model
		selection = view.view.selectionModel()
		if not selection:
			return

		allowed_cols = {2, 5, 6, 7, 9}
		for index in selection.selectedIndexes():
			col = index.column()
			if col not in allowed_cols:
				continue
			item = index.internalPointer()
			if not hasattr(item, 'style_manager'):
				continue

			item.style_manager.set_background_color(col, None)
			item.style_manager.set_text_color(col, None)
			model.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])

		view.manager.is_modified = True
		view.view.viewport().update()
	
	# -------------------- Обновление ---------------------
	def reload_data(self):
		""" Заново загружает базу данных, осежает предтавление """
		self.project.set_library()
		view = self.current_boq_view()
		if not view:
			return
		model = view.model
		view.manager.set_position_mode()
		view.manager.calculate_pos_nums()
		view.manager.check_changes()
		model.layoutChanged.emit()
		view.view.expandAll()
		
	# -------------------- Экспорт ---------------------
	def open_export_dialog(self):
		view = self.current_boq_view()
		manager = view.manager
		data = manager.data_validation

		invalid_quantities = data.get('invalid_quantities')
		incorrect_positions = data.get('incorrect_positions')
		error_link_positions = data.get('error_link_positions')
		nonlink_positions = data.get('nonlink_positions')
		if invalid_quantities:
			QMessageBox.warning(self, 'Экспорт', "В ведомости присутствуют невалидные значения.")
			return
		if incorrect_positions or error_link_positions or nonlink_positions:
			problems = []
			if incorrect_positions:
				problems.append('Не все позиции имею статус готовности')
			if 	nonlink_positions:
				problems.append('Есть позиции с пустыми ссылкамию. Будет создана заглушка')
			if error_link_positions:
				problems.append('Некоторые ссылки не корректы. Результат может привести к ошибке')
			reply = Requestion.ask(
				self,
				'Предупреждение',
				f'В ведомости есть следующие проблемы:\n{"\n".join(problems)}\nПродолжить?',
				with_cancel= False
			)
			if reply == QMessageBox.StandardButton.Cancel or (
				
			):
				return
		exp_dialog = Export_Dialog(self)
		if exp_dialog.exec() == QDialog.DialogCode.Accepted:
			format, form, subsec = exp_dialog.get_data()
			try:
				convertor = Convertor(manager.project)
				if format in ('.xml', '.gge'):
					convertor.create_xml_3p01(manager, format, subsection= subsec)
					open_func = self.project.open_xml_folder
				else:
					convertor.export_to_pdf(manager, form, subsec)
					open_func = self.project.open_pdf_folder
				folder = {'.xml': 'XML', '.gge': 'XML', '.pdf': 'PDF'}	
				QMessageBox.information(self, 'Экспорт', f'Файл экспортирован в папку {folder.get(format, '#ОШИБКА')}')
				open_func()
			except Exception as e:
				QMessageBox.warning(self, 'Ошибка', f'Не удалость экспортировать файл:\n{e}')



class BoQ_View(QWidget):
	def __init__(self, parent, project, file_manager: BoQ_manager):
		super().__init__(parent)
		self.project = project
		self.manager = file_manager			# Класс управления данными файла (ведомости)
		self._shutdown_called = False
		self.setup_ui()

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

		self.view = QTreeView()
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

		self.view.setStyleSheet("""
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
		self.view.expandAll()

		splitter.addWidget(self.view)

		# -------------------------- Таблица архивных данных ----------------------------

		self.archive_view = QTreeView()
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
	
	def eventFilter(self, obj, event):
		if obj is self.view and event.type() == QEvent.Type.KeyPress:
			# --- Delete ---
			if event.key() == Qt.Key.Key_Delete:
				self.clear_selected_cells()
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

		# Удаляем модель (она удалит ссылки на manager и данные)
		if self.model:
			self.model.beginResetModel()
			self.model.manager = None   # разрываем ссылку
			self.model.deleteLater()
			self.model = None
		
		if self.archive_model:
			self.archive_model.beginResetModel()
			self.archive_model.manager = None
			self.archive_model.deleteLater()
			self.archive_model = None

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
			add_section_up.triggered.connect(lambda: self.add_section(index, item, True))
			add_section_down = section_submenu.addAction('Снизу')
			add_section_down.setIcon(down_arrow_icon)
			add_section_down.triggered.connect(lambda: self.add_section(index, item, False))

			add_work_action = menu.addAction('Добавить работу')
			add_work_action.setIcon(work_icon)
			add_work_action.triggered.connect(lambda: self.add_work(index, item))
		else:
			item: Work
			copy_submenu = menu.addMenu('Копировать...')
			copy_icon = Icons.recolor_icon(Icons.copy, QColor('#000000'))
			copy_submenu.setIcon(copy_icon)
			action_copy_address = copy_submenu.addAction('Копировать ссылку на позицию')
			action_copy_address.triggered.connect(lambda: self._copy_to_clipboard(item.format_address))

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
				add_work_up.triggered.connect(lambda: self.add_work(index, item, True))

				add_work_down = work_submenu.addAction('Снизу')
				add_work_down.setIcon(down_arrow_icon)
				add_work_down.triggered.connect(lambda: self.add_work(index, item, False))

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
			action_status_correct.triggered.connect(lambda: self._set_status(selected_indexes, 1))
			action_status_calculated = status_submenu.addAction('Отметить осмеченным')
			calculated_icon = Icons.recolor_icon(Icons.done_all, QColor("#0fcc38"))
			action_status_calculated.setIcon(calculated_icon)
			action_status_calculated.triggered.connect(lambda: self._set_status(selected_indexes, 2))
			action_status_nonvalid = status_submenu.addAction('Отметить недействительным')
			nonvalid_icon = Icons.recolor_icon(Icons.reset_status, QColor("#ff0000"))
			action_status_nonvalid.setIcon(nonvalid_icon)
			action_status_nonvalid.triggered.connect(lambda: self._set_status(selected_indexes, 0))
		
		menu.addSeparator()

		remove_action = menu.addAction('Удалить элемент')
		remove_icon = Icons.recolor_icon(Icons.delete, QColor('#000000'))
		remove_action.setIcon(remove_icon)
		remove_action.triggered.connect(self._remove_pos)
			
		# Очистка содержимого (доступна всегда)
		if selected_count > 0:
			menu.addSeparator()
			clear_action = menu.addAction('Очистить содержимое ячеек')
			clear_action.triggered.connect(self.clear_selected_cells)

		menu.exec(self.view.viewport().mapToGlobal(pos))

	# ------------------------------ Добавление элементов -------------------------------

	def add_section(self, index, item, insert):
		""" Добавляет раздел выше или ниже выбранного раздела 
		:insert: Вставка на место текущего раздела"""
		manager = self.model.manager
		if isinstance(item, Section):
			if insert:
				manager.add_section(item.address)
			else:
				manager.add_section(item.address+1)
		self.model.layoutChanged.emit()
		#self.view.expandAll()
	
	def add_work(self, index, item, insert = None):
		""" Добавляет работу в раздел через контекстное меню """
		manager = self.model.manager
		if insert is None and isinstance(item, Section):
			manager.add_work(item.address)
		elif insert is False and isinstance(item, Work):
			manager.add_work(item.address[0], item.address[1]+1)
		elif insert is True and isinstance(item, Work):
			manager.add_work(item.address[0], item.address[1])
		self.model.layoutChanged.emit()
		self.view.expandAll()

	def add_resource(self, item, insert = None):
		""" Добавляет ресурс к работе через контекстное меню """
		manager = self.model.manager
		if insert is None and isinstance(item, Work):
			manager.add_resource(item.address[0], item.address[1])
		elif insert is False and isinstance(item, Resource):
			manager.add_resource(item.address[0], item.address[1], item.address[2]+1)
		elif insert is True and isinstance(item, Resource):
			manager.add_resource(item.address[0], item.address[1], item.address[2])
		self.model.layoutChanged.emit()
		self.view.expandAll()

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


	def _set_status(self, indexes: list[QModelIndex], mode):
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
		clipboard = QApplication.clipboard()
		clipboard.setText(f'{key}|{rnd}')

	# ------------------------------- Вставка текста --------------------------------
	def _paste_unit(self):
		"""Вставляет данные о ед.изм. из буфера обмена во все выделенные ячейки в колонке 3."""
		# Проверяем, что в буфере лежит корректый ключ еденицы измерения
		clipboard = QApplication.clipboard()
		text = clipboard.text()
		if not '|' in text:
			return
		key, rnd = text.split('|')
		if rnd == 'None':
			rnd = None
		else:
			rnd = convert_value(rnd) 
		if isinstance(rnd, str) or isinstance(rnd, float):
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
				item.remove_links_from_manager()
				item.links.clear()
		for idx in indexes:
			self.model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole])
	
	def _remove_pos(self):
		current_index = self.view.currentIndex()
		if not current_index.isValid():
			return
		item = current_index.internalPointer()

		# Сбросить выделение и текущий индекс до удаления
		self.view.clearSelection()
		self.view.setCurrentIndex(QModelIndex())

		self.model.beginResetModel()
		try:
			if isinstance(item, Section):
				self.manager.remove_obj((item.address, None, None))
			elif isinstance(item, (Work, Resource)):
				self.manager.remove_obj(item.address)
		finally:
			self.model.endResetModel()
		self.view.expandAll()


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
			# Обновление происходит автоматически через signal из модели	

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


class Export_Dialog(QDialog):
	""" Окно экспорта ведомости объемов работ """
	def __init__(self, parent):
		super().__init__(parent)
		self.setWindowTitle('параметры экспорта')
		self.setModal(True)

		edit_layout = QVBoxLayout(self)

		edit_layout.addWidget(QLabel("Выберите формат экспорта:"))
		self.format_combobox = QComboBox()
		self.format_combobox.addItems(('GGE','XML', 'PDF по форме 1', 'PDF по форме 2'))
		self.format_combobox.setEditable(False)
		self.format_combobox.setCurrentIndex(0)
		edit_layout.addWidget(self.format_combobox)

		self.subsection_num = QSpinBox()
		self.subsection_num.setMinimum(0)
		self.subsection_num.setMaximumWidth(40)
		self.subsection_num.setValue(4)

		subsec_line = QHBoxLayout()
		subsec_line.addWidget(QLabel('Номер подраздела СД: '))
		subsec_line.addWidget(self.subsection_num)

		edit_layout.addLayout(subsec_line)


		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
		ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
		ok_button.setText('Применить')
		cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
		cancel_button.setText('Отменить')
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)

		edit_layout.addWidget(buttons)

	def get_data(self):
		subsec = self.subsection_num.value()
		match self.format_combobox.currentText():
			case  'GGE':
				return ('.gge', None, subsec)
			case 'XML':
				return ('.xml', None, subsec)
			case 'PDF по форме 1':
				return ('.pdf', 0, subsec)
			case 'PDF по форме 2':
				return ('.pdf', 1, subsec)


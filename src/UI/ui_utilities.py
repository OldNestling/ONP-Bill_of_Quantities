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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QMenu, QTreeView, QDialog, 
							 QTextEdit, QLineEdit, QDialogButtonBox, QStyledItemDelegate, 
							 QPlainTextEdit, QTableWidget, QFrame, QStyle, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QModelIndex
from PyQt6.QtGui import QPainter, QColor, QBrush, QTextDocument, QFont, QPen, QIntValidator

class Switch(QWidget):
	"""Кастомный переключатель (слайдер)"""
	toggled = pyqtSignal(bool)  # сигнал, испускаемый при изменении состояния

	def __init__(self, parent=None, checked=False):
		super().__init__(parent)
		self.setFixedSize(30, 15)		  # фиксированный размер
		self._checked = checked			 # начальное состояние
		self.setCursor(Qt.CursorShape.PointingHandCursor)  # курсор-рука

	def paintEvent(self, event):
		"""Отрисовка переключателя"""
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)

		# Цвет фона в зависимости от состояния
		if self._checked:
			bg_color = QColor(76, 175, 80)   # зелёный (включено)
		else:
			bg_color = QColor(204, 204, 204)  # серый (выключено)

		# Рисуем закруглённый фон
		painter.setBrush(QBrush(bg_color))
		painter.setPen(Qt.PenStyle.NoPen)
		painter.drawRoundedRect(0, 0, self.width(), self.height(),
								self.height() / 2, self.height() / 2)

		# Рисуем круглый ползунок (белый кружок)
		margin = 2
		if self._checked:
			# Включён – ползунок справа
			x = self.width() - self.height() + margin
		else:
			# Выключен – ползунок слева
			x = margin
		y = margin
		circle_size = self.height() - 2 * margin
		painter.setBrush(QBrush(QColor(255, 255, 255)))
		painter.drawEllipse(x, y, circle_size, circle_size)

	def mousePressEvent(self, event):
		"""Обработка клика – переключение состояния"""
		self._checked = not self._checked
		self.update()					   # перерисовать
		self.toggled.emit(self._checked)	# испустить сигнал

	def isChecked(self):
		"""Возвращает текущее состояние"""
		return self._checked

	def setChecked(self, checked):
		"""Устанавливает состояние программно"""
		if self._checked != checked:
			self._checked = checked
			self.update()

class WordWrapDelegate(QStyledItemDelegate):
	"""Делегат для отображения текста с переносом и автоматической высотой строк."""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.margin = 4

	def is_parent_item(self, index):
		"""Проверяет, является ли элемент родительским (имеет детей)."""
		model = index.model()
		return model is not None and model.rowCount(index) > 0

	def paint(self, painter: QPainter, option, index: QModelIndex):
		painter.save()

		# Рисуем фон (из модели или стандартный)
		bg_brush = index.data(Qt.ItemDataRole.BackgroundRole)
		if bg_brush is not None:
			painter.fillRect(option.rect, bg_brush)
		else:
			if option.state & QStyle.StateFlag.State_Selected:
				painter.fillRect(option.rect, option.palette.highlight())
			else:
				painter.fillRect(option.rect, option.palette.base())

		text = index.data(Qt.ItemDataRole.DisplayRole) or ""

		if self.is_parent_item(index):
			# Для родительских строк: текст в одну строку
			painter.setFont(option.font)
			text_rect = option.rect.adjusted(self.margin, self.margin, -self.margin, -self.margin)
			if option.state & QStyle.StateFlag.State_Selected:
				color = option.palette.highlightedText().color()
			else:
				color = option.palette.text().color()
			painter.setPen(color)
			painter.drawText(text_rect, Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
		else:
			# Для дочерних строк: перенос через QTextDocument
			doc = QTextDocument()
			doc.setPlainText(text)
			text_width = option.rect.width() - 2 * self.margin
			doc.setTextWidth(max(text_width, 1))
			if option.state & QStyle.StateFlag.State_Selected:
				color = option.palette.highlightedText().color()
			else:
				color = option.palette.text().color()
			doc.setDefaultStyleSheet(f"body {{ color: {color.name()}; }}")
			painter.translate(option.rect.x() + self.margin, option.rect.y() + self.margin)
			doc.drawContents(painter)
			painter.translate(-option.rect.x() - self.margin, -option.rect.y() - self.margin)

		painter.restore()

	def sizeHint(self, option, index: QModelIndex) -> QSize:
		if self.is_parent_item(index):
			# Стандартная высота для родительской строки (однострочный текст)
			fm = option.fontMetrics
			height = fm.height() + 2 * self.margin
			width = option.rect.width() if option.rect.width() > 0 else 100
			return QSize(width, height)
		else:
			text = index.data(Qt.ItemDataRole.DisplayRole) or ""
			if not text:
				return QSize(0, 0)

			width = option.rect.width()
			if width <= 0:
				tree_view = option.widget
				if tree_view:
					width = tree_view.columnWidth(index.column())
				else:
					width = 100

			text_width = width - 2 * self.margin
			if text_width <= 0:
				text_width = 1

			doc = QTextDocument()
			doc.setPlainText(text)
			doc.setTextWidth(text_width)

			size = doc.size().toSize()
			size.setHeight(size.height() + 2 * self.margin)
			return size

class MultiLineEditDelegate(QStyledItemDelegate):
	"""Делегат для редактирования многострочного текста с корректным sizeHint."""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.margin = 4

	def createEditor(self, parent, option, index):
		editor = QTextEdit(parent)
		editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
		editor.setFrameStyle(QFrame.Shape.NoFrame)
		return editor

	def setEditorData(self, editor, index):
		text = index.data(Qt.ItemDataRole.EditRole) or ""
		editor.setPlainText(text)

	def setModelData(self, editor, model, index):
		text = editor.toPlainText()
		# Сохраняем текст в DisplayRole (для отображения) и в EditRole (для редактирования)
		model.setData(index, text, Qt.ItemDataRole.DisplayRole)
		model.setData(index, text, Qt.ItemDataRole.EditRole)
		# Заставляем дерево пересчитать высоту строк
		tree_view = self.parent()
		if tree_view and isinstance(tree_view, QTreeView):
			tree_view.scheduleDelayedItemsLayout()
			tree_view.viewport().update()

	def updateEditorGeometry(self, editor, option, index):
		editor.setGeometry(option.rect)

	def sizeHint(self, option, index: QModelIndex) -> QSize:
		"""Возвращает высоту, необходимую для отображения всего текста с переносом."""
		text = index.data(Qt.ItemDataRole.DisplayRole) or ""
		if not text:
			return QSize(0, 0)

		width = option.rect.width()
		if width <= 0:
			tree_view = option.widget
			if tree_view:
				width = tree_view.columnWidth(index.column())
			else:
				width = 100

		text_width = width - 2 * self.margin
		if text_width <= 0:
			text_width = 1

		doc = QTextDocument()
		doc.setPlainText(text)
		doc.setTextWidth(text_width)

		size = doc.size().toSize()
		size.setHeight(size.height() + 2 * self.margin)
		return size

class MultilineTextDelegate(QStyledItemDelegate):
	"""Делегат для многострочного редактирования текста в ячейке таблицы."""
	def createEditor(self, parent, option, index):
		editor = QPlainTextEdit(parent)
		editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

		# Получаем ссылку на таблицу (родительский виджет)
		table = index.model().parent() if hasattr(index.model(), 'parent') else parent.parent()
		if isinstance(table, QTableWidget):
			# Сохраняем номер строки и ссылку на таблицу
			editor.current_row = index.row()
			editor.table = table
			# Подключаем сигнал изменения текста
			editor.textChanged.connect(lambda: self.on_text_changed(editor))
		return editor
	
	def on_text_changed(self, editor):
		"""Обработчик изменения текста — обновляет высоту строки."""
		if hasattr(editor, 'table') and hasattr(editor, 'current_row'):
			editor.table.resizeRowToContents(editor.current_row)
	
	def setEditorData(self, editor, index):
		text = index.model().data(index, Qt.ItemDataRole.DisplayRole) or ""
		editor.setPlainText(text)
		
	def setModelData(self, editor, model, index):
		model.setData(index, editor.toPlainText(), Qt.ItemDataRole.EditRole)

	def updateEditorGeometry(self, editor, option, index):
		editor.setGeometry(option.rect)


def create_ok_cancel_buttons(dialog, is_edit_mode, ok_text = None, cancel_text = None):
	"""
	Создаёт кнопки OK/Cancel, настраивает текст OK в зависимости от режима.

	Args:
		:dialog: диалог, к которому будут подключены сигналы (должен иметь accept и reject)
		:is_edit_mode: True — режим редактирования, False — создания

	Returns:
		:return: QDialogButtonBox
	"""

	btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
	ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
	if ok_text is None:
		ok_btn_name = 'Применить' if is_edit_mode else 'Создать'
	else:
		ok_btn_name = ok_text
	ok_btn.setText(ok_btn_name)

	cancel_btn = btns.button(QDialogButtonBox.StandardButton.Cancel)
	if cancel_text is None:
		cancel_btn.setText('Отменить')
	else:
		cancel_btn.setText(cancel_text)
	btns.accepted.connect(dialog.accept)
	btns.rejected.connect(dialog.reject)
	return btns

class NoteTooltip(QLabel):
	"""Всплывающая подсказка для заметки."""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowFlags(Qt.WindowType.ToolTip)
		self.setWordWrap(True)
		self.setMaximumWidth(300)
		self.setFont(QFont("Arial", 10))
		self.setStyleSheet("""
			background-color: #ffffe0;
			border: 1px solid black;
			padding: 4px;
			color: black;
		""")
		self.hide()

	def show_note(self, text, pos):
		self.setText(text)
		self.adjustSize()
		self.move(pos)
		self.show()

	def hide_note(self):
		self.hide()

class TableWithNotes(QTableWidget):
	"""Таблица с поддержкой заметок (obj.comment) в первом столбце."""
	def __init__(self, manager, parent=None, lib_type='soils_dict'):
		super().__init__(parent)
		self.manager = manager
		# lib_type больше не используется, но оставлен для обратной совместимости
		self.tooltip = NoteTooltip(self)
		self.current_tooltip_cell = None		  # (row, col) ячейки, для которой показана подсказка
		self.setMouseTracking(True)			   # отслеживаем движение мыши

	def set_manager(self, manager):
		"""Обновляет ссылку на менеджер (при смене проекта)."""
		self.manager = manager

	def _get_object_by_key(self, key_str):
		"""Возвращает объект из библиотеки по ключу (строка из первого столбца)."""
		if not self.manager or not hasattr(self.manager, 'library'):
			return None

		lib = self.manager.library
		if isinstance(lib, dict):
			# Словарь: ключ — строка
			return lib.get(key_str)
		elif isinstance(lib, list):
			# Список: ключ — индекс (строка таблицы)
			try:
				idx = int(key_str) - 1
				if 0 <= idx < len(lib):
					return lib[idx]
			except (ValueError, TypeError):
				pass
		return None

	# ---------- События мыши для отображения/скрытия подсказки ----------
	def mouseMoveEvent(self, event):
		super().mouseMoveEvent(event)

		pos = event.position().toPoint()
		index = self.indexAt(pos)
		if index.isValid() and index.column() == 0:
			item = self.item(index.row(), 0)
			if item:
				obj = self._get_object_by_key(item.text())
				if obj and obj.comment:
					if (index.row(), index.column()) != self.current_tooltip_cell:
						rect = self.visualRect(index)
						global_pos = self.viewport().mapToGlobal(rect.topRight())
						self.tooltip.show_note(obj.comment, global_pos)
						self.current_tooltip_cell = (index.row(), index.column())
					return  # не скрываем подсказку, если она показана
		# Если мы не в нужной ячейке или нет комментария, скрываем подсказку
		if self.current_tooltip_cell is not None:
			self.tooltip.hide_note()
			self.current_tooltip_cell = None

	def leaveEvent(self, event):
		"""Скрываем подсказку, когда мышь покидает таблицу."""
		self.tooltip.hide_note()
		self.current_tooltip_cell = None
		super().leaveEvent(event)

	# ---------- Контекстное меню для редактирования заметки ----------
	def contextMenuEvent(self, event):
		pos = event.pos()
		index = self.indexAt(pos)
		if index.isValid() and index.column() == 0:
			item = self.item(index.row(), 0)
			if item:
				obj = self._get_object_by_key(item.text())
				if obj:
					menu = QMenu()
					if obj.comment:
						action_edit = menu.addAction("Изменить заметку...")
						action_remove = menu.addAction("Удалить заметку")
					else:
						action_add = menu.addAction("Добавить заметку...")
					action = menu.exec(self.viewport().mapToGlobal(pos))
					if obj.comment:
						if action == action_edit:
							self.edit_comment(obj)
						elif action == action_remove:
							self.set_comment(obj, None)
					else:
						if action == action_add:
							self.edit_comment(obj)
					return  # событие обработано, дальше не передаём
		# Для всех остальных столбцов (или если не удалось обработать столбец 0) передаём событие дальше
		super().contextMenuEvent(event)

	def edit_comment(self, obj):
		"""Открывает диалог редактирования примечания."""
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
			self.set_comment(obj, new_note if new_note else None)

	def set_comment(self, obj, comment):
		"""Сохраняет комментарий в объекте и обновляет отображение."""
		obj.set_comment(comment)
		# Скрываем текущую подсказку, чтобы при повторном наведении обновилась
		if self.current_tooltip_cell is not None:
			self.tooltip.hide_note()
			self.current_tooltip_cell = None
		# Перерисовываем таблицу для обновления треугольника
		self.update()

	def paintEvent(self, event):
		super().paintEvent(event)
		painter = QPainter(self.viewport())
		painter.setPen(QPen(QColor(255, 0, 0), 2))
		for row in range(self.rowCount()):
			item = self.item(row, 0)
			if item:
				obj = self._get_object_by_key(item.text())
				if obj and obj.comment:
					rect = self.visualRect(self.model().index(row, 0))
					points = [
						rect.topRight() + QPoint(-5, 0),
						rect.topRight(),
						rect.topRight() + QPoint(0, 5)
					]
					painter.setBrush(QColor(255, 0, 0))
					painter.drawPolygon(points)



class IntDelegate(QStyledItemDelegate):
	def createEditor(self, parent, option, index):
		if not (index.flags() & Qt.ItemFlag.ItemIsEditable):
			return None
		editor = QLineEdit(parent)
		editor.setValidator(QIntValidator())   # ограничиваем ввод только целыми числами
		return editor

	def setEditorData(self, editor, index):
		value = index.model().data(index, Qt.ItemDataRole.EditRole)
		if value is not None:
			editor.setText(str(value))

	def setModelData(self, editor, model, index):
		model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)



class Requestion(QMessageBox):
	"""
	Класс для отображения вопросов с кнопками на русском языке.
	Наследует QMessageBox и предоставляет готовые кнопки Да, Нет, Отмена.
	"""

	def __init__(
		self,
		parent=None,
		title: str = "",
		text: str = "",
		yes_text: str = "Да",
		no_text: str = "Нет",
		cancel_text: str = "Отмена",
		with_cancel: bool = True
	):
		"""
		:param parent: родительский виджет
		:param title: заголовок окна
		:param text: текст запроса
		:param yes_text: надпись на кнопке 'Да'
		:param no_text: надпись на кнопке 'Нет'
		:param cancel_text: надпись на кнопке 'Отмена'
		:param with_cancel: создать кнопку 'Отмена'
		"""
		super().__init__(parent)

		# Установка основных атрибутов
		self.setWindowTitle(title)
		self.setText(text)
		self.setIcon(QMessageBox.Icon.Question)

		# Добавление стандартных кнопок с переопределёнными текстами
		yes_btn = self.addButton(QMessageBox.StandardButton.Yes)
		yes_btn.setText(yes_text)

		no_btn = self.addButton(QMessageBox.StandardButton.No)
		no_btn.setText(no_text)

		if with_cancel:
			cancel_btn = self.addButton(QMessageBox.StandardButton.Cancel)
			cancel_btn.setText(cancel_text)

		# Установка кнопок по умолчанию (Enter → Да, Esc → Отмена)
		self.setDefaultButton(yes_btn)
		if with_cancel: self.setEscapeButton(cancel_btn)

	@staticmethod
	def ask(
		parent=None,
		title: str = "",
		text: str = "",
		yes_text: str = "Да",
		no_text: str = "Нет",
		cancel_text: str = "Отмена",
		with_cancel: bool = True
	) -> QMessageBox.StandardButton:
		"""
		Статический метод для быстрого вызова диалога.
		Возвращает значение QMessageBox.StandardButton (Yes, No или Cancel).
		"""
		box = Requestion(parent, title, text, yes_text, no_text, cancel_text, with_cancel)
		return box.exec()  # exec() возвращает нажатую стандартную кнопку
	

# ===================================== Вспомогательные функции =============================================

def create_separator(shape=QFrame.Shape.HLine, shadow=QFrame.Shadow.Sunken):
	separator = QFrame()
	separator.setFrameShape(shape)
	separator.setFrameShadow(shadow)
	return separator

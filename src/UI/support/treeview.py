
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

from PyQt6.QtWidgets import QTreeView, QAbstractItemView
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtCore import (
	Qt, QModelIndex, QEvent, QPropertyAnimation, QEasingCurve, QPoint
)



class SmoothTreeView(QTreeView):
	"""QTreeView с плавной прокруткой и масштабированием по Ctrl+колесо."""

	ZOOM_MIN      = -6         # минимальный «шаг» зума
	ZOOM_MAX      = 20         # максимальный
	ZOOM_STEP     = 1.0        # pt за один щелчок колеса
	WHEEL_DURATION = 180       # мс анимации прокрутки
	
	TOUCHPAD_FACTOR = 5.0     # тачпад: pixelDelta часто слишком мелкая
	WHEEL_FACTOR    = 2.5     # мышь: сколько «строк» за один щелчок колеса

	# --- пороги для pinch-жеста (значения Qt-жестов очень мелкие) ---
	PINCH_THRESHOLD = 0.08      # столько накопить, чтобы сдвинуть зум на 1 pt
	PINCH_MAX_STEP  = 3         # максимум «шагов зума» за одно событие

	# ------------------------------------------------------------------
	# Базовый QSS виджета БЕЗ font-size. Размер шрифта подставляется
	# динамически в _apply_font_style() c более специфичным селектором,
	# чем глобальный '* { font-size: 10pt }' из styles.py.
	# ------------------------------------------------------------------
	_BASE_STYLE = """
		QTreeView {{
			outline: none;
		}}
		QTreeView::item {{
			border-bottom: 1px solid #d0d0d0;
			border-right: 1px solid #d0d0d0;
		}}
		QTreeView::item:first {{
			border-top: 1px solid #d0d0d0;
		}}
		QTreeView::item:last {{
			border-bottom: 1px solid #d0d0d0;
		}}
	"""
	def __init__(self, parent=None):
		super().__init__(parent)

		# сохраняем эталонные шрифты view и header ДО возможных правок
		self._base_view_font   = QFont(self.font())
		self._base_header_font = QFont(self.header().font())

		base_pt = self._base_view_font.pointSizeF()
		if base_pt <= 0:
			base_pt = float(self._base_view_font.pixelSize())
		self._base_font_size = base_pt if base_pt > 0 else 10.0

		# --- пиксельная прокрутка ---
		self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
		self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

		# --- анимация «инерции» колеса ---
		self._anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
		self._anim.setDuration(self.WHEEL_DURATION)
		self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

		# --- состояние зума ---
		self._zoom_level = 0
		self._scale_columns = True
		self._base_col_widths: dict[int, int] = {}
		self._zooming = False

		# аккумулятор pinch-жеста
		self._pinch_accum = 0.0

		# при ручном ресайзе колонок (при зуме 0) обновляем «эталон»
		self.header().sectionResized.connect(self._on_section_resized)

		# Ctrl+0 — сброс зума
		act = QAction(self)
		act.setShortcut("Ctrl+0")
		act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
		act.triggered.connect(self.reset_zoom)
		self.addAction(act)

		# Применяем начальный QSS с текущим размером шрифта
		self._apply_font_style()


	def _apply_font_style(self):
		"""Устанавливает QSS с актуальным размером шрифта.

		Селекторы QTreeView и QHeaderView::section имеют специфичность
		выше, чем глобальный '* { font-size: 10pt }' из styles.py,
		поэтому эти правила переопределяют глобальный размер ТОЛЬКО
		для данного виджета и его заголовка.
		"""
		new_pt = max(4.0, self._base_font_size + self._zoom_level * self.ZOOM_STEP)

		style = self._BASE_STYLE.format() + f"""
			QTreeView {{
				font-size: {new_pt:.2f}pt;
			}}
			QHeaderView::section {{
				font-size: {new_pt:.2f}pt;
			}}
		"""
		self.setStyleSheet(style)

	# ===== Нативные жесты (pinch) — приходят не как QWheelEvent ======
	def event(self, event):
		if event.type() == QEvent.Type.NativeGesture:
			gtyp = event.gestureType()
			if gtyp == Qt.NativeGestureType.ZoomNativeGesture:
				self._on_pinch(event.value())
				return True
		return super().event(event)


	def _on_pinch(self, value: float):
		"""value приходит очень мелким (обычно ±0.005…±0.05 за кадр)."""
		self._pinch_accum += value
		if abs(self._pinch_accum) <self.PINCH_THRESHOLD:
			return

		steps = int(self._pinch_accum / self.PINCH_THRESHOLD)
		steps = max(-self.PINCH_MAX_STEP, min(self.PINCH_MAX_STEP, steps))
		self._pinch_accum -= steps * self.PINCH_THRESHOLD

		for _ in range(abs(steps)):
			self._change_zoom(1 if steps > 0 else -1)

	# =========================== Колесо мыши =========================
	def wheelEvent(self, event):
		# --- Ctrl+Wheel = zoom ---
		if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
			delta = event.angleDelta().y() or event.pixelDelta().y()
			if delta > 0:
				self._change_zoom(+1)
			elif delta < 0:
				self._change_zoom(-1)
			event.accept()
			return

		# --- обычная прокрутка ---
		pixel = event.pixelDelta()
		angle = event.angleDelta()

		if not pixel.isNull():
			# тачпад: пиксельная дельта, уже «естественная» — не масштабируем
			step = int(pixel.y() * self.TOUCHPAD_FACTOR)
		elif not angle.isNull():
			# обычная мышь: 1 щелчок = 120 units ≈ высота строки
			row_h = self.sizeHintForRow(0) or 24
			step = int(row_h * angle.y() * self.WHEEL_FACTOR/ 120)
		else:
			return super().wheelEvent(event)

		if step == 0:
			# очень мелкое движение — не запускаем анимацию зря
			event.accept()
			return

		bar = self.verticalScrollBar()
		current = bar.value()
		target = max(bar.minimum(), min(bar.maximum(), current - step))

		if self._anim.state() == QPropertyAnimation.State.Running:
			self._anim.stop()
		self._anim.setStartValue(current)
		self._anim.setEndValue(target)
		self._anim.start()
		event.accept()

	# ============================== zoom ===================================
	def _change_zoom(self, direction: int):
		new_level = self._zoom_level + direction
		if not (self.ZOOM_MIN <= new_level <= self.ZOOM_MAX):
			return
		self._zoom_level = new_level
		self._apply_zoom()

	def reset_zoom(self):
		if self._zoom_level != 0:
			self._zoom_level = 0
			self._apply_zoom()

	def _apply_zoom(self):
		# 1. запоминаем «якорь» — верхний видимый index + смещение пикселя
		anchor_index, anchor_offset = self._top_anchor()

		# 2. останавливаем анимацию, чтобы не мешала
		if self._anim.state() == QPropertyAnimation.State.Running:
			self._anim.stop()

		# 3. ГЛАВНОЕ: применяем размер шрифта через QSS виджета.
		#    setFont() здесь бесполезен — глобальный '* { font-size }'
		#    имеет приоритет над ним, а вот более специфичный селектор
		#    QTreeView в stylesheet самого виджета — выигрывает.
		self._apply_font_style()

		# 4. дополнительно обновляем font самого виджета и его header —
		#    это нужно для расчёта размеров (sizeHintForRow, visualRect и т.п.),
		#    чтобы layout-движок знал актуальные метрики.
		new_pt = max(4.0, self._base_font_size + self._zoom_level * self.ZOOM_STEP)

		# сам QTreeView
		vf = QFont(self._base_view_font)
		vf.setPointSizeF(new_pt)
		super().setFont(vf)

		# заголовок — иначе он останется на прежнем размере
		hf = QFont(self._base_header_font)
		hf.setPointSizeF(new_pt)
		# сохраняем bold, который вы выставляете в setup_ui
		hf.setBold(self._base_header_font.bold())
		self.header().setFont(hf)

		# 5. масштабируем ширины столбцов от базовых значений
		if self._scale_columns:
			factor = new_pt / self._base_font_size
			self._zooming = True
			try:
				model = self.model()
				if model is not None:
					for col in range(model.columnCount()):
						if col not in self._base_col_widths:
							w = self.columnWidth(col)
							self._base_col_widths[col] = w if w > 0 else 80
						self.setColumnWidth(
							col, max(20, int(self._base_col_widths[col] * factor))
						)
			finally:
				self._zooming = False

		# 6. восстанавливаем «якорь» на месте
		if anchor_index is not None and anchor_index.isValid():
			self.scrollTo(anchor_index,
						  QAbstractItemView.ScrollHint.PositionAtTop)
			bar = self.verticalScrollBar()
			bar.setValue(max(bar.minimum(), bar.value() + anchor_offset))

	# ------------------------------------------------------------------
	def _top_anchor(self):
		"""Возвращает (QModelIndex верхнего видимого элемента, смещение в пикселях)."""
		rect = self.viewport().rect()
		probe = QPoint(rect.left() + 1, rect.top() + 1)
		idx = self.indexAt(probe)
		if not idx.isValid():
			return None, 0
		vr = self.visualRect(idx)
		offset = rect.top() - vr.top()      # отрицательное, если строка ушла вверх
		return idx, offset

	# ------------------------------------------------------------------
	def _on_section_resized(self, logicalIndex, oldSize, newSize):
		"""Пользователь двигает разделитель колонки — обновляем эталон."""
		if self._zooming:
			return                          # это наш собственный setColumnWidth
		if self._zoom_level == 0:
			self._base_col_widths[logicalIndex] = newSize
		else:
			# при активном зуме пересчитываем эталон, снимая масштаб
			factor = (self._base_font_size
					  + self._zoom_level * self.ZOOM_STEP) / self._base_font_size
			if factor > 0:
				self._base_col_widths[logicalIndex] = max(1, int(newSize / factor))

	# ======================= Навигация стрелками =======================
	def moveCursor(self, cursorAction, modifiers):
		"""Переопределяем поведение Left/Right: вместо сворачивания/разворачивания —
		перемещение выделения по горизонтали.

		Важно: QTreeView реализует collapse/expand именно внутри своего
		moveCursor(). Переопределив этот метод для MoveLeft/MoveRight,
		мы полностью убираем побочный эффект в дереве. Всё остальное
		(Shift-расширение выделения, автоскролл, обработка Up/Down/Home/End)
		остаётся на Qt — она сама вызывает moveCursor() и выставляет флаги
		выделения через selectionCommand().
		"""
		if cursorAction == QAbstractItemView.CursorAction.MoveLeft:
			return self._horizontal_neighbor(-1)
		if cursorAction == QAbstractItemView.CursorAction.MoveRight:
			return self._horizontal_neighbor(+1)
		return super().moveCursor(cursorAction, modifiers)


	def _horizontal_neighbor(self, delta: int) -> QModelIndex:
		"""Возвращает индекс ячейки, смещённый на delta столбцов от текущей,
		в пределах той же строки. Если вышли за границу — возвращает текущий
		индекс (Qt это воспринимает как «сдвига нет»)."""
		current = self.currentIndex()
		if not current.isValid():
			return current

		model = self.model()
		if model is None:
			return current

		row    = current.row()
		parent = current.parent()
		cols   = model.columnCount(parent)

		new_col = current.column() + delta
		while 0 <= new_col < cols:
			idx = model.index(row, new_col, parent)
			if idx.isValid():
				return idx
			new_col += delta

		return current

	# ==================== Alt+Left / Alt+Right ====================
	def keyPressEvent(self, event):
		key  = event.key()
		mods = event.modifiers()

		if mods & Qt.KeyboardModifier.AltModifier:
			if key == Qt.Key.Key_Left:
				self._collapse_current()
				event.accept()
				return
			if key == Qt.Key.Key_Right:
				self._expand_current()
				event.accept()
				return

		super().keyPressEvent(event)


	def _collapse_current(self):
		idx = self._tree_index(self.currentIndex())
		if idx.isValid() and self.isExpanded(idx):
			self.collapse(idx)


	def _expand_current(self):
		idx = self._tree_index(self.currentIndex())
		model = self.model()
		if (idx.isValid() and model is not None
				and model.hasChildren(idx) and not self.isExpanded(idx)):
			self.expand(idx)


	def _tree_index(self, idx: QModelIndex) -> QModelIndex:
		"""Возвращает индекс той же строки, но в столбце 0 —
		именно с ним работают expand/collapse у QTreeView.
		Если индекс уже в столбце 0 или невалиден — возвращает его же."""
		if not idx.isValid() or idx.column() == 0:
			return idx
		model = self.model()
		if model is None:
			return idx
		sibling = model.sibling(idx.row(), 0, idx)
		return sibling if sibling.isValid() else idx
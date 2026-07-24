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
	QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QCompleter,
	QLineEdit, QApplication, QScrollArea, QFrame, QListWidget
	)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from ..icons import Icons
from Core.Utilities import clearing_string
import re, math

class Calculator:
	SAFE_DICT = {
				'__builtins__': None,
				'abs': abs,
				'модуль': abs,
				'round': round,
				'округл': round,
				'min': min,
				'мин': min,
				'max': max,
				'макс': max,
				'pow': pow,
				'степень': pow,
				'sqrt': math.sqrt,
				'корень': math.sqrt,
				'sin': math.sin,
				'синус': math.sin,
				'cos': math.cos,
				'косинус': math.cos,
				'tan': math.tan,
				'тангенс': math.tan,
				'asin': math.asin,
				'асинус': math.asin,
				'acos': math.acos,
				'акосинус': math.acos,
				'atan': math.atan,
				'атангенс': math.atan,
				'log': math.log,
				'логарифм': math.log,
				'log10': math.log10,
				'логарифм10': math.log10,
				'exp': math.exp,
				'pi': math.pi,
				'пи': math.pi,
				'e': math.e,
				'rad': math.radians,
				'рад': math.radians,
				'deg': math.degrees,
				'град': math.degrees,
				'длн_круга': lambda r: 2*math.pi*r,
				'пов_цилиндра': lambda r, h: 2*math.pi*r*h,
				'пл_круга': lambda r: math.pi*r**2,
				'объем_цилиндра': lambda r, h: h*math.pi*r**2
			}
	
	def __init__(self):
		self.calc_story = []  # [ [expression, result], ... ]

	def calculate(self, input_str, is_recalc=False):
		"""
		Вычисляет строку и, если is_recalc=False, добавляет в историю.
		"""
		if not input_str:
			return None

		# Переменная для очищенной строки – объявляем заранее
		clear_input = ""
		try:
			clear_input = clearing_string(input_str)
			text_to_calc = clear_input.replace('^', '**').replace(';',',')
			text_to_calc = self._replace_links(text_to_calc)

			# Безопасное окружение для eval
			
			res = eval(text_to_calc, self.SAFE_DICT)

			if isinstance(res, float):
				res = round(res, 6)

			if not is_recalc:
				self.calc_story.append([clear_input, res])
			else:
				return res

		except Exception as e:
			# Если произошла ошибка – записываем в историю 'Ошибка'
			if not is_recalc:
				self.calc_story.append([clear_input if clear_input else input_str, '#Ошибка'])
			else:
				return '#Ошибка'

	def _replace_links(self, expr: str) -> str:
		"""Заменяет $N на значение из истории (индексация с 1)"""
		pattern = re.compile(r'\$(\d+)')

		def repl(match):
			idx = int(match.group(1)) - 1
			if 0 <= idx < len(self.calc_story):
				val = self.calc_story[idx][1]
				if val == '#Ошибка':
					raise ValueError(f"Ссылка ${idx+1} ведёт на ошибочное выражение")
				return str(val)
			else:
				# Несуществующая ссылка – выбросим исключение
				raise ValueError(f"Ссылка ${idx+1} не существует")

		try:
			return pattern.sub(repl, expr)
		except ValueError as e:
			# Пробрасываем дальше, чтобы обработать в calculate
			raise

	def recalc_element(self, idx: int):
		expr = self.calc_story[idx][0]
		new_res = self.calculate(expr, is_recalc=True)
		self.calc_story[idx][1] = new_res

	def recalc_all(self):
		for i in range(len(self.calc_story)):
			self.recalc_element(i)

	def clear_story(self):
		self.calc_story.clear()

	def copy_res_to_clipboard(self, index=-1):
		if not self.calc_story:
			return
		res = self.calc_story[index][1]
		QApplication.clipboard().setText(str(res))

	# ---------------------------------- Пользовательские функции ----------------------------------

class HistoryItemWidget(QWidget):
	"""Виджет строки истории: $индекс | выражение | результат | копировать | удалить"""
	expressionChanged = pyqtSignal(int, str)   # индекс, новое выражение
	copyRequested = pyqtSignal(int)			# индекс
	deleteRequested = pyqtSignal(int)		  # индекс

	def __init__(self, index: int, expr: str, result, parent=None):
		super().__init__(parent)
		self.index = index
		self.setup_ui(expr, result)

	def setup_ui(self, expr, result):
		layout = QHBoxLayout(self)
		layout.setContentsMargins(5, 2, 5, 2)

		# Метка с индексом
		self.lbl_index = QLabel(f"${self.index + 1}")
		self.lbl_index.setMinimumWidth(40)
		layout.addWidget(self.lbl_index)

		# Редактируемое выражение
		self.expr_edit = QLineEdit(expr)
		self.expr_edit.textChanged.connect(self.on_expr_changed)
		layout.addWidget(self.expr_edit, stretch=2)

		# Результат
		self.lbl_result = QLabel(str(result))
		#self.lbl_result.setMinimumWidth(80)
		font = self.lbl_result.font()
		font.setBold(True)
		self.lbl_result.setFont(font)
		layout.addWidget(self.lbl_result)

		# Кнопка копирования
		self.btn_copy = QPushButton()
		self.btn_copy.setIcon(Icons.copy)   # предполагается, что Icons.copy существует
		self.btn_copy.setToolTip("Копировать результат")
		self.btn_copy.setFixedSize(24, 24)
		self.btn_copy.clicked.connect(lambda: self.copyRequested.emit(self.index))
		layout.addWidget(self.btn_copy)

		# Кнопка удаления
		self.btn_delete = QPushButton()
		self.btn_delete.setIcon(Icons.delete)
		self.btn_delete.setToolTip("Удалить строку")
		self.btn_delete.setFixedSize(24, 24)
		self.btn_delete.clicked.connect(lambda: self.deleteRequested.emit(self.index))
		layout.addWidget(self.btn_delete)

	def on_expr_changed(self, new_text):
		self.expressionChanged.emit(self.index, new_text)

	def update_result(self, new_result):
		self.lbl_result.setText(str(new_result))


class CalculatorWidget(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.calculator = Calculator()
		self.setup_ui()

	def setup_ui(self):
		main_layout = QVBoxLayout(self)
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.setSpacing(5)

		# ---------- Кнопка очистки истории ----------
		
		self.btn_clear = QPushButton("Очистить историю")
		self.btn_clear.clicked.connect(self.clear_history)
		main_layout.addWidget(self.btn_clear)

		# ---------- Обзорщик формул ----------
		formula_group = QFrame()
		formula_group.setFrameShape(QFrame.Shape.StyledPanel)
		formula_layout = QVBoxLayout(formula_group)
		formula_layout.setContentsMargins(5, 5, 5, 5)

		lbl_formulas = QLabel("<b>Готовые формулы:</b>")
		formula_layout.addWidget(lbl_formulas)

		self.formula_list = QListWidget()
		self.formula_list.setMaximumHeight(100)
		self.formula_list.itemDoubleClicked.connect(self.insert_formula)
		# Заполняем список формул
		formulas = [
				'модуль(n)',
				'округл(n;m)',
				'мин([n1;n2])',
				'макс([n1;n2])',
				'степень(n;m)',
				'корень(n)',
				'синус(rad)',
				'косинус(rad)',
				'тангенс(rad)',
				'асинус(rad)',
				'акосинус(rad)',
				'атангенс(rad)',
				'логарифм(n;b)',
				'логарифм10(n)',
				'пи',
				'рад(°)',
				'град(r)',
				'длн_круга(r)',
				'пов_цилиндра(r;h)',
				'пл_круга(r)',
				'объем_цилиндра(r;h)'
			]
		self.formula_list.addItems(formulas)
		formula_layout.addWidget(self.formula_list)

		main_layout.addWidget(formula_group)


		# ---------- История вычислений ----------
		self.scroll_area = QScrollArea()
		self.scroll_area.setWidgetResizable(True)
		self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
		self.history_container = QWidget()
		self.history_layout = QVBoxLayout(self.history_container)
		self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
		self.history_layout.setContentsMargins(0, 0, 0, 0)
		self.history_layout.setSpacing(2)
		self.scroll_area.setWidget(self.history_container)
		main_layout.addWidget(self.scroll_area, stretch=1)

		# ---------- Строка ввода ----------
		input_layout = QHBoxLayout()
		self.input_edit = QLineEdit()
		self.input_edit.setPlaceholderText("Введите формулу")
		self.input_edit.setToolTip('Поддерживаются ссылки $N и формулы')
		completer = QCompleter(tuple(Calculator.SAFE_DICT.keys()))
		self.input_edit.setCompleter(completer)
		self.input_edit.returnPressed.connect(self.calculate_new)
		self.input_edit.setMinimumHeight(30)
		self.btn_calc = QPushButton()
		self.btn_calc.setIcon(Icons.calculate)
		self.btn_calc.setIconSize(QSize(30,30))
		self.btn_calc.clicked.connect(self.calculate_new)
		input_layout.addWidget(self.input_edit, stretch=1)
		input_layout.addWidget(self.btn_calc)
		main_layout.addLayout(input_layout)

		self.update_history()

	def insert_formula(self, item):
		"""Вставляет выбранную формулу в строку ввода."""
		formula = item.text()
		current_text = self.input_edit.text()
		# Если в строке уже есть текст – добавляем формулу с пробелом, иначе просто формулу
		if current_text and not current_text.endswith(' '):
			new_text = current_text + ' ' + formula
		else:
			new_text = current_text + formula
		self.input_edit.setText(new_text)
		self.input_edit.setFocus()
		# Устанавливаем курсор в конец
		self.input_edit.end(False)

	def update_history(self):
		"""Полностью перестраивает список истории (при изменении количества строк)."""
		while self.history_layout.count():
			child = self.history_layout.takeAt(0)
			if child.widget():
				child.widget().deleteLater()

		for idx, (expr, res) in enumerate(self.calculator.calc_story):
			item = HistoryItemWidget(idx, expr, res)
			item.expressionChanged.connect(self.on_expression_changed)
			item.copyRequested.connect(self.on_copy_requested)
			item.deleteRequested.connect(self.on_delete_requested)
			self.history_layout.addWidget(item)

		QTimer.singleShot(50, self.scroll_to_bottom)

	def refresh_results(self):
		"""Обновляет отображение результатов без пересоздания виджетов."""
		for i in range(self.history_layout.count()):
			item_widget = self.history_layout.itemAt(i).widget()
			if isinstance(item_widget, HistoryItemWidget):
				# Обновляем результат из калькулятора
				new_result = self.calculator.calc_story[i][1]
				item_widget.update_result(new_result)

	def scroll_to_bottom(self):
		scrollbar = self.scroll_area.verticalScrollBar()
		scrollbar.setValue(scrollbar.maximum())

	def calculate_new(self):
		expr = self.input_edit.text().strip()
		if not expr:
			return
		self.calculator.calculate(expr)
		self.input_edit.clear()
		self.update_history()  # Добавилась новая строка — перестраиваем

	def on_expression_changed(self, idx, new_expr):
		"""Изменение текста в строке истории — пересчёт без перестройки списка."""
		if idx >= len(self.calculator.calc_story):
			return
		self.calculator.calc_story[idx][0] = new_expr
		self.calculator.recalc_all()	  # пересчитываем всё (из-за возможных ссылок)
		self.refresh_results()			 # обновляем только результаты в существующих виджетах

	def on_copy_requested(self, idx):
		self.calculator.copy_res_to_clipboard(idx)

	def on_delete_requested(self, idx):
		if idx < len(self.calculator.calc_story):
			del self.calculator.calc_story[idx]
			self.calculator.recalc_all()
			self.update_history()		  # изменилось количество строк — полная перестройка

	def clear_history(self):
		self.calculator.clear_story()
		self.update_history()
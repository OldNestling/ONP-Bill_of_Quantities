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
	QApplication, QWidget, QLabel, QDialog, QDialogButtonBox, QVBoxLayout,
	QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
	QComboBox, QSpinBox
	)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from Core.Project import File_BoQ, BoQ_manager
from Core.Convertor_BoQ import Convertor

from ..ui_utilities import MultilineTextDelegate, create_ok_cancel_buttons
from ..resources.icons import Icons

from PyQt6.QtWidgets import (
	QCheckBox, QAbstractItemView, QMessageBox, QProgressDialog,
)


class ExportFormatDialog(QDialog):
	""" Диалоговое окно выбора формата экспорта ведомостей """
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Экспорт ведомости")
		self.setModal(True)

		layout = QVBoxLayout(self)

		layout.addWidget(QLabel("Выберите формат экспорта:"))

		self.format_combobox = QComboBox()
		self.format_combobox.addItems((
			"XML",
			"GGE",
			"PDF по форме 1",
			"PDF по форме 2"
		))
		layout.addWidget(self.format_combobox)

		self.subsection_num = QSpinBox()
		self.subsection_num.setMinimum(0)
		self.subsection_num.setMaximumWidth(60)
		self.subsection_num.setValue(4)

		subsec_line = QHBoxLayout()
		subsec_line.addWidget(QLabel('Номер подраздела СД: '))
		subsec_line.addWidget(self.subsection_num)

		layout.addLayout(subsec_line)

		btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
		btn_box.accepted.connect(self.accept)
		btn_box.rejected.connect(self.reject)
		layout.addWidget(btn_box)


	def get_data(self):
		"""Возвращает расширение файла: .xml или .gge"""
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



class BoQExportSummaryDialog(QDialog):
	"""Сводный диалог с результатами проверки ведомостей перед экспортом.  """

	COLUMNS = (
		"Наименование файла",
		"Позиции осмечены",
		"Значения валидны",
		"Все ссылки корректны",
		"Нет пустых ссылок",
		"Экспортировать",
	)

	def __init__(
		self,
		candidates: list[tuple[File_BoQ, BoQ_manager, dict]],
		parent=None
	):
		"""
		### Args:
		:candidates: список кортежей (file_BoQ, manager, validation_data)
		"""
		super().__init__(parent)
		self.setWindowTitle("Анализ ведомостей перед экспортом")
		self.resize(920, 520)
		self._rows: list[tuple[File_BoQ, BoQ_manager, QCheckBox]] = []
		self._setup_ui(candidates)


	def _setup_ui(
		self,
		candidates: list[tuple[File_BoQ, object, dict]]
	):
		layout = QVBoxLayout(self)

		hint = QLabel(
			"Проверьте результаты анализа ведомостей.<br>"
			"Снимите отметки с тех разделов, которые не нужно экспортировать.<br>"
			"Разделы с невалидными объёмами исключены автоматически."
		)
		hint.setWordWrap(True)
		layout.addWidget(hint)

		self.table = QTableWidget()
		self.table.setColumnCount(len(self.COLUMNS))
		self.table.setHorizontalHeaderLabels(self.COLUMNS)
		self.table.setRowCount(len(candidates))
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.verticalHeader().setVisible(False)

		header = self.table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
		for col in range(1, len(self.COLUMNS)):
			header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

		for row, (file_BoQ, manager, validation) in enumerate(candidates):
			self._fill_row(row, file_BoQ, manager, validation)

		layout.addWidget(self.table, 1)  # таблица растягивается и прокручивается

		buttons = create_ok_cancel_buttons(self, False, 'Экспортировать')
		layout.addWidget(buttons)


	def _make_icon_cell(self, has_problem: bool, tooltip: str = "") -> QWidget:
		label = QLabel()
		
		if has_problem:
			icon = Icons.close
		else:
			icon = Icons.recolor_icon(Icons.status, QColor("#008B13"))          # RRGGBB
		
		label.setPixmap(icon.pixmap(16, 16))
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)

		if has_problem:
			label.setToolTip(tooltip)

		cell = QWidget()
		layout = QHBoxLayout(cell)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(label)
		layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
		return cell


	def _fill_row(self, row: int, file_BoQ: File_BoQ, manager, validation: dict):
		# 0. Наименование
		name_item = QTableWidgetItem(file_BoQ.path.name)
		name_item.setToolTip(str(file_BoQ.path))
		self.table.setItem(row, 0, name_item)

		# — флаги проверок (True = есть проблема → крестик) ---
		checks = (
			(
				bool(validation.get('incorrect_positions')), 
				"Не все позиции имеют статус готовности"
			),
			(
				bool(validation.get('invalid_quantities')),
				"Обнаружены невалидные значения объёмов"
			),
			(
				bool(validation.get('error_link_positions')),
				"Обнаружены некорректные ссылки"
			),
			(
				bool(validation.get('nonlink_positions')),
				"Есть позиции с пустыми ссылками (будет создана заглушка)"
			)
		)

		for col, (has_problem, tooltip) in enumerate(checks, start=1):
			self.table.setCellWidget(row, col, self._make_icon_cell(has_problem, tooltip))

		# — чекбокс ---
		values_valid = not checks[1][0]  # invalid_quantities
		checkbox = QCheckBox()
		checkbox.setChecked(values_valid)	# по умолчанию включен, если валиден
		checkbox.setEnabled(values_valid)	# доступен, если валиден
		if not values_valid:
			checkbox.setToolTip("Значения объёмов невалидны — экспорт невозможен")

		cell = QWidget()
		cell_layout = QHBoxLayout(cell)
		cell_layout.addWidget(checkbox)
		cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
		cell_layout.setContentsMargins(0, 0, 0, 0)
		self.table.setCellWidget(row, 5, cell)

		self._rows.append((file_BoQ, manager, checkbox))


	def get_export_list(self) -> list[tuple[File_BoQ, BoQ_manager]]:
		"""Возвращает (file_BoQ, manager) только для выбранных пользователем."""
		return [
			(file_BoQ, manager)
			for file_BoQ, manager, checkbox in self._rows
			if checkbox.isChecked()
		]



class ExportManager:
	"""Инкапсулирует весь сценарий экспорта ведомостей.

	Шаги:
	  1) сбор выбранных строк таблицы;
	  2) проверка блокировок;
	  3) однократная загрузка менеджеров в память;
	  4) сводный диалог проверок;
	  5) выбор формата;
	  6) собственно экспорт.
	"""

	def __init__(self, main_tab):
		# main_tab — это MainProjectTab (нужен для parent-окон и доступа к project)
		self.main_tab = main_tab
		self.project = main_tab.project


	def run(self) -> None:
		if self.project is None:
			QMessageBox.warning(self.main_tab, "Экспорт", "Проект не загружен.")
			return

		selected = self._collect_selected()
		if not selected:
			return

		available = self._filter_locked(selected)
		if not available:
			return

		loaded = self._load_managers(available)
		if not loaded:
			QMessageBox.information(self.main_tab, "Экспорт", "Нет разделов для экспорта.")
			return

		dialog = BoQExportSummaryDialog(loaded, parent=self.main_tab)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return

		export_list = dialog.get_export_list()
		if not export_list:
			QMessageBox.information(self.main_tab, "Экспорт", "Нет разделов для экспорта.")
			return

		form = self._ask_format()
		if form is None:
			return

		self._execute(export_list, form)


	def _collect_selected(self) -> list[File_BoQ] | None:
		table = self.main_tab.project_BoQs_table
		rows = {idx.row() for idx in table.selectedIndexes()}
		if not rows:
			QMessageBox.warning(self.main_tab, "Экспорт", "Сначала выберите ведомости в таблице.")
			return None
		return [table.files[row] for row in sorted(rows)]


	def _filter_locked(self, files: list[File_BoQ]) -> list[File_BoQ]:
		available, locked = [], []
		for file_BoQ in files:
			try:
				status, user = file_BoQ.status_lock
				if status:
					locked.append((file_BoQ.path.name, user))
				else:
					available.append(file_BoQ)
			except KeyError:
				locked.append((file_BoQ.path.name, "не определён"))

		if locked:
			msg = "Следующие ведомости заблокированы и не могут быть экспортированы:\n"
			msg += "\n".join(f"- {name} (пользователь: {user})" for name, user in locked)
			QMessageBox.warning(self.main_tab, "Экспорт", msg)

		return available


	def _load_managers(self, files: list[File_BoQ]) -> list[tuple[File_BoQ, object, dict]]:
		"""Однократная загрузка — все данные далее хранятся в памяти."""
		loaded = []
		for file_BoQ in files:
			try:
				manager = self.project.open_BoQ_for_export(file_BoQ)
			except Exception as e:
				QMessageBox.warning(
					self.main_tab, "Экспорт",
					f"{file_BoQ.path.name}: не удалось загрузить — {e}"
				)
				continue
			loaded.append((file_BoQ, manager, manager.data_validation))
		return loaded


	def _ask_format(self):
		dialog = ExportFormatDialog(self.main_tab)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return None
		return dialog.get_data()


	def _execute(self, export_list: list[tuple[File_BoQ, object]], form: tuple) -> None:
		extension, form_type, subsec = form

		progress = QProgressDialog(
			"Экспорт разделов...", "Отмена", 0, len(export_list), self.main_tab
		)
		progress.setWindowModality(Qt.WindowModality.WindowModal)
		progress.setMinimumDuration(0)
		progress.setValue(0)

		convertor = Convertor(self.project)
		success = 0
		errors: list[str] = []

		for idx, (file_BoQ, manager) in enumerate(export_list):
			if progress.wasCanceled():
				break
			progress.setLabelText(f"Экспорт: {file_BoQ.path.name}")
			progress.setValue(idx)
			QApplication.processEvents()

			try:
				if extension in ('.gge', '.xml'):
					convertor.create_xml_3p01(manager, extension, subsec)
				else:
					convertor.export_to_pdf(manager, form_type, subsec)
				success += 1
			except Exception as e:
				errors.append(f"{file_BoQ.path.name}: ошибка экспорта — {e}")

		progress.setValue(len(export_list))
		progress.close()

		self._show_result(success, len(export_list), errors, extension)


	def _show_result(self, success: int, total: int, errors: list[str], extension: str) -> None:
		msg = f"Экспорт завершён.\nУспешно: {success} из {total}"
		if errors:
			msg += "\n\nОшибки:\n" + "\n".join(errors[:10])
			if len(errors) > 10:
				msg += f"\n... и ещё {len(errors) - 10} ошибок"
			QMessageBox.warning(self.main_tab, "Экспорт", msg)
		else:
			QMessageBox.information(self.main_tab, "Экспорт", msg)

		if success:
			match extension:
				case '.gge' | '.xml':
					self.project.open_xml_folder()
				case '.pdf':
					self.project.open_pdf_folder()
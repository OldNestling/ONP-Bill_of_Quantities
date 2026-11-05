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

from pathlib import Path
from openpyxl import load_workbook

from PyQt6.QtWidgets import (
	QApplication, QWidget, QLabel, QFileDialog, QDialog, QDialogButtonBox,
	QVBoxLayout, QMessageBox, QListWidget, QAbstractItemView, QProgressDialog
	)
from PyQt6.QtCore import Qt

from Core.Convertor_BoQ import Convertor, SchemaError, ValidatorJSON



class ImportManager:
	""" Отвечает за функционал импорта файлов ВОР """
	def __init__(self, main_tab: QWidget):
		self.main_tab = main_tab
		self.project = main_tab.project
		self.success_count = 0
		self.total_items = 0
		self.convertor = Convertor(self.project)


	def _get_files(self):
		""" Открываетдиалоговое окно выбора файлов """
		# Диалог выбора файлов с расширенным фильтром
		files, _ = QFileDialog.getOpenFileNames(
			self.main_tab,
			'Выберите файлы для импорта (Excel или XML)',
			'',
			'Поддерживаемые форматы ' \
			'(*.xlsx *.xlsm *.xml *.gge *.json);;' \
			'Excel файлы (*.xlsx *.xlsm);;' \
			'XML файлы (*.xml *.gge);;' \
			'Файлы "Системы ВОР" (*.json)'
		)
		return files

 
	def _show_sheet_selection_dialog(self, file_name, sheet_names):
		"""
		Отображает диалог с множественным выбором листов.
		Возвращает список выбранных имён листов или None, если диалог отменён.
		"""
		dialog = QDialog(self.main_tab)
		dialog.setWindowTitle(f"Выбор листов для импорта: {file_name}")
		dialog.setModal(True)
		layout = QVBoxLayout(dialog)

		label = QLabel("Выберите листы для конвертации (можно несколько):")
		layout.addWidget(label)

		list_widget = QListWidget()
		list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
		for name in sheet_names:
			list_widget.addItem(name)
		layout.addWidget(list_widget)

		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
		buttons.accepted.connect(dialog.accept)
		buttons.rejected.connect(dialog.reject)
		layout.addWidget(buttons)

		if dialog.exec() != QDialog.DialogCode.Accepted:
			return None

		selected = [item.text() for item in list_widget.selectedItems()]
		return selected


	def _import_from_xml(self, file_path: Path):
		try:
			self.convertor.import_from_xml_3p01(file_path)
			self.success_count += 1
			print(f"Импорт из XML: {file_path.name} успешно завершён")
		except SchemaError as e:
			QMessageBox.warning(self.main_tab, 'Импорт XML', e.info())
		except Exception as e:
			QMessageBox.warning(self.main_tab, 'Импорт XML', f"Ошибка при импорте {file_path.name}:\n{e}")


	def _import_from_excel(self, file_path: Path):
		try:
			# Проверяем, что файл можно открыть и получить листы
			wb = load_workbook(file_path, data_only=True, read_only=True)
			sheet_names = wb.sheetnames
			wb.close()
		except Exception as e:
			QMessageBox.warning(
				self.main_tab, 'Импорт Excel', f"Не удалось открыть файл {file_path.name}:\n{e}"
			)
			return

		if not sheet_names:
			QMessageBox.warning(
				self.main_tab, 'Импорт Excel', f"Файл {file_path.name} не содержит листов."
			)
			return

		# Показываем диалог выбора листов
		selected_sheets = self._show_sheet_selection_dialog(file_path.name, sheet_names)
		if not selected_sheets:
			return  # пользователь отменил выбор

		# Запускаем импорт выбранных листов
		try:
			processed = self.convertor.import_from_excel(file_path, sheet_names=selected_sheets)
			if processed > 0:
				self.success_count += 1
				self.total_items += processed
			else:
				QMessageBox.warning(
					self.main_tab, 'Импорт Excel',
					f"В файле {file_path.name} не найдено подходящих листов (A1='Документ')."
				)
		except Exception as e:
			QMessageBox.warning(
				self.main_tab, 'Импорт Excel', f"Ошибка при импорте {file_path.name}:\n{e}"
			)


	def _import_from_JSON(self, file_path: Path):
		result = ValidatorJSON(self.project).import_file(file_path)

		match result:
			case {'success': True}:
				self.success_count += 1
			case _:
				QMessageBox.warning(
					self.main_tab, 'Импорт JSON',
					f'Ошибка импорта файла {file_path.name}:\n'	\
					f'{result.get('message', 'Неизвестная ошибка')}'
				)

 
	def run(self):
		if self.project is None:
			QMessageBox.warning(self.main_tab, "Импорт", "Проект не загружен.")
			return

		files = self._get_files()

		if not files:
			return

		progress = QProgressDialog(
			'Импорт файлов ВОР...', 'Отмена', 0, len(files), self.main_tab
		)
		progress.setWindowModality(Qt.WindowModality.WindowModal)
		progress.setMinimumDuration(0)
		progress.setValue(0)
	

		for idx, file_path_str in enumerate(files):
			if progress.wasCanceled():
				break
			file_path = Path(file_path_str)
			
			progress.setLabelText(f"Импорт: {file_path.name}")
			progress.setValue(idx)
			QApplication.processEvents()
			
			# определяем тип импорта
			# так как пользователь может выбрать несколько форматов за раз, 
			# то делаем это для каждого файла
			suffix = Path(file_path).suffix.lower()
			if suffix in ('.xml', '.gge'):				# Импорт из XML
				self._import_from_xml(file_path)
			elif suffix in ('.xlsx', '.xlsm'):			# Импорт из Excel
				self._import_from_excel(file_path)
			elif suffix == '.json':						# импорт собственного формата
				self._import_from_JSON(file_path)
			else:
				QMessageBox.warning(self.main_tab, 'Импорт', f"Неподдерживаемый формат файла: {suffix}")
				return

		progress.setValue(len(files))
		progress.close()

		# Итоговое сообщение
		if self.success_count > 0:
			if self.total_items:
				QMessageBox.information(self.main_tab, 'Импорт завершён',
					f"Импортировано файлов: {self.success_count}\n" \
					f"Всего листов/разделов: {self.total_items}")
			else:
				QMessageBox.information(self.main_tab, 'Импорт завершён',
					f"Успешно импортировано файлов: {self.success_count}")
		
		elif self.success_count == 0 and files:
			QMessageBox.warning(self.main_tab, 'Импорт', "Ни один файл не был импортирован.")

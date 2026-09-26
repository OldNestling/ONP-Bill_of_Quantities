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
	QApplication, QWidget, QLabel, QPushButton, QDialog, 
	QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLineEdit,
	QPlainTextEdit, QMessageBox, QTableWidget, QTableWidgetItem, 
	QHeaderView, QComboBox, QCompleter, QMenu, QSpinBox, QStyledItemDelegate,
	QStyleOptionViewItem, QStyle
	)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from Core.Project import File_BoQ
from Core.Utilities import text_after, text_before
from ..ui_utilities import MultilineTextDelegate

from Templates.About import (
	ABOUT, COPYRIGHT, GITHUB, PROGRAM_NAME, PROGRAM_VERSION, PARTICIPANTS
)

class Project_Info_Edit_Dialog(QDialog):
	""" Окно редактирования данных проекта """
	def __init__(self, parent, chiefs, construction_site, code, verifier_name, description):
		super().__init__(parent)
		self.setWindowTitle('Редактирование информации о проекте')
		self.setModal(True)

		edit_layout = QVBoxLayout(self)

		self._construction_site_edit_line = QPlainTextEdit(construction_site)
		self._construction_site_edit_line.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
		self._construction_site_edit_line.setMaximumHeight(100)
		self._construction_site_edit_line.setMinimumWidth(600)
		edit_layout.addWidget(QLabel('Наименование объекта:'))
		edit_layout.addWidget(self._construction_site_edit_line)

		self._code_edit_line = QLineEdit(code)
		edit_layout.addWidget(QLabel('Шифр: '))
		edit_layout.addWidget(self._code_edit_line)

		self._verifier_edit_combobox = QComboBox()
		verifiers_list = chiefs
		self._verifier_edit_combobox.addItems(verifiers_list)
		self._verifier_edit_combobox.setEditable(True)
		self._verifier_edit_combobox.setCurrentText(verifier_name)
		edit_layout.addWidget(QLabel('ГИП: '))
		edit_layout.addWidget(self._verifier_edit_combobox)
		

		self.description_edit_plain = QPlainTextEdit(description)
		self.description_edit_plain.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
		self.description_edit_plain.setMinimumWidth(600)
		edit_layout.addWidget(QLabel('Описание объекта:'))
		edit_layout.addWidget(self.description_edit_plain)

		project_info_edit_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
		ok_button = project_info_edit_buttons.button(QDialogButtonBox.StandardButton.Ok)
		ok_button.setText('Применить')
		cancel_button = project_info_edit_buttons.button(QDialogButtonBox.StandardButton.Cancel)
		cancel_button.setText('Отменить')
		project_info_edit_buttons.accepted.connect(self.accept)
		project_info_edit_buttons.rejected.connect(self.reject)

		edit_layout.addWidget(project_info_edit_buttons)

	def get_data(self):
		output = {
			'ConstructionSite': self._construction_site_edit_line.toPlainText(),
			'Code': self._code_edit_line.text(),
			'VerifierName': self._verifier_edit_combobox.currentText(),
			'Description': self.description_edit_plain.toPlainText()
		}
		return output



class ColorTextDelegate(QStyledItemDelegate):
	"""
	Красит текст ячейки в QColor, лежащий в Qt.ItemDataRole.UserRole.
    Игнорирует QSS-правила QTableWidget::item { color: ... }.
    Если в UserRole не QColor — работает как обычный делегат.
	"""
	def paint(self, painter, option, index):
		color = index.data(Qt.ItemDataRole.UserRole)
		if not isinstance(color, QColor):
			super().paint(painter, option, index)
			return
		
		opt = QStyleOptionViewItem(option)
		self.initStyleOption(opt, index)

		text = opt.text
		opt.text = ''	# Стиль не должен рисовать текст своим цветом
		
		widget = opt.widget
		style = widget.style() if widget else QApplication.style()
		style.drawControl(
			QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget
		)

		painter.save()
		painter.setPen(color)
		painter.setFont(opt.font)
		text_rect = style.subElementRect(
			QStyle.SubElement.SE_ItemViewItemText, opt, widget
		)
		painter.drawText(
			text_rect,
			opt.displayAlignment | Qt.AlignmentFlag.AlignVCenter,
			text
		)
		painter.restore()

class BoQs_TableWidget(QTableWidget):
	"""
	Таблица для отображения списка разделов.
	"""
	def __init__(self, parent=None, main_tab=None):
		super().__init__(parent)
		self.main_tab = main_tab
		self.setColumnCount(9)
		self.setHorizontalHeaderLabels([
			"Номер ВОР", "Наименование", "Статус",
			"Исполнитель", "Должность", "Последняя Дата",
			"Доступность", "№ ЛСР", "Файл"])
		self.files = []
		for i in range(self.columnCount()):
			self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
		self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(self.on_table_context_menu)
		self.color_delegate = ColorTextDelegate(self)
		self.setItemDelegateForColumn(2, self.color_delegate)
		self.setItemDelegateForColumn(6, self.color_delegate)


	def update_table(self, list_BoQs):
		self.files = list_BoQs
		self.setRowCount(len(list_BoQs))
		for row, obj in enumerate(list_BoQs):
			obj: File_BoQ
			self.setItem(row, 0, QTableWidgetItem(obj.num))
			self.setItem(row, 1, QTableWidgetItem(obj.object_name))

			if obj.status == 2:
				status = "Готово"
			elif obj.status == 1:
				status = 'Не осмечено'
			else:
				status = "Не готово"
			
			STATUS_COLORS = {
				0: QColor('#C22222'), 
				1: QColor("#0B64C9"), 
				2: QColor('#38A14f')
			}

			status_item = QTableWidgetItem(status)
			status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			status_item.setData(Qt.ItemDataRole.UserRole, STATUS_COLORS.get(obj.status))
			self.setItem(row, 2, status_item)
			self.setItem(row, 3, QTableWidgetItem(obj.composer))
			self.setItem(row, 4, QTableWidgetItem(obj.composer_position))
			self.setItem(row, 5, QTableWidgetItem(obj.date))
			
			if not obj.is_locked:
				access = 'Доступно'
				access_color = QColor("#38A14F")
			else:
				access = f'Открыт пользователем {obj.active_user}'
				access_color = QColor("#C22222")
			
			access_item = QTableWidgetItem(access)
			access_item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
			access_item.setData(Qt.ItemDataRole.UserRole, access_color)
			self.setItem(row, 6, access_item)
			self.setItem(row, 7, QTableWidgetItem(obj.local_estimate))
			self.setItem(row, 8, QTableWidgetItem(obj.path.name))

	def on_table_context_menu(self, pos):
		# Получаем позицию и индекс ячейки
		index = self.indexAt(pos)
		if not index.isValid():
			return
		row = index.row()
		# Проверяем, что есть выделенные строки
		if self.rowCount() == 0:
			return
		# Создаём меню
		menu = QMenu(self)

		# Действия, которые всегда доступны (если есть выделение)
		action_open = menu.addAction("Открыть")
		action_open.triggered.connect(self.main_tab.open_file_BoQ)

		action_edit = menu.addAction("Редактировать")
		action_edit.triggered.connect(self.main_tab.edit_selected_BoQ)

		action_delete = menu.addAction("Удалить")
		action_delete.triggered.connect(self.main_tab.delete_selected_BoQ)

		menu.addSeparator()

		action_unlock = menu.addAction("Разблокировать")
		action_unlock.triggered.connect(self.main_tab.unlock_BoQ)

		action_export = menu.addAction("Экспорт")
		action_export.triggered.connect(self.main_tab.export_selected_BoQs)

		menu.addSeparator()

		action_reload = menu.addAction("Обновить список")
		action_reload.triggered.connect(self.main_tab.reload_BoQs_table)

		# Показываем меню в позиции курсора
		menu.exec(self.viewport().mapToGlobal(pos))		

class BoQLogs_TableWidget(QTableWidget):
	"""
	Таблица для отображения реестра изменений текущего выделенного раздела.
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setColumnCount(2)
		self.setHorizontalHeaderLabels(["Дата", "Событие"])
		self.setColumnWidth(0, 100)
		self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
		self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
		self.setWordWrap(True)
		self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

	def update_table(self, log_list):
		self.setRowCount(len(log_list))
		for row, entry in enumerate(log_list):
			self.setItem(row, 0, QTableWidgetItem(entry.get('Date')))
			self.setItem(row, 1, QTableWidgetItem(entry.get('Event')))
		self.resizeRowsToContents()



class BoQ_Dialog(QDialog):
	"""Окно создания/редактирования раздела ВОР"""
	def __init__(self, parent, performers, performers_positions, list_BoQs,
				 edit_mode=False, current_data: File_BoQ | None =None, project = None):
		super().__init__(parent)
		window_name = 'Редактирование раздела ВОР' if edit_mode else 'Создание нового раздела ВОР'
		self.setWindowTitle(window_name)
		self.setModal(True)

		self._template = None
		self.list_BoQs = list_BoQs
		self.edit_mode = edit_mode
		self.project = project
		self.current_data = current_data

		edit_layout = QHBoxLayout(self)
		left_layout = QVBoxLayout()
		right_layout = QVBoxLayout()

		# Поля ввода
		__file_name_edit = current_data.path.stem if self.edit_mode else '00_Наименование работы'
		__template_BoQs = (
			'01_Подготовительные_работы',
			'02_Земляное_полотно',
			'03_Дорожная_одежда',
			'04_Примыкания_и_пересечения',
			'05_Автобусные_остановки',
			'06_Сопряжения',
			'07_Водоотвод',
			'08_Обустройство',
			'09_Площадка_для_ВЗиС',
			'10_Крайние_опоры',
			'11_Промежуточные_опоры',
			'12_Пролетные_строения',
			'13_Мостовое_полотно',
			'14_Сопряжение_моста_с_насыпью',
			'15_Регуляционные_сооружения',
			'16_Устройство_объездного_моста',
			'17_Устройство_объездной_дороги',
			'18_Разборка_объездного_моста',
			'19_Разборка_объездной_дороги',
			'20_СВСиУ_Рабочие_площадки_Рабочий_мост',
		)
		self._file_name_combobox = QComboBox()
		self._file_name_combobox.addItems(__template_BoQs)
		self._file_name_combobox.setEditable(True)
		self._file_name_combobox.setCurrentText(__file_name_edit)
		self._file_name_combobox.currentTextChanged.connect(self.update_object_name)
		left_layout.addWidget(QLabel('Наименование файла раздела:'))
		left_layout.addWidget(self._file_name_combobox)

		__current_object_name = current_data.object_name if self.edit_mode else ''
		self._object_name_plain = QPlainTextEdit(__current_object_name)
		self._object_name_plain.setPlaceholderText('Наименование раздела работы')
		self._object_name_plain.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
		self._object_name_plain.setMaximumHeight(45)

		left_layout.addWidget(QLabel('Наименование раздела:'))
		left_layout.addWidget(self._object_name_plain)

		__current_num = current_data.num if self.edit_mode else ''
		self._num_edit_line = QLineEdit(__current_num)
		self._num_edit_line.setPlaceholderText('ВО-0')
		left_layout.addWidget(QLabel('Номер ведомости:'))
		left_layout.addWidget(self._num_edit_line)

		# Комбобоксы с автодополнением
		performers_list = performers
		performers.sort()
		self._composer_combo_box = QComboBox()
		self._composer_combo_box.addItems(performers_list)
		self._composer_combo_box.setEditable(True)
		completer = QCompleter(performers_list)
		self._composer_combo_box.setCompleter(completer)
		left_layout.addWidget(QLabel('Составил:'))
		left_layout.addWidget(self._composer_combo_box)

		positions_list = performers_positions
		self._composer_positions_combo_box = QComboBox()
		self._composer_positions_combo_box.addItems(positions_list)
		self._composer_positions_combo_box.setEditable(True)
		completer_positions = QCompleter(positions_list)
		self._composer_positions_combo_box.setCompleter(completer_positions)
		if self.edit_mode:
			self._composer_combo_box.setCurrentText(current_data.composer)
			self._composer_positions_combo_box.setCurrentText(current_data.composer_position)
		else:
			self._composer_positions_combo_box.setCurrentText('Ведущий инженер')
		left_layout.addWidget(QLabel('Должность:'))
		left_layout.addWidget(self._composer_positions_combo_box)

		# Дополнительные поля режима редактирования
		if self.edit_mode:
			__current_date = current_data.date
			self._date_edit_line = QLineEdit(__current_date)
			left_layout.addWidget(QLabel('Последняя дата документа:'))
			left_layout.addWidget(self._date_edit_line)

			__current_local_estimate = current_data.local_estimate
			self._local_estimate_edit_line = QLineEdit(__current_local_estimate)
			left_layout.addWidget(QLabel('№ ЛСР:'))
			left_layout.addWidget(self._local_estimate_edit_line)

			# Таблица журнала изменений
			right_layout.addWidget(QLabel('Журнал изменений:'))

			self.logs_table = QTableWidget()
			self.logs_table.setColumnCount(2)
			self.logs_table.setHorizontalHeaderLabels(['Дата', 'Событие'])
			self.logs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
			self.logs_table.setWordWrap(True)
			self.logs_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
			self.logs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
			self.logs_table.setItemDelegateForColumn(1, MultilineTextDelegate())

			log_list = current_data.log_list
			self.logs_table.setRowCount(len(log_list))
			for row, entry in enumerate(log_list):
				self.logs_table.setItem(row, 0, QTableWidgetItem(entry.get('Date', '')))
				self.logs_table.setItem(row, 1, QTableWidgetItem(entry.get('Event', '')))
			self.logs_table.resizeRowsToContents()

			right_layout.addWidget(self.logs_table)

			# Кнопки управления журналом
			logs_buttons_layout = QHBoxLayout()
			self.btn_add_log = QPushButton('Добавить запись')
			self.btn_add_log.clicked.connect(self.add_log_row)
			self.btn_remove_log = QPushButton('Удалить запись')
			self.btn_remove_log.clicked.connect(self.remove_log_row)
			logs_buttons_layout.addWidget(self.btn_add_log)
			logs_buttons_layout.addWidget(self.btn_remove_log)
			right_layout.addLayout(logs_buttons_layout)

		# Кнопки
		new_BoQ_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
		ok_button = new_BoQ_buttons.button(QDialogButtonBox.StandardButton.Ok)
		ok_button_name = 'Применить' if self.edit_mode else 'Создать'
		ok_button.setText(ok_button_name)
		cancel_button = new_BoQ_buttons.button(QDialogButtonBox.StandardButton.Cancel)
		cancel_button.setText('Отменить')
		new_BoQ_buttons.accepted.connect(self.accept)
		new_BoQ_buttons.rejected.connect(self.reject)

		left_layout.addWidget(new_BoQ_buttons)

		# Контейнеры для ограничения ширины
		left_container = QWidget()
		left_container.setLayout(left_layout)
		if edit_mode:
			left_container.setMaximumWidth(300)

		right_container = QWidget()
		right_container.setLayout(right_layout)
		right_container.setMinimumWidth(500)

		edit_layout.addWidget(left_container)
		if edit_mode:
			edit_layout.addWidget(right_container)
			edit_layout.setStretchFactor(left_container, 1)
			edit_layout.setStretchFactor(right_container, 2)

	# ------------------------- Методы обновления наименовния -------------------------

	def update_object_name(self):
		""" Обновляет имя раздела при выборе имени файла, если оно пустое """
		non_list = {'',' ','-', None, 'None','...', '.'}
		if self._object_name_plain.toPlainText().strip() in non_list and not self.edit_mode:
			filename = text_after(self._file_name_combobox.currentText(),'_').replace('_',' ')
			self._object_name_plain.setPlainText(filename)
		
		if self._num_edit_line.text() in non_list and not self.edit_mode:
			num = text_before(self._file_name_combobox.currentText(),'_')
			num = num[1:] if num.startswith('0') else num
			self._num_edit_line.setText(f'ВО-{num}')
		
	

	# ------------------------ Методы для управления журналом -------------------------
	def add_log_row(self):
		row = self.logs_table.rowCount()
		self.logs_table.insertRow(row)
		self.logs_table.setItem(row, 0, QTableWidgetItem(self.project.now.strftime("%d.%m.%Y")))
		self.logs_table.setItem(row, 1, QTableWidgetItem(''))

	def remove_log_row(self):
		current_row = self.logs_table.currentRow()
		if current_row >= 0:
			self.logs_table.removeRow(current_row)

	# ---------------------------- Методы основных действий ---------------------------
	def accept(self):
		filename = self._file_name_combobox.currentText().strip()
		filenames = [f.path.stem for f in self.list_BoQs]
		if not filename:
			QMessageBox.warning(self, "Ошибка", "Имя файла не может быть пустым.")
			return
		if filename in filenames and not self.edit_mode:
			QMessageBox.information(self, "Внимание!", "Файл с таким именем уже существует.")
			return
		super().accept()


	def get_data(self):
		date = self._date_edit_line.text() if self.edit_mode else self.project.now.strftime("%d.%m.%Y")
		local_estimate = self._local_estimate_edit_line.text() if self.edit_mode else 'Укажите номер ЛСР'
		log_list = []

		if self.edit_mode:
			for row in range(self.logs_table.rowCount()):
				date_item = self.logs_table.item(row, 0)
				event_item = self.logs_table.item(row, 1)
				log_list.append({
					'Date': date_item.text() if date_item else '',
					'Event': event_item.text() if event_item else ''
				})

		output = {
			'FileName': self._file_name_combobox.currentText().strip(),
			'metadata': {
				'ObjectName': self._object_name_plain.toPlainText(),
				'Num': self._num_edit_line.text(),
				'Date': date,
				'Signatures': {
					'Composer': self._composer_combo_box.currentText(),
					'Composer_Position': self._composer_positions_combo_box.currentText()
				},
				'Status_Done': self.current_data.status if self.edit_mode else False,
				'local_estimate': local_estimate,
				'log_list': log_list,
				'note': self.current_data.note if self.edit_mode else ''
			}
		}
		return output if not self._template else self._template

class Export_Dialog(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Экспорт ведомости")
		self.setModal(True)

		layout = QVBoxLayout(self)

		layout.addWidget(QLabel("Выберите формат экспорта:"))

		self.format_combobox = QComboBox()
		self.format_combobox.addItems(["XML", "GGE", "PDF по форме 1", "PDF по форме 2"])
		layout.addWidget(self.format_combobox)

		self.subsection_num = QSpinBox()
		self.subsection_num.setMinimum(0)
		self.subsection_num.setMaximumWidth(40)
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

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QLabel, QFrame, QTextBrowser
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap

from Templates.About import (
    ABOUT, COPYRIGHT, GITHUB, PROGRAM_NAME, PROGRAM_VERSION, PARTICIPANTS
)
from ..ui_utilities import create_separator
from ..resources.icons import Icons


class HelpDialog(QDialog):
    """Диалог справки: информация о программе, контакты, реквизиты."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Справка")
        self.setModal(True)
        self.setWindowIcon(Icons.recolor_icon(Icons.help, QColor("#000000")))
        self._setup_ui()


    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._build_about_group())
        main_layout.addWidget(self._build_info_group())
        main_layout.addStretch()

        # Центрируем диалог относительно главного окна
        self.setMinimumWidth(500)
        self.setMinimumHeight(550)
        self.adjustSize()

    # ------------------------------------------------------------------ #
    #                        Группа "О программе"                        #
    # ------------------------------------------------------------------ #
    def _build_about_group(self) -> QGroupBox:
        group = QGroupBox("О программе")
        layout = QVBoxLayout()

        title_label = QLabel(f"<h2>{PROGRAM_NAME}</h2>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        version_label = QLabel(f"<b>Версия:</b> {PROGRAM_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        copyright_label = QLabel(f"<i>{COPYRIGHT} (GPLv3)</i>")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)

        layout.addWidget(create_separator(QFrame.Shape.HLine))

        about_text = QTextBrowser()
        about_text.setOpenExternalLinks(True)
        about_text.setHtml(f"<p>{ABOUT.replace(chr(10), '<br>')}</p>")
        about_text.setMaximumHeight(120)
        about_text.setMinimumHeight(60)
        layout.addWidget(about_text)
        layout.addStretch()

        group.setLayout(layout)
        return group

    # ------------------------------------------------------------------ #
    #                    Группа "Справка и контакты"                     #
    # ------------------------------------------------------------------ #
    def _build_info_group(self) -> QGroupBox:
        group = QGroupBox("Справка и контакты")
        layout = QVBoxLayout()

        layout.addWidget(self._build_tutorial_label())
        layout.addWidget(self._build_contact_label())

        participants = QLabel(PARTICIPANTS)
        participants.setWordWrap(True)
        layout.addWidget(participants)

        layout.addWidget(create_separator(QFrame.Shape.HLine))

        thanks_label = QLabel(
            "<i>Программа создана за спасибо.<br>"
            "Более весомая благодарность стимулирет разработчика "
            "поддержать продукт :)</i>"
        )
        thanks_label.setWordWrap(True)
        thanks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thanks_label)

        layout.addWidget(self._build_qr_label())

        group.setLayout(layout)
        return group

    def _build_tutorial_label(self) -> QLabel:
        label = QLabel()
        label.setOpenExternalLinks(True)
        label.setText(
            f'<b>Справочная информация: </b>'
            f'<a href="{GITHUB}" style="color: #3B82F6; '
            f'text-decoration: none;">{GITHUB}</a>'
        )
        label.setWordWrap(True)
        return label

    def _build_contact_label(self) -> QLabel:
        label = QLabel(
            f'<b>Связь с разработчиком: </b>'
            f'<a href="mailto:oldnestling@yandex.ru" style="color: #3B82F6; '
            f'text-decoration: none;">oldnestling@yandex.ru</a>'
            f'<br><b>Счёт для благодарности: </b>'
            f'<a href="https://www.tinkoff.ru/rm/r_aOqwUwfbRm.lZNlrKjSLm/oMI8k46003" '
            f'style="color: #3B82F6; text-decoration: none;">'
            f'4081 7810 6000 9641 9718</a>'
        )
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        return label

    def _build_qr_label(self) -> QLabel:
        qr_path = Path(Icons.resource_path("UI/icons/donate_qr.jpg"))
        pixmap = QPixmap(str(qr_path))
        pixmap = pixmap.scaled(
            200, 200,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    # ------------------------------------------------------------------ #
    #                       Конструктор 		                         #
    # ------------------------------------------------------------------ #
    @classmethod
    def show_help(cls, parent=None):
        """Создаёт и показывает диалог. Возвращает результат `exec()`."""
        dialog = cls(parent)
        return dialog.exec()
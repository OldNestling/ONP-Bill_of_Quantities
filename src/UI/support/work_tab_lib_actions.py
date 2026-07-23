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
	QWidget, QLabel, QDialog, QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QListWidget, 
	QAbstractItemView, QLineEdit, QComboBox, QSpinBox, QStackedWidget, QCheckBox
	)
from PyQt6.QtCore import QLocale
from Core.Utilities import convert_value
from Core.BoQ import BoQ_manager
from Core.Machinery import Machine
from Core.Soils import Soil, Gesn5
from Core.UserLibs import Library, Group, MainElement
from ..ui_utilities import create_ok_cancel_buttons, create_separator

class Earth_Work_Dialog(QDialog):
	""" Окно создания позиции земляной работы """
	def __init__(self, parent, manager):
		super().__init__(parent)
		self.setWindowTitle('Создание земляной работы')
		self.setModal(True)

		self.manager: BoQ_manager = manager

		layout = QVBoxLayout(self)
		
		self.mode_selector = QComboBox()
		self.mode_selector.setStyleSheet(""" 
			QComboBox  {
	 		background-color: #45464F;
	 		color: white;
	 		border-radius: 4px;
	 		padding: 6px;
			}
			QComboBox QListView {
				background-color: #45464F;
				border-radius: 10px;
			}
			QComboBox QListView::item {
				background-color: #51525C;
				color: white;
				border-radius: 4px;
			}
		""")
		self.mode_selector.addItem('Разработка грунта, м³', 'excavation')
		self.mode_selector.addItem('Устройство буронабивных свай, м³', 'drilling_piles')
		self.mode_selector.currentIndexChanged.connect(self.on_mode_changed)
		layout.addWidget(self.mode_selector)

		self.earth_work_modes = QStackedWidget()
		layout.addWidget(self.earth_work_modes)

		self.excavation_dialog = Excavation_SubDialog(self, self.manager)
		self.earth_work_modes.addWidget(self.excavation_dialog)

		self.drilling_dialog = Drilling_Piles_SubDialog(self, self.manager)
		self.earth_work_modes.addWidget(self.drilling_dialog)


		# --------- Кнопки ---------
		btns = create_ok_cancel_buttons(self, False)
		layout.addWidget(btns)

	def on_mode_changed(self, index):
		self.earth_work_modes.setCurrentIndex(index)
	
	
	def get_data(self):
		widget = self.earth_work_modes.currentWidget()
		return widget.get_data()


	
class Excavation_SubDialog(QWidget):
	def __init__(self, parent, manager: BoQ_manager):
		super().__init__(parent)
		self.manager = manager
		# запуск диалого может быть только при менеджере с проектом, поэтому без проверок
		self.project = self.manager.project
		self.soils_data = self.project.get_soils_gesn1_data()	# Список кортежей
		self.sources_data = self.project.get_sources_data()		# Список кортежей
		self.machines_data = self.project.get_machines_data()	# Словарь с списками
		self.setup_excavation_ui()
		
	
	def setup_excavation_ui(self):
		""" Создаёт интерфейс для создания позиции разработки грунта """
		layout = QVBoxLayout(self)

		# -------- Уровень 1 --------
		level_1 = QHBoxLayout()
		self.soil_num_selector = QComboBox()
		for (key, works) in self.soils_data:
			self.soil_num_selector.addItem(key, works)
		self.soil_num_selector.setCurrentIndex(0)
		self.soil_num_selector.currentTextChanged.connect(self.update_works)

		self.count_edit_lite = QLineEdit()
		self.count_edit_lite.setPlaceholderText('Количество грунта, м³')

		level_1.addWidget(QLabel('Номер ИГЭ:'))
		level_1.addWidget(self.soil_num_selector)
		level_1.addWidget(QLabel('Формула:'))
		level_1.addWidget(self.count_edit_lite)
		layout.addLayout(level_1)

		# -------- Уровень 2 --------
		self.type_excavation = QComboBox()
		works_list = self.soil_num_selector.currentData()
		for (name, alias, i) in works_list:
			self.type_excavation.addItem(name, (alias, i))
		self.type_excavation.setCurrentIndex(0)
		self.type_excavation.currentTextChanged.connect(self.fill_mechanization)

		layout.addWidget(QLabel('Способ разработки грунта:'))
		layout.addWidget(self.type_excavation)

		# -------- Уровень 3 --------
		self.mechanization = QComboBox()
		self.fill_mechanization()

		layout.addWidget(QLabel('Механизация по проекту:'))
		layout.addWidget(self.mechanization)


		# -------- Уровень 4 --------
		level_4 = QHBoxLayout()
		self.transportation_checkbox = QCheckBox()
		self.transportation_checkbox.setChecked(True)	# По умолчанию True
		self.transportation_checkbox.toggled.connect(self.on_toogled_transportation)

		self.tranport_selector = QComboBox()

		source_name = 'Площадка складирования грунта'
		source_key = 'ПлощСклГрунт'
		source_index = 0

		if self.sources_data:
			for i, (name, alias) in enumerate(self.sources_data):
				self.tranport_selector.addItem(name, alias)
				if name == source_name or alias == source_key:
					source_index = i
		else:
			name = 'Транспортировка автосамосвалами грузоподъёмностью до 15 т'
			alias = 'Транспортировка автосамосвалами грузоподъёмностью до 15 т'
			self.tranport_selector.addItem(name, alias)

		self.tranport_selector.setCurrentIndex(source_index)

		layout.addWidget(create_separator())

		layout.addWidget(QLabel('<b>Подпозиция транспортировки</b>'))

		level_4.addWidget(QLabel('С перевозкой:'))
		level_4.addWidget(self.transportation_checkbox)
		level_4.addWidget(self.tranport_selector)
		layout.addLayout(level_4)

		# -------- Уровень 5 --------
		level_5 = QHBoxLayout()

		self.embankment_checkbox = QCheckBox()
		self.embankment_checkbox.setChecked(False)	# По умолчанию False
		self.embankment_checkbox.toggled.connect(self.on_toogled_embankment)

		self.distance_edit = QSpinBox()
		self.distance_edit.setMinimum(0)
		self.distance_edit.setValue(0)
		self.distance_edit.setMaximumWidth(70)
		self.distance_edit.setEnabled(False)	# Включен если в насыпь

		level_5.addWidget(QLabel('В насыпь:'))
		level_5.addWidget(self.embankment_checkbox)
		level_5.addStretch()
		level_5.addWidget(QLabel('Расстояние:'))
		level_5.addWidget(self.distance_edit)
		layout.addLayout(level_5)

		layout.addStretch()
		

	# ====================================== Методы =====================================	
	
	def update_works(self):
		""" Обнавляет доступный список выбора видов разработки текущего грунта """
		works_data = self.soil_num_selector.currentData()
		self.type_excavation.clear()
		for (name, alias, i) in works_data:
			self.type_excavation.addItem(name, (alias, i))
		self.type_excavation.setCurrentIndex(0)

	def fill_mechanization(self):
		""" Заполняет допустимыми средствами механизации список выбора """
		def __set_data(key, blank):
			machines: list = self.machines_data.get(key) if isinstance(self.machines_data, dict) else None
			if not machines:
				text = blank
				self.mechanization.addItem('Нет данных', text) # Нет ссылок, будет просто текст
			else:
				for m in machines:
					m: Machine
					self.mechanization.addItem(m.name, f'@{m.alias_work}')
		self.mechanization.clear()
		data = self.type_excavation.currentData()
		if data:
			_, type_exc = data
		else:
			type_exc = None

		self.mechanization.setEnabled(True)
			
		if type_exc in range(3):
			__set_data('Экскаватор','экскаватором с емкостью ковша 1 м³')
		elif type_exc == 3:
			__set_data('Скрепер','скрепером самоходным, геометрическая емкость ковша 8.0 м³')
		elif type_exc == 4:
			__set_data('Бульдозер','бульдозером мощностью 130 л.с. с перемещением грунта до 50 м')
		elif type_exc == 5:
			__set_data('Грейдер','автогрейдером среднего типа, мощность 99 кВт (135 л.с.)')
		elif type_exc == 6:
			__set_data('Грейдер-элеватор','[характеристика грейдера-элеватора]')
		elif type_exc == 7:
			__set_data(
				'Бурильнокрановая машина', 
				'бурильно-крановой машиной на автомобильном ходу, диаметр бурения до 800 мм, глубина бурения до 5 м'
			)
		elif type_exc == 8:		# Разработка грунтов вручную
			__set_data('Инструмент','вручную')
		elif type_exc == 9:		# Разрыхление мерзлых грунтов
			__set_data('Экскаватор','клин-молотом, подвешенным на стреле экскаватора с емкостью ковша 1 м³')
		elif type_exc == 10:	# Нарезка прорезей в мерзлых грунтах баровыми машинами
			__set_data('Баровая машина','установкой двухбаровой на тракторе, мощность 79 кВт (108 л.с.)')
		elif type_exc in (11, 12):	# Рыхление грунта бульдозерами рыхлителями
			__set_data('Бульдозер-рыхлитель','бульдозером-рыхлителем на тракторе, мощность 243 кВт (330 л.с.)')

		self.mechanization.setCurrentIndex(0)
	
	def on_toogled_transportation(self, checked):
		""" Обрабатывает событие переключения режима транспортировки """
		if checked:
			self.embankment_checkbox.setEnabled(True)
			self.tranport_selector.setEnabled(True)

		else:
			self.embankment_checkbox.setEnabled(False)
			self.tranport_selector.setEnabled(False)	

	def on_toogled_embankment(self, checked):
		""" Обрабатывает событие переключения режима транспортировки в насыпь """
		if checked:
			self.distance_edit.setEnabled(True)
		else:
			self.distance_edit.setEnabled(False)

	def get_data(self) -> dict:
		""" Возвращает данные для BoQ_manager.add_excavation """
		data = {
			'mode': 'excavation',
			'soil_key': self.soil_num_selector.currentText(),
			'quantity': self.count_edit_lite.text(),
			'laboriousness': self.type_excavation.currentData()[0],
			'method': self.mechanization.currentData(),
			'transportation': self.transportation_checkbox.isChecked(),
			'source': self.tranport_selector.currentData(),
			'into_embankment': self.embankment_checkbox.isChecked(),
			'distance': self.distance_edit.value()
		}
		return data

class Drilling_Piles_SubDialog(QWidget):
	def __init__(self, parent, manager: BoQ_manager):
		super().__init__(parent)
		self.manager = manager
		self.project = self.manager.project
		self.soils_data = self.project.get_soils_gesn5_data()	# Список объектов
		self.machines_data: dict = self.project.get_machines_data()	# Словарь с списками
		self.setup_drilloing_ui()

	def setup_drilloing_ui(self):
		""" Создаёт интерфейс для создания позиций устройства буронабивных свай """
		layout = QVBoxLayout(self)

		# -------- Уровень 1 --------
		level_1 = QHBoxLayout()
		self.diameter_spinebox = QDoubleSpinBox()
		self.diameter_spinebox.setMinimum(0.00)
		self.diameter_spinebox.setDecimals(2)
		self.diameter_spinebox.setSingleStep(0.1)
		self.diameter_spinebox.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))

		self.length_spinebox = QDoubleSpinBox()
		self.length_spinebox.setMinimum(0.00)
		self.length_spinebox.setDecimals(2)
		self.length_spinebox.setMaximum(1000)
		self.length_spinebox.setSingleStep(1.0)
		self.length_spinebox.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))

		level_1.addWidget(QLabel('Диаметр:'))
		level_1.addStretch()
		level_1.addWidget(self.diameter_spinebox)
		level_1.addWidget(QLabel('Общая длина:'))
		level_1.addStretch()
		level_1.addWidget(self.length_spinebox)
		layout.addLayout(level_1)

		# -------- Уровень 2 --------
		self.concrete_properties = QLineEdit()
		self.concrete_properties.setText('Бетон B25 W6')

		layout.addWidget(QLabel('Характеристика бетона:'))
		layout.addWidget(self.concrete_properties)

		# -------- Уровень 3 --------
		self.drilling_method = QComboBox()
		self.drilling_method.addItem('Вращательное бурение')
		self.drilling_method.addItem('Ударно-канатное бурение')

		layout.addWidget(QLabel('Способ бурения:'))
		layout.addWidget(self.drilling_method)

		# -------- Уровень 4 --------
		self.machines_combobox = QComboBox()
		self.fill_machines()
		self.machines_combobox.currentIndexChanged.connect(self.set_diameter)

		layout.addWidget(QLabel('Механизация:'))
		layout.addWidget(self.machines_combobox)

		# -------- Уровень 5 --------
		self.soils_combobox = QComboBox()
		self.fill_soils()
		self.soils_combobox.currentIndexChanged.connect(self.fill_simmilar_soils)

		layout.addWidget(QLabel('Номер ИГЭ:'))
		layout.addWidget(self.soils_combobox)

		# -------- Уровень 6 --------
		self.other_soils = QListWidget()
		self.other_soils.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
		self.fill_simmilar_soils()

		layout.addWidget(QLabel('Дополнительные грунты'))
		layout.addWidget(self.other_soils)


	def fill_soils(self):
		self.soils_combobox.clear()
		if not self.soils_data:
			self.soils_combobox.addItem('Нет данных', None)
		else:
			for soil in self.soils_data:
				self.soils_combobox.addItem(soil.local_num, soil)
	
	def fill_simmilar_soils(self):
		self.other_soils.clear()	
		if not self.soils_data:
			return
		current_soil: Soil = self.soils_combobox.currentData()
		gesn_5_obj: Gesn5 = current_soil.gesn_5_obj
		if self.drilling_method.currentIndex() == 0:
			current_group = gesn_5_obj.soil_group_1
		else:
			current_group = gesn_5_obj.soil_group_2
		for soil in self.soils_data:
			soil: Soil
			soil_gesn_5_obj: Gesn5 = soil.gesn_5_obj
			if self.drilling_method.currentIndex() == 0:
				group = soil_gesn_5_obj.soil_group_1
			else:
				group = soil_gesn_5_obj.soil_group_2
			if group == current_group and soil.local_num != current_soil.local_num:
				self.other_soils.addItem(soil.local_num)
		
	def fill_machines(self):
		# Очищаем комбобокс перед заполнением
		self.machines_combobox.clear()

		# Проверяем наличие данных о машинах
		if not self.machines_data:
			text = ('Устройство буронабивных свай диаметром 1.5 м буровыми установками '
					'с крутящим моментом 250-350 кНм под защитой обсадными трубами '
					'(с извлечением труб)')
			self.machines_combobox.addItem('Нет данных', text)
			self.diameter_spinebox.setValue(1.5)
			return

		# Ищем категорию 'Буровая установка'
		drilling_machines = self.machines_data.get('Буровая установка')
		if not drilling_machines:
			text = ('Устройство буронабивных свай диаметром 1.5 м буровыми установками '
					'с крутящим моментом 250-350 кНм под защитой обсадными трубами '
					'(с извлечением труб)')
			self.machines_combobox.addItem('Нет данных', text)
			self.diameter_spinebox.setValue(1.5)
			return

		# Перебираем кортежи (name, alias_work) внутри списка
		for m in drilling_machines:
			m: Machine
			self.machines_combobox.addItem(m.name, m)

		# Устанавливаем диаметр по первой машине (или пересмотрите логику set_diameter)
		self.set_diameter()

	def set_diameter(self):
		try:
			machine: Machine = self.machines_combobox.currentData()
			lst = machine.work.split()
			index = lst.index('диаметром')
			val = convert_value(lst[index+1])
			if isinstance(val, (int, float)):
				self.diameter_spinebox.setValue(val)
		except ValueError:
			self.diameter_spinebox.setValue(0)
	
	def get_data(self):
		selected_soils = self.other_soils.selectedItems()
		other_soils = [soil.text() for soil in selected_soils]
		machine: Machine = self.machines_combobox.currentData()
		check_machine_data = self.machines_combobox.currentText() != 'Нет данных'
		data = {
			'mode': 'drilling_piles',
			'lenght': self.length_spinebox.value(),
			'diametr': self.diameter_spinebox.value(),
			'drilling_method': self.drilling_method.currentIndex(),
			'text_mechanization': f'@{machine.alias_work}' if check_machine_data else machine,
			'soil': self.soils_combobox.currentData(),
			'other_soils': other_soils,
			'concrete': self.concrete_properties.text()
		}
		return data

class User_Libs_Dialog(QDialog):
	""" Открывает диалог выбора пользовательской библиотеки и её элементов для создания позиций"""
	def __init__(self, parent, manager: BoQ_manager):
		super().__init__(parent)
		self.setWindowTitle('Добавление элементов пользовательской библиотеки')
		self.setModal(True)

		self.manager: BoQ_manager = manager
		self.libs: list[Library] = self.manager.project.get_user_libs_data()

		layout = QVBoxLayout(self)

		# -------- Уровень 1 --------
		self.lib_selector = QComboBox()
		self.lib_selector.currentTextChanged.connect(self.fill_group_selector)
		layout.addWidget(self.lib_selector)

		# -------- Уровень 2 --------
		self.group_selector = QComboBox()
		self.group_selector.currentTextChanged.connect(self.fill_main_elements_selector)
		layout.addWidget(self.group_selector)

		# -------- Уровень 3 --------
		level3 = QHBoxLayout()
		self.main_element_checkbox = QCheckBox()
		self.main_element_checkbox.setChecked(False)
		self.main_element_checkbox.toggled.connect(self.on_togle_only_main)

		self.main_element_selector = QComboBox()
		self.main_element_selector.currentTextChanged.connect(self.fill_sub_elements_selector)
		self.main_element_selector.setEnabled(False)

		level3.addWidget(QLabel('Добавить только основную позицию'))
		level3.addWidget(self.main_element_checkbox)
		level3.addWidget(self.main_element_selector)
		layout.addLayout(level3)

		# -------- Уровень 4 --------
		level4 = QHBoxLayout()

		self.sub_elements_checkbox = QCheckBox()
		self.sub_elements_checkbox.setChecked(False)
		self.sub_elements_checkbox.setEnabled(False)
		self.sub_elements_checkbox.toggled.connect(self.on_togle_only_sub)

		self.sub_elements_selector = QComboBox()
		self.sub_elements_selector.setEnabled(False)

		level4.addWidget(QLabel('Добавить только дополнительную позицию'))
		level4.addWidget(self.sub_elements_checkbox)
		level4.addWidget(self.sub_elements_selector)
		layout.addLayout(level4)

		btns = create_ok_cancel_buttons(self, False)
		layout.addWidget(btns)		

		self.fill_libs_selector()

	def fill_libs_selector(self):
		self.lib_selector.clear()
		for lib in self.libs:
			self.lib_selector.addItem(lib.name, lib)
		self.fill_main_elements_selector()
	
	def fill_group_selector(self):
		lib: Library = self.lib_selector.currentData()
		if not lib:
			return
		self.group_selector.clear()
		for group in lib.groups:
			self.group_selector.addItem(group.name, group)
		self.fill_main_elements_selector()

	def fill_main_elements_selector(self):
		group: Group = self.group_selector.currentData()
		if not group:
			return
		self.main_element_selector.clear()
		for main_el  in group.main_elements:
			self.main_element_selector.addItem(main_el.name, main_el)
		self.fill_sub_elements_selector()

	def fill_sub_elements_selector(self):
		main_element: MainElement = self.main_element_selector.currentData()
		if not main_element:
			return
		self.sub_elements_selector.clear()
		for sub_el in main_element.sub_elements:
			self.sub_elements_selector.addItem(sub_el.name, sub_el)

	def on_togle_only_main(self):
		if self.main_element_checkbox.isChecked():
			self.main_element_selector.setEnabled(True)
			self.sub_elements_checkbox.setEnabled(True)
		else:
			self.main_element_selector.setEnabled(False)
			self.sub_elements_checkbox.setChecked(False)
			self.sub_elements_checkbox.setEnabled(False)
	
	def on_togle_only_sub(self):
		if self.sub_elements_checkbox.isChecked():
			self.sub_elements_selector.setEnabled(True)
		else:
			self.sub_elements_selector.setEnabled(False)
		
	def get_data(self):
		group = self.group_selector.currentData()
		main_element = self.main_element_selector.currentData()
		sub_element = self.sub_elements_selector.currentData()

		data = {
			'group': group,
			'main_element': main_element if self.main_element_checkbox.isChecked() else None,
			'sub_element': sub_element if self.sub_elements_checkbox.isChecked() else None
		}

		return data
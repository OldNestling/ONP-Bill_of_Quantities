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

import json, shutil, os, time
from pathlib import Path
from datetime import datetime
from .Utilities import text_after, requesting_value, get_user_log, open_folder
from .Soils import Soils_Manager
from .Sources import Sources_Manager
from .Machinery import Machinery_Manager
from .Documentation import DOCs_Manager
from .BoQ import BoQ_manager
from .UserLibs import LibManager

from Templates.About import PROGRAM_SETTINGS_FOLDER, RECENT_DIRS_LOG



class Project:
	'''
	Управляющий данными по проекту класс. Для создания единственного объекта
	
	:base_dir: директория папки src с модулями проекта. По умолчанию определяется автоматически.
	:sourсes_folder: наименование папки сохранения настроек проекта. По умолчанию "Data"
	:settings_file_name: Корневой файл с настройками проекта. По умолчанию "Core.json"
	'''

	@staticmethod
	def get_app_data_dir(app_name=PROGRAM_SETTINGS_FOLDER) -> Path:
		"""Возвращает путь к папке для сохранения данных приложения"""
		base = os.environ.get('APPDATA')
		if base is None:
			base = Path.home() / '.config'
		else:
			base = Path(base)
		app_dir = base / app_name
		app_dir.mkdir(parents=True, exist_ok=True)
		return app_dir

	@staticmethod
	def load_recent_dirs() -> list:
		"""Загружает список последних использованных директорий"""
		app_dir = Project.get_app_data_dir()
		filename = app_dir / RECENT_DIRS_LOG
		try:
			with open(filename, "r", encoding="utf-8") as f:
				data = json.load(f)
				if isinstance(data, list):
					# Отсев не существующих путей
					data = [path for path in data if Path(path).exists()]
					return data
		except FileNotFoundError:
			pass
		return []

	@staticmethod
	def save_recent_dir(dir_path: str | Path) -> None:
		"""Добавляет директорию в историю (не более 10 записей)"""
		dirs = Project.load_recent_dirs()
		dir_str = str(dir_path)
		# Если уже есть, удаляем старую запись, чтобы переместить в конец
		if dir_str in dirs:
			dirs.remove(dir_str)
		dirs.append(dir_str)
		# Оставляем только последние 10
		while len(dirs) > 10:
			dirs.pop(0)
		app_dir = Project.get_app_data_dir()
		filename = app_dir / RECENT_DIRS_LOG
		with open(filename, "w", encoding="utf-8") as f:
			json.dump(dirs, f, indent=4, ensure_ascii=False)
	
	@staticmethod
	def remove_recent_dir(dir_path: str) -> None:
		""" Удаляет не существующий путь из истории """
		dirs = Project.load_recent_dirs()
		try:
			dirs.remove(dir_path)
			print(f'[DEBUG] {dir_path=} removed')
			app_dir = Project.get_app_data_dir()
			filename = app_dir / RECENT_DIRS_LOG
			with open(filename, "w", encoding="utf-8") as f:
				json.dump(dirs, f, indent=4, ensure_ascii=False)
			
		except ValueError:
			return

	# ================================== Инициализация ==================================

	def __init__(
			self, 
			base_dir = None, 
			sourсes_folder = r'Data', 
			settings_file_name = 'Project.json', 
			project_BoQs_folder = 'ВОР'
	):
		
		# ------------------------------- пути к файлам ---------------------------------

		self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent # Определение директории проекта
		self.sourсes_folder = sourсes_folder # Дирректория базы данных
		self.settings_file_name = settings_file_name # Файл с основными настройками проекта
		self.settings_file_path: Path = self.base_dir / sourсes_folder / settings_file_name # полный путь к файлу настроек
		self.project_BoQs_folder = project_BoQs_folder # Наименование рабочей папки с файлам ВОР
		self.project_BoQs_path: Path = self.base_dir / project_BoQs_folder # путь к рабочей папки с фалами ВОР

		# ------------------------------ атрибуты проекта -------------------------------

		self.construction_site: str = ''				# Наименование объекта
		self.verifier: dict = {							# Заверитель
			'Name': None,								# Имя
			'Position': None							# Позиция
		}
		self.code: str = ''								# Шифр
		self.description: str = ''						# Дополнительное описание

		# Базовые параметры проекта
		self.project_data: dict = None 					# Словарь настройки проекта	TODO вынести в отдельный атрибут
		self.units: dict = None 						# Словарь с еденицами измерения и их параметрами
		self.work_modes: dict = None 					# Словарь с настройкой режимов работы среды
		self.posts: list = []	 						# Список с должностями исполнителей
		self.performers: list = [] 						# Список с исполниетелями
		self.chiefs: list = []							# Список с ГИПами

		self.recent_dirs: list | None = None			# Список прошлых директорий
		self.project_BoQs: tuple[File_BoQ] = tuple()	# Кортеж с объектами данных о файлах BoQ
		self.library = dict() 							# Словарь всех библиотек проекта, используемых для ссылок
		self.clipboard: tuple | None = None				# буфер обмена для работы с разделами. 
		self.now = datetime.now()						# Для работы с текущей датой

		# ---------------- Автоматическая загрузка при создании объекта -----------------

		self.start_project_settings()
		self.soils_manager = Soils_Manager(self)				# единый менеджер грунтов
		self.sources_manager = Sources_Manager(self)			# единый менеджер источников
		self.libraries_manager = LibManager(self)				# менеджер управления пользовательскими библиотеками
		self.machinery_manager = Machinery_Manager(self)		# единый менеджер средств механизации
		self.documentation_manager = DOCs_Manager(self)			# единый менеджер документации

	# =============================== Загрузка/Сохранение ===============================

	def _get_clean_start(self):
		'''Функция инициализации базовых настроек среды и проекта при отсутствии загрузочного файла Project.json'''
		import Templates.ProjectTemplate as Template

		# Настройки проекта
		self.project_data = Template.PROJECT_DATA_TEMPLATE

		self.construction_site: str = Template.PROJECT_DATA_TEMPLATE.get('ConstructionSite', '')
		self.verifier: dict = Template.PROJECT_DATA_TEMPLATE.get('Verifier', dict())
		self.code: str = Template.PROJECT_DATA_TEMPLATE.get('Code', '')
		self.description: str = Template.PROJECT_DATA_TEMPLATE.get('Description', '')

		#Библиотек едениз измерений
		self.units = Template.UNITS_TEMPLATE

		# Режимы работы
		self.work_modes = Template.WORK_MODES_TEMPLATE

		# Должности
		self.posts = list(Template.POSTS_TEMPLATE)

		# Исполнители
		self.performers= list(Template.PERFORMERS_TEMPLATE)

		# ГИПы
		self.chiefs = list(Template.CHIEFS)

	def _get_load_data(self):
		'''Функция инициализации базовых настроек среды и проекта из загрузочного файла Project.json'''
		import Templates.ProjectTemplate as Template

		with open(self.settings_file_path, "r", encoding="utf-8") as f:
			settings_data = json.load(f)
			self.project_data = settings_data.get('project_data', Template.PROJECT_DATA_TEMPLATE) # загрузка данных проекта

			self.construction_site: str = settings_data.get(
				'ConstructionSite',
				Template.PROJECT_DATA_TEMPLATE.get('ConstructionSite', '')
			)

			self.verifier: dict = settings_data.get(
				'Verifier',
				Template.PROJECT_DATA_TEMPLATE.get('Verifier', dict())
			)

			self.code: str = settings_data.get(
				'Code',
				Template.PROJECT_DATA_TEMPLATE.get('Code', '')
			)

			self.description: str = settings_data.get(
				'Description',
				Template.PROJECT_DATA_TEMPLATE.get('Description', '')
			)

			self.units = settings_data.get('units_settings', Template.UNITS_TEMPLATE) # загрузка настроек едениц измерений
			self.work_modes = settings_data.get('work_modes_settings', Template.WORK_MODES_TEMPLATE) # загрузка настроек проекта
			self.posts = settings_data.get('posts_lib', list(Template.POSTS_TEMPLATE)) # загрузка возможных должностей
			self.performers = settings_data.get('performers_lib', list(Template.PERFORMERS_TEMPLATE)) # загрузка списка исполнителей
			if isinstance(self.performers, list):
				self.performers.sort()
			else:
				self.performers = []
			self.chiefs = settings_data.get('chiefs_lib', list(Template.CHIEFS)) # загрузка списка ГИПов
			if isinstance(self.chiefs, list):
				self.chiefs.sort()
			else:
				self.chiefs = []

	def start_project_settings(self):
		'''Функция получения настроек проекта из файла настроек или из шаблона'''

		if os.path.exists(self.settings_file_path):
			self._get_load_data() # загрузка данных из файла настроек проекта
		else:
			self._get_clean_start() # инициация базы данных из шаблона

	def saving_settings(self):
		export_elements = {
			'ConstructionSite': self.construction_site,
			'Verifier': self.verifier,
			'Code': self.code,
			'Description': self.description,
			'units_settings': self.units,
			'work_modes_settings': self.work_modes,
			'posts_lib': self.posts,
			'performers_lib': self.performers,
			'chiefs_lib': self.chiefs
		}
		folder = self.base_dir / self.sourсes_folder
		folder.mkdir(parents=True, exist_ok=True) # parents=True — рекурсивно создаёт вложенные папки
		with open(self.settings_file_path, "w", encoding="utf-8") as f: # сохранение параметров в JSON файл
			json.dump(export_elements, f, indent=4, ensure_ascii=False)

	def create_new_refinement(self, name: str):
		""" Создаёт новую ревизию методом копирования содержимого текущего каталога """
		new_path = self.base_dir.parent / name
		if new_path.exists():
			return None
		shutil.copytree(self.base_dir, new_path)
		return new_path

	# ------------------------------- Данные о разделах ---------------------------------
	@property
	def BoQs(self) -> tuple[File_BoQ]:
		'''Загрузка существующих разделов ВОР и их данных'''
		# получаем список файлов
		if not self.project_BoQs_path.exists():
			self.project_BoQs_path.mkdir(parents=True, exist_ok=True) # parents=True — рекурсивно создаёт вложенные папки
			return [] # папки нет – возвращаем пустой словарь
		files = self.project_BoQs_path.glob('*.json') 			# Список файлов разделов
		locked_files = []
		for f in self.project_BoQs_path.glob('*.lock'):
			parts = f.stem.split('__')
			if len(parts) >= 2:
				file_name = '__'.join(parts[:-1])   # всё, кроме последней части – имя файла
				user = parts[-1]
			else:
				file_name = f.stem
				user = None
			locked_files.append((file_name, user))
		BoQs = []
		for file in files:
			obj = File_BoQ(file, locked_files, self)
			BoQs.append(obj)
		BoQs.sort(key= lambda obj: obj.num)
		self.project_BoQs = tuple(BoQs)
		return BoQs
		

	def create_BoQ(self, filename: str, metadata) -> bool:
		'''
		Создать новый файл раздела ВОР
		:filename: наименование нового файла
		:metadata: словарь с информацией о новом разделе ВОР
		'''
		file_path: Path = self.project_BoQs_path / f'{filename}.json'
		if file_path.exists():
			return False		# Файл с таким именем уже существует

		data_template = {"sections" : [], "archive": []}

		data = {}
		data['metadata'] = metadata['metadata']
		data['data'] = data_template
		
		try:
			self.project_BoQs_path.mkdir(parents=True, exist_ok=True) # parents=True - рекурсивно создаёт вложенные папки
			with open(file_path, "w", encoding="utf-8") as f:
				# Записываем словарь в файл с форматированием
				json.dump(data, f, indent=4, ensure_ascii=False)
		except Exception as e:
			return False
		return True
	
	def open_BoQ(self, idx_BoQ) -> BoQ_manager:
		try:
			self.set_library()
			file: File_BoQ = self.project_BoQs[idx_BoQ]
			if not file.path.exists():
				raise FileNotFoundError
			lock_info = file.status_lock
			if lock_info[0]:
				raise FileIsBusy(lock_info[1])
			init_lock = file.lock()
			if not init_lock:
				# file.lock() сам по себе  вызывает FileNotFoundError, FileIsBusy
				return
			return BoQ_manager(self, file.path, False)
		except IndexError:									# Передоётся в GUI для обновления списка
			raise IndexError
		except FileNotFoundError:						# Передоётся в GUI для сообщения
			raise FileNotFoundError('Text')
		except FileIsBusy:
			return BoQ_manager(self, file.path, True)		# Открытие в режиме чтения

	def open_BoQ_for_export(self, file_BoQ):
		"""
		Загружает BoQ_manager из файла раздела без проверки блокировки.
		Используется для экспорта.
		"""
		from Core.BoQ import BoQ_manager  # локальный импорт
		manager = BoQ_manager(self, file_BoQ.path)
		return manager

	# =========================== Работа с атрибутами проекта ===========================

	def select_unit(self):
		'''Назначение ключа еденицы измерения для поиска'''
		i=0
		key_list = []
		for key, value in self.units.items():
			i += 1
			key_list.append(key)
		unit_id = requesting_value(int,'Выберите еденицу измерения')-1
		return key_list[unit_id]

	# ------------------------------- Изменение атрибутов -------------------------------

	def set_project_name(self):
		ConstructionSite = input('Введите новое название проекта: ')
		self.project_data['ConstructionSite'] = ConstructionSite
		code = input('Укажите новый шифр объекта: ')
		self.project_data['Code'] = code
	
	def set_verifier(self):
		verifier = input('Введите имя ответственного за проект ГИПа: ')
		self.project_data['Verifier'] = verifier

	# =========================== Работа с библиотекой ссылок ===========================

	def set_library(self):
		"""
		Создаёт библиотеку ссылок на переменные проекта в виде словаря,
		запросы к которому отправляются через self.process_library_requests()
		TODO перевести функцию генерацию в модули, сдесь только вызов
		"""
		self.library = {}

		if self.soils_manager:
			self._build_soils_library()
		if self.sources_manager:
			self._build_sources_library()
		if self.machinery_manager:
			self._build_machinery_library()
		if self.libraries_manager:
			self.library.update(self.libraries_manager.build_library())

	def _build_soils_library(self):
		soils_key = 'вг'
		self.library[soils_key] = {}
		soils = list(self.soils_manager.library.values())
		for soil in soils:
			local_key = soil.local_num.lower()
			self.library[soils_key][local_key] = {
				'y': soil.accepted_density,
				'прим1': soil._note1,
				'прим2': soil._note2,
			}
			if soil.gesn_1_obj:
				gesn1 = soil.gesn_1_obj
				self.library[soils_key][local_key]['гэсн1'] = {
					str(i): getattr(gesn1, f'work_{i}') for i in range(1, 14)
				}
			if soil.gesn_4_obj:
				self.library[soils_key][local_key]['гэсн4'] = {
					'группа': soil.gesn_4_obj.soil_group
				}
			if soil.gesn_5_obj:
				gesn5 = soil.gesn_5_obj
				self.library[soils_key][local_key]['гэсн5'] = {
					'группа1': gesn5.soil_group_1,
					'группа2': gesn5.soil_group_2,
					'расход_630': gesn5.expenditure_1,
					'расход_720': gesn5.expenditure_2,
					'расход_830': gesn5.expenditure_3,
					'расход_1020': gesn5.expenditure_4,
				}

	def _build_sources_library(self):
		sources_key = 'ви'
		self.library[sources_key] = {}
		for source in self.sources_manager.library:
			_, alias, work_part = source.alias_work.split('.')
			format_alias = alias.lower()
			self.library[sources_key][format_alias] = {
				work_part.lower(): source._work_text,
				text_after(source.alias_transportation, '.', 2).lower(): source.transportation_text,
				text_after(source.alias_note, '.', 2).lower(): source.note,
			}

	def _build_materials_library(self):
		materials_key = 'вм'
		self.library[materials_key] = {}
		for material in self.materials_manager.library:
			_, alias, work_part = material.alias_work.split('.')
			format_alias = alias.lower()
			self.library[materials_key][format_alias] = {
				work_part.lower(): material.work_text,
				text_after(material.alias_material, '.', 2).lower(): material.material_text,
				text_after(material.alias_factor, '.', 2).lower(): material.factor,
				text_after(material.alias_note1, '.', 2).lower(): material.note1,
				text_after(material.alias_note2, '.', 2).lower(): material.note2,
			}

	def _build_turnover_library(self):
		turnover_key = 'во'
		self.library[turnover_key] = {}
		for obj in self.reuse_manager.library:
			_, alias, note_part = obj._alias_note.split('.')
			format_alias = alias.lower()
			self.library[turnover_key][format_alias] = {
				note_part.lower(): obj._note
			}

	def _build_road_constr_library(self):
		rc_key = 'вдо'
		self.library[rc_key] = {}
		for road_constr in self.road_constr_manager.library:
			_, rc_alias = road_constr.alias.split('.')
			format_rc_alias = rc_alias.lower()
			self.library[rc_key][format_rc_alias] = {}

			for layer in road_constr.layers:
				layer_alias, work_part = layer.alias_work.split('.')
				format_layer_alias = layer_alias.lower()
				layer_dict = self.library[rc_key][format_rc_alias][format_layer_alias] = {}
				layer_dict[work_part.lower()] = layer.work_text
				layer_dict[text_after(layer.alias_material, '.').lower()] = layer.material_text
				layer_dict[text_after(layer.alias_factor, '.').lower()] = layer.factor
				layer_dict[text_after(layer.alias_note1, '.').lower()] = layer.note1
				layer_dict[text_after(layer.alias_note2, '.').lower()] = layer.note2

				if layer.children:
					for sub in layer.children:
						sub_alias = sub.alias.lower()
						sub_dict = self.library[rc_key][format_rc_alias][sub_alias] = {}
						sub_dict[work_part.lower()] = sub.work_text
						sub_dict[text_after(sub.alias_material, '.').lower()] = sub.material_text
						sub_dict[text_after(sub.alias_factor, '.').lower()] = sub.factor
						sub_dict[text_after(sub.alias_note1, '.').lower()] = sub.note1
						sub_dict[text_after(sub.alias_note2, '.').lower()] = sub.note2
	
	def _build_machinery_library(self):
		machinery_key = 'всм'	# Ведомость средств механизации
		self.library[machinery_key] = {}
		for machine in self.machinery_manager.library:
			alias = machine.alias.lower()
			self.library[machinery_key][alias] = machine.work

	def get_all_library_paths(self) -> tuple:
		"""
		Возвращает кортеж всех возможных строк-обращений к библиотеке,
		например ('@вг.пгс.у', '@вдо.покрытие.асфальт.работа', ...).
		"""
		result = []

		def walk(current_dict, current_path):
			for key, value in current_dict.items():
				new_path = current_path + [key]
				if isinstance(value, dict):
					walk(value, new_path)
				else:
					# конечное значение — формируем строку обращения
					full_alias = '.'.join(new_path)
					result.append(full_alias.upper())
		if not self.library:
			self.set_library()
		walk(self.library, [])
		return tuple(sorted(result))

	def get_soils_gesn1_data(self) -> list:
		""" Собирает данные для диалога земляных работ
		Возвращает список с кортежами внутри которых: номер грунта, доступные работы
		Доступные работы содержат в себе: Наименование работы, ссылку, индекс
		"""
		if not self.soils_manager:
			return
		return self.soils_manager.get_soils_gesn1_data()
	
	def get_soils_gesn5_data(self) -> list:
		if not self.soils_manager:
			return
		return self.soils_manager.get_soils_gesn5_data()
	
	def get_sources_data(self) -> list:
		""" Собирает данные для диалога земляных работ.
		Возвращает список с кортежами внутри которых: Наименование перевозки, Основной псевдоним"""
		if not self.sources_manager:
			return
		return self.sources_manager.get_sources_data()
	
	def get_machines_data(self)-> list:
		""" Собирает данные для диалога земляных работ
		Возвращает словарь со списком кортежей внутри которых: наименование механизации, ссылка"""
		if not self.machinery_manager:
			return
		return self.machinery_manager.get_machines_data()
	
	
	def get_user_libs_data(self) -> list:
		if not self.libraries_manager:
			return
		return self.libraries_manager.libraries
	
	# -------------------------------- Вспомогательное ---------------------------------
	def open_project_folder(self):
		open_folder(self.base_dir)

	def open_xml_folder(self):
		path = self.base_dir / 'XML'
		open_folder(path)

	def open_pdf_folder(self):
		path = self.base_dir / 'PDF'
		open_folder(path)
	
	def emergency_shutdown(self):
		""" Преобразует lock-файлы открытых пользователем ведомостей в резервные копии исходных файлов """
		if not self.project_BoQs_path.exists():
			return
		locked_files = self.project_BoQs_path.glob('*.lock')
		username = get_user_log()
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		locked_files = [locked_file for locked_file in locked_files if username in locked_file.name]
		for file in locked_files:
			# Фильтруем только файлы текущего пользователя
			if username not in file.stem:
				continue
			name = file.stem  # например "00_Наименование__user"
			new_name = name + '_' + timestamp + '.json'
			file.rename(self.project_BoQs_path / new_name)

class File_BoQ:
	"""Представляет один файл раздела ВОР. Управляет чтением, записью, блокировками."""
	def __init__(self, path: Path, locked_files, project: Project = None):
		self.path = Path(path)				# Объект пути к файлу
		self.project = project				# Объект данных проекта. Центральная система
		# -------------------------------- Метаданные файла ---------------------------------
		self.num = ''
		self.object_name = ''
		self.composer = ''
		self.composer_position = ''
		self.date = ''
		self.status_done = False
		self.local_estimate = ''
		self.log_list = {}
		self.note = ''

		self.is_locked = False				# Является ли файл заблокированным
		self.active_user = None				# Текущий пользователь (пользователи)

		self._exists = self.path.exists()
		if self._exists:
			self._load_metadata(locked_files)
		
	def _load_metadata(self, locked_files):
		"""Загружает только метаданные из JSON-файла."""
		filename = self.path.stem
		active_user =  None
		for data in locked_files:
			f_name, user = data
			if filename == f_name:
				active_user = user
				break
		self.is_locked = True if active_user else False
		self.active_user = active_user	
		try:
			with open(self.path, 'r', encoding='utf-8') as f:
				data = json.load(f)
				content = data.get('metadata')
				self.num = content.get('Num', '')
				self.object_name = content.get('ObjectName', '')
				sig =  content.get('Signatures',{})
				self.composer = sig.get('Composer','')
				self.composer_position = sig.get('Composer_Position','')
				self.date = content.get('Date', self.project.now.strftime("%d.%m.%Y"))
				self.status_done = content.get('Status_Done', False)
				self.local_estimate = content.get('local_estimate','')
				self.log_list = content.get('log_list',{})
				self.note = content.get('note', '')
		except (json.JSONDecodeError, PermissionError) as e:
			print(f"Ошибка при чтении файла {self.path}: {e}")

	def _load_data(self):
		"""Загружает полные данные раздела (ключ 'data') при необходимости."""
		if self.project is None:
			return
		try:
			with open(self.path, 'r', encoding='utf-8') as f:
				content = json.load(f)
				return content.get('data', None)
		except FileNotFoundError:
			raise FileNotFoundError
		except Exception as e:
			print(f"Ошибка загрузки данных из {self.path}: {e}")
			return

	@property
	def status_lock(self) -> tuple:
		locked_files = self._get_locked_files()
		filename = self.path.stem
		for data in locked_files:
			f_name, user = data.stem.split('__')
			if filename == f_name:
				return (True, user)
		return (False, None)
	
	def _get_locked_files(self):
		locked_files = self.project.project_BoQs_path.glob('*.lock') 	# Список открытых файлов
		locked_files = list(filter(lambda f: f.stem.startswith(self.path.stem), locked_files))
		return locked_files


	def lock(self) -> bool: 
		"""Создаёт lock-файл с именем пользователя."""
		if self.status_lock[0]:
			return False
		current_username = get_user_log('get_name')
		filename: Path = self.path.parent/ f'{self.path.stem}__{current_username}.lock'
		try:
			shutil.copy(self.path, filename)
			# Для проверки малой вероятности события, когда разные пользователи одновременно начали процесс открытия
			time.sleep(0.5)
			locked_files = self._get_locked_files()
			if len(locked_files) > 1:
				for lf in locked_files:
					_, username = lf.stem.split('__')
					if username != current_username:
						filename.unlink()
						raise FileIsBusy(username)
			return True
		except FileNotFoundError:
			raise FileNotFoundError
	
	def unlock(self):
		"""	Удаляет файл блокировки	"""
		username = get_user_log('get_name')
		filename: Path = self.path.parent / f'{self.path.stem}__{username}.lock'
		filename.unlink()

	def remove_lock(self):
		locked_files = self._get_locked_files()
		if not locked_files:
			return
		for lf in locked_files:
			lf: Path
			lf.unlink(True)


	def edit_file(self, metadata: dict):
		"""	Сохраняет результат редактирования метаданных """
		data = self._load_data()	
		if data is None:
			return 'нет данных'
		filename = metadata.pop('FileName')
		output = metadata
		output['data'] = data
		with open(self.path, 'w', encoding='utf-8') as f:
			json.dump(output, f, indent=4, ensure_ascii=False)
		if filename and filename != self.path.stem:
			self.unlock()
			new_file_path = self.path.parent / f'{filename}.json'
			self.path.rename(new_file_path)
			self.path = new_file_path
		else:
			self.unlock()
	
	def remove_file(self):
		self.path.unlink(True)

	def merge_filse(self, second_file: Path):
		pass



class FileIsBusy(Exception):
	"""
	Вызывает в случае, если в момент создания файла блокировки был обнаружен файл блокировки 
	от другого пользователя
	"""
	def __init__(self, username):
		super().__init__()
		self.username = username		# Текущий активный пользователь
	
	def get_data(self):
		return self.username
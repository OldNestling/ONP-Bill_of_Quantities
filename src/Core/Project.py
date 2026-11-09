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

import shutil, os, time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from orjson import JSONDecodeError

from .Utilities import get_user_log, open_folder, get_thread_count, read_json, save_json
from .DataLib import DataLibraryManager
from .Soils import Soils_Manager
from .Sources import Sources_Manager
from .Machinery import Machinery_Manager
from .Documentation import DOCs_Manager
from .BoQ import BoQ_manager
from .UserLibs import LibManager

from Templates.About import PROGRAM_SETTINGS_FOLDER, RECENT_DIRS_LOG, TEMPLATE_PROJECT_FILE



class Project:
	'''
	Управляющий данными по проекту класс. Для создания единственного объекта
	'''

	# ---------------------------- Работа с каталогом -----------------------------------
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
			data = read_json(filename)
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
		save_json(filename, dirs)

	
	@staticmethod
	def get_path_to_template() -> Path:
		""" Получает путь до глобального проекта-шаблона. 
		Шаблон содержит персонал организации, пользовательские библиотеки, источники.
		Используется для быстрой инициализации нового проекта
		"""
		app_dirr = Project.get_app_data_dir()
		filename = app_dirr / TEMPLATE_PROJECT_FILE
		path = None	# путь к проекту-шаблону
		try:
			data = read_json(filename)
			if isinstance(data, dict):
				path = data.get('path')
		except FileNotFoundError:
			return
		if not path:
			return
		
		path = Path(path)
		if path.exists():
			return path


	@staticmethod
	def save_path_to_template(path: Path):
		""" Сохраняет файл с путем к шаблонному проекту в папке настроек программы """
		app_dir = Project.get_app_data_dir()
		filename = app_dir / TEMPLATE_PROJECT_FILE
		save_json(filename, {'path': path})

	# ================================== Инициализация ==================================
	def __init__(
			self, 
			base_dir = None, 
			sources_folder = 'Data', 
			settings_file_name = 'Project.json', 
			project_BoQs_folder = 'ВОР'
	):
		"""
		:base_dir: директория папки проекта.
		:sourсes_folder: наименование папки сохранения настроек проекта.
		:settings_file_name: Корневой файл с настройками проекта.
		"""
		# ------------------------------- пути к файлам ---------------------------------
		# Определение директории проекта
		self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent	
		self.sources_folder = sources_folder			# Директория базы данных
		self.settings_file_name = settings_file_name	# Файл с основными настройками проекта
		# полный путь к файлу настроек
		self.settings_file_path: Path = self.base_dir / sources_folder / settings_file_name
		self.project_BoQs_folder = project_BoQs_folder 	# Наименование рабочей папки с файлам ВОР
		# путь к рабочей папки с фалами ВОР
		self.project_BoQs_path: Path = self.base_dir / project_BoQs_folder

		# ------------------------------ атрибуты проекта -------------------------------
		self.construction_site: str = ''				# Наименование объекта
		self.shorted_name: str | None = None			# Короткое имя для окна
		self.verifier: dict = {							# Заверитель
			'Name': None,								# Имя
			'Position': None							# Позиция
		}
		self.code: str = ''								# Шифр
		self.description: str = ''						# Дополнительное описание

		# Базовые параметры проекта
		self.units: dict = None 						# Словарь с единицами измерения и их параметрами
		self.work_modes: dict = None 					# Словарь с настройкой режимов работы среды
		self.posts: list = []	 						# Список с должностями исполнителей
		self.performers: list = [] 						# Список с исполнителями
		self.chiefs: list = []							# Список с ГИПами

		self.recent_dirs: list | None = None			# Список прошлых директорий
		self.project_BoQs: tuple[File_BoQ] = tuple()	# Кортеж с объектами данных о файлах BoQ
		
		# Словарь всех библиотек проекта, используемых для ссылок
		# модифицируется менеджерами
		self.library = dict() 							
		
		self.clipboard: tuple | None = None				# буфер обмена для работы с разделами. 
		self.now = datetime.now()						# Для работы с текущей датой

		# ---------------- Автоматическая загрузка при создании объекта -----------------

		self.start_project_settings()
		DataLibraryManager.DATA = self.sources_folder			# сводим всех наследников к единому атрибуту
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
		self.construction_site: str = Template.PROJECT_DATA_TEMPLATE.get('ConstructionSite', '')
		self.verifier: dict = Template.PROJECT_DATA_TEMPLATE.get('Verifier', dict())
		self.code: str = Template.PROJECT_DATA_TEMPLATE.get('Code', '')
		self.description: str = Template.PROJECT_DATA_TEMPLATE.get('Description', '')

		#Библиотек единиц измерений
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

		settings_data = read_json(self.settings_file_path)

		self.construction_site: str = settings_data.get(
			'ConstructionSite',
			Template.PROJECT_DATA_TEMPLATE.get('ConstructionSite', '')
		)

		self.shorted_name: str = settings_data.get('shorted_name')

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

		# загрузка настроек единиц измерений
		self.units = settings_data.get('units_settings', Template.UNITS_TEMPLATE) 
		# загрузка настроек проекта
		self.work_modes = settings_data.get('work_modes_settings', Template.WORK_MODES_TEMPLATE) 
		# загрузка возможных должностей
		self.posts = settings_data.get('posts_lib', list(Template.POSTS_TEMPLATE))
		# загрузка списка исполнителей
		self.performers = settings_data.get('performers_lib', list(Template.PERFORMERS_TEMPLATE)) 
		if isinstance(self.performers, list):
			self.performers.sort()
		else:
			self.performers = []
		# загрузка списка ГИПов
		self.chiefs = settings_data.get('chiefs_lib', list(Template.CHIEFS)) 
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
		""" Сохраняет параметры и настройки проекта """
		export_elements = {
			'ConstructionSite': self.construction_site,
			'shorted_name': self.shorted_name,
			'Verifier': self.verifier,
			'Code': self.code,
			'Description': self.description,
			'units_settings': self.units,
			'work_modes_settings': self.work_modes,
			'posts_lib': self.posts,
			'performers_lib': self.performers,
			'chiefs_lib': self.chiefs
		}
		folder = self.base_dir / self.sources_folder
		folder.mkdir(parents=True, exist_ok=True) # parents=True — рекурсивно создаёт вложенные папки
		save_json(self.settings_file_path, export_elements)


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
		file_paths = self.project_BoQs_path.glob('*.json') 			# Список файлов разделов
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

		def __get_BoQ(path):
			try:
				return path, read_json(path), None
			except Exception as e:
				return path, None, e

		BoQs = []
		errors = []
	
		with ThreadPoolExecutor(max_workers=get_thread_count()) as ex:
			futures = [ex.submit(__get_BoQ, fp) for fp in file_paths]
			for fut in as_completed(futures):
				path, file_data, error = fut.result()
				if error is not None: 
					errors.append((path, error))
					continue
				# без валидации по схеме, так как станет слишком долго
				obj = File_BoQ(path, locked_files, file_data, self)
				if obj.is_was_error:
					errors.append((path, obj.error_msg))
					continue
				else:
					BoQs.append(obj)

		if errors:
			for path, err in errors:
				print(f"Пропущен файл {path.name}: {err}")

		BoQs.sort(key= lambda obj: obj.num)
		BoQs = tuple(BoQs)
		self.project_BoQs = BoQs
		return BoQs
		

	def create_BoQ(self, filename: str, metadata) -> bool:
		'''
		Создать новый файл раздела ВОР
		:filename: наименование нового файла
		:metadata: словарь с информацией о новом разделе ВОР
		'''
		def __cleaning_filename_of_special_characters(text:str):
			""" Очищает от символов `__` имя файла """
			filename = text
			while '__' in filename:
				filename = filename.replace('__', '_')
			return filename


		name = __cleaning_filename_of_special_characters(filename)

		file_path: Path = self.project_BoQs_path / f'{name}.json'
		if file_path.exists():
			return False		# Файл с таким именем уже существует

		data_template = {"sections" : [], "archive": []}

		data = {}
		data['metadata'] = metadata['metadata']
		data['data'] = data_template
		
		try:
			# parents=True - рекурсивно создаёт вложенные папки
			self.project_BoQs_path.mkdir(parents=True, exist_ok=True) 
			save_json(file_path, data)
		except Exception as e:
			return False
		return True

	
	def open_BoQ(self, idx_BoQ: int, read_mode: bool = False) -> BoQ_manager:
		try:
			self.set_library()
			file: File_BoQ = self.project_BoQs[idx_BoQ]
			if not file.path.exists():
				raise FileNotFoundError

			# Принудительный режим чтения — блокировку не ставим
			if read_mode:
				return BoQ_manager(self, file, True)
			
			lock_info = file.status_lock
			if lock_info[0]:
				raise FileIsBusy(lock_info[1])
			init_lock = file.lock()
			if not init_lock:
				# lock() вернул False (гонка) — откатываемся в режим чтения
				return BoQ_manager(self, file, True)
			return BoQ_manager(self, file, False)
		except IndexError:						# Передаётся в GUI для обновления списка
			raise IndexError
		except FileNotFoundError:						# Передаётся в GUI для сообщения
			raise FileNotFoundError('Файл отсутствует')
		except FileIsBusy:
			return BoQ_manager(self, file, True)		# Открытие в режиме чтения


	def open_BoQ_for_export(self, file_BoQ):
		"""
		Загружает BoQ_manager из файла раздела без проверки блокировки.
		Используется для экспорта.
		"""
		from Core.BoQ import BoQ_manager  # локальный импорт
		manager = BoQ_manager(self, file_BoQ)
		return manager


	# =========================== Работа с библиотекой ссылок ===========================
	def set_library(self):
		"""
		Создаёт библиотеку ссылок на переменные проекта в виде словаря,
		запросы к которому отправляются через self.process_library_requests()
		TODO перевести функцию генерацию в модули, здесь только вызов
		"""
		self.library = {}	# модифицируется менеджерами библиотек

		if self.soils_manager:
			self.soils_manager.build_soils_library()
		if self.sources_manager:
			self.sources_manager.build_sources_library()
		if self.machinery_manager:
			self.machinery_manager.build_machinery_library()
		if self.libraries_manager:
			self.libraries_manager.build_library()


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


	def get_soils_GESN1_data(self) -> list:
		""" Собирает данные для диалога земляных работ
		Возвращает список с кортежами внутри которых: номер грунта, доступные работы
		Доступные работы содержат в себе: Наименование работы, ссылку, индекс
		"""
		if not self.soils_manager:
			return
		return self.soils_manager.get_soils_gesn1_data()

	
	def get_soils_GESN5_data(self) -> list:
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
		return self.libraries_manager.library
	
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

	# ============================== Импорт библиотек проекта ===========================
	def get_data_from_other_project (self, path: str | Path) -> dict | None:
		""" Проверяет, какие данные из проекта доступны для импорта  и агрегирует их в словарь"""
		if isinstance(path, Path):
			path_to_project = path
		elif isinstance(path, str):
			path_to_project = Path(path)
		else:
			return

		if not path_to_project.exists():
			return

		project_data = None

		try:
			project_json = path_to_project / self.sources_folder / self.settings_file_name
			project_data = read_json(project_json)
		except Exception:
			return None


		def __get_library_file_data(root_path: Path, library_manager: DataLibraryManager):
			path = root_path / self.sources_folder / (library_manager.FILE+'.json')
			try:
				return read_json(path)
			except Exception:
				return None

		data = {
			'performers_lib': project_data.get('performers_lib') if isinstance(project_data, dict) else None,
			'chiefs_lib': project_data.get('chiefs_lib') if isinstance(project_data, dict) else None,
			'posts_lib': project_data.get('posts_lib') if isinstance(project_data, dict) else None,
			'units_settings': project_data.get('units_settings') if isinstance(project_data, dict) else None,
			'soils_lib': __get_library_file_data(path_to_project, self.soils_manager),
			'sources_lib': __get_library_file_data(path_to_project, self.sources_manager),
			'user_libs': __get_library_file_data(path_to_project, self.libraries_manager),
			'machinery_lib': __get_library_file_data(path_to_project, self.machinery_manager)
		}
		return data
		

	def import_data_from_other_project(
			self, 
			instructions: dict[str, bool | list],
			data: dict
	) -> dict[str, bool | None] | None:
		""" Импортирует библиотеки данных из других проектов в текущие библиотеки
		### Args:
			- :instuctions: словарь с опциями импорта
			- :data: словарь со всеми библиотеками
		
		### Returns: 
			отчёт о результатах импорта данных
		"""
		if not data and not isinstance(data, dict):
			return

		# ----- Предварительная подготовка ----
		# библиотеки проекта за исключением единиц измерения
		LIB_KEYS = ('performers_lib', 'chiefs_lib', 'posts_lib', 'units_settings',
			'soils_lib', 'sources_lib', 'user_libs', 'machinery_lib')	

		# результат импорта данных для отчёта
		# None - не было импорта, False - не удалось, True — удалось
		results = {key: None for key in LIB_KEYS}
		# -----//-----

		# ----- Импорт библиотек объекта Project ----
		def __get_instruction(key: str, fail_value: False | None = False) -> bool:
			return instructions.get(key, fail_value)
		
		is_was_project_import = False
		# единицы измерения
		if __get_instruction('units_settings'):
			other_units = data.get('units_settings', {})
			if other_units and isinstance(other_units, dict):
				self.units.update(other_units)
				is_was_project_import = True
				results['units_settings'] = True
			else:
				results['units_settings'] = False


		def __process_project_list_data(current_lib: list, key: str):
			""" Импортирует в коллекции self.performers, self.chiefs, self.posts новые данные """
			nonlocal results, is_was_project_import, data

			if not __get_instruction(key):
				return

			lib_data = data.get(key, [])
			if lib_data and isinstance(lib_data, list):
				current_lib.extend(lib_data)
				# мутируем список in-place, чтобы изменения отразились в self.<collection>
				current_lib[:] = sorted(set(current_lib))
				is_was_project_import = True
				results[key] = True
			else:
				results[key] = False


		project_libs = zip(
			('performers_lib', 'chiefs_lib', 'posts_lib'),
			(self.performers, self.chiefs, self.posts)
		)

		for key, lib in project_libs:
			__process_project_list_data(lib, key)
		
		if is_was_project_import: # сохранение новых данных
			self.saving_settings()

		# -----//-----

		# ----- Импорт библиотек из менеджеров данных ----
		def __get_selected_libs(libs: list, selection: list[int]) -> list | None:
			""" Получает определённые библиотеки из всех выбранных в другом проекте
			### Args:
				- :libs: полная библиотека данных из другого проекта
				- :selection: список с индексами выбранных библиотек
			"""
			if not libs or not isinstance(libs, list):
				return
			import_libs = []
			for index in selection:
				try: import_libs.append(libs[index])
				except IndexError: continue

			return import_libs

		
		def __import_lib_data(key: str, manager: DataLibraryManager):
			""" Импортирует из другого проекта данные указанной библиотеки , добавляет к текущей, сохраняет
			### Args:
				- :key: словарь результатов импорта
			"""
			nonlocal results, data

			lib_data = data.get(key, [])
			if not isinstance(lib_data, list) or not manager.lock_libs():
				results[key] = False
				return

			# получаем выбранные элементы, если был передан список выбора
			selected_libs = __get_instruction(f'{key}_selection', None)
			if selected_libs is not None:
				lib_data = __get_selected_libs(lib_data, selected_libs)

			for raw_obj in lib_data:
				obj = manager.deserialization_function(raw_obj)
				if key != 'soils_lib': manager.library.append(obj)

			manager.save_lib()
			results[key] = True


		# библиотеки из менеджеров данных
		managers = (self.soils_manager, self.sources_manager,
		
			self.libraries_manager, self.machinery_manager)

		for i, key in enumerate(LIB_KEYS[4:]):
			if __get_instruction(key) is False: #не долежит импорту
				continue
			manager = managers[i].path
			__import_lib_data(key, manager)
		# -----//-----
		
		return results



class File_BoQ:
	"""Представляет один файл раздела ВОР. Управляет чтением, записью, блокировками."""
	def __init__(self, path: Path, locked_files, file_data: dict, project: Project = None):
		self.path = Path(path)				# Объект пути к файлу
		self.project = project				# Объект данных проекта. Центральная система
		# -------------------------------- Метаданные файла ---------------------------------
		self.num = ''
		self.object_name = ''
		self.composer = ''
		self.composer_position = ''
		self.date = ''
		self.status: int[0|1|2] = 0
		self.local_estimate = ''
		self.log_list = {}
		self.note = ''

		self.is_locked = False				# Является ли файл заблокированным
		self.active_user = None				# Текущий пользователь (пользователи)
		self.is_was_error = False
		self.error_msg: str | None = None

		self._exists = self.path.exists()
		if self._exists:
			self._load_metadata(locked_files, file_data)


	def __str__(self):
		return str(self.path)


	def __fspath__(self):
		return str(self.path)

		
	def _load_metadata(self, locked_files, data):
		"""Загружает только метаданные из JSON-файла."""
		filename = self.path.stem
		active_user =  None
		for lock_info in locked_files:
			f_name, user = lock_info
			if filename == f_name:
				active_user = user
				break
		self.is_locked = True if active_user else False
		self.active_user = active_user	
		try:
			content = data.get('metadata')
			self.num = content.get('Num', '')
			self.object_name = content.get('ObjectName', '')
			sig =  content.get('Signatures',{})
			self.composer = sig.get('Composer','')
			self.composer_position = sig.get('Composer_Position','')
			self.date = content.get('Date', self.project.now.strftime("%d.%m.%Y"))

			# для совместимости со старыми файлами
			status_done = content.get('Status_Done')
			if status_done is None:
				self.status = content.get('Status', 0)
			elif isinstance(status_done, bool):
				self.status = 2 if status_done else 0
			elif isinstance(status_done, int) and status_done in (0, 1, 2):
				self.status = status_done
			else:
				self.status = 0

			self.local_estimate = content.get('local_estimate','')
			self.log_list = content.get('log_list',{})
			self.note = content.get('note', '')
		except (JSONDecodeError, PermissionError, ValueError, AttributeError) as e:
			text = f"[File_BoQ: _load_metadata] {self.path.name}: {e}" 
			self.is_was_error = True
			self.error_msg = text


	def _load_data(self):
		"""Загружает полные данные раздела (ключ 'data') при необходимости."""
		if self.project is None:
			return
		try:
			content = read_json(self.path)
			return content.get('data', None)
		except FileNotFoundError:
			raise FileNotFoundError
		except Exception as e:
			print(f"[File_BoQ: _load_data] {e}")


	@property
	def status_lock(self) -> tuple[bool, str | None]:
		locked_files = self._get_locked_files()
		filename = self.path.stem
		for data in locked_files:
			f_name = None
			user = None
			try:
				f_name, user = data.stem.split('__')
			# в старом файле присутствуют лишние символы __, 
			# которые не были устранены исправлением символов в имени файла,
			# появившегося позже   
			except ValueError:		
				lock_file_name = data.stem
				parts = lock_file_name.split('__')
				parts = [p for p in parts if p]		# очищаем от пустых элементов
				user = parts.pop()
				end_part = '__' if lock_file_name.endswith('__') else ''
				f_name = '__'.join(parts) + end_part
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
		save_json(self.path, output)
			
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


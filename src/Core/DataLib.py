from filelock import FileLock, Timeout
from abc import ABC, abstractmethod
from pathlib import Path
from .Utilities import get_user_log
import os, time, json


class DataLibraryManager(ABC):
	""" Данный класс используется для создания менеджеров библиотек """
	DATA = 'Data' 			# Папка с базами данных	
	FILE = '' 				# Файл с данными. Необходимо переопределить у наследника
	LOCK_TIMEOUT = 10		# максимальное время ожидания блокировки (сек)

	def __init__(self):
		super().__init__()
		self._lock: FileLock = None
		self.lock_owned = False
		self.project = None
		self.library = []
		

	# ------------------------------------ Пути -----------------------------------------

	@property
	def _file_dir(self) -> Path | None:
		if self.project and hasattr(self.project, 'base_dir') and self.project.base_dir:
			return self.project.base_dir / self.DATA
		return None

	@property
	def _file_path(self) -> Path | None:
		""" Получает путь к файлу сохранения данных"""
		file_dir = self._file_dir
		if file_dir:
			return file_dir / (self.FILE + '.json')
		return None
	
	@property
	def _lock_file(self) -> Path:
		file_path = self._file_path
		if file_path:
			return file_path.with_suffix('.lock')
		return None
	
	@property
	def _meta_file(self) -> Path:
		lock_file = self._lock_file
		if lock_file:
			return lock_file.with_suffix('.meta')
		return None

	# --------------------------------- Блокировка --------------------------------------
	def lock_libs(self) -> bool:
		"""Захватывает блокировку и записывает метаданные."""
		if self.lock_owned:
			return True
		if self._lock_file is None:
			return False		
		lock = FileLock(self._lock_file, timeout=self.LOCK_TIMEOUT)
		try:
			lock.acquire()
		except Timeout:
			return False
		
		# Записываем мета-информацию (перезаписываем, если был старый)
		meta = {
			"user": get_user_log("get_name"),
			"pid": os.getpid(),
			"timestamp": time.time()
		}
		try:
			with open(self._meta_file, "w") as f:
				json.dump(meta, f)
		except Exception as e:
			lock.release()
			print(f"Ошибка записи мета-файла: {e}")
			return False
		self._lock = lock
		self.lock_owned = True
		return True


	def unlock(self):
		"""Снимает блокировку и удаляет метаданные."""
		if not self.lock_owned:
			return
		if self._lock:
			self._lock.release()
		if self._meta_file:
			self._meta_file.unlink(missing_ok=True)
		self._lock = None
		self.lock_owned = False


	@property
	def lock_owner(self):
		"""
		Возвращает информацию о владельце блокировки или None.
		Если блокировка свободна (или висит), очищает мусор.
		"""
		# Если lock-файла нет – блокировка отсутствует
		if self._lock_file is None:
			return None
		if not self._lock_file.exists():
			if self._meta_file:
				self._meta_file.unlink(missing_ok=True)
			return None
		# Пытаемся захватить блокировку с малым таймаутом (неблокирующий режим)
		test_lock = FileLock(self._lock_file, timeout=0.001)
		try:
			test_lock.acquire()
			# Успешно – блокировка свободна, удаляем мусор
			test_lock.release()
			self._lock_file.unlink(missing_ok=True)
			if self._meta_file:
				self._meta_file.unlink(missing_ok=True)
			return None
		except Timeout:
			# Блокировка занята – читаем мета-файл
			if self._meta_file.exists():
				try:
					with open(self._meta_file) as f:
						return json.load(f)
				except:
					return {"user": "неизвестен", "pid": None, "timestamp": None}

	# ---------------------------- Загрузка / Сохранение --------------------------------

	@abstractmethod
	def deserialization_function(data) -> object:
		""" Функция десериализации для конкретной библиотеки данных 
			
			:data: словарь с данными единичноо объекта из json"""
		pass

	def load_lib(self):
		""" Загружает данные библиотеки из JSON-файл """
		if not self.project:
			return
		try:
			with open(self._file_path, "r", encoding="utf-8") as f:
				data = json.load(f)
				for element in data:
					obj = self.deserialization_function(element)
					self.library.append(obj)
		except FileNotFoundError:
			self.library = []
		except json.JSONDecodeError:
			pass
		except Exception as e:
			raise RuntimeError(f'{"-"*40}\nОшибка загрузки файла {self._file_path}: {e}')

	def save_lib(self):
		""" Сохраняет данные библиотеки в JSON-файл """
		if not self.project or not self.lock_owned:
			return False
		try:
			tmp_path = self._file_path.with_suffix(".tmp")
			with open(tmp_path, 'w', encoding='utf-8') as f:
				data = []
				for obj in self.library:
					data.append(obj.serialization())
				json.dump(data, f, indent=4, ensure_ascii=False)
			tmp_path.replace(self._file_path)
			return True
		except Exception as e:
			print(f'{"-"*40}\nПроизошла ошибка: {e}')
			if tmp_path.exists():
				tmp_path.unlink(missing_ok=True)
			return False
		finally:
			self.unlock()
		
	def reload_lib(self):
		""" Сбрасывает данные библиотеки и повторно их загружает"""
		self.library = []
		self.load_lib()
		self.unlock()

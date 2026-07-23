from filelock import FileLock, Timeout
from abc import ABC, abstractmethod
from pathlib import Path
from .Utilities import get_user_log
import os, time, json


class DataLibraryManager(ABC):
	""" Данный класс используется для создания менеджеров библиотек """
	DATA = 'Data' 			# Папка с базами данных	
	FILE = '' 				# Файл с данными. Необходимо переопределить в наследника
	LOCK_TIMEOUT = 10		# максимальное время ожидания блокировки (сек)

	def __init__(self):
		super().__init__()
		self._lock: FileLock = None
		self.lock_owned = False

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
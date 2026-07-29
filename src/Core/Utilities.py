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

import re, os, pyperclip, sys, hashlib,  subprocess
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# ГЛОБАЛЬНЫЕ ФУНКЦИИ ПРОЕКТА 

# ------------------------------------ Запрос данных ------------------------------------------
def requesting_value(value_type, input_object: str, min_value = None, max_value = None):
	'''
	Функция для запроса ввода данных пользователем с проверкой соблюдения условий

	:value_type: тип запрашиваеомго значения
	:input_object: указатель сущности запроса
	:min_value: минимальное допустимое значение
	:max_value: максимально допустимое значение
	'''

	while True:
		input_value = input(f'{input_object}: ')
		
		if value_type == str:
			return input_value  # Возвращаем введённую строку
		
		elif value_type == int:
			# Проверяем наличие точки ИЛИ запятой
			if '.' in input_value or ',' in input_value:
				print('Введите целое значение (без точки и запятой)')
				continue  # Возвращаемся к началу цикла
			
			try:
				value = int(input_value)  # Преобразуем число
				if min_value <= value <= max_value:
					return value
				else:
					print(f'Введенное число находится за пределами диапазона от {min_value} до {max_value}')
					continue
			except ValueError:
				print('Введите целое значение (без точки и запятой)')
				continue  # Повторяем ввод
		elif value_type == float:
			try:
				value = float(input_value.replace(',','.'))
				
				if min_value <= value <= max_value:
					return value
				else:
					print(f'Введенное число находится за пределами диапазона от {min_value} до {max_value}')
					continue
			except ValueError:
				print('Ошибка: введите число')
				continue  # Повторяем ввод

def decimal_round(number, precision=2):
	# Преобразуем число в строку, чтобы Decimal точно его понял
	# Формируем строку для указания точности, например '0.01' для 2 знаков
	quantize_str = '0.' + '0' * precision
	# Выполняем округление с нужным правилом
	return Decimal(str(number)).quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

def clearing_string(string):
	"""Подготовка строки для вычисления."""
	s = str(string) # на всякий
	s = s.strip()
	s = s.replace(' ', '')
	s = s.replace('\n', '')
	s = s.replace(',', '.')
	return s

def fixing_decimals(string: str):
	""" Заменяет в числах десятичный разделитель на точку """
	pattern = r'\d+\,\d+'
	matches = re.findall(pattern, string)
	text = string
	for m in matches:
		fix = m.replace(',', '.')
		text = text.replace(m, fix)
	return text

def fixing_spaces(string: str):
	""" Убирает лишние пробелы в тексте"""
	pattern = r'\s{2,}'
	MARKER = '\x00'  # непечатаемый символ, который вряд ли встретится в данных
	text = string.replace('\n', MARKER) # чтобы избежать повреждения переноса строк
	matches = re.findall(pattern, text)
	output = text
	for m in matches:
		output = output.replace(m, ' ')
	return output.replace(MARKER, '\n')

def convert_value(text):
	"""
	Пытается преобразовать строку в число.
	Если возможно - возвращает int или float, иначе - строку.
	"""
	if isinstance(text, int) or isinstance(text, float):
		return text
	
	value = clearing_string(text)
	
	# Пропускаем пустые значения
	if not value or value == "-":
		return None
	
	# Пробуем преобразовать в int
	try:
		return int(value)
	except ValueError:
		pass
	
	# Пробуем преобразовать в float
	try:
		return float(value)
	except ValueError:
		pass
	
	# Если не получилось - возвращаем строку
	return value
	
def resource_path(relative_path):
	"""Получить абсолютный путь к файлу ресурса, работающий и в .exe, и в скрипте."""
	try:
		# PyInstaller создаёт временную папку и хранит её путь в _MEIPASS
		base_path = sys._MEIPASS
	except AttributeError:
		base_path = os.path.abspath(".")
	return os.path.join(base_path, relative_path)

def get_hash_text(text: str) -> str:
	""" Используется для сравнения изменений текстовых ячеек в позициях """
	# Форматирование текста без учёта мелких корректировок
	text = text.replace(' ','').replace(',','').replace('.','').replace('\n','').lower().strip()
	hash_object = hashlib.md5(text.encode())
	hex_digest = hash_object.hexdigest()
	return hex_digest
	
def text_before(text, part, match=1):
	"""
	Аналог функции ТЕКСТДО()

	Args:
		text (str): исходный текст.
		part (str): искомый фрагмент.
		match (int): номер вхождения фрагмента (начиная с 1).
		
	Returns:
		str: текст до указанного вхождения или 'Ошибка!' при ошибке.
	"""
	# Проверяем корректность match
	if match < 1:
		print('Ошибка: параметр match должен быть >= 1')
		return 'Ошибка!'
	
	# Находим все позиции вхождений фрагмента
	positions = []
	start = 0
	while True:
		pos = text.find(part, start)
		if pos == -1:  # больше вхождений нет
			break
		positions.append(pos)
		start = pos + 1  # ищем следующее вхождение
	
	# Проверяем, достаточно ли вхождений
	if len(positions) < match:
		print(f'Ошибка: найдено только {len(positions)} вхождений, запрошено: {match}')
		return 'Ошибка!'
		
	# Возвращаем текст до нужного вхождения
	target_pos = positions[match - 1]
	return text[:target_pos]

def text_after(text, part, match=1):
	"""
	Аналог функции ТЕКСТПОСЛЕ()

	Args:
		text (str): исходный текст.
		part (str): искомый фрагмент.
		match (int): номер вхождения фрагмента (начиная с 1).
		
	Returns:
		str: текст после указанного вхождения или 'Ошибка!' при ошибке.
	"""
	# Проверяем корректность match
	if match < 1:
		print('Ошибка: параметр match должен быть >= 1')
		return 'Ошибка!'
	
	# Находим все позиции вхождений фрагмента
	positions = []
	start = 0
	while True:
		pos = text.find(part, start)
		if pos == -1:  # больше вхождений нет
			break
		positions.append(pos)
		start = pos + 1  # ищем следующее вхождение
	
	# Проверяем, достаточно ли вхождений
	if len(positions) < match:
		print(f'Ошибка: найдено только {len(positions)} вхождений, запрошено: {match}')
		return 'Ошибка!'
		
	# Возвращаем текст до нужного вхождения
	target_pos = positions[match - 1]
	return text[target_pos+len(part):]

# --------------------------------- Работа с пользователем ---------------------------------------

def get_user_log(mode = 'get_name'):
	'''
	Функция получения данных о активности пользователя

	:mode: Режим вывода "get_name": - получить только имя; "get_name_date" - получить имя и дату со временем
	'''
	user = os.getlogin()
	now = datetime.now()

	if mode == 'get_name':
		try:
			return user
		except OSError:
			print("os.getlogin() не работает в некоторых окружениях (например, в некоторых сервисах)")
	
	elif mode == 'get_name_date':
		try:
			return f'{user} ({now.strftime("%Y.%m.%d %H:%M")})'
		except OSError:
			print("os.getlogin() не работает в некоторых окружениях (например, в некоторых сервисах)")

def copy_to_clipboard(text):
	"""
	Копирует текст в буфер обмена.
	
	Args:
		text (str): текст для копирования.
	"""
	pyperclip.copy(text)
	print("Текст скопирован в буфер обмена!")

def open_folder(path):
	""" Открывает указанную папку  """
	try:
		if sys.platform == "win32":
			os.startfile(path)
		elif sys.platform == "darwin":
			subprocess.Popen(["open", path])
		else:
			subprocess.Popen(["xdg-open", path])
	except Exception as e:
		print(e)
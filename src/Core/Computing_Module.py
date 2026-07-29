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

import math, re
from .Utilities import convert_value, text_after, clearing_string, decimal_round


# ---------------------------------------------------------------------------------------
# ================================= Вычислительный модуль ===============================
# ---------------------------------------------------------------------------------------
# Данный модуль используется для вычисления формул позиций в ведомости объемов работ. 
# Импортируется в BoQ.py и work_tab_support.py

# Сожержит функции запроса к библиотеке проекта, пользовательские функции и обший 
# вычичслитель функций
#---------------------------------------------------------------------------------------


def get_all_alias_request(text):
	""" Получает список обращений к библотеке проекта, декорированных начальным символом @ """
	PATTERN = r'@[^\s.,+\-*/()]+(?:\.[^\s.,+\-*/()]+)+'
	matches = re.findall(PATTERN, text)
	return matches

def get_from_library(alias: str, library: dict):
	"""
	Возвращает значение по строке-запросу
	
	Ars:
		:alias: текстовый запрос с декоратором @ и ключами к словарям, записанными через точку
	
	Returns:
		:str: значение из библотеки проекта или отчёт об ошибке
	"""
	keys = text_after(alias, '@').lower().replace(';','').split('.')

	value = None
	iter = 0

	for key in keys:
		if iter > 0 and value is None:
			break
		if value is None:
			value = library.get(key, None)
		else:
			try:
				value = value.get(key, None)
				iter += 1
			except AttributeError:
				print('Ошибка изъятия значения')
				if  isinstance(value, list):
					return f"{' '.join(map(lambda x: str(x), value))}"
				return f'[{value}]'
	
	if isinstance(value, dict):
		return '[Ошибка: не полный ключ]'
	elif value:
		return value
	else:
		return f'[Ошибка запроса в сегменте {iter+1}]'
	

def extract_numbers_from_string(text):
	"""
	Извлекает все полные числа из строки.
	
	Аргументы:
		text (str): Входная строка с числами, отделенными пробелами
	
	Возвращает:
		list: Список чисел (int или float)
	"""
	# Регулярное выражение для поиска чисел
	pattern = r'[-+]?\d+(?:\.\d+)?'
	
	# Находим все совпадения
	matches = re.findall(pattern, text)
	
	# Преобразуем найденные строки в числа
	numbers = []
	for match in matches:
		try:
			# Пробуем преобразовать в float, затем проверяем, целое ли
			float_value = float(match)
			if float_value.is_integer():
				numbers.append(int(float_value))
			else:
				numbers.append(float_value)
		except ValueError:
			# Если преобразование не удалось, пропускаем
			continue
	
	return numbers

def find_args(text: str, args_count: int):
	""" Ищет аргументы для формулы по разделителю ";" 
	- :text: сырая строка для рsасчленения
	- :args_count: сколько сегментов аргументации нужно найти
	"""
	""" В табличном редакторе все аргументы изначально являются текстом, 
	а потому  могут перебивать порядок аргументов, эта функцияя нужна для простоты 
	 вместо разбиения по символу и передачи в пользовательские функции"""
	MARKER = '\x00'  # непечатаемый символ, который вряд ли встретится в данных
	processed = text.replace('";"', MARKER)
	
	# Разбиваем по настоящим разделителям ';'
	parts = processed.split(';')
	if len(parts) < args_count:
		return
	args = []
	count = 0
	for _ in range(len(parts)):
		if count + 1 == args_count and len(parts) > 1:
			args.insert(0, ' '.join(parts).strip())
			break
		args.insert(0, parts.pop().strip())
		count += 1
	
	args = [arg.replace(MARKER, ';') for arg in args]
	return args

# ---------------------------- Пользовательские функции ---------------------------------

def sum_numbers(array: str):
	''' Аналог  функции СУММ()'''
	args = array.split(';')
	args = [convert_value(val) for val in args]
	if len(args) == 1 and isinstance(args[0], str):
		numbers = args[0].split(',')
		nums = []
		for n in numbers:
			nums.append(float(n))
		res = sum(nums)
	else:
		res = sum(args)
	return res

def extract_number(string: str):
	"""извлекает i-ое число из строки. """
	string = string.replace('(',' ').replace(')',' ')
	args = find_args(string, 2)
	if args is None or len(args) != 2:
		return '#ОШИБКА'
	text, i = args
	try:
		i = int(i)
	except Exception:
		return '#ОШИБКА'
	numbers = extract_numbers_from_string(str(text))
	if not numbers:
		return '#ПУСТО'
	if 1 <= i <= len(numbers):
		return numbers[i - 1]
	else:
		return '#ОШИБКА'

def text_before_func(string: str):
	"""
	Аналог функции ТЕКСТДО()

	Args:
		text (str): исходный текст.
		part (str): искомый фрагмент.
		match (int): номер вхождения фрагмента (начиная с 1).
		
	Returns:
		str: текст до указанного вхождения или 'Ошибка!' при ошибке.
	"""
	args = find_args(string, 3)
	if args is None or len(args) != 3:
		return '#ОШИБКА'
	text, part, m = args

	try:
		m = int(m)
	except Exception:
		return '#ОШИБКА'
	# Проверяем корректность match
	if m < 1:
		return '#ОШИБКА'
	
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
	if len(positions) < m:
		return '#ОШИБКА ДИАПОЗОНА'
		
	# Возвращаем текст до нужного вхождения
	target_pos = positions[m - 1]
	return text[:target_pos]

def text_after_func(string: str) -> str:
	"""
	Аналог функции ТЕКСТПОСЛЕ()

	Args:
		text (str): исходный текст.
		part (str): искомый фрагмент.
		match (int): номер вхождения фрагмента (начиная с 1).
		
	Returns:
		str: текст после указанного вхождения или 'Ошибка!' при ошибке.
	"""
	args = find_args(string, 3)
	if args is None or len(args) != 3:
		return '#ОШИБКА'
	
	text, part, m = args
	# Проверяем корректность match

	try:
		m = int(m)
	except Exception:
		return '#ОШИБКА'

	if m == 0:
		return 'Ошибка!'
	elif m == -1:
		inv: str = text[::-1]
		idx = inv.find(part)
		idx = len(text) - idx
		return text[idx:]
	
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
	if len(positions) < m:
		print(f'Ошибка: найдено только {len(positions)} вхождений, запрошено: {m}')
		return 'Ошибка!'
		
	# Возвращаем текст до нужного вхождения
	target_pos = positions[m - 1]
	return text[target_pos+len(part):]

def calculate_segment(text):
	text = clearing_string(text).replace('^', '**')
	try:
		return eval(text, {"__builtins__": None})
	except:
		return text
	
def round_func(string: str):
	""" Функция округления из запроса-строки """
	args = find_args(string, 2)
	if args is None or len(args) != 2:
		return '#ОШИБКА'
	
	val, m = args
	# Проверяем корректность match
	try:
		val = convert_value(val)
		m = int(m)
		return decimal_round(val, m)
	except Exception:
		return '#ОШИБКА'



def get_pi(*args):
	return math.pi

def get_pow(string: str):
	args = find_args(string, 2)
	if args is None or len(args) != 2:
		return '#ОШИБКА'
	val, exp = args
	try:
		val = convert_value(val)
		exp = convert_value(exp)
	except Exception:
		return '#ОШИБКА'
	return pow(val, exp)

def get_sqrt(val: str):
	try:
		val = convert_value(val)
	except Exception:
		return '#ОШИБКА'
	return	math.sqrt(val)

def get_cicle_area(r: str):
	try:
		r = convert_value(r)
	except Exception:
		return '#ОШИБКА'
	return math.pi*r**2

def get_cicle_lenght(r: str):
	try:
		r = convert_value(r)
	except Exception:
		return '#ОШИБКА'
	return 2*math.pi*r

def get_cylinder_area(string: str):
	args = find_args(string, 2)
	if args is None or len(args) != 2:
		return '#ОШИБКА'
	r, h = args
	try:
		r = convert_value(r)
		h = convert_value(h)
	except Exception:
		return '#ОШИБКА'
	return 2*math.pi*r*h

def get_cylinder_volume(string: str):
	args = find_args(string, 2)
	if args is None or len(args) != 2:
		return '#ОШИБКА'
	r, h = args
	try:
		r = convert_value(r)
		h = convert_value(h)
	except Exception:
		return '#ОШИБКА'

def get_sin(val):
	try:
		val = convert_value(val)
	except Exception:
		return '#ОШИБКА'
	return math.sin(val)

def get_cos(val):
	try:
		val = convert_value(val)
	except Exception:
		return '#ОШИБКА'
	return math.cos(val)

def get_rad(val):
	try:
		val = convert_value(val)
	except Exception:
		return '#ОШИБКА'
	return math.radians(val)

def get_deg(val):
	try:
		val = convert_value(val)
	except Exception:
		return '#ОШИБКА'
	return math.degrees(val)




# ---------------------------- Вычислитель формул ---------------------------------

# Пользовательские функции
FUNCTIONS = {
		'СТЕПЕНЬ': get_pow,
		'КОРЕНЬ': get_sqrt,
		"ИЗВЛЕЧЬ": extract_number,
		"СУММ": sum_numbers,
		"ТЕКСТДО": text_before_func,
		"ТЕКСТПОСЛЕ": text_after_func,
		"ВЫЧИСЛИТЬ": calculate_segment,
		"ОКРУГЛ": round_func,
		"ПЛ_КРУГА": get_cicle_area,
		'ДЛН_КРУГА': get_cicle_lenght,
		'ПОВ_ЦИЛИНДРА': get_cylinder_area,
		'ОБЪЕМ_ЦИЛИНДРА': get_cylinder_volume,
		'ПИ': get_pi,
		'sin': get_sin,
		'cos': get_cos,
		'РАД': get_rad,
		'ГРАД': get_deg
	}

# Заранее собираем паттерн для имён функций
func_pattern = '|'.join(re.escape(name) for name in FUNCTIONS.keys())

def eval_functions(s: str):
	"""
	Рекурсивно вычисляет пользовательские функции в строке.
	Возвращает результат вычисления (число, строку) или None при ошибке.
	"""
	
	try:
		# Пока есть вхождения функций
		while True:
			# Ищем имя функции, за которым следует '('
			match = re.search(rf'({func_pattern})\s*\(', s)
			if not match:
				break
			
			func_name = match.group(1)
			start = match.start()
			paren_pos = match.end() - 1   # позиция символа '('

			# Ищем парную закрывающую скобку с учётом вложенности
			depth = 1
			i = paren_pos + 1
			while i < len(s) and depth > 0:
				if s[i] == '(':
					depth += 1
				elif s[i] == ')':
					depth -= 1
				i += 1
			
			if depth != 0:
				# Не найдена парная скобка — синтаксическая ошибка, ничего не заменяем
				break

			end = i                     # позиция после закрывающей ')'
			args_str = s[paren_pos + 1:end - 1]
			
			# Проверяем, известна ли функция
			if func_name not in FUNCTIONS:
				# Неизвестная функция → возвращаем None (не ломаем программу)
				return '#ФУНКЦИЯ'
			
			# Рекурсивно обрабатываем аргументы (внутри args_str могут быть другие функции)
			args_processed = eval_functions(args_str)
			if args_processed is None:
				return None
			
			# Вызываем пользовательскую функцию
			try:
				result = FUNCTIONS[func_name](args_processed)
			except Exception:
				return None
			
			# Подставляем результат вместо вызова функции
			s = s[:start] + str(result) + s[end:]
		return s
	
	except Exception:
		# Любая непредвиденная ошибка — возвращаем None
		return None
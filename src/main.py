# Copyright © 2026 OldNestling
# License: GPLv3 (GNU General Public License Version 3)
#
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

# ==============================  О ПРОЕКТЕ ===================================

# ПРОЕКТ: "ONP: Система ВОР"
# РАЗРАБОЧИК: OldNestling (OldNestling@yandex.ru)
# GitHub: https://github.com/OldNestling/ONP-Bill_of_Quantities.git

# Данный проект разработан для автоматизации и упрощения составления
# ведомостей объемов работ в дорожно-строительной сфере с выводом данных
# в соответствии с XML-схемой.

# Помимо этого, проект послужил процессу обучения программированию на Python для автора.
# Проект находится в стадии активной разработки, код может требовать рефакторинга.

import sys, traceback

from Templates.styles import CSS_SETTING
from UI.project_window import Project_Window
from Core.Utilities import resource_path


from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QIcon

# ---------- Глобальная ссылка на окно (для обработчика) ----------
_main_window = None

def set_main_window(window):
	global _main_window
	_main_window = window

# ---------- Обработчик ошибок с показом окна ----------
def show_critical_error(error_msg):
	"""Показывает окно с подробным текстом ошибки."""
	msg = QMessageBox()
	msg.setIcon(QMessageBox.Icon.Critical)
	msg.setWindowTitle("Критическая ошибка")
	msg.setText("Произошла необработанная ошибка. Подробности в раскрывающемся блоке.")
	msg.setDetailedText(error_msg)
	msg.setStandardButtons(QMessageBox.StandardButton.Ok)
	msg.exec()

def global_exception_handler(exc_type, exc_value, exc_tb):
	"""Обработчик для sys.excepthook."""
	error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))

	# ---- Аварийное преобразование lock-файлов ----
	try:
		if _main_window is not None and _main_window.project is not None:
			_main_window.project.emergency_shutdown()
	except Exception as e:
		print(f"Ошибка при аварийном сохранении: {e}")

	# Показываем окно
	show_critical_error(error_msg)
	# Завершаем приложение после закрытия окна
	QApplication.quit()
	sys.exit(1)

# Устанавливаем глобальный перехватчик для исключений вне событий Qt
sys.excepthook = global_exception_handler


# ---------- Класс приложения для перехвата исключений в слотах ----------
class CustomApplication(QApplication):
	def notify(self, receiver, event):
		try:
			return super().notify(receiver, event)
		except Exception:
			# Перехватываем любые исключения в событиях и слотах
			exc_type, exc_value, exc_tb = sys.exc_info()
			global_exception_handler(exc_type, exc_value, exc_tb)
			return False   # говорим Qt, что событие не обработано

def main():
	app = CustomApplication(sys.argv)
	#app = QApplication(sys.argv)

	light_palette = app.style().standardPalette()
	# Меняем роли на светлые
	light_palette.setColor(QPalette.ColorRole.Window, QColor('#E1E1E1'))
	light_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
	app.setPalette(light_palette)	

	
	app.setStyleSheet(CSS_SETTING)

	icon = QIcon(resource_path(r'UI\icons\icon_main.ico'))
	app.setWindowIcon(icon)
	window = Project_Window()
	window.setWindowIcon(icon)
	
	set_main_window(window)

	sys.exit(app.exec())


if __name__ == "__main__":
	main()
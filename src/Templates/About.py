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

# Данные для вывода информации о программе
PROGRAM_NAME = 'ONP: Система ВОР'
PROGRAM_VERSION = '1.0.4.1 (от 2026.11.09)'
COPYRIGHT = "Copyright © 2026 OldNestling"

# папка с настройками по пути С:\Users\User\AppData\Roaming\
PROGRAM_SETTINGS_FOLDER = "ONP_Система_ВОР"
RECENT_DIRS_LOG ='recent_dirs.json'				# файл с реестром последних открытых каталогов
TEMPLATE_PROJECT_FILE = 'template_project.json'		# файл с указанием пути к проекту-шаблону

AUTHOR = r'https://github.com/OldNestling'			# Страница автора на GitHub
GITHUB = r'https://github.com/OldNestling/ONP-Bill_of_Quantities.git'	# Репозиторий

ABOUT = 'Программа создана для автоматизированного формирования ведомости объемов работ в формате XML-схемы,' \
		' утвержденной Минстроем, с акцентом на применение в дорожно-строительной области.'

PARTICIPANTS ='''<p "align" = "left"> \
			<b>Участники проекта:</b><br> \
			<i>OldNestling</i>: разработка архитектуры, интерфейса, стандарта, написание кода и раннее прототипирование<br> \
			<i>Хощенко А.О.</i>: раннее прототипирование, разработка стандарта, отдельных алгоритмов и логики вкладок «Грунты»
			 и «Источники и транспортировка», тестирование и многократная поломка программы
			</p>'''

SUPPORT_PLEASE =(
			"<i>Программа создана за спасибо.<br>"
			"Более весомая благодарность стимулирует разработчика "
			"поддерживать продукт :)</i>"
)

TUTORIAL = (
	f'<b>Справочная информация: </b>'
	f'<a href="{GITHUB}" style="color: #3B82F6; '
	f'text-decoration: none;">{GITHUB}</a>'
)

COMMUNICATION_AND_RECEIPTS = (
	f'<b>Связь с разработчиком: </b>'
	f'<a href="mailto:oldnestling@yandex.ru" style="color: #3B82F6; '
	f'text-decoration: none;">oldnestling@yandex.ru</a>'
	f'<br><b>Telegram-канал: </b>'
	f'<a href="https://t.me/old_nestling_projects" style="color: #3B82F6; '
	f'text-decoration: none;">Old Nestling\'s Projects</a>'
	f'<br><b>Номер карты для благодарности: </b>'
	f'<a href="https://www.tinkoff.ru/rm/r_aOqwUwfbRm.lZNlrKjSLm/oMI8k46003" '
	f'style="color: #3B82F6; text-decoration: none;">'
	f'2200 7004 2212 0336</a>'
)
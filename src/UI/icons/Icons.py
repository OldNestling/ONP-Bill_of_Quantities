# Copyright © 2026 OldNestling

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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


from PyQt6.QtGui import QIcon, QPixmap, QTransform, QPainter, QColor
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem, QApplication
from Core.Utilities import resource_path


help = QIcon(resource_path('UI/icons/icon_help.svg'))						# Справка

folder_open = QIcon(resource_path('UI/icons/icon_folder_open.svg'))			# Открыть папку

database = QIcon(resource_path('UI/icons/icon_database.svg'))				# база данных
edit = QIcon(resource_path('UI/icons/icon_edit.svg'))						# редактировать
save = QIcon(resource_path('UI/icons/icon_save.svg'))						# сохранить
save_as = QIcon(resource_path('UI/icons/icon_save_as.svg'))					# созранить как

reload = QIcon(resource_path('UI/icons/icon_reload.svg'))					# перезагрузить
reopen = QIcon(resource_path('UI/icons/icon_reopen_window.svg'))			# открыть повторно
refresh = QIcon(resource_path('UI/icons/icon_screen_rotation_alt.svg'))		# освежить

add = QIcon(resource_path('UI/icons/icon_add.svg'))							# добавить
remove = QIcon(resource_path('UI/icons/icon_remove.svg'))					# удалить
unlock = QIcon(resource_path('UI/icons/icon_lock_open.svg'))				# разблокировать
lock = QIcon(resource_path('UI/icons/icon_lock.svg'))						# заблокировать

note_add = QIcon(resource_path('UI/icons/icon_note_add.svg'))				# добавить заметку
file_open = QIcon(resource_path('UI/icons/icon_file_open.svg'))				# открыть файл
delete = QIcon(resource_path('UI/icons/icon_delete.svg'))					# удалить
edit_document = QIcon(resource_path('UI/icons/icon_edit_document.svg'))		# редактировать документ
merge = QIcon(resource_path('UI/icons/icon_merge.svg'))						# объеденить

download = QIcon(resource_path('UI/icons/icon_download.svg'))				# загрузить
upload = QIcon(resource_path('UI/icons/icon_upload.svg'))					# выгрузть

move_up = QIcon(resource_path('UI/icons/icon_move_up.svg'))					# переместить вверх
move_down = QIcon(resource_path('UI/icons/icon_move_down.svg'))				# переместить вниз
move_item = QIcon(resource_path('UI/icons/icon_move_item.svg'))				# сбросить в архив
move_right = QIcon(resource_path('UI/icons/icon_double_arrow.svg'))			# Переместить вправо

cut = QIcon(resource_path('UI/icons/icon_content_cut.svg'))					# вырезать
copy = QIcon(resource_path('UI/icons/icon_content_copy.svg'))				# копировать
paste = QIcon(resource_path('UI/icons/icon_content_paste.svg'))				# вставить

close_tab = QIcon(resource_path('UI/icons/icon_tab_close.svg')) 			# закрыть вкладку
close = QIcon(resource_path('UI/icons/icon_close.svg')) 					# закрыть вкладку

undo = QIcon(resource_path('UI/icons/icon_undo.svg'))						# отменить
redo = QIcon(resource_path('UI/icons/icon_redo.svg'))						# вернуть

add_ad = QIcon(resource_path('UI/icons/icon_add_ad.svg'))					# Добавить раздел
add_box = QIcon(resource_path('UI/icons/icon_add_box.svg'))					# Добавить работу
add_triangle = QIcon(resource_path('UI/icons/icon_add_triangle.svg'))		# Добавить работу

fill_color = QIcon(resource_path('UI/icons/icon_format_color_fill.svg')) 	# залить фон
color_text = QIcon(resource_path('UI/icons/icon_format_color_text.svg')) 	# закрасить шрифт
eraser_off = QIcon(resource_path('UI/icons/icon_ink_eraser_off_.svg'))  	# сбросить формат

done = QIcon(resource_path('UI/icons/icon_check.svg'))  					# отработано
done_all = QIcon(resource_path('UI/icons/icon_done_all.svg'))  				# осметчино
reset_status = QIcon(resource_path('UI/icons/icon_block.svg'))  			# сброс статусов
status = QIcon(resource_path('UI/icons/icon_check_circle.svg'))

expande = QIcon(resource_path('UI/icons/icon_expand.svg'))  				# развернеть
compress = QIcon(resource_path('UI/icons/icon_compress.svg')) 				# свернуть

calculate = QIcon(resource_path('UI/icons/icon_calculate.svg'))				# калькулятор

road_add = QIcon(resource_path('UI/icons/icon_add_road.svg'))				# Дорожная конструкция
excavator = QIcon(resource_path('UI/icons/icon_excavator.svg'))
material = QIcon(resource_path('UI/icons/icon_landslide.svg'))				# Материал
template = QIcon(resource_path('UI/icons/icon_wysiwyg.svg'))				# Шаблон
layers = QIcon(resource_path('UI/icons/icon_layers.svg'))					# Слои

checklist = QIcon(resource_path('UI/icons/icon_checklist.svg'))				# Чеклист
attach = QIcon(resource_path('UI/icons/icon_attach_file_add.svg'))			# Вложение
log_list = QIcon(resource_path('UI/icons/icon_clock_arrow_down.svg'))		# Логлист
data_table = QIcon(resource_path('UI/icons/icon_data_table.svg'))			# Содержание
edit_note = QIcon(resource_path('UI/icons/icon_edit_note.svg'))				# Заметка

find = QIcon(resource_path('UI/icons/icon_search_check_2.svg'))	

up_arrow = QIcon(resource_path('UI/icons/icon_upgrade.svg'))	
down_arrow = QIcon(resource_path('UI/icons/icon_vertical_align_bottom.svg'))	

def rotate_icon(icon: QIcon, angle: float, size: QSize = QSize(24, 24)) -> QIcon:
	"""
	Возвращает новый QIcon, повёрнутый на заданный угол (градусы).
	size — размер, который используется для получения pixmap из исходной иконки.
	"""
	rotated_icon = QIcon()
	for mode in (QIcon.Mode.Normal, QIcon.Mode.Disabled, QIcon.Mode.Active, QIcon.Mode.Selected):
		for state in (QIcon.State.On, QIcon.State.Off):
			pixmap = icon.pixmap(size, mode, state)
			if not pixmap.isNull():
				transform = QTransform().rotate(angle)
				rotated_pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
				rotated_icon.addPixmap(rotated_pixmap, mode, state)
	return rotated_icon


def recolor_icon(icon: QIcon, color: QColor, size: QSize = QSize(24, 24)) -> QIcon:
	"""
	Возвращает новый QIcon, перекрашенный в указанный цвет.
	Исходная икона должна быть монохромной (лучше всего – белый рисунок на прозрачном фоне).
	"""
	new_icon = QIcon()
	for mode in (QIcon.Mode.Normal, QIcon.Mode.Disabled, QIcon.Mode.Active, QIcon.Mode.Selected):
		for state in (QIcon.State.On, QIcon.State.Off):
			pixmap = icon.pixmap(size, mode, state)
			if not pixmap.isNull():
				# Создаём новый pixmap того же размера с прозрачным фоном
				colored_pixmap = QPixmap(pixmap.size())
				colored_pixmap.fill(Qt.GlobalColor.transparent)
				
				# Рисуем исходную иконку как маску
				painter = QPainter(colored_pixmap)
				painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
				painter.drawPixmap(0, 0, pixmap)
				# Применяем цвет: исходные пиксели (непрозрачные) закрашиваем новым цветом
				painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
				painter.fillRect(colored_pixmap.rect(), color)
				painter.end()
				
				new_icon.addPixmap(colored_pixmap, mode, state)
	return new_icon



class AdaptiveIconDelegate(QStyledItemDelegate):
	def paint(self, painter, option, index):
		original_icon = index.data(Qt.ItemDataRole.DecorationRole)
		if original_icon and isinstance(original_icon, QIcon):
			# Цвет фона элемента (не окна)
			bg_color = option.palette.base().color()
			brightness = bg_color.red() * 0.299 + bg_color.green() * 0.587 + bg_color.blue() * 0.114
			target_color = QColor(0, 0, 0) if brightness > 128 else QColor(255, 255, 255)

			# Получаем стандартный размер иконки для данного стиля
			icon_size = option.widget.style().pixelMetric(
				QStyle.PixelMetric.PM_SmallIconSize, option, option.widget
			)
			size = QSize(icon_size, icon_size)

			# Берём pixmap исходной иконки нужного размера
			pixmap = original_icon.pixmap(size)
			if pixmap.isNull():
				# Если нет, пробуем размер 24x24
				pixmap = original_icon.pixmap(QSize(24, 24))
			if not pixmap.isNull():
				# Масштабируем до нужного размера
				pixmap = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
									Qt.TransformationMode.SmoothTransformation)
				# Перекрашиваем pixmap в нужный цвет (сохраняя прозрачность)
				painter.save()
				painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
				painter.fillRect(pixmap.rect(), target_color)
				painter.restore()
				# Рисуем перекрашенную иконку в левой части ячейки
				icon_rect = option.rect
				icon_rect.setLeft(icon_rect.left() + 4)
				icon_rect.setWidth(icon_size)
				icon_rect.setHeight(icon_size)
				# Центрируем по вертикали
				dy = (option.rect.height() - icon_size) // 2
				icon_rect.moveTop(option.rect.top() + dy)
				painter.drawPixmap(icon_rect, pixmap)

				# Рисуем текст и всё остальное, но без оригинальной иконки
				opt = QStyleOptionViewItem(option)
				opt.icon = QIcon()  # убираем иконку, чтобы не рисовалась дважды
				style = opt.widget.style() if opt.widget else QApplication.style()
				style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
				return  # завершаем, чтобы не вызывать super().paint

		super().paint(painter, option, index)
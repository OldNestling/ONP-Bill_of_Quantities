from collections import deque 

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from .BoQ import BoQ_manager 

class HistoryManager:
    """ 
    Субменеджер для основного BoQ_manager, отвечающий за управление откатом прошлых действий 
    """
    def __init__(self, max_size=20):
        self.undo_stack = deque(maxlen=max_size)
        self.redo_stack = deque(maxlen=max_size)

    def add_action(self, action):
        """Добавить новое действие (очищает redo)"""
        self.undo_stack.append(action)
        self.redo_stack.clear()   # новая ветка – сбрасываем возврат

    def undo(self):
        """Отменить последнее действие, вернуть его (для выполнения отката)"""
        if not self.undo_stack:
            return None
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        return action

    def redo(self):
        """Вернуть отменённое действие"""
        if not self.redo_stack:
            return None
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        return action

    def can_undo(self):
        return bool(self.undo_stack)

    def can_redo(self):
        return bool(self.redo_stack)
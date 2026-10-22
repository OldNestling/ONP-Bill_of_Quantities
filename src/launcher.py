# src/launcher.py
import os, sys, json, runpy


def get_base_dir():
	"""Папка, где лежит exe (или сам launcher.py при отладке)."""
	if getattr(sys, 'frozen', False):
		return os.path.dirname(sys.executable)
	return os.path.dirname(os.path.abspath(__file__))


def load_config(base_dir):
	"""Читаем config.json рядом с exe. Если нет — значения по умолчанию."""
	cfg_path = os.path.join(base_dir, "config.json")
	defaults = {
		# Имя папки репозитория (или абсолютный путь).
		"repo_path": "ONP-Bill_of_Quantities",
		# Рабочая директория, которую откроет программа (пусто = корень репо)
		"default_project_path": "",
	}
	if os.path.isfile(cfg_path):
		try:
			with open(cfg_path, "r", encoding="utf-8") as f:
				defaults.update(json.load(f))
		except Exception as e:
			print(f"[launcher] Не удалось прочитать config.json: {e}")
	return defaults


def find_repo_dir(base_dir, repo_path):
	"""
	Ищет корень репозитория (папку, содержащую src/main.py).

	Порядок:
	  1. Если repo_path абсолютный — проверяем его напрямую.
	  2. Иначе поднимаемся от base_dir вверх (до 5 уровней) и на каждом уровне
		 проверяем:
		   a) саму папку уровня (exe уже внутри репозитория);
		   b) подпапку с именем repo_path (exe рядом с репозиторием).

	Возвращает (repo_dir | None, список проверенных путей).
	"""
	repo_name = os.path.basename(os.path.normpath(repo_path)) if repo_path else None

	candidates = []

	def add(p):
		p = os.path.normpath(os.path.abspath(p))
		if p not in candidates:
			candidates.append(p)

	if os.path.isabs(repo_path):
		add(repo_path)
	else:
		current = os.path.abspath(base_dir)
		for _ in range(5):
			add(current)                       # (a) этот уровень — сам репозиторий
			if repo_name:
				add(os.path.join(current, repo_name))  # (b) подпапка с именем репо
			parent = os.path.dirname(current)
			if parent == current:              # достигли корня диска
				break
			current = parent

	checked = []
	for c in candidates:
		checked.append(c)
		if os.path.isfile(os.path.join(c, 'src', 'main.py')):
			return c, checked

	return None, checked


def main():
	base_dir = get_base_dir()
	cfg = load_config(base_dir)

	repo_dir, checked = find_repo_dir(base_dir, cfg["repo_path"])

	if repo_dir is None:
		import tkinter.messagebox as mb
		paths = "\n".join(f"  - {p}" for p in checked)
		mb.showerror(
			"ONP: Система ВОР",
			"Не найден файл src\\main.py.\n\n"
			"Проверены пути:\n"
			f"{paths}\n\n"
			"Проверьте, что каталог ONP-Bill_of_Quantities содержит папку src с main.py,\n"
			"или задайте абсолютный путь в \"repo_path\" в config.json рядом с exe."
		)
		sys.exit(1)

	src_dir = os.path.join(repo_dir, "src")
	main_py = os.path.join(src_dir, "main.py")

	# 1. src в sys.path — чтобы работали импорты Core, UI и т.д.
	if src_dir not in sys.path:
		sys.path.insert(0, src_dir)

	# 2. Рабочая директория.
	work_dir = cfg.get("default_project_path") or repo_dir
	if not os.path.isdir(work_dir):
		work_dir = repo_dir
	os.chdir(work_dir)

	# 3. Аргументы для main.py.
	if cfg.get("default_project_path"):
		sys.argv = [main_py, cfg["default_project_path"]]

	# 4. Запуск.
	runpy.run_path(main_py, run_name="__main__")


if __name__ == "__main__":
	main()
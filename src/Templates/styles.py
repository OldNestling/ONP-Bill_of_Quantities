CSS_SETTING = """
		QLabel a {
			color: #003D7A;
			text-decoration: none;
		}
		QLabel a:hover {
			text-decoration: underline;
		}
		/* Кнопки */
		QPushButton {
	 		background-color: #45464F;
	 		color: white;
	 		border-radius: 4px;
	 		padding: 6px;
	 	}
	 	QPushButton:hover {
	 		background-color: #0053a6;
	 	}	
	 	QPushButton:pressed {
	 		background-color: #003d80;
	 	}
	 	QPushButton:disabled {
	 		background-color: #3a3a3a;
	 		color: #a0a0a0;
	 	}
	 	QGroupBox {
	 		border: 1px solid #9f9f9f;
	 		border-radius: 5px;
	 		margin-top: 1ex;
	 		padding-top: 8px;
	 		font-weight: bold;
	 	}
	 	QGroupBox::title {
	 		subcontrol-origin: margin;
	 		left: 10px;
	 		padding: 0 5px;
	 	}	
	 	/* ===================== Скроллбары (упрощённые) ===================== */
	 	QScrollBar:vertical {
	 		border: none;
	 		background: #9F9F9F;
	 		width: 8px;
	 		margin: 0px;
	 		border-radius: 4px;
	 	}
	 	QScrollBar::handle:vertical {
	 		background: #45464f;
	 		min-height: 20px;
	 		border-radius: 4px;
	 	}
	 	QScrollBar::handle:vertical:hover {
	 		background: #7a7a7a;
	 	}
	 	QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
	 		border: none;
	 		background: none;
	 		height: 0px;
	 	}
	 	QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
	 		background: none;
	 	}

	 	QScrollBar:horizontal {
	 		border: none;
	 		background: #9F9F9F;
	 		height: 8px;
	 		margin: 0px;
	 		border-radius: 4px;
	 	}
	 	QScrollBar::handle:horizontal {
	 		background: #45464f;
	 		min-width: 20px;
	 		border-radius: 4px;
	 	}
	 	QScrollBar::handle:horizontal:hover {
	 		background: #7a7a7a;
	 	}
	 	QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
	 		border: none;
	 		background: none;
	 		width: 0px;
	 	}
	 	QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
	 		background: none;
	 	}   
	 	/* ===================== Текстовые поля ===================== */
	 	QLineEdit, QPlainTextEdit, QTextEdit {
	 		border: 1px solid #3a3a3a;
	 		border-radius: 3px;
	 		padding: 2px;
	 		selection-background-color: #0053a6;
			color: #000000;
			background: #ffffff;
	 	}
	 	QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
	 		border: 1px solid #0053a6;
	 	}
		QLineEdit::placeholder, QPlainTextEdit::placeholder, QTextEdit::placeholder {
			color: #808080;
			font-style: italic;
		}	   
	 	/* ===================== Выпадающие списки ===================== */
	 	QComboBox {
	 		border: 1px solid #3a3a3a;
	 		border-radius: 3px;
	 		padding: 4px;
	 	}
	 	QComboBox:hover {
	 		border-color: #0053a6;
	 	}

	 	QComboBox QAbstractItemView {
	 		selection-background-color: #0053a6;
	 		selection-color: white;
	 		border: 1px solid #45464f;
	 	}
	 	QTabWidget::pane {
	 		border: 1px solid #c0c0c0;
	 		background-color: #ffffff;
	 		margin-top: -1px;
	 	}
	 	QTabBar::tab {
	 		border: 1px solid #c0c0c0;
	 		border-bottom: none;
	 		border-top-left-radius: 4px;
	 		border-top-right-radius: 4px;
	 		padding: 4px 8px;
	 		margin-right: 2px;
	 		margin-bottom: -1px;
	 		background-color: #f5f5f5;
	 	}
	 	QTabBar::tab:selected {
	 		border-bottom: 1px solid #ffffff;
	 		background-color: #ffffff;
	 		margin-bottom: -2px;
	 	}
	 	QTabBar::tab:hover:!selected {
	 		background-color: #e0e0e0;
	 	}


	 	QTableWidget, QTreeView {
	 		border: 1px solid #c0c0c0;
	 		border-radius: 4px;
	 		background-color: #ffffff;
	 	}
	 	/* ===================== Контекстное меню ===================== */
	 	QMenu {
	 		background-color: #ffffff;
	 		border: 1px solid #c0c0c0;
	 		border-radius: 6px;
	 		padding: 4px 0px;
	 	}
	 	QMenu::item {
	 		background-color: transparent;
	 		color: #1e1e1e;
	 		padding: 6px 24px 6px 20px;
	 		margin: 2px 4px;
	 		border-radius: 4px;
	 	}
	 	QMenu::item:selected {
	 		background-color: #0053a6;
	 		color: white;
	 	}
	 	QMenu::separator {
	 		height: 1px;
	 		background-color: #e0e0e0;
	 		margin: 4px 8px;
	 	}
	 	/* ================= Панель инструментов ===================== */
	 	QToolBar {
	 		background-color: #f5f5f5;
	 		border: 1px solid #c0c0c0;
	 		border-radius: 5px;
	 		spacing: 4px;
	 		padding: 4px;
	 	}
	 	QToolBar QToolButton {
	 		background-color: #5A565F;
	 		border: none;
	 		border-radius: 4px;
	 		padding: 4px;
	 	}
	 	QToolBar QToolButton:hover {
	 		background-color: #0053a6;
	 	}
	 	QToolBar QToolButton:pressed {
	 		background-color: #003d80;
	 	}
	 	QToolBar QToolButton:disabled {
	 		background-color: transparent;
	 	}
	 	/* ================= Прочее ===================== */
	 	QFrame[class="panel"] {
	 		background: #f5f5f5;
	 		border: 1px solid #d0d0d0;
	 		border-radius: 4px;
	 	}
		/* ================= Заголовки таблиц и деревьев ================= */
		QHeaderView::section {
			background-color: #f0f0f0;
			border: 1px solid #a0a0a0;
			border-left: none;
			border-top: none;
			padding: 4px;
			font-weight: bold;
		}
		QHeaderView::section:horizontal {
			border-bottom: 1px solid #a0a0a0;
		}
		QHeaderView::section:vertical {
			border-right: 1px solid #a0a0a0;
		}
		/* Убираем двойные границы на пересечении */
		QTableCornerButton::section {
			background-color: #f0f0f0;
			border: 1px solid #a0a0a0;
			border-left: none;
			border-top: none;
		}
		/* Для QTreeView – дополнительные границы ячеек (опционально) */
		QTreeView::item {
			border-bottom: 1px solid #d0d0d0;
			padding: 2px;
		}
		QTreeView::item:selected {
			background-color: #0053a6;
			color: white;
		}
		/* Если нужно выделение заголовка при наведении */
		QHeaderView::section:hover {
			background-color: #e0e0e0;
		}
		/* ================= Принудительная светлая тема для ComboBox (особенно Win11) ================= */
		QComboBox {
			background-color: #ffffff;
			color: #000000;
			border: 1px solid #3a3a3a;
			border-radius: 3px;
			padding: 4px;
		}
		QComboBox:editable {
			background-color: #ffffff;
		}
		QComboBox:!editable {
			background-color: #ffffff;
		}
		/* Выпадающий список */
		QComboBox QAbstractItemView {
			background-color: #ffffff;
			color: #000000;
			selection-background-color: #0053a6;
			selection-color: #ffffff;
			border: 1px solid #45464f;
			outline: 0;
		}
		QComboBox QAbstractItemView::item {
			background-color: #ffffff;
			color: #000000;
			padding: 4px;
		}
		QComboBox QAbstractItemView::item:selected {
			background-color: #0053a6;
			color: #ffffff;
		}
		QComboBox QAbstractItemView::item:hover {
			background-color: #e0e0e0;
			color: #000000;
		}
		/* ===================== QToolBox ===================== */
		QToolBox {
			border: 1px solid #c0c0c0;
			border-radius: 4px;
			background-color: #ffffff;
		}
		QToolBox::tab {
			background-color: #5F6175;
			color: white;
			border-radius: 4px;
			font-weight: bold;
		}
		QToolBox::tab:selected {
			background-color: #0053a6;
		}
		QToolBox::tab:hover:!selected {
			background-color: #0053a6;
		}
		QToolBox::tab:pressed {
			background-color: #003d80;
		}
		QToolBox::pane {
			border-top: 1px solid #c0c0c0;
			background-color: #ffffff;
			padding: 4px;
		}
		/* ===================== QCheckBox ===================== */
		QCheckBox {
			spacing: 8px;
			color: #1e1e1e;
			font-weight: normal;
		}
		QCheckBox:disabled {
			color: #a0a0a0;
		}
		QCheckBox:focus {
			outline: none;
		}
	
	 	"""


	# пока не удаётся настроить стрелки для числовых полей, временно отключил переопредление
	#/* ===================== QSpinBox, QDoubleSpinBox ===================== */

	#	QSpinBox, QDoubleSpinBox {
	#		border: 1px solid #3a3a3a;
	#		border-radius: 3px;
	#		padding: 4px;
	#		background-color: #ffffff;
	#		color: #000000;
	#		min-height: 22px;
	#	}
	#	QSpinBox:focus, QDoubleSpinBox:focus {
	#		border: 1px solid #0053a6;
	#	}
	#	QSpinBox::up-button, QDoubleSpinBox::up-button {
	#		subcontrol-origin: border;
	#		subcontrol-position: top right;
	#		width: 16px;
	#		height: 50%;
	#		background-color: #f0f0f0;
	#		border-left: 1px solid #3a3a3a;
	#		border-bottom: 1px solid #3a3a3a;
	#		border-top-right-radius: 3px;
	#	}
	#	QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
	#		background-color: #e0e0e0;
	#	}
	#	QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {
	#		background-color: #d0d0d0;
	#	}
	#	QSpinBox::down-button, QDoubleSpinBox::down-button {
	#		subcontrol-origin: border;
	#		subcontrol-position: bottom right;
	#		width: 16px;
	#		height: 50%;
	#		background-color: #f0f0f0;
	#		border-left: 1px solid #3a3a3a;
	#		border-top: 1px solid #3a3a3a;
	#		border-bottom-right-radius: 3px;
	#	}
	#	QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
	#		background-color: #e0e0e0;
	#	}
	#	QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
	#		background-color: #d0d0d0;
	#	}
	#	/* Стрелки через inline SVG (без внешних файлов) */
	#	QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
	#		width: 10px;
	#		height: 10px;
	#		image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpolygon points='5,2 2,8 8,8' fill='%23333333'/%3E%3C/svg%3E");
	#	}
	#	QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
	#		width: 10px;
	#		height: 10px;
	#		image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpolygon points='5,8 2,2 8,2' fill='%23333333'/%3E%3C/svg%3E");
	#	}

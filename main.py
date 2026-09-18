import sys
import os
import json
import re
from spellchecker import SpellChecker

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QColorDialog, QFontDialog,
    QFileDialog, QWidget, QVBoxLayout, QDialog, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QMessageBox, QListWidget, QListWidgetItem,
    QSplitter, QStackedWidget, QCheckBox, QInputDialog, QAbstractItemView,
    QMenu, QStatusBar
)
from PyQt6.QtGui import QAction, QColor, QFont, QTextCursor, QTextCharFormat, QSyntaxHighlighter
from PyQt6.QtCore import Qt, QSize, QVariantAnimation, QEasingCurve


SESSION_FILE = "session.json"
spell_engine = SpellChecker()


class SpellHighlighter(QSyntaxHighlighter):
    """Customizable spellchecker backed by PySpellChecker."""
    def __init__(self, parent=None, underline_color="#FF453A"):
        super().__init__(parent)
        self.enabled = True
        self.underline_color = QColor(underline_color)
        self.user_dictionary = set()

    def set_underline_color(self, color_hex: str):
        self.underline_color = QColor(color_hex)
        self.rehighlight()

    def add_user_word(self, word: str):
        self.user_dictionary.add(word.lower())
        spell_engine.word_frequency.add(word.lower())
        self.rehighlight()

    def remove_user_word(self, word: str):
        self.user_dictionary.discard(word.lower())
        self.rehighlight()

    def highlightBlock(self, text):
        if not self.enabled:
            return

        fmt = QTextCharFormat()
        fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        fmt.setUnderlineColor(self.underline_color)

        for match in re.finditer(r'\b[A-Za-z]+\b', text):
            word = match.group()
            word_lower = word.lower()
            
            if len(word) > 1 and word_lower not in self.user_dictionary:
                if word_lower in spell_engine.unknown([word_lower]):
                    self.setFormat(match.start(), match.end() - match.start(), fmt)


class DictionaryManagerDialog(QDialog):
    """Dialog to add, edit, and remove custom dictionary words."""
    def __init__(self, main_app):
        super().__init__(main_app)
        self.main_app = main_app
        self.setWindowTitle("Custom Dictionary Manager")
        self.setFixedSize(380, 420)

        self.setStyleSheet("""
            QDialog { background-color: #1C1C1E; color: #F2F2F7; }
            QLabel { color: #8E8E93; font-size: 12px; font-weight: 500; }
            QListWidget {
                background-color: #2C2C2E; color: #F2F2F7;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px; padding: 4px; outline: none;
            }
            QListWidget::item { border-radius: 6px; padding: 6px; }
            QListWidget::item:selected { background-color: #0A84FF; color: #FFFFFF; }
            QPushButton {
                background-color: #2C2C2E; color: #0A84FF;
                border: none; border-radius: 8px;
                padding: 6px 12px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background-color: #3A3A3C; }
            QPushButton:pressed { background-color: #0A84FF; color: #FFFFFF; }
            QPushButton#delete_btn { color: #FF453A; }
            QPushButton#delete_btn:hover { background-color: rgba(255, 69, 58, 0.2); }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("User Dictionary Words:"))

        self.word_list = QListWidget()
        layout.addWidget(self.word_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.add_btn = QPushButton("➕ Add")
        self.edit_btn = QPushButton("✏️ Edit")
        self.delete_btn = QPushButton("🗑️ Remove")
        self.delete_btn.setObjectName("delete_btn")

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self.add_word)
        self.edit_btn.clicked.connect(self.edit_word)
        self.delete_btn.clicked.connect(self.delete_word)

        self.populate_words()

    def populate_words(self):
        self.word_list.clear()
        for word in sorted(self.main_app.custom_dictionary):
            self.word_list.addItem(word)

    def add_word(self):
        word, ok = QInputDialog.getText(self, "Add Word", "Enter word to add:")
        if ok and word.strip():
            self.main_app.add_word_to_all_highlighters(word.strip().lower())
            self.populate_words()

    def edit_word(self):
        current_item = self.word_list.currentItem()
        if not current_item:
            return
        old_word = current_item.text()
        new_word, ok = QInputDialog.getText(self, "Edit Word", "Modify word:", text=old_word)
        if ok and new_word.strip() and new_word.strip().lower() != old_word:
            self.main_app.remove_word_from_all_highlighters(old_word)
            self.main_app.add_word_to_all_highlighters(new_word.strip().lower())
            self.populate_words()

    def delete_word(self):
        current_item = self.word_list.currentItem()
        if not current_item:
            return
        word = current_item.text()
        self.main_app.remove_word_from_all_highlighters(word)
        self.populate_words()


class TabItemWidget(QWidget):
    def __init__(self, title, on_close_callback):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(6)

        self.label = QLabel(title)
        self.label.setFont(QFont("SF Pro Text", 10) if sys.platform == "darwin" else QFont("Segoe UI", 10))
        self.label.setStyleSheet("color: #F2F2F7; border: none; font-weight: 500;")

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(235, 235, 245, 0.35);
                border: none;
                font-size: 11px;
                font-weight: bold;
                border-radius: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 69, 58, 0.85);
                color: #FFFFFF;
            }
        """)
        self.close_btn.clicked.connect(on_close_callback)

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.close_btn)
        self.setLayout(layout)

    def set_title(self, title):
        self.label.setText(title)


class FindReplaceDialog(QDialog):
    def __init__(self, main_app, editor: QTextEdit):
        super().__init__(main_app)
        self.main_app = main_app
        self.editor = editor
        self.setWindowTitle("Find & Replace")
        self.setFixedSize(400, 200)

        self.setStyleSheet("""
            QDialog { background-color: #1C1C1E; color: #F2F2F7; }
            QLabel { color: #8E8E93; font-size: 12px; font-weight: 500; }
            QLineEdit {
                background-color: #2C2C2E; color: #F2F2F7;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px; padding: 6px 10px;
                selection-background-color: #0A84FF;
            }
            QLineEdit:focus { border: 1px solid #0A84FF; }
            QCheckBox { color: #F2F2F7; font-size: 12px; }
            QPushButton {
                background-color: #2C2C2E; color: #0A84FF;
                border: none; border-radius: 8px;
                padding: 6px 12px; font-weight: 600;
            }
            QPushButton:hover { background-color: #3A3A3C; }
            QPushButton:pressed { background-color: #0A84FF; color: #FFFFFF; }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:   "))
        self.find_input = QLineEdit()
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)

        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)

        self.all_files_cb = QCheckBox("Search across all open files")
        layout.addWidget(self.all_files_cb)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.find_btn = QPushButton("Find Next")
        self.replace_btn = QPushButton("Replace")
        self.replace_all_btn = QPushButton("Replace All")

        btn_layout.addWidget(self.find_btn)
        btn_layout.addWidget(self.replace_btn)
        btn_layout.addWidget(self.replace_all_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.find_btn.clicked.connect(self.find_text)
        self.replace_btn.clicked.connect(self.replace_text)
        self.replace_all_btn.clicked.connect(self.replace_all)

    def find_text(self):
        text = self.find_input.text()
        if not text:
            return False

        if not self.all_files_cb.isChecked():
            editor = self.main_app.get_current_editor()
            if editor and editor.find(text):
                return True
            QMessageBox.information(self, "Find", f"'{text}' not found.")
            return False

        start_idx = self.main_app.tab_list.currentRow()
        total_tabs = len(self.main_app.tabs_data)

        current_ed = self.main_app.tabs_data[start_idx]["widget"]
        if current_ed.find(text):
            return True

        for offset in range(1, total_tabs + 1):
            target_idx = (start_idx + offset) % total_tabs
            ed = self.main_app.tabs_data[target_idx]["widget"]
            ed.moveCursor(QTextCursor.MoveOperation.Start)
            if ed.find(text):
                self.main_app.tab_list.setCurrentRow(target_idx)
                self.main_app.switch_tab(target_idx)
                ed.setFocus()
                return True

        QMessageBox.information(self, "Find", f"'{text}' not found in any open file.")
        return False

    def replace_text(self):
        editor = self.main_app.get_current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
            self.find_text()
        else:
            if self.find_text():
                cursor = self.main_app.get_current_editor().textCursor()
                cursor.insertText(self.replace_input.text())

    def replace_all(self):
        text = self.find_input.text()
        replace = self.replace_input.text()
        if not text:
            return

        target_editors = [t["widget"] for t in self.main_app.tabs_data] if self.all_files_cb.isChecked() else [self.main_app.get_current_editor()]
        for ed in target_editors:
            if ed:
                content = ed.toPlainText().replace(text, replace)
                ed.setPlainText(content)


class ModernNotesApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notes")
        self.setGeometry(100, 100, 980, 680)

        self.current_bg_color = "#000000"
        self.selection_bg_color = "#0A84FF"
        self.spell_color = "#FF453A"
        self.sidebar_width = 240
        self.sidebar_collapsed = False
        self.custom_dictionary = set()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)

        self.sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍  Search all notes...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.07);
                color: #F2F2F7;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px; padding: 6px 10px; font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #0A84FF;
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        self.search_bar.textChanged.connect(self.filter_notes_by_search)

        self.new_tab_btn = QPushButton("+  New Note")
        self.new_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #0A84FF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px; padding: 8px 12px;
                font-size: 13px; font-weight: 600; text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(10, 132, 255, 0.15);
                border: 1px solid rgba(10, 132, 255, 0.3);
            }
            QPushButton:pressed { background-color: #0A84FF; color: #FFFFFF; }
        """)
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab())

        self.tab_list = QListWidget()
        self.tab_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tab_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tab_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tab_list.currentRowChanged.connect(self.switch_tab)
        self.tab_list.model().rowsMoved.connect(self.sync_tabs_on_reorder)

        sidebar_layout.addWidget(self.search_bar)
        sidebar_layout.addWidget(self.new_tab_btn)
        sidebar_layout.addWidget(self.tab_list)
        self.sidebar_container.setLayout(sidebar_layout)

        self.editor_stack = QStackedWidget()

        self.splitter.addWidget(self.sidebar_container)
        self.splitter.addWidget(self.editor_stack)
        self.splitter.setSizes([self.sidebar_width, 740])

        self.setCentralWidget(self.splitter)

        self.highlighters = []
        self.tabs_data = []

        self.create_status_bar()
        self.create_menu_bar()
        self.apply_theme()
        self.load_session()

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_line_col = QLabel("Ln 1, Col 1")
        self.status_char_count = QLabel("0 characters")
        self.status_file_type = QLabel("Plain text")

        for lbl in (self.status_line_col, self.status_char_count, self.status_file_type):
            lbl.setStyleSheet("color: #8E8E93; font-size: 11px; padding: 0 8px;")

        self.status_bar.addWidget(self.status_line_col)
        self.status_bar.addWidget(self.status_char_count)
        self.status_bar.addWidget(self.status_file_type)

    def update_status_bar(self):
        editor = self.get_current_editor()
        if not editor:
            self.status_line_col.setText("Ln 1, Col 1")
            self.status_char_count.setText("0 characters")
            return

        cursor = editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.status_line_col.setText(f"Ln {line}, Col {col}")

        total_chars = len(editor.toPlainText())
        if cursor.hasSelection():
            selected_chars = len(cursor.selectedText())
            self.status_char_count.setText(f"{selected_chars} of {total_chars} characters")
        else:
            self.status_char_count.setText(f"{total_chars} characters")

    def sync_tabs_on_reorder(self, parent, start, end, destination, row):
        if start == row or start == row - 1:
            return
        dest = row if row < start else row - 1
        item = self.tabs_data.pop(start)
        self.tabs_data.insert(dest, item)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #000000; }
            QMenuBar {
                background-color: #1C1C1E; color: #F2F2F7;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                padding: 3px 8px; font-size: 13px; font-weight: 500;
            }
            QMenuBar::item { background-color: transparent; padding: 6px 12px; border-radius: 6px; }
            QMenuBar::item:selected { background-color: rgba(255, 255, 255, 0.08); }
            QMenuBar::item:pressed { background-color: rgba(10, 132, 255, 0.25); }
            QMenu {
                background-color: #2C2C2E; color: #F2F2F7;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px; padding: 6px;
            }
            QMenu::item { padding: 6px 24px; border-radius: 6px; font-size: 13px; }
            QMenu::item:selected { background-color: #0A84FF; color: #FFFFFF; }
            QMenu::separator { height: 1px; background: rgba(255, 255, 255, 0.1); margin: 4px 6px; }
            QListWidget { background-color: #1E1E2E; border: none; border-radius: 10px; outline: none; padding: 2px; }
            QListWidget::item { border-radius: 8px; margin-bottom: 2px; }
            QListWidget::item:hover { background-color: rgba(255, 255, 255, 0.04); }
            QListWidget::item:selected { background-color: rgba(10, 132, 255, 0.22); border: 1px solid rgba(10, 132, 255, 0.4); }
            QSplitter::handle { background-color: rgba(255, 255, 255, 0.08); }
            QStatusBar {
                background-color: #1C1C1E; color: #8E8E93;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)

    def get_current_editor(self) -> QTextEdit:
        return self.editor_stack.currentWidget()

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        new_action = QAction("New Note", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(lambda: self.add_new_tab())
        file_menu.addAction(new_action)

        open_action = QAction("Open Note...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_note)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_note)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_note_as)
        file_menu.addAction(save_as_action)

        save_all_action = QAction("Save All", self)
        save_all_action.setShortcut("Ctrl+Alt+S")
        save_all_action.triggered.connect(self.save_all_notes)
        file_menu.addAction(save_all_action)

        file_menu.addSeparator()

        close_tab_action = QAction("Close Note", self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(lambda: self.close_tab(self.tab_list.currentRow()))
        file_menu.addAction(close_tab_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menu_bar.addMenu("Edit")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(lambda: self.get_current_editor().undo() if self.get_current_editor() else None)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(lambda: self.get_current_editor().redo() if self.get_current_editor() else None)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        find_action = QAction("Find & Replace...", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.open_find_dialog)
        edit_menu.addAction(find_action)

        edit_menu.addSeparator()

        dict_mgr_action = QAction("Manage Custom Dictionary...", self)
        dict_mgr_action.triggered.connect(self.open_dictionary_manager)
        edit_menu.addAction(dict_mgr_action)

        view_menu = menu_bar.addMenu("View")
        toggle_sidebar_action = QAction("Toggle Sidebar", self)
        toggle_sidebar_action.setShortcut("Ctrl+B")
        toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(toggle_sidebar_action)

        view_menu.addSeparator()

        bg_color_action = QAction("Change Canvas Color...", self)
        bg_color_action.triggered.connect(self.change_bg_color)
        view_menu.addAction(bg_color_action)

        selection_color_action = QAction("Selection Highlight Color...", self)
        selection_color_action.triggered.connect(self.change_selection_color)
        view_menu.addAction(selection_color_action)

        spell_color_action = QAction("Spellcheck Underline Color...", self)
        spell_color_action.triggered.connect(self.change_spell_color)
        view_menu.addAction(spell_color_action)

        format_menu = menu_bar.addMenu("Format")
        font_action = QAction("Font Style...", self)
        font_action.triggered.connect(self.change_font)
        format_menu.addAction(font_action)

        text_color_action = QAction("Text Color...", self)
        text_color_action.triggered.connect(self.change_text_color)
        format_menu.addAction(text_color_action)

        format_menu.addSeparator()

        checkbox_action = QAction("Insert iOS Checkbox", self)
        checkbox_action.setShortcut("Ctrl+Shift+C")
        checkbox_action.triggered.connect(self.insert_checkbox)
        format_menu.addAction(checkbox_action)

    def filter_notes_by_search(self, query):
        query = query.lower().strip()
        for index in range(self.tab_list.count()):
            item = self.tab_list.item(index)
            if not query:
                item.setHidden(False)
                continue

            data = self.tabs_data[index]
            editor = data["widget"]
            content = editor.toPlainText().lower()
            title = self.tab_list.itemWidget(item).label.text().lower()

            item.setHidden(not (query in title or query in content))

    def insert_checkbox(self):
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.insertText("◯ ")

    def toggle_checkbox_on_click(self, editor: QTextEdit, event):
        cursor = editor.cursorForPosition(event.pos())
        pos = cursor.position()
        doc = editor.document()
        text = doc.toPlainText()

        for target_pos in (pos, pos - 1):
            if 0 <= target_pos < len(text):
                ch = text[target_pos]
                if ch in ("◯", "◉"):
                    new_ch = "◉" if ch == "◯" else "◯"
                    cursor.setPosition(target_pos)
                    cursor.setPosition(target_pos + 1, QTextCursor.MoveMode.KeepAnchor)
                    cursor.insertText(new_ch)
                    return True
        return False

    def open_dictionary_manager(self):
        dialog = DictionaryManagerDialog(self)
        dialog.exec()

    def add_word_to_all_highlighters(self, word: str):
        self.custom_dictionary.add(word.lower())
        valid_highlighters = []
        for h in self.highlighters:
            try:
                h.add_user_word(word)
                valid_highlighters.append(h)
            except RuntimeError:
                pass
        self.highlighters = valid_highlighters

    def remove_word_from_all_highlighters(self, word: str):
        self.custom_dictionary.discard(word.lower())
        valid_highlighters = []
        for h in self.highlighters:
            try:
                h.remove_user_word(word)
                valid_highlighters.append(h)
            except RuntimeError:
                pass
        self.highlighters = valid_highlighters

    def change_spell_color(self):
        color = QColorDialog.getColor(QColor(self.spell_color), self, "Select Spellcheck Line Color")
        if color.isValid():
            self.spell_color = color.name()
            valid_highlighters = []
            for h in self.highlighters:
                try:
                    h.set_underline_color(self.spell_color)
                    valid_highlighters.append(h)
                except RuntimeError:
                    pass
            self.highlighters = valid_highlighters

    def change_selection_color(self):
        color = QColorDialog.getColor(QColor(self.selection_bg_color), self, "Select Text Selection Color")
        if color.isValid():
            self.selection_bg_color = color.name()
            self.update_editors_style()

    def update_editors_style(self):
        for tab in self.tabs_data:
            editor = tab["widget"]
            editor.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {self.current_bg_color};
                    color: #F2F2F7;
                    border: none;
                    padding: 24px;
                    selection-background-color: {self.selection_bg_color};
                }}
            """)

    def toggle_sidebar(self):
        start_val = self.splitter.sizes()[0]
        end_val = 0 if not self.sidebar_collapsed else self.sidebar_width

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setStartValue(start_val)
        self.anim.setEndValue(end_val)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def step(val):
            total = sum(self.splitter.sizes())
            self.splitter.setSizes([val, total - val])

        self.anim.valueChanged.connect(step)
        self.anim.start()
        self.sidebar_collapsed = not self.sidebar_collapsed

    def show_spelling_menu(self, editor: QTextEdit, pos):
        """Build context menu containing top 3 PySpellChecker suggestions if clicked word is misspelled."""
        cursor = editor.cursorForPosition(pos)
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        selected_word = cursor.selectedText().strip()

        menu = editor.createStandardContextMenu()

        if selected_word and len(selected_word) > 1:
            word_clean = selected_word.lower()
            if word_clean in spell_engine.unknown([word_clean]) and word_clean not in self.custom_dictionary:
                candidates = list(spell_engine.candidates(word_clean) or [])[:3]

                suggestion_actions = []
                for cand in candidates:
                    formatted_cand = cand.capitalize() if selected_word[0].isupper() else cand
                    act = QAction(f"💡 {formatted_cand}", menu)
                    act.triggered.connect(lambda checked=False, c=formatted_cand: cursor.insertText(c))
                    suggestion_actions.append(act)

                add_dict_act = QAction(f"➕ Add '{selected_word}' to Dictionary", menu)
                add_dict_act.triggered.connect(lambda: self.add_word_to_all_highlighters(selected_word))

                first_action = menu.actions()[0] if menu.actions() else None
                for act in reversed(suggestion_actions):
                    menu.insertAction(first_action, act)
                
                menu.insertAction(first_action, add_dict_act)
                if suggestion_actions:
                    menu.insertSeparator(first_action)

        menu.exec(editor.mapToGlobal(pos))

    def create_editor_widget(self, content="") -> QTextEdit:
        editor = QTextEdit()
        editor.setFont(QFont("SF Pro Text", 13) if sys.platform == "darwin" else QFont("Segoe UI", 12))
        editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.current_bg_color};
                color: #F2F2F7;
                border: none;
                padding: 24px;
                selection-background-color: {self.selection_bg_color};
            }}
        """)
        editor.setPlainText(content)

        highlighter = SpellHighlighter(editor.document(), underline_color=self.spell_color)
        for w in self.custom_dictionary:
            highlighter.add_user_word(w)
        self.highlighters.append(highlighter)

        editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        editor.customContextMenuRequested.connect(lambda pos: self.show_spelling_menu(editor, pos))

        editor.cursorPositionChanged.connect(self.update_status_bar)
        editor.selectionChanged.connect(self.update_status_bar)

        original_mouse_press = editor.mousePressEvent

        def mousePressEvent(event):
            if event.button() == Qt.MouseButton.LeftButton:
                if self.toggle_checkbox_on_click(editor, event):
                    return
                cursor = editor.cursorForPosition(event.pos())
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)
                word = cursor.selectedText().strip().lower()

                if word and len(word) > 1 and word in spell_engine.unknown([word]) and word not in self.custom_dictionary:
                    self.show_spelling_menu(editor, event.pos())
                    return

            original_mouse_press(event)

        editor.mousePressEvent = mousePressEvent
        return editor

    def compute_dynamic_title(self, raw_text: str, max_chars: int = 20) -> str:
        lstripped = raw_text.lstrip()
        if not lstripped:
            return "Untitled Note"
        first_line = lstripped.split('\n', 1)[0]
        return first_line[:max_chars] if first_line else "Untitled Note"

    def update_tab_title_from_text(self, editor: QTextEdit):
        index = self.editor_stack.indexOf(editor)
        if index < 0 or index >= len(self.tabs_data):
            return

        data = self.tabs_data[index]
        if data["file_path"]:
            return

        title = self.compute_dynamic_title(editor.toPlainText())

        list_item = self.tab_list.item(index)
        if list_item:
            item_widget = self.tab_list.itemWidget(list_item)
            if item_widget:
                item_widget.set_title(title)

    def add_new_tab(self, title="Untitled Note", file_path=None, content=""):
        editor = self.create_editor_widget(content)
        self.editor_stack.addWidget(editor)

        index = self.tab_list.count()
        tab_data = {"file_path": file_path, "widget": editor}
        self.tabs_data.append(tab_data)

        editor.textChanged.connect(lambda e=editor: self.update_tab_title_from_text(e))

        list_item = QListWidgetItem(self.tab_list)
        list_item.setSizeHint(QSize(0, 38))

        if not file_path:
            title = self.compute_dynamic_title(content)

        item_widget = TabItemWidget(title, lambda idx=index: self.close_tab_by_widget(list_item))
        self.tab_list.addItem(list_item)
        self.tab_list.setItemWidget(list_item, item_widget)

        self.tab_list.setCurrentRow(index)
        self.update_status_bar()

    def switch_tab(self, index):
        if index < 0 or index >= len(self.tabs_data):
            return

        data = self.tabs_data[index]
        file_path = data["file_path"]

        if file_path and not os.path.exists(file_path):
            msg = QMessageBox(self)
            msg.setWindowTitle("File Not Found")
            msg.setText(f"The file at:\n'{file_path}'\nmay have been moved or deleted.")
            msg.setInformativeText("Do you want to remove this tab?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)

            if msg.exec() == QMessageBox.StandardButton.Yes:
                self.close_tab(index)
                return

        self.editor_stack.setCurrentIndex(index)
        self.update_status_bar()

    def close_tab_by_widget(self, item: QListWidgetItem):
        row = self.tab_list.row(item)
        self.close_tab(row)

    def close_tab(self, index):
        if index < 0 or index >= len(self.tabs_data):
            return

        item = self.tab_list.takeItem(index)
        widget = self.tabs_data[index]["widget"]

        doc = widget.document()
        self.highlighters = [h for h in self.highlighters if h.document() != doc]

        self.editor_stack.removeWidget(widget)
        widget.deleteLater()

        del self.tabs_data[index]
        del item

        if len(self.tabs_data) == 0:
            self.add_new_tab()
        else:
            self.update_status_bar()

    def open_find_dialog(self):
        editor = self.get_current_editor()
        if editor:
            dialog = FindReplaceDialog(self, editor)
            dialog.exec()

    def change_font(self):
        editor = self.get_current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        fmt = QTextCharFormat()
        current_font = cursor.charFormat().font()
        font, ok = QFontDialog.getFont(current_font, self)

        if ok:
            fmt.setFont(font)
            cursor.mergeCharFormat(fmt)
            editor.mergeCurrentCharFormat(fmt)

    def change_text_color(self):
        editor = self.get_current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        current_color = cursor.charFormat().foreground().color()

        color = QColorDialog.getColor(current_color, self, "Select Text Color")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            cursor.mergeCharFormat(fmt)
            editor.mergeCurrentCharFormat(fmt)

    def change_bg_color(self):
        color = QColorDialog.getColor(QColor(self.current_bg_color), self, "Select Background Color")
        if color.isValid():
            self.current_bg_color = color.name()
            self.update_editors_style()

    def open_note(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Note", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            filename = os.path.basename(file_path)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.add_new_tab(title=filename, file_path=file_path, content=content)

    def save_note(self):
        index = self.tab_list.currentRow()
        if index < 0:
            return

        data = self.tabs_data[index]
        if not data["file_path"]:
            self.save_note_as()
        else:
            self._write_file(index, data["file_path"])

    def save_note_as(self):
        index = self.tab_list.currentRow()
        if index < 0:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Note As", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self._write_file(index, file_path)

    def save_all_notes(self):
        for index, data in enumerate(self.tabs_data):
            if data["file_path"]:
                self._write_file(index, data["file_path"])
            else:
                file_path, _ = QFileDialog.getSaveFileName(self, f"Save Note {index + 1} As", "", "Text Files (*.txt);;All Files (*)")
                if file_path:
                    self._write_file(index, file_path)

    def _write_file(self, index, file_path):
        data = self.tabs_data[index]
        data["file_path"] = file_path
        filename = os.path.basename(file_path)
        editor = data["widget"]

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(editor.toPlainText())

        list_item = self.tab_list.item(index)
        item_widget = self.tab_list.itemWidget(list_item)
        if item_widget:
            item_widget.set_title(filename)

    def save_session(self):
        session_data = {
            "active_tab": self.tab_list.currentRow(),
            "bg_color": self.current_bg_color,
            "selection_bg_color": self.selection_bg_color,
            "spell_color": self.spell_color,
            "custom_dictionary": list(self.custom_dictionary),
            "tabs": []
        }

        for index, tab in enumerate(self.tabs_data):
            path = tab["file_path"]
            editor = tab["widget"]

            list_item = self.tab_list.item(index)
            item_widget = self.tab_list.itemWidget(list_item)
            title = item_widget.label.text() if item_widget else "Untitled"

            session_data["tabs"].append({
                "title": title,
                "file_path": path,
                "unsaved_text": editor.toPlainText() if not path else ""
            })

        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=4)

    def load_session(self):
        if not os.path.exists(SESSION_FILE):
            self.add_new_tab()
            return

        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            self.current_bg_color = session_data.get("bg_color", "#000000")
            self.selection_bg_color = session_data.get("selection_bg_color", "#0A84FF")
            self.spell_color = session_data.get("spell_color", "#FF453A")
            self.custom_dictionary = set(session_data.get("custom_dictionary", []))

            for w in self.custom_dictionary:
                spell_engine.word_frequency.add(w.lower())

            tabs = session_data.get("tabs", [])

            if not tabs:
                self.add_new_tab()
                return

            for tab in tabs:
                path = tab.get("file_path")
                title = tab.get("title", "Untitled Note")
                content = ""

                if path and os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as file:
                        content = file.read()
                else:
                    content = tab.get("unsaved_text", "")

                self.add_new_tab(title=title, file_path=path, content=content)

            active_index = session_data.get("active_tab", 0)
            if 0 <= active_index < len(self.tabs_data):
                self.tab_list.setCurrentRow(active_index)

        except Exception as e:
            print(f"Failed to load session: {e}")
            self.add_new_tab()

    def closeEvent(self, event):
        self.save_session()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernNotesApp()
    window.show()
    sys.exit(app.exec())
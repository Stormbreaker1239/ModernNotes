import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QColorDialog, QFontDialog,
    QFileDialog, QWidget, QVBoxLayout, QDialog, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QMessageBox, QListWidget, QListWidgetItem,
    QSplitter, QStackedWidget, QFrame
)
from PyQt6.QtGui import QAction, QColor, QFont, QTextCursor, QTextCharFormat
from PyQt6.QtCore import Qt, QSize, QVariantAnimation, QEasingCurve

SESSION_FILE = "session.json"


class TabItemWidget(QWidget):
    """iOS-styled item widget for the sidebar list with hoverable close button."""
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
    """Polished Find and Replace dialog."""
    def __init__(self, parent, editor: QTextEdit):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Find & Replace")
        self.setFixedSize(380, 170)

        self.setStyleSheet("""
            QDialog {
                background-color: #1C1C1E;
                color: #F2F2F7;
            }
            QLabel {
                color: #8E8E93;
                font-size: 12px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: #2C2C2E;
                color: #F2F2F7;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: #0A84FF;
            }
            QLineEdit:focus {
                border: 1px solid #0A84FF;
            }
            QPushButton {
                background-color: #2C2C2E;
                color: #0A84FF;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3A3A3C;
            }
            QPushButton:pressed {
                background-color: #0A84FF;
                color: #FFFFFF;
            }
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
        found = self.editor.find(text)
        if not found:
            self.editor.moveCursor(QTextCursor.MoveOperation.Start)
            found = self.editor.find(text)
            if not found:
                QMessageBox.information(self, "Find", f"'{text}' not found.")
        return found

    def replace_text(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
            self.find_text()
        else:
            if self.find_text():
                cursor = self.editor.textCursor()
                cursor.insertText(self.replace_input.text())

    def replace_all(self):
        text = self.find_input.text()
        replace = self.replace_input.text()
        if text:
            content = self.editor.toPlainText().replace(text, replace)
            self.editor.setPlainText(content)


class ModernNotesApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notes")
        self.setGeometry(100, 100, 980, 680)

        self.current_bg_color = "#000000"
        self.sidebar_width = 240
        self.sidebar_collapsed = False

        # Main Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)

        # --- Sidebar Setup ---
        self.sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        # New Note Button
        self.new_tab_btn = QPushButton("+  New Note")
        self.new_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #0A84FF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(10, 132, 255, 0.15);
                border: 1px solid rgba(10, 132, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: #0A84FF;
                color: #FFFFFF;
            }
        """)
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab())

        # Sidebar Notes List
        self.tab_list = QListWidget()
        self.tab_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tab_list.currentRowChanged.connect(self.switch_tab)

        sidebar_layout.addWidget(self.new_tab_btn)
        sidebar_layout.addWidget(self.tab_list)
        self.sidebar_container.setLayout(sidebar_layout)

        # --- Editor Canvas Stage ---
        self.editor_stack = QStackedWidget()

        self.splitter.addWidget(self.sidebar_container)
        self.splitter.addWidget(self.editor_stack)
        self.splitter.setSizes([self.sidebar_width, 740])

        self.setCentralWidget(self.splitter)

        self.create_menu_bar()
        self.apply_theme()

        self.tabs_data = []
        self.load_session()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #000000;
            }
            QMenuBar {
                background-color: #1C1C1E;
                color: #F2F2F7;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                padding: 2px 6px;
                font-size: 13px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
                border-radius: 6px;
            }
            QMenuBar::item:selected {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QMenu {
                background-color: #2C2C2E;
                color: #F2F2F7;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 22px;
                border-radius: 6px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #0A84FF;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.1);
                margin: 4px 6px;
            }
            QListWidget {
                background-color: #1E1E2E;
                border: none;
                border-radius: 10px;
                outline: none;
                padding: 2px;
            }
            QListWidget::item {
                border-radius: 8px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.04);
            }
            QListWidget::item:selected {
                background-color: rgba(10, 132, 255, 0.22);
                border: 1px solid rgba(10, 132, 255, 0.4);
            }
            QSplitter::handle {
                background-color: rgba(255, 255, 255, 0.08);
            }
        """)

    def get_current_editor(self) -> QTextEdit:
        return self.editor_stack.currentWidget()

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # Sidebar Toggle
        toggle_action = QAction("☰", self)
        toggle_action.setToolTip("Toggle Sidebar (Ctrl+B)")
        toggle_action.setShortcut("Ctrl+B")
        toggle_action.triggered.connect(self.toggle_sidebar)
        menu_bar.addAction(toggle_action)

        # FILE MENU
        file_menu = menu_bar.addMenu("File")

        new_action = QAction("New Note Tab", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(lambda: self.add_new_tab())
        file_menu.addAction(new_action)

        open_action = QAction("Open File...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_note)
        file_menu.addAction(open_action)

        save_action = QAction("Save Note", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_note)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        close_tab_action = QAction("Close Current Tab", self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(lambda: self.close_tab(self.tab_list.currentRow()))
        file_menu.addAction(close_tab_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # EDIT MENU
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

        cut_action = QAction("Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(lambda: self.get_current_editor().cut() if self.get_current_editor() else None)
        edit_menu.addAction(cut_action)

        copy_action = QAction("Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(lambda: self.get_current_editor().copy() if self.get_current_editor() else None)
        edit_menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(lambda: self.get_current_editor().paste() if self.get_current_editor() else None)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        find_action = QAction("Find & Replace...", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.open_find_dialog)
        edit_menu.addAction(find_action)

        # VIEW & FORMAT MENU
        view_menu = menu_bar.addMenu("View")

        font_action = QAction("Change Font...", self)
        font_action.triggered.connect(self.change_font)
        view_menu.addAction(font_action)

        text_color_action = QAction("Text Color...", self)
        text_color_action.triggered.connect(self.change_text_color)
        view_menu.addAction(text_color_action)

        bg_color_action = QAction("Background Color...", self)
        bg_color_action.triggered.connect(self.change_bg_color)
        view_menu.addAction(bg_color_action)

    # Animated Sidebar Collapse / Expand
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

    # Editor Creation
    def create_editor_widget(self, content="") -> QTextEdit:
        editor = QTextEdit()
        editor.setFont(QFont("SF Pro Text", 13) if sys.platform == "darwin" else QFont("Segoe UI", 12))
        editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.current_bg_color};
                color: #F2F2F7;
                border: none;
                padding: 24px;
                selection-background-color: #0A84FF;
            }}
        """)
        editor.setPlainText(content)
        return editor

    def add_new_tab(self, title="Untitled Note", file_path=None, content=""):
        editor = self.create_editor_widget(content)
        self.editor_stack.addWidget(editor)

        index = self.tab_list.count()
        tab_data = {"file_path": file_path, "widget": editor}
        self.tabs_data.append(tab_data)

        list_item = QListWidgetItem(self.tab_list)
        list_item.setSizeHint(QSize(0, 38))

        item_widget = TabItemWidget(title, lambda idx=index: self.close_tab_by_widget(list_item))
        self.tab_list.addItem(list_item)
        self.tab_list.setItemWidget(list_item, item_widget)

        self.tab_list.setCurrentRow(index)

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

    def close_tab_by_widget(self, item: QListWidgetItem):
        row = self.tab_list.row(item)
        self.close_tab(row)

    def close_tab(self, index):
        if index < 0 or index >= len(self.tabs_data):
            return

        item = self.tab_list.takeItem(index)
        widget = self.tabs_data[index]["widget"]
        self.editor_stack.removeWidget(widget)
        widget.deleteLater()

        del self.tabs_data[index]
        del item

        if len(self.tabs_data) == 0:
            self.add_new_tab()

    # --- Actions ---
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
        # Create a character format container
        fmt = QTextCharFormat()

        # Get current font at cursor position as default in dialog
        current_font = cursor.charFormat().font()
        font, ok = QFontDialog.getFont(current_font, self)

        if ok:
            fmt.setFont(font)
            # Merge format applies ONLY to selected text, or to future typing at current cursor
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
            
            # Merge format applies ONLY to selected text, or to future typing at current cursor
            cursor.mergeCharFormat(fmt)
            editor.mergeCurrentCharFormat(fmt)

    def change_bg_color(self):
        color = QColorDialog.getColor(QColor(self.current_bg_color), self, "Select Background Color")
        if color.isValid():
            self.current_bg_color = color.name()
            # ONLY change editor background canvas, leave text colors untouched
            for tab in self.tabs_data:
                editor = tab["widget"]
                editor.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {self.current_bg_color};
                        border: none;
                        padding: 24px;
                        selection-background-color: #0A84FF;
                    }}
                """)

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
        file_path = data["file_path"]

        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Note", "", "Text Files (*.txt);;All Files (*)")
            if not file_path:
                return
            data["file_path"] = file_path

        filename = os.path.basename(file_path)
        editor = data["widget"]

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(editor.toPlainText())

        list_item = self.tab_list.item(index)
        item_widget = self.tab_list.itemWidget(list_item)
        if item_widget:
            item_widget.set_title(filename)

    # --- Persistence Logic ---
    def save_session(self):
        session_data = {
            "active_tab": self.tab_list.currentRow(),
            "bg_color": self.current_bg_color,
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
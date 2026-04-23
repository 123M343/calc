import sys
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QListWidget,
    QLabel, QMessageBox, QFrame, QGraphicsOpacityEffect,
    QComboBox
)
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtCore import QTimer, QPropertyAnimation

import main as chatbot_main
import save_chat
import database_utilities
from teach_system import teach_trigger_word
from table_viewer import TableViewer


class ChatbotGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Math ChatBot GUI")
        self.resize(1260, 800)

        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self.update_typing_indicator)
        self.typing_dot_count = 0
        self.typing_active = False
        self.typing_block_start = None
        self.typing_block_end = None

        self.build_ui()
        self.apply_styles()
        self.refresh_db_lists()
        self.refresh_actions()

        for msg in chatbot_main.get_startup_messages():
            self.add_bot_message(msg)

    def build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)

        title = QLabel("Math ChatBot")
        title.setObjectName("mainTitle")
        left_layout.addWidget(title)

        subtitle = QLabel("Solve equations, calculate, or use database tools.")
        subtitle.setObjectName("subLabel")
        left_layout.addWidget(subtitle)

        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        self.chat_box.setObjectName("chatBox")
        left_layout.addWidget(self.chat_box)

        input_row = QHBoxLayout()

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Message Math ChatBot...")
        self.entry.returnPressed.connect(self.send_message)
        input_row.addWidget(self.entry)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primaryButton")
        self.send_button.clicked.connect(self.send_message)
        input_row.addWidget(self.send_button)

        left_layout.addLayout(input_row)

        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        tools = QLabel("Tools")
        tools.setObjectName("sectionTitle")
        right_layout.addWidget(tools)

        self.btn_show_dbs = QPushButton("Show Databases")
        self.btn_show_dbs.clicked.connect(self.gui_show_databases)
        right_layout.addWidget(self.btn_show_dbs)

        self.btn_show_tables = QPushButton("Show Tables")
        self.btn_show_tables.clicked.connect(self.gui_show_tables)
        right_layout.addWidget(self.btn_show_tables)

        self.btn_last = QPushButton("Last 10 Messages")
        self.btn_last.clicked.connect(self.gui_show_last_10)
        right_layout.addWidget(self.btn_last)

        self.btn_export = QPushButton("Export CSV")
        self.btn_export.clicked.connect(self.gui_export_csv)
        right_layout.addWidget(self.btn_export)

        self.btn_clear = QPushButton("Clear History")
        self.btn_clear.clicked.connect(self.gui_clear_history)
        right_layout.addWidget(self.btn_clear)

        search_label = QLabel("Search All Data")
        search_label.setObjectName("sectionLabel")
        right_layout.addWidget(search_label)

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Enter keyword...")
        right_layout.addWidget(self.search_entry)

        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self.gui_search)
        right_layout.addWidget(self.btn_search)

        teach_label = QLabel("Teach Trigger Word")
        teach_label.setObjectName("sectionLabel")
        right_layout.addWidget(teach_label)

        self.teach_word_entry = QLineEdit()
        self.teach_word_entry.setPlaceholderText("New trigger word...")
        right_layout.addWidget(self.teach_word_entry)

        self.action_combo = QComboBox()
        right_layout.addWidget(self.action_combo)

        self.btn_teach = QPushButton("Teach Word")
        self.btn_teach.clicked.connect(self.gui_teach)
        right_layout.addWidget(self.btn_teach)

        db_label = QLabel("Databases")
        db_label.setObjectName("sectionLabel")
        right_layout.addWidget(db_label)

        self.db_list = QListWidget()
        self.db_list.itemClicked.connect(self.on_db_clicked)
        right_layout.addWidget(self.db_list)

        table_label = QLabel("Tables")
        table_label.setObjectName("sectionLabel")
        right_layout.addWidget(table_label)

        self.table_list = QListWidget()
        self.table_list.itemClicked.connect(self.on_table_clicked)
        right_layout.addWidget(self.table_list)

        main_layout.addWidget(left_panel, 3)
        main_layout.addWidget(right_panel, 1)

    def apply_styles(self):
        self.setFont(QFont("Arial", 11))
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #EAEAEA;
            }
            QFrame {
                background-color: #262626;
                border: 1px solid #3A3A3A;
                border-radius: 14px;
            }
            QLabel#mainTitle {
                font-size: 24px;
                font-weight: 800;
                color: #10A37F;
            }
            QLabel#subLabel {
                font-size: 12px;
                color: #BBBBBB;
            }
            QLabel#sectionTitle {
                font-size: 16px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QLabel#sectionLabel {
                font-size: 13px;
                font-weight: 600;
                color: #D5D5D5;
                padding-top: 6px;
            }
            QTextEdit#chatBox, QLineEdit, QListWidget, QComboBox {
                background-color: #121212;
                border: 1px solid #3A3A3A;
                border-radius: 10px;
                padding: 8px;
                color: #EAEAEA;
            }
            QPushButton {
                background-color: #2F2F2F;
                border-radius: 10px;
                padding: 10px;
                font-weight: 600;
                color: white;
            }
            QPushButton:hover {
                background-color: #3F3F3F;
            }
            QPushButton#primaryButton {
                background-color: #10A37F;
            }
            QPushButton#primaryButton:hover {
                background-color: #13C89A;
            }
            QTableWidget {
                background-color: #121212;
                color: #EAEAEA;
                gridline-color: #444444;
            }
            QHeaderView::section {
                background-color: #2A2A2A;
                padding: 6px;
                border: 1px solid #444444;
                color: #EAEAEA;
            }
        """)

    def current_timestamp(self):
        return datetime.now().strftime("%I:%M %p").lstrip("0")

    def is_equation(self, text):
        lowered = str(text).lower()
        return any(key in lowered for key in [
            "step 1", "step 2", "step 3",
            "final answer", "you’re solving", "you're solving"
        ])

    def format_math_steps(self, text):
        lines = str(text).splitlines()
        out = []

        for line in lines:
            stripped = line.strip()
            lowered = stripped.lower()

            if lowered.startswith("step 1"):
                out.append(f"<div style='color:#66B3FF; font-weight:700; margin-top:8px;'>{stripped}</div>")
            elif lowered.startswith("step 2"):
                out.append(f"<div style='color:#FFD966; font-weight:700; margin-top:8px;'>{stripped}</div>")
            elif lowered.startswith("step 3"):
                out.append(f"<div style='color:#FFB366; font-weight:700; margin-top:8px;'>{stripped}</div>")
            elif lowered.startswith("final answer"):
                out.append(f"<div style='color:#7DFFA1; font-weight:800; margin-top:10px;'>{stripped}</div>")
            elif "you’re solving" in lowered or "you're solving" in lowered:
                out.append(f"<div style='color:#FFFFFF; font-weight:700; margin-bottom:6px;'>{stripped}</div>")
            else:
                out.append(f"<div>{stripped}</div>")

        return "".join(out)

    def smooth_scroll_to_bottom(self):
        scrollbar = self.chat_box.verticalScrollBar()
        target = scrollbar.maximum()
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(8)

        def step():
            current = scrollbar.value()
            if current >= target:
                self.scroll_timer.stop()
                return
            scrollbar.setValue(min(current + 35, target))

        self.scroll_timer.timeout.connect(step)
        self.scroll_timer.start()

    def fade_in_chat(self):
        effect = QGraphicsOpacityEffect(self.chat_box.viewport())
        self.chat_box.viewport().setGraphicsEffect(effect)

        self.fade_anim = QPropertyAnimation(effect, b"opacity")
        self.fade_anim.setDuration(220)
        self.fade_anim.setStartValue(0.35)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()

    def build_bubble_html(self, sender, message):
        time = self.current_timestamp()

        if sender == "You":
            align = "flex-end"
            bubble = "#2563EB"
            label = "You"
        elif sender == "Typing":
            align = "flex-start"
            bubble = "#3A3A3A"
            label = "ChatBot"
        else:
            align = "flex-start"
            bubble = "#10A37F"
            label = "ChatBot"

        if sender == "ChatBot" and self.is_equation(message):
            text = self.format_math_steps(message)
            text = f"""
            <div style='background:#0F2E26;padding:12px;border-left:4px solid #10FFB0;border-radius:8px;'>
                {text}
            </div>
            """
        else:
            text = str(message).replace("\n", "<br>")

        return f"""
        <div style="display:flex; justify-content:{align}; margin:10px;">
            <div style="max-width:60%; background:{bubble}; padding:12px; border-radius:16px;">
                <b>{label}</b><br>
                <small style="color:#ddd">{time}</small><br>
                {text}
            </div>
        </div>
        """

    def append_chat(self, sender, message):
        html = self.build_bubble_html(sender, message)
        self.chat_box.moveCursor(QTextCursor.End)
        self.chat_box.insertHtml(html)
        self.chat_box.insertPlainText("\n")
        self.chat_box.moveCursor(QTextCursor.End)
        self.fade_in_chat()
        self.smooth_scroll_to_bottom()

    def add_user_message(self, msg):
        self.append_chat("You", msg)
        save_chat.save_message("user", msg)

    def add_bot_message(self, msg):
        self.append_chat("ChatBot", msg)
        save_chat.save_message("bot", msg)

    def insert_typing_indicator(self):
        self.remove_typing_indicator()
        html = self.build_bubble_html("Typing", "ChatBot is thinking.")
        cursor = self.chat_box.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.typing_block_start = cursor.position()
        cursor.insertHtml(html)
        cursor.insertText("\n")
        self.typing_block_end = cursor.position()
        self.chat_box.setTextCursor(cursor)

    def remove_typing_indicator(self):
        if self.typing_block_start is None or self.typing_block_end is None:
            return

        cursor = self.chat_box.textCursor()
        cursor.setPosition(self.typing_block_start)
        cursor.setPosition(self.typing_block_end, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        self.chat_box.setTextCursor(cursor)
        self.typing_block_start = None
        self.typing_block_end = None

    def start_typing_indicator(self):
        self.typing_active = True
        self.typing_dot_count = 1
        self.insert_typing_indicator()
        self.typing_timer.start(350)

    def stop_typing_indicator(self):
        self.typing_active = False
        self.typing_timer.stop()
        self.remove_typing_indicator()

    def update_typing_indicator(self):
        if not self.typing_active:
            return

        self.typing_dot_count = 1 if self.typing_dot_count >= 3 else self.typing_dot_count + 1
        dots = "." * self.typing_dot_count

        self.remove_typing_indicator()
        html = self.build_bubble_html("Typing", f"ChatBot is thinking{dots}")
        cursor = self.chat_box.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.typing_block_start = cursor.position()
        cursor.insertHtml(html)
        cursor.insertText("\n")
        self.typing_block_end = cursor.position()
        self.chat_box.setTextCursor(cursor)

    def process_input(self, text):
        self.start_typing_indicator()
        QTimer.singleShot(500, lambda: self.finish_response(text))

    def finish_response(self, user_input):
        self.stop_typing_indicator()
        response = chatbot_main.process_user_input(user_input)
        self.add_bot_message(response)
        self.refresh_db_lists()

    def send_message(self):
        text = self.entry.text().strip()
        if not text:
            return
        self.entry.clear()
        self.add_user_message(text)
        self.process_input(text)

    def refresh_db_lists(self):
        self.db_list.clear()
        for db in database_utilities.load_user_databases():
            self.db_list.addItem(str(db))

        self.table_list.clear()
        for table in database_utilities.get_tables("Chat_Bot_DB"):
            self.table_list.addItem(str(table))

    def refresh_actions(self):
        self.action_combo.clear()
        for action_name, symbol in database_utilities.get_actions():
            self.action_combo.addItem(f"{action_name} ({symbol})", action_name)

    def gui_show_databases(self):
        self.add_user_message("show databases")
        self.process_input("show databases")

    def gui_show_tables(self):
        self.add_user_message("show tables")
        self.process_input("show tables")

    def gui_show_last_10(self):
        self.add_user_message("show last 10")
        self.process_input("show last 10")

    def gui_export_csv(self):
        self.add_user_message("export csv")
        self.process_input("export csv")

    def gui_clear_history(self):
        self.add_user_message("clear history")
        self.process_input("clear history")
        self.chat_box.clear()

    def gui_search(self):
        keyword = self.search_entry.text().strip()
        if not keyword:
            QMessageBox.warning(self, "Search", "Enter a search term.")
            return
        self.add_user_message(f"search {keyword}")
        self.process_input(f"search {keyword}")

    def gui_teach(self):
        word = self.teach_word_entry.text().strip()
        if not word:
            QMessageBox.warning(self, "Teach", "Enter a trigger word.")
            return

        action_name = self.action_combo.currentData()
        response = teach_trigger_word(word, action_name)
        self.add_user_message(f"teach {word} {action_name}")
        self.add_bot_message(response)
        self.teach_word_entry.clear()
        self.refresh_db_lists()

    def on_db_clicked(self, item):
        self.add_bot_message(database_utilities.show_tables(item.text()))

    def on_table_clicked(self, item):
        table_name = item.text()
        headers, rows = database_utilities.fetch_table_rows("Chat_Bot_DB", table_name, 100)

        if not headers:
            self.add_bot_message("Could not load table.")
            return

        viewer = TableViewer(table_name, headers, rows)
        viewer.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotGUI()
    window.show()
    sys.exit(app.exec())

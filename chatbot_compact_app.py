import sys
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import main as chatbot_main
from export_csv import export_all_data_to_csv
from graphing import GraphSeries, build_graph_points, is_graph_request, parse_graph_request
from history import clear_history
from last_10_messages import show_last_10_messages
from ocr_scanner import extract_math_lines


class GraphCanvas(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.series: GraphSeries = []
        self.setMinimumHeight(260)
        self.setObjectName("graphCanvas")

    def set_series(self, series: GraphSeries) -> None:
        self.series = series
        self.update()

    def clear_series(self) -> None:
        self.series = []
        self.update()

    def paintEvent(self, event: Any) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect().adjusted(14, 14, -14, -14)
        painter.fillRect(self.rect(), QColor("#FFFDF9"))

        painter.setPen(QPen(QColor("#D8CBB8"), 1))
        painter.drawRoundedRect(rect, 14, 14)

        if not self.series:
            painter.setPen(QColor("#7F8A98"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Graph will appear here.")
            return

        all_x: list[float] = []
        all_y: list[float] = []
        for line in self.series:
            all_x.extend(float(x) for x in line["x"])
            all_y.extend(float(y) for y in line["y"] if y == y)

        if not all_x or not all_y:
            painter.setPen(QColor("#7F8A98"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No drawable graph points.")
            return

        x_min = min(all_x)
        x_max = max(all_x)
        y_min = min(all_y)
        y_max = max(all_y)

        if x_min == x_max:
            x_min -= 1.0
            x_max += 1.0
        if y_min == y_max:
            y_min -= 1.0
            y_max += 1.0

        plot_rect = rect.adjusted(26, 16, -16, -30)

        painter.setPen(QPen(QColor("#E8DBC8"), 1))
        for fraction in (0.25, 0.5, 0.75):
            x_line = int(plot_rect.left() + plot_rect.width() * fraction)
            y_line = int(plot_rect.top() + plot_rect.height() * fraction)
            painter.drawLine(x_line, plot_rect.top(), x_line, plot_rect.bottom())
            painter.drawLine(plot_rect.left(), y_line, plot_rect.right(), y_line)

        def map_x(value: float) -> float:
            return plot_rect.left() + ((value - x_min) / (x_max - x_min)) * plot_rect.width()

        def map_y(value: float) -> float:
            return plot_rect.bottom() - ((value - y_min) / (y_max - y_min)) * plot_rect.height()

        if x_min <= 0 <= x_max:
            zero_x = int(map_x(0.0))
            painter.setPen(QPen(QColor("#B8A487"), 1.6))
            painter.drawLine(zero_x, plot_rect.top(), zero_x, plot_rect.bottom())

        if y_min <= 0 <= y_max:
            zero_y = int(map_y(0.0))
            painter.setPen(QPen(QColor("#B8A487"), 1.6))
            painter.drawLine(plot_rect.left(), zero_y, plot_rect.right(), zero_y)

        for line in self.series:
            path = QPainterPath()
            started = False
            for x_value, y_value in zip(line["x"], line["y"]):
                y_float = float(y_value)
                if y_float != y_float:
                    started = False
                    continue

                point_x = map_x(float(x_value))
                point_y = map_y(y_float)
                if not started:
                    path.moveTo(point_x, point_y)
                    started = True
                else:
                    path.lineTo(point_x, point_y)

            painter.setPen(QPen(QColor(str(line["color"])), 2.4))
            painter.drawPath(path)

        painter.setPen(QColor("#6A717D"))
        painter.drawText(rect.adjusted(10, 4, -10, 0), f"x: {x_min:.2f} to {x_max:.2f}")
        painter.drawText(
            rect.adjusted(10, 0, -10, -4),
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            f"y: {y_min:.2f} to {y_max:.2f}"
        )


class CompactChatbotApp(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Math ChatBot Compact App")
        self.resize(1180, 760)
        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self.update_typing_indicator)
        self.typing_frame = 0
        self.bot_busy = False
        self.pending_response: str | None = None
        self.build_ui()
        self.apply_styles()

        for message in chatbot_main.get_startup_messages():
            self.add_bot_message(message)

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Math ChatBot Compact App")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        root.addWidget(title)

        subtitle = QLabel("A simpler app that still solves math, previews graph data, scans homework, and manages history.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subTitle")
        root.addWidget(subtitle)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        chat_panel = QFrame()
        chat_panel.setObjectName("panel")
        chat_panel.setFrameShape(QFrame.Shape.StyledPanel)
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(12, 12, 12, 12)
        chat_layout.setSpacing(10)

        chat_label = QLabel("Chat")
        chat_label.setObjectName("sectionTitle")
        chat_layout.addWidget(chat_label)

        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        self.chat_box.setObjectName("chatBox")
        chat_layout.addWidget(self.chat_box, 1)

        self.typing_label = QLabel("")
        self.typing_label.setObjectName("typingLabel")
        self.typing_label.setMinimumHeight(24)
        chat_layout.addWidget(self.typing_label)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.entry = QLineEdit()
        self.entry.setObjectName("chatEntry")
        self.entry.setPlaceholderText("Try: graph y = x^2 and y = 2x + 1")
        self.entry.returnPressed.connect(self.send_message)
        input_row.addWidget(self.entry, 1)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primaryButton")
        self.send_button.clicked.connect(self.send_message)
        input_row.addWidget(self.send_button)

        chat_layout.addLayout(input_row)
        splitter.addWidget(chat_panel)

        tools_panel = QFrame()
        tools_panel.setObjectName("panel")
        tools_panel.setFrameShape(QFrame.Shape.StyledPanel)
        tools_layout = QVBoxLayout(tools_panel)
        tools_layout.setContentsMargins(12, 12, 12, 12)
        tools_layout.setSpacing(10)

        tools_label = QLabel("Tools And Graph Preview")
        tools_label.setObjectName("sectionTitle")
        tools_layout.addWidget(tools_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.last_button = QPushButton("Last 10")
        self.last_button.clicked.connect(self.show_last_10)
        button_row.addWidget(self.last_button)

        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_csv)
        button_row.addWidget(self.export_button)

        self.clear_button = QPushButton("Clear History")
        self.clear_button.clicked.connect(self.clear_chat_history)
        button_row.addWidget(self.clear_button)

        self.scan_button = QPushButton("Scan Homework")
        self.scan_button.clicked.connect(self.scan_homework)
        button_row.addWidget(self.scan_button)

        tools_layout.addLayout(button_row)

        preview_label = QLabel("Graph Preview")
        preview_label.setObjectName("subSectionTitle")
        tools_layout.addWidget(preview_label)

        self.graph_canvas = GraphCanvas()
        tools_layout.addWidget(self.graph_canvas, 1)

        self.graph_summary = QTextEdit()
        self.graph_summary.setReadOnly(True)
        self.graph_summary.setObjectName("summaryBox")
        self.graph_summary.setPlaceholderText("Graph summaries will appear here when you send a graph request.")
        tools_layout.addWidget(self.graph_summary, 1)

        self.graph_table = QTableWidget()
        self.graph_table.setObjectName("graphTable")
        self.graph_table.setColumnCount(2)
        self.graph_table.setHorizontalHeaderLabels(["x", "y"])
        tools_layout.addWidget(self.graph_table, 1)

        splitter.addWidget(tools_panel)
        splitter.setSizes([720, 420])

    def apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #f4efe7;
                color: #18212b;
                font-size: 14px;
            }
            QFrame#panel {
                background: #fffaf2;
                border: 1px solid #d8cbb8;
                border-radius: 18px;
            }
            QLabel {
                background: transparent;
            }
            QLabel#subTitle {
                color: #6a717d;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: 700;
                color: #8d3b2f;
            }
            QLabel#subSectionTitle {
                font-size: 16px;
                font-weight: 700;
                color: #22577a;
            }
            QLabel#typingLabel {
                color: #9a5c2f;
                font-style: italic;
                padding-left: 4px;
            }
            QTextEdit#chatBox, QTextEdit#summaryBox, QLineEdit#chatEntry, QTableWidget#graphTable, QWidget#graphCanvas {
                background: #fffdf9;
                border: 1px solid #d8cbb8;
                border-radius: 14px;
                padding: 8px;
            }
            QTextEdit#chatBox {
                selection-background-color: #f2c27b;
            }
            QLineEdit#chatEntry {
                min-height: 38px;
                padding-left: 10px;
            }
            QPushButton {
                background: #e7dccd;
                color: #18212b;
                border: 1px solid #ccbca8;
                border-radius: 12px;
                padding: 9px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #dcc8ad;
            }
            QPushButton#primaryButton {
                background: #8d3b2f;
                color: #fffaf2;
                border: 1px solid #7a2f25;
            }
            QPushButton#primaryButton:hover {
                background: #a34839;
            }
            QTableWidget#graphTable {
                gridline-color: #e8dbc8;
            }
            QHeaderView::section {
                background: #efe3d0;
                color: #264653;
                border: none;
                border-bottom: 1px solid #d8cbb8;
                padding: 6px;
                font-weight: 700;
            }
            QScrollBar:vertical {
                background: #f1e8dc;
                width: 12px;
                margin: 8px 2px 8px 2px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #c7a97c;
                min-height: 26px;
                border-radius: 6px;
            }
            """
        )

    def append_message(self, sender: str, message: str) -> None:
        html = self.build_message_html(sender, message)
        self.chat_box.append(html)
        self.chat_box.verticalScrollBar().setValue(self.chat_box.verticalScrollBar().maximum())

    def build_message_html(self, sender: str, message: str) -> str:
        escaped_message = (
            str(message)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )

        if sender == "You":
            message_color = "#8C3512"
            label_color = "#6F2608"
            accent = "#E26D2F"
            align = "right"
        else:
            message_color = "#0F5A87"
            label_color = "#0A4668"
            accent = "#1692D0"
            align = "left"

        return (
            f"<table width='100%' cellspacing='0' cellpadding='0' style='margin-top:10px; margin-bottom:10px;'>"
            f"<tr><td align='{align}'>"
            f"<div style='font-size:11px; font-weight:700; color:{label_color}; margin-bottom:3px;'>"
            f"{sender}</div>"
            f"<div style='font-size:14px; line-height:1.55; color:{message_color}; font-weight:600;'>"
            f"<span style='color:{accent}; font-weight:700;'>&#9679;</span> {escaped_message}</div>"
            f"</td></tr></table>"
        )

    def add_user_message(self, message: str) -> None:
        self.append_message("You", message)

    def add_bot_message(self, message: str) -> None:
        self.append_message("ChatBot", message)

    def start_typing_indicator(self) -> None:
        self.bot_busy = True
        self.typing_frame = 0
        self.entry.setEnabled(False)
        self.send_button.setEnabled(False)
        self.typing_label.setText("ChatBot is typing")
        self.typing_timer.start(280)

    def update_typing_indicator(self) -> None:
        dots = "." * ((self.typing_frame % 3) + 1)
        self.typing_label.setText(f"ChatBot is typing{dots}")
        self.typing_frame += 1

    def finish_typing_with_response(self, response: str) -> None:
        self.typing_timer.stop()
        self.bot_busy = False
        self.entry.setEnabled(True)
        self.send_button.setEnabled(True)
        self.entry.setFocus()
        self.typing_label.clear()
        self.add_bot_message(response)

    def queue_bot_response(self, response: str, delay_ms: int = 650) -> None:
        self.pending_response = response
        self.start_typing_indicator()
        QTimer.singleShot(delay_ms, self.deliver_pending_response)

    def deliver_pending_response(self) -> None:
        if self.pending_response is None:
            self.typing_timer.stop()
            self.bot_busy = False
            self.entry.setEnabled(True)
            self.send_button.setEnabled(True)
            self.typing_label.clear()
            return

        response = self.pending_response
        self.pending_response = None
        self.finish_typing_with_response(response)

    def send_message(self) -> None:
        if self.bot_busy:
            return

        text = self.entry.text().strip()
        if not text:
            return

        self.entry.clear()
        self.add_user_message(text)

        if is_graph_request(text):
            self.handle_graph_request(text)
            return

        response = chatbot_main.process_user_input(text)
        self.queue_bot_response(str(response))

    def handle_graph_request(self, text: str) -> None:
        try:
            graph_task = parse_graph_request(text)
            series = build_graph_points(graph_task)
        except Exception as exc:
            self.queue_bot_response(f"I could not preview that graph.\n\n{exc}")
            return

        self.update_graph_preview(series)
        function_count = len(series)
        self.queue_bot_response(
            f"Prepared graph preview for {function_count} function{'s' if function_count != 1 else ''}. "
            "Check the panel on the right for sample points."
        )

    def update_graph_preview(self, series: GraphSeries) -> None:
        summary_lines: list[str] = []
        first_points: list[tuple[float, float]] = []

        self.graph_canvas.set_series(series)

        for item in series:
            label = str(item["label"])
            x_values = [float(value) for value in item["x"]]
            y_values = [float(value) for value in item["y"] if str(value) != "nan"]
            summary_lines.append(
                f"{label}\n"
                f"points: {len(item['x'])}\n"
                f"x-range: {min(x_values):.2f} to {max(x_values):.2f}\n"
                f"valid y-points: {len(y_values)}"
            )

            if not first_points:
                for x_value, y_value in zip(item["x"], item["y"]):
                    y_float = float(y_value)
                    if str(y_float) == "nan":
                        continue
                    first_points.append((float(x_value), y_float))
                    if len(first_points) >= 12:
                        break

        self.graph_summary.setPlainText("\n\n".join(summary_lines))
        self.populate_graph_table(first_points)

    def populate_graph_table(self, points: list[tuple[float, float]]) -> None:
        self.graph_table.clearContents()
        self.graph_table.setRowCount(len(points))

        for row_index, (x_value, y_value) in enumerate(points):
            self.graph_table.setItem(row_index, 0, QTableWidgetItem(f"{x_value:.4f}"))
            self.graph_table.setItem(row_index, 1, QTableWidgetItem(f"{y_value:.4f}"))

        self.graph_table.resizeColumnsToContents()

    def show_last_10(self) -> None:
        self.queue_bot_response(show_last_10_messages(), delay_ms=500)

    def export_csv(self) -> None:
        self.queue_bot_response(export_all_data_to_csv(), delay_ms=500)

    def clear_chat_history(self) -> None:
        response = clear_history()
        self.chat_box.clear()
        self.queue_bot_response(response, delay_ms=420)

    def scan_homework(self) -> None:
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Homework Photo",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not image_path:
            return

        try:
            scan_result = extract_math_lines(image_path)
        except Exception as exc:
            QMessageBox.warning(self, "Scan Error", f"Could not scan that image.\n\n{exc}")
            return

        math_lines: list[str] = scan_result["math_lines"]
        if not math_lines:
            self.queue_bot_response("I scanned the image, but I did not find any math lines to solve.")
            return

        solved_sections: list[str] = []
        for line in math_lines:
            solved_sections.append(f"{line}\n{chatbot_main.process_user_input(line)}")

        response = (
            "I scanned the homework photo and found these math lines:\n\n"
            + "\n".join(math_lines)
            + "\n\nSolved Results:\n\n"
            + "\n\n".join(solved_sections)
        )
        self.queue_bot_response(response, delay_ms=900)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CompactChatbotApp()
    window.show()
    sys.exit(app.exec())

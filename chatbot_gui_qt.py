import sys
import signal
from datetime import datetime
from typing import Any, cast

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton,
    QLabel, QMessageBox, QFrame, QGraphicsOpacityEffect,
    QComboBox, QScrollArea, QTableWidget, QTableWidgetItem,
    QColorDialog, QFileDialog
)
from PySide6.QtGui import QColor, QFont, QFontDatabase, QTextCursor
from PySide6.QtCore import QTimer, QPropertyAnimation

from graphing import GraphSeries, GraphTask, build_graph_points, is_graph_request, parse_graph_request
from ocr_scanner import extract_math_lines

try:
    import pyqtgraph as pg  # type: ignore[import-untyped]
except ImportError:
    pg = None

import main as chatbot_main
import save_chat
import database_utilities
from teach_system import teach_trigger_word
from load_operations import load_operations
FigureCanvasQTAgg = None
NavigationToolbar2QT = None
Figure = None
THEMES = {
    "Dark": {
        "window": "#111827",
        "panel": "#1B2330",
        "panel_alt": "#0F1722",
        "border": "#2B384A",
        "text": "#E5EEF7",
        "muted": "#9FB0C3",
        "bubble_user": "#1D4ED8",
        "bubble_bot": "#172A3A",
        "bubble_typing": "#223244",
        "accent": "#10B981",
        "input": "#0E1621",
        "graph": "#101820",
        "step_bg": "#0C2A24",
    },
    "Light": {
        "window": "#EEF2F7",
        "panel": "#FFFFFF",
        "panel_alt": "#F7FAFC",
        "border": "#D5DFEA",
        "text": "#142132",
        "muted": "#5F7185",
        "bubble_user": "#2563EB",
        "bubble_bot": "#E7F0F7",
        "bubble_typing": "#DCE8F3",
        "accent": "#0F9D7A",
        "input": "#F8FBFD",
        "graph": "#F3F7FB",
        "step_bg": "#E7F8F1",
    },
    "Custom": {
        "window": "#131722",
        "panel": "#1C2230",
        "panel_alt": "#121826",
        "border": "#334155",
        "text": "#E6EDF5",
        "muted": "#9CAAC0",
        "bubble_user": "#7C3AED",
        "bubble_bot": "#1B2B40",
        "bubble_typing": "#24364D",
        "accent": "#F97316",
        "input": "#0F1722",
        "graph": "#10151D",
        "step_bg": "#202B15",
    },
}


def load_matplotlib_backend() -> bool:
    global FigureCanvasQTAgg, NavigationToolbar2QT, Figure

    if FigureCanvasQTAgg is not None and Figure is not None:
        return True

    try:
        # Import lazily so startup stays fast when pyqtgraph is available.
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as canvas_class
        from matplotlib.backends.backend_qt import NavigationToolbar2QT as toolbar_class
        from matplotlib.figure import Figure as figure_class
    except ImportError:
        return False

    FigureCanvasQTAgg = canvas_class
    NavigationToolbar2QT = toolbar_class
    Figure = figure_class
    return True


def color_with_alpha(hex_color: str, alpha_hex: str) -> str:
    return f"{hex_color}{alpha_hex}"


def get_preferred_app_font() -> QFont:
    # Use a real installed font to avoid Qt alias warnings on startup.
    available_families = set(QFontDatabase.families())
    for family in ["SF Pro Display", ".AppleSystemUIFont", "Helvetica Neue", "Arial"]:
        if family in available_families:
            return QFont(family, 11)

    font = QApplication.font()
    font.setPointSize(11)
    return font


class ChatbotGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Math ChatBot GUI")
        self.setMinimumSize(900, 600)
        self.resize_to_available_screen()
        self.current_theme = "Dark"
        self.custom_accent = THEMES["Custom"]["accent"]

        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self.update_typing_indicator)
        self.typing_dot_count = 0
        self.typing_active = False
        self.typing_block_start = None
        self.typing_block_end = None
        self.graph_plot_widget = None
        self.graph_legend = None
        self.graph_canvas = None
        self.graph_toolbar = None
        self.graph_figure = None
        self.graph_axis = None

        self.build_ui()
        self.apply_styles()
        database_utilities.ensure_trigger_word_unique_index()
        database_utilities.ensure_saved_equations_table()
        self.refresh_all_data()

        for msg in chatbot_main.get_startup_messages():
            self.add_bot_message(msg)

    def build_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(12)

        header_card = QFrame()
        header_card.setObjectName("heroPanel")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(6)

        title = QLabel("Math ChatBot")
        title.setObjectName("mainTitle")
        header_layout.addWidget(title)

        subtitle = QLabel("Solve equations, graph functions, calculate, and store formulas.")
        subtitle.setObjectName("subLabel")
        header_layout.addWidget(subtitle)
        left_layout.addWidget(header_card)

        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        self.chat_box.setObjectName("chatBox")
        left_layout.addWidget(self.chat_box, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Try: graph y = x^2 and y = 2x + 1")
        self.entry.setMinimumHeight(44)
        self.entry.returnPressed.connect(self.send_message)
        input_row.addWidget(self.entry, 1)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primaryButton")
        self.send_button.setMinimumHeight(44)
        self.send_button.clicked.connect(self.send_message)
        input_row.addWidget(self.send_button)

        left_layout.addLayout(input_row, 0)

        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(14, 14, 14, 14)
        right_panel_layout.setSpacing(10)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)

        theme_label = QLabel("Theme")
        theme_label.setObjectName("sectionLabel")
        theme_row.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_row.addWidget(self.theme_combo, 1)

        self.color_button = QPushButton("Accent")
        self.color_button.clicked.connect(self.choose_custom_color)
        theme_row.addWidget(self.color_button)
        right_panel_layout.addLayout(theme_row)

        # Keep the right side ordered the same way the user asked for:
        # tools first, graph second, coordinates table third.
        tools_scroll = QScrollArea()
        tools_scroll.setWidgetResizable(True)
        tools_scroll.setFrameShape(QFrame.Shape.NoFrame)

        tools_widget = QWidget()
        tools_widget.setObjectName("toolsWidget")
        right_layout = QVBoxLayout(tools_widget)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        tools_scroll.setWidget(tools_widget)
        right_panel_layout.addWidget(tools_scroll)

        tools = QLabel("Tools")
        tools.setObjectName("sectionTitle")
        right_layout.addWidget(tools)

        self.btn_last = QPushButton("Last 10 Messages")
        self.btn_last.clicked.connect(self.gui_show_last_10)
        right_layout.addWidget(self.btn_last)

        self.btn_export = QPushButton("Export CSV")
        self.btn_export.clicked.connect(self.gui_export_csv)
        right_layout.addWidget(self.btn_export)

        self.btn_refresh = QPushButton("Refresh Data")
        self.btn_refresh.clicked.connect(self.gui_refresh_data)
        right_layout.addWidget(self.btn_refresh)

        self.btn_clear = QPushButton("Clear History")
        self.btn_clear.clicked.connect(self.gui_clear_history)
        right_layout.addWidget(self.btn_clear)

        self.btn_scan_homework = QPushButton("Scan Homework Photo")
        self.btn_scan_homework.clicked.connect(self.gui_scan_homework)
        right_layout.addWidget(self.btn_scan_homework)

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

        remove_trigger_label = QLabel("Remove Trigger Word")
        remove_trigger_label.setObjectName("sectionLabel")
        right_layout.addWidget(remove_trigger_label)

        self.trigger_word_combo = QComboBox()
        right_layout.addWidget(self.trigger_word_combo)

        self.btn_remove_trigger = QPushButton("Remove Word")
        self.btn_remove_trigger.clicked.connect(self.gui_remove_trigger_word)
        right_layout.addWidget(self.btn_remove_trigger)

        saved_eq_label = QLabel("Saved Equations")
        saved_eq_label.setObjectName("sectionLabel")
        right_layout.addWidget(saved_eq_label)

        self.saved_equations_combo = QComboBox()
        right_layout.addWidget(self.saved_equations_combo)

        self.btn_load_equation = QPushButton("Load Equation")
        self.btn_load_equation.clicked.connect(self.gui_load_saved_equation)
        right_layout.addWidget(self.btn_load_equation)

        right_layout.addStretch()

        graph_title = QLabel("Graph")
        graph_title.setObjectName("sectionTitle")
        right_panel_layout.addWidget(graph_title)

        self.graph_status = QLabel("Graph a function to keep it visible here. Try: graph y = x^2")
        self.graph_status.setObjectName("graphHint")
        self.graph_status.setWordWrap(True)
        right_panel_layout.addWidget(self.graph_status)

        self.graph_panel = QFrame()
        self.graph_panel.setObjectName("graphPanel")
        self.graph_panel.setMinimumHeight(280)
        graph_layout = QVBoxLayout(self.graph_panel)
        graph_layout.setContentsMargins(10, 10, 10, 10)
        graph_layout.setSpacing(8)
        self.graph_container_layout = graph_layout
        right_panel_layout.addWidget(self.graph_panel, 1)

        self.initialize_graph_panel()

        table_title = QLabel("Graph Coordinates")
        table_title.setObjectName("sectionLabel")
        right_panel_layout.addWidget(table_title)

        # This table mirrors the sampled points currently shown in the graph.
        self.graph_table = QTableWidget()
        self.graph_table.setObjectName("graphTable")
        self.graph_table.setColumnCount(0)
        self.graph_table.setRowCount(0)
        self.graph_table.setMinimumHeight(220)
        self.graph_table.setAlternatingRowColors(True)
        self.graph_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.graph_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.graph_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.graph_table.verticalHeader().setVisible(False)
        right_panel_layout.addWidget(self.graph_table)

        main_layout.addWidget(left_panel, 3)
        main_layout.addWidget(right_panel, 2)

    def resize_to_available_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(1260, 720)
            return

        available = screen.availableGeometry()
        width = min(1260, max(900, available.width() - 80))
        height = min(720, max(600, available.height() - 80))
        self.resize(width, height)

    def apply_styles(self) -> None:
        theme = self.get_theme_colors()
        self.setFont(get_preferred_app_font())
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme["window"]};
                color: {theme["text"]};
            }}
            QFrame#panel {{
                background-color: {theme["panel"]};
                border: 1px solid {theme["border"]};
                border-radius: 18px;
            }}
            QFrame#heroPanel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {theme["panel_alt"]}, stop:1 {theme["panel"]});
                border: 1px solid {theme["border"]};
                border-radius: 18px;
            }}
            QFrame#graphPanel {{
                background-color: {theme["graph"]};
                border: 1px solid {theme["border"]};
                border-radius: 16px;
            }}
            QLabel#mainTitle {{
                font-size: 28px;
                font-weight: 800;
                color: {theme["accent"]};
            }}
            QLabel#subLabel {{
                font-size: 13px;
                color: {theme["muted"]};
            }}
            QLabel#sectionTitle {{
                font-size: 16px;
                font-weight: 700;
                color: {theme["text"]};
            }}
            QLabel#sectionLabel {{
                font-size: 12px;
                font-weight: 700;
                color: {theme["muted"]};
                letter-spacing: 0.4px;
                text-transform: uppercase;
                padding-top: 6px;
            }}
            QLabel#graphHint {{
                font-size: 12px;
                color: {theme["muted"]};
            }}
            QTextEdit#chatBox, QLineEdit, QListWidget, QComboBox {{
                background-color: {theme["input"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
                padding: 10px;
                color: {theme["text"]};
            }}
            QTextEdit#chatBox {{
                padding: 14px;
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border: 1px solid {theme["accent"]};
            }}
            QTableWidget#graphTable {{
                background-color: {theme["input"]};
                alternate-background-color: {theme["panel_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
                color: {theme["text"]};
                gridline-color: {theme["border"]};
            }}
            QPushButton {{
                background-color: {theme["panel_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 12px;
                padding: 10px 12px;
                font-weight: 600;
                color: {theme["text"]};
            }}
            QPushButton:hover {{
                border: 1px solid {theme["accent"]};
            }}
            QPushButton#primaryButton {{
                background-color: {theme["accent"]};
                border: 1px solid {theme["accent"]};
                color: white;
            }}
            QPushButton#primaryButton:hover {{
                background-color: {color_with_alpha(theme["accent"], "DD")};
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QTableWidget {{
                background-color: {theme["input"]};
                color: {theme["text"]};
                gridline-color: {theme["border"]};
            }}
            QHeaderView::section {{
                background-color: {theme["panel_alt"]};
                padding: 6px;
                border: 1px solid {theme["border"]};
                color: {theme["text"]};
            }}
        """)
        self.update_graph_theme()

    def current_timestamp(self) -> str:
        return datetime.now().strftime("%I:%M %p").lstrip("0")

    def get_theme_colors(self) -> dict[str, str]:
        theme = dict(THEMES.get(self.current_theme, THEMES["Dark"]))
        if self.current_theme == "Custom":
            theme["accent"] = self.custom_accent
        return theme

    def change_theme(self, theme_name: str) -> None:
        self.current_theme = theme_name
        self.apply_styles()

    def choose_custom_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.custom_accent), self, "Pick Accent Color")
        if not color.isValid():
            return
        self.custom_accent = color.name()
        self.theme_combo.setCurrentText("Custom")
        self.apply_styles()

    def update_graph_theme(self) -> None:
        theme = self.get_theme_colors()
        if self.graph_plot_widget is not None and pg is not None:
            pg_module = cast(Any, pg)
            self.graph_plot_widget.setBackground(theme["graph"])
            axis_pen = pg_module.mkPen(theme["muted"])
            for axis_name in ["bottom", "left"]:
                axis = self.graph_plot_widget.getAxis(axis_name)
                axis.setPen(axis_pen)
                axis.setTextPen(axis_pen)
            return

        if self.graph_axis is not None:
            self.style_matplotlib_axis()
            if self.graph_canvas is not None:
                self.graph_canvas.draw_idle()

    def is_equation(self, text: str) -> bool:
        lowered = str(text).lower()
        return any(key in lowered for key in [
            "step 1", "step 2", "step 3",
            "final answer", "you’re solving", "you're solving"
        ])

    def format_math_steps(self, text: str) -> str:
        theme = self.get_theme_colors()
        accent = theme["accent"]
        text_color = theme["text"]
        lines = str(text).splitlines()
        out: list[str] = []

        for line in lines:
            stripped = line.strip()
            lowered = stripped.lower()

            if lowered.startswith("step 1"):
                out.append(f"<div style='color:#60A5FA; font-weight:700; margin-top:8px;'>{stripped}</div>")
            elif lowered.startswith("step 2"):
                out.append(f"<div style='color:#FBBF24; font-weight:700; margin-top:8px;'>{stripped}</div>")
            elif lowered.startswith("step 3"):
                out.append(f"<div style='color:#FB923C; font-weight:700; margin-top:8px;'>{stripped}</div>")
            elif lowered.startswith("final answer"):
                out.append(f"<div style='color:{accent}; font-weight:800; margin-top:10px;'>{stripped}</div>")
            elif "you’re solving" in lowered or "you're solving" in lowered:
                out.append(f"<div style='color:{text_color}; font-weight:700; margin-bottom:6px;'>{stripped}</div>")
            else:
                out.append(f"<div>{stripped}</div>")

        return "".join(out)

    def smooth_scroll_to_bottom(self) -> None:
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

    def fade_in_chat(self) -> None:
        effect = QGraphicsOpacityEffect(self.chat_box.viewport())
        self.chat_box.viewport().setGraphicsEffect(effect)

        self.fade_anim = QPropertyAnimation(effect, b"opacity")
        self.fade_anim.setDuration(220)
        self.fade_anim.setStartValue(0.35)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()

    def build_bubble_html(self, sender: str, message: str) -> str:
        theme = self.get_theme_colors()
        time = self.current_timestamp()
        step_bg = theme["step_bg"]
        accent = theme["accent"]
        border = theme["border"]
        muted = theme["muted"]

        if sender == "You":
            align = "flex-end"
            bubble = theme["bubble_user"]
            label = "You"
            text_color = "#FFFFFF"
        elif sender == "Typing":
            align = "flex-start"
            bubble = theme["bubble_typing"]
            label = "ChatBot"
            text_color = theme["text"]
        else:
            align = "flex-start"
            bubble = theme["bubble_bot"]
            label = "ChatBot"
            text_color = theme["text"]

        if sender == "ChatBot" and self.is_equation(message):
            text = self.format_math_steps(message)
            text = f"""
            <div style='background:{step_bg};padding:12px;border-left:4px solid {accent};border-radius:12px;'>
                {text}
            </div>
            """
        else:
            text = str(message).replace("\n", "<br>")

        return f"""
        <div style="display:flex; justify-content:{align}; margin:10px 6px;">
            <div style="
                max-width:72%;
                background:{bubble};
                color:{text_color};
                padding:14px 16px;
                border-radius:22px;
                border:1px solid {border};
            ">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                    <span style="font-weight:800;">{label}</span>
                    <span style="font-size:11px; color:{muted};">{time}</span>
                </div>
                {text}
            </div>
        </div>
        """

    def append_chat(self, sender: str, message: str) -> None:
        html = self.build_bubble_html(sender, message)
        self.chat_box.moveCursor(QTextCursor.MoveOperation.End)
        self.chat_box.insertHtml(html)
        self.chat_box.insertPlainText("\n")
        self.chat_box.moveCursor(QTextCursor.MoveOperation.End)
        self.fade_in_chat()
        self.smooth_scroll_to_bottom()

    def add_user_message(self, msg: str) -> None:
        self.append_chat("You", msg)
        save_chat.save_message("user", msg)

    def add_bot_message(self, msg: str) -> None:
        self.append_chat("ChatBot", msg)
        save_chat.save_message("bot", msg)

    def clear_graph_container(self) -> None:
        while self.graph_container_layout.count():
            item = self.graph_container_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def initialize_graph_panel(self) -> None:
        self.clear_graph_container()

        # Prefer pyqtgraph for the embedded interactive graph.
        if pg is not None:
            self.build_embedded_pyqtgraph()
            return

        if load_matplotlib_backend():
            self.build_embedded_matplotlib()
            return

        fallback = QLabel(
            "Install `pyqtgraph` or `matplotlib` in the project virtual environment to enable graphing."
        )
        fallback.setObjectName("graphHint")
        fallback.setWordWrap(True)
        self.graph_container_layout.addWidget(fallback)

    def build_embedded_pyqtgraph(self) -> None:
        theme = self.get_theme_colors()
        pg_module = cast(Any, pg)
        pg_module.setConfigOptions(antialias=True, background=theme["graph"], foreground=theme["text"])
        self.graph_plot_widget = pg_module.PlotWidget()
        self.graph_plot_widget.showGrid(x=True, y=True, alpha=0.28)
        self.graph_plot_widget.setLabel("bottom", "x")
        self.graph_plot_widget.setLabel("left", "y")
        self.graph_plot_widget.setMenuEnabled(False)
        self.graph_plot_widget.getViewBox().setMouseEnabled(x=True, y=True)
        self.graph_plot_widget.setBackground(theme["graph"])
        self.graph_legend = self.graph_plot_widget.addLegend(offset=(8, 8))
        self.graph_container_layout.addWidget(self.graph_plot_widget, 1)

    def build_embedded_matplotlib(self) -> None:
        theme = self.get_theme_colors()
        figure_class = cast(Any, Figure)
        canvas_class = cast(Any, FigureCanvasQTAgg)
        toolbar_class = cast(Any, NavigationToolbar2QT)

        self.graph_figure = figure_class(facecolor=theme["graph"])
        self.graph_canvas = canvas_class(self.graph_figure)
        if NavigationToolbar2QT is not None:
            self.graph_toolbar = toolbar_class(self.graph_canvas, self)
            self.graph_container_layout.addWidget(self.graph_toolbar)
        self.graph_container_layout.addWidget(self.graph_canvas, 1)
        self.graph_axis = self.graph_figure.add_subplot(111)
        self.style_matplotlib_axis()
        self.graph_canvas.draw_idle()

    def style_matplotlib_axis(self) -> None:
        if self.graph_axis is None:
            return
        theme = self.get_theme_colors()

        self.graph_axis.clear()
        self.graph_axis.set_facecolor(theme["graph"])
        self.graph_axis.grid(True, color=theme["border"], alpha=0.6)
        self.graph_axis.axhline(0, color=theme["muted"], linewidth=1.0)
        self.graph_axis.axvline(0, color=theme["muted"], linewidth=1.0)
        self.graph_axis.tick_params(colors=theme["text"])
        self.graph_axis.xaxis.label.set_color(theme["text"])
        self.graph_axis.yaxis.label.set_color(theme["text"])
        self.graph_axis.set_xlabel("x")
        self.graph_axis.set_ylabel("y")
        for spine in self.graph_axis.spines.values():
            spine.set_color(theme["border"])

    def format_graph_value(self, value: Any) -> str:
        if value != value:
            return "undefined"

        rounded = round(float(value), 6)
        if rounded.is_integer():
            return str(int(rounded))
        return str(rounded).rstrip("0").rstrip(".")

    def update_graph_table(self, series: GraphSeries) -> None:
        if not series:
            self.graph_table.setRowCount(0)
            self.graph_table.setColumnCount(0)
            return

        headers = ["x"] + [f"y ({line['label']})" for line in series]
        row_count = len(series[0]["x"])

        self.graph_table.clear()
        self.graph_table.setColumnCount(len(headers))
        self.graph_table.setRowCount(row_count)
        self.graph_table.setHorizontalHeaderLabels(headers)

        for row_index in range(row_count):
            x_item = QTableWidgetItem(self.format_graph_value(series[0]["x"][row_index]))
            self.graph_table.setItem(row_index, 0, x_item)

            for column_index, line in enumerate(series, start=1):
                y_item = QTableWidgetItem(self.format_graph_value(line["y"][row_index]))
                self.graph_table.setItem(row_index, column_index, y_item)

        self.graph_table.resizeColumnsToContents()

    def render_graph(self, graph_task: GraphTask) -> None:
        series: GraphSeries = build_graph_points(graph_task)
        labels = ", ".join(function["label"] for function in graph_task["functions"])
        self.graph_status.setText(f"Showing: {labels}")
        self.update_graph_table(series)

        if self.graph_plot_widget is not None:
            self.graph_plot_widget.clear()
            if self.graph_legend is not None:
                self.graph_legend.clear()
            # Draw every requested function on the same axes.
            for line in series:
                pg_module = cast(Any, pg)
                pen = pg_module.mkPen(color=line["color"], width=2.4)
                self.graph_plot_widget.plot(line["x"], line["y"], pen=pen, name=line["label"])
            self.graph_plot_widget.enableAutoRange()
            return

        if self.graph_axis is not None:
            self.style_matplotlib_axis()
            for line in series:
                self.graph_axis.plot(
                    line["x"],
                    line["y"],
                    color=line["color"],
                    linewidth=2.2,
                    label=line["label"]
                )
            self.graph_axis.legend(facecolor="#182028", edgecolor="#52606D", labelcolor="#EAEAEA")
            if self.graph_figure is not None:
                self.graph_figure.tight_layout()
            if self.graph_canvas is not None:
                self.graph_canvas.draw_idle()
            return

    def insert_typing_indicator(self) -> None:
        self.remove_typing_indicator()
        html = self.build_bubble_html("Typing", "ChatBot is thinking.")
        cursor = self.chat_box.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.typing_block_start = cursor.position()
        cursor.insertHtml(html)
        cursor.insertText("\n")
        self.typing_block_end = cursor.position()
        self.chat_box.setTextCursor(cursor)

    def remove_typing_indicator(self) -> None:
        if self.typing_block_start is None or self.typing_block_end is None:
            return

        document_limit = max(self.chat_box.document().characterCount() - 1, 0)
        if (
            self.typing_block_start < 0
            or self.typing_block_end < self.typing_block_start
            or self.typing_block_start > document_limit
            or self.typing_block_end > document_limit
        ):
            self.typing_block_start = None
            self.typing_block_end = None
            return

        cursor = self.chat_box.textCursor()
        cursor.setPosition(self.typing_block_start)
        cursor.setPosition(self.typing_block_end, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        self.chat_box.setTextCursor(cursor)
        self.typing_block_start = None
        self.typing_block_end = None

    def start_typing_indicator(self) -> None:
        self.typing_active = True
        self.typing_dot_count = 1
        self.insert_typing_indicator()
        self.typing_timer.start(350)

    def stop_typing_indicator(self) -> None:
        self.typing_active = False
        self.typing_timer.stop()
        self.remove_typing_indicator()

    def update_typing_indicator(self) -> None:
        if not self.typing_active:
            return

        self.typing_dot_count = 1 if self.typing_dot_count >= 3 else self.typing_dot_count + 1
        dots = "." * self.typing_dot_count

        self.remove_typing_indicator()
        html = self.build_bubble_html("Typing", f"ChatBot is thinking{dots}")
        cursor = self.chat_box.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.typing_block_start = cursor.position()
        cursor.insertHtml(html)
        cursor.insertText("\n")
        self.typing_block_end = cursor.position()
        self.chat_box.setTextCursor(cursor)

    def process_input(self, text: str) -> None:
        self.start_typing_indicator()
        # Small delay keeps the typing animation visible before the reply appears.
        QTimer.singleShot(500, lambda: self.finish_response(text))

    def finish_response(self, user_input: str) -> None:
        self.stop_typing_indicator()
        if is_graph_request(user_input):
            self.handle_graph_request(user_input)
            return
        response = chatbot_main.process_user_input(user_input)
        self.add_bot_message(response)
        self.refresh_all_data()

    def handle_graph_request(self, user_input: str) -> None:
        try:
            graph_task: GraphTask = parse_graph_request(user_input)
            self.render_graph(graph_task)
            summary = ", ".join(function["label"] for function in graph_task["functions"])
            self.add_bot_message(
                "Updated the right-side graph panel with dark mode, zoom, grid, and multiple-function support.\n\n"
                f"Graphing: {summary}"
            )
        except Exception as exc:
            self.add_bot_message(f"Could not graph that function.\n\n{exc}")

    def send_message(self) -> None:
        text = self.entry.text().strip()
        if not text:
            return
        self.entry.clear()
        self.add_user_message(text)
        self.process_input(text)

    def refresh_actions(self) -> None:
        self.action_combo.clear()
        for action_name, symbol in database_utilities.get_actions():
            self.action_combo.addItem(f"{action_name} ({symbol})", action_name)

    def refresh_trigger_words(self) -> None:
        self.trigger_word_combo.clear()
        for trigger_id, word, action_name, symbol in database_utilities.get_trigger_words():
            self.trigger_word_combo.addItem(f"{word} -> {action_name} ({symbol})", trigger_id)

        has_triggers = self.trigger_word_combo.count() > 0
        self.trigger_word_combo.setEnabled(has_triggers)
        self.btn_remove_trigger.setEnabled(has_triggers)

    def refresh_saved_equations(self) -> None:
        self.saved_equations_combo.clear()
        for equation_name, equation_text in database_utilities.get_saved_equations():
            self.saved_equations_combo.addItem(f"{equation_name} = {equation_text}", equation_name)

        has_equations = self.saved_equations_combo.count() > 0
        self.saved_equations_combo.setEnabled(has_equations)
        self.btn_load_equation.setEnabled(has_equations)

    def refresh_all_data(self) -> None:
        self.refresh_actions()
        self.refresh_trigger_words()
        self.refresh_saved_equations()

    def gui_refresh_data(self) -> None:
        self.refresh_all_data()
        self.add_bot_message("Data refreshed from the SQL database.")

    def gui_show_last_10(self) -> None:
        self.add_user_message("show last 10")
        self.process_input("show last 10")

    def gui_export_csv(self) -> None:
        self.add_user_message("export csv")
        self.process_input("export csv")

    def gui_clear_history(self) -> None:
        self.stop_typing_indicator()
        self.add_user_message("clear history")
        self.process_input("clear history")
        self.chat_box.clear()

    def gui_scan_homework(self) -> None:
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Homework Photo",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not image_path:
            return

        self.add_user_message(f"scan homework photo: {image_path}")

        try:
            scan_result = extract_math_lines(image_path)
        except Exception as exc:
            self.add_bot_message(f"Could not scan that image.\n\n{exc}")
            return

        extracted_lines: list[str] = scan_result["math_lines"]
        solved_sections: list[str] = []

        # Solve each OCR line with the same chatbot pipeline the user already uses.
        for line in extracted_lines:
            solved_sections.append(f"{line}\n{chatbot_main.process_user_input(line)}")

        response: str = (
            "I scanned the homework photo and found these math lines:\n\n"
            + "\n".join(extracted_lines)
            + "\n\nSolved Results:\n\n"
            + "\n\n".join(solved_sections)
        )
        self.add_bot_message(response)
        self.refresh_all_data()

    def gui_teach(self) -> None:
        word = self.teach_word_entry.text().strip()
        if not word:
            QMessageBox.warning(self, "Teach", "Enter a trigger word.")
            return

        action_name = cast(str | None, self.action_combo.currentData())
        if action_name is None:
            QMessageBox.warning(self, "Teach", "Select an action first.")
            return
        response = teach_trigger_word(word, action_name)
        self.add_user_message(f"teach {word} {action_name}")
        self.add_bot_message(response)
        self.teach_word_entry.clear()
        self.refresh_trigger_words()

    def gui_remove_trigger_word(self) -> None:
        trigger_id = cast(int | None, self.trigger_word_combo.currentData())
        if trigger_id is None:
            QMessageBox.warning(self, "Remove", "No trigger words are available to remove.")
            return

        trigger_text = self.trigger_word_combo.currentText()
        confirm = QMessageBox.question(
            self,
            "Remove Trigger Word",
            f"Remove {trigger_text}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, response = database_utilities.delete_trigger_word(trigger_id)
        if success:
            load_operations()
            self.refresh_trigger_words()

        self.add_user_message(f"remove trigger {trigger_text}")
        self.add_bot_message(response)

    def gui_load_saved_equation(self) -> None:
        equation_name = cast(str | None, self.saved_equations_combo.currentData())
        if equation_name is None:
            QMessageBox.warning(self, "Load Equation", "No saved equations are available.")
            return
        self.add_user_message(f"load {equation_name}")
        self.process_input(f"load {equation_name}")


if __name__ == "__main__":
    # Running this file directly starts the desktop GUI application.
    app = QApplication(sys.argv)
    def handle_sigint(*_: Any) -> None:
        app.quit()

    signal.signal(signal.SIGINT, handle_sigint)

    # This timer keeps Ctrl+C responsive while the Qt event loop is running.
    interrupt_timer = QTimer()
    interrupt_timer.timeout.connect(lambda: None)
    interrupt_timer.start(100)

    window = ChatbotGUI()
    window.show()
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        app.quit()
        sys.exit(0)

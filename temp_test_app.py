import sys

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import main as chatbot_main
from ocr_scanner import extract_math_lines


class TempTestApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Temp Calc Test App")
        self.resize(860, 620)
        self.build_ui()

    def build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Temporary Test App")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)

        hint = QLabel("Use this app to quickly test typed math or scan a homework photo.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Try: what is 400 divided by 2")
        self.entry.returnPressed.connect(self.solve_typed_input)
        input_row.addWidget(self.entry, 1)

        solve_button = QPushButton("Solve Text")
        solve_button.clicked.connect(self.solve_typed_input)
        input_row.addWidget(solve_button)

        scan_button = QPushButton("Scan Photo")
        scan_button.clicked.connect(self.scan_photo)
        input_row.addWidget(scan_button)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_output)
        input_row.addWidget(clear_button)

        layout.addLayout(input_row)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        self.append_output("ChatBot", "Temporary test app ready.")

    def append_output(self, label: str, text: str) -> None:
        self.output.append(f"{label}:\n{text}\n")

    def solve_typed_input(self) -> None:
        text = self.entry.text().strip()
        if not text:
            return

        self.entry.clear()
        self.append_output("You", text)
        self.append_output("ChatBot", str(chatbot_main.process_user_input(text)))

    def scan_photo(self) -> None:
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Homework Photo",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not image_path:
            return

        self.append_output("You", f"scan homework photo: {image_path}")

        try:
            scan_result = extract_math_lines(image_path)
        except Exception as exc:
            self.append_output("ChatBot", f"Could not scan that image.\n\n{exc}")
            return

        math_lines: list[str] = scan_result["math_lines"]
        solved_sections: list[str] = []

        # Reuse the same chatbot logic here so this test app matches the main app.
        for line in math_lines:
            solved_sections.append(f"{line}\n{chatbot_main.process_user_input(line)}")

        response = (
            "I scanned the homework photo and found these math lines:\n\n"
            + "\n".join(math_lines)
            + "\n\nSolved Results:\n\n"
            + "\n\n".join(solved_sections)
        )
        self.append_output("ChatBot", response)

    def clear_output(self) -> None:
        self.output.clear()
        self.append_output("ChatBot", "Temporary test app ready.")


if __name__ == "__main__":
    # Running this file directly starts a lightweight test window.
    app = QApplication(sys.argv)
    window = TempTestApp()
    window.show()
    sys.exit(app.exec())

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
)


class TableViewer(QDialog):
    def __init__(self, table_name, headers, rows):
        super().__init__()
        self.setWindowTitle(f"Table Viewer - {table_name}")
        self.resize(700, 400)

        layout = QVBoxLayout(self)

        title = QLabel(f"Table: {table_name}")
        title.setStyleSheet("font-size:16px; font-weight:bold; margin-bottom:8px;")
        layout.addWidget(title)

        table = QTableWidget()
        table.setRowCount(len(rows))
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        for row_index, row_data in enumerate(rows):
            for col_index, value in enumerate(row_data):
                table.setItem(row_index, col_index, QTableWidgetItem(str(value)))

        table.resizeColumnsToContents()
        layout.addWidget(table)

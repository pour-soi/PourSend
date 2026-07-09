from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from PySide6.QtCore import Qt

from core.importing import PastePreviewRow, preview_pasted_recipients


class PersonDialog(QDialog):
    def __init__(self, parent=None, phone: str = "", groups: list[str] | None = None, selected_group: str = "", notes: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Recipient")
        self.phone_edit = QLineEdit(phone)
        self.group_combo = QComboBox()
        for group in groups or []:
            self.group_combo.addItem(group)
        if selected_group:
            index = self.group_combo.findText(selected_group)
            if index >= 0:
                self.group_combo.setCurrentIndex(index)
        self.notes_edit = QTextEdit(notes)
        self.notes_edit.setFixedHeight(90)

        form = QFormLayout()
        form.addRow("Phone number", self.phone_edit)
        form.addRow("Group", self.group_combo)
        form.addRow("Notes", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, str]:
        return self.phone_edit.text().strip(), self.group_combo.currentText().strip(), self.notes_edit.toPlainText().strip()


class PasteListDialog(QDialog):
    def __init__(self, parent=None, existing_numbers: set[str] | None = None, groups: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Paste List")
        self.resize(760, 560)
        self.existing_numbers = existing_numbers or set()
        self.preview_rows: list[PastePreviewRow] = []

        self.input = QTextEdit()
        self.input.setPlaceholderText("Name, phone number\nName    phone number")
        self.preview = QTableWidget(0, 3)
        self.preview.setHorizontalHeaderLabels(["Original", "Normalized", "Status"])
        self.status = QLabel("Paste a list, then preview it before importing.")
        self.group_combo = QComboBox()
        for group in groups or []:
            self.group_combo.addItem(group)

        preview_button = QPushButton("Preview")
        preview_button.clicked.connect(self.refresh_preview)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Add All Recipients")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.input)
        layout.addWidget(preview_button)
        layout.addWidget(self.preview)
        layout.addWidget(QLabel("Group for new recipients"))
        layout.addWidget(self.group_combo)
        layout.addWidget(self.status)
        layout.addWidget(buttons)

    def refresh_preview(self) -> None:
        self.preview_rows = preview_pasted_recipients(self.input.toPlainText(), self.existing_numbers)
        self.preview.setRowCount(0)
        for row_data in self.preview_rows:
            row = self.preview.rowCount()
            self.preview.insertRow(row)
            for column, value in enumerate([
                row_data.phone,
                row_data.normalized or "-",
                row_data.status,
            ]):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.preview.setItem(row, column, item)
        self.preview.resizeColumnsToContents()
        valid = sum(1 for row in self.preview_rows if row.status == "Valid")
        duplicates = sum(1 for row in self.preview_rows if row.status == "Duplicate in this batch")
        existing = sum(1 for row in self.preview_rows if row.status == "Already exists")
        invalid = sum(1 for row in self.preview_rows if row.status == "Invalid")
        self.status.setText(
            f"Ready to add {valid}. Duplicates skipped: {duplicates}. "
            f"Already existed: {existing}. Invalid skipped: {invalid}."
        )

    def accept(self) -> None:
        self.refresh_preview()
        if self.rows_to_add():
            super().accept()

    def rows_to_add(self) -> list[PastePreviewRow]:
        return [row for row in self.preview_rows if row.status == "Valid"]

    def selected_group(self) -> str:
        return self.group_combo.currentText().strip()

    def summary_counts(self) -> tuple[int, int, int, int]:
        return (
            sum(1 for row in self.preview_rows if row.status == "Valid"),
            sum(1 for row in self.preview_rows if row.status == "Duplicate in this batch"),
            sum(1 for row in self.preview_rows if row.status == "Already exists"),
            sum(1 for row in self.preview_rows if row.status == "Invalid"),
        )

    def invalid_examples(self, limit: int = 5) -> list[str]:
        return [row.phone for row in self.preview_rows if row.status == "Invalid"][:limit]


class CsvColumnDialog(QDialog):
    def __init__(self, parent, columns: list[str]):
        super().__init__(parent)
        self.setWindowTitle("Choose CSV Columns")
        self.name_combo = QComboBox()
        self.phone_combo = QComboBox()
        self.name_combo.addItems(columns)
        self.phone_combo.addItems(columns)

        form = QFormLayout()
        form.addRow("Name column", self.name_combo)
        form.addRow("Phone column", self.phone_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose which columns contain each value."))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        return self.name_combo.currentText(), self.phone_combo.currentText()

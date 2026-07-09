from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
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

from core.importing import PastePreviewRow, invalid_examples, preview_pasted_recipients, preview_summary


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


class BatchEditDialog(QDialog):
    def __init__(self, parent=None, groups: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Batch Edit")
        self.change_group = QCheckBox("Change group")
        self.group_combo = QComboBox()
        for group in groups or []:
            self.group_combo.addItem(group)
        self.change_notes = QCheckBox("Replace notes")
        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(90)

        form = QFormLayout()
        form.addRow(self.change_group, self.group_combo)
        form.addRow(self.change_notes, self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str | None, str | None]:
        group = self.group_combo.currentText().strip() if self.change_group.isChecked() else None
        notes = self.notes_edit.toPlainText().strip() if self.change_notes.isChecked() else None
        return group, notes


class PasteListDialog(QDialog):
    def __init__(
        self,
        parent=None,
        existing_numbers: set[str] | None = None,
        groups: list[str] | None = None,
        jump_to_existing=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Paste List")
        self.resize(760, 560)
        self.existing_numbers = existing_numbers or set()
        self.preview_rows: list[PastePreviewRow] = []
        self.jump_to_existing = jump_to_existing

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
        existing_button = QPushButton("Show Existing")
        existing_button.clicked.connect(self.show_existing)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Add All Recipients")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.input)
        layout.addWidget(preview_button)
        layout.addWidget(existing_button)
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
        self.status.setText(format_preview_status(self.preview_rows))

    def accept(self) -> None:
        self.refresh_preview()
        if self.rows_to_add():
            super().accept()

    def rows_to_add(self) -> list[PastePreviewRow]:
        return [row for row in self.preview_rows if row.status == "Valid"]

    def selected_group(self) -> str:
        return self.group_combo.currentText().strip()

    def summary_counts(self) -> tuple[int, int, int, int]:
        summary = preview_summary(self.preview_rows)
        return summary.added, summary.duplicates, summary.already_exists, summary.invalid

    def invalid_examples(self, limit: int = 5) -> list[str]:
        return invalid_examples(self.preview_rows, limit)

    def show_existing(self) -> None:
        if self.jump_to_existing is None:
            return
        row = self.preview.currentRow()
        if row < 0 or row >= len(self.preview_rows):
            return
        preview_row = self.preview_rows[row]
        if preview_row.status == "Already exists" and preview_row.normalized:
            self.jump_to_existing(preview_row.normalized)


class ImportPreviewDialog(QDialog):
    def __init__(
        self,
        parent=None,
        rows: list[PastePreviewRow] | None = None,
        groups: list[str] | None = None,
        selected_group: str = "",
        jump_to_existing=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Import Preview")
        self.resize(760, 520)
        self.preview_rows = rows or []
        self.jump_to_existing = jump_to_existing

        self.preview = QTableWidget(0, 3)
        self.preview.setHorizontalHeaderLabels(["Original", "Normalized", "Status"])
        self.group_combo = QComboBox()
        for group in groups or []:
            self.group_combo.addItem(group)
        if selected_group:
            index = self.group_combo.findText(selected_group)
            if index >= 0:
                self.group_combo.setCurrentIndex(index)
        self.status = QLabel(format_preview_status(self.preview_rows))

        existing_button = QPushButton("Show Existing")
        existing_button.clicked.connect(self.show_existing)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Import Added Recipients")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview)
        layout.addWidget(existing_button)
        layout.addWidget(QLabel("Group for new recipients"))
        layout.addWidget(self.group_combo)
        layout.addWidget(self.status)
        layout.addWidget(buttons)
        self.refresh_preview()

    def refresh_preview(self) -> None:
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

    def rows_to_add(self) -> list[PastePreviewRow]:
        return [row for row in self.preview_rows if row.status == "Valid"]

    def selected_group(self) -> str:
        return self.group_combo.currentText().strip()

    def summary_counts(self) -> tuple[int, int, int, int]:
        summary = preview_summary(self.preview_rows)
        return summary.added, summary.duplicates, summary.already_exists, summary.invalid

    def invalid_examples(self, limit: int = 5) -> list[str]:
        return invalid_examples(self.preview_rows, limit)

    def show_existing(self) -> None:
        if self.jump_to_existing is None:
            return
        row = self.preview.currentRow()
        if row < 0 or row >= len(self.preview_rows):
            return
        preview_row = self.preview_rows[row]
        if preview_row.status == "Already exists" and preview_row.normalized:
            self.jump_to_existing(preview_row.normalized)


def format_preview_status(rows: list[PastePreviewRow]) -> str:
    summary = preview_summary(rows)
    lines = [
        f"Extracted: {summary.extracted}",
        f"Added: {summary.added}",
        f"Already Exists: {summary.already_exists}",
        f"Duplicates: {summary.duplicates}",
        f"Invalid: {summary.invalid}",
    ]
    examples = invalid_examples(rows)
    if examples:
        lines.append("Invalid examples:")
        lines.extend(examples)
    return "\n".join(lines)


class ExportDialog(QDialog):
    def __init__(self, parent=None, count_by_scope: dict[str, int] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Export Recipients")
        self.format_combo = QComboBox()
        self.format_combo.addItem("TXT", "txt")
        self.format_combo.addItem("CSV", "csv")
        self.format_combo.addItem("Excel", "xlsx")
        self.scope_combo = QComboBox()
        for label, value in [
            ("All", "all"),
            ("Current Group", "group"),
            ("Current Search", "search"),
            ("Current Selection", "selection"),
        ]:
            count = (count_by_scope or {}).get(value, 0)
            self.scope_combo.addItem(f"{label} ({count})", value)

        form = QFormLayout()
        form.addRow("Format", self.format_combo)
        form.addRow("Scope", self.scope_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        return self.format_combo.currentData(), self.scope_combo.currentData()


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

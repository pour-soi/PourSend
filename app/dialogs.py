from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.importing import ParsedRecipient, RejectedRow, parse_pasted_list


class PersonDialog(QDialog):
    def __init__(self, parent=None, name: str = "", phone: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Person")
        self.name_edit = QLineEdit(name)
        self.phone_edit = QLineEdit(phone)

        form = QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Phone number", self.phone_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.phone_edit.text().strip()


class PasteListDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paste List")
        self.resize(680, 500)
        self.accepted_rows: list[ParsedRecipient] = []
        self.rejected_rows: list[RejectedRow] = []

        self.input = QTextEdit()
        self.input.setPlaceholderText("Name, phone number\nName    phone number")
        self.preview = QListWidget()
        self.status = QLabel("Paste a list, then preview it before importing.")

        preview_button = QPushButton("Preview")
        preview_button.clicked.connect(self.refresh_preview)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.input)
        layout.addWidget(preview_button)
        layout.addWidget(self.preview)
        layout.addWidget(self.status)
        layout.addWidget(buttons)

    def refresh_preview(self) -> None:
        self.preview.clear()
        self.accepted_rows, self.rejected_rows = parse_pasted_list(self.input.toPlainText())
        for row in self.accepted_rows:
            self.preview.addItem(f"Import: {row.name} | {row.phone}")
        for row in self.rejected_rows:
            self.preview.addItem(f"Skip: {row.source} | {row.reason}")
        self.status.setText(f"Ready to import {len(self.accepted_rows)} rows. Skipping {len(self.rejected_rows)} malformed rows.")

    def accept(self) -> None:
        self.refresh_preview()
        if self.accepted_rows:
            super().accept()


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

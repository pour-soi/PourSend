from __future__ import annotations

import csv
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.dialogs import CsvColumnDialog, PasteListDialog, PersonDialog
from app.storage import load_recipients, save_recipients
from core.importing import detect_csv_columns, read_csv_recipients
from core.phone import normalize_us_phone
from core.recipients import build_clipboard_output


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RingCentral Recipient Prep")
        self.resize(1040, 680)
        self.recipients, load_error = load_recipients()
        self._building_table = False
        self._build_ui()
        self.refresh_table()
        if load_error:
            QMessageBox.warning(self, "Local data", load_error)

    def _build_ui(self) -> None:
        title = QLabel("RingCentral Recipient Prep")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name or phone number")
        self.search.textChanged.connect(self.refresh_table)

        add_button = QPushButton("Add Person")
        paste_button = QPushButton("Paste List")
        import_button = QPushButton("Import CSV")
        add_button.clicked.connect(self.add_person)
        paste_button.clicked.connect(self.paste_list)
        import_button.clicked.connect(self.import_csv)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addWidget(self.search, stretch=1)
        top.addWidget(add_button)
        top.addWidget(paste_button)
        top.addWidget(import_button)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Select", "Name", "Phone number", "Normalized", "Status"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 210)
        self.table.setColumnWidth(2, 190)
        self.table.setColumnWidth(3, 190)
        self.table.itemChanged.connect(self.table_item_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self.edit_selected())

        select_all = QPushButton("Select All")
        deselect_all = QPushButton("Deselect All")
        edit_button = QPushButton("Edit Person")
        delete_button = QPushButton("Delete Person")
        export_button = QPushButton("Export Backup")
        clear_button = QPushButton("Clear All Data")
        select_all.clicked.connect(lambda: self.set_all_visible(True))
        deselect_all.clicked.connect(lambda: self.set_all_visible(False))
        edit_button.clicked.connect(self.edit_selected)
        delete_button.clicked.connect(self.delete_selected)
        export_button.clicked.connect(self.export_backup)
        clear_button.clicked.connect(self.clear_all)

        tools = QHBoxLayout()
        for button in [select_all, deselect_all, edit_button, delete_button, export_button, clear_button]:
            tools.addWidget(button)
        tools.addStretch(1)

        self.format_combo = QComboBox()
        self.format_combo.addItem("Comma-separated", "comma")
        self.format_combo.addItem("Semicolon-separated", "semicolon")
        self.format_combo.addItem("One number per line", "newline")
        self.count_label = QLabel("")
        copy_button = QPushButton("Copy Selected Numbers")
        copy_button.setMinimumHeight(48)
        copy_button.setStyleSheet("font-size: 17px; font-weight: 600;")
        copy_button.clicked.connect(self.copy_selected)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Output format"))
        bottom.addWidget(self.format_combo)
        bottom.addStretch(1)
        bottom.addWidget(self.count_label)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addLayout(tools)
        layout.addLayout(bottom)
        layout.addWidget(copy_button)

        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

        self.addAction(self._shortcut("Ctrl+N", self.add_person))
        self.addAction(self._shortcut("Ctrl+F", lambda: self.search.setFocus()))
        self.addAction(self._shortcut("Delete", self.delete_selected))

    def _shortcut(self, keys: str, slot) -> QAction:
        action = QAction(self)
        action.setShortcut(QKeySequence(keys))
        action.triggered.connect(slot)
        return action

    def refresh_table(self) -> None:
        query = self.search.text().strip().lower()
        self._building_table = True
        self.table.setRowCount(0)
        for index, recipient in enumerate(self.recipients):
            haystack = f"{recipient.get('name', '')} {recipient.get('phone', '')}".lower()
            if query and query not in haystack:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(str(index)))
            checked = QTableWidgetItem("")
            checked.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            checked.setCheckState(Qt.Checked if recipient.get("selected") else Qt.Unchecked)
            self.table.setItem(row, 0, checked)
            self.table.setItem(row, 1, QTableWidgetItem(recipient.get("name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(recipient.get("phone", "")))
            normalized, status = normalize_us_phone(recipient.get("phone", ""))
            normalized_item = QTableWidgetItem(normalized)
            normalized_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            normalized_item.setToolTip(normalized)
            self.table.setItem(row, 3, normalized_item)
            status_item = QTableWidgetItem(status)
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            status_item.setToolTip(status)
            self.table.setItem(row, 4, status_item)
        self._building_table = False
        self.update_counts()

    def table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._building_table:
            return
        index = self._recipient_index(item.row())
        if index is None:
            return
        if item.column() == 0:
            self.recipients[index]["selected"] = item.checkState() == Qt.Checked
        elif item.column() == 1:
            self.recipients[index]["name"] = item.text().strip()
        elif item.column() == 2:
            self.recipients[index]["phone"] = item.text().strip()
            self.refresh_table()
        self.save_and_update()

    def _recipient_index(self, visible_row: int) -> int | None:
        header = self.table.verticalHeaderItem(visible_row)
        if header is None:
            return None
        return int(header.text())

    def selected_visible_index(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return self._recipient_index(row)

    def add_person(self) -> None:
        dialog = PersonDialog(self)
        if dialog.exec() != PersonDialog.Accepted:
            return
        name, phone = dialog.values()
        if not name or not phone:
            QMessageBox.warning(self, "Add person", "Enter both a name and phone number.")
            return
        self.recipients.append({"name": name, "phone": phone, "selected": False})
        self.save_and_update()

    def paste_list(self) -> None:
        dialog = PasteListDialog(self)
        if dialog.exec() != PasteListDialog.Accepted:
            return
        for row in dialog.accepted_rows:
            self.recipients.append({"name": row.name, "phone": row.phone, "selected": False})
        self.save_and_update()
        QMessageBox.information(self, "Paste list", f"Imported {len(dialog.accepted_rows)} rows. Skipped {len(dialog.rejected_rows)} malformed rows.")

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV files (*.csv);;All files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                columns = list(reader.fieldnames or [])
        except (OSError, csv.Error) as exc:
            QMessageBox.critical(self, "Import CSV", f"The CSV file could not be opened: {exc}")
            return
        if not columns:
            QMessageBox.warning(self, "Import CSV", "The CSV file is empty or has no header row.")
            return

        name_column, phone_column = detect_csv_columns(columns)
        if not name_column or not phone_column:
            dialog = CsvColumnDialog(self, columns)
            if dialog.exec() != CsvColumnDialog.Accepted:
                return
            name_column, phone_column = dialog.values()

        try:
            accepted, rejected = read_csv_recipients(path, name_column, phone_column)
        except (OSError, csv.Error) as exc:
            QMessageBox.critical(self, "Import CSV", f"The CSV file could not be imported: {exc}")
            return

        if not accepted:
            QMessageBox.warning(self, "Import CSV", "No usable rows were found in the CSV file.")
            return
        for row in accepted:
            self.recipients.append({"name": row.name, "phone": row.phone, "selected": False})
        self.save_and_update()
        QMessageBox.information(self, "Import CSV", f"Imported {len(accepted)} rows. Skipped {len(rejected)} malformed rows.")

    def edit_selected(self) -> None:
        index = self.selected_visible_index()
        if index is None:
            QMessageBox.information(self, "Edit person", "Select one person to edit.")
            return
        recipient = self.recipients[index]
        dialog = PersonDialog(self, recipient.get("name", ""), recipient.get("phone", ""))
        if dialog.exec() != PersonDialog.Accepted:
            return
        name, phone = dialog.values()
        if not name or not phone:
            QMessageBox.warning(self, "Edit person", "Enter both a name and phone number.")
            return
        recipient["name"] = name
        recipient["phone"] = phone
        self.save_and_update()

    def delete_selected(self) -> None:
        indexes = sorted({self._recipient_index(item.row()) for item in self.table.selectedItems() if self._recipient_index(item.row()) is not None}, reverse=True)
        if not indexes:
            index = self.selected_visible_index()
            indexes = [] if index is None else [index]
        if not indexes:
            QMessageBox.information(self, "Delete person", "Select one or more people to delete.")
            return
        for index in indexes:
            del self.recipients[index]
        self.save_and_update()

    def set_all_visible(self, selected: bool) -> None:
        for row in range(self.table.rowCount()):
            index = self._recipient_index(row)
            if index is not None:
                self.recipients[index]["selected"] = selected
        self.save_and_update()

    def copy_selected(self) -> None:
        result = build_clipboard_output(self.recipients, self.format_combo.currentData())
        if result.selected == 0:
            QMessageBox.information(self, "Copy selected numbers", "No recipients are selected.")
            return
        if result.copied == 0:
            QMessageBox.warning(self, "Copy selected numbers", "No valid selected phone numbers were found.")
            return
        try:
            QApplication.clipboard().setText(result.output)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Copy selected numbers", f"The numbers could not be copied: {exc}")
            return
        QMessageBox.information(
            self,
            "Copy selected numbers",
            f"Copied {result.copied} unique phone numbers.\n\n"
            f"Selected: {result.selected}\n"
            f"Copied: {result.copied}\n"
            f"Duplicates removed: {result.duplicates_removed}\n"
            f"Invalid skipped: {result.invalid_skipped}",
        )

    def export_backup(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Backup", "recipients-backup.json", "JSON files (*.json)")
        if not path:
            return
        error = save_recipients_to_path(self.recipients, path)
        if error:
            QMessageBox.critical(self, "Export backup", error)
        else:
            QMessageBox.information(self, "Export backup", "Backup exported.")

    def clear_all(self) -> None:
        answer = QMessageBox.question(self, "Clear all data", "Clear all saved recipients?")
        if answer != QMessageBox.Yes:
            return
        self.recipients.clear()
        self.save_and_update()

    def save_and_update(self) -> None:
        error = save_recipients(self.recipients)
        self.refresh_table()
        if error:
            QMessageBox.warning(self, "Local data", error)

    def update_counts(self) -> None:
        selected = sum(1 for recipient in self.recipients if recipient.get("selected"))
        self.count_label.setText(f"Selected: {selected} | Total: {len(self.recipients)}")


def save_recipients_to_path(recipients: list[dict], path: str) -> str | None:
    import json

    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(recipients, handle, indent=2)
    except OSError as exc:
        return f"Could not export backup: {exc}"
    return None


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

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
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.dialogs import CsvColumnDialog, PasteListDialog, PersonDialog
from app.storage import load_recipient_data, make_saved_data, save_recipient_data
from core.groups import (
    ALL_RECIPIENTS,
    UNASSIGNED,
    assign_to_group,
    collect_groups,
    create_group,
    delete_group,
    filtered_recipient_indexes,
    normalize_recipient_groups,
    remove_from_group,
    rename_group,
    set_selected,
)
from core.importing import detect_csv_columns, read_csv_recipients, rows_to_add
from core.phone import normalize_us_phone
from core.recipients import build_clipboard_output


ALL_RECIPIENTS_LABEL = "All Recipients"
UNASSIGNED_LABEL = "Unassigned"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RingCentral Recipient Prep")
        self.resize(1180, 700)
        self.recipients, self.groups, load_error = load_recipient_data()
        self._building_table = False
        self._building_groups = False
        self._build_ui()
        self.refresh_group_list()
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

        self.group_list = QListWidget()
        self.group_list.currentItemChanged.connect(lambda _current, _previous: self.refresh_table())
        self.group_list.setMinimumWidth(180)

        new_group_button = QPushButton("New Group")
        rename_group_button = QPushButton("Rename Group")
        delete_group_button = QPushButton("Delete Group")
        assign_group_button = QPushButton("Assign Checked")
        remove_group_button = QPushButton("Remove Checked")
        new_group_button.clicked.connect(self.create_group)
        rename_group_button.clicked.connect(self.rename_group)
        delete_group_button.clicked.connect(self.delete_group)
        assign_group_button.clicked.connect(self.assign_checked_to_group)
        remove_group_button.clicked.connect(self.remove_checked_from_current_group)

        group_tools = QVBoxLayout()
        group_tools.addWidget(QLabel("Groups"))
        group_tools.addWidget(self.group_list, stretch=1)
        for button in [
            new_group_button,
            rename_group_button,
            delete_group_button,
            assign_group_button,
            remove_group_button,
        ]:
            group_tools.addWidget(button)

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

        select_all = QPushButton("Select All in This Group")
        deselect_all = QPushButton("Deselect All in This Group")
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

        main_layout = QHBoxLayout()
        main_layout.addLayout(group_tools)
        main_layout.addLayout(layout, stretch=1)

        root = QWidget()
        root.setLayout(main_layout)
        self.setCentralWidget(root)

        self.addAction(self._shortcut("Ctrl+N", self.add_person))
        self.addAction(self._shortcut("Ctrl+F", lambda: self.search.setFocus()))
        self.addAction(self._shortcut("Delete", self.delete_selected))

    def _shortcut(self, keys: str, slot) -> QAction:
        action = QAction(self)
        action.setShortcut(QKeySequence(keys))
        action.triggered.connect(slot)
        return action

    def current_group_filter(self) -> str:
        item = self.group_list.currentItem()
        if item is None:
            return ALL_RECIPIENTS
        return item.data(Qt.UserRole)

    def current_named_group(self) -> str | None:
        group = self.current_group_filter()
        if group in {ALL_RECIPIENTS, UNASSIGNED}:
            return None
        return group

    def refresh_group_list(self, selected_group: str | None = None) -> None:
        current = selected_group or self.current_group_filter()
        self.groups = collect_groups(self.recipients, self.groups)
        self._building_groups = True
        self.group_list.clear()
        for label, value in [(ALL_RECIPIENTS_LABEL, ALL_RECIPIENTS), (UNASSIGNED_LABEL, UNASSIGNED)]:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, value)
            self.group_list.addItem(item)
        for group in self.groups:
            item = QListWidgetItem(group)
            item.setData(Qt.UserRole, group)
            self.group_list.addItem(item)

        row_to_select = 0
        for row in range(self.group_list.count()):
            if self.group_list.item(row).data(Qt.UserRole) == current:
                row_to_select = row
                break
        self.group_list.setCurrentRow(row_to_select)
        self._building_groups = False

    def refresh_table(self) -> None:
        if self._building_groups:
            return
        query = self.search.text().strip().lower()
        self._building_table = True
        self.table.setRowCount(0)
        for index in filtered_recipient_indexes(self.recipients, self.current_group_filter(), query):
            recipient = self.recipients[index]
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

    def checked_visible_indexes(self) -> list[int]:
        indexes: list[int] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            index = self._recipient_index(row)
            if item is not None and index is not None and item.checkState() == Qt.Checked:
                indexes.append(index)
        return indexes

    def add_person(self) -> None:
        dialog = PersonDialog(self, groups=self.groups)
        if dialog.exec() != PersonDialog.Accepted:
            return
        name, phone, groups = dialog.values()
        if not name or not phone:
            QMessageBox.warning(self, "Add person", "Enter both a name and phone number.")
            return
        self.recipients.append({"name": name, "phone": phone, "selected": False, "groups": groups})
        self.save_and_update()

    def paste_list(self) -> None:
        dialog = PasteListDialog(self, self.existing_normalized_numbers(), self.groups)
        if dialog.exec() != PasteListDialog.Accepted:
            return
        groups = dialog.selected_groups()
        for recipient in rows_to_add(dialog.rows_to_add(), groups):
            self.recipients.append(recipient)
        self.save_and_update()
        added, duplicates, existing, invalid = dialog.summary_counts()
        QMessageBox.information(
            self,
            "Paste list",
            f"Added: {added}\n"
            f"Duplicates skipped: {duplicates}\n"
            f"Already existed: {existing}\n"
            f"Invalid skipped: {invalid}",
        )

    def existing_normalized_numbers(self) -> set[str]:
        numbers: set[str] = set()
        for recipient in self.recipients:
            normalized, status = normalize_us_phone(recipient.get("phone", ""))
            if status == "Valid":
                numbers.add(normalized)
        return numbers

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
            self.recipients.append({"name": row.name, "phone": row.phone, "selected": False, "groups": []})
        self.save_and_update()
        QMessageBox.information(self, "Import CSV", f"Imported {len(accepted)} rows. Skipped {len(rejected)} malformed rows.")

    def edit_selected(self) -> None:
        index = self.selected_visible_index()
        if index is None:
            QMessageBox.information(self, "Edit person", "Select one person to edit.")
            return
        recipient = self.recipients[index]
        dialog = PersonDialog(
            self,
            recipient.get("name", ""),
            recipient.get("phone", ""),
            self.groups,
            normalize_recipient_groups(recipient),
        )
        if dialog.exec() != PersonDialog.Accepted:
            return
        name, phone, groups = dialog.values()
        if not name or not phone:
            QMessageBox.warning(self, "Edit person", "Enter both a name and phone number.")
            return
        recipient["name"] = name
        recipient["phone"] = phone
        recipient["groups"] = groups
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
        set_selected(self.recipients, [index for index in self.checked_or_visible_indexes()], selected)
        self.save_and_update()

    def checked_or_visible_indexes(self) -> list[int]:
        return [
            index
            for row in range(self.table.rowCount())
            for index in [self._recipient_index(row)]
            if index is not None
        ]

    def create_group(self) -> None:
        name, ok = QInputDialog.getText(self, "New group", "Group name")
        if not ok:
            return
        if not create_group(self.groups, name):
            QMessageBox.warning(self, "New group", "Enter a unique group name.")
            return
        self.save_and_update(selected_group=name.strip())

    def rename_group(self) -> None:
        group = self.current_named_group()
        if group is None:
            QMessageBox.information(self, "Rename group", "Select a user-created group to rename.")
            return
        name, ok = QInputDialog.getText(self, "Rename group", "Group name", text=group)
        if not ok:
            return
        if not rename_group(self.recipients, self.groups, group, name):
            QMessageBox.warning(self, "Rename group", "Enter a unique group name.")
            return
        self.save_and_update(selected_group=name.strip())

    def delete_group(self) -> None:
        group = self.current_named_group()
        if group is None:
            QMessageBox.information(self, "Delete group", "Select a user-created group to delete.")
            return
        answer = QMessageBox.question(self, "Delete group", f"Delete group '{group}'? Recipients will not be deleted.")
        if answer != QMessageBox.Yes:
            return
        delete_group(self.recipients, self.groups, group)
        self.save_and_update(selected_group=ALL_RECIPIENTS)

    def assign_checked_to_group(self) -> None:
        indexes = self.checked_visible_indexes()
        if not indexes:
            QMessageBox.information(self, "Assign to group", "Check one or more visible recipients first.")
            return
        if not self.groups:
            QMessageBox.information(self, "Assign to group", "Create a group first.")
            return
        group, ok = QInputDialog.getItem(self, "Assign to group", "Group", self.groups, 0, False)
        if not ok:
            return
        assign_to_group(self.recipients, indexes, group)
        self.save_and_update(selected_group=self.current_group_filter())

    def remove_checked_from_current_group(self) -> None:
        group = self.current_named_group()
        if group is None:
            QMessageBox.information(self, "Remove from group", "Open a user-created group first.")
            return
        indexes = self.checked_visible_indexes()
        if not indexes:
            QMessageBox.information(self, "Remove from group", "Check one or more visible recipients first.")
            return
        remove_from_group(self.recipients, indexes, group)
        self.save_and_update(selected_group=group)

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
        error = save_recipients_to_path(self.recipients, self.groups, path)
        if error:
            QMessageBox.critical(self, "Export backup", error)
        else:
            QMessageBox.information(self, "Export backup", "Backup exported.")

    def clear_all(self) -> None:
        answer = QMessageBox.question(self, "Clear all data", "Clear all saved recipients?")
        if answer != QMessageBox.Yes:
            return
        self.recipients.clear()
        self.groups.clear()
        self.save_and_update(selected_group=ALL_RECIPIENTS)

    def save_and_update(self, selected_group: str | None = None) -> None:
        self.groups = collect_groups(self.recipients, self.groups)
        error = save_recipient_data(self.recipients, self.groups)
        self.refresh_group_list(selected_group)
        self.refresh_table()
        if error:
            QMessageBox.warning(self, "Local data", error)

    def update_counts(self) -> None:
        visible_indexes = self.checked_or_visible_indexes()
        visible_selected = sum(1 for index in visible_indexes if self.recipients[index].get("selected"))
        total_selected = sum(1 for recipient in self.recipients if recipient.get("selected"))
        self.count_label.setText(
            f"Visible selected: {visible_selected} | Total selected: {total_selected} | "
            f"Visible: {len(visible_indexes)} | Total: {len(self.recipients)}"
        )


def save_recipients_to_path(recipients: list[dict], groups: list[str], path: str) -> str | None:
    import json

    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(make_saved_data(recipients, groups), handle, indent=2)
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

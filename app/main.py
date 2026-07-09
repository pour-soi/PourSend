from __future__ import annotations

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

from app.dialogs import PasteListDialog, PersonDialog
from app.storage import load_recipient_data, make_saved_data, save_recipient_data
from core.groups import (
    ALL_RECIPIENTS,
    assign_to_group,
    collect_groups,
    create_group,
    DEFAULT_GROUP,
    delete_group,
    filtered_recipient_indexes,
    normalize_recipient_group,
    preferred_group,
    recipient_phone_key,
    rename_group,
    set_selected,
    valid_group_or_default,
)
from core.importing import preview_import_file, rows_to_add
from core.phone import normalize_us_phone
from core.recipients import build_clipboard_output


ALL_RECIPIENTS_LABEL = "All Recipients"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PourSend")
        self.resize(1180, 700)
        self.recipients, self.groups, load_error = load_recipient_data()
        self.recent_group = DEFAULT_GROUP
        self._building_table = False
        self._building_groups = False
        self._build_ui()
        self.refresh_group_list()
        self.refresh_table()
        if load_error:
            QMessageBox.warning(self, "Local data", load_error)

    def _build_ui(self) -> None:
        title = QLabel("PourSend")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by phone number or notes")
        self.search.textChanged.connect(self.refresh_table)

        add_button = QPushButton("Add Recipient")
        paste_button = QPushButton("Paste List")
        import_button = QPushButton("Import File")
        add_button.clicked.connect(self.add_person)
        paste_button.clicked.connect(self.paste_list)
        import_button.clicked.connect(self.import_csv)

        self.group_list = QListWidget()
        self.group_list.currentItemChanged.connect(lambda _current, _previous: self.refresh_table())
        self.group_list.setMinimumWidth(180)

        new_group_button = QPushButton("New Group")
        rename_group_button = QPushButton("Rename Group")
        delete_group_button = QPushButton("Delete Group")
        assign_group_button = QPushButton("Move Checked")
        remove_group_button = QPushButton("Move Checked to Default")
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
        self.table.setHorizontalHeaderLabels(["Select", "Phone number", "Group", "Notes", "Status"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 190)
        self.table.setColumnWidth(2, 170)
        self.table.setColumnWidth(3, 260)
        self.table.itemChanged.connect(self.table_item_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self.edit_selected())

        select_all = QPushButton("Select All in This Group")
        deselect_all = QPushButton("Deselect All in This Group")
        edit_button = QPushButton("Edit Recipient")
        delete_button = QPushButton("Delete Recipient")
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
        if group == ALL_RECIPIENTS:
            return None
        return group

    def preferred_group(self) -> str:
        return preferred_group(self.current_named_group(), self.recent_group, self.groups)

    def refresh_group_list(self, selected_group: str | None = None) -> None:
        current = selected_group or self.current_group_filter()
        self.groups = collect_groups(self.recipients, self.groups)
        self._building_groups = True
        self.group_list.clear()
        for label, value in [(ALL_RECIPIENTS_LABEL, ALL_RECIPIENTS)]:
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
            self.table.setItem(row, 1, QTableWidgetItem(recipient.get("phone", "")))
            group_item = QTableWidgetItem(normalize_recipient_group(recipient, self.groups))
            group_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 2, group_item)
            self.table.setItem(row, 3, QTableWidgetItem(recipient.get("notes", "")))
            normalized, status = normalize_us_phone(recipient.get("phone", ""))
            status_item = QTableWidgetItem(status)
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            status_item.setToolTip(normalized or status)
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
            phone = item.text().strip()
            normalized, status = normalize_us_phone(phone)
            if status == "Valid":
                key = normalized
                duplicate = any(
                    other_index != index and recipient_phone_key(recipient) == key
                    for other_index, recipient in enumerate(self.recipients)
                )
                if duplicate:
                    QMessageBox.warning(self, "Edit recipient", "That phone number already exists.")
                    self.refresh_table()
                    return
                self.recipients[index]["phone"] = normalized
            else:
                self.recipients[index]["phone"] = phone
            self.refresh_table()
        elif item.column() == 3:
            self.recipients[index]["notes"] = item.text().strip()
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
        dialog = PersonDialog(self, groups=self.groups, selected_group=self.preferred_group())
        if dialog.exec() != PersonDialog.Accepted:
            return
        phone, group, notes = dialog.values()
        normalized, status = normalize_us_phone(phone)
        if status != "Valid":
            QMessageBox.warning(self, "Add recipient", status)
            return
        if normalized in self.existing_normalized_numbers():
            QMessageBox.warning(self, "Add recipient", "That phone number already exists.")
            return
        group = self.valid_group(group)
        self.recipients.append({"phone": normalized, "selected": False, "group": group, "groups": [group], "notes": notes})
        self.recent_group = group
        self.save_and_update(selected_group=group)

    def paste_list(self) -> None:
        dialog = PasteListDialog(self, self.existing_normalized_numbers(), self.groups)
        if dialog.exec() != PasteListDialog.Accepted:
            return
        group = self.valid_group(dialog.selected_group())
        for recipient in rows_to_add(dialog.rows_to_add(), group):
            self.recipients.append(recipient)
        self.recent_group = group
        self.save_and_update(selected_group=group)
        added, duplicates, existing, invalid = dialog.summary_counts()
        extracted = added + duplicates + existing + invalid
        invalid_examples = dialog.invalid_examples()
        invalid_text = ""
        if invalid_examples:
            invalid_text = "\nInvalid examples:\n" + "\n".join(invalid_examples)
        QMessageBox.information(
            self,
            "Paste list",
            f"Extracted: {extracted}\n"
            f"Added: {added}\n"
            f"Duplicates skipped: {duplicates}\n"
            f"Already existed: {existing}\n"
            f"Invalid skipped: {invalid}"
            f"{invalid_text}",
        )

    def existing_normalized_numbers(self) -> set[str]:
        numbers: set[str] = set()
        for recipient in self.recipients:
            normalized, status = normalize_us_phone(recipient.get("phone", ""))
            if status == "Valid":
                numbers.add(normalized)
        return numbers

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import File",
            "",
            "Import files (*.txt *.csv *.xlsx);;Text files (*.txt);;CSV files (*.csv);;Excel files (*.xlsx);;All files (*)",
        )
        if not path:
            return
        try:
            preview_rows = preview_import_file(path, self.existing_normalized_numbers())
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Import file", f"The file could not be imported: {exc}")
            return
        group = self.preferred_group()
        recipients = rows_to_add(preview_rows, group)
        if not recipients:
            QMessageBox.warning(self, "Import file", "No new valid phone numbers were found in the file.")
            return
        for recipient in recipients:
            self.recipients.append(recipient)
        self.recent_group = group
        self.save_and_update(selected_group=group)
        added = len(recipients)
        duplicates = sum(1 for row in preview_rows if row.status == "Duplicate in this batch")
        existing = sum(1 for row in preview_rows if row.status == "Already exists")
        invalid = sum(1 for row in preview_rows if row.status == "Invalid")
        QMessageBox.information(
            self,
            "Import file",
            f"Added: {added}\n"
            f"Duplicates skipped: {duplicates}\n"
            f"Already existed: {existing}\n"
            f"Invalid skipped: {invalid}",
        )

    def edit_selected(self) -> None:
        index = self.selected_visible_index()
        if index is None:
            QMessageBox.information(self, "Edit person", "Select one person to edit.")
            return
        recipient = self.recipients[index]
        dialog = PersonDialog(
            self,
            recipient.get("phone", ""),
            self.groups,
            normalize_recipient_group(recipient, self.groups),
            recipient.get("notes", ""),
        )
        if dialog.exec() != PersonDialog.Accepted:
            return
        phone, group, notes = dialog.values()
        normalized, status = normalize_us_phone(phone)
        if status != "Valid":
            QMessageBox.warning(self, "Edit recipient", status)
            return
        if any(other_index != index and recipient_phone_key(other) == normalized for other_index, other in enumerate(self.recipients)):
            QMessageBox.warning(self, "Edit recipient", "That phone number already exists.")
            return
        group = self.valid_group(group)
        recipient["phone"] = normalized
        recipient["group"] = group
        recipient["groups"] = [group]
        recipient["notes"] = notes
        self.recent_group = group
        self.save_and_update(selected_group=group)

    def delete_selected(self) -> None:
        indexes = sorted({self._recipient_index(item.row()) for item in self.table.selectedItems() if self._recipient_index(item.row()) is not None}, reverse=True)
        if not indexes:
            index = self.selected_visible_index()
            indexes = [] if index is None else [index]
        if not indexes:
            QMessageBox.information(self, "Delete recipient", "Select one or more recipients to delete.")
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
        if group is None or group == DEFAULT_GROUP:
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
        if group is None or group == DEFAULT_GROUP:
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
            QMessageBox.information(self, "Move to group", "Check one or more visible recipients first.")
            return
        if not self.groups:
            QMessageBox.information(self, "Move to group", "Create a group first.")
            return
        group, ok = QInputDialog.getItem(self, "Move to group", "Group", self.groups, 0, False)
        if not ok:
            return
        assign_to_group(self.recipients, indexes, group)
        self.recent_group = group
        self.save_and_update(selected_group=self.current_group_filter())

    def remove_checked_from_current_group(self) -> None:
        indexes = self.checked_visible_indexes()
        if not indexes:
            QMessageBox.information(self, "Move to default", "Check one or more visible recipients first.")
            return
        assign_to_group(self.recipients, indexes, DEFAULT_GROUP)
        self.recent_group = DEFAULT_GROUP
        self.save_and_update(selected_group=DEFAULT_GROUP)

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
        if self.recent_group not in self.groups:
            self.recent_group = DEFAULT_GROUP
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

    def valid_group(self, group: str) -> str:
        return valid_group_or_default(group, self.groups)


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

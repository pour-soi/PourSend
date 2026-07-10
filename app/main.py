from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, Qt
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
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.dialogs import BatchEditDialog, ExportDialog, ImportPreviewDialog, PasteListDialog, PersonDialog
from app.storage import load_recipient_data, save_recipient_data
from core.exporting import (
    COPY_DIGITS,
    COPY_DISPLAYED,
    COPY_E164,
    SCOPE_ALL,
    SCOPE_GROUP,
    SCOPE_SEARCH,
    SCOPE_SELECTION,
    backup_json,
    build_copy_text,
    export_csv,
    export_txt,
    export_xlsx_bytes,
    parse_backup_json,
    resolve_recipient_scope,
)
from core.groups import (
    ALL_RECIPIENTS,
    assign_to_group,
    batch_update_recipients,
    checked_recipient_indexes as checked_recipient_indexes_for_bulk,
    collect_groups,
    count_duplicate_phone_numbers,
    create_group,
    DEFAULT_GROUP,
    delete_group,
    find_recipient_index_by_phone,
    filtered_recipient_indexes,
    remove_from_group,
    valid_recipient_groups,
    preferred_group,
    recipient_phone_key,
    rename_group,
    SORT_GROUP,
    SORT_PHONE,
    SORT_RECENT,
    set_selected,
    valid_group_or_default,
)
from core.importing import add_import_rows as apply_import_rows
from core.importing import preview_import_file, preview_summary, remove_imported_numbers
from core.phone import PHONE_FORMATS, format_phone_number, normalize_us_phone


ALL_RECIPIENTS_LABEL = "All Recipients"
NO_CHECKED_RECIPIENTS_MESSAGE = "No recipients are checked. Select one or more recipients in the Select column, then try again."


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PourSend")
        self.resize(1180, 700)
        self.recipients, self.groups, self.settings, load_error = load_recipient_data()
        self.setAcceptDrops(True)
        self.recent_group = DEFAULT_GROUP
        self.last_imported_numbers: list[str | dict] = []
        self._building_table = False
        self._building_groups = False
        self._build_ui()
        QApplication.instance().installEventFilter(self)
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

        self.sort_field_combo = QComboBox()
        self.sort_field_combo.addItem("Recently Added", SORT_RECENT)
        self.sort_field_combo.addItem("Phone Number", SORT_PHONE)
        self.sort_field_combo.addItem("Group", SORT_GROUP)
        self.sort_field_combo.currentIndexChanged.connect(self.refresh_table)

        self.sort_direction_combo = QComboBox()
        self.sort_direction_combo.addItem("Ascending", False)
        self.sort_direction_combo.addItem("Descending", True)
        self.sort_direction_combo.currentIndexChanged.connect(self.refresh_table)

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
        assign_group_button = QPushButton("Add Checked to Group")
        remove_group_button = QPushButton("Remove Checked from Group")
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
        top.addWidget(QLabel("Sort"))
        top.addWidget(self.sort_field_combo)
        top.addWidget(self.sort_direction_combo)
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
        batch_edit_button = QPushButton("Batch Edit Checked")
        delete_button = QPushButton("Delete Recipient")
        undo_import_button = QPushButton("Undo Last Import")
        export_button = QPushButton("Export")
        export_backup_button = QPushButton("Export Backup")
        import_backup_button = QPushButton("Import Backup")
        clear_button = QPushButton("Clear All Data")
        select_all.clicked.connect(lambda: self.set_all_visible(True))
        deselect_all.clicked.connect(lambda: self.set_all_visible(False))
        edit_button.clicked.connect(self.edit_selected)
        batch_edit_button.clicked.connect(self.batch_edit_checked)
        delete_button.clicked.connect(self.delete_selected)
        undo_import_button.clicked.connect(self.undo_last_import)
        export_button.clicked.connect(self.export_recipients)
        export_backup_button.clicked.connect(self.export_backup)
        import_backup_button.clicked.connect(self.import_backup)
        clear_button.clicked.connect(self.clear_all)

        tools = QHBoxLayout()
        for button in [
            select_all,
            deselect_all,
            edit_button,
            batch_edit_button,
            delete_button,
            undo_import_button,
            export_button,
            export_backup_button,
            import_backup_button,
            clear_button,
        ]:
            tools.addWidget(button)
        tools.addStretch(1)

        self.phone_format_combo = QComboBox()
        for format_key, label in PHONE_FORMATS:
            self.phone_format_combo.addItem(label, format_key)
        saved_format = self.settings.get("phone_format")
        for index in range(self.phone_format_combo.count()):
            if self.phone_format_combo.itemData(index) == saved_format:
                self.phone_format_combo.setCurrentIndex(index)
                break
        self.phone_format_combo.currentIndexChanged.connect(self.phone_format_changed)

        self.copy_scope_combo = QComboBox()
        self.copy_scope_combo.addItem("Checked Numbers", SCOPE_SELECTION)
        self.copy_scope_combo.addItem("Current Search", SCOPE_SEARCH)
        self.copy_format_combo = QComboBox()
        self.copy_format_combo.addItem("Displayed Number", COPY_DISPLAYED)
        self.copy_format_combo.addItem("Digits Only", COPY_DIGITS)
        self.copy_format_combo.addItem("E.164", COPY_E164)
        self.count_label = QLabel("")
        copy_button = QPushButton("Copy Checked Numbers")
        copy_button.setMinimumHeight(48)
        copy_button.setStyleSheet("font-size: 17px; font-weight: 600;")
        copy_button.clicked.connect(self.copy_selected)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Phone format"))
        bottom.addWidget(self.phone_format_combo)
        bottom.addWidget(QLabel("Copy"))
        bottom.addWidget(self.copy_scope_combo)
        bottom.addWidget(self.copy_format_combo)
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

    def _shortcut(self, keys: str, slot) -> QAction:
        action = QAction(self)
        action.setShortcut(QKeySequence(keys))
        action.triggered.connect(slot)
        return action

    def eventFilter(self, watched, event) -> bool:
        if event.type() != QEvent.KeyPress or not self.shortcut_focus_is_inside_window():
            return super().eventFilter(watched, event)

        if event.matches(QKeySequence.Paste):
            if editable_text_widget_has_focus():
                return False
            self.paste_list()
            return True
        if event.matches(QKeySequence.Find):
            self.search.setFocus()
            return True
        if event.matches(QKeySequence.SelectAll):
            if editable_text_widget_has_focus():
                return False
            self.set_all_visible(True)
            return True
        if event.matches(QKeySequence.Undo):
            if editable_text_widget_has_focus():
                return False
            self.undo_last_import()
            return True
        if event.key() == Qt.Key_Delete and event.modifiers() == Qt.NoModifier:
            if editable_text_widget_has_focus():
                return False
            self.delete_selected()
            return True

        return super().eventFilter(watched, event)

    def shortcut_focus_is_inside_window(self) -> bool:
        focused = QApplication.focusWidget()
        return focused is None or focused is self or self.isAncestorOf(focused)

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
        indexes = filtered_recipient_indexes(
            self.recipients,
            self.current_group_filter(),
            query,
            self.current_phone_format(),
            self.sort_field_combo.currentData(),
            self.sort_direction_combo.currentData(),
        )
        phone_format = self.current_phone_format()
        self._building_table = True
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.table.setRowCount(len(indexes))
        for row, index in enumerate(indexes):
            recipient = self.recipients[index]
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(str(index)))
            checked = QTableWidgetItem("")
            checked.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            checked.setCheckState(Qt.Checked if recipient.get("selected") else Qt.Unchecked)
            self.table.setItem(row, 0, checked)
            phone_item = QTableWidgetItem(format_phone_number(recipient.get("phone", ""), phone_format))
            phone_item.setToolTip(recipient.get("phone", ""))
            self.table.setItem(row, 1, phone_item)
            group_item = QTableWidgetItem("; ".join(valid_recipient_groups(recipient, self.groups)))
            group_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 2, group_item)
            self.table.setItem(row, 3, QTableWidgetItem(recipient.get("notes", "")))
            normalized, status = normalize_us_phone(recipient.get("phone", ""))
            status_item = QTableWidgetItem(status)
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            status_item.setToolTip(normalized or status)
            self.table.setItem(row, 4, status_item)
        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)
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

    def checked_recipient_indexes(self) -> list[int]:
        return checked_recipient_indexes_for_bulk(self.recipients)

    def add_person(self) -> None:
        dialog = PersonDialog(self, groups=self.groups, selected_group=self.preferred_group())
        if dialog.exec() != PersonDialog.Accepted:
            return
        phone, groups, notes = dialog.values()
        normalized, status = normalize_us_phone(phone)
        if status != "Valid":
            QMessageBox.warning(self, "Add recipient", status)
            return
        valid_groups = self.valid_groups(groups)
        existing_index = find_recipient_index_by_phone(self.recipients, normalized)
        if existing_index is not None:
            existing = self.recipients[existing_index]
            new_groups = [group for group in valid_groups if group not in valid_recipient_groups(existing, self.groups)]
            if not new_groups:
                QMessageBox.information(self, "Add recipient", "That phone number already exists in the selected group.")
                return
            existing["groups"] = [*valid_recipient_groups(existing, self.groups), *new_groups]
            existing["group"] = existing["groups"][0]
            if notes:
                existing["notes"] = "\n".join(text for text in [existing.get("notes", ""), notes] if text)
            self.recent_group = new_groups[0]
            self.save_and_update(selected_group=new_groups[0])
            return
        self.recipients.append({"phone": normalized, "selected": False, "group": valid_groups[0], "groups": valid_groups, "notes": notes})
        self.recent_group = valid_groups[0]
        self.save_and_update(selected_group=valid_groups[0])

    def paste_list(self) -> None:
        dialog = PasteListDialog(
            self,
            self.existing_group_memberships(),
            self.groups,
            self.select_recipient_by_normalized_phone,
        )
        if dialog.exec() != PasteListDialog.Accepted:
            return
        group = self.valid_group(dialog.selected_group())
        actions = self.add_import_rows(dialog.rows_to_add(), group)
        added, added_to_group, duplicates, existing, invalid = dialog.summary_counts()
        self.show_import_result("Paste list", added, added_to_group, duplicates, existing, invalid, dialog.invalid_examples())
        if actions:
            self.last_imported_numbers = actions

    def existing_normalized_numbers(self) -> set[str]:
        numbers: set[str] = set()
        for recipient in self.recipients:
            normalized, status = normalize_us_phone(recipient.get("phone", ""))
            if status == "Valid":
                numbers.add(normalized)
        return numbers

    def existing_group_memberships(self) -> dict[str, list[str]]:
        memberships: dict[str, list[str]] = {}
        for recipient in self.recipients:
            normalized, status = normalize_us_phone(recipient.get("phone", ""))
            if status == "Valid":
                memberships[normalized] = valid_recipient_groups(recipient, self.groups)
        return memberships

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import File",
            "",
            "Import files (*.txt *.csv *.xlsx);;Text files (*.txt);;CSV files (*.csv);;Excel files (*.xlsx);;All files (*)",
        )
        if not path:
            return
        self.import_file_path(path)

    def import_file_path(self, path: str) -> None:
        try:
            preview_rows = preview_import_file(path, self.existing_group_memberships(), self.preferred_group())
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Import file", f"The file could not be imported: {exc}")
            return
        dialog = ImportPreviewDialog(
            self,
            preview_rows,
            self.groups,
            self.preferred_group(),
            self.select_recipient_by_normalized_phone,
            lambda group: preview_import_file(path, self.existing_group_memberships(), self.valid_group(group)),
        )
        if dialog.exec() != ImportPreviewDialog.Accepted:
            return
        group = self.valid_group(dialog.selected_group())
        preview_rows = dialog.preview_rows
        actions = self.add_import_rows(preview_rows, group)
        summary = preview_summary(preview_rows)
        if not actions:
            QMessageBox.warning(self, "Import file", "No new valid phone numbers were found in the file.")
        self.show_import_result(
            "Import file",
            summary.added,
            summary.added_to_group,
            summary.duplicates,
            summary.already_exists,
            summary.invalid,
            dialog.invalid_examples(),
        )
        if actions:
            self.last_imported_numbers = actions

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.import_file_path(path)
                event.acceptProposedAction()
                return

    def add_import_rows(self, preview_rows, group: str) -> list[str | dict]:
        actions = apply_import_rows(self.recipients, preview_rows, group)
        if actions:
            self.recent_group = group
            self.save_and_update(selected_group=group)
        return actions

    def show_import_result(
        self,
        title: str,
        added: int,
        added_to_group: int,
        duplicates: int,
        existing: int,
        invalid: int,
        invalid_examples: list[str],
    ) -> None:
        extracted = added + added_to_group + duplicates + existing + invalid
        invalid_text = ""
        if invalid_examples:
            invalid_text = "\nInvalid examples:\n" + "\n".join(invalid_examples)
        QMessageBox.information(
            self,
            title,
            f"Extracted: {extracted}\n"
            f"New Recipients: {added}\n"
            f"Added to Group: {added_to_group}\n"
            f"Already in Group: {existing}\n"
            f"Duplicates in Input: {duplicates}\n"
            f"Invalid: {invalid}"
            f"{invalid_text}",
        )

    def undo_last_import(self) -> None:
        if not self.last_imported_numbers:
            QMessageBox.information(self, "Undo last import", "There is no import to undo.")
            return
        removed = remove_imported_numbers(self.recipients, self.last_imported_numbers)
        self.last_imported_numbers = []
        self.save_and_update()
        QMessageBox.information(self, "Undo last import", f"Undid {removed} change(s) from the last import.")

    def select_recipient_by_normalized_phone(self, normalized: str) -> None:
        index = find_recipient_index_by_phone(self.recipients, normalized)
        if index is None:
            return
        self.refresh_group_list(ALL_RECIPIENTS)
        self.search.clear()
        self.refresh_table()
        for row in range(self.table.rowCount()):
            if self._recipient_index(row) == index:
                self.table.selectRow(row)
                self.table.scrollToItem(self.table.item(row, 1))
                return

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
            valid_recipient_groups(recipient, self.groups),
            recipient.get("notes", ""),
        )
        if dialog.exec() != PersonDialog.Accepted:
            return
        phone, groups, notes = dialog.values()
        normalized, status = normalize_us_phone(phone)
        if status != "Valid":
            QMessageBox.warning(self, "Edit recipient", status)
            return
        if any(other_index != index and recipient_phone_key(other) == normalized for other_index, other in enumerate(self.recipients)):
            QMessageBox.warning(self, "Edit recipient", "That phone number already exists.")
            return
        valid_groups = self.valid_groups(groups)
        recipient["phone"] = normalized
        recipient["group"] = valid_groups[0]
        recipient["groups"] = valid_groups
        recipient["notes"] = notes
        self.recent_group = valid_groups[0]
        self.save_and_update(selected_group=valid_groups[0])

    def batch_edit_checked(self) -> None:
        indexes = self.checked_recipient_indexes()
        if not indexes:
            QMessageBox.information(self, "Batch edit", NO_CHECKED_RECIPIENTS_MESSAGE)
            return
        dialog = BatchEditDialog(self, self.groups)
        if dialog.exec() != BatchEditDialog.Accepted:
            return
        group, notes = dialog.values()
        if group is None and notes is None:
            QMessageBox.information(self, "Batch edit", "Choose a group or notes change.")
            return
        updated = batch_update_recipients(self.recipients, indexes, group=group, notes=notes)
        if group:
            self.recent_group = group
        self.save_and_update(selected_group=self.current_group_filter())
        QMessageBox.information(self, "Batch edit", f"Updated {updated} recipients.")

    def delete_selected(self) -> None:
        indexes = self.checked_recipient_indexes()
        if not indexes:
            QMessageBox.information(self, "Delete recipient", NO_CHECKED_RECIPIENTS_MESSAGE)
            return
        answer = QMessageBox.question(self, "Delete recipient", f"Delete {len(indexes)} recipients?")
        if answer != QMessageBox.Yes:
            return
        for index in sorted(indexes, reverse=True):
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

    def visible_indexes(self) -> list[int]:
        return [
            index
            for row in range(self.table.rowCount())
            for index in [self._recipient_index(row)]
            if index is not None
        ]

    def scope_selection(self, scope: str):
        return resolve_recipient_scope(
            self.recipients,
            scope,
            group_filter=self.current_group_filter(),
            query=self.search.text(),
            phone_format=self.current_phone_format(),
            sort_field=self.sort_field_combo.currentData(),
            descending=self.sort_direction_combo.currentData(),
        )

    def scope_counts(self) -> dict[str, int]:
        return {
            SCOPE_ALL: len(self.scope_selection(SCOPE_ALL).recipients),
            SCOPE_GROUP: len(self.scope_selection(SCOPE_GROUP).recipients),
            SCOPE_SEARCH: len(self.scope_selection(SCOPE_SEARCH).recipients),
            SCOPE_SELECTION: len(self.scope_selection(SCOPE_SELECTION).recipients),
        }

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
        indexes = self.checked_recipient_indexes()
        if not indexes:
            QMessageBox.information(self, "Add to group", NO_CHECKED_RECIPIENTS_MESSAGE)
            return
        if not self.groups:
            QMessageBox.information(self, "Add to group", "Create a group first.")
            return
        group, ok = QInputDialog.getItem(self, "Add to group", "Group", self.groups, 0, False)
        if not ok:
            return
        assign_to_group(self.recipients, indexes, group)
        self.recent_group = group
        self.save_and_update(selected_group=self.current_group_filter())

    def remove_checked_from_current_group(self) -> None:
        indexes = self.checked_recipient_indexes()
        if not indexes:
            QMessageBox.information(self, "Remove from group", NO_CHECKED_RECIPIENTS_MESSAGE)
            return
        group = self.current_named_group()
        if group is None:
            QMessageBox.information(self, "Remove from group", "Open a group before removing checked recipients from it.")
            return
        remove_from_group(self.recipients, indexes, group)
        self.save_and_update(selected_group=group)

    def copy_selected(self) -> None:
        selection = self.scope_selection(self.copy_scope_combo.currentData())
        if not selection.recipients:
            QMessageBox.information(self, "Copy checked numbers", selection.empty_reason)
            return
        output = build_copy_text(selection.recipients, self.copy_format_combo.currentData(), self.current_phone_format())
        if not output:
            QMessageBox.warning(self, "Copy checked numbers", "No valid checked phone numbers were found.")
            return
        try:
            QApplication.clipboard().setText(output)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Copy checked numbers", f"The numbers could not be copied: {exc}")
            return
        QMessageBox.information(
            self,
            "Copy checked numbers",
            f"Copied {len(output.splitlines())} phone numbers.",
        )

    def export_recipients(self) -> None:
        dialog = ExportDialog(self, self.scope_counts())
        if dialog.exec() != ExportDialog.Accepted:
            return
        file_format, scope = dialog.values()
        selection = self.scope_selection(scope)
        if not selection.recipients:
            QMessageBox.information(self, "Export", selection.empty_reason)
            return

        extensions = {"txt": "txt", "csv": "csv", "xlsx": "xlsx"}
        filters = {
            "txt": "Text files (*.txt)",
            "csv": "CSV files (*.csv)",
            "xlsx": "Excel files (*.xlsx)",
        }
        default_name = f"recipients.{extensions[file_format]}"
        path, _ = QFileDialog.getSaveFileName(self, "Export", default_name, filters[file_format])
        if not path:
            return
        if "." not in path.rsplit("/", 1)[-1]:
            path = f"{path}.{extensions[file_format]}"
        try:
            if file_format == "txt":
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(export_txt(selection.recipients, self.current_phone_format()))
            elif file_format == "csv":
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(export_csv(selection.recipients, self.current_phone_format()))
            else:
                with open(path, "wb") as handle:
                    handle.write(export_xlsx_bytes(selection.recipients, self.current_phone_format()))
        except OSError as exc:
            QMessageBox.critical(self, "Export", f"Could not export recipients: {exc}")
            return
        QMessageBox.information(self, "Export", "Recipients exported.")

    def export_backup(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Backup", "recipients-backup.json", "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(backup_json(self.recipients, self.groups, self.settings))
        except OSError as exc:
            QMessageBox.critical(self, "Export backup", f"Could not export backup: {exc}")
            return
        QMessageBox.information(self, "Export backup", "Backup exported.")

    def import_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Backup", "", "JSON files (*.json);;All files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                recipients, groups, settings, version = parse_backup_json(handle.read())
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Import backup", f"Backup could not be imported: {exc}")
            return
        answer = QMessageBox.question(
            self,
            "Import backup",
            f"Replace existing PourSend data with this backup?\n\n"
            f"Recipients: {len(recipients)}\nGroups: {len(groups)}\nBackup version: {version}",
        )
        if answer != QMessageBox.Yes:
            return
        self.recipients = recipients
        self.groups = groups
        self.settings = settings
        self.last_imported_numbers = []
        self.set_phone_format(self.settings.get("phone_format"))
        self.save_and_update(selected_group=ALL_RECIPIENTS)
        QMessageBox.information(self, "Import backup", "Backup imported.")

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
        error = save_recipient_data(self.recipients, self.groups, self.settings)
        self.refresh_group_list(selected_group)
        self.refresh_table()
        if error:
            QMessageBox.warning(self, "Local data", error)

    def update_counts(self) -> None:
        visible_indexes = self.checked_or_visible_indexes()
        visible_selected = sum(1 for index in visible_indexes if self.recipients[index].get("selected"))
        total_selected = sum(1 for recipient in self.recipients if recipient.get("selected"))
        current_group = self.current_group_filter()
        group_count = len(self.scope_selection(SCOPE_GROUP).recipients)
        search_count = len(visible_indexes)
        duplicates = count_duplicate_phone_numbers(self.recipients)
        group_label = ALL_RECIPIENTS_LABEL if current_group == ALL_RECIPIENTS else current_group
        self.count_label.setText(
            f"Total recipients: {len(self.recipients)} | Current group ({group_label}): {group_count} | "
            f"Current search: {search_count} | Stored duplicates: {duplicates} | "
            f"Visible checked: {visible_selected} | Total checked: {total_selected}"
        )

    def valid_group(self, group: str) -> str:
        return valid_group_or_default(group, self.groups)

    def valid_groups(self, groups: list[str]) -> list[str]:
        valid = []
        for group in groups:
            clean = self.valid_group(group)
            if clean not in valid:
                valid.append(clean)
        return valid or [DEFAULT_GROUP]

    def current_phone_format(self) -> str:
        return self.phone_format_combo.currentData()

    def set_phone_format(self, format_key: str | None) -> None:
        for index in range(self.phone_format_combo.count()):
            if self.phone_format_combo.itemData(index) == format_key:
                self.phone_format_combo.blockSignals(True)
                self.phone_format_combo.setCurrentIndex(index)
                self.phone_format_combo.blockSignals(False)
                return

    def phone_format_changed(self) -> None:
        self.settings["phone_format"] = self.current_phone_format()
        self.save_and_update(selected_group=self.current_group_filter())


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


def editable_text_widget_has_focus(widget=None) -> bool:
    focused = widget if widget is not None else QApplication.focusWidget()
    if focused is None:
        return False
    if isinstance(focused, QLineEdit):
        return not focused.isReadOnly()
    if isinstance(focused, (QTextEdit, QPlainTextEdit)):
        return not focused.isReadOnly()
    return False


if __name__ == "__main__":
    raise SystemExit(main())

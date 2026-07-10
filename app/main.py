from __future__ import annotations

import sys

from PySide6.QtCore import QByteArray, QEvent, QRect, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedLayout,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.dialogs import DeleteConfirmationDialog, BatchEditDialog, ExportDialog, ImportPreviewDialog, PasteListDialog, PersonDialog
from app.storage import load_recipient_data, save_recipient_data
from app.theme import DANGER_BUTTON, PRIMARY_BUTTON, SECONDARY_BUTTON, SUBTLE_BUTTON, apply_app_theme, mark_button
from app.ui_helpers import checked_status_text, empty_state_message, group_recipient_count, workspace_title
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


HEADER_HEIGHT = 102
CONTROL_HEIGHT = 48
SECONDARY_BUTTON_HEIGHT = 46
SIDEBAR_WIDTH = 340
TABLE_HEADER_HEIGHT = 48
TABLE_ROW_HEIGHT = 68


SVG_ICONS = {
    "add": '<path d="M12 5v14M5 12h14"/>',
    "clipboard": '<rect x="8" y="5" width="8" height="3" rx="1"/><path d="M7 7h-1a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-1"/><path d="M8 12h8M8 16h6"/>',
    "copy": '<rect x="8" y="8" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1"/>',
    "download": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
    "edit": '<path d="M4 20h4l10.5-10.5a2.1 2.1 0 0 0-3-3L5 17v3z"/><path d="m13.5 6.5 4 4"/>',
    "file-up": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6"/><path d="m9 15 3-3 3 3"/>',
    "groups": '<path d="M7 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M17 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M3 20a5 5 0 0 1 8 0"/><path d="M13 20a5 5 0 0 1 8 0"/>',
    "home": '<path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    "more": '<path d="M6 9l6 6 6-6"/>',
    "phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.4 19.4 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.6a2 2 0 0 1-.5 2.1L8 9.6a16 16 0 0 0 6.4 6.4l1.2-1.2a2 2 0 0 1 2.1-.5c.8.3 1.7.5 2.6.6a2 2 0 0 1 1.7 2z"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
    "star": '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z"/>',
    "tag": '<path d="M20 13 11 22 2 13V2h11l7 7z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    "trash": '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v5M14 11v5"/>',
    "user-add": '<path d="M15 21a6 6 0 0 0-12 0"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M16 11h6"/>',
    "user-minus": '<path d="M15 21a6 6 0 0 0-12 0"/><circle cx="9" cy="7" r="4"/><path d="M16 11h6"/>',
}


def svg_pixmap(name: str, color: str = "#3b7cf4", size: int = 20) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'{SVG_ICONS[name]}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


class SvgIconLabel(QLabel):
    def __init__(self, name: str, color: str = "#3b7cf4", size: int = 20) -> None:
        super().__init__()
        self.setPixmap(svg_pixmap(name, color, size))
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)


def icon_button(text: str, icon: str, role: str = SECONDARY_BUTTON, color: str = "#23314d") -> QPushButton:
    button = mark_button(QPushButton(text), role)
    button.setIcon(QIcon(svg_pixmap(icon, "#ffffff" if role == PRIMARY_BUTTON else color, 18)))
    button.setIconSize(QSize(18, 18))
    return button


class RecipientTableDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        rect = option.rect
        selected = bool(option.state & QStyle.State_Selected)
        if selected:
            fill = QColor("#edf5ff")
        elif index.row() % 2:
            fill = QColor("#f8fbff")
        else:
            fill = QColor("#ffffff")
        painter.fillRect(rect, fill)
        painter.setPen(QPen(QColor("#e7edf6"), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        if index.column() == 0:
            check_state = index.data(Qt.CheckStateRole)
            checked = getattr(check_state, "value", check_state) == Qt.Checked.value
            box_size = 20
            box = QRect(
                rect.x() + (rect.width() - box_size) // 2,
                rect.y() + (rect.height() - box_size) // 2,
                box_size,
                box_size,
            )
            painter.setRenderHint(QPainter.Antialiasing)
            if checked:
                painter.setBrush(QColor("#3b7cf4"))
                painter.setPen(QPen(QColor("#3b7cf4"), 1))
                painter.drawRoundedRect(box, 5, 5)
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.drawLine(box.left() + 5, box.center().y(), box.left() + 9, box.bottom() - 6)
                painter.drawLine(box.left() + 9, box.bottom() - 6, box.right() - 5, box.top() + 6)
            else:
                painter.setBrush(QColor("#ffffff"))
                painter.setPen(QPen(QColor("#cbd6e6"), 1.4))
                painter.drawRoundedRect(box.adjusted(1, 1, -1, -1), 5, 5)
            painter.restore()
            return

        super().paint(painter, option, index)
        painter.restore()

    def editorEvent(self, event, model, option, index) -> bool:
        if index.column() != 0 or event.type() not in (QEvent.MouseButtonRelease, QEvent.KeyPress):
            return super().editorEvent(event, model, option, index)
        if event.type() == QEvent.KeyPress and event.key() not in (Qt.Key_Space, Qt.Key_Select):
            return False
        current = index.data(Qt.CheckStateRole)
        model.setData(index, Qt.Unchecked if current == Qt.Checked else Qt.Checked, Qt.CheckStateRole)
        return True


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PourSend")
        self.resize(1588, 1006)
        self.setMinimumSize(1120, 700)
        self.recipients, self.groups, self.settings, load_error = load_recipient_data()
        self.setAcceptDrops(True)
        self.recent_group = DEFAULT_GROUP
        self.last_imported_numbers: list[str | dict] = []
        self._building_table = False
        self._building_groups = False
        apply_app_theme(QApplication.instance())
        self._build_ui()
        QApplication.instance().installEventFilter(self)
        self.refresh_group_list()
        self.refresh_table()
        if load_error:
            QMessageBox.warning(self, "Local data", load_error)

    def _build_ui(self) -> None:
        app_icon = QLabel("P")
        app_icon.setObjectName("AppIcon")
        app_icon.setAlignment(Qt.AlignCenter)
        app_icon.setFixedSize(58, 58)
        title = QLabel("PourSend")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Recipient organizer")
        subtitle.setObjectName("AppSubtitle")
        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)

        self.search = QLineEdit()
        self.search.setObjectName("SearchField")
        self.search.setPlaceholderText("Search recipients...")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(350)
        self.search.setFixedHeight(CONTROL_HEIGHT)
        self.search.addAction(QIcon(svg_pixmap("search", "#3b7cf4", 18)), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self.refresh_table)

        self.sort_field_combo = QComboBox()
        self.sort_field_combo.addItem("Recently Added", SORT_RECENT)
        self.sort_field_combo.addItem("Phone Number", SORT_PHONE)
        self.sort_field_combo.addItem("Group", SORT_GROUP)
        self.sort_field_combo.setMinimumWidth(176)
        self.sort_field_combo.setFixedHeight(SECONDARY_BUTTON_HEIGHT)
        self.sort_field_combo.currentIndexChanged.connect(self.refresh_table)

        self.sort_direction_combo = QComboBox()
        self.sort_direction_combo.addItem("Ascending", False)
        self.sort_direction_combo.addItem("Descending", True)
        self.sort_direction_combo.setMinimumWidth(164)
        self.sort_direction_combo.setFixedHeight(SECONDARY_BUTTON_HEIGHT)
        self.sort_direction_combo.currentIndexChanged.connect(self.refresh_table)

        add_button = icon_button("Add Recipient", "add", PRIMARY_BUTTON)
        paste_button = icon_button("Paste List", "clipboard")
        import_button = icon_button("Import File", "file-up")
        copy_button = icon_button("Copy", "copy")
        export_button = icon_button("Export", "download")
        more_button = icon_button("More", "more", SUBTLE_BUTTON)
        add_button.setMinimumWidth(170)
        paste_button.setMinimumWidth(128)
        import_button.setMinimumWidth(138)
        copy_button.setMinimumWidth(92)
        export_button.setMinimumWidth(104)
        more_button.setMinimumWidth(96)
        add_button.clicked.connect(self.add_person)
        paste_button.clicked.connect(self.paste_list)
        import_button.clicked.connect(self.import_csv)
        copy_button.clicked.connect(self.copy_selected)
        export_button.clicked.connect(self.export_recipients)

        more_menu = QMenu(more_button)
        more_menu.addAction("Undo Last Import", self.undo_last_import)
        more_menu.addSeparator()
        more_menu.addAction("Import Backup", self.import_backup)
        more_menu.addAction("Export Backup", self.export_backup)
        more_menu.addSeparator()
        more_menu.addAction("Clear All Data", self.clear_all)
        more_button.setMenu(more_menu)

        self.group_list = QListWidget()
        self.group_list.currentItemChanged.connect(lambda _current, _previous: self.refresh_table())
        self.group_list.setMinimumWidth(286)
        self.group_list.setMaximumWidth(306)
        self.group_list.setSpacing(2)
        self.group_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.group_list.setSelectionMode(QAbstractItemView.SingleSelection)

        new_group_button = icon_button("New Group", "add")
        rename_group_button = icon_button("Rename", "edit")
        delete_group_button = icon_button("Delete", "trash", DANGER_BUTTON, "#d24b4b")
        assign_group_button = icon_button("Add Checked", "user-add")
        remove_group_button = icon_button("Remove Checked", "user-minus", SECONDARY_BUTTON, "#d24b4b")
        new_group_button.clicked.connect(self.create_group)
        rename_group_button.clicked.connect(self.rename_group)
        delete_group_button.clicked.connect(self.delete_group)
        assign_group_button.clicked.connect(self.assign_checked_to_group)
        remove_group_button.clicked.connect(self.remove_checked_from_current_group)

        group_title = QLabel("Groups")
        group_title.setObjectName("SectionTitle")
        top_new_group_button = mark_button(QPushButton("+"), SECONDARY_BUTTON)
        top_new_group_button.setObjectName("IconButton")
        top_new_group_button.setFixedSize(32, 32)
        top_new_group_button.setToolTip("New Group")
        top_new_group_button.clicked.connect(self.create_group)
        group_header = QHBoxLayout()
        group_header.setSpacing(8)
        group_header.addWidget(group_title)
        group_header.addStretch(1)
        group_header.addWidget(top_new_group_button)
        group_tools = QVBoxLayout()
        group_tools.setContentsMargins(18, 18, 18, 18)
        group_tools.setSpacing(12)
        group_tools.addLayout(group_header)
        group_tools.addWidget(self.group_list, stretch=1)
        group_tools.addWidget(new_group_button)
        group_action_row = QHBoxLayout()
        group_action_row.setSpacing(6)
        group_action_row.addWidget(rename_group_button)
        group_action_row.addWidget(delete_group_button)
        group_tools.addLayout(group_action_row)
        group_checked_row = QHBoxLayout()
        group_checked_row.setSpacing(6)
        group_checked_row.addWidget(assign_group_button)
        group_checked_row.addWidget(remove_group_button)
        group_tools.addLayout(group_checked_row)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        sidebar.setLayout(group_tools)

        command_bar = QHBoxLayout()
        command_bar.setSpacing(8)
        command_bar.addWidget(add_button)
        command_bar.addWidget(paste_button)
        command_bar.addWidget(import_button)
        command_bar.addSpacing(8)
        command_bar.addWidget(copy_button)
        command_bar.addWidget(export_button)
        command_bar.addWidget(more_button)

        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(HEADER_HEIGHT)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 22, 20)
        header_layout.setSpacing(18)
        header_layout.addWidget(app_icon)
        header_layout.addLayout(title_block)
        header_layout.addSpacing(118)
        header_layout.addWidget(self.search)
        header_layout.addLayout(command_bar)

        self.workspace_title = QLabel("All Recipients")
        self.workspace_title.setObjectName("WorkspaceTitle")
        self.workspace_meta = QLabel("")
        self.workspace_meta.setObjectName("CountBadge")

        workspace_heading = QHBoxLayout()
        workspace_heading.setSpacing(8)
        workspace_heading.addWidget(self.workspace_title)
        workspace_heading.addWidget(self.workspace_meta)
        workspace_heading.addStretch(1)

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)
        filter_bar.setContentsMargins(0, 2, 0, 0)
        filter_bar.addWidget(QLabel("Sort by"))
        filter_bar.addWidget(self.sort_field_combo)
        filter_bar.addWidget(self.sort_direction_combo)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Select", "Phone number", "Group", "Notes", "Status"])
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setItemDelegate(RecipientTableDelegate(self.table))
        table_header = self.table.horizontalHeader()
        table_header.setFixedHeight(TABLE_HEADER_HEIGHT)
        table_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(1, QHeaderView.Interactive)
        table_header.setSectionResizeMode(2, QHeaderView.Interactive)
        table_header.setSectionResizeMode(3, QHeaderView.Interactive)
        table_header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 94)
        self.table.setColumnWidth(1, 255)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 320)
        self.table.itemChanged.connect(self.table_item_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self.edit_selected())

        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignCenter)
        self.empty_title = QLabel("No recipients found")
        self.empty_title.setObjectName("EmptyTitle")
        self.empty_subtitle = QLabel("Try changing your search or add a new recipient.")
        self.empty_subtitle.setObjectName("EmptySubtitle")
        empty_layout.addWidget(self.empty_title, alignment=Qt.AlignCenter)
        empty_layout.addWidget(self.empty_subtitle, alignment=Qt.AlignCenter)

        table_area = QWidget()
        self.table_stack = QStackedLayout(table_area)
        self.table_stack.addWidget(self.table)
        self.table_stack.addWidget(self.empty_state)

        select_all = mark_button(QPushButton("Select All in This Group"), SUBTLE_BUTTON)
        deselect_all = mark_button(QPushButton("Deselect All in This Group"), SUBTLE_BUTTON)
        edit_button = mark_button(QPushButton("Edit Recipient"), SECONDARY_BUTTON)
        select_all.clicked.connect(lambda: self.set_all_visible(True))
        deselect_all.clicked.connect(lambda: self.set_all_visible(False))
        edit_button.clicked.connect(self.edit_selected)

        table_tools = QHBoxLayout()
        table_tools.setSpacing(8)
        table_tools.addWidget(select_all)
        table_tools.addWidget(deselect_all)
        table_tools.addWidget(edit_button)
        table_tools.addStretch(1)

        self.phone_format_combo = QComboBox()
        for format_key, label in PHONE_FORMATS:
            self.phone_format_combo.addItem(label, format_key)
        self.phone_format_combo.setMinimumWidth(164)
        self.phone_format_combo.setFixedHeight(SECONDARY_BUTTON_HEIGHT)
        saved_format = self.settings.get("phone_format")
        for index in range(self.phone_format_combo.count()):
            if self.phone_format_combo.itemData(index) == saved_format:
                self.phone_format_combo.setCurrentIndex(index)
                break
        self.phone_format_combo.currentIndexChanged.connect(self.phone_format_changed)
        filter_bar.addWidget(QLabel("Phone format"))
        filter_bar.addWidget(self.phone_format_combo)

        self.copy_scope_combo = QComboBox()
        self.copy_scope_combo.addItem("Checked Numbers", SCOPE_SELECTION)
        self.copy_scope_combo.addItem("Current Search", SCOPE_SEARCH)
        self.copy_scope_combo.setMinimumWidth(210)
        self.copy_scope_combo.setFixedHeight(SECONDARY_BUTTON_HEIGHT)
        self.copy_format_combo = QComboBox()
        self.copy_format_combo.addItem("Displayed Number", COPY_DISPLAYED)
        self.copy_format_combo.addItem("Digits Only", COPY_DIGITS)
        self.copy_format_combo.addItem("E.164", COPY_E164)
        self.copy_format_combo.setMinimumWidth(200)
        self.copy_format_combo.setFixedHeight(SECONDARY_BUTTON_HEIGHT)
        self.count_label = QLabel("")
        self.count_label.setObjectName("MutedText")
        filter_bar.addWidget(QLabel("Copy"))
        filter_bar.addWidget(self.copy_scope_combo)
        filter_bar.addWidget(self.copy_format_combo)
        filter_bar.addStretch(1)

        self.bulk_bar = QFrame()
        self.bulk_bar.setObjectName("BulkBar")
        bulk_layout = QHBoxLayout(self.bulk_bar)
        bulk_layout.setContentsMargins(14, 10, 14, 10)
        bulk_layout.setSpacing(10)
        self.bulk_count_label = QLabel("0 recipients checked")
        self.bulk_count_label.setObjectName("BulkCount")
        bulk_copy_button = icon_button("Copy", "clipboard")
        bulk_set_button = icon_button("Set Groups", "tag")
        bulk_add_button = icon_button("Add to Group", "user-add")
        bulk_remove_button = icon_button("Remove from Group", "user-minus")
        bulk_delete_button = icon_button("Delete", "trash", DANGER_BUTTON, "#d24b4b")
        bulk_copy_button.clicked.connect(self.copy_selected)
        bulk_set_button.clicked.connect(self.batch_edit_checked)
        bulk_add_button.clicked.connect(self.assign_checked_to_group)
        bulk_remove_button.clicked.connect(self.remove_checked_from_current_group)
        bulk_delete_button.clicked.connect(self.delete_selected)
        bulk_layout.addWidget(self.bulk_count_label)
        bulk_layout.addStretch(1)
        bulk_layout.addWidget(bulk_copy_button)
        bulk_layout.addWidget(bulk_add_button)
        bulk_layout.addWidget(bulk_set_button)
        bulk_layout.addWidget(bulk_remove_button)
        bulk_layout.addWidget(bulk_delete_button)

        workspace = QFrame()
        workspace.setObjectName("Workspace")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(24, 20, 24, 20)
        workspace_layout.setSpacing(16)
        workspace_layout.addLayout(workspace_heading)
        workspace_layout.addLayout(filter_bar)
        workspace_layout.addWidget(table_area)
        workspace_layout.addLayout(table_tools)
        workspace_layout.addStretch(1)
        workspace_layout.addWidget(self.bulk_bar)

        body = QHBoxLayout()
        body.setContentsMargins(18, 20, 18, 20)
        body.setSpacing(16)
        body.addWidget(sidebar)
        body.addWidget(workspace, stretch=1)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header)
        main_layout.addLayout(body, stretch=1)

        root = QWidget()
        root.setObjectName("AppRoot")
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
            item = QListWidgetItem("")
            item.setData(Qt.UserRole, value)
            item.setSizeHint(QSize(0, 48))
            self.group_list.addItem(item)
            self.group_list.setItemWidget(item, self.group_row_widget(label, value))
        for group in self.groups:
            item = QListWidgetItem("")
            item.setData(Qt.UserRole, group)
            item.setSizeHint(QSize(0, 48))
            self.group_list.addItem(item)
            self.group_list.setItemWidget(item, self.group_row_widget(group, group))

        row_to_select = 0
        for row in range(self.group_list.count()):
            if self.group_list.item(row).data(Qt.UserRole) == current:
                row_to_select = row
                break
        self.group_list.setCurrentRow(row_to_select)
        self._building_groups = False

    def group_row_widget(self, label: str, group: str) -> QWidget:
        row = QWidget()
        row.setObjectName("GroupRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        icon_name, icon_color = self.group_icon(group)
        icon = SvgIconLabel(icon_name, icon_color, 20)
        icon.setObjectName("GroupIcon")
        icon.setProperty("groupName", group)
        name = QLabel(label)
        name.setObjectName("GroupName")
        count = QLabel(str(group_recipient_count(self.recipients, group)))
        count.setObjectName("GroupCountBadge")
        count.setAlignment(Qt.AlignCenter)
        count.setMinimumWidth(30)
        layout.addWidget(icon)
        layout.addWidget(name)
        layout.addStretch(1)
        layout.addWidget(count)
        return row

    def group_icon(self, group: str) -> tuple[str, str]:
        if group == ALL_RECIPIENTS:
            return "groups", "#3b7cf4"
        if group == DEFAULT_GROUP:
            return "home", "#53627c"
        if group == "Female Mandarin":
            return "groups", "#f05a75"
        if group == "Male Cantonese":
            return "groups", "#3b7cf4"
        if group == "Follow Up":
            return "star", "#f2a91f"
        return "groups", "#53627c"

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
        table_height = TABLE_HEADER_HEIGHT + max(4, min(len(indexes), 6)) * TABLE_ROW_HEIGHT + 3
        self.table.setFixedHeight(table_height)
        for row, index in enumerate(indexes):
            recipient = self.recipients[index]
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(str(index)))
            checked = QTableWidgetItem("")
            checked.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            checked.setCheckState(Qt.Checked if recipient.get("selected") else Qt.Unchecked)
            checked.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, checked)
            phone_item = QTableWidgetItem(format_phone_number(recipient.get("phone", ""), phone_format))
            phone_item.setIcon(QIcon(svg_pixmap("phone", "#3b7cf4", 18)))
            phone_font = phone_item.font()
            phone_font.setBold(True)
            phone_item.setFont(phone_font)
            phone_item.setToolTip(recipient.get("phone", ""))
            self.table.setItem(row, 1, phone_item)
            self.table.setCellWidget(row, 2, self.group_tags_widget(valid_recipient_groups(recipient, self.groups)))
            self.table.setItem(row, 3, QTableWidgetItem(recipient.get("notes", "")))
            normalized, status = normalize_us_phone(recipient.get("phone", ""))
            self.table.setCellWidget(row, 4, self.status_badge_widget(status, normalized or status))
        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)
        self._building_table = False
        self.table_stack.setCurrentWidget(self.table if indexes else self.empty_state)
        empty_title, empty_subtitle = empty_state_message(query)
        self.empty_title.setText(empty_title)
        self.empty_subtitle.setText(empty_subtitle)
        self.update_counts()

    def group_tags_widget(self, groups: list[str]) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)
        memberships = valid_recipient_groups({"groups": groups})
        for group in memberships[:2]:
            tag = QLabel(group)
            tag.setObjectName("GroupTag")
            tag.setProperty("groupName", group)
            tag.setFixedHeight(30)
            layout.addWidget(tag)
        if len(memberships) > 2:
            more = QLabel(f"+{len(memberships) - 2}")
            more.setObjectName("GroupTag")
            more.setFixedHeight(30)
            layout.addWidget(more)
        layout.addStretch(1)
        return container

    def status_badge_widget(self, status: str, tooltip: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 2, 6, 2)
        badge = QLabel(status)
        badge.setObjectName("StatusBadge")
        badge.setToolTip(tooltip)
        badge.setFixedHeight(32)
        layout.addWidget(badge)
        layout.addStretch(1)
        return container

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
        dialog = DeleteConfirmationDialog(len(indexes), self)
        if dialog.exec() != DeleteConfirmationDialog.Accepted:
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
        group_label = workspace_title(current_group)
        self.workspace_title.setText(group_label)
        self.workspace_meta.setText("1 recipient" if group_count == 1 else f"{group_count} recipients")
        self.bulk_count_label.setText(checked_status_text(total_selected))
        self.bulk_bar.setVisible(total_selected > 0)
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

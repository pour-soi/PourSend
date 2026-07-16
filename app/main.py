from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QRect, QSize, Qt
from PySide6.QtGui import QAction, QColor, QGuiApplication, QIcon, QKeySequence, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
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
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
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
from core.version import __version__


ALL_RECIPIENTS_LABEL = "All Recipients"
NO_CHECKED_RECIPIENTS_MESSAGE = "No recipients are checked. Select one or more recipients in the Select column, then try again."
APP_LOGO_ASSET = "assets/poursend-logo.png"
APP_ICON_ASSET = "assets/poursend-icon-256.png"
BRAND_BLUE = "#5d8ff3"
BRAND_BLUE_DARK = "#4779df"
BRAND_SELECTION = "#edf4ff"


class LayoutMetrics:
    DEFAULT_WINDOW = QSize(1440, 900)
    MIN_WINDOW = QSize(360, 300)
    HEADER_MIN_HEIGHT = 104
    HEADER_MARGIN_X = 26
    HEADER_MARGIN_Y = 20
    HEADER_MARGIN_RIGHT = 22
    CONTROL_HEIGHT = 46
    PRIMARY_CONTROL_HEIGHT = 48
    LOGO_SIZE = 92
    LOGO_MIN_SIZE = 60
    ICON_BUTTON_SIZE = 34
    ICON_SIZE = 18
    SIDEBAR_MIN_WIDTH = 168
    SIDEBAR_PREFERRED_WIDTH = 260
    SIDEBAR_MAX_WIDTH = 300
    SIDEBAR_PADDING = 18
    GROUP_ROW_MARGIN_X = 10
    LIST_ITEM_SPACING = 2
    SEARCH_MIN_WIDTH = 80
    SEARCH_MAX_WIDTH = 460
    SORT_FIELD_MIN_WIDTH = 120
    SORT_DIRECTION_MIN_WIDTH = 120
    PHONE_FORMAT_MIN_WIDTH = 120
    COPY_SCOPE_MIN_WIDTH = 120
    COPY_FORMAT_MIN_WIDTH = 120
    PAGE_TITLE_MAX_WIDTH = 460
    BUTTON_MIN_WIDTHS = {
        "add": 150,
        "paste": 112,
        "import": 124,
        "copy": 86,
        "export": 96,
        "more": 96,
    }
    BUTTON_MINIMUM_WIDTHS = {
        "add": 38,
        "paste": 38,
        "import": 38,
        "copy": 38,
        "export": 38,
        "more": 42,
    }
    TABLE_SELECT_WIDTH = 76
    TABLE_STATUS_WIDTH = 124
    TABLE_PHONE_MIN_WIDTH = 150
    TABLE_PHONE_MAX_WIDTH = 250
    TABLE_GROUP_MIN_WIDTH = 180
    TABLE_GROUP_MAX_WIDTH = 520
    TABLE_NOTES_MIN_WIDTH = 120
    FILTER_COLUMNS = 3
    TABLE_HEADER_HEIGHT = 48
    TABLE_ROW_HEIGHT = 68
    SIDEBAR_ROW_HEIGHT = 50
    BADGE_HEIGHT = 30
    STATUS_BADGE_HEIGHT = 32
    PAGE_MARGIN_X = 18
    PAGE_MARGIN_Y = 20
    PANEL_MARGIN_X = 24
    PANEL_MARGIN_Y = 20
    EMPTY_TEXT_MAX_WIDTH = 520
    SPACING_XXS = 4
    SPACING_XS = 8
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 16
    SPACING_XL = 24
    BRAND_GAP = 8


COMMAND_LABELS = {
    "add": ("Add Recipient", "Add"),
    "paste": ("Paste List", "Paste"),
    "import": ("Import File", "Import"),
    "copy": ("Copy", "Copy"),
    "export": ("Export", "Export"),
    "more": ("More", "More"),
}


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


def svg_pixmap(name: str, color: str = BRAND_BLUE, size: int = 20) -> QPixmap:
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


def resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base_path / relative_path


def logo_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(str(resource_path(APP_LOGO_ASSET)))
    if pixmap.isNull():
        return QPixmap()
    return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class SvgIconLabel(QLabel):
    def __init__(self, name: str, color: str = BRAND_BLUE, size: int = 20) -> None:
        super().__init__()
        self.setPixmap(svg_pixmap(name, color, size))
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)


class PreferredWidthFrame(QFrame):
    def __init__(self, preferred_width: int) -> None:
        super().__init__()
        self.preferred_width = preferred_width

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        hint.setWidth(self.preferred_width)
        return hint


class ElidedLabel(QLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.full_text = text
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def setText(self, text: str) -> None:
        self.full_text = text
        self.setToolTip(text)
        super().setText(text)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        text = self.fontMetrics().elidedText(self.full_text, Qt.ElideRight, self.width())
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setFont(self.font())
        painter.drawText(self.rect(), self.alignment() | Qt.AlignVCenter, text)


def control_group(label_text: str, control: QWidget) -> QWidget:
    label = QLabel(label_text)
    label.setObjectName("FilterLabel")
    group = QWidget()
    group.setMinimumWidth(0)
    group.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    layout = QVBoxLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(LayoutMetrics.SPACING_XS)
    layout.addWidget(label)
    layout.addWidget(control)
    return group


def configure_combo(combo: QComboBox, minimum_width: int) -> QComboBox:
    combo.setMinimumWidth(0)
    combo.setMinimumContentsLength(8)
    combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumHeight(LayoutMetrics.CONTROL_HEIGHT)
    combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    return combo


def text_block_minimum_height(label: QLabel, lines: int) -> int:
    return label.fontMetrics().lineSpacing() * lines + LayoutMetrics.SPACING_SM


def icon_button(text: str, icon: str, role: str = SECONDARY_BUTTON, color: str = "#23314d") -> QPushButton:
    button = mark_button(QPushButton(text), role)
    button.setIcon(QIcon(svg_pixmap(icon, "#ffffff" if role == PRIMARY_BUTTON else color, LayoutMetrics.ICON_SIZE)))
    button.setIconSize(QSize(LayoutMetrics.ICON_SIZE, LayoutMetrics.ICON_SIZE))
    button.setMinimumHeight(LayoutMetrics.PRIMARY_CONTROL_HEIGHT if role == PRIMARY_BUTTON else LayoutMetrics.CONTROL_HEIGHT)
    button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    return button


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().setParent(None)
        elif item.layout():
            clear_layout(item.layout())


def fluid_ratio(width: int, narrow: int = 720, wide: int = 1400) -> float:
    if width <= narrow:
        return 0.0
    if width >= wide:
        return 1.0
    return (width - narrow) / (wide - narrow)


def fluid_value(width: int, narrow_value: int, wide_value: int, narrow: int = 720, wide: int = 1400) -> int:
    ratio = fluid_ratio(width, narrow, wide)
    return round(narrow_value + (wide_value - narrow_value) * ratio)


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def is_checked_state(value) -> bool:
    return getattr(value, "value", value) == Qt.Checked.value


class RecipientTableDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        rect = option.rect
        selected = bool(option.state & QStyle.State_Selected)
        if selected:
            fill = QColor(BRAND_SELECTION)
        elif index.row() % 2:
            fill = QColor("#f8fbff")
        else:
            fill = QColor("#ffffff")
        painter.fillRect(rect, fill)
        painter.setPen(QPen(QColor("#e7edf6"), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        if index.column() == 0:
            check_state = index.data(Qt.CheckStateRole)
            checked = is_checked_state(check_state)
            box_size = 20
            box = QRect(
                rect.x() + (rect.width() - box_size) // 2,
                rect.y() + (rect.height() - box_size) // 2,
                box_size,
                box_size,
            )
            painter.setRenderHint(QPainter.Antialiasing)
            if checked:
                painter.setBrush(QColor(BRAND_BLUE))
                painter.setPen(QPen(QColor(BRAND_BLUE), 1))
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
        model.setData(index, Qt.Unchecked if is_checked_state(current) else Qt.Checked, Qt.CheckStateRole)
        return True


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PourSend")
        self.setWindowIcon(QIcon(str(resource_path(APP_ICON_ASSET))))
        self.resize(LayoutMetrics.DEFAULT_WINDOW)
        self.setMinimumSize(LayoutMetrics.MIN_WINDOW)
        self.recipients, self.groups, self.settings, load_error = load_recipient_data()
        self.setAcceptDrops(True)
        self.recent_group = DEFAULT_GROUP
        self.last_imported_numbers: list[str | dict] = []
        self._building_table = False
        self._building_groups = False
        apply_app_theme(QApplication.instance())
        self._build_ui()
        self.restore_window_geometry()
        QApplication.instance().installEventFilter(self)
        self.refresh_group_list()
        self.refresh_table()
        if load_error:
            QMessageBox.warning(self, "Local data", load_error)

    def _build_ui(self) -> None:
        app_icon = QLabel()
        self.app_icon = app_icon
        app_icon.setObjectName("AppIcon")
        app_icon.setAlignment(Qt.AlignCenter)
        app_icon.setFixedSize(LayoutMetrics.LOGO_SIZE, LayoutMetrics.LOGO_SIZE)
        app_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        app_icon.setScaledContents(False)
        app_icon.setPixmap(logo_pixmap(LayoutMetrics.LOGO_SIZE))
        title = QLabel("PourSend")
        self.brand_title = title
        title.setObjectName("AppTitle")

        self.search = QLineEdit()
        self.search.setObjectName("SearchField")
        self.search.setPlaceholderText("Search recipients...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(LayoutMetrics.SEARCH_MIN_WIDTH)
        self.search.setMaximumWidth(LayoutMetrics.SEARCH_MAX_WIDTH)
        self.search.setMinimumHeight(LayoutMetrics.CONTROL_HEIGHT)
        self.search.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search.addAction(QIcon(svg_pixmap("search", BRAND_BLUE, 18)), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self.refresh_table)

        self.sort_field_combo = QComboBox()
        self.sort_field_combo.addItem("Recently Added", SORT_RECENT)
        self.sort_field_combo.addItem("Phone Number", SORT_PHONE)
        self.sort_field_combo.addItem("Group", SORT_GROUP)
        configure_combo(self.sort_field_combo, LayoutMetrics.SORT_FIELD_MIN_WIDTH)
        self.sort_field_combo.currentIndexChanged.connect(self.refresh_table)

        self.sort_direction_combo = QComboBox()
        self.sort_direction_combo.addItem("Ascending", False)
        self.sort_direction_combo.addItem("Descending", True)
        configure_combo(self.sort_direction_combo, LayoutMetrics.SORT_DIRECTION_MIN_WIDTH)
        self.sort_direction_combo.currentIndexChanged.connect(self.refresh_table)

        add_button = icon_button(COMMAND_LABELS["add"][0], "add", PRIMARY_BUTTON)
        paste_button = icon_button(COMMAND_LABELS["paste"][0], "clipboard")
        import_button = icon_button(COMMAND_LABELS["import"][0], "file-up")
        copy_button = icon_button(COMMAND_LABELS["copy"][0], "copy")
        export_button = icon_button(COMMAND_LABELS["export"][0], "download")
        more_button = icon_button(COMMAND_LABELS["more"][0], "more", SUBTLE_BUTTON)
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
        more_menu.addAction("About PourSend", self.show_about)
        more_menu.addSeparator()
        more_menu.addAction("Clear All Data", self.clear_all)
        more_button.setMenu(more_menu)

        self.group_list = QListWidget()
        self.group_list.currentItemChanged.connect(lambda _current, _previous: self.refresh_table())
        self.group_list.setMinimumWidth(0)
        self.group_list.setSpacing(LayoutMetrics.LIST_ITEM_SPACING)
        self.group_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.group_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.group_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        new_group_button = icon_button("New Group", "add")
        rename_group_button = icon_button("Rename", "edit")
        delete_group_button = icon_button("Delete", "trash", DANGER_BUTTON, "#d24b4b")
        new_group_button.clicked.connect(self.create_group)
        rename_group_button.clicked.connect(self.rename_group)
        delete_group_button.clicked.connect(self.delete_group)

        group_title = QLabel("Groups")
        group_title.setObjectName("SectionTitle")
        top_new_group_button = mark_button(QPushButton("+"), SECONDARY_BUTTON)
        top_new_group_button.setObjectName("IconButton")
        top_new_group_button.setFixedSize(LayoutMetrics.ICON_BUTTON_SIZE, LayoutMetrics.ICON_BUTTON_SIZE)
        top_new_group_button.setToolTip("New Group")
        top_new_group_button.clicked.connect(self.create_group)
        group_header = QHBoxLayout()
        group_header.setSpacing(LayoutMetrics.SPACING_SM)
        group_header.addWidget(group_title)
        group_header.addStretch(1)
        group_header.addWidget(top_new_group_button)
        group_tools = QVBoxLayout()
        group_tools.setContentsMargins(
            LayoutMetrics.SIDEBAR_PADDING,
            LayoutMetrics.SIDEBAR_PADDING,
            LayoutMetrics.SIDEBAR_PADDING,
            LayoutMetrics.SIDEBAR_PADDING,
        )
        group_tools.setSpacing(LayoutMetrics.SPACING_MD)
        group_tools.addLayout(group_header)
        group_tools.addWidget(self.group_list, stretch=1)
        group_tools.addWidget(new_group_button)
        group_action_row = QVBoxLayout()
        group_action_row.setSpacing(LayoutMetrics.SPACING_XS)
        group_action_row.addWidget(rename_group_button)
        group_action_row.addWidget(delete_group_button)
        group_tools.addLayout(group_action_row)

        sidebar = PreferredWidthFrame(LayoutMetrics.SIDEBAR_PREFERRED_WIDTH)
        self.sidebar = sidebar
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(LayoutMetrics.SIDEBAR_MIN_WIDTH)
        sidebar.setMaximumWidth(LayoutMetrics.SIDEBAR_MAX_WIDTH)
        sidebar.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sidebar.setLayout(group_tools)

        self.command_buttons = [
            ("add", add_button),
            ("paste", paste_button),
            ("import", import_button),
            ("copy", copy_button),
            ("export", export_button),
            ("more", more_button),
        ]
        self.command_icons = {key: button.icon() for key, button in self.command_buttons}
        self.command_bar = QGridLayout()
        self.command_bar.setContentsMargins(0, 0, 0, 0)
        self.command_bar.setHorizontalSpacing(LayoutMetrics.SPACING_XS)
        self.command_bar.setVerticalSpacing(LayoutMetrics.SPACING_XS)
        self.command_bar_built = False

        brand = QWidget()
        self.brand = brand
        brand.setObjectName("BrandLockup")
        brand.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.brand_layout = QHBoxLayout(brand)
        self.brand_layout.setContentsMargins(0, 0, 0, 0)
        self.brand_layout.setSpacing(LayoutMetrics.BRAND_GAP)
        self.brand_layout.addWidget(app_icon)
        self.brand_layout.addWidget(title, alignment=Qt.AlignVCenter)
        brand.setFixedSize(brand.sizeHint())

        command_widget = QWidget()
        self.command_widget = command_widget
        command_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        command_widget.setLayout(self.command_bar)

        header = QFrame()
        self.header = header
        header.setObjectName("Header")
        header.setMinimumHeight(LayoutMetrics.HEADER_MIN_HEIGHT)
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.header_layout = QHBoxLayout(header)
        self.header_layout.setContentsMargins(
            LayoutMetrics.HEADER_MARGIN_X,
            LayoutMetrics.HEADER_MARGIN_Y,
            LayoutMetrics.HEADER_MARGIN_RIGHT,
            LayoutMetrics.HEADER_MARGIN_Y,
        )
        self.header_layout.setSpacing(LayoutMetrics.SPACING_LG)
        self.header_layout.addWidget(brand)
        self.header_layout.addWidget(self.search, stretch=2)
        self.header_layout.addWidget(command_widget)

        self.workspace_title = ElidedLabel("All Recipients")
        self.workspace_title.setObjectName("WorkspaceTitle")
        self.workspace_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.workspace_title.setMaximumWidth(LayoutMetrics.PAGE_TITLE_MAX_WIDTH)
        self.workspace_meta = QLabel("")
        self.workspace_meta.setObjectName("CountBadge")
        self.workspace_meta.setAlignment(Qt.AlignCenter)
        self.workspace_meta.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        heading_cluster = QWidget()
        heading_cluster.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        heading_cluster_layout = QHBoxLayout(heading_cluster)
        heading_cluster_layout.setContentsMargins(0, 0, 0, 0)
        heading_cluster_layout.setSpacing(LayoutMetrics.SPACING_SM)
        heading_cluster_layout.addWidget(self.workspace_title)
        heading_cluster_layout.addWidget(self.workspace_meta, alignment=Qt.AlignVCenter)

        workspace_heading = QHBoxLayout()
        workspace_heading.setSpacing(LayoutMetrics.SPACING_SM)
        workspace_heading.setContentsMargins(0, 0, 0, 0)
        workspace_heading.addWidget(heading_cluster)
        workspace_heading.addStretch(1)

        filter_bar = QGridLayout()
        self.filter_bar = filter_bar
        self.filter_bar_columns = 0
        filter_bar.setHorizontalSpacing(LayoutMetrics.SPACING_LG)
        filter_bar.setVerticalSpacing(LayoutMetrics.SPACING_MD)
        filter_bar.setContentsMargins(0, 2, 0, 0)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Select", "Phone number", "Group", "Notes", "Status"])
        for column in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(column)
            if header_item is None:
                continue
            header_item.setTextAlignment(Qt.AlignCenter if column in (0, 4) else Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(LayoutMetrics.TABLE_ROW_HEIGHT)
        self.table.setMinimumHeight(LayoutMetrics.TABLE_HEADER_HEIGHT + LayoutMetrics.TABLE_ROW_HEIGHT * 4)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_recipient_context_menu)
        self.table.setItemDelegate(RecipientTableDelegate(self.table))
        table_header = self.table.horizontalHeader()
        table_header.setFixedHeight(LayoutMetrics.TABLE_HEADER_HEIGHT)
        table_header.setMinimumSectionSize(72)
        table_header.setSectionResizeMode(0, QHeaderView.Fixed)
        table_header.setSectionResizeMode(1, QHeaderView.Fixed)
        table_header.setSectionResizeMode(2, QHeaderView.Fixed)
        table_header.setSectionResizeMode(3, QHeaderView.Stretch)
        table_header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.itemChanged.connect(self.table_item_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self.edit_selected())

        self.empty_state = QWidget()
        self.empty_state.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        empty_outer = QVBoxLayout(self.empty_state)
        empty_outer.setContentsMargins(0, 0, 0, 0)
        empty_outer.setSpacing(0)
        empty_outer.addStretch(1)
        empty_content = QWidget()
        empty_content.setObjectName("EmptyStateContent")
        empty_content.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        empty_layout = QVBoxLayout(empty_content)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(LayoutMetrics.SPACING_LG)
        empty_layout.setAlignment(Qt.AlignCenter)
        self.empty_title = QLabel("No recipients found")
        self.empty_title.setObjectName("EmptyTitle")
        self.empty_subtitle = QLabel("Try changing your search or add a new recipient.")
        self.empty_subtitle.setObjectName("EmptySubtitle")
        self.empty_subtitle.setAlignment(Qt.AlignCenter)
        self.empty_subtitle.setWordWrap(True)
        self.empty_subtitle.setMaximumWidth(LayoutMetrics.EMPTY_TEXT_MAX_WIDTH)
        self.empty_subtitle.setMinimumHeight(text_block_minimum_height(self.empty_subtitle, 2))
        empty_layout.addWidget(self.empty_title, alignment=Qt.AlignCenter)
        empty_layout.addWidget(self.empty_subtitle, alignment=Qt.AlignCenter)
        self.empty_actions = QWidget()
        empty_actions_layout = QHBoxLayout(self.empty_actions)
        empty_actions_layout.setContentsMargins(0, LayoutMetrics.SPACING_SM, 0, 0)
        empty_actions_layout.setSpacing(LayoutMetrics.SPACING_SM)
        empty_add_button = icon_button("Add Recipient", "add", PRIMARY_BUTTON)
        empty_paste_button = icon_button("Paste List", "clipboard")
        empty_import_button = icon_button("Import File", "file-up")
        empty_add_button.clicked.connect(self.add_person)
        empty_paste_button.clicked.connect(self.paste_list)
        empty_import_button.clicked.connect(self.import_csv)
        empty_actions_layout.addWidget(empty_add_button)
        empty_actions_layout.addWidget(empty_paste_button)
        empty_actions_layout.addWidget(empty_import_button)
        empty_layout.addWidget(self.empty_actions, alignment=Qt.AlignCenter)
        empty_outer.addWidget(empty_content, alignment=Qt.AlignCenter)
        empty_outer.addStretch(1)

        self.table_stack = QStackedWidget()
        self.table_stack.setMinimumWidth(0)
        self.table_stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.table_stack.addWidget(self.table)
        self.table_stack.addWidget(self.empty_state)

        self.phone_format_combo = QComboBox()
        for format_key, label in PHONE_FORMATS:
            self.phone_format_combo.addItem(label, format_key)
        configure_combo(self.phone_format_combo, LayoutMetrics.PHONE_FORMAT_MIN_WIDTH)
        saved_format = self.settings.get("phone_format")
        for index in range(self.phone_format_combo.count()):
            if self.phone_format_combo.itemData(index) == saved_format:
                self.phone_format_combo.setCurrentIndex(index)
                break
        self.phone_format_combo.currentIndexChanged.connect(self.phone_format_changed)

        self.copy_scope_combo = QComboBox()
        self.copy_scope_combo.addItem("Checked Numbers", SCOPE_SELECTION)
        self.copy_scope_combo.addItem("Current Search", SCOPE_SEARCH)
        self.copy_scope_combo.setToolTip("Choose which recipients the Copy action uses.")
        configure_combo(self.copy_scope_combo, LayoutMetrics.COPY_SCOPE_MIN_WIDTH)
        self.copy_format_combo = QComboBox()
        self.copy_format_combo.addItem("Displayed Number", COPY_DISPLAYED)
        self.copy_format_combo.addItem("Digits Only", COPY_DIGITS)
        self.copy_format_combo.addItem("E.164", COPY_E164)
        self.copy_format_combo.setToolTip("Choose how phone numbers are formatted when copied.")
        configure_combo(self.copy_format_combo, LayoutMetrics.COPY_FORMAT_MIN_WIDTH)
        self.count_label = QLabel("")
        self.count_label.setObjectName("MutedText")
        self.filter_groups = [
            control_group("Sort", self.sort_field_combo),
            control_group("Order", self.sort_direction_combo),
            control_group("Phone Format", self.phone_format_combo),
            control_group("Copy Scope", self.copy_scope_combo),
            control_group("Copy Format", self.copy_format_combo),
        ]
        self.arrange_filter_toolbar()

        self.action_bar = QFrame()
        self.action_bar.setObjectName("ActionBar")
        action_layout = QVBoxLayout(self.action_bar)
        action_layout.setContentsMargins(LayoutMetrics.SPACING_MD, LayoutMetrics.SPACING_SM, LayoutMetrics.SPACING_MD, LayoutMetrics.SPACING_SM)
        action_layout.setSpacing(LayoutMetrics.SPACING_SM)
        self.selection_actions = QWidget()
        selection_layout = QGridLayout(self.selection_actions)
        selection_layout.setContentsMargins(0, 0, 0, 0)
        selection_layout.setHorizontalSpacing(LayoutMetrics.SPACING_SM)
        selection_layout.setVerticalSpacing(LayoutMetrics.SPACING_SM)
        self.select_all_button = mark_button(QPushButton("Select All"), SUBTLE_BUTTON)
        self.deselect_all_button = mark_button(QPushButton("Clear Selection"), SUBTLE_BUTTON)
        self.edit_button = mark_button(QPushButton("Edit Recipient"), SECONDARY_BUTTON)
        self.select_all_button.clicked.connect(lambda: self.set_all_visible(True))
        self.deselect_all_button.clicked.connect(lambda: self.set_all_visible(False))
        self.edit_button.clicked.connect(self.edit_selected)
        self.table_action_buttons = [self.select_all_button, self.deselect_all_button, self.edit_button]
        for button in self.table_action_buttons:
            button.setMinimumHeight(LayoutMetrics.CONTROL_HEIGHT)
            button.setMinimumWidth(0)
            button.setToolTip(button.text())
            button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.select_all_button.setToolTip("Check all recipients currently visible in the table.")
        self.deselect_all_button.setToolTip("Clear checks from all recipients currently visible in the table.")
        self.bulk_count_label = QLabel("0 recipients checked")
        self.bulk_count_label.setObjectName("BulkCount")
        self.bulk_actions = QWidget()
        bulk_layout = QGridLayout(self.bulk_actions)
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        bulk_layout.setHorizontalSpacing(LayoutMetrics.SPACING_SM)
        bulk_layout.setVerticalSpacing(LayoutMetrics.SPACING_SM)
        bulk_copy_button = icon_button("Copy", "clipboard")
        bulk_set_button = icon_button("Set Groups", "tag")
        bulk_add_button = icon_button("Add Checked to Group", "user-add")
        bulk_remove_button = icon_button("Remove Checked from Group", "user-minus")
        bulk_delete_button = icon_button("Delete Selected...", "trash", DANGER_BUTTON, "#d24b4b")
        bulk_copy_button.clicked.connect(self.copy_selected)
        bulk_set_button.clicked.connect(self.batch_edit_checked)
        bulk_add_button.clicked.connect(self.assign_checked_to_group)
        bulk_remove_button.clicked.connect(self.remove_checked_from_current_group)
        bulk_delete_button.clicked.connect(self.delete_selected)
        self.selection_layout = selection_layout
        self.bulk_layout = bulk_layout
        self.bulk_action_buttons = [bulk_copy_button, bulk_add_button, bulk_set_button, bulk_remove_button, bulk_delete_button]
        for button in self.bulk_action_buttons:
            button.setMinimumWidth(0)
            button.setToolTip(button.text())
            button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.action_bar_columns = 0
        action_layout.addWidget(self.bulk_actions)

        workspace = QFrame()
        workspace.setObjectName("Workspace")
        workspace.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.workspace_layout = QVBoxLayout(workspace)
        self.workspace_layout.setContentsMargins(
            LayoutMetrics.PANEL_MARGIN_X,
            LayoutMetrics.PANEL_MARGIN_Y,
            LayoutMetrics.PANEL_MARGIN_X,
            LayoutMetrics.PANEL_MARGIN_Y,
        )
        self.workspace_layout.setSpacing(LayoutMetrics.SPACING_LG)
        self.workspace_layout.addLayout(workspace_heading)
        self.workspace_layout.addLayout(filter_bar)
        self.workspace_layout.addWidget(self.selection_actions)
        self.workspace_layout.addWidget(self.table_stack, stretch=1)
        self.workspace_layout.addWidget(self.action_bar)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(
            LayoutMetrics.PAGE_MARGIN_X,
            LayoutMetrics.PAGE_MARGIN_Y,
            LayoutMetrics.PAGE_MARGIN_X,
            LayoutMetrics.PAGE_MARGIN_Y,
        )
        self.body_layout.setSpacing(LayoutMetrics.SPACING_LG)
        self.body_layout.addWidget(sidebar)
        self.body_layout.addWidget(workspace, stretch=1)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header)
        main_layout.addLayout(self.body_layout, stretch=1)

        root = QWidget()
        root.setObjectName("AppRoot")
        root.setLayout(main_layout)
        self.main_scroll_area = QScrollArea()
        self.main_scroll_area.setObjectName("MainScrollArea")
        self.main_scroll_area.setWidgetResizable(True)
        self.main_scroll_area.setFrameShape(QFrame.NoFrame)
        self.main_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_scroll_area.setWidget(root)
        self.setCentralWidget(self.main_scroll_area)
        self.arrange_responsive_layout()

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
            if editable_text_widget_has_focus() or not self.recipient_table_has_focus():
                return False
            self.set_all_visible(True)
            return True
        if event.key() == Qt.Key_A and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            if editable_text_widget_has_focus() or not self.recipient_table_has_focus():
                return False
            self.set_all_visible(False)
            return True
        if event.matches(QKeySequence.Undo):
            if editable_text_widget_has_focus():
                return False
            self.undo_last_import()
            return True
        if event.key() == Qt.Key_Delete and event.modifiers() == Qt.NoModifier:
            if editable_text_widget_has_focus() or not self.recipient_table_has_focus():
                return False
            self.delete_highlighted_recipient()
            return True

        return super().eventFilter(watched, event)

    def shortcut_focus_is_inside_window(self) -> bool:
        focused = QApplication.focusWidget()
        return focused is None or focused is self or self.isAncestorOf(focused)

    def recipient_table_has_focus(self) -> bool:
        focused = QApplication.focusWidget()
        return focused is self.table or focused is self.table.viewport() or self.table.isAncestorOf(focused)

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
            item.setSizeHint(QSize(0, LayoutMetrics.SIDEBAR_ROW_HEIGHT))
            self.group_list.addItem(item)
            self.group_list.setItemWidget(item, self.group_row_widget(label, value))
        for group in self.groups:
            item = QListWidgetItem("")
            item.setData(Qt.UserRole, group)
            item.setSizeHint(QSize(0, LayoutMetrics.SIDEBAR_ROW_HEIGHT))
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
        layout.setContentsMargins(LayoutMetrics.GROUP_ROW_MARGIN_X, 0, LayoutMetrics.GROUP_ROW_MARGIN_X, 0)
        layout.setSpacing(LayoutMetrics.SPACING_SM)
        icon_name, icon_color = self.group_icon(group)
        icon = SvgIconLabel(icon_name, icon_color, 20)
        icon.setObjectName("GroupIcon")
        icon.setProperty("groupName", group)
        name = ElidedLabel(label)
        name.setObjectName("GroupName")
        name.setMinimumWidth(0)
        name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        count = QLabel(str(group_recipient_count(self.recipients, group)))
        count.setObjectName("GroupCountBadge")
        count.setAlignment(Qt.AlignCenter)
        count.setMinimumWidth(30)
        layout.addWidget(icon)
        layout.addWidget(name, stretch=1)
        layout.addWidget(count)
        return row

    def group_icon(self, group: str) -> tuple[str, str]:
        if group == ALL_RECIPIENTS:
            return "groups", BRAND_BLUE
        if group == DEFAULT_GROUP:
            return "home", "#53627c"
        if group == "Female Mandarin":
            return "groups", "#f05a75"
        if group == "Male Cantonese":
            return "groups", BRAND_BLUE
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
        for row, index in enumerate(indexes):
            recipient = self.recipients[index]
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(str(index)))
            checked = QTableWidgetItem("")
            checked.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            checked.setCheckState(Qt.Checked if recipient.get("selected") else Qt.Unchecked)
            checked.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, checked)
            phone_item = QTableWidgetItem(format_phone_number(recipient.get("phone", ""), phone_format))
            phone_item.setIcon(QIcon(svg_pixmap("phone", BRAND_BLUE, 18)))
            phone_font = phone_item.font()
            phone_font.setBold(True)
            phone_item.setFont(phone_font)
            phone_item.setToolTip(recipient.get("phone", ""))
            phone_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 1, phone_item)
            self.table.setCellWidget(row, 2, self.group_tags_widget(valid_recipient_groups(recipient, self.groups)))
            notes_item = QTableWidgetItem(recipient.get("notes", ""))
            notes_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 3, notes_item)
            normalized, status = normalize_us_phone(recipient.get("phone", ""))
            self.table.setCellWidget(row, 4, self.status_badge_widget(status, normalized or status))
        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)
        self._building_table = False
        has_visible_recipients = bool(indexes)
        has_recipients = bool(self.recipients)
        self.table_stack.setCurrentWidget(self.table if has_visible_recipients else self.empty_state)
        empty_title, empty_subtitle = empty_state_message(query, has_recipients)
        self.empty_title.setText(empty_title)
        self.empty_subtitle.setText(empty_subtitle)
        self.empty_actions.setVisible(not has_recipients)
        self.resize_table_columns()
        self.update_counts()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.arrange_responsive_layout()
        if hasattr(self, "filter_bar"):
            self.arrange_filter_toolbar()
        if hasattr(self, "table"):
            self.resize_table_columns()

    def arrange_responsive_layout(self) -> None:
        width = self.responsive_width()
        self.update_brand_lockup()
        if hasattr(self, "command_bar"):
            self.arrange_command_bar()
        if hasattr(self, "selection_layout"):
            self.arrange_action_bar()
        if hasattr(self, "header_layout"):
            margin_x = fluid_value(width, LayoutMetrics.SPACING_LG, LayoutMetrics.HEADER_MARGIN_X)
            margin_y = fluid_value(width, LayoutMetrics.SPACING_SM, LayoutMetrics.HEADER_MARGIN_Y)
            self.header_layout.setContentsMargins(margin_x, margin_y, margin_x, margin_y)
            self.header_layout.setSpacing(fluid_value(width, LayoutMetrics.SPACING_SM, LayoutMetrics.SPACING_LG))
        if hasattr(self, "header"):
            logo_size = self.app_icon.height() if hasattr(self, "app_icon") else LayoutMetrics.LOGO_SIZE
            self.header.setMinimumHeight(max(LayoutMetrics.HEADER_MIN_HEIGHT, logo_size + margin_y * 2))
        if hasattr(self, "body_layout"):
            if hasattr(self, "sidebar"):
                sidebar_width = clamp(
                    round(width * 0.185),
                    128,
                    LayoutMetrics.SIDEBAR_PREFERRED_WIDTH,
                )
                self.sidebar.setMinimumWidth(sidebar_width)
                self.sidebar.setMaximumWidth(sidebar_width)
            margin_x = fluid_value(width, LayoutMetrics.SPACING_XS, LayoutMetrics.PAGE_MARGIN_X)
            margin_y = fluid_value(width, LayoutMetrics.SPACING_SM, LayoutMetrics.PAGE_MARGIN_Y)
            self.body_layout.setContentsMargins(margin_x, margin_y, margin_x, margin_y)
            self.body_layout.setSpacing(fluid_value(width, LayoutMetrics.SPACING_SM, LayoutMetrics.SPACING_LG))
        if hasattr(self, "workspace_layout"):
            margin_x = fluid_value(width, LayoutMetrics.SPACING_MD, LayoutMetrics.PANEL_MARGIN_X)
            margin_y = fluid_value(width, LayoutMetrics.SPACING_MD, LayoutMetrics.PANEL_MARGIN_Y)
            self.workspace_layout.setContentsMargins(margin_x, margin_y, margin_x, margin_y)
            self.workspace_layout.setSpacing(fluid_value(width, LayoutMetrics.SPACING_MD, LayoutMetrics.SPACING_LG))
        if hasattr(self, "filter_bar"):
            self.filter_bar.setHorizontalSpacing(fluid_value(width, LayoutMetrics.SPACING_SM, LayoutMetrics.SPACING_LG))
            self.filter_bar.setVerticalSpacing(fluid_value(width, LayoutMetrics.SPACING_SM, LayoutMetrics.SPACING_MD))

    def responsive_width(self) -> int:
        if hasattr(self, "main_scroll_area") and self.main_scroll_area.viewport().width() > 0:
            return self.main_scroll_area.viewport().width()
        return self.width()

    def update_brand_lockup(self) -> None:
        if not hasattr(self, "app_icon"):
            return
        width = self.responsive_width()
        logo_size = fluid_value(width, LayoutMetrics.LOGO_MIN_SIZE, LayoutMetrics.LOGO_SIZE)
        self.app_icon.setFixedSize(logo_size, logo_size)
        self.app_icon.setPixmap(logo_pixmap(logo_size))
        self.brand_layout.setSpacing(fluid_value(width, LayoutMetrics.SPACING_XS, LayoutMetrics.BRAND_GAP))
        self.brand.setFixedSize(self.brand.sizeHint())

    def arrange_command_bar(self) -> None:
        if not self.command_bar_built:
            clear_layout(self.command_bar)
            for index, (_key, button) in enumerate(self.command_buttons):
                column = index + (1 if index >= 3 else 0)
                self.command_bar.addWidget(button, 0, column)
            self.command_bar_built = True
        width = self.responsive_width()
        self.command_bar.setHorizontalSpacing(fluid_value(width, LayoutMetrics.SPACING_XXS, LayoutMetrics.SPACING_XS))
        self.command_bar.setColumnMinimumWidth(3, fluid_value(width, LayoutMetrics.SPACING_XXS, LayoutMetrics.SPACING_XS))
        for key, button in self.command_buttons:
            full_label, _compact_label = COMMAND_LABELS[key]
            button_width = fluid_value(
                width,
                LayoutMetrics.BUTTON_MINIMUM_WIDTHS[key],
                LayoutMetrics.BUTTON_MIN_WIDTHS[key],
                wide=1200,
            )
            button.setMinimumWidth(button_width)
            button.setMaximumWidth(button_width)
            button.setText(self.elided_button_text(button, full_label, button_width))
            button.setIcon(self.command_icons[key])
            button.setToolTip(full_label)
            self.set_dynamic_property(button, "responsiveCommand", button_width < LayoutMetrics.BUTTON_MIN_WIDTHS[key])

    def elided_button_text(self, button: QPushButton, text: str, button_width: int) -> str:
        icon_space = button.iconSize().width() + LayoutMetrics.SPACING_XS if not button.icon().isNull() else 0
        text_width = button_width - icon_space - fluid_value(self.responsive_width(), 12, 16)
        if text_width < button.fontMetrics().horizontalAdvance("W"):
            return ""
        return button.fontMetrics().elidedText(text, Qt.ElideRight, text_width)

    def set_dynamic_property(self, widget: QWidget, name: str, value: bool) -> None:
        if widget.property(name) == value:
            return
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def arrange_action_bar(self) -> None:
        available_width = self.available_workspace_width()
        columns = 5 if available_width >= 960 else 3 if available_width >= 520 else 2
        if self.action_bar_columns == columns and self.selection_layout.count() and self.bulk_layout.count():
            return
        clear_layout(self.selection_layout)
        clear_layout(self.bulk_layout)
        for column in range(8):
            self.selection_layout.setColumnStretch(column, 0)
            self.bulk_layout.setColumnStretch(column, 0)
        selection_columns = 3 if columns >= 5 else 2
        for index, button in enumerate(self.table_action_buttons):
            self.selection_layout.addWidget(button, index // selection_columns, index % selection_columns)
        if columns >= 5:
            self.selection_layout.setColumnStretch(3, 1)
            self.bulk_layout.addWidget(self.bulk_count_label, 0, 0)
            self.bulk_layout.setColumnStretch(1, 1)
            for index, button in enumerate(self.bulk_action_buttons):
                self.bulk_layout.addWidget(button, 0, index + 2)
        else:
            self.bulk_layout.addWidget(self.bulk_count_label, 0, 0, 1, columns)
            for index, button in enumerate(self.bulk_action_buttons):
                self.bulk_layout.addWidget(button, 1 + index // columns, index % columns)
        self.action_bar_columns = columns

    def available_workspace_width(self) -> int:
        width = self.responsive_width()
        body_margins = self.body_layout.contentsMargins() if hasattr(self, "body_layout") else None
        workspace_margins = self.workspace_layout.contentsMargins() if hasattr(self, "workspace_layout") else None
        sidebar_width = self.sidebar.width() if hasattr(self, "sidebar") else 0
        body_margin_width = body_margins.left() + body_margins.right() if body_margins else 0
        workspace_margin_width = workspace_margins.left() + workspace_margins.right() if workspace_margins else 0
        body_spacing = self.body_layout.spacing() if hasattr(self, "body_layout") else 0
        return max(0, width - sidebar_width - body_margin_width - body_spacing - workspace_margin_width)

    def arrange_filter_toolbar(self) -> None:
        columns = LayoutMetrics.FILTER_COLUMNS
        if columns == self.filter_bar_columns:
            return
        while self.filter_bar.count():
            item = self.filter_bar.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for index, group in enumerate(self.filter_groups):
            row = index // columns
            column = index % columns
            self.filter_bar.addWidget(group, row, column)
        for column in range(LayoutMetrics.FILTER_COLUMNS):
            self.filter_bar.setColumnStretch(column, 1 if column < columns else 0)
        self.filter_bar_columns = columns

    def resize_table_columns(self) -> None:
        viewport_width = self.table.viewport().width()
        if viewport_width <= 0:
            return
        ratio = fluid_ratio(self.width())
        self.table.horizontalHeader().setMinimumSectionSize(fluid_value(self.width(), 44, 72))
        select_width = fluid_value(self.width(), 64, LayoutMetrics.TABLE_SELECT_WIDTH)
        status_width = fluid_value(self.width(), 82, LayoutMetrics.TABLE_STATUS_WIDTH)
        phone_min = fluid_value(self.width(), 128, LayoutMetrics.TABLE_PHONE_MIN_WIDTH)
        phone_max = fluid_value(self.width(), 180, LayoutMetrics.TABLE_PHONE_MAX_WIDTH)
        group_min = fluid_value(self.width(), 96, LayoutMetrics.TABLE_GROUP_MIN_WIDTH)
        group_max = fluid_value(self.width(), 180, LayoutMetrics.TABLE_GROUP_MAX_WIDTH)
        notes_min = fluid_value(self.width(), 72, LayoutMetrics.TABLE_NOTES_MIN_WIDTH)
        group_ratio = 0.45 + (0.72 - 0.45) * ratio
        phone_width = min(phone_max, max(phone_min, fluid_value(self.width(), 128, 176)))
        available_for_flexible_columns = max(0, viewport_width - select_width - status_width - phone_width - 4)
        group_width = min(group_max, max(group_min, int(available_for_flexible_columns * group_ratio)))
        if group_width + notes_min > available_for_flexible_columns:
            group_width = max(group_min, available_for_flexible_columns - notes_min)
        self.table.setColumnWidth(0, select_width)
        self.table.setColumnWidth(1, phone_width)
        self.table.setColumnWidth(2, group_width)
        self.table.setColumnWidth(4, status_width)
        self.table.updateGeometries()
        self.table.viewport().update()

    def restore_window_geometry(self) -> None:
        saved = self.settings.get("window_geometry")
        if not isinstance(saved, dict):
            return
        try:
            width = int(saved.get("width", 0))
            height = int(saved.get("height", 0))
            x = int(saved.get("x", 0))
            y = int(saved.get("y", 0))
        except (TypeError, ValueError):
            return
        if width < LayoutMetrics.MIN_WINDOW.width() or height < LayoutMetrics.MIN_WINDOW.height():
            return
        rect = QRect(x, y, width, height)
        screen = self.screen() or QGuiApplication.primaryScreen()
        if not self.window_rect_intersects_visible_screen(rect):
            if screen is None:
                return
            available = screen.availableGeometry()
            rect.moveCenter(available.center())
            rect.moveTopLeft(available.topLeft() if not available.intersects(rect) else rect.topLeft())
        self.setGeometry(rect)
        if saved.get("maximized") is True:
            self.showMaximized()

    def window_rect_intersects_visible_screen(self, rect: QRect) -> bool:
        for screen in QGuiApplication.screens():
            if screen.availableGeometry().intersects(rect):
                return True
        return False

    def save_window_geometry(self) -> None:
        geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
        if geometry.width() <= 0 or geometry.height() <= 0:
            return
        self.settings["window_geometry"] = {
            "x": geometry.x(),
            "y": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height(),
            "maximized": self.isMaximized(),
        }
        save_recipient_data(self.recipients, self.groups, self.settings)

    def closeEvent(self, event) -> None:
        self.save_window_geometry()
        super().closeEvent(event)

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
            tag.setFixedHeight(LayoutMetrics.BADGE_HEIGHT)
            tag.setFixedWidth(tag.fontMetrics().horizontalAdvance(group) + 60)
            tag.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            layout.addWidget(tag)
        if len(memberships) > 2:
            more = QLabel(f"+{len(memberships) - 2}")
            more.setObjectName("GroupTag")
            more.setFixedHeight(LayoutMetrics.BADGE_HEIGHT)
            more.setFixedWidth(more.fontMetrics().horizontalAdvance(more.text()) + 60)
            more.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            layout.addWidget(more)
        layout.addStretch(1)
        return container

    def status_badge_widget(self, status: str, tooltip: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.addStretch(1)
        badge = QLabel(status)
        badge.setObjectName("StatusBadge")
        badge.setToolTip(tooltip)
        badge.setFixedHeight(LayoutMetrics.STATUS_BADGE_HEIGHT)
        badge.setFixedWidth(badge.fontMetrics().horizontalAdvance(status) + 44)
        badge.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
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

    def show_recipient_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        self.table.selectRow(row)
        menu = QMenu(self.table)
        menu.addAction("Edit", self.edit_selected)
        menu.addAction("Delete...", self.delete_highlighted_recipient)
        menu.exec(self.table.viewport().mapToGlobal(position))

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
        self.save_and_update(selected_group=self.current_group_filter())

    def delete_highlighted_recipient(self) -> None:
        index = self.selected_visible_index()
        if index is None:
            QMessageBox.information(self, "Delete recipient", "Select one recipient to delete.")
            return
        self.delete_recipient_at_index(index)

    def delete_recipient_at_index(self, index: int) -> None:
        if not 0 <= index < len(self.recipients):
            return
        phone = str(self.recipients[index].get("phone", ""))
        display_phone = format_phone_number(phone, self.current_phone_format())
        answer = QMessageBox.question(
            self,
            "Delete this recipient?",
            f"Delete recipient {display_phone}?\n\nThis cannot be undone.",
        )
        if answer != QMessageBox.Yes:
            return
        del self.recipients[index]
        self.save_and_update(selected_group=self.current_group_filter())

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

    def show_about(self) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("About PourSend")
        dialog.setIconPixmap(logo_pixmap(128))
        dialog.setText("PourSend")
        dialog.setInformativeText(
            f"Version {__version__}\n\n"
            "A local desktop utility for organizing recipients and preparing phone-number lists."
        )
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec()

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
        has_visible_recipients = search_count > 0
        group_label = workspace_title(current_group)
        self.workspace_title.setText(group_label)
        self.workspace_meta.setText("1 recipient" if group_count == 1 else f"{group_count} recipients")
        self.bulk_count_label.setText(checked_status_text(total_selected))
        self.bulk_actions.setVisible(total_selected > 0)
        self.selection_actions.setVisible(has_visible_recipients)
        self.action_bar.setVisible(total_selected > 0)
        for button in self.table_action_buttons:
            button.setEnabled(has_visible_recipients)
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
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(resource_path(APP_ICON_ASSET))))
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

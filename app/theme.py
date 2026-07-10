from __future__ import annotations

from PySide6.QtWidgets import QApplication, QPushButton


PRIMARY_BUTTON = "primary"
SECONDARY_BUTTON = "secondary"
DANGER_BUTTON = "danger"
SUBTLE_BUTTON = "subtle"


def mark_button(button: QPushButton, role: str = SECONDARY_BUTTON) -> QPushButton:
    button.setProperty("buttonRole", role)
    return button


def apply_app_theme(app: QApplication) -> None:
    if app.property("poursendThemeApplied"):
        return
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setProperty("poursendThemeApplied", True)


STYLESHEET = """
* {
    font-family: "Segoe UI Variable", "Segoe UI", Arial, sans-serif;
    font-size: 10.5pt;
    color: #1f2937;
}

QMainWindow, QDialog {
    background: #f3f7fc;
}

QWidget#AppRoot {
    background: #f3f7fc;
}

QFrame#Header,
QFrame#Sidebar,
QFrame#Workspace,
QFrame#BulkBar,
QFrame#DialogSurface {
    background: #ffffff;
    border: 1px solid #dce6f2;
    border-radius: 16px;
}

QFrame#Header {
    background: #f1f7ff;
    border-radius: 0;
    border-left: 0;
    border-right: 0;
    border-top: 0;
}

QLabel#AppTitle {
    font-size: 20pt;
    font-weight: 700;
    color: #17233b;
}

QLabel#AppIcon {
    background: #3b7cf4;
    color: #ffffff;
    font-size: 27pt;
    font-weight: 750;
    border-radius: 13px;
}

QLabel#MutedText,
QLabel#EmptySubtitle {
    color: #74819a;
    font-size: 10pt;
}

QLabel#AppSubtitle {
    color: #74819a;
    font-size: 9pt;
}

QLabel#SectionTitle,
QLabel#WorkspaceTitle {
    font-size: 14pt;
    font-weight: 700;
    color: #17233b;
}

QLabel#EmptyTitle {
    font-size: 15pt;
    font-weight: 650;
    color: #1f2937;
}

QLabel#BulkCount {
    font-weight: 650;
    color: #17233b;
}

QLabel#CountBadge,
QLabel#GroupCountBadge {
    padding: 2px 8px;
    border: 1px solid #dde8f6;
    border-radius: 11px;
    background: #f1f6ff;
    color: #5e6b84;
    font-size: 9.5pt;
}

QLabel#GroupIcon {
    background: transparent;
}

QLabel#GroupName {
    color: #34425c;
    font-size: 10.5pt;
}

QLabel#GroupTag {
    padding: 3px 8px;
    border: 0;
    border-radius: 7px;
    background: #f1f5fa;
    color: #52617a;
    font-size: 9.5pt;
}

QLabel#GroupTag[groupName="Female Mandarin"] {
    background: #fff0f2;
    color: #b94756;
}

QLabel#GroupTag[groupName="Male Cantonese"] {
    background: #eaf3ff;
    color: #2f6fe3;
}

QLabel#GroupTag[groupName="Follow Up"] {
    background: #fff7e9;
    color: #a66a18;
}

QLabel#StatusBadge {
    padding: 3px 9px;
    border: 0;
    border-radius: 7px;
    background: #eaf7ee;
    color: #25814a;
    font-weight: 600;
    font-size: 9.5pt;
}

QLineEdit, QTextEdit, QComboBox, QListWidget, QTableWidget {
    background: #ffffff;
    border: 1px solid #e7ecf4;
    border-radius: 9px;
    selection-background-color: #eaf3ff;
    selection-color: #1f2937;
}

QLineEdit {
    min-height: 48px;
    padding: 0 16px;
    border-radius: 10px;
}

QTextEdit {
    padding: 7px;
}

QComboBox {
    min-height: 46px;
    padding: 4px 34px 4px 14px;
    border-radius: 9px;
}

QComboBox::drop-down {
    border: 0;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QListWidget:focus, QTableWidget:focus {
    border: 1px solid #4f8ef7;
}

QPushButton {
    min-height: 42px;
    padding: 4px 14px;
    border-radius: 10px;
    border: 1px solid #d8e0ec;
    background: #ffffff;
    color: #1f2937;
}

QPushButton:hover {
    background: #edf5ff;
    border-color: #c9d8f0;
}

QPushButton:pressed {
    background: #eaf3ff;
}

QPushButton:disabled {
    background: #f4f7fb;
    color: #9ca3af;
    border-color: #e7ecf4;
}

QPushButton[buttonRole="primary"] {
    background: #3b7cf4;
    border-color: #3b7cf4;
    color: #ffffff;
    font-weight: 600;
    min-height: 48px;
    padding-left: 18px;
    padding-right: 18px;
}

QPushButton[buttonRole="primary"]:hover {
    background: #2f6fe3;
    border-color: #2f6fe3;
}

QPushButton[buttonRole="danger"] {
    color: #b43d3d;
    border-color: #f4dddd;
    background: #fff8f8;
}

QPushButton[buttonRole="danger"]:hover {
    background: #fff0f0;
    border-color: #e45a5a;
}

QPushButton[buttonRole="subtle"] {
    border-color: #e7edf6;
    background: #f8fbff;
    color: #2d3a52;
}

QPushButton[buttonRole="subtle"]:hover {
    background: #edf5ff;
    border-color: #e7ecf4;
}

QPushButton#IconButton {
    min-height: 0;
    min-width: 0;
    padding: 0;
    border-radius: 17px;
    font-size: 15pt;
    font-weight: 500;
}

QListWidget {
    background: #fbfcfe;
    border: 0;
    outline: 0;
    padding: 4px 3px;
}

QListWidget::item {
    min-height: 50px;
    padding: 0;
    border-radius: 12px;
}

QListWidget::item:hover {
    background: #edf5ff;
}

QListWidget::item:selected {
    background: #eaf3ff;
    color: #1f2937;
}

QTableWidget {
    gridline-color: #e7ecf4;
    border: 1px solid #dce6f2;
    border-radius: 12px;
    background: #ffffff;
    alternate-background-color: #ffffff;
}

QTableWidget::item {
    padding: 8px 12px;
    border: 0;
}

QTableWidget::item:selected {
    background: #eaf3ff;
    color: #1f2937;
}

QHeaderView::section {
    background: #f3f7fc;
    color: #65728a;
    font-weight: 600;
    border: 0;
    border-bottom: 1px solid #e7ecf4;
    padding: 11px 12px;
}

QMenu {
    background: #ffffff;
    border: 1px solid #e7ecf4;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 7px 24px;
    border-radius: 5px;
}

QMenu::item:selected {
    background: #eaf3ff;
}

QDialogButtonBox QPushButton {
    min-width: 88px;
}
"""

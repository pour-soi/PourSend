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
    font-size: 10pt;
    color: #1f2937;
}

QMainWindow, QDialog {
    background: #f3f4f6;
}

QWidget#AppRoot {
    background: #f3f4f6;
}

QFrame#Header,
QFrame#Sidebar,
QFrame#Workspace,
QFrame#BulkBar,
QFrame#DialogSurface {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}

QFrame#Header {
    border-radius: 0;
    border-left: 0;
    border-right: 0;
    border-top: 0;
}

QLabel#AppTitle {
    font-size: 18pt;
    font-weight: 650;
    color: #111827;
}

QLabel#AppSubtitle,
QLabel#MutedText,
QLabel#WorkspaceMeta,
QLabel#EmptySubtitle {
    color: #6b7280;
}

QLabel#SectionTitle,
QLabel#WorkspaceTitle {
    font-size: 13pt;
    font-weight: 650;
    color: #111827;
}

QLabel#EmptyTitle {
    font-size: 15pt;
    font-weight: 650;
    color: #111827;
}

QLabel#BulkCount {
    font-weight: 650;
    color: #111827;
}

QLineEdit, QTextEdit, QComboBox, QListWidget, QTableWidget {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 7px;
    selection-background-color: #dbeafe;
    selection-color: #111827;
}

QLineEdit {
    min-height: 34px;
    padding: 0 10px;
}

QTextEdit {
    padding: 7px;
}

QComboBox {
    min-height: 32px;
    padding: 3px 28px 3px 10px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QListWidget:focus, QTableWidget:focus {
    border: 1px solid #2563eb;
}

QPushButton {
    min-height: 32px;
    padding: 5px 12px;
    border-radius: 7px;
    border: 1px solid #d1d5db;
    background: #ffffff;
    color: #1f2937;
}

QPushButton:hover {
    background: #f9fafb;
    border-color: #9ca3af;
}

QPushButton:pressed {
    background: #eef2ff;
}

QPushButton:disabled {
    background: #f3f4f6;
    color: #9ca3af;
    border-color: #e5e7eb;
}

QPushButton[buttonRole="primary"] {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}

QPushButton[buttonRole="primary"]:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
}

QPushButton[buttonRole="danger"] {
    color: #991b1b;
    border-color: #fecaca;
    background: #fff7f7;
}

QPushButton[buttonRole="danger"]:hover {
    background: #fee2e2;
}

QPushButton[buttonRole="subtle"] {
    border-color: transparent;
    background: transparent;
    color: #374151;
}

QPushButton[buttonRole="subtle"]:hover {
    background: #f3f4f6;
    border-color: #e5e7eb;
}

QListWidget {
    border: 0;
    outline: 0;
    padding: 4px;
}

QListWidget::item {
    min-height: 32px;
    padding: 5px 8px;
    border-radius: 6px;
}

QListWidget::item:hover {
    background: #f3f4f6;
}

QListWidget::item:selected {
    background: #dbeafe;
    color: #1e3a8a;
}

QTableWidget {
    gridline-color: #edf0f3;
    border: 0;
    border-radius: 0;
    alternate-background-color: #fbfdff;
}

QTableWidget::item {
    padding: 7px;
    border-bottom: 1px solid #edf0f3;
}

QTableWidget::item:selected {
    background: #eef2ff;
    color: #111827;
}

QHeaderView::section {
    background: #f9fafb;
    color: #4b5563;
    font-weight: 600;
    border: 0;
    border-bottom: 1px solid #e5e7eb;
    padding: 8px;
}

QMenu {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 7px;
    padding: 4px;
}

QMenu::item {
    padding: 7px 24px;
    border-radius: 5px;
}

QMenu::item:selected {
    background: #eef2ff;
}

QDialogButtonBox QPushButton {
    min-width: 88px;
}
"""

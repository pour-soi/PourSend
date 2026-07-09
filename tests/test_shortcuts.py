import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPlainTextEdit, QTextEdit

from app.main import editable_text_widget_has_focus


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


class ShortcutSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app()

    def test_editable_line_edit_keeps_normal_text_shortcuts(self):
        widget = QLineEdit()

        self.assertTrue(editable_text_widget_has_focus(widget))

    def test_read_only_line_edit_allows_application_shortcuts(self):
        widget = QLineEdit()
        widget.setReadOnly(True)

        self.assertFalse(editable_text_widget_has_focus(widget))

    def test_editable_multiline_widgets_keep_normal_text_shortcuts(self):
        self.assertTrue(editable_text_widget_has_focus(QTextEdit()))
        self.assertTrue(editable_text_widget_has_focus(QPlainTextEdit()))

    def test_non_text_widgets_allow_application_shortcuts(self):
        self.assertFalse(editable_text_widget_has_focus(QLabel("Recipients")))


if __name__ == "__main__":
    unittest.main()

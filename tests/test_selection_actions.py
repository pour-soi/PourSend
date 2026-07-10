import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from app.main import MainWindow
from core.groups import DEFAULT_GROUP, checked_recipient_indexes


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def recipient(phone: str, group: str = DEFAULT_GROUP, selected: bool = False) -> dict:
    return {"phone": phone, "group": group, "groups": [group], "notes": "", "selected": selected}


class SelectionActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app()

    def make_window(self) -> MainWindow:
        with patch("app.main.load_recipient_data", return_value=([], [DEFAULT_GROUP], {}, None)):
            window = MainWindow()
        window.recipients = [
            recipient("+14151111111", "Caregivers"),
            recipient("+16282222222", "Caregivers"),
            recipient("+17073333333", "Follow-up"),
        ]
        window.groups = [DEFAULT_GROUP, "Caregivers", "Follow-up"]
        window.settings = {}
        window.save_and_update = lambda selected_group=None: (
            window.refresh_group_list(selected_group),
            window.refresh_table(),
        )
        window.refresh_group_list()
        window.refresh_table()
        return window

    def test_delete_uses_checked_rows_without_highlighted_row(self):
        window = self.make_window()
        self.addCleanup(window.close)
        window.recipients[0]["selected"] = True
        window.recipients[2]["selected"] = True
        window.refresh_table()
        window.table.clearSelection()

        with patch("app.main.QMessageBox.question", return_value=QMessageBox.Yes) as question:
            window.delete_selected()

        question.assert_called_once()
        self.assertEqual(question.call_args.args[2], "Delete 2 recipients?")
        self.assertEqual([recipient["phone"] for recipient in window.recipients], ["+16282222222"])
        self.assertEqual(checked_recipient_indexes(window.recipients), [])

    def test_delete_ignores_highlighted_unchecked_rows(self):
        window = self.make_window()
        self.addCleanup(window.close)
        window.table.selectRow(0)

        with patch("app.main.QMessageBox.information") as information, patch("app.main.QMessageBox.question") as question:
            window.delete_selected()

        information.assert_called_once()
        self.assertEqual(information.call_args.args[2], "No recipients are checked. Select one or more recipients in the Select column, then try again.")
        question.assert_not_called()
        self.assertEqual([recipient["phone"] for recipient in window.recipients], ["+14151111111", "+16282222222", "+17073333333"])


if __name__ == "__main__":
    unittest.main()

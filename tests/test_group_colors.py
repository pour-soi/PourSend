import os
import unittest
from copy import deepcopy
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox

from app.dialogs import GroupColorDialog
from app.main import MainWindow
from app.storage import make_saved_data, parse_saved_settings
from core.groups import (
    ALL_RECIPIENTS,
    ALL_RECIPIENTS_COLOR,
    DEFAULT_GROUP,
    DEFAULT_GROUP_COLOR,
    GROUP_COLOR_PALETTE,
    delete_group_color,
    ensure_group_colors,
    rename_group_color,
)


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


class GroupColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app()

    def setUp(self):
        save_patcher = patch("app.main.save_recipient_data", return_value=None)
        save_patcher.start()
        self.addCleanup(save_patcher.stop)

    def make_window(self, groups=None, settings=None, recipients=None) -> MainWindow:
        groups = groups or [DEFAULT_GROUP, "Friends", "Work"]
        with patch("app.main.load_recipient_data", return_value=(recipients or [], groups, settings or {}, None)):
            window = MainWindow()
        self.addCleanup(self.close_window, window)
        return window

    def close_window(self, window: MainWindow) -> None:
        self.app.removeEventFilter(window)
        window.close()

    def select_group(self, window: MainWindow, group: str) -> None:
        for row in range(window.group_list.count()):
            if window.group_list.item(row).data(Qt.UserRole) == group:
                window.group_list.setCurrentRow(row)
                return
        raise AssertionError(f"group not found: {group}")

    def test_legacy_settings_assign_colors_to_existing_groups(self):
        window = self.make_window(settings={"phone_format": "e164"})

        self.assertEqual(list(window.group_colors), [DEFAULT_GROUP, "Friends", "Work"])
        self.assertEqual(window.group_colors[DEFAULT_GROUP], DEFAULT_GROUP_COLOR)
        self.assertEqual(list(window.group_colors.values())[1:], list(GROUP_COLOR_PALETTE[:2]))
        self.assertEqual(len(window.settings["group_colors"]), len(window.group_colors))
        self.assertTrue(all(group_id.count("-") == 4 for group_id in window.settings["group_colors"]))

    def test_new_group_receives_next_available_color(self):
        window = self.make_window(groups=[DEFAULT_GROUP])

        with patch("app.main.GroupNameDialog") as dialog:
            dialog.Accepted = QDialog.Accepted
            dialog.return_value.exec.return_value = QDialog.Accepted
            dialog.return_value.group_name.return_value = "Friends"
            window.create_group()

        self.assertEqual(window.group_colors["Friends"], GROUP_COLOR_PALETTE[0])

    def test_group_colors_persist_through_saved_settings_and_restart(self):
        window = self.make_window()
        saved = make_saved_data([], window.groups, window.settings)
        reloaded_settings = parse_saved_settings(saved)
        reloaded = self.make_window(groups=window.groups, settings=reloaded_settings)

        self.assertEqual(reloaded.group_colors, window.group_colors)

    def test_rename_preserves_color_and_group_selection(self):
        settings = {
            "group_colors": {DEFAULT_GROUP: GROUP_COLOR_PALETTE[0], "Friends": GROUP_COLOR_PALETTE[3]},
            "group_selections": {"Friends": ["+14151111111"]},
        }
        recipients = [{"phone": "+14151111111", "groups": ["Friends"], "selected": False, "notes": ""}]
        window = self.make_window(groups=[DEFAULT_GROUP, "Friends"], settings=settings, recipients=recipients)
        self.select_group(window, "Friends")

        with patch("app.main.GroupNameDialog") as dialog:
            dialog.Accepted = QDialog.Accepted
            dialog.return_value.exec.return_value = QDialog.Accepted
            dialog.return_value.group_name.return_value = "Family"
            window.rename_group()

        self.assertNotIn("Friends", window.group_colors)
        self.assertEqual(window.group_colors["Family"], GROUP_COLOR_PALETTE[3])
        self.assertNotIn("Friends", window.group_selections)
        self.assertEqual(window.group_selections["Family"], {"+14151111111"})

    def test_delete_removes_color_and_group_selection(self):
        settings = {
            "group_colors": {DEFAULT_GROUP: GROUP_COLOR_PALETTE[0], "Friends": GROUP_COLOR_PALETTE[2]},
            "group_selections": {"Friends": ["+14151111111"]},
        }
        recipients = [{"phone": "+14151111111", "groups": ["Friends"], "selected": False, "notes": ""}]
        window = self.make_window(groups=[DEFAULT_GROUP, "Friends"], settings=settings, recipients=recipients)
        self.select_group(window, "Friends")

        with patch("app.main.QMessageBox.question", return_value=QMessageBox.Yes):
            window.delete_group()

        self.assertNotIn("Friends", window.group_colors)
        self.assertNotIn("Friends", window.settings["group_colors"])
        self.assertNotIn("Friends", window.group_selections)

    def test_palette_reuses_colors_in_order_after_all_are_used(self):
        groups = [f"Group {index}" for index in range(len(GROUP_COLOR_PALETTE) + 2)]

        colors = ensure_group_colors(groups)

        self.assertEqual(colors[groups[-2]], GROUP_COLOR_PALETTE[0])
        self.assertEqual(colors[groups[-1]], GROUP_COLOR_PALETTE[1])

    def test_deleted_color_becomes_next_available(self):
        colors = ensure_group_colors(["Friends", "Family", "Work"])
        delete_group_color(colors, "Family")

        reassigned = ensure_group_colors(["Friends", "Work", "VIP"], colors)

        self.assertEqual(reassigned["VIP"], GROUP_COLOR_PALETTE[1])

    def test_all_recipients_uses_independent_neutral_color(self):
        window = self.make_window(groups=[DEFAULT_GROUP])

        self.assertEqual(window.group_color(ALL_RECIPIENTS), ALL_RECIPIENTS_COLOR)
        self.assertNotIn(ALL_RECIPIENTS, window.group_colors)

    def test_group_row_colors_icon_and_name_without_color_dot(self):
        window = self.make_window(groups=[DEFAULT_GROUP, "Friends"])
        self.select_group(window, "Friends")
        item = window.group_list.currentItem()
        row = window.group_list.itemWidget(item)
        icon = row.findChild(QLabel, "GroupIcon")
        name = row.findChild(QLabel, "GroupName")

        self.assertIsNone(row.findChild(QLabel, "GroupColorDot"))
        self.assertEqual(icon.property("groupColor"), name.property("groupColor"))
        self.assertIn(name.property("groupColor"), name.styleSheet())
        self.assertTrue(row.active)
        self.assertEqual(row.color.name(), window.group_color("Friends"))

    def test_color_helpers_preserve_and_remove_entries(self):
        colors = {"Friends": GROUP_COLOR_PALETTE[4]}

        rename_group_color(colors, "Friends", "Family")
        self.assertEqual(colors, {"Family": GROUP_COLOR_PALETTE[4]})
        delete_group_color(colors, "Family")
        self.assertEqual(colors, {})

    def test_manual_color_change_preserves_active_group_search_recipients_and_selections(self):
        settings = {"group_selections": {"Friends": ["+14151111111"]}}
        recipients = [{"phone": "+14151111111", "groups": ["Friends"], "selected": False, "notes": ""}]
        window = self.make_window(groups=[DEFAULT_GROUP, "Friends"], settings=settings, recipients=recipients)
        self.select_group(window, "Friends")
        window.search.setText("415")
        window.table.selectRow(0)
        before_recipients = deepcopy(window.recipients)
        before_selections = deepcopy(window.settings["group_selections"])

        with patch("app.main.GroupColorDialog") as dialog:
            dialog.Accepted = QDialog.Accepted
            dialog.return_value.exec.return_value = QDialog.Accepted
            dialog.return_value.selected_color.return_value = GROUP_COLOR_PALETTE[5]
            window.change_group_color()

        self.assertEqual(window.group_colors["Friends"], GROUP_COLOR_PALETTE[5])
        self.assertEqual(window.current_group_filter(), "Friends")
        self.assertEqual(window.search.text(), "415")
        self.assertEqual(window.selected_visible_index(), 0)
        self.assertEqual(window.recipients, before_recipients)
        self.assertEqual(window.settings["group_selections"], before_selections)
        active_row = window.group_list.itemWidget(window.group_list.currentItem())
        icon = active_row.findChild(QLabel, "GroupIcon")
        name = active_row.findChild(QLabel, "GroupName")
        self.assertEqual(active_row.color.name(), GROUP_COLOR_PALETTE[5])
        self.assertEqual(icon.property("groupColor"), name.property("groupColor"))

    def test_manual_color_persists_after_save_and_reload(self):
        window = self.make_window(groups=[DEFAULT_GROUP, "Friends"])
        self.select_group(window, "Friends")
        with patch("app.main.GroupColorDialog") as dialog:
            dialog.Accepted = QDialog.Accepted
            dialog.return_value.exec.return_value = QDialog.Accepted
            dialog.return_value.selected_color.return_value = GROUP_COLOR_PALETTE[6]
            window.change_group_color()

        saved = make_saved_data([], window.groups, window.settings)
        reloaded = self.make_window(groups=window.groups, settings=parse_saved_settings(saved))

        self.assertEqual(reloaded.group_colors["Friends"], GROUP_COLOR_PALETTE[6])

    def test_multiple_groups_can_use_same_manual_color(self):
        window = self.make_window(groups=[DEFAULT_GROUP, "Friends", "Work"])

        for group in ("Friends", "Work"):
            with patch("app.main.GroupColorDialog") as dialog:
                dialog.Accepted = QDialog.Accepted
                dialog.return_value.exec.return_value = QDialog.Accepted
                dialog.return_value.selected_color.return_value = GROUP_COLOR_PALETTE[7]
                window.change_group_color(group)

        self.assertEqual(window.group_colors["Friends"], GROUP_COLOR_PALETTE[7])
        self.assertEqual(window.group_colors["Work"], GROUP_COLOR_PALETTE[7])

    def test_manual_color_survives_rename_and_is_removed_on_delete(self):
        window = self.make_window(groups=[DEFAULT_GROUP, "Friends"])
        self.select_group(window, "Friends")
        with patch("app.main.GroupColorDialog") as dialog:
            dialog.Accepted = QDialog.Accepted
            dialog.return_value.exec.return_value = QDialog.Accepted
            dialog.return_value.selected_color.return_value = GROUP_COLOR_PALETTE[4]
            window.change_group_color()
        with patch("app.main.GroupNameDialog") as dialog:
            dialog.Accepted = QDialog.Accepted
            dialog.return_value.exec.return_value = QDialog.Accepted
            dialog.return_value.group_name.return_value = "Family"
            window.rename_group()

        self.assertEqual(window.group_colors["Family"], GROUP_COLOR_PALETTE[4])
        with patch("app.main.QMessageBox.question", return_value=QMessageBox.Yes):
            window.delete_group()
        self.assertNotIn("Family", window.group_colors)

    def test_all_recipients_and_default_cannot_open_color_chooser(self):
        window = self.make_window(groups=[DEFAULT_GROUP, "Friends"])

        with patch("app.main.GroupColorDialog") as dialog:
            window.change_group_color(ALL_RECIPIENTS)
            window.change_group_color(DEFAULT_GROUP)

        dialog.assert_not_called()
        self.assertFalse(window.change_group_color_button.isVisible())

    def test_color_action_visibility_follows_user_created_group(self):
        window = self.make_window(groups=[DEFAULT_GROUP, "Friends"])
        window.show()
        self.app.processEvents()
        self.assertFalse(window.change_group_color_button.isVisible())

        self.select_group(window, "Friends")
        self.app.processEvents()
        self.assertTrue(window.change_group_color_button.isVisible())

    def test_color_dialog_marks_current_color_and_supports_keyboard_cancel(self):
        dialog = GroupColorDialog(None, GROUP_COLOR_PALETTE[2])
        self.addCleanup(dialog.close)
        dialog.show()
        self.app.processEvents()

        self.assertTrue(dialog.swatches[2].isChecked())
        self.assertEqual(dialog.swatches[2].text(), "✓")
        QTest.keyClick(dialog.swatches[2], Qt.Key_Right)
        self.assertTrue(dialog.swatches[3].hasFocus())
        QTest.keyClick(dialog, Qt.Key_Escape)

        self.assertEqual(dialog.result(), QDialog.Rejected)
        self.assertIsNone(dialog.selected_color())

    def test_color_dialog_selects_palette_color_and_closes(self):
        dialog = GroupColorDialog(None, GROUP_COLOR_PALETTE[0])
        self.addCleanup(dialog.close)
        dialog.show()
        self.app.processEvents()

        dialog.swatches[5].click()

        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.selected_color(), GROUP_COLOR_PALETTE[5])


if __name__ == "__main__":
    unittest.main()

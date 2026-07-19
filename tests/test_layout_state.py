import os
import unittest
from typing import Optional
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy, QWidget

from app.main import LayoutMetrics, MainWindow
from core.groups import DEFAULT_GROUP


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def recipient(phone: str, selected: bool = False) -> dict:
    return {"phone": phone, "groups": [DEFAULT_GROUP], "notes": "", "selected": selected}


def settle_layout(window: MainWindow, app: QApplication) -> None:
    for _ in range(8):
        app.processEvents()
    window.arrange_responsive_layout()
    window.arrange_filter_toolbar()
    window.resize_table_columns()
    for _ in range(4):
        app.processEvents()


def widget_is_inside_window(window: MainWindow, widget: QWidget) -> bool:
    top_left = widget.mapTo(window, widget.rect().topLeft())
    return window.rect().contains(QRect(top_left, widget.size()))


class LayoutStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app()

    def make_window(self, recipients: Optional[list[dict]] = None, settings: Optional[dict] = None) -> MainWindow:
        with (
            patch("app.main.load_recipient_data", return_value=([], [DEFAULT_GROUP], settings or {}, None)),
            patch("app.main.save_recipient_data", return_value=None),
        ):
            window = MainWindow()
        window.recipients = recipients or []
        window.groups = [DEFAULT_GROUP]
        window.group_selections = window.load_group_selections()
        window.refresh_group_list()
        window.refresh_table()
        return window

    def test_empty_database_shows_centered_empty_state_actions(self):
        window = self.make_window([])
        self.addCleanup(window.close)

        self.assertIs(window.table_stack.currentWidget(), window.empty_state)
        self.assertFalse(window.empty_actions.isHidden())
        self.assertTrue(window.action_bar.isHidden())

    def test_brand_logo_loads_in_header(self):
        window = self.make_window([])
        self.addCleanup(window.close)

        app_icon = window.findChild(QLabel, "AppIcon")
        self.assertIsNotNone(app_icon)
        self.assertIsNotNone(app_icon.pixmap())
        self.assertFalse(app_icon.pixmap().isNull())

    def test_brand_logo_uses_bounded_proportional_display_size_without_scaled_contents(self):
        window = self.make_window([])
        self.addCleanup(window.close)

        app_icon = window.findChild(QLabel, "AppIcon")
        brand = window.findChild(QWidget, "BrandLockup")

        self.assertIsNotNone(app_icon)
        self.assertIsNotNone(brand)
        self.assertGreaterEqual(app_icon.size().width(), LayoutMetrics.LOGO_MIN_SIZE)
        self.assertLessEqual(app_icon.size().width(), LayoutMetrics.LOGO_SIZE)
        self.assertEqual(app_icon.size().width(), app_icon.size().height())
        self.assertEqual(app_icon.pixmap().width(), app_icon.pixmap().height())
        self.assertFalse(app_icon.hasScaledContents())
        self.assertEqual(app_icon.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
        self.assertEqual(app_icon.sizePolicy().verticalPolicy(), QSizePolicy.Fixed)
        self.assertEqual(brand.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
        self.assertEqual(brand.sizePolicy().verticalPolicy(), QSizePolicy.Fixed)

    def test_brand_logo_resizes_proportionally_with_window_width(self):
        window = self.make_window([])
        self.addCleanup(window.close)
        app_icon = window.findChild(QLabel, "AppIcon")
        sizes = []

        for width, height in ((1400, 900), (1200, 800), (1000, 650), (900, 600), (720, 480)):
            window.resize(width, height)
            window.show()
            settle_layout(window, self.app)
            sizes.append(app_icon.size().width())

            self.assertEqual(app_icon.size().width(), app_icon.size().height())
            self.assertEqual(app_icon.pixmap().width(), app_icon.pixmap().height())

        self.assertEqual(sizes, sorted(sizes, reverse=True))
        self.assertEqual(sizes[0], LayoutMetrics.LOGO_SIZE)
        self.assertEqual(sizes[-1], LayoutMetrics.LOGO_MIN_SIZE)
        self.assertGreater(len(set(sizes)), 3)

    def test_populated_table_shows_recipient_action_access(self):
        window = self.make_window([recipient("+14151111111"), recipient("+16282222222")])
        self.addCleanup(window.close)
        window.resize(1200, 800)
        window.show()
        settle_layout(window, self.app)

        self.assertIs(window.table_stack.currentWidget(), window.table)
        self.assertLess(window.workspace_layout.indexOf(window.selection_actions), window.workspace_layout.indexOf(window.table_stack))
        self.assertTrue(window.action_bar.isHidden())
        self.assertTrue(window.bulk_actions.isHidden())
        self.assertNotEqual(window.selection_actions.isHidden(), window.recipient_actions_button.isHidden())
        self.assertTrue(window.select_all_button.isEnabled())
        self.assertFalse(window.deselect_all_button.isEnabled())
        self.assertFalse(window.edit_button.isEnabled())
        self.assertFalse(window.delete_recipient_button.isEnabled())

    def test_checked_recipient_enables_bulk_action_row(self):
        window = self.make_window([recipient("+14151111111", selected=True), recipient("+16282222222")])
        self.addCleanup(window.close)
        window.resize(1200, 800)
        window.show()
        settle_layout(window, self.app)

        if window.compact_recipient_actions:
            self.assertTrue(window.action_bar.isHidden())
            self.assertTrue(window.menu_delete_selected_action.isEnabled())
        else:
            self.assertFalse(window.action_bar.isHidden())
            self.assertFalse(window.bulk_actions.isHidden())
        self.assertEqual(window.bulk_count_label.text(), "1 recipient checked")
        self.assertIn("Add Checked to Group", [button.text() for button in window.bulk_action_buttons])
        self.assertIn("Remove Checked from Group", [button.text() for button in window.bulk_action_buttons])

    def test_search_empty_hides_database_empty_actions(self):
        window = self.make_window([recipient("+14151111111")])
        self.addCleanup(window.close)
        window.search.setText("no-match")
        window.refresh_table()

        self.assertIs(window.table_stack.currentWidget(), window.empty_state)
        self.assertTrue(window.empty_actions.isHidden())
        self.assertTrue(window.selection_actions.isHidden())
        self.assertTrue(window.recipient_actions_button.isHidden())
        self.assertTrue(window.action_bar.isHidden())

    def test_core_recipient_actions_remain_reachable_at_supported_sizes(self):
        window = self.make_window([recipient("+14151111111", selected=True), recipient("+16282222222")])
        self.addCleanup(window.close)
        expected_menu_actions = [
            "Edit Recipient",
            "Delete Recipient...",
            "Select All",
            "Clear Selection",
            "Copy Selected",
            "Add to Group",
            "Set Groups",
            "Remove from Group",
            "Delete Selected...",
        ]

        for width, height in ((1200, 800), (1000, 650), (900, 600), (800, 540), (720, 480), (360, 300)):
            with self.subTest(size=f"{width}x{height}"):
                window.resize(width, height)
                window.show()
                settle_layout(window, self.app)
                window.table.selectRow(0)
                self.app.processEvents()

                self.assertEqual(window.main_scroll_area.horizontalScrollBar().maximum(), 0)
                self.assertFalse(window.main_scroll_area.horizontalScrollBar().isVisible())
                if window.compact_recipient_actions:
                    self.assertTrue(window.recipient_actions_button.isVisible())
                    self.assertTrue(widget_is_inside_window(window, window.recipient_actions_button))
                    self.assertGreaterEqual(
                        window.recipient_actions_button.width(),
                        window.recipient_actions_button.minimumSizeHint().width(),
                    )
                    menu_actions = window.recipient_actions_menu.actions()
                    self.assertEqual([action.text() for action in menu_actions if not action.isSeparator()], expected_menu_actions)
                    self.assertEqual(sum(action.isSeparator() for action in menu_actions), 2)
                    heading_layout = window.workspace_layout.itemAt(0).layout()
                    self.assertIsNotNone(heading_layout)
                    self.assertGreaterEqual(heading_layout.indexOf(window.recipient_actions_button), 0)
                    self.assertTrue(window.selection_actions.isHidden())
                    self.assertTrue(window.action_bar.isHidden())
                else:
                    self.assertTrue(window.selection_actions.isVisible())
                    self.assertTrue(widget_is_inside_window(window, window.selection_actions))
                    for button in window.table_action_buttons:
                        self.assertGreater(button.width(), 0)
                        self.assertTrue(widget_is_inside_window(window, button))
                    self.assertTrue(window.action_bar.isVisible())
                    self.assertTrue(widget_is_inside_window(window, window.action_bar))
                    for button in window.bulk_action_buttons:
                        self.assertGreaterEqual(button.width(), button.minimumSizeHint().width())
                        self.assertTrue(widget_is_inside_window(window, button))
                    self.assertTrue(window.recipient_actions_button.isHidden())

    def test_resizing_wide_to_compact_and_back_preserves_action_access(self):
        window = self.make_window([recipient("+14151111111", selected=True), recipient("+16282222222")])
        self.addCleanup(window.close)

        window.resize(2400, 1000)
        window.show()
        settle_layout(window, self.app)
        self.assertFalse(window.compact_recipient_actions)
        self.assertTrue(window.selection_actions.isVisible())

        window.resize(720, 480)
        settle_layout(window, self.app)
        self.assertTrue(window.compact_recipient_actions)
        self.assertTrue(window.recipient_actions_button.isVisible())
        self.assertTrue(window.selection_actions.isHidden())

        window.resize(2400, 1000)
        settle_layout(window, self.app)
        self.assertFalse(window.compact_recipient_actions)
        self.assertTrue(window.selection_actions.isVisible())
        self.assertTrue(window.action_bar.isVisible())

    def test_menu_actions_use_the_same_handlers_as_direct_controls(self):
        window = self.make_window([recipient("+14151111111", selected=True), recipient("+16282222222")])
        self.addCleanup(window.close)
        window.table.selectRow(0)
        window.update_recipient_action_states()

        pairs = (
            (window.edit_button, window.menu_edit_action, "edit_selected"),
            (window.delete_recipient_button, window.menu_delete_recipient_action, "delete_highlighted_recipient"),
            (window.select_all_button, window.menu_select_all_action, "set_all_visible"),
            (window.deselect_all_button, window.menu_clear_selection_action, "set_all_visible"),
            (window.bulk_copy_button, window.menu_copy_checked_action, "copy_checked_recipients"),
            (window.bulk_add_button, window.menu_add_checked_action, "assign_checked_to_group"),
            (window.bulk_set_button, window.menu_set_groups_action, "batch_edit_checked"),
            (window.bulk_remove_button, window.menu_remove_checked_action, "remove_checked_from_current_group"),
            (window.bulk_delete_button, window.menu_delete_selected_action, "delete_selected"),
        )
        for button, action, handler_name in pairs:
            with self.subTest(action=action.text()), patch.object(window, handler_name) as handler:
                button.click()
                action.trigger()
                self.assertEqual(handler.call_count, 2)

    def test_filter_toolbar_uses_responsive_column_counts(self):
        window = self.make_window([recipient("+14151111111")])
        self.addCleanup(window.close)

        window.resize(1600, 900)
        window.arrange_filter_toolbar()
        self.assertEqual(window.filter_bar_columns, LayoutMetrics.FILTER_COLUMNS)

        window.resize(1280, 720)
        window.arrange_filter_toolbar()
        self.assertEqual(window.filter_bar_columns, LayoutMetrics.FILTER_COLUMNS)

    def test_main_window_has_small_safety_minimum_size(self):
        window = self.make_window([recipient("+14151111111")])
        self.addCleanup(window.close)

        self.assertLessEqual(window.minimumWidth(), 400)
        self.assertLessEqual(window.minimumHeight(), 320)

    def test_small_window_size_is_allowed(self):
        window = self.make_window([recipient("+14151111111")])
        self.addCleanup(window.close)

        window.resize(600, 400)
        self.app.processEvents()

        self.assertLessEqual(window.width(), 620)
        self.assertLessEqual(window.height(), 420)

    def test_small_window_uses_vertical_overflow_without_horizontal_scrolling(self):
        window = self.make_window([recipient("+14151111111")])
        self.addCleanup(window.close)

        window.resize(LayoutMetrics.MIN_WINDOW)
        window.show()
        self.app.processEvents()

        self.assertIs(window.centralWidget(), window.main_scroll_area)
        self.assertEqual(window.main_scroll_area.horizontalScrollBar().maximum(), 0)
        self.assertFalse(window.main_scroll_area.horizontalScrollBar().isVisible())
        self.assertGreater(window.main_scroll_area.verticalScrollBar().maximum(), 0)

    def test_practical_compact_widths_avoid_horizontal_scrolling(self):
        window = self.make_window([recipient("+14151111111"), recipient("+16282222222", selected=True)])
        self.addCleanup(window.close)

        for width, height in ((1100, 700), (1000, 650), (900, 600), (800, 540), (720, 480)):
            with self.subTest(size=f"{width}x{height}"):
                window.resize(width, height)
                window.show()
                settle_layout(window, self.app)

                hscroll = window.main_scroll_area.horizontalScrollBar().maximum()
                diagnostic = (
                    f"root={window.main_scroll_area.widget().minimumSizeHint().toTuple()} "
                    f"viewport={window.main_scroll_area.viewport().size().toTuple()} "
                    f"brand={window.brand.width()} sidebar={window.sidebar.width()} "
                    f"content={window.table_stack.width()} "
                    f"workspace_min={window.table_stack.parentWidget().minimumSizeHint().toTuple()} "
                    f"filter_min={window.filter_bar.minimumSize().toTuple()} "
                    f"filter_hint={window.filter_bar.sizeHint().toTuple()} "
                    f"table_min={window.table.minimumSizeHint().toTuple()} "
                    f"stack_min={window.table_stack.minimumSizeHint().toTuple()} "
                    f"action={window.action_bar.sizeHint().toTuple()}"
                )
                self.assertEqual(hscroll, 0, diagnostic)

    def test_sidebar_and_table_columns_resize_fluidly(self):
        window = self.make_window([recipient("+14151111111"), recipient("+16282222222", selected=True)])
        self.addCleanup(window.close)

        measurements = []
        for width, height in ((1100, 700), (1000, 650), (900, 600), (800, 540), (720, 480)):
            window.resize(width, height)
            window.show()
            settle_layout(window, self.app)
            sidebar = window.findChild(QWidget, "Sidebar")
            measurements.append((sidebar.width(), window.table_stack.width(), window.table.columnWidth(1)))

        sidebars = [measurement[0] for measurement in measurements]
        table_viewports = [measurement[1] for measurement in measurements]
        phone_columns = [measurement[2] for measurement in measurements]
        self.assertEqual(sidebars, sorted(sidebars, reverse=True))
        self.assertEqual(table_viewports, sorted(table_viewports, reverse=True))
        self.assertEqual(phone_columns, sorted(phone_columns, reverse=True))

    def test_large_fixed_child_constraints_do_not_reset_window_minimum(self):
        window = self.make_window([recipient("+14151111111")])
        self.addCleanup(window.close)

        self.assertNotEqual(window.minimumSize(), LayoutMetrics.DEFAULT_WINDOW)
        self.assertLess(window.minimumWidth(), 720)
        self.assertLess(window.minimumHeight(), 480)

    def test_window_geometry_restores_from_settings(self):
        settings = {"window_geometry": {"x": 20, "y": 30, "width": 720, "height": 480, "maximized": False}}
        window = self.make_window(settings=settings)
        self.addCleanup(window.close)

        self.assertEqual(window.geometry().size(), LayoutMetrics.MIN_WINDOW.expandedTo(window.geometry().size()))
        self.assertEqual(window.width(), 720)
        self.assertEqual(window.height(), 480)

    def test_offscreen_window_geometry_is_recentered(self):
        settings = {"window_geometry": {"x": -50000, "y": -50000, "width": 720, "height": 480, "maximized": False}}
        window = self.make_window(settings=settings)
        self.addCleanup(window.close)

        self.assertTrue(window.window_rect_intersects_visible_screen(window.geometry()))

    def test_window_geometry_is_saved_without_minimized_state(self):
        window = self.make_window([recipient("+14151111111")])
        self.addCleanup(window.close)
        window.setGeometry(QRect(25, 35, 720, 480))

        with patch("app.main.save_recipient_data", return_value=None) as save_data:
            window.save_window_geometry()

        saved_settings = save_data.call_args.args[2]
        self.assertEqual(saved_settings["window_geometry"]["width"], 720)
        self.assertEqual(saved_settings["window_geometry"]["height"], 480)
        self.assertIn("maximized", saved_settings["window_geometry"])
        self.assertNotIn("minimized", saved_settings["window_geometry"])


if __name__ == "__main__":
    unittest.main()

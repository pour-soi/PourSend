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

    def test_populated_table_shows_action_bar_without_bulk_actions_until_checked(self):
        window = self.make_window([recipient("+14151111111"), recipient("+16282222222")])
        self.addCleanup(window.close)

        self.assertIs(window.table_stack.currentWidget(), window.table)
        self.assertFalse(window.action_bar.isHidden())
        self.assertTrue(window.bulk_actions.isHidden())
        self.assertTrue(all(button.isEnabled() for button in window.table_action_buttons))

    def test_checked_recipient_enables_bulk_action_row(self):
        window = self.make_window([recipient("+14151111111", selected=True), recipient("+16282222222")])
        self.addCleanup(window.close)

        self.assertFalse(window.action_bar.isHidden())
        self.assertFalse(window.bulk_actions.isHidden())
        self.assertEqual(window.bulk_count_label.text(), "1 recipient checked")

    def test_search_empty_hides_database_empty_actions(self):
        window = self.make_window([recipient("+14151111111")])
        self.addCleanup(window.close)
        window.search.setText("no-match")
        window.refresh_table()

        self.assertIs(window.table_stack.currentWidget(), window.empty_state)
        self.assertTrue(window.empty_actions.isHidden())
        self.assertTrue(window.action_bar.isHidden())

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

    def test_small_window_overflow_uses_scroll_area(self):
        window = self.make_window([recipient("+14151111111")])
        self.addCleanup(window.close)

        window.resize(LayoutMetrics.MIN_WINDOW)
        window.show()
        self.app.processEvents()

        self.assertIs(window.centralWidget(), window.main_scroll_area)
        self.assertGreater(window.main_scroll_area.horizontalScrollBar().maximum(), 0)
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
                self.assertGreater(window.main_scroll_area.verticalScrollBar().maximum(), 0)

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

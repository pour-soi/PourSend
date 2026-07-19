import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.storage import APP_FOLDER, load_recipient_data, make_saved_data, parse_saved_settings


class StorageTests(unittest.TestCase):
    def test_primary_data_folder_uses_poursend_branding(self):
        self.assertEqual(APP_FOLDER, "poursend_data")

    def test_window_geometry_setting_round_trips(self):
        settings = {
            "phone_format": "dashes",
            "window_geometry": {"x": 10, "y": 20, "width": 720, "height": 480, "maximized": False},
        }

        saved = make_saved_data([], [], settings)
        parsed = parse_saved_settings(saved)

        self.assertEqual(parsed["window_geometry"], settings["window_geometry"])

    def test_invalid_window_geometry_setting_is_ignored(self):
        parsed = parse_saved_settings({"settings": {"phone_format": "dashes", "window_geometry": "not geometry"}})

        self.assertNotIn("window_geometry", parsed)

    def test_group_selections_round_trip_and_normalize_phone_identities(self):
        settings = {
            "group_selections": {
                "Caregivers": ["(415) 111-1111", "+14151111111", "+16282222222"],
                "Follow-up": ["+17073333333"],
            }
        }

        saved = make_saved_data([], ["Caregivers", "Follow-up"], settings)
        parsed = parse_saved_settings(saved)

        self.assertEqual(
            parsed["group_selections"],
            {
                "Caregivers": ["+14151111111", "+16282222222"],
                "Follow-up": ["+17073333333"],
            },
        )

    def test_invalid_group_selection_settings_are_ignored(self):
        parsed = parse_saved_settings({"settings": {"group_selections": ["not", "a", "mapping"]}})

        self.assertNotIn("group_selections", parsed)

    def test_missing_data_file_is_created_with_empty_database(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / APP_FOLDER / "recipients.json"
            path.parent.mkdir()

            with patch("app.storage.data_path", return_value=path):
                recipients, groups, settings, error = load_recipient_data()

            self.assertIsNone(error)
            self.assertEqual(recipients, [])
            self.assertIn("Default", groups)
            self.assertEqual(settings["phone_format"], "e164")
            self.assertTrue(path.exists())

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["recipients"], [])
            self.assertEqual(saved["settings"]["phone_format"], "e164")


if __name__ == "__main__":
    unittest.main()

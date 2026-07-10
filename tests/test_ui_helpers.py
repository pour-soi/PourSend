import unittest

from app.ui_helpers import checked_status_text, empty_state_message, group_display_text, group_recipient_count, workspace_title
from core.groups import ALL_RECIPIENTS, DEFAULT_GROUP


class UiHelperTests(unittest.TestCase):
    def test_group_display_uses_compact_delimiter(self):
        self.assertEqual(group_display_text(["Female Mandarin", "Follow Up"]), "Female Mandarin · Follow Up")

    def test_checked_status_text_handles_singular_and_plural(self):
        self.assertEqual(checked_status_text(1), "1 recipient checked")
        self.assertEqual(checked_status_text(4), "4 recipients checked")

    def test_group_counts_use_membership_and_deduplicate_all(self):
        recipients = [
            {"phone": "+14151111111", "groups": ["Female Mandarin", "Follow Up"]},
            {"phone": "415-111-1111", "groups": ["Follow Up"]},
            {"phone": "+16282222222", "group": DEFAULT_GROUP},
        ]

        self.assertEqual(group_recipient_count(recipients, ALL_RECIPIENTS), 2)
        self.assertEqual(group_recipient_count(recipients, "Follow Up"), 1)

    def test_workspace_title_and_empty_state_copy(self):
        self.assertEqual(workspace_title(ALL_RECIPIENTS), "All Recipients")
        self.assertEqual(workspace_title("Follow Up"), "Follow Up")
        self.assertEqual(empty_state_message("amy"), ("No recipients found", "Try changing your search."))
        self.assertEqual(
            empty_state_message(""),
            ("No recipients found", "Try changing your search or add a new recipient."),
        )


if __name__ == "__main__":
    unittest.main()

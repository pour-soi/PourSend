import unittest

from app.storage import make_saved_data, parse_saved_data
from core.importing import preview_pasted_recipients, rows_to_add


def raw_phone(area: str = "415", exchange: str = "123", line: str = "4567", separator: str = "-") -> str:
    return separator.join([area, exchange, line])


def normalized(area: str = "415", exchange: str = "123", line: str = "4567") -> str:
    return "+1" + area + exchange + line


class BatchPasteTests(unittest.TestCase):
    def test_multiple_phone_numbers_one_per_line(self):
        rows = preview_pasted_recipients(f"{raw_phone()}\n{raw_phone('628')}")

        self.assertEqual([row.phone for row in rows], [raw_phone(), raw_phone("628")])
        self.assertEqual([row.name for row in rows], ["None", "None"])
        self.assertEqual([row.status for row in rows], ["Valid", "Valid"])

    def test_comma_separated_phone_numbers(self):
        rows = preview_pasted_recipients(f"{raw_phone()}, {raw_phone('628')}")

        self.assertEqual([row.normalized for row in rows], [normalized(), normalized("628")])

    def test_semicolon_separated_phone_numbers(self):
        rows = preview_pasted_recipients(f"{raw_phone()}; {raw_phone('628')}")

        self.assertEqual([row.normalized for row in rows], [normalized(), normalized("628")])

    def test_spreadsheet_style_pasted_rows(self):
        rows = preview_pasted_recipients(f"Amy\t{raw_phone()}\nJohn\t{raw_phone('628')}")

        self.assertEqual([(row.name, row.phone, row.status) for row in rows], [
            ("Amy", raw_phone(), "Valid"),
            ("John", raw_phone("628"), "Valid"),
        ])

    def test_phone_numbers_containing_spaces_are_not_split(self):
        rows = preview_pasted_recipients(raw_phone(separator=" "))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].normalized, normalized())

    def test_default_name_is_none_and_every_number_becomes_separate_recipient(self):
        rows = preview_pasted_recipients(f"{raw_phone()}\n{raw_phone('628')}")
        recipients = rows_to_add(rows)

        self.assertEqual([recipient["name"] for recipient in recipients], ["None", "None"])
        self.assertEqual([recipient["phone"] for recipient in recipients], [raw_phone(), raw_phone("628")])

    def test_duplicate_inside_same_batch_is_skipped(self):
        rows = preview_pasted_recipients(f"{raw_phone()}\n{normalized()}")
        recipients = rows_to_add(rows)

        self.assertEqual([row.status for row in rows], ["Valid", "Duplicate in this batch"])
        self.assertEqual(len(recipients), 1)

    def test_already_existing_recipient_is_detected(self):
        rows = preview_pasted_recipients(raw_phone(), {normalized()})

        self.assertEqual(rows[0].status, "Already exists")
        self.assertEqual(rows_to_add(rows), [])

    def test_invalid_number_is_skipped(self):
        rows = preview_pasted_recipients("123")

        self.assertEqual(rows[0].status, "Invalid")
        self.assertEqual(rows_to_add(rows), [])

    def test_optional_group_assignment(self):
        rows = preview_pasted_recipients(raw_phone())
        recipients = rows_to_add(rows, ["Caregivers"])

        self.assertEqual(recipients[0]["groups"], ["Caregivers"])

    def test_assignment_to_multiple_groups(self):
        rows = preview_pasted_recipients(raw_phone())
        recipients = rows_to_add(rows, ["Caregivers", "Follow-up"])

        self.assertEqual(recipients[0]["groups"], ["Caregivers", "Follow-up"])

    def test_existing_recipient_groups_remain_unchanged_when_number_already_exists(self):
        existing = [{"name": "Amy", "phone": raw_phone(), "selected": False, "groups": ["Caregivers"]}]
        rows = preview_pasted_recipients(raw_phone(), {normalized()})
        existing.extend(rows_to_add(rows, ["Follow-up"]))

        self.assertEqual(existing, [
            {"name": "Amy", "phone": raw_phone(), "selected": False, "groups": ["Caregivers"]}
        ])

    def test_persistence_after_batch_import(self):
        rows = preview_pasted_recipients(f"{raw_phone()}\n{raw_phone('628')}")
        recipients = rows_to_add(rows, ["Caregivers"])
        saved = make_saved_data(recipients, ["Caregivers"])

        restored_recipients, restored_groups = parse_saved_data(saved)

        self.assertEqual(restored_groups, ["Caregivers"])
        self.assertEqual([recipient["name"] for recipient in restored_recipients], ["None", "None"])
        self.assertEqual([recipient["groups"] for recipient in restored_recipients], [["Caregivers"], ["Caregivers"]])

    def test_strict_old_name_phone_format_still_works(self):
        rows = preview_pasted_recipients(f"Amy, {raw_phone()}")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].name, "Amy")
        self.assertEqual(rows[0].normalized, normalized())
        self.assertEqual(rows[0].status, "Valid")

    def test_messy_text_with_multiple_phone_formats(self):
        text = (
            f"Call Amy at {raw_phone()} or John at ({'628'}) {'123'}-{'4567'}. "
            f"Backup: {'510'} {'123'} {'4567'}; office +1 {'707'} {'123'} {'4567'}; "
            f"legacy 1-{'925'}-{'123'}-{'4567'}"
        )

        rows = preview_pasted_recipients(text)

        self.assertEqual([row.normalized for row in rows], [
            normalized(),
            normalized("628"),
            normalized("510"),
            normalized("707"),
            normalized("925"),
        ])
        self.assertEqual([row.status for row in rows], ["Valid", "Valid", "Valid", "Valid", "Valid"])

    def test_pasted_names_and_phone_numbers_are_extracted(self):
        rows = preview_pasted_recipients(f"Amy {raw_phone()}\nJohn\t{raw_phone('628')}")

        self.assertEqual([(row.name, row.normalized) for row in rows], [
            ("Amy", normalized()),
            ("John", normalized("628")),
        ])

    def test_duplicate_numbers_in_different_formats_are_detected(self):
        rows = preview_pasted_recipients(
            f"{raw_phone()}\n"
            f"({'415'}) {'123'}-{'4567'}\n"
            f"+1 {'415'} {'123'} {'4567'}"
        )

        self.assertEqual([row.status for row in rows], [
            "Valid",
            "Duplicate in this batch",
            "Duplicate in this batch",
        ])

    def test_invalid_non_phone_text_is_ignored(self):
        rows = preview_pasted_recipients("Call Amy soon. No number here.")

        self.assertEqual(rows, [])

    def test_invalid_phone_like_fragment_is_reported(self):
        rows = preview_pasted_recipients("123")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].phone, "123")
        self.assertEqual(rows[0].status, "Invalid")

    def test_already_existing_normalized_number_is_skipped_from_messy_text(self):
        rows = preview_pasted_recipients(f"Existing contact: ({'415'}) {'123'}-{'4567'}", {normalized()})

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].normalized, normalized())
        self.assertEqual(rows[0].status, "Already exists")


if __name__ == "__main__":
    unittest.main()

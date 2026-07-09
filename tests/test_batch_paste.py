import unittest
import tempfile
import zipfile
from pathlib import Path

from app.storage import make_export_data, make_saved_data, parse_saved_data, parse_saved_settings
from core.groups import DEFAULT_GROUP
from core.importing import normalized_numbers_from_text, preview_import_file, preview_pasted_recipients, rows_to_add
from core.phone import PHONE_FORMAT_DASHES


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

    def test_phone_only_import_creates_phone_recipients(self):
        rows = preview_pasted_recipients(f"{raw_phone()}\n{raw_phone('628')}")
        recipients = rows_to_add(rows)

        self.assertEqual([recipient["phone"] for recipient in recipients], [normalized(), normalized("628")])
        self.assertEqual([recipient["group"] for recipient in recipients], [DEFAULT_GROUP, DEFAULT_GROUP])
        self.assertEqual([recipient["notes"] for recipient in recipients], ["", ""])

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
        recipients = rows_to_add(rows, "Caregivers")

        self.assertEqual(recipients[0]["group"], "Caregivers")
        self.assertEqual(recipients[0]["groups"], ["Caregivers"])

    def test_import_uses_one_selected_group(self):
        rows = preview_pasted_recipients(raw_phone())
        recipients = rows_to_add(rows, "Caregivers")

        self.assertEqual(recipients[0]["groups"], ["Caregivers"])

    def test_existing_recipient_groups_remain_unchanged_when_number_already_exists(self):
        existing = [{"name": "Amy", "phone": raw_phone(), "selected": False, "groups": ["Caregivers"]}]
        rows = preview_pasted_recipients(raw_phone(), {normalized()})
        existing.extend(rows_to_add(rows, "Follow-up"))

        self.assertEqual(existing, [
            {"name": "Amy", "phone": raw_phone(), "selected": False, "groups": ["Caregivers"]}
        ])

    def test_persistence_after_batch_import(self):
        rows = preview_pasted_recipients(f"{raw_phone()}\n{raw_phone('628')}")
        recipients = rows_to_add(rows, "Caregivers")
        saved = make_saved_data(recipients, ["Caregivers"])

        restored_recipients, restored_groups = parse_saved_data(saved)

        self.assertEqual(restored_groups, [DEFAULT_GROUP, "Caregivers"])
        self.assertEqual([recipient["phone"] for recipient in restored_recipients], [normalized(), normalized("628")])
        self.assertEqual([recipient["groups"] for recipient in restored_recipients], [["Caregivers"], ["Caregivers"]])

    def test_saved_phone_numbers_remain_e164_when_format_preference_changes(self):
        rows = preview_pasted_recipients(raw_phone())
        saved = make_saved_data(rows_to_add(rows, "Caregivers"), ["Caregivers"], {"phone_format": PHONE_FORMAT_DASHES})

        self.assertEqual(saved["settings"]["phone_format"], PHONE_FORMAT_DASHES)
        self.assertEqual(saved["recipients"][0]["phone"], normalized())

    def test_export_uses_selected_phone_format(self):
        rows = preview_pasted_recipients(raw_phone())
        exported = make_export_data(rows_to_add(rows, "Caregivers"), ["Caregivers"], PHONE_FORMAT_DASHES)

        self.assertEqual(exported["recipients"][0]["phone"], "415-123-4567")

    def test_old_data_without_settings_uses_default_phone_format(self):
        settings = parse_saved_settings({"version": 3, "recipients": [], "groups": []})

        self.assertEqual(settings["phone_format"], "e164")

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
        recipients = rows_to_add(rows, "Caregivers")

        self.assertEqual([(row.name, row.normalized) for row in rows], [
            ("Amy", normalized()),
            ("John", normalized("628")),
        ])
        self.assertNotIn("name", recipients[0])
        self.assertEqual([recipient["phone"] for recipient in recipients], [normalized(), normalized("628")])

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

    def test_required_single_number_formats(self):
        formats = [
            "4151111111",
            "415 111 1111",
            "415-111-1111",
            "(415) 111-1111",
            "+1 415 111 1111",
            "1-415-111-1111",
        ]

        for value in formats:
            with self.subTest(value=value):
                self.assertEqual(normalized_numbers_from_text(value), ["+14151111111"])

    def test_two_compact_numbers_separated_by_one_space(self):
        self.assertEqual(
            normalized_numbers_from_text("4151111111 6282222222"),
            ["+14151111111", "+16282222222"],
        )

    def test_two_dashed_numbers_on_one_line(self):
        self.assertEqual(
            normalized_numbers_from_text("415-111-1111 628-222-2222"),
            ["+14151111111", "+16282222222"],
        )

    def test_two_parenthesized_numbers_on_one_line(self):
        self.assertEqual(
            normalized_numbers_from_text("(415)111-1111 (628)222-2222"),
            ["+14151111111", "+16282222222"],
        )

    def test_two_plus_one_space_formatted_numbers_on_one_line(self):
        self.assertEqual(
            normalized_numbers_from_text("+1 415 111 1111 +1 628 222 2222"),
            ["+14151111111", "+16282222222"],
        )

    def test_numbers_surrounded_by_arbitrary_text(self):
        self.assertEqual(
            normalized_numbers_from_text("Primary: 4151111111 Secondary: 6282222222"),
            ["+14151111111", "+16282222222"],
        )

    def test_chinese_comma_separation(self):
        self.assertEqual(
            normalized_numbers_from_text("4151111111，6282222222"),
            ["+14151111111", "+16282222222"],
        )

    def test_slash_separation(self):
        self.assertEqual(
            normalized_numbers_from_text("4151111111 / 6282222222"),
            ["+14151111111", "+16282222222"],
        )

    def test_pipe_separation(self):
        self.assertEqual(
            normalized_numbers_from_text("4151111111 | 6282222222"),
            ["+14151111111", "+16282222222"],
        )

    def test_preserves_number_order(self):
        self.assertEqual(
            normalized_numbers_from_text("5103333333 then 4151111111 then 6282222222"),
            ["+15103333333", "+14151111111", "+16282222222"],
        )

    def test_txt_import_uses_shared_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "numbers.txt"
            path.write_text("John 4151111111\n4151111111 6282222222", encoding="utf-8")
            rows = preview_import_file(path)

        self.assertEqual([row.normalized for row in rows], [
            "+14151111111",
            "+14151111111",
            "+16282222222",
        ])
        self.assertEqual([row.status for row in rows], [
            "Valid",
            "Duplicate in this batch",
            "Valid",
        ])

    def test_csv_import_uses_shared_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "numbers.csv"
            path.write_text("Name,Phone\nAmy,4151111111 6282222222\n", encoding="utf-8")
            rows = preview_import_file(path)

        self.assertEqual([row.normalized for row in rows], ["+14151111111", "+16282222222"])

    def test_xlsx_import_uses_shared_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "numbers.xlsx"
            write_minimal_xlsx(path, ["Amy 4151111111", "6282222222"])
            rows = preview_import_file(path)

        self.assertEqual([row.normalized for row in rows], ["+14151111111", "+16282222222"])


def write_minimal_xlsx(path: Path, values: list[str]) -> None:
    shared_items = "".join(f"<si><t>{value}</t></si>" for value in values)
    cells = "".join(
        f'<row r="{index + 1}"><c r="A{index + 1}" t="s"><v>{index}</v></c></row>'
        for index in range(len(values))
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>""")
        archive.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>""")
        archive.writestr("xl/sharedStrings.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">{shared_items}</sst>""")
        archive.writestr("xl/worksheets/sheet1.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{cells}</sheetData></worksheet>""")


if __name__ == "__main__":
    unittest.main()

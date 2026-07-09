import tempfile
import unittest
from pathlib import Path

from core.importing import detect_csv_columns, parse_pasted_list, read_csv_recipients
from core.phone import (
    PHONE_FORMAT_DASHES,
    PHONE_FORMAT_DIGITS,
    PHONE_FORMAT_E164,
    PHONE_FORMAT_PARENS,
    PHONE_FORMAT_SPACES,
    format_phone_number,
    normalize_us_phone,
)
from core.recipients import build_clipboard_output


def raw_phone(area: str = "415", exchange: str = "123", line: str = "4567", separator: str = "-") -> str:
    return separator.join([area, exchange, line])


def normalized(area: str = "415", exchange: str = "123", line: str = "4567") -> str:
    return "+1" + area + exchange + line


def parenthesized(area: str = "415", exchange: str = "123", line: str = "4567") -> str:
    return "(" + area + ") " + exchange + "-" + line


class PhoneNormalizationTests(unittest.TestCase):
    def test_10_digit_us_number_normalizes_with_country_code(self):
        self.assertEqual(normalize_us_phone(raw_phone()), (normalized(), "Valid"))

    def test_11_digit_us_number_normalizes_with_plus(self):
        self.assertEqual(normalize_us_phone("1-" + raw_phone()), (normalized(), "Valid"))

    def test_already_normalized_plus_one_number_is_kept(self):
        self.assertEqual(normalize_us_phone(normalized()), (normalized(), "Valid"))

    def test_punctuation_is_removed(self):
        punctuated = "(" + "415" + ") " + "123" + "." + "4567"
        self.assertEqual(normalize_us_phone(punctuated), (normalized(), "Valid"))

    def test_invalid_number_is_rejected(self):
        normalized, status = normalize_us_phone("12345")
        self.assertEqual(normalized, "")
        self.assertTrue(status.startswith("Invalid"))

    def test_phone_display_formats_are_exact(self):
        value = normalized()

        self.assertEqual(format_phone_number(value, PHONE_FORMAT_E164), "+14151234567")
        self.assertEqual(format_phone_number(value, PHONE_FORMAT_DIGITS), "4151234567")
        self.assertEqual(format_phone_number(value, PHONE_FORMAT_DASHES), "415-123-4567")
        self.assertEqual(format_phone_number(value, PHONE_FORMAT_PARENS), "(415) 123-4567")
        self.assertEqual(format_phone_number(value, PHONE_FORMAT_SPACES), "+1 415 123 4567")


class ClipboardOutputTests(unittest.TestCase):
    def test_filters_selected_deduplicates_and_skips_invalid(self):
        result = build_clipboard_output(
            [
                {"name": "Amy", "phone": raw_phone(), "selected": True},
                {"name": "Duplicate Amy", "phone": normalized(), "selected": True},
                {"name": "Invalid", "phone": "12345", "selected": True},
                {"name": "Unselected", "phone": raw_phone("628"), "selected": False},
                {"name": "John", "phone": raw_phone("628"), "selected": True},
            ],
            "comma",
        )

        self.assertEqual(result.selected, 4)
        self.assertEqual(result.copied, 2)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(result.invalid_skipped, 1)
        self.assertEqual(result.output, ",".join([normalized(), normalized("628")]))

    def test_output_format_can_be_changed(self):
        recipients = [
            {"name": "Amy", "phone": raw_phone(), "selected": True},
            {"name": "John", "phone": raw_phone("628"), "selected": True},
        ]

        self.assertEqual(build_clipboard_output(recipients, "semicolon").output, ";".join([normalized(), normalized("628")]))
        self.assertEqual(build_clipboard_output(recipients, "newline").output, "\n".join([normalized(), normalized("628")]))

    def test_phone_display_format_can_be_changed_for_copy(self):
        recipients = [
            {"phone": normalized(), "selected": True},
            {"phone": raw_phone("628"), "selected": True},
        ]

        result = build_clipboard_output(recipients, "comma", PHONE_FORMAT_DASHES)

        self.assertEqual(result.output, "415-123-4567,628-123-4567")


class ImportingTests(unittest.TestCase):
    def test_pasted_list_parses_common_formats(self):
        accepted, rejected = parse_pasted_list(
            f"{raw_phone('510')}\n"
            f"Amy, {raw_phone()}\n"
            f"John, {parenthesized('628')}\n"
            f"Mary    {raw_phone(separator='.')}\n"
            "Bad row\n"
        )

        self.assertEqual([(row.name, row.phone) for row in accepted], [
            ("", raw_phone("510")),
            ("Amy", raw_phone()),
            ("John", parenthesized("628")),
            ("Mary", raw_phone(separator=".")),
        ])
        self.assertEqual(len(rejected), 1)

    def test_csv_column_detection_recognizes_variants(self):
        self.assertEqual(detect_csv_columns(["full_name", "mobile"]), ("full_name", "mobile"))
        self.assertEqual(detect_csv_columns(["Contact", "Phone Number"]), ("Contact", "Phone Number"))

    def test_csv_reader_imports_rows_and_rejects_missing_phone(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.csv"
            path.write_text(f"Name,Phone\nAmy,{raw_phone()}\n,{raw_phone('628')}\nMissing,\n", encoding="utf-8")

            accepted, rejected = read_csv_recipients(path, "Name", "Phone")

        self.assertEqual([(row.name, row.phone) for row in accepted], [("Amy", raw_phone()), ("", raw_phone("628"))])
        self.assertEqual(len(rejected), 1)


if __name__ == "__main__":
    unittest.main()

import csv
import io
import json
import unittest
import zipfile
from xml.etree import ElementTree

from core.exporting import (
    SCOPE_ALL,
    SCOPE_GROUP,
    SCOPE_SEARCH,
    SCOPE_SELECTION,
    backup_json,
    export_csv,
    export_txt,
    export_xlsx_bytes,
    parse_backup_json,
    resolve_recipient_scope,
)
from core.groups import ALL_RECIPIENTS, DEFAULT_GROUP, SORT_PHONE
from core.phone import PHONE_FORMAT_DASHES


def recipient(phone: str, group: str = DEFAULT_GROUP, notes: str = "", selected: bool = False) -> dict:
    return {"phone": phone, "group": group, "groups": [group], "notes": notes, "selected": selected}


class ExportingTests(unittest.TestCase):
    def setUp(self):
        self.recipients = [
            recipient("+14151111111", "Caregivers", "needs, comma", True),
            recipient("+16282222222", "Caregivers", 'quote "here"', False),
            recipient("+17073333333", "Follow-up", "line\nbreak", True),
        ]

    def test_export_scope_all(self):
        selection = resolve_recipient_scope(self.recipients, SCOPE_ALL)

        self.assertEqual([row["phone"] for row in selection.recipients], ["+14151111111", "+16282222222", "+17073333333"])

    def test_export_scope_current_group(self):
        selection = resolve_recipient_scope(self.recipients, SCOPE_GROUP, group_filter="Caregivers")

        self.assertEqual([row["phone"] for row in selection.recipients], ["+14151111111", "+16282222222"])

    def test_export_scope_current_search(self):
        selection = resolve_recipient_scope(
            self.recipients,
            SCOPE_SEARCH,
            group_filter=ALL_RECIPIENTS,
            query="follow",
            sort_field=SORT_PHONE,
        )

        self.assertEqual([row["phone"] for row in selection.recipients], ["+17073333333"])

    def test_export_scope_current_selection_preserves_visible_order(self):
        selection = resolve_recipient_scope(
            self.recipients,
            SCOPE_SELECTION,
            group_filter=ALL_RECIPIENTS,
            sort_field=SORT_PHONE,
            descending=True,
        )

        self.assertEqual([row["phone"] for row in selection.recipients], ["+17073333333", "+14151111111"])

    def test_txt_export_uses_display_format_and_scope(self):
        text = export_txt(self.recipients[:2], PHONE_FORMAT_DASHES)

        self.assertEqual(text, "415-111-1111\n628-222-2222")

    def test_csv_export_has_headers_rows_and_escaping(self):
        text = export_csv(self.recipients, PHONE_FORMAT_DASHES)
        rows = list(csv.reader(io.StringIO(text)))

        self.assertEqual(rows[0], ["Phone Number", "Group", "Notes"])
        self.assertEqual(rows[1], ["415-111-1111", "Caregivers", "needs, comma"])
        self.assertEqual(rows[2], ["628-222-2222", "Caregivers", 'quote "here"'])
        self.assertEqual(rows[3], ["707-333-3333", "Follow-up", "line\nbreak"])

    def test_xlsx_export_is_valid_with_headers_and_rows(self):
        content = export_xlsx_bytes(self.recipients[:1], PHONE_FORMAT_DASHES)

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))

        values = [node.text for node in sheet.findall(".//{*}t")]
        self.assertEqual(values, ["Phone Number", "Group", "Notes", "415-111-1111", "Caregivers", "needs, comma"])

    def test_backup_export_preserves_canonical_data_and_settings(self):
        data = json.loads(backup_json(self.recipients, ["Caregivers", "Follow-up"], {"phone_format": PHONE_FORMAT_DASHES}))

        self.assertEqual(data["backup_version"], 1)
        self.assertEqual(data["app"], "PourSend")
        self.assertEqual(data["data"]["settings"]["phone_format"], PHONE_FORMAT_DASHES)
        self.assertEqual(data["data"]["recipients"][0]["phone"], "+14151111111")
        self.assertEqual(data["data"]["recipients"][0]["notes"], "needs, comma")

    def test_backup_import_restores_valid_backup(self):
        text = backup_json(self.recipients, ["Caregivers", "Follow-up"], {"phone_format": PHONE_FORMAT_DASHES})

        recipients, groups, settings, version = parse_backup_json(text)

        self.assertEqual(version, 1)
        self.assertEqual(groups, [DEFAULT_GROUP, "Caregivers", "Follow-up"])
        self.assertEqual(settings["phone_format"], PHONE_FORMAT_DASHES)
        self.assertEqual(recipients[0]["phone"], "+14151111111")

    def test_backup_import_accepts_empty_backup_with_default_settings(self):
        text = backup_json([], [], {})

        recipients, groups, settings, version = parse_backup_json(text)

        self.assertEqual(version, 1)
        self.assertEqual(recipients, [])
        self.assertEqual(groups, [DEFAULT_GROUP])
        self.assertEqual(settings["phone_format"], "e164")

    def test_empty_export_scope_has_clear_reason(self):
        recipients = [recipient("+14151111111", selected=False)]

        selection = resolve_recipient_scope(recipients, SCOPE_SELECTION)

        self.assertEqual(selection.recipients, [])
        self.assertEqual(selection.empty_reason, "No recipients match that scope.")

    def test_backup_import_rejects_invalid_json(self):
        with self.assertRaises(ValueError):
            parse_backup_json("{")

    def test_backup_import_rejects_unsupported_structure(self):
        with self.assertRaises(ValueError):
            parse_backup_json(json.dumps({"backup_version": 99, "data": {}}))

    def test_backup_import_rejects_invalid_recipient_phone(self):
        backup = {
            "backup_version": 1,
            "app": "PourSend",
            "data": {
                "version": 3,
                "settings": {},
                "groups": [DEFAULT_GROUP],
                "recipients": [{"phone": "not a phone", "group": DEFAULT_GROUP}],
            },
        }

        with self.assertRaises(ValueError):
            parse_backup_json(json.dumps(backup))


if __name__ == "__main__":
    unittest.main()

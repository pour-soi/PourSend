import json
import tempfile
import unittest
from pathlib import Path

from app.storage import make_saved_data, parse_saved_data
from core.groups import (
    ALL_RECIPIENTS,
    UNASSIGNED,
    assign_to_group,
    create_group,
    delete_group,
    filtered_recipient_indexes,
    remove_from_group,
    rename_group,
    set_selected,
)
from core.recipients import build_clipboard_output


def raw_phone(area: str = "415", exchange: str = "123", line: str = "4567") -> str:
    return "-".join([area, exchange, line])


def normalized(area: str = "415", exchange: str = "123", line: str = "4567") -> str:
    return "+1" + area + exchange + line


def sample_recipients() -> list[dict]:
    return [
        {"name": "Amy", "phone": raw_phone(), "selected": False, "groups": ["Caregivers"]},
        {"name": "John", "phone": raw_phone("628"), "selected": False, "groups": ["Job Seekers"]},
        {"name": "Mary", "phone": raw_phone("707"), "selected": False, "groups": []},
    ]


class GroupTests(unittest.TestCase):
    def test_old_recipient_list_loads_as_unassigned(self):
        old_data = [{"name": "Amy", "phone": raw_phone(), "selected": True}]

        recipients, groups = parse_saved_data(old_data)

        self.assertEqual(groups, [])
        self.assertEqual(recipients[0]["name"], "Amy")
        self.assertEqual(recipients[0]["phone"], raw_phone())
        self.assertTrue(recipients[0]["selected"])
        self.assertEqual(recipients[0]["groups"], [])
        self.assertEqual(filtered_recipient_indexes(recipients, UNASSIGNED), [0])

    def test_one_recipient_can_belong_to_multiple_groups(self):
        recipients = [{"name": "Amy", "phone": raw_phone(), "selected": False, "groups": []}]
        groups = ["Caregivers", "Follow-up"]

        assign_to_group(recipients, [0], groups[0])
        assign_to_group(recipients, [0], groups[1])

        self.assertEqual(recipients[0]["groups"], ["Caregivers", "Follow-up"])
        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers"), [0])
        self.assertEqual(filtered_recipient_indexes(recipients, "Follow-up"), [0])

    def test_group_creation(self):
        groups: list[str] = []

        self.assertTrue(create_group(groups, "Caregivers"))
        self.assertFalse(create_group(groups, "Caregivers"))

        self.assertEqual(groups, ["Caregivers"])

    def test_group_rename_updates_memberships(self):
        recipients = sample_recipients()
        groups = ["Caregivers", "Job Seekers"]

        self.assertTrue(rename_group(recipients, groups, "Caregivers", "Follow-up"))

        self.assertEqual(groups, ["Follow-up", "Job Seekers"])
        self.assertEqual(recipients[0]["groups"], ["Follow-up"])
        self.assertEqual(filtered_recipient_indexes(recipients, "Follow-up"), [0])

    def test_group_delete_does_not_delete_recipients(self):
        recipients = sample_recipients()
        groups = ["Caregivers", "Job Seekers"]

        self.assertTrue(delete_group(recipients, groups, "Caregivers"))

        self.assertEqual(len(recipients), 3)
        self.assertEqual(groups, ["Job Seekers"])
        self.assertEqual(recipients[0]["groups"], [])
        self.assertEqual(filtered_recipient_indexes(recipients, UNASSIGNED), [0, 2])

    def test_unassigned_filtering(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, UNASSIGNED), [2])

    def test_named_group_filtering(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers"), [0])

    def test_select_all_in_group_affects_only_group(self):
        recipients = sample_recipients()

        set_selected(recipients, filtered_recipient_indexes(recipients, "Caregivers"), True)

        self.assertTrue(recipients[0]["selected"])
        self.assertFalse(recipients[1]["selected"])
        self.assertFalse(recipients[2]["selected"])

    def test_deselect_all_in_group_affects_only_group(self):
        recipients = sample_recipients()
        for recipient in recipients:
            recipient["selected"] = True

        set_selected(recipients, filtered_recipient_indexes(recipients, "Caregivers"), False)

        self.assertFalse(recipients[0]["selected"])
        self.assertTrue(recipients[1]["selected"])
        self.assertTrue(recipients[2]["selected"])

    def test_group_specific_search(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "Amy"), [0])
        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers", "Amy"), [0])
        self.assertEqual(filtered_recipient_indexes(recipients, "Job Seekers", "Amy"), [])
        self.assertEqual(filtered_recipient_indexes(recipients, "Job Seekers", "628"), [1])

    def test_group_persistence_round_trip(self):
        recipients = sample_recipients()
        groups = ["Caregivers", "Job Seekers"]
        recipients[0]["groups"].append("Job Seekers")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            path.write_text(json.dumps(make_saved_data(recipients, groups)), encoding="utf-8")
            loaded = json.loads(path.read_text(encoding="utf-8"))

        restored_recipients, restored_groups = parse_saved_data(loaded)

        self.assertEqual(restored_groups, ["Caregivers", "Job Seekers"])
        self.assertEqual(restored_recipients[0]["groups"], ["Caregivers", "Job Seekers"])

    def test_deleted_group_stays_deleted_after_persistence(self):
        recipients = sample_recipients()
        groups = ["Caregivers", "Job Seekers"]
        delete_group(recipients, groups, "Caregivers")

        restored_recipients, restored_groups = parse_saved_data(make_saved_data(recipients, groups))

        self.assertEqual(restored_groups, ["Job Seekers"])
        self.assertEqual(restored_recipients[0]["groups"], [])
        self.assertEqual(len(restored_recipients), 3)

    def test_copy_behavior_after_group_selection(self):
        recipients = sample_recipients()
        recipients.append(
            {"name": "Duplicate Amy", "phone": normalized(), "selected": False, "groups": ["Caregivers"]}
        )
        recipients.append({"name": "Invalid", "phone": "12345", "selected": False, "groups": ["Caregivers"]})

        set_selected(recipients, filtered_recipient_indexes(recipients, "Caregivers"), True)
        result = build_clipboard_output(recipients, "comma")

        self.assertEqual(result.selected, 3)
        self.assertEqual(result.copied, 1)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(result.invalid_skipped, 1)
        self.assertEqual(result.output, normalized())

    def test_remove_selected_from_group(self):
        recipients = sample_recipients()

        remove_from_group(recipients, [0], "Caregivers")

        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers"), [])
        self.assertEqual(filtered_recipient_indexes(recipients, UNASSIGNED), [0, 2])


if __name__ == "__main__":
    unittest.main()

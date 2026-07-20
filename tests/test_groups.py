import json
import tempfile
import unittest
from pathlib import Path

from app.storage import make_saved_data, parse_saved_data
from core.groups import (
    ALL_RECIPIENTS,
    DEFAULT_GROUP,
    assign_to_group,
    batch_update_recipients,
    checked_recipient_indexes,
    create_group,
    count_duplicate_phone_numbers,
    delete_group,
    filtered_recipient_indexes,
    normalize_recipient_group,
    normalize_recipients,
    preferred_group,
    remove_from_group,
    rename_group,
    SORT_GROUP,
    SORT_PHONE,
    SORT_RECENT,
    set_selected,
    valid_group_or_default,
)
from core.importing import preview_pasted_recipients, rows_to_add
from core.phone import PHONE_FORMAT_DASHES, PHONE_FORMAT_PARENS
from core.recipients import build_clipboard_output


def raw_phone(area: str = "415", exchange: str = "123", line: str = "4567") -> str:
    return "-".join([area, exchange, line])


def normalized(area: str = "415", exchange: str = "123", line: str = "4567") -> str:
    return "+1" + area + exchange + line


def sample_recipients() -> list[dict]:
    return [
        {"phone": raw_phone(), "selected": False, "group": "Caregivers", "notes": "morning"},
        {"phone": raw_phone("628"), "selected": False, "group": "Job Seekers", "notes": ""},
        {"phone": raw_phone("707"), "selected": False, "group": DEFAULT_GROUP, "notes": "follow up"},
    ]


class GroupTests(unittest.TestCase):
    def test_legacy_recipient_without_group_falls_back_to_default(self):
        old_data = [{"name": "Amy", "phone": raw_phone(), "selected": True}]

        recipients, groups = parse_saved_data(old_data)

        self.assertEqual(groups, [DEFAULT_GROUP])
        self.assertEqual(recipients[0]["name"], "Amy")
        self.assertEqual(recipients[0]["phone"], normalized())
        self.assertTrue(recipients[0]["selected"])
        self.assertEqual(recipients[0]["group"], DEFAULT_GROUP)
        self.assertEqual(recipients[0]["groups"], [DEFAULT_GROUP])

    def test_legacy_recipient_name_is_not_required(self):
        recipients, groups = parse_saved_data([{"phone": raw_phone(), "selected": False}])

        self.assertEqual(groups, [DEFAULT_GROUP])
        self.assertEqual(recipients[0]["phone"], normalized())
        self.assertEqual(recipients[0]["group"], DEFAULT_GROUP)

    def test_legacy_group_membership_remains_accessible(self):
        recipients, groups = parse_saved_data(
            [{"name": "Amy", "phone": raw_phone(), "selected": False, "groups": ["Caregivers"]}]
        )

        self.assertEqual(groups, [DEFAULT_GROUP, "Caregivers"])
        self.assertEqual(recipients[0]["group"], "Caregivers")
        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers"), [0])

    def test_recipient_can_belong_to_multiple_groups(self):
        recipients, groups = parse_saved_data(
            [{"phone": raw_phone(), "group": "Caregivers", "groups": ["Caregivers", "Follow-up"]}]
        )

        self.assertEqual(groups, [DEFAULT_GROUP, "Caregivers", "Follow-up"])
        self.assertEqual(recipients[0]["groups"], ["Caregivers", "Follow-up"])
        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers"), [0])
        self.assertEqual(filtered_recipient_indexes(recipients, "Follow-up"), [0])
        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS), [0])

    def test_saved_groups_field_memberships_are_preserved_when_group_list_is_incomplete(self):
        data = {
            "groups": ["Caregivers"],
            "recipients": [{"phone": raw_phone(), "groups": ["Caregivers", "Follow-up", "Follow-up"]}],
        }

        recipients, groups = parse_saved_data(data)

        self.assertEqual(groups, [DEFAULT_GROUP, "Caregivers", "Follow-up"])
        self.assertEqual(recipients[0]["groups"], ["Caregivers", "Follow-up"])

    def test_missing_saved_group_falls_back_to_default(self):
        data = {
            "groups": ["Caregivers"],
            "recipients": [{"phone": raw_phone(), "group": "Deleted Group", "selected": False}],
        }

        recipients, groups = parse_saved_data(data)

        self.assertEqual(groups, [DEFAULT_GROUP, "Caregivers"])
        self.assertEqual(recipients[0]["group"], DEFAULT_GROUP)

    def test_phone_number_is_unique_identifier(self):
        recipients = normalize_recipients(
            [
                {"phone": raw_phone(), "group": "Caregivers"},
                {"phone": normalized(), "group": "Job Seekers"},
            ],
            ["Caregivers", "Job Seekers"],
        )

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]["group"], "Caregivers")
        self.assertEqual(recipients[0]["groups"], ["Caregivers", "Job Seekers"])

    def test_duplicate_phone_migration_merges_non_identity_fields(self):
        recipients = normalize_recipients(
            [
                {"phone": raw_phone(), "group": "Caregivers", "selected": False, "notes": "first"},
                {"phone": normalized(), "group": "Job Seekers", "selected": True, "notes": "second"},
            ],
            ["Caregivers", "Job Seekers"],
        )

        self.assertEqual(len(recipients), 1)
        self.assertTrue(recipients[0]["selected"])
        self.assertEqual(recipients[0]["notes"], "first\nsecond")

    def test_notes_are_optional(self):
        recipients = normalize_recipients([{"phone": raw_phone(), "group": DEFAULT_GROUP}], [DEFAULT_GROUP])

        self.assertEqual(recipients[0]["notes"], "")

    def test_group_creation_rejects_empty_and_duplicate_names(self):
        groups = [DEFAULT_GROUP]

        self.assertFalse(create_group(groups, " "))
        self.assertTrue(create_group(groups, "Caregivers"))
        self.assertFalse(create_group(groups, "Caregivers"))

        self.assertEqual(groups, [DEFAULT_GROUP, "Caregivers"])

    def test_group_creation_is_globally_casefold_unique_and_protects_system_names(self):
        groups = [DEFAULT_GROUP, "Group"]

        self.assertFalse(create_group(groups, "group"))
        self.assertFalse(create_group(groups, " Group "))
        self.assertTrue(create_group(groups, "Straße"))
        self.assertFalse(create_group(groups, "STRASSE"))
        self.assertTrue(create_group(groups, "A组"))
        self.assertFalse(create_group(groups, "Ａ组"))
        self.assertTrue(create_group(groups, "équipe"))
        self.assertFalse(create_group(groups, "équipe"))
        self.assertFalse(create_group(groups, "All Recipients"))
        self.assertFalse(create_group(groups, " all recipients "))
        self.assertFalse(create_group(groups, "default"))
        self.assertFalse(create_group(groups, "   "))
        self.assertEqual(groups, [DEFAULT_GROUP, "Group", "Straße", "A组", "équipe"])

    def test_group_rename_updates_memberships(self):
        recipients = sample_recipients()
        recipients[0]["groups"] = ["Caregivers", "Follow-up"]
        groups = [DEFAULT_GROUP, "Caregivers", "Job Seekers"]

        self.assertTrue(rename_group(recipients, groups, "Caregivers", "Family"))

        self.assertEqual(groups, [DEFAULT_GROUP, "Family", "Job Seekers"])
        self.assertEqual(recipients[0]["group"], "Family")
        self.assertEqual(recipients[0]["groups"], ["Family", "Follow-up"])
        self.assertEqual(filtered_recipient_indexes(recipients, "Family"), [0])

    def test_group_rename_rejects_default_empty_and_duplicate(self):
        recipients = sample_recipients()
        groups = [DEFAULT_GROUP, "Caregivers", "Job Seekers"]

        self.assertFalse(rename_group(recipients, groups, DEFAULT_GROUP, "Other"))
        self.assertFalse(rename_group(recipients, groups, "Caregivers", ""))
        self.assertFalse(rename_group(recipients, groups, "Caregivers", "Job Seekers"))

    def test_group_rename_rejects_nfkc_equivalent_name(self):
        recipients = sample_recipients()
        groups = [DEFAULT_GROUP, "Caregivers", "A组"]
        before_memberships = [list(recipient.get("groups", [])) for recipient in recipients]

        self.assertFalse(rename_group(recipients, groups, "Caregivers", "Ａ组"))

        self.assertEqual(groups, [DEFAULT_GROUP, "Caregivers", "A组"])
        self.assertEqual([recipient.get("groups", []) for recipient in recipients], before_memberships)

    def test_rejected_rename_preserves_groups_and_recipient_memberships(self):
        recipients = sample_recipients()
        groups = [DEFAULT_GROUP, "Caregivers", "Job Seekers"]
        before_groups = list(groups)
        before_memberships = [list(recipient.get("groups", [])) for recipient in recipients]

        self.assertFalse(rename_group(recipients, groups, "Caregivers", " job seekers "))
        self.assertFalse(rename_group(recipients, groups, "Caregivers", "ALL RECIPIENTS"))

        self.assertEqual(groups, before_groups)
        self.assertEqual([recipient.get("groups", []) for recipient in recipients], before_memberships)

    def test_group_delete_moves_recipients_to_default(self):
        recipients = sample_recipients()
        recipients[0]["groups"] = ["Caregivers", "Follow-up"]
        groups = [DEFAULT_GROUP, "Caregivers", "Job Seekers"]

        self.assertTrue(delete_group(recipients, groups, "Caregivers"))

        self.assertEqual(len(recipients), 3)
        self.assertEqual(groups, [DEFAULT_GROUP, "Job Seekers"])
        self.assertEqual(recipients[0]["group"], "Follow-up")
        self.assertEqual(recipients[0]["groups"], ["Follow-up"])
        self.assertEqual(filtered_recipient_indexes(recipients, DEFAULT_GROUP), [2])

    def test_default_group_cannot_be_deleted(self):
        recipients = sample_recipients()
        groups = [DEFAULT_GROUP, "Caregivers"]

        self.assertFalse(delete_group(recipients, groups, DEFAULT_GROUP))
        self.assertEqual(groups, [DEFAULT_GROUP, "Caregivers"])

    def test_group_filtering(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS), [0, 1, 2])
        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers"), [0])
        self.assertEqual(filtered_recipient_indexes(recipients, DEFAULT_GROUP), [2])

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

    def test_group_specific_search_uses_phone_and_notes(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "morning"), [0])
        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers", "morning"), [0])
        self.assertEqual(filtered_recipient_indexes(recipients, "Job Seekers", "morning"), [])
        self.assertEqual(filtered_recipient_indexes(recipients, "Job Seekers", "628"), [1])

    def test_search_by_displayed_phone_number(self):
        recipients = sample_recipients()

        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "415-123", PHONE_FORMAT_DASHES),
            [0],
        )

    def test_search_by_e164_phone_number(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "+1415123"), [0])

    def test_punctuation_insensitive_and_partial_phone_search(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "(415) 123"), [0])
        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "415 123"), [0])

    def test_search_by_group(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "seekers"), [1])

    def test_search_is_case_insensitive_for_notes(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "MORNING"), [0])

    def test_clearing_search_restores_all_recipients(self):
        recipients = sample_recipients()

        self.assertEqual(filtered_recipient_indexes(recipients, ALL_RECIPIENTS, ""), [0, 1, 2])

    def test_search_does_not_mutate_recipients(self):
        recipients = sample_recipients()
        before = [dict(recipient) for recipient in recipients]

        filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "415")

        self.assertEqual(recipients, before)

    def test_search_works_after_display_format_change(self):
        recipients = sample_recipients()

        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "(415) 123", PHONE_FORMAT_PARENS),
            [0],
        )

    def test_phone_sort_ascending_and_descending(self):
        recipients = [
            {"phone": raw_phone("707"), "group": DEFAULT_GROUP},
            {"phone": raw_phone("415"), "group": DEFAULT_GROUP},
            {"phone": raw_phone("628"), "group": DEFAULT_GROUP},
        ]

        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "", "e164", SORT_PHONE, False),
            [1, 2, 0],
        )
        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "", "e164", SORT_PHONE, True),
            [0, 2, 1],
        )

    def test_group_sort_ascending_and_descending(self):
        recipients = [
            {"phone": raw_phone("415"), "group": "beta"},
            {"phone": raw_phone("628"), "group": "Alpha"},
            {"phone": raw_phone("707"), "group": DEFAULT_GROUP},
        ]

        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "", "e164", SORT_GROUP, False),
            [1, 0, 2],
        )
        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "", "e164", SORT_GROUP, True),
            [2, 0, 1],
        )

    def test_recently_added_sort_uses_list_order(self):
        recipients = sample_recipients()

        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "", "e164", SORT_RECENT, False),
            [0, 1, 2],
        )
        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "", "e164", SORT_RECENT, True),
            [2, 1, 0],
        )

    def test_sorting_has_stable_secondary_order(self):
        recipients = [
            {"phone": raw_phone("415"), "group": "Caregivers"},
            {"phone": raw_phone("628"), "group": "Caregivers"},
            {"phone": raw_phone("707"), "group": "Caregivers"},
        ]

        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "", "e164", SORT_GROUP, True),
            [0, 1, 2],
        )

    def test_search_and_sorting_compose(self):
        recipients = [
            {"phone": raw_phone("707"), "group": "Caregivers", "notes": "call"},
            {"phone": raw_phone("415"), "group": "Caregivers", "notes": "call"},
            {"phone": raw_phone("628"), "group": "Caregivers", "notes": "other"},
        ]

        self.assertEqual(
            filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "call", "e164", SORT_PHONE, False),
            [1, 0],
        )

    def test_group_persistence_round_trip(self):
        recipients = sample_recipients()
        groups = [DEFAULT_GROUP, "Caregivers", "Job Seekers"]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            path.write_text(json.dumps(make_saved_data(recipients, groups)), encoding="utf-8")
            loaded = json.loads(path.read_text(encoding="utf-8"))

        restored_recipients, restored_groups = parse_saved_data(loaded)

        self.assertEqual(restored_groups, [DEFAULT_GROUP, "Caregivers", "Job Seekers"])
        self.assertEqual(restored_recipients[0]["group"], "Caregivers")
        self.assertEqual(restored_recipients[0]["notes"], "morning")

    def test_deleted_group_stays_deleted_after_persistence(self):
        recipients = sample_recipients()
        groups = [DEFAULT_GROUP, "Caregivers", "Job Seekers"]
        delete_group(recipients, groups, "Caregivers")

        restored_recipients, restored_groups = parse_saved_data(make_saved_data(recipients, groups))

        self.assertEqual(restored_groups, [DEFAULT_GROUP, "Job Seekers"])
        self.assertEqual(restored_recipients[0]["group"], DEFAULT_GROUP)
        self.assertEqual(len(restored_recipients), 3)

    def test_batch_move_recipients(self):
        recipients = sample_recipients()

        assign_to_group(recipients, [0, 2], "Follow-up")

        self.assertEqual(recipients[0]["groups"], ["Caregivers", "Follow-up"])
        self.assertEqual(recipients[2]["groups"], ["Follow-up"])
        self.assertEqual(recipients[0]["notes"], "morning")

    def test_batch_update_recipients_updates_group_and_notes(self):
        recipients = sample_recipients()

        updated = batch_update_recipients(recipients, [0, 2], group="Follow-up", notes="new note")

        self.assertEqual(updated, 2)
        self.assertEqual(recipients[0]["group"], "Follow-up")
        self.assertEqual(recipients[2]["group"], "Follow-up")
        self.assertEqual(recipients[0]["notes"], "new note")
        self.assertEqual(recipients[2]["notes"], "new note")

    def test_duplicate_phone_count_uses_normalized_identity(self):
        recipients = sample_recipients()
        recipients.append({"phone": normalized(), "group": "Caregivers", "notes": ""})

        self.assertEqual(count_duplicate_phone_numbers(recipients), 1)

    def test_remove_from_group_moves_to_default(self):
        recipients = sample_recipients()

        remove_from_group(recipients, [0], "Caregivers")

        self.assertEqual(normalize_recipient_group(recipients[0]), DEFAULT_GROUP)
        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers"), [])

    def test_remove_from_one_group_preserves_other_memberships(self):
        recipients = sample_recipients()
        recipients[0]["groups"] = ["Caregivers", "Follow-up"]

        remove_from_group(recipients, [0], "Caregivers")

        self.assertEqual(recipients[0]["groups"], ["Follow-up"])
        self.assertEqual(filtered_recipient_indexes(recipients, "Follow-up"), [0])

    def test_removing_last_group_falls_back_to_default(self):
        recipients = sample_recipients()

        remove_from_group(recipients, [0], "Caregivers")

        self.assertEqual(recipients[0]["groups"], [DEFAULT_GROUP])

    def test_invalid_filter_state_recovers_after_group_deletion(self):
        recipients = sample_recipients()
        groups = [DEFAULT_GROUP, "Caregivers", "Job Seekers"]

        delete_group(recipients, groups, "Caregivers")

        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers"), [])
        self.assertEqual(filtered_recipient_indexes(recipients, DEFAULT_GROUP), [0, 2])

    def test_recently_used_group_prefers_current_then_recent(self):
        groups = [DEFAULT_GROUP, "Caregivers", "Follow-up"]

        self.assertEqual(preferred_group("Caregivers", "Follow-up", groups), "Caregivers")
        self.assertEqual(preferred_group(None, "Follow-up", groups), "Follow-up")

    def test_missing_recently_used_group_falls_back_to_default(self):
        groups = [DEFAULT_GROUP, "Caregivers"]

        self.assertEqual(preferred_group(None, "Deleted", groups), DEFAULT_GROUP)
        self.assertEqual(valid_group_or_default("Deleted", groups), DEFAULT_GROUP)

    def test_copy_behavior_after_group_selection(self):
        recipients = sample_recipients()
        recipients.append({"phone": normalized(), "selected": False, "group": "Caregivers", "notes": ""})
        recipients.append({"phone": "12345", "selected": False, "group": "Caregivers", "notes": ""})

        set_selected(recipients, filtered_recipient_indexes(recipients, "Caregivers"), True)
        result = build_clipboard_output(recipients, "comma")

        self.assertEqual(result.selected, 3)
        self.assertEqual(result.copied, 1)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(result.invalid_skipped, 1)
        self.assertEqual(result.output, normalized())

    def test_checked_recipient_lookup_survives_sorting(self):
        recipients = sample_recipients()
        recipients[0]["selected"] = True
        recipients[2]["selected"] = True

        filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "", "e164", SORT_PHONE, True)

        self.assertEqual(checked_recipient_indexes(recipients), [0, 2])

    def test_checked_recipient_lookup_survives_search_and_filter_refresh(self):
        recipients = sample_recipients()
        recipients[1]["selected"] = True

        self.assertEqual(filtered_recipient_indexes(recipients, "Caregivers", "morning"), [0])
        self.assertEqual(checked_recipient_indexes(recipients), [1])

    def test_checked_recipient_lookup_deduplicates_by_phone_number(self):
        recipients = sample_recipients()
        recipients.append({"phone": normalized(), "selected": True, "group": "Follow-up", "notes": ""})
        recipients[0]["selected"] = True

        self.assertEqual(checked_recipient_indexes(recipients), [0])

    def test_imported_recipients_receive_selected_group(self):
        rows = preview_pasted_recipients(f"Amy {raw_phone()}\nJohn {raw_phone('628')}")
        recipients = rows_to_add(rows, "Caregivers")

        self.assertEqual([recipient["group"] for recipient in recipients], ["Caregivers", "Caregivers"])
        self.assertNotIn("name", recipients[0])

    def test_import_with_missing_group_falls_back_to_default_on_save(self):
        rows = preview_pasted_recipients(raw_phone())
        saved = make_saved_data(rows_to_add(rows, ""), [])

        recipients, groups = parse_saved_data(saved)

        self.assertEqual(groups, [DEFAULT_GROUP])
        self.assertEqual(recipients[0]["group"], DEFAULT_GROUP)


if __name__ == "__main__":
    unittest.main()

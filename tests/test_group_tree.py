import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from app.dialogs import GroupNameDialog
from app.main import MainWindow
from app.storage import make_saved_data, parse_saved_settings, repair_saved_group_names
from core.group_tree import (
    add_group_record,
    children_of,
    group_scope_names,
    move_group_record,
    normalize_group_tree,
    record_by_name,
    remove_group_records,
    resolved_group_color,
    visible_group_records,
)
from core.groups import DEFAULT_GROUP, GROUP_COLOR_PALETTE, delete_group, filtered_recipient_indexes, group_name_error


class GroupTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_legacy_flat_groups_migrate_to_stable_top_level_records(self):
        first = normalize_group_tree([DEFAULT_GROUP, "Friends", "Work"])
        second = normalize_group_tree([DEFAULT_GROUP, "Friends", "Work"])

        self.assertTrue(all(record["parent_id"] is None for record in first))
        self.assertEqual([record["id"] for record in first], [record["id"] for record in second])

    def test_create_top_level_and_subgroup_but_reject_third_level(self):
        records = normalize_group_tree([DEFAULT_GROUP])
        parent = add_group_record(records, "Family")
        child = add_group_record(records, "Close Family", parent["id"])

        self.assertIsNotNone(parent)
        self.assertEqual(child["parent_id"], parent["id"])
        self.assertIsNone(add_group_record(records, "Too Deep", child["id"]))

    def test_group_names_are_unique_across_all_tree_levels(self):
        records = normalize_group_tree([DEFAULT_GROUP])
        first_parent = add_group_record(records, "A")
        second_parent = add_group_record(records, "B")
        self.assertIsNotNone(add_group_record(records, "Customer", first_parent["id"]))

        self.assertIsNone(add_group_record(records, "customer", first_parent["id"]))
        self.assertIsNone(add_group_record(records, " CUSTOMER ", second_parent["id"]))
        self.assertIsNone(add_group_record(records, "Customer", None))

    def test_group_name_conflicts_use_nfkc_unicode_normalization(self):
        records = normalize_group_tree([DEFAULT_GROUP])
        parent = add_group_record(records, "Parent")

        self.assertIsNotNone(add_group_record(records, "A组", parent["id"]))
        self.assertIsNone(add_group_record(records, "Ａ组", None))
        self.assertIsNotNone(add_group_record(records, "équipe", None))
        self.assertIsNone(add_group_record(records, "équipe", parent["id"]))

    def test_name_dialog_keeps_conflicting_input_and_focus(self):
        dialog = GroupNameDialog(
            None,
            title="New group",
            validator=lambda value: group_name_error(value, [DEFAULT_GROUP, "Friends"]),
        )
        self.addCleanup(dialog.close)
        dialog.show()
        self.app.processEvents()
        dialog.name_edit.setText(" friends ")

        dialog.validate_and_accept()
        self.app.processEvents()

        self.assertEqual(dialog.result(), QDialog.Rejected)
        self.assertEqual(dialog.name_edit.text(), " friends ")
        self.assertEqual(
            dialog.error_label.text(),
            'A group named "friends" already exists. Please choose a different name.',
        )
        self.assertTrue(dialog.name_edit.hasFocus())

    def test_legacy_duplicate_names_are_repaired_deterministically(self):
        data = {
            "groups": ["Clients", " clients ", "CLIENTS"],
            "recipients": [
                {"phone": "+14151111111", "groups": ["Clients"]},
                {"phone": "+16282222222", "groups": [" clients "]},
            ],
            "settings": {
                "group_tree": [
                    {"id": "one", "name": "Clients", "parent_id": None, "color": GROUP_COLOR_PALETTE[0]},
                    {"id": "two", "name": " clients ", "parent_id": None, "color": GROUP_COLOR_PALETTE[1]},
                    {"id": "three", "name": "CLIENTS", "parent_id": None, "color": GROUP_COLOR_PALETTE[2]},
                ]
            },
        }

        repaired, warnings = repair_saved_group_names(data)
        repeated, repeated_warnings = repair_saved_group_names(repaired)

        self.assertEqual(repaired["groups"], [DEFAULT_GROUP, "Clients", "clients (2)", "CLIENTS (3)"])
        self.assertEqual(repaired["recipients"][0]["groups"], ["Clients"])
        self.assertEqual(repaired["recipients"][1]["groups"], ["clients (2)"])
        self.assertEqual([record["name"] for record in repaired["settings"]["group_tree"]], repaired["groups"][1:])
        self.assertEqual(len(warnings), 2)
        self.assertEqual(repeated, repaired)
        self.assertEqual(repeated_warnings, [])

    def test_legacy_unicode_equivalent_names_are_repaired(self):
        data = {
            "groups": ["A组", "Ａ组", "équipe", "équipe"],
            "recipients": [
                {"phone": "+14151111111", "groups": ["Ａ组"]},
                {"phone": "+16282222222", "groups": ["équipe"]},
            ],
        }

        repaired, warnings = repair_saved_group_names(data)

        self.assertEqual(repaired["groups"], [DEFAULT_GROUP, "A组", "Ａ组 (2)", "équipe", "équipe (2)"])
        self.assertEqual(repaired["recipients"][0]["groups"], ["Ａ组 (2)"])
        self.assertEqual(repaired["recipients"][1]["groups"], ["équipe (2)"])
        self.assertEqual(len(warnings), 2)

    def test_subgroup_inherits_parent_color_until_overridden(self):
        records = normalize_group_tree([DEFAULT_GROUP])
        parent = add_group_record(records, "Family")
        child = add_group_record(records, "Close Family", parent["id"])
        parent["color"] = GROUP_COLOR_PALETTE[4]

        self.assertIsNone(child["color"])
        self.assertEqual(resolved_group_color(records, child["id"]), GROUP_COLOR_PALETTE[4])
        child["color"] = GROUP_COLOR_PALETTE[6]
        parent["color"] = GROUP_COLOR_PALETTE[2]
        self.assertEqual(resolved_group_color(records, child["id"]), GROUP_COLOR_PALETTE[6])

    def test_expand_state_and_tree_round_trip(self):
        records = normalize_group_tree([DEFAULT_GROUP, "Family"])
        record_by_name(records, "Family")["expanded"] = False
        settings = {"group_tree": records}
        parsed = parse_saved_settings(make_saved_data([], [DEFAULT_GROUP, "Family"], settings))
        restored = normalize_group_tree([DEFAULT_GROUP, "Family"], parsed["group_tree"])

        self.assertFalse(record_by_name(restored, "Family")["expanded"])

    def test_collapsed_parent_hides_children_without_deleting_them(self):
        records = normalize_group_tree([DEFAULT_GROUP, "Family", "Close Family"])
        parent = record_by_name(records, "Family")
        child = record_by_name(records, "Close Family")
        child["parent_id"] = parent["id"]
        parent["expanded"] = False

        visible_names = [record["name"] for record, _depth in visible_group_records(records)]
        self.assertNotIn("Close Family", visible_names)
        self.assertEqual(children_of(records, parent["id"]), [child])

    def test_parent_scope_aggregates_direct_and_child_members_without_duplicates(self):
        records = normalize_group_tree([DEFAULT_GROUP, "Family", "Close Family"])
        parent = record_by_name(records, "Family")
        child = record_by_name(records, "Close Family")
        child["parent_id"] = parent["id"]
        recipients = [
            {"phone": "+14151111111", "groups": ["Family", "Close Family"]},
            {"phone": "+16282222222", "groups": ["Close Family"]},
        ]

        indexes = filtered_recipient_indexes(recipients, group_scope_names(records, parent["id"]))
        self.assertEqual(indexes, [0, 1])
        self.assertEqual(filtered_recipient_indexes(recipients, ["Close Family"]), [0, 1])

    def test_rename_keeps_id_parent_and_color(self):
        records = normalize_group_tree([DEFAULT_GROUP, "Family", "Close Family"])
        parent = record_by_name(records, "Family")
        child = record_by_name(records, "Close Family")
        child["parent_id"] = parent["id"]
        before = (child["id"], child["parent_id"], child["color"])
        child["name"] = "Relatives"
        self.assertEqual((child["id"], child["parent_id"], child["color"]), before)

    def test_move_subgroup_to_another_parent_and_top_level(self):
        records = normalize_group_tree([DEFAULT_GROUP, "Family", "Work", "Close Family"])
        family = record_by_name(records, "Family")
        work = record_by_name(records, "Work")
        child = record_by_name(records, "Close Family")
        child["parent_id"] = family["id"]

        self.assertTrue(move_group_record(records, child["id"], work["id"]))
        self.assertEqual(child["parent_id"], work["id"])
        self.assertTrue(move_group_record(records, child["id"], None))
        self.assertIsNone(child["parent_id"])

    def test_delete_subgroup_and_parent_never_delete_recipient_records(self):
        records = normalize_group_tree([DEFAULT_GROUP, "Family", "Close Family"])
        parent = record_by_name(records, "Family")
        child = record_by_name(records, "Close Family")
        child["parent_id"] = parent["id"]
        recipients = [{"phone": "+14151111111", "groups": ["Family", "Close Family"]}]
        groups = [DEFAULT_GROUP, "Family", "Close Family"]

        remove_group_records(records, parent["id"], True)
        delete_group(recipients, groups, "Family")
        self.assertEqual(len(recipients), 1)
        self.assertIsNone(record_by_name(records, "Close Family")["parent_id"])

        delete_group(recipients, groups, "Close Family")
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]["groups"], [DEFAULT_GROUP])

    def test_delete_parent_and_subgroups_removes_only_memberships(self):
        records = normalize_group_tree([DEFAULT_GROUP, "Family", "Close Family"])
        parent = record_by_name(records, "Family")
        child = record_by_name(records, "Close Family")
        child["parent_id"] = parent["id"]
        recipients = [{"phone": "+14151111111", "groups": ["Family", "Close Family"]}]
        groups = [DEFAULT_GROUP, "Family", "Close Family"]

        removed = remove_group_records(records, parent["id"], False)
        for record in removed:
            delete_group(recipients, groups, record["name"])

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]["groups"], [DEFAULT_GROUP])
        self.assertIsNone(record_by_name(records, "Family"))
        self.assertIsNone(record_by_name(records, "Close Family"))

    def test_default_cannot_be_parent_and_cycles_are_rejected(self):
        records = normalize_group_tree([DEFAULT_GROUP, "Family"])
        default = record_by_name(records, DEFAULT_GROUP)
        family = record_by_name(records, "Family")
        self.assertIsNone(add_group_record(records, "Invalid", default["id"]))
        self.assertFalse(move_group_record(records, family["id"], family["id"]))

    def test_parent_and_child_selection_states_are_independent(self):
        groups = [DEFAULT_GROUP, "Family", "Close Family"]
        records = normalize_group_tree(groups)
        parent = record_by_name(records, "Family")
        record_by_name(records, "Close Family")["parent_id"] = parent["id"]
        settings = {
            "group_tree": records,
            "group_selections": {"Family": ["+14151111111"], "Close Family": ["+16282222222"]},
        }
        recipients = [
            {"phone": "+14151111111", "groups": ["Family"]},
            {"phone": "+16282222222", "groups": ["Close Family"]},
        ]
        with patch("app.main.load_recipient_data", return_value=(recipients, groups, settings, None)), patch(
            "app.main.save_recipient_data", return_value=None
        ):
            window = MainWindow()
        self.addCleanup(window.close)

        self.assertEqual(window.selected_phone_keys("Family"), {"+14151111111"})
        self.assertEqual(window.selected_phone_keys("Close Family"), {"+16282222222"})
        self.assertNotEqual(window.selected_phone_keys("Family"), window.selected_phone_keys("Close Family"))


if __name__ == "__main__":
    unittest.main()

# PourSend v2.3.0 — Nested Groups and Clearer Colors

PourSend v2.3.0 adds two-level group organization and clearer group colors while preserving recipient records and existing import and export formats.

## Nested Groups

- Create top-level groups and one level of subgroups.
- Expand and collapse parent groups; expansion state is saved automatically.
- Move subgroups between parent groups or promote them back to the top level.
- Rename groups without changing their hierarchy, colors, memberships, or selections.

## Clearer Group Colors

- Group icons and names now use the same muted group color.
- The previous low-visibility color dots have been removed.
- Subgroups can inherit their parent color or use an independently selected palette color.
- Display colors are adjusted automatically when needed to preserve readable contrast.

## Group Behavior

- Selecting a parent group shows its direct recipients and recipients from its subgroups.
- Aggregated parent views deduplicate recipients by normalized phone number.
- Parent groups and subgroups preserve independent checked-recipient selections.
- Deleting a group removes memberships without deleting recipients from All Recipients.

## Safer Group Names

- Group names are globally unique across top-level groups and subgroups.
- Name comparison ignores case and surrounding whitespace.
- Unicode NFKC normalization prevents visually equivalent names from being treated as different groups.
- The All Recipients and Default system names remain protected.

## Migration

- Legacy flat groups migrate automatically to top-level groups.
- Existing recipients, group colors, and group selections are preserved.
- Conflicting legacy names are repaired deterministically with `(2)`, `(3)`, and subsequent suffixes.
- Existing recipient and export formats remain compatible.

## Download

Download `PourSend-v2.3.0-Windows.zip`, extract the complete folder, and run `PourSend.exe`. Python is not required.

## Validation

- 224 automated tests passed.
- Compile and syntax checks passed.
- macOS PySide6 Cocoa GUI acceptance passed.
- Windows CI validates the build and executable startup; manual Windows visual validation has not yet been performed.

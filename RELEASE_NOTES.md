# PourSend v2.2.0 — Group Selection and Colors

PourSend v2.2.0 adds independent checked-recipient selections for each group and persistent muted group colors without changing recipient or export formats.

## What's New

- Each group remembers its own checked recipients when switching views.
- Select All and Clear Selection affect only visible results in the active group.
- Copy Selected and Delete Selected operate only on the active group's checked recipients.
- Existing and newly created groups receive persistent muted colors automatically.
- User-created groups can select any color from the existing eight-color palette.

## Improvements

- Group color assignments survive restart and transfer when groups are renamed.
- Deleted groups have their saved color assignments removed.
- The color chooser supports visible selection, hover and focus states, arrow-key navigation, and Escape cancellation.
- All Recipients remains fixed blue-gray, and Default cannot be manually recolored.
- Manual color changes preserve recipients, search state, active group, row highlighting, and group selections.

## Compatibility

- Existing settings are migrated automatically.
- Recipient records and the recipient data schema are unchanged.
- Import, CSV, copy, export, and backup formats are unchanged.
- Recipient data remains local.

## Download

Download `PourSend-v2.2.0-Windows.zip`, extract the complete folder, and run `PourSend.exe`. Python is not required.

## Validation

- 201 automated tests passed locally.
- Compile and syntax checks passed.
- Windows CI build and executable smoke-test results are verified before publication.

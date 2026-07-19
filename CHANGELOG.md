# Changelog

## v2.2.0 - 2026-07-19

### Group-Local Selection

- Stores checked-recipient state independently for each group.
- Restores each group's checked recipients when switching groups.
- Limits Select All and Clear Selection to visible results in the active group.
- Limits Copy Selected and Delete Selected to checked recipients in the active group.
- Preserves checked state while searching and keeps row highlighting independent.

### Group Colors

- Assigns persistent muted colors to existing and newly created groups.
- Preserves colors when groups are renamed and removes them when groups are deleted.
- Adds a compact Change Color chooser with eight palette colors.
- Supports mouse and keyboard color selection, including Escape cancellation.
- Keeps All Recipients fixed blue-gray and prevents manual recoloring of Default.

### Compatibility

- Migrates existing settings safely without changing recipient records.
- Preserves existing recipient, import, export, and backup formats.
- Keeps recipient data local.

## v2.0.0 - 2026-07-09

### Recipient Model

- Uses phone number as the recipient identity.
- Normalizes valid U.S. phone numbers to E.164 format.
- Detects duplicate normalized phone identities.
- Supports optional notes.
- Uses a single-group recipient model.
- Migrates supported older data schemas without requiring names or groups.

### Groups

- Includes a default group for unassigned or migrated recipients.
- Supports creating, renaming, and deleting user-created groups.
- Moves recipients between groups without deleting recipient records.

### Search and Display

- Searches instantly while typing.
- Matches phone numbers regardless of punctuation.
- Supports sorting by recently added order, phone number, or group.
- Supports ascending and descending sort direction.
- Displays phone numbers in selectable formats.

### Import

- Imports through Paste List.
- Imports TXT, CSV, and XLSX files.
- Extracts phone numbers from messy copied text.
- Supports multiple numbers on one line.
- Handles surrounding names, labels, and mixed text without saving names as identity.
- Shows an import preview before adding recipients.
- Reports invalid examples, existing numbers, and duplicate input entries.
- Supports drag-and-drop file import.
- Supports Undo Last Import.

### Copy and Export

- Copies displayed numbers, digits only, or E.164 numbers.
- Copies checked recipients or the current search.
- Exports TXT, CSV, and XLSX files.
- Supports export scopes for all recipients, current group, current search, and checked recipients.

### Backup

- Exports JSON backups.
- Imports JSON backups.
- Preserves backup version, recipients, groups, and settings.

### Productivity

- Supports batch editing checked recipients.
- Shows recipient statistics.
- Supports keyboard shortcuts that avoid overriding normal text-field editing.
- Saves automatically after data-changing workflows.
- Improves refresh behavior for large recipient lists.

### Polish and Safety

- Uses checked-recipient terminology consistently.
- Handles empty scopes with clear messages.
- Adds regression coverage for shortcut safety, import/export behavior, backups, grouping, and phone normalization.

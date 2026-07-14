# PourSend

[![Latest Release](https://img.shields.io/github/v/release/pour-soi/PourSend?style=flat-square&label=Latest%20Release)](https://github.com/pour-soi/PourSend/releases)
[![Windows](https://img.shields.io/badge/Windows-Desktop-0078D4?style=flat-square)](https://github.com/pour-soi/PourSend/releases/latest)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/pour-soi/PourSend/build-windows.yml?style=flat-square&label=Windows%20Build)](https://github.com/pour-soi/PourSend/actions/workflows/build-windows.yml)

<p align="center">
  <img src="assets/poursend-logo.png" alt="PourSend official logo" width="260">
</p>

Prepare recipient lists before sending.

A local-first Windows desktop application for intelligent recipient management with multi-group organization, fast copy workflows, and a responsive desktop UI.

Windows desktop app · Local-first data · Multi-group recipients · Fast copy/export workflow

![PourSend main window](assets/poursend-main-window.png)

*Main window with groups, search, filters, recipient table, and checked-recipient actions.*

PourSend does not send messages itself. You copy prepared recipient numbers from the app, paste them into RingCentral, and send manually.

This is an independent, unofficial utility and is not affiliated with or endorsed by RingCentral.

## Download

**Current release: v2.1.2**

1. Download `PourSend-v2.1.2-Windows.zip` from the [official v2.1.2 GitHub Release](https://github.com/pour-soi/PourSend/releases/tag/v2.1.2).
2. Extract the complete zip file to a normal folder, such as Desktop or Documents.
3. Run `PourSend.exe` from the extracted folder.

No installation is required. Do not run `PourSend.exe` directly from inside the zip file. Windows may block files or prevent PourSend from saving data where you expect until the package is fully extracted.

## Highlights

### Recipient Organization

- Assign one recipient to multiple groups at the same time.
- Add an existing phone number to another group without creating a duplicate record.
- Keep **All Recipients** deduplicated by normalized phone number.
- Delete groups without deleting the recipients inside them.
- Preserve checked-recipient workflows across search, filters, and groups.

### Smart Import

- Paste copied phone lists with **Paste List**.
- Import TXT, CSV, and XLSX files.
- Drag and drop TXT, CSV, or XLSX files into the app.
- Extract multiple numbers from one line.
- Extract numbers from mixed text, labels, and copied CRM-style content.
- Review an import preview before adding recipients.
- See new-recipient, added-to-group, already-in-group, duplicate-input, and invalid counts.
- Reuse existing recipient records when imported numbers already exist.
- Undo the most recent successful import.

### Fast Preparation Workflow

- Check recipients from any group they belong to.
- Copy checked recipients in the format you need.
- Export all recipients, the current group, the current search, or checked recipients.
- Batch edit checked recipients without leaving the main window.
- Save changes automatically after data-changing workflows.

### Copy & Export

- Copy displayed numbers, digits only, or E.164 numbers.
- Copy checked recipients or the current search results.
- Export TXT, CSV, or XLSX files.
- Export all recipients, the current group, the current search, or checked recipients.

### Search & Filtering

- Search instantly while typing.
- Search phone numbers regardless of punctuation.
- Sort by recently added order, phone number, or group.
- Choose ascending or descending sort direction.
- Display phone numbers in selectable formats.
- Keep current search and current selection deduplicated by phone number.

### Fluid Responsive Layout

- Resize the window smoothly without switching between separate desktop and compact layouts.
- Let the sidebar, search field, filters, table, buttons, margins, and spacing adapt continuously.
- Keep the recipient table usable with scrolling when space is limited.
- Avoid horizontal scrolling at common working sizes.

### Backup & Recovery

- Export JSON backups.
- Restore from JSON backups.
- Preserve recipients, groups, settings, and notes through the backup workflow.

### Productivity

- Batch edit checked recipients.
- View total recipients, current group count, current search count, stored duplicate count, and checked counts.
- Use keyboard shortcuts without overriding normal text-field editing.
- Save changes automatically after data-changing workflows.
- Work with large recipient lists more comfortably.

### Privacy

- Recipient data is stored locally.
- Data is created beside the portable app by default.
- The app does not require a cloud account.
- No telemetry is collected.
- There is no RingCentral API integration.
- There is no automatic message sending.

## Multi-Group Recipients

PourSend keeps phone number as the unique recipient identity. One recipient can belong to multiple groups at the same time.

Example:

```text
Phone:
+1 415 111 1111

Groups:
- Default
- Female Mandarin
- Follow Up
- VIP
```

- Adding `+1 415 111 1111` to another group does not create another recipient.
- The existing recipient simply gains another group membership.
- **All Recipients** still shows one recipient record for that phone number.
- Group views show the recipient in every group it belongs to.
- Deleting a group never deletes recipients.
- If all groups are removed from a recipient, PourSend automatically assigns `Default`.

## Screenshots

![PourSend main window](assets/poursend-main-window.png)

*Main window: local recipient management with groups, search, import, copy, export, and checked-recipient actions.*

TODO: Add future screenshots for:

- Multi-group management
- Import
- Export
- Search
- Responsive resizing GIF

## Brand Assets

`assets/poursend-logo.png` is the official PourSend logo and the source artwork for application icons. Do not redraw, recolor, crop, stretch, or reinterpret it. Scale it proportionally on clean backgrounds with comfortable whitespace.

## How To Use

### Basic Workflow

```text
Open app -> Choose a group or recipients -> Check recipients -> Copy numbers -> Paste into RingCentral -> Send manually
```

### Add Recipients

- Use **Add Recipient** to add one phone number manually.
- Use **Paste List** to paste copied text.
- Use **Import File** for TXT, CSV, or XLSX files.
- Drag and drop a supported file into the app.

Each valid phone number becomes a separate recipient unless that normalized phone number already exists.

Existing phone numbers are not duplicated. If an existing recipient is imported or added to a new group, PourSend adds that group membership to the existing recipient.

Names and surrounding labels in pasted or imported text are used only to help detect phone numbers. They are not saved as recipient identity.

During preview and import:

- Duplicate numbers inside the pasted batch are skipped.
- Phone numbers that already belong to the chosen group are skipped.
- Invalid phone numbers are skipped.
- Existing recipients are never overwritten.
- Supported older data schemas are migrated automatically.
- New recipient workflows do not require names.
- Newly added recipients and existing recipients added to a new group receive the chosen batch group.

### Groups

- Recipients can belong to one or more groups.
- Adding an existing phone number to a new group adds membership instead of creating a duplicate.
- Deleting a group does not delete the recipients inside it.
- Records without a valid group fall back to `Default`.
- You can open a group, search within that group, then select or deselect only the visible recipients in that group.

### Copy Numbers

Copy options include:

- **Displayed Number**
- **Digits Only**
- **E.164**
- **Checked Numbers**
- **Current Search**

Copied output is one number per line. Duplicate numbers are removed during copy, and invalid numbers are skipped.

### Export Data

Export formats:

- TXT
- CSV
- XLSX

Export scopes:

- All recipients
- Current group
- Current search
- Checked recipients

### Back Up And Restore

Use **Export Backup** to save a JSON backup.

Use **Import Backup** to restore recipients, groups, settings, and notes from a PourSend backup file.

## Keyboard Shortcuts

- `Ctrl+V`: open Paste List when focus is not in a text field.
- `Ctrl+F`: focus the search field.
- `Ctrl+A`: check all visible recipients when focus is not in a text field.
- `Ctrl+Z`: undo the most recent successful import when focus is not in a text field.
- `Delete`: delete checked recipients when focus is not in a text field.

## Data Storage

PourSend is portable and stores data locally.

When running the packaged Windows app, PourSend automatically creates this folder beside `PourSend.exe`:

```text
<PourSend folder>\poursend_data\
```

The folder contains:

- `recipients.json`: recipients, groups, notes, selected state, and related recipient data.
- `settings.json`: window size, position, maximized state, and application preferences.

The folder is portable. To move PourSend to another computer, copy the extracted PourSend folder together with `poursend_data`.

When running from source, PourSend uses:

```text
<repository root>\poursend_data\
```

If the primary folder is not writable, PourSend falls back to:

```text
%USERPROFILE%\.poursend_data\
```

Use **Export Backup** before moving PourSend to a different folder or computer. Backup files are user-chosen JSON files and are separate from the automatic local data folder.

## Upgrading

- Older databases are migrated automatically when PourSend starts.
- Legacy single-group records are converted to multi-group records.
- Existing phone numbers, groups, notes, selected state, and settings are preserved.
- Recipients without a valid group are assigned to `Default`.
- Before upgrading, create a backup with **Export Backup** or copy the `poursend_data` folder.

## Troubleshooting

### Windows SmartScreen

PourSend is distributed as an unsigned portable Windows executable. Windows may show a SmartScreen warning the first time you run it. Only continue if you downloaded the zip from the official GitHub Release page.

### Missing Or Blocked Executable

If `PourSend.exe` is missing, blocked, or fails to open:

- Extract the entire zip before running the app.
- Keep `PourSend.exe`, `README.md`, and `LICENSE` together in the extracted folder.
- Check whether Windows Security or another antivirus tool quarantined the executable.
- If Windows marks the file as downloaded from the internet, open file properties and unblock it.

### Data Not Found

Check the data locations above. If you moved the app folder, the original `poursend_data` folder may still be next to the previous copy of `PourSend.exe`.

### Display Scaling

PourSend is tested at common Windows scaling levels, including 100%, 125%, and 150%. If the interface looks clipped after changing display scaling, close and reopen the app.

### Report An Issue

Use [GitHub Issues](https://github.com/pour-soi/PourSend/issues) for bug reports and feature requests. Include your PourSend version, Windows version, display scaling, what you expected, what happened, and a screenshot when useful.

## Running From Source

On Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

On macOS or Linux for development:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Testing

Run the automated test suite:

```powershell
python -m unittest
```

The current suite has 154 tests covering phone normalization, copy behavior, paste parsing, CSV detection, grouping, storage migration, batch phone-number import, search, sorting, phone display formatting, export formats, export scopes, backup import/export, shortcut safety, release versioning, storage path branding, and responsive layout behavior.

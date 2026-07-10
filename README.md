# PourSend

A local Windows desktop utility for organizing recipients, batch-importing phone numbers, and copying checked recipient numbers for manual use with RingCentral.

[![Latest Release](https://img.shields.io/github/v/release/pour-soi/PourSend?label=latest%20release)](https://github.com/pour-soi/PourSend/releases/tag/v2.0.0)
![Windows](https://img.shields.io/badge/platform-Windows-0078D4)
![Tests](https://img.shields.io/badge/tests-134%20passing-brightgreen)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Portable Windows app · Local data · No telemetry

![PourSend main window](assets/poursend-main-window.png)

PourSend does not send messages itself. You copy prepared recipient numbers from the app, paste them into RingCentral, and send manually.

This is an independent, unofficial utility and is not affiliated with or endorsed by RingCentral.

## Download

**Current release: v2.0.0**

1. Download `PourSend-v2.0.0-Windows.zip` from the [official v2.0.0 GitHub Release](https://github.com/pour-soi/PourSend/releases/tag/v2.0.0).
2. Extract the zip.
3. Run `PourSend.exe`.

No installation is required.

## Highlights

### Smart Import

- Paste copied phone lists with **Paste List**.
- Import TXT, CSV, and XLSX files.
- Drag and drop TXT, CSV, or XLSX files into the app.
- Extract multiple numbers from one line.
- Extract numbers from mixed text, labels, and copied CRM-style content.
- Review an import preview before adding recipients.
- See duplicate, already-existing, and invalid counts.
- Undo the most recent successful import.

### Search & Organization

- Organize recipients into groups.
- Search instantly while typing.
- Search phone numbers regardless of punctuation.
- Sort by recently added order, phone number, or group.
- Choose ascending or descending sort direction.
- Display phone numbers in selectable formats.
- Use checked-recipient workflows for copy, export, group membership, and batch edit actions.

### Copy & Export

- Copy displayed numbers, digits only, or E.164 numbers.
- Copy checked recipients or the current search results.
- Export TXT, CSV, or XLSX files.
- Export all recipients, the current group, the current search, or checked recipients.

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
- The app does not require a cloud account.
- No telemetry is collected.
- There is no RingCentral API integration.
- There is no automatic message sending.

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

A recipient can belong to one or more groups. Records without a valid group fall back to `Default`.

Deleting a group does not delete the recipients inside it. Recipients with no remaining valid groups fall back to `Default`.

You can open a group, search within that group, then select or deselect only the visible recipients in that group.

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

## Data Location

The app tries to save recipients in:

```text
poursend_data/recipients.json
```

next to the running app. If that location is not writable, it saves under the current Windows user profile.

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

The current suite has 134 tests covering phone normalization, copy behavior, paste parsing, CSV detection, grouping, storage migration, batch phone-number import, search, sorting, phone display formatting, export formats, export scopes, backup import/export, shortcut safety, release versioning, and storage path branding.

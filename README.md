# PourSend

<p align="center">
  <img src="assets/poursend-logo.png" alt="PourSend official logo" width="260">
</p>

A local Windows desktop utility for organizing recipients, batch-importing phone numbers, and copying checked recipient numbers for manual use with RingCentral.

[![Latest Release](https://img.shields.io/github/v/release/pour-soi/PourSend?label=latest%20release)](https://github.com/pour-soi/PourSend/releases/tag/v2.1.2)
![Windows](https://img.shields.io/badge/platform-Windows-0078D4)
![Tests](https://img.shields.io/badge/tests-154%20passing-brightgreen)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Portable Windows app · Local data · No telemetry

![PourSend main window](assets/poursend-main-window.png)

PourSend does not send messages itself. You copy prepared recipient numbers from the app, paste them into RingCentral, and send manually.

This is an independent, unofficial utility and is not affiliated with or endorsed by RingCentral.

## Download

**Current release: v2.1.2**

1. Download `PourSend-v2.1.2-Windows.zip` from the [official v2.1.2 GitHub Release](https://github.com/pour-soi/PourSend/releases/tag/v2.1.2).
2. Extract the complete zip file to a normal folder, such as Desktop or Documents.
3. Run `PourSend.exe` from the extracted folder.

No installation is required. Do not run `PourSend.exe` directly from inside the zip file. Windows may block files or prevent PourSend from saving data where you expect until the package is fully extracted.

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

PourSend is portable and stores data locally.

When running the packaged Windows app, the primary data file is:

```text
<folder containing PourSend.exe>\poursend_data\recipients.json
```

When running from source, the primary data file is:

```text
<repository root>\poursend_data\recipients.json
```

If the primary folder is not writable, PourSend falls back to:

```text
%USERPROFILE%\.poursend_data\recipients.json
```

Use **Export Backup** before moving PourSend to a different folder or computer. Backup files are user-chosen JSON files and are separate from the automatic local data file.

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

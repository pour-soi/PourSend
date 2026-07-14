# PourSend

<p align="center">
  <img src="assets/poursend-logo.png" alt="PourSend official logo" width="260">
</p>

[![Latest Release](https://img.shields.io/github/v/release/pour-soi/PourSend?style=flat-square&label=Latest%20Release)](https://github.com/pour-soi/PourSend/releases)
[![Windows](https://img.shields.io/badge/Windows-Desktop-0078D4?style=flat-square)](https://github.com/pour-soi/PourSend/releases/latest)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/pour-soi/PourSend/build-windows.yml?style=flat-square&label=Windows%20Build)](https://github.com/pour-soi/PourSend/actions/workflows/build-windows.yml)

Prepare recipient lists before sending.

A local-first Windows desktop application for intelligent recipient management with multi-group organization, fast copy workflows, and a responsive desktop UI.

Windows desktop app · Local-first data · Multi-group recipients · Fast copy/export workflow

PourSend does not send messages itself. You copy prepared recipient numbers from the app, paste them into RingCentral, and send manually.

This is an independent, unofficial utility and is not affiliated with or endorsed by RingCentral.

## Download

**Current release: v2.1.2**

1. Download `PourSend-v2.1.2-Windows.zip` from the [official v2.1.2 GitHub Release](https://github.com/pour-soi/PourSend/releases/tag/v2.1.2).
2. Extract the complete zip file to a normal folder, such as Desktop or Documents.
3. Run `PourSend.exe` from the extracted folder.

No installation is required. Do not run `PourSend.exe` directly from inside the zip file.

## Key Features

- **Multi-group recipients:** One phone number can belong to multiple groups without duplicate recipient records.
- **Intelligent duplicate detection:** Existing numbers are reused during add, paste, and import workflows.
- **Fast recipient preparation:** Check recipients, copy numbers, export lists, and batch edit group membership from the main window.
- **Smart import:** Paste text or import TXT, CSV, and XLSX files with preview counts for new, existing, invalid, and duplicate-input numbers.
- **Search and filtering:** Search while typing, search through formatted phone numbers, sort views, and keep selections deduplicated.
- **Fluid responsive layout:** Sidebar, filters, search, table, margins, and actions resize continuously with the window.
- **Local-first privacy:** Recipient data is stored locally, with no telemetry, cloud account, RingCentral API integration, or automatic message sending.
- **Backup and restore:** Export and restore JSON backups for recipients, groups, settings, and notes.

## Screenshots

![PourSend main window](assets/poursend-main-window.png)

*Main window with groups, search, filters, recipient table, and checked-recipient actions.*

TODO: Add future screenshots for:

- Multi-group management
- Import
- Export / copy
- Search and filtering
- Responsive resizing GIF

## Multi-Group Recipients

PourSend keeps phone number as the unique recipient identity. A recipient can belong to multiple groups at the same time.

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

- Adding `+1 415 111 1111` to another group adds membership to the existing recipient.
- **All Recipients** still shows one recipient record for that phone number.
- Group views show the recipient in every group it belongs to.
- Deleting a group never deletes recipients.
- If all groups are removed from a recipient, PourSend automatically assigns `Default`.

## How To Use

### Basic Workflow

```text
Open app -> Choose a group or recipients -> Check recipients -> Copy numbers -> Paste into RingCentral -> Send manually
```

### Add Or Import Recipients

- Use **Add Recipient** to add one phone number manually.
- Use **Paste List** to paste copied text.
- Use **Import File** for TXT, CSV, or XLSX files.
- Drag and drop a supported file into the app.

During preview and import:

- New phone numbers create recipient records.
- Existing phone numbers are not duplicated.
- Existing recipients can be added to the chosen group.
- Duplicate numbers inside the input are skipped.
- Invalid phone numbers are skipped.
- The most recent successful import can be undone.

### Copy Or Export Numbers

Copy formats:

- Displayed number
- Digits only
- E.164

Copy and export scopes:

- Checked recipients
- Current search
- Current group
- All recipients

Exports support TXT, CSV, and XLSX.

### Back Up, Restore, And Upgrade

- Use **Export Backup** to save a JSON backup.
- Use **Import Backup** to restore recipients, groups, settings, and notes.
- Older databases are migrated automatically when PourSend starts.
- Legacy single-group records are converted to multi-group records.
- Before upgrading, create a backup or copy the `poursend_data` folder.

## Data Storage

PourSend is portable and stores data locally.

When running the packaged Windows app, PourSend automatically creates this folder beside `PourSend.exe`:

```text
<PourSend folder>\poursend_data\
```

The folder contains:

- `recipients.json`: recipients, groups, notes, selected state, and related recipient data.
- `settings.json`: window size, position, maximized state, and application preferences.

To move PourSend to another computer, copy the extracted PourSend folder together with `poursend_data`.

When running from source, PourSend uses:

```text
<repository root>\poursend_data\
```

If the primary folder is not writable, PourSend falls back to:

```text
%USERPROFILE%\.poursend_data\
```

## Keyboard Shortcuts

- `Ctrl+V`: open Paste List when focus is not in a text field.
- `Ctrl+F`: focus the search field.
- `Ctrl+A`: check all visible recipients when focus is not in a text field.
- `Ctrl+Z`: undo the most recent successful import when focus is not in a text field.
- `Delete`: delete checked recipients when focus is not in a text field.

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

## Development

Run from source on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Run from source on macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Run the automated test suite:

```powershell
python -m unittest
```

The current suite has 154 tests covering phone normalization, copy behavior, paste parsing, CSV detection, grouping, storage migration, batch import, search, sorting, export formats, backup import/export, shortcut safety, release versioning, storage path branding, and responsive layout behavior.

Design guidance lives in [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md).

## License

PourSend is released under the [MIT License](LICENSE).

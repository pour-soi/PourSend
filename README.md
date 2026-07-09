# PourSend

PourSend is a local Windows desktop utility for organizing recipients, batch-importing phone numbers, and copying selected recipient numbers for use with RingCentral.

The application does not send messages itself. You copy prepared recipient numbers from the app, paste them into RingCentral, and send manually.

This is an independent, unofficial utility and is not affiliated with or endorsed by RingCentral.

## Core Workflow

```text
Open app -> Choose a group or recipients -> Select recipients -> Copy numbers -> Paste into RingCentral -> Send manually
```

Batch import workflow:

```text
Copy many phone numbers -> Paste List -> Review preview -> Add All Recipients -> Select group -> Copy
```

## Features

- Add, edit, and delete recipients.
- Search by phone number or notes.
- Organize recipients into groups.
- Move recipients between groups.
- View `All Recipients`.
- Search within the currently selected group.
- Select all visible recipients with `Select All in This Group`.
- Deselect all visible recipients with `Deselect All in This Group`.
- Import through `Paste List`.
- Paste phone-only batches.
- Paste phone numbers from name + phone rows while ignoring names for saved recipients.
- Import TXT, CSV, and XLSX files with supported phone-number formats.
- Assign a pasted batch to one existing group.
- Detect duplicates inside a pasted batch.
- Detect phone numbers that already exist.
- Detect invalid phone numbers before import.
- Store optional notes for recipients.
- Save recipients and groups locally between launches.
- Export a backup.
- Clear all data with confirmation.
- Normalize valid US phone numbers to `+1XXXXXXXXXX`.
- Copy only checked recipients.
- Remove duplicate numbers during copy.
- Skip invalid numbers during copy.
- Copy as comma-separated output.
- Copy as semicolon-separated output.
- Copy as one number per line.

## Batch Import Behavior

Each valid phone number in a pasted batch becomes a separate recipient unless that normalized phone number already exists.

Names and surrounding labels in pasted or imported text are used only to help detect phone numbers. They are not saved as recipient identity.

During preview and import:

- Duplicate numbers inside the pasted batch are skipped.
- Phone numbers that already exist in the recipient list are skipped.
- Invalid phone numbers are skipped.
- Existing recipients are never overwritten.
- Existing legacy names are preserved for compatibility, but new recipient workflows do not require names.
- Only newly added recipients receive the selected batch group.

## Groups

A recipient belongs to one group. Records without a valid group fall back to `Default`.

Deleting a group does not delete the recipients inside it. It moves those recipients to `Default`.

You can open a group, search within that group, then select or deselect only the visible recipients in that group.

## Privacy

PourSend is local-only.

- All recipient data is stored locally.
- The application makes no network requests.
- No analytics are collected.
- No telemetry is collected.
- No cloud syncing is used.
- No contact syncing is used.
- There is no RingCentral API integration.
- There is no automatic message sending.

## Installation / Running From Source

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

## Portable Windows Build

This repository includes a manual GitHub Actions workflow that builds:

```text
PourSend.exe
```

To build it:

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Select **Build PourSend Windows executable**.
4. Click **Run workflow**.
5. Run the workflow on `main`.
6. When it finishes, download the `PourSend-Windows` artifact.
7. Extract `PourSend.exe`.

This is a portable executable, not an official signed installer.

## Testing

Run the automated test suite:

```powershell
python -m unittest
```

The current suite has 69 tests covering phone normalization, copy behavior, paste parsing, CSV detection, grouping, storage migration, and batch phone-number import.

## Data Location

The app tries to save recipients in:

```text
ringcentral_recipient_prep_data/recipients.json
```

next to the running app. If that location is not writable, it saves under the current Windows user profile.

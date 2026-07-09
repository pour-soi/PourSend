# RingCentral Recipient Prep

A small local Windows desktop utility for preparing multiple recipient phone numbers for RingCentral.

The app helps you maintain a local list of names and phone numbers, select recipients, clean and validate US phone numbers, remove duplicates, and copy the selected numbers to the clipboard. You then paste the numbers into RingCentral yourself.

This app never sends messages and does not connect to RingCentral.

## Privacy

- Runs locally on your computer.
- Stores recipients in a local JSON file only.
- Makes no network requests.
- Has no analytics or telemetry.
- Does not sync contacts.
- Does not automate RingCentral, browsers, clicking, typing, or sending.

## Features

- Add, edit, delete, search, select all, and deselect all recipients.
- Paste a list and preview what will be imported.
- Import CSV files with common name and phone column names.
- Choose clipboard output format: comma-separated, semicolon-separated, or one number per line.
- Normalize valid US numbers to `+1XXXXXXXXXX`.
- Skip invalid numbers and remove duplicates during copy.
- Export a JSON backup and clear all data with confirmation.

## Run From Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Run Tests

```powershell
python -m unittest
```

## Build A Portable Windows App

From Windows, install PyInstaller in the virtual environment:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name RingCentralRecipientPrep main.py
```

The portable executable will be created under `dist\RingCentralRecipientPrep.exe`.

No administrator privileges or installer are required. Keep the executable in a normal writable folder so the app can save its local JSON data next to the app. If that folder is not writable, it falls back to a local user folder.

## Data Location

The app tries to save recipients in:

```text
ringcentral_recipient_prep_data/recipients.json
```

next to the running app. If that location is not writable, it saves under the current Windows user profile.

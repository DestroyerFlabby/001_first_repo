# Creator Clipping Setup

Use these steps from a clean Windows terminal to create a local Python environment for the creator clipping pipeline.

## 1. Open The Project Folder

From the repository root:

```powershell
cd CREATOR_CLIPPING_BUSINESS
```

## 2. Create A Virtual Environment

```powershell
python -m venv .venv
```

If `python` is not found, install Python for Windows and make sure "Add Python to PATH" is enabled, or use:

```powershell
py -m venv .venv
```

## 3. Activate The Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, allow scripts for the current user:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 4. Install Requirements

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This installs the dependencies used by the current automation scripts:

- `requests`
- `python-dotenv`
- `yt-dlp`

## 5. Verify The Commands

Run these from inside `CREATOR_CLIPPING_BUSINESS` after activating the virtual environment:

```powershell
python AUTOMATION\batch_download.py --help
python AUTOMATION\run_pipeline.py --help
python AUTOMATION\tts_generate.py --help
```

Each command should print usage text and exit without an import error.

## Troubleshooting

### `ModuleNotFoundError: No module named 'requests'`

The virtual environment is not activated, or requirements were not installed in the active environment.

Run:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python AUTOMATION\tts_generate.py --help
```

### `ModuleNotFoundError: No module named 'yt_dlp'`

Install requirements in the active environment:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -c "import yt_dlp; print('yt_dlp ok')"
```

### `python` Uses The Wrong Environment

Confirm the active Python path:

```powershell
where python
python -m pip --version
```

The first `python` path should point to:

```text
CREATOR_CLIPPING_BUSINESS\.venv\Scripts\python.exe
```

### API Keys

Do not put real API keys in this file or in Git. Voiceover generation can run in stub mode without an API key. Use `.env` locally for private settings when needed.

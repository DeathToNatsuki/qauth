# QAUTH v1.0.0

Initial release.

## Download

`qauth-v1.0.0.zip` (attached below) contains a single prebuilt Windows binary, `qauth.exe`. Extract the zip and run `qauth.exe` — no Python or install required. A `Vaults/` folder will be created next to it automatically.

## Features

- Terminal 2FA authenticator with a purple, arrow-key-driven UI
- Live TOTP codes for every account, auto-refreshing every second with a countdown bar — no interaction needed once logged in
- Multiple vaults, each stored as a single portable `Vaults/<name>.qauth` file
- Vault picker on launch: open an existing vault, create a new one, or switch vaults from inside the dashboard (`v` key)
- Local encryption: PBKDF2-HMAC-SHA256 (600,000 iterations) + Fernet (AES-128-CBC + HMAC), unique random salt per vault
- Add/delete accounts from the dashboard (`a` / `d`)
- Idle spinner and unlock animation
- `Vaults/` folder created next to the script or built `.exe` — including single-file `--onefile` builds, which resolve their real launcher path so vault data doesn't end up in a temp folder

## Requirements

- Python 3.9+
- `pyotp`, `cryptography` (`windows-curses` on Windows only)

See `requirements.txt` and the README for install and usage instructions.

## Building the .exe

Nuitka is recommended over PyInstaller for this release — it compiles to a real native binary, giving faster startup and far fewer antivirus false positives:

```
pip install nuitka
python -m nuitka --onefile --windows-console-mode=force --assume-yes-for-downloads --output-dir=dist qauth.py
```

See the README's "Building a standalone .exe" section for the PyInstaller alternative and troubleshooting.

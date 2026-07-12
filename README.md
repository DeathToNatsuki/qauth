# QAUTH

A terminal-based 2FA authenticator. Purple UI, arrow-key navigation, live TOTP codes, multiple encrypted vaults.

No mouse, no clicking — log in once and every code on screen refreshes itself every second until you tell it to do something else.

## Features

- **Live TOTP codes** for all your accounts, auto-refreshing every second with a countdown bar
- **Multiple vaults** — switch between them from the picker screen, each one a single portable `.qauth` file
- **Strong local encryption** — PBKDF2-HMAC-SHA256 (600,000 iterations) + Fernet (AES-128-CBC + HMAC), nothing ever leaves your machine
- **Arrow-key navigation** throughout — no mouse required
- **Animated UI** — spinners, unlock animation, and a live countdown bar, all in purple
- Fully portable vaults: copy/move the `.qauth` file anywhere, no separate export/import step

## Download (prebuilt Windows binary)

Grab `qauth-v1.0.0.zip` from the [Releases page](https://github.com/DeathToNatsuki/qauth/releases), extract it anywhere, and run `qauth.exe` from inside the extracted folder. A `Vaults/` folder will be created right next to it the first time you make a vault. No install, no Python required.

## Installation (from source)

```bash
git clone https://github.com/DeathToNatsuki/qauth.git
cd qauth
pip install -r requirements.txt
python qauth.py
```

Windows users additionally need `windows-curses`, which is already listed in `requirements.txt` and will install automatically on Windows.

## Usage

On first run you'll land on the **vault picker**:

| Key | Action |
|---|---|
| `↑` / `↓` | Select a vault |
| `Enter` | Open the selected vault |
| `n` | Create a new vault (prompts for name, then a master password) |
| `q` | Quit |

Once inside a vault (the **dashboard**), codes refresh automatically — you don't need to press anything:

| Key | Action |
|---|---|
| `↑` / `↓` | Select an account |
| `a` | Add an account (issuer, name, base32 secret) |
| `d` | Delete the selected account |
| `v` | Lock and switch to another vault |
| `q` | Quit |

## Vault files

Each vault lives in a `Vaults/` folder created next to `qauth.py` (or the built `.exe`), as `Vaults/<name>.qauth`. It's a single self-contained JSON file holding a random salt and the encrypted account list — copy it, back it up, or move it to another machine and it'll just work with its password.

## Building a standalone .exe

**Recommended: Nuitka.** It compiles to a real native binary instead of just bundling the interpreter, which means faster startup and far fewer antivirus false positives than PyInstaller — worth it for a security/vault tool.

```bash
pip install nuitka
python -m nuitka --onefile --windows-console-mode=force --assume-yes-for-downloads --output-dir=dist qauth.py
```

This produces a single `dist/qauth.exe`. Onefile builds normally run from a temp folder, which would break "Vaults next to the exe" — the code works around this on Windows/Linux by resolving the real launcher path via Nuitka's `NUITKA_ONEFILE_PARENT`, so `Vaults/` still ends up next to the actual `qauth.exe`, not a temp copy. (If you ever build with `--standalone` instead, that also works and needs no such workaround.)

If it complains about missing modules, add `--include-package=cryptography --include-module=_curses`.

**Alternative: PyInstaller** (simpler, but more prone to AV false positives on onefile builds):

```bash
pip install pyinstaller
pyinstaller --onefile --console --name qauth qauth.py
```

The `Vaults/` folder is created next to wherever the `.exe` (or script) is running from, so this works the same whether you run it as a script or a frozen binary. If PyInstaller can't find the crypto backend, add `--hidden-import=cryptography.hazmat.backends.openssl.backend`.

## Security notes

- Master password never leaves memory in plaintext and is never stored — only used to derive the encryption key each time you open a vault.
- Each vault has its own random 16-byte salt.
- QAUTH doesn't sync or phone home anywhere. Losing your password means losing the vault — there is no recovery by design.

## License

MIT — see [LICENSE](LICENSE).

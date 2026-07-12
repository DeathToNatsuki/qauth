#!/usr/bin/env python3
"""QAUTH - purple terminal 2FA authenticator. Multi-vault, arrow-key nav, live codes."""
import curses, os, sys, json, base64, time, secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import pyotp

def _base_dir():
    if getattr(sys, "frozen", False):            # PyInstaller
        return os.path.dirname(sys.executable)
    if "__compiled__" in globals():               # Nuitka (build with --standalone, not --onefile)
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))

VAULT_DIR = os.path.join(_base_dir(), "Vaults")
EXT = ".qauth"
ITER = 600_000
SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# ---------- crypto / storage ----------
def derive_key(password, salt):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def _write(path, salt, token):
    d = {"salt": base64.b64encode(salt).decode(), "data": base64.b64encode(token).decode()}
    with open(path, "w") as fh:
        json.dump(d, fh)

def create_vault(path, password):
    salt = secrets.token_bytes(16)
    f = Fernet(derive_key(password, salt))
    _write(path, salt, f.encrypt(json.dumps([]).encode()))

def load_vault(path, password):
    with open(path) as fh:
        d = json.load(fh)
    salt = base64.b64decode(d["salt"])
    f = Fernet(derive_key(password, salt))
    accounts = json.loads(f.decrypt(base64.b64decode(d["data"])).decode())
    return accounts, salt

def save_vault(path, accounts, password, salt):
    f = Fernet(derive_key(password, salt))
    _write(path, salt, f.encrypt(json.dumps(accounts).encode()))

def list_vaults():
    os.makedirs(VAULT_DIR, exist_ok=True)
    return sorted(f for f in os.listdir(VAULT_DIR) if f.endswith(EXT))

def sanitize(name):
    safe = "".join(c for c in name if c.isalnum() or c in "-_ ").strip().replace(" ", "_")
    return safe or "vault"

# ---------- colors ----------
def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_MAGENTA, -1)                     # primary (bold = bright)
    curses.init_pair(3, curses.COLOR_MAGENTA, -1)                     # accents / codes
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)                     # secondary/help (non-bold)
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)                     # selection marker bar

P = lambda: curses.color_pair(1) | curses.A_BOLD          # bright purple
PDIM = lambda: curses.color_pair(4)                        # dim purple, secondary text
MARK = lambda: curses.color_pair(6) | curses.A_BOLD        # selection marker bar

def draw_row(stdscr, y, x, text, selected, maxw):
    bar = "▌" if selected else " "
    stdscr.addstr(y, x, bar, MARK())
    stdscr.addstr(y, x + 2, text[: max(0, maxw - 2)], P())

# ---------- ui helpers ----------
def draw_frame(stdscr, title, tick):
    h, w = stdscr.getmaxyx()
    stdscr.attron(P())
    stdscr.border()
    stdscr.addstr(0, max(2, (w - len(title)) // 2), f" {title} ")
    spin = SPIN[(tick // 2) % len(SPIN)]
    if w > 6:
        stdscr.addstr(0, w - 4, spin)
    stdscr.attroff(P())

def animate_unlock(stdscr, label="Unlocking vault"):
    h, w = stdscr.getmaxyx()
    for i in range(12):
        stdscr.addstr(h // 2, max(0, w // 2 - len(label) // 2),
                       f"{label} {SPIN[i % len(SPIN)]}", P())
        stdscr.refresh()
        time.sleep(0.05)

def get_string(stdscr, y, x, prompt, mask=False):
    curses.curs_set(1)
    stdscr.timeout(-1)
    buf = ""
    h, w = stdscr.getmaxyx()
    while True:
        stdscr.addstr(y, x, prompt + " " * max(0, w - x - len(prompt) - 1), PDIM())
        shown = "*" * len(buf) if mask else buf
        stdscr.addstr(y, x + len(prompt) + 1, shown[:max(0, w - x - len(prompt) - 2)], P())
        stdscr.move(y, min(w - 1, x + len(prompt) + 1 + len(buf)))
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (10, 13):
            break
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif ch == 27:
            curses.curs_set(0)
            return None
        elif 32 <= ch <= 126:
            buf += chr(ch)
    curses.curs_set(0)
    return buf

# ---------- vault picker (select / create / switch) ----------
def vault_picker(stdscr):
    idx, tick = 0, 0
    stdscr.timeout(150)
    curses.curs_set(0)
    while True:
        vaults = list_vaults()
        stdscr.erase()
        draw_frame(stdscr, "QAUTH", tick)
        h, w = stdscr.getmaxyx()
        if not vaults:
            stdscr.addstr(3, 2, "No vaults yet. Press 'n' to create one.", PDIM())
        else:
            for i, v in enumerate(vaults):
                draw_row(stdscr, 3 + i, 2, v[: -len(EXT)], i == idx, w - 4)
        stdscr.addstr(h - 2, 2, "↑/↓ select  Enter open  n new vault  q quit"[: w - 4], PDIM())
        stdscr.refresh()
        ch = stdscr.getch()
        tick += 1
        if ch == -1:
            continue
        elif ch == curses.KEY_UP:
            idx = max(0, idx - 1)
        elif ch == curses.KEY_DOWN:
            idx = min(len(vaults) - 1, idx + 1) if vaults else 0
        elif ch in (10, 13) and vaults:
            return "open", os.path.join(VAULT_DIR, vaults[idx])
        elif ch in (ord('n'), ord('N')):
            name = get_string(stdscr, h - 4, 2, "New vault name:")
            stdscr.timeout(150)
            if name:
                path = os.path.join(VAULT_DIR, sanitize(name) + EXT)
                if not os.path.exists(path):
                    return "new", path
        elif ch in (ord('q'), ord('Q')):
            sys.exit(0)

def register_flow(stdscr, path):
    stdscr.timeout(-1)
    draw_frame(stdscr, "QAUTH - NEW VAULT", 0)
    stdscr.addstr(2, 2, "Set a master password (min 6 chars).", PDIM())
    while True:
        p1 = get_string(stdscr, 4, 2, "New password:", mask=True)
        if p1 is None:
            return None
        p2 = get_string(stdscr, 6, 2, "Confirm password:", mask=True)
        if p2 is None:
            return None
        if p1 == p2 and len(p1) >= 6:
            return p1
        stdscr.addstr(8, 2, "Mismatch or too short - try again.", P())

def login_flow(stdscr, path):
    stdscr.timeout(-1)
    draw_frame(stdscr, "QAUTH - LOGIN", 0)
    while True:
        pw = get_string(stdscr, 3, 2, "Master password (Esc = back):", mask=True)
        if pw is None:
            return None
        try:
            accounts, salt = load_vault(path, pw)
            return accounts, salt, pw
        except Exception:
            stdscr.addstr(5, 2, "Wrong password. Try again.", P())

# ---------- dashboard ----------
def dashboard(stdscr, accounts, password, salt, path):
    idx, msg, tick = 0, "", 0
    stdscr.timeout(200)
    curses.curs_set(0)
    while True:
        now = time.time()
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        draw_frame(stdscr, "QAUTH", tick)
        if not accounts:
            stdscr.addstr(3, 2, "No accounts yet. Press 'a' to add one.", PDIM())
        else:
            remaining = 30 - int(now % 30)
            for i, acc in enumerate(accounts):
                code = pyotp.TOTP(acc["secret"]).now()
                line = f"{acc['issuer'][:14]:<15}{acc['name'][:14]:<15}{code[:3]} {code[3:]}"
                draw_row(stdscr, 3 + i, 2, line, i == idx, w - 4)
            bar_w = 20
            filled = int(bar_w * remaining / 30)
            bar = "█" * filled + "░" * (bar_w - filled)
            stdscr.addstr(4 + len(accounts), 2, f"[{bar}] {remaining:2d}s", P())
        if msg:
            stdscr.addstr(h - 3, 2, msg[: w - 4], PDIM())
        stdscr.addstr(h - 2, 2, "↑/↓ select  a add  d delete  v switch vault  q quit"[: w - 4], PDIM())
        stdscr.refresh()
        ch = stdscr.getch()
        tick += 1
        msg = ""
        if ch == -1:
            continue
        elif ch == curses.KEY_UP:
            idx = max(0, idx - 1)
        elif ch == curses.KEY_DOWN:
            idx = min(len(accounts) - 1, idx + 1) if accounts else 0
        elif ch in (ord('q'), ord('Q')):
            return "quit"
        elif ch in (ord('v'), ord('V')):
            return "switch"
        elif ch in (ord('a'), ord('A')):
            issuer = get_string(stdscr, h - 5, 2, "Issuer:")
            stdscr.timeout(200)
            name = get_string(stdscr, h - 5, 2, "Account name:") if issuer is not None else None
            stdscr.timeout(200)
            secret = get_string(stdscr, h - 5, 2, "Secret (base32):") if name is not None else None
            stdscr.timeout(200)
            if secret:
                secret = secret.strip().upper().replace(" ", "")
                try:
                    pyotp.TOTP(secret).now()
                except Exception:
                    msg = "Invalid secret."
                    continue
                accounts.append({"issuer": issuer or "", "name": name or "", "secret": secret})
                save_vault(path, accounts, password, salt)
                msg = "Account added."
        elif ch in (ord('d'), ord('D')) and accounts:
            del accounts[idx]
            idx = max(0, idx - 1)
            save_vault(path, accounts, password, salt)
            msg = "Deleted."

# ---------- entry ----------
def main(stdscr):
    curses.curs_set(0)
    init_colors()
    stdscr.keypad(True)
    try:
        curses.set_escdelay(25)
    except Exception:
        pass
    while True:
        mode, path = vault_picker(stdscr)
        if mode == "new":
            pw = register_flow(stdscr, path)
            if pw is None:
                continue
            animate_unlock(stdscr, "Creating vault")
            create_vault(path, pw)
            accounts, salt = load_vault(path, pw)
            password = pw
        else:
            res = login_flow(stdscr, path)
            if res is None:
                continue
            accounts, salt, password = res
            animate_unlock(stdscr)
        action = dashboard(stdscr, accounts, password, salt, path)
        if action == "quit":
            break

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
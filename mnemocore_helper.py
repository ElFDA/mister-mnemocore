#!/usr/bin/env python3
"""
mnemocore helper.

100% native MiSTer data sources, no external dependencies:

 1. /tmp/CORENAME
    Name of the currently running core (e.g. "MegaDrive", "Arcade").
    Written by MiSTer itself on every core change.

 2. /media/fat/config/<CORENAME>_recent_1.cfg
    Binary file with NUL-separated records that the OSD browser writes
    when you browse a core's own folder, to remember the last file
    selected there. The first record is the most recent one (MRU
    order). Record structure: <folder>\\0<filename>\\0<display_name>\\0

 3. /media/fat/config/cores_recent.cfg
    Same record format, but shared across every core -- what MiSTer
    writes instead when a game is launched through the unified
    searchable Arcade menu (which is how most arcade games actually
    get launched). Only trusted as a fallback when its entry's
    filename matches the current corename, see get_last_file_for_core().

Requires recents=1 in MiSTer.ini -- without it MiSTer doesn't write
either of the files above at all (cfg.recents defaults to off).

Behavior:
 - Arcade (.mra extension) or entry already .mgl: bootcore= points
   directly to the file, MiSTer already knows how to load it on its own.
 - Console/computer (ROM loaded directly, e.g. .md/.sfc/.nes):
   generates AutoBoot.mgl on the fly with the right parameters (rbf/
   delay/type/index) taken from the PROFILES table, and points
   bootcore there.
 - No active game (you're in the menu, CORENAME empty or "MENU"):
   nothing is touched, bootcore stays at the last valid game.
 - Core without a profile in PROFILES: logged and ignored, bootcore
   stays unchanged until you add the missing entry.

Meant to be called repeatedly by mnemocore.sh (polling every few
seconds), it isn't a daemon itself: it runs one pass and exits.

Launched with the --configure argument, it instead opens a full-screen
curses menu (same approach as MiSTer's own Update_all.sh settings
screen, confirmed to work fine on the framebuffer console MiSTer uses
for both CRT and HDMI) to enable/disable autoboot as a whole and to
exclude individual systems. This is how mnemocore.sh calls this script
when it's launched by hand from the Scripts menu instead of from
user-startup.sh.
"""
import curses
import glob
import os
import sys

CORENAME_FILE = "/tmp/CORENAME"
CONFIG_DIR = "/media/fat/config"
MISTER_INI = "/media/fat/MiSTer.ini"
BOOT_MGL_DIR = "/media/fat"
BOOT_MGL_NAME = "AutoBoot.mgl"
LOG = "/media/fat/MnemoCore/mnemocore.log"
CONFIG_FILE = "/media/fat/MnemoCore/mnemocore.conf"

# Special key used in CONFIG_FILE to disable autoboot for ALL arcade
# cores (.mra/.mgl files), which don't go through the PROFILES table
# and therefore don't have a fixed corename to list one by one.
ARCADE_SENTINEL = "__ARCADE__"
ARCADE_LABEL = "Arcade (all cores with an .mra file)"

# MGL parameters (rbf, delay, type, index) per system.
# Key = exact value returned by /tmp/CORENAME for that core.
# Source: official MiSTer MGL wiki
# https://mister-devel.github.io/MkDocs_MiSTer/advanced/mgl/
PROFILES = {
    "Minimig":         dict(rbf="_Computer/Minimig",       delay=1, index=0, type="f"),
    "Arcadia":         dict(rbf="_Console/Arcadia",         delay=1, index=1, type="f"),
    "AdventureVision": dict(rbf="_Console/AdventureVision", delay=1, index=1, type="f"),
    "Astrocade":       dict(rbf="_Console/Astrocade",       delay=1, index=1, type="f"),
    "Atari7800":       dict(rbf="_Console/Atari7800",       delay=1, index=1, type="f"),
    "Atari5200":       dict(rbf="_Console/Atari5200",       delay=1, index=1, type="s"),
    "AtariLynx":       dict(rbf="_Console/AtariLynx",       delay=1, index=0, type="f"),
    "C64":             dict(rbf="_Computer/C64",            delay=1, index=1, type="f"),
    "ChannelF":        dict(rbf="_Console/ChannelF",        delay=1, index=1, type="f"),
    "ColecoVision":    dict(rbf="_Console/ColecoVision",    delay=1, index=1, type="f"),
    "CreatiVision":    dict(rbf="_Console/CreatiVision",    delay=1, index=1, type="f"),
    "Gameboy2P":       dict(rbf="_Console/Gameboy2P",       delay=2, index=1, type="f"),
    "Gameboy":         dict(rbf="_Console/Gameboy",         delay=2, index=1, type="f"),
    "Gamate":          dict(rbf="_Console/Gamate",          delay=1, index=1, type="f"),
    "GnW":             dict(rbf="_Console/GnW",             delay=1, index=1, type="f"),
    # Same physical core also plays Game Gear (and SG-1000), so
    # corename is "SMS" regardless of which one is loaded. index=1 is
    # the Master System slot; Game Gear would need index=2 instead.
    # Deliberately not addable as a separate profile (one entry per
    # corename): kept on Master System.
    "SMS":             dict(rbf="_Console/SMS",             delay=1, index=1, type="f"),
    "GBA2P":           dict(rbf="_Console/GBA2P",           delay=2, index=0, type="f"),
    "GBA":             dict(rbf="_Console/GBA",             delay=2, index=1, type="f"),
    "MegaDrive":       dict(rbf="_Console/MegaDrive",       delay=1, index=1, type="f"),
    "Intellivision":   dict(rbf="_Console/Intellivision",   delay=1, index=1, type="f"),
    "MegaCD":          dict(rbf="_Console/MegaCD",          delay=1, index=0, type="s"),
    "N64":             dict(rbf="_Console/N64",             delay=1, index=1, type="f"),
    # /tmp/CORENAME is "NEOGEO" (all caps), not "NeoGeo" -- confirmed
    # on real hardware, differs from the rbf/folder name casing.
    "NEOGEO":          dict(rbf="_Console/NeoGeo",          delay=1, index=1, type="f"),
    "NES":             dict(rbf="_Console/NES",             delay=2, index=1, type="f"),
    "Odyssey2":        dict(rbf="_Console/Odyssey2",        delay=1, index=1, type="f"),
    "PSX":             dict(rbf="_Console/PSX",             delay=1, index=1, type="s"),
    "WonderSwan":      dict(rbf="_Console/WonderSwan",      delay=1, index=1, type="f"),
    "PokemonMini":     dict(rbf="_Console/PokemonMini",     delay=1, index=1, type="f"),
    "Saturn":          dict(rbf="_Console/Saturn",          delay=1, index=0, type="s"),
    "S32X":            dict(rbf="_Console/S32X",            delay=1, index=1, type="f"),
    "SGB":             dict(rbf="_Console/SGB",             delay=1, index=1, type="f"),
    "SNES":            dict(rbf="_Console/SNES",            delay=2, index=0, type="f"),
    "SuperVision":     dict(rbf="_Console/SuperVision",     delay=1, index=1, type="s"),
    # /tmp/CORENAME is "TGFX16", not "TurboGrafx16" -- confirmed on
    # real hardware, differs from the rbf/folder name.
    "TGFX16":          dict(rbf="_Console/TurboGrafx16",    delay=1, index=0, type="f"),
    "VC4000":          dict(rbf="_Console/VC4000",          delay=1, index=1, type="f"),
    "Vectrex":         dict(rbf="_Console/Vectrex",         delay=1, index=1, type="f"),

    # Below: additional systems cross-checked against wizzomafizzo/mrext's
    # pkg/games/systems.go (an actively maintained tool with its own MGL
    # generation logic), restricted to entries where that source has a
    # single, unambiguous slot -- or, for multi-slot systems, exactly one
    # "file" (type=f) slot, matching the same convention already used
    # above for C64 (favor the single-file game slot over an alternate
    # disk-image slot, consistent with this project's one-<file>-tag
    # limitation, see README "Known limitations").
    "3DO":             dict(rbf="_Console/3DO",             delay=1, index=1, type="s"),
    "Casio_PV-1000":   dict(rbf="_Console/Casio_PV-1000",   delay=1, index=1, type="f"),
    "CDi":             dict(rbf="_Console/CDi",             delay=1, index=1, type="s"),
    "Jaguar":          dict(rbf="_Console/Jaguar",           delay=1, index=1, type="s"),
    "AcornAtom":       dict(rbf="_Computer/AcornAtom",       delay=1, index=1, type="s"),
    "AcornElectron":   dict(rbf="_Computer/AcornElectron",   delay=1, index=0, type="s"),
    "AliceMC10":       dict(rbf="_Computer/AliceMC10",       delay=1, index=1, type="f"),
    "Apogee":          dict(rbf="_Computer/Apogee",          delay=1, index=1, type="f"),
    "Apple-I":         dict(rbf="_Computer/Apple-I",         delay=1, index=1, type="f"),
    "EDSAC":           dict(rbf="_Computer/EDSAC",           delay=1, index=1, type="f"),
    "Galaksija":       dict(rbf="_Computer/Galaksija",       delay=1, index=1, type="f"),
    "Interact":        dict(rbf="_Computer/Interact",        delay=1, index=1, type="f"),
    "Jupiter":         dict(rbf="_Computer/Jupiter",         delay=1, index=1, type="f"),
    "Laser310":        dict(rbf="_Computer/Laser310",        delay=1, index=1, type="f"),
    "Lynx48":          dict(rbf="_Computer/Lynx48",          delay=1, index=1, type="f"),
    "MultiComp":       dict(rbf="_Computer/MultiComp",       delay=1, index=1, type="s"),
    "Oric":            dict(rbf="_Computer/Oric",            delay=1, index=0, type="s"),
    "PDP1":            dict(rbf="_Computer/PDP1",            delay=1, index=1, type="f"),
    "PET2001":         dict(rbf="_Computer/PET2001",         delay=1, index=1, type="f"),
    "PMD85":           dict(rbf="_Computer/PMD85",           delay=1, index=1, type="f"),
    "TatungEinstein":  dict(rbf="_Computer/TatungEinstein",  delay=1, index=0, type="s"),
    "TSConf":          dict(rbf="_Computer/TSConf",          delay=1, index=0, type="s"),
    "UK101":           dict(rbf="_Computer/UK101",           delay=1, index=1, type="f"),
    "Specialist":      dict(rbf="_Computer/Specialist",      delay=1, index=0, type="f"),
    "QL":              dict(rbf="_Computer/QL",              delay=1, index=2, type="f"),
    "ZXNext":          dict(rbf="_Computer/ZXNext",          delay=1, index=1, type="f"),
    "BK0011M":         dict(rbf="_Computer/BK0011M",         delay=1, index=1, type="f"),
    "C16":             dict(rbf="_Computer/C16",             delay=1, index=1, type="f"),
}


def log(msg):
    with open(LOG, "a") as f:
        f.write(msg + "\n")


def load_config():
    """Reads CONFIG_FILE and returns (enabled, disabled):
     - enabled: bool, general autoboot switch (line 'enabled=0'/
       'enabled=1', defaults to True if missing).
     - disabled: set of individually excluded corenames (one name per
       line, '#' for comments; ARCADE_SENTINEL for all arcade cores).
    Missing file = default behavior, autoboot active for everything.

    Deliberately strict about what counts as a valid 'enabled=' line
    or a valid corename: a real-world config file was found missing
    its '#' comment markers (cause unclear -- possibly hand-edited),
    and a looser version of this parser mistook the comment line
    documenting 'enabled=0 completely disables...' for the actual
    enabled= directive, since it also starts with 'enabled=' and its
    value just needed to not literally equal '0'."""
    enabled = True
    disabled = set()
    if not os.path.exists(CONFIG_FILE):
        return enabled, disabled
    try:
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("enabled="):
                    value = line.split("=", 1)[1].strip()
                    if value in ("0", "1"):
                        enabled = value != "0"
                    # else: malformed, ignore rather than misparse
                elif line == ARCADE_SENTINEL or line in PROFILES:
                    disabled.add(line)
                # else: not a recognized corename, ignore -- protects
                # against a corrupted/hand-edited file polluting the
                # exclusion set with garbage that can never match.
    except OSError as e:
        log(f"ERROR reading {CONFIG_FILE}: {e}")
    return enabled, disabled


def save_config(enabled, disabled):
    lines = [
        "# File generated/managed by 'mnemocore.sh' launched from the Scripts menu.\n",
        "# enabled=0 completely disables autoboot, enabled=1 (default) re-enables it.\n",
        "# Every other line = individually excluded corename\n",
        f"# ({ARCADE_SENTINEL} for all arcade cores). Can also be edited by hand.\n",
        f"enabled={1 if enabled else 0}\n",
    ]
    lines += [f"{name}\n" for name in sorted(disabled)]
    with open(CONFIG_FILE, "w") as f:
        f.writelines(lines)


def get_current_core():
    try:
        with open(CORENAME_FILE, "r") as f:
            return f.read().strip()
    except OSError:
        return None


def _read_recent_record(cfg_path):
    """Reads the first record (dir, name, label triplet, most recent
    first) out of a MiSTer *_recent_*.cfg-style file and returns
    (folder, filename), or None if the file is missing/empty/invalid.
    Works for both the per-core files and the shared cores_recent.cfg
    (same fixed-size-struct-with-NUL-padding layout under the hood --
    splitting on NUL and dropping empty parts recovers the fields
    regardless of the padding)."""
    try:
        with open(cfg_path, "rb") as f:
            data = f.read()
    except OSError as e:
        log(f"ERROR reading {cfg_path}: {e}")
        return None

    parts = [p.decode("utf-8", errors="replace") for p in data.split(b"\x00") if p]
    if len(parts) < 2:
        return None

    folder = parts[0]
    filename = parts[1]
    if not filename.strip():
        return None
    return folder, filename


def get_last_file_for_core(corename):
    """Reads <CORENAME>_recent_N.cfg (usually _1), the per-core/folder
    recent list MiSTer writes when you browse a core's own folder.

    Falls back to the shared cores_recent.cfg if that's missing: this
    is what MiSTer writes instead when a game is launched through the
    unified searchable Arcade menu (source: MiSTer's own recent.cpp/
    menu.cpp -- recent_update(..., -1) targets "cores_recent.cfg"
    rather than a per-corename file for that selection path), which is
    how most arcade games actually get launched in practice.

    cores_recent.cfg isn't scoped to a single core -- it's a shared
    MRU list across every selection made that way, of any core. To
    avoid picking up a stale/unrelated entry (e.g. the last arcade
    game played, while some OTHER known console core with no
    per-corename file of its own is now active), the fallback is only
    attempted when corename isn't one of PROFILES' known console/
    computer corenames -- arcade short names (e.g. "bgaregga") never
    are, by construction, so this precisely scopes the fallback to the
    arcade case without ever overriding a recognized console core.
    (Matching the entry's filename against corename, tried in an
    earlier version, doesn't work: confirmed on real hardware that the
    "name" field holds the .mra's full display filename, e.g. "Battle
    Garegga (Europe - USA - Japan - Asia) (Sat Feb 3 1996).mra", not
    the short name /tmp/CORENAME holds.)"""
    candidates = sorted(glob.glob(os.path.join(CONFIG_DIR, f"{corename}_recent_*.cfg")))
    if candidates:
        result = _read_recent_record(candidates[0])
        if result is not None:
            return result

    if corename not in PROFILES:
        return _read_recent_record(os.path.join(CONFIG_DIR, "cores_recent.cfg"))

    return None


def _insert_after_mister_section(lines, new_line):
    """Inserts new_line right after the [MiSTer] section header
    (case-insensitive match, same as MiSTer's own ini parser). Falls
    back to appending at the very end only if no such header exists
    at all (shouldn't normally happen -- every real MiSTer.ini has
    one)."""
    for i, line in enumerate(lines):
        if line.strip().lower() == "[mister]":
            return lines[:i + 1] + [new_line] + lines[i + 1:]
    return lines + ["\n", new_line]


def set_bootcore(value):
    if not os.path.exists(MISTER_INI):
        log("ERROR: MiSTer.ini not found")
        return

    with open(MISTER_INI, "r") as f:
        lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("bootcore=") or stripped.startswith(";bootcore="):
            if not found:
                new_lines.append(f"bootcore={value}\n")
                found = True
            # subsequent duplicate bootcore= lines are dropped
        else:
            new_lines.append(line)

    if not found:
        # Insert right after [MiSTer] rather than appending at EOF:
        # appending would land the line inside whatever custom section
        # happens to be last in the file (e.g. a trailing [menu]
        # section some other tool added), which MiSTer's ini parser
        # only treats as "active" in specific circumstances --
        # [MiSTer] itself is always active, so this is the only
        # placement guaranteed to be read at boot regardless of what
        # else is in the file.
        new_lines = _insert_after_mister_section(new_lines, f"bootcore={value}\n")

    with open(MISTER_INI, "w") as f:
        f.writelines(new_lines)

    log(f"bootcore set to: {value}")


def write_mgl(rbf, delay, file_type, index, path):
    mgl_path = os.path.join(BOOT_MGL_DIR, BOOT_MGL_NAME)
    xml = (
        "<mistergamedescription>\n"
        f"\t<rbf>{rbf}</rbf>\n"
        f'\t<file delay="{delay}" type="{file_type}" index="{index}" path="{path}"/>\n'
        "</mistergamedescription>\n"
    )
    with open(mgl_path, "w") as f:
        f.write(xml)
    log(f"wrote {mgl_path}: rbf={rbf} delay={delay} type={file_type} index={index} path={path}")
    return BOOT_MGL_NAME


def disable_autoboot_now():
    """Neutralizes bootcore= immediately (same trick as antipanic.sh):
    forces it to AutoBoot.mgl and deletes that file, so the very next
    boot falls back to the menu. Without this, turning the general
    switch off in the configure menu only stops *future* updates to
    bootcore= -- the value already sitting in MiSTer.ini from before
    (whatever core/game was last active) would otherwise still
    autoboot on the next reboot, silently ignoring the switch."""
    set_bootcore(BOOT_MGL_NAME)
    mgl_path = os.path.join(BOOT_MGL_DIR, BOOT_MGL_NAME)
    if os.path.exists(mgl_path):
        os.remove(mgl_path)
        log(f"removed {mgl_path} (general switch turned off)")


def resolve_abs_folder(folder):
    """The 'folder' field read from the *_recent_*.cfg file can be
    relative (e.g. '../usb0/games/MegaDrive') or already an absolute
    path. We always normalize it relative to /media/fat."""
    if folder.startswith("/"):
        return folder
    return os.path.normpath(os.path.join("/media/fat", folder))


def main():
    enabled, disabled = load_config()
    if not enabled:
        # Autoboot disabled by the general switch: don't touch anything.
        return

    corename = get_current_core()
    if not corename or corename.upper() in ("MENU", ""):
        # In the menu, no active game: don't touch bootcore.
        return

    result = get_last_file_for_core(corename)
    if result is None:
        log(f"no recent file found for core '{corename}'")
        return

    folder, filename = result
    log(f"core={corename} folder={folder!r} file={filename!r}")

    ext = os.path.splitext(filename)[1].lower()

    if ext in (".mra", ".mgl"):
        if ARCADE_SENTINEL in disabled:
            log("arcade autoboot disabled by configuration, skipping")
            return
        # Arcade or shortcut already ready: bootcore loads it on its own.
        set_bootcore(filename)
        return

    if corename in disabled:
        log(f"core '{corename}' disabled by configuration, skipping")
        return

    profile = PROFILES.get(corename)
    if not profile:
        log(f"WARNING: no profile for corename={corename!r}, skipping")
        return

    full_path = os.path.join(resolve_abs_folder(folder), filename)

    mgl_name = write_mgl(
        rbf=profile["rbf"],
        delay=profile["delay"],
        file_type=profile["type"],
        index=profile["index"],
        path=full_path,
    )
    set_bootcore(mgl_name)


_GENERAL_SWITCH = "__ENABLED__"


def _menu_items():
    """General switch entry + special arcade entry + one system for
    every corename in PROFILES, in alphabetical order."""
    items = [(_GENERAL_SWITCH, "Autoboot enabled (general switch)")]
    items.append((ARCADE_SENTINEL, ARCADE_LABEL))
    items += [(name, name) for name in sorted(PROFILES)]
    return items


def _run_menu(stdscr, items):
    """Full-screen curses checklist, same approach as Update_all.sh's
    settings screen: bordered window, reverse-video highlight for the
    selected row (works without color, fine on CRT), arrow keys to
    move, Space/Enter to toggle. Returns (enabled, disabled, saved)."""
    curses.curs_set(0)
    stdscr.keypad(True)

    enabled, disabled = load_config()
    selected = 0
    top = 0
    dirty = False
    quit_confirm = False
    status = ""

    def is_checked(idx):
        key, _ = items[idx]
        if key == _GENERAL_SWITCH:
            return enabled
        return key not in disabled

    def toggle(idx):
        nonlocal enabled, dirty
        key, _ = items[idx]
        if key == _GENERAL_SWITCH:
            enabled = not enabled
        elif key in disabled:
            disabled.discard(key)
        else:
            disabled.add(key)
        dirty = True

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        stdscr.border()

        title = " MnemoCore - configuration "
        stdscr.addstr(0, max(1, (max_x - len(title)) // 2), title[:max_x - 2], curses.A_BOLD)

        list_top = 2
        list_height = max(1, max_y - list_top - 3)
        if selected < top:
            top = selected
        if selected >= top + list_height:
            top = selected - list_height + 1

        for row, idx in enumerate(range(top, min(len(items), top + list_height))):
            key, label = items[idx]
            mark = "X" if is_checked(idx) else " "
            line = f"[{mark}] {label}"
            attr = curses.A_REVERSE if idx == selected else curses.A_NORMAL
            stdscr.addstr(list_top + row, 2, line[:max_x - 4].ljust(max_x - 4), attr)
            if key == _GENERAL_SWITCH and row + 1 < list_height:
                stdscr.hline(list_top + row + 1, 2, ord('-'), max_x - 4)

        footer1 = "Up/Down move   Space/Enter toggle   A all   N none"
        footer2 = "S save and exit   Q exit without saving"
        stdscr.addstr(max_y - 3, 2, footer1[:max_x - 4], curses.A_DIM)
        stdscr.addstr(max_y - 2, 2, footer2[:max_x - 4], curses.A_DIM)
        if status:
            stdscr.addstr(max_y - 2, 2, status[:max_x - 4], curses.A_BOLD)

        stdscr.refresh()
        ch = stdscr.getch()
        status = ""

        if ch in (curses.KEY_UP, ord('k')):
            selected = max(0, selected - 1)
            quit_confirm = False
        elif ch in (curses.KEY_DOWN, ord('j')):
            selected = min(len(items) - 1, selected + 1)
            quit_confirm = False
        elif ch in (curses.KEY_ENTER, 10, 13, ord(' ')):
            toggle(selected)
            quit_confirm = False
        elif ch in (ord('a'), ord('A')):
            disabled.clear()
            dirty = True
            quit_confirm = False
        elif ch in (ord('n'), ord('N')):
            disabled = {key for key, _ in items[1:]}
            dirty = True
            quit_confirm = False
        elif ch in (ord('s'), ord('S')):
            save_config(enabled, disabled)
            if not enabled:
                disable_autoboot_now()
            return enabled, disabled, True
        elif ch in (ord('q'), ord('Q'), 27):
            if dirty and not quit_confirm:
                status = "Unsaved changes! Press Q again to quit, any other key to cancel."
                quit_confirm = True
                continue
            return enabled, disabled, False
        else:
            quit_confirm = False


def configure():
    """Full-screen curses menu for the general switch and per-core
    exclusions. Called by mnemocore.sh when launched by hand from the
    Scripts menu (instead of from user-startup.sh)."""
    items = _menu_items()
    enabled, disabled, saved = curses.wrapper(_run_menu, items)
    if saved:
        print(f"Configuration saved to {CONFIG_FILE}")
        if enabled:
            print("Changes will be applied on the daemon's next poll (a few seconds at most).")
        else:
            print("Autoboot disabled: bootcore= reset now, next boot goes to the menu.")
    else:
        print("Exited without saving.")


if __name__ == "__main__":
    if "--configure" in sys.argv:
        configure()
    else:
        main()

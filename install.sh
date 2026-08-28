#!/bin/sh
# install.sh
#
# Automated installer for MnemoCore. Run it directly on the MiSTer,
# e.g. over SSH:
#
#   curl -kfsSL https://raw.githubusercontent.com/ElFDA/mister-mnemocore/master/install.sh | sh
#
# (-k / --no-check-certificate is required because stock MiSTer Linux
# ships with no CA certificates, so plain HTTPS verification fails.)
#
# If the project files are already present in the current directory
# (e.g. a local git checkout), those are copied instead of downloading
# them again.
#
# Safe to re-run: every step is idempotent.

set -e

cat << 'BANNER'
 __  __                             ____
|  \/  |_ __   ___ _ __ ___   ___  / ___|___  _ __ ___
| |\/| | '_ \ / _ \ '_ ` _ \ / _ \| |   / _ \| '__/ _ \
| |  | | | | |  __/ | | | | | (_) | |__| (_) | | |  __/
|_|  |_|_| |_|\___|_| |_| |_|\___/ \____\___/|_|  \___|

BANNER

MEDIA_FAT="${MEDIA_FAT:-/media/fat}"
RAW_BASE="https://raw.githubusercontent.com/ElFDA/mister-mnemocore/master"

if [ ! -e "$MEDIA_FAT/MiSTer.ini" ]; then
    echo "ERROR: $MEDIA_FAT/MiSTer.ini not found -- this doesn't look like a MiSTer root." >&2
    echo "Set MEDIA_FAT to the correct path if you're testing off-device." >&2
    exit 1
fi

fetch() {
    # fetch <name> <dest>
    name="$1"
    dest="$2"
    if [ -e "./$name" ]; then
        cp "./$name" "$dest"
    elif command -v curl >/dev/null 2>&1; then
        curl -kfsSL "$RAW_BASE/$name" -o "$dest"
    elif command -v wget >/dev/null 2>&1; then
        wget --no-check-certificate -qO "$dest" "$RAW_BASE/$name"
    else
        echo "ERROR: neither curl nor wget is available, and no local $name found." >&2
        exit 1
    fi
}

echo "Installing MnemoCore into $MEDIA_FAT ..."

mkdir -p "$MEDIA_FAT/Scripts" "$MEDIA_FAT/MnemoCore"

fetch mnemocore.sh "$MEDIA_FAT/Scripts/mnemocore.sh"
chmod +x "$MEDIA_FAT/Scripts/mnemocore.sh"
echo "  installed $MEDIA_FAT/Scripts/mnemocore.sh"

fetch mnemocore_helper.py "$MEDIA_FAT/MnemoCore/mnemocore_helper.py"
chmod +x "$MEDIA_FAT/MnemoCore/mnemocore_helper.py"
echo "  installed $MEDIA_FAT/MnemoCore/mnemocore_helper.py"

fetch antipanic.sh "$MEDIA_FAT/MnemoCore/antipanic.sh"
chmod +x "$MEDIA_FAT/MnemoCore/antipanic.sh"
echo "  installed $MEDIA_FAT/MnemoCore/antipanic.sh"

fetch uninstall.sh "$MEDIA_FAT/MnemoCore/uninstall.sh"
chmod +x "$MEDIA_FAT/MnemoCore/uninstall.sh"
echo "  installed $MEDIA_FAT/MnemoCore/uninstall.sh"

STARTUP="$MEDIA_FAT/linux/user-startup.sh"
STARTUP_LINE="[ -e $MEDIA_FAT/Scripts/mnemocore.sh ] && setsid $MEDIA_FAT/Scripts/mnemocore.sh < /dev/null >> $MEDIA_FAT/MnemoCore/mnemocore.log 2>&1 &"

if [ ! -e "$STARTUP" ]; then
    mkdir -p "$MEDIA_FAT/linux"
    printf '#!/bin/sh\n' > "$STARTUP"
fi

if grep -qF "mnemocore.sh" "$STARTUP"; then
    echo "  $STARTUP already references mnemocore.sh, leaving it untouched"
else
    printf '%s\n' "$STARTUP_LINE" >> "$STARTUP"
    echo "  added autostart line to $STARTUP"
fi

INI="$MEDIA_FAT/MiSTer.ini"
BACKUP="$INI.mnemocore-bak"

if [ ! -e "$BACKUP" ]; then
    cp "$INI" "$BACKUP"
    echo "  backed up $INI to $BACKUP"
fi

upsert_ini_key() {
    # upsert_ini_key <key> <value>
    # If the key already exists, replaces it in place. Otherwise
    # inserts it right after the [MiSTer] section header instead of
    # appending at EOF -- appending would land the line inside
    # whatever custom section happens to be last in the file (e.g. a
    # trailing [menu] section some other tool added, common with
    # Zaparoo), which MiSTer's ini parser only treats as "active" in
    # specific circumstances. [MiSTer] itself is always active.
    key="$1"
    value="$2"
    if grep -qE "^;?${key}=" "$INI"; then
        sed -i "s|^;\{0,1\}${key}=.*|${key}=${value}|" "$INI"
    else
        awk -v k="$key" -v v="$value" '
            { print }
            !done && tolower($0) ~ /^\[mister\]/ { print k "=" v; done=1 }
            END { if (!done) print k "=" v }
        ' "$INI" > "$INI.tmp" && mv "$INI.tmp" "$INI"
    fi
}

upsert_ini_key bootcore AutoBoot.mgl
upsert_ini_key bootcore_timeout 1
upsert_ini_key recents 1
echo "  set bootcore=AutoBoot.mgl, bootcore_timeout=1 and recents=1 in $INI"

echo
echo "Done. Reboot the MiSTer to activate MnemoCore:"
echo "  reboot"
echo
echo "After boot, verify with:"
echo "  ps | grep mnemocore"
echo "  tail -10 $MEDIA_FAT/MnemoCore/mnemocore.log"

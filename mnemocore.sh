#!/bin/sh
# mnemocore.sh
#
# Lightweight daemon that keeps the bootcore= line in MiSTer.ini always
# up to date with the last game/core actually launched.
#
# No external dependencies: relies only on /tmp/CORENAME and the
# /media/fat/config/<CORENAME>_recent_*.cfg files that MiSTer already
# writes on its own. See mnemocore_helper.py for the full logic.
#
# Meant to be launched as a background service from user-startup.sh, e.g.:
#   [ -e /media/fat/Scripts/mnemocore.sh ] && setsid /media/fat/Scripts/mnemocore.sh < /dev/null >> /media/fat/MnemoCore/mnemocore.log 2>&1 &
#
# Launched by hand from the Scripts menu instead (stdin is a terminal,
# not /dev/null), it first self-configures if needed (autostart line
# in user-startup.sh, bootcore=/bootcore_timeout=/recents=1 in
# MiSTer.ini -- idempotent, same checks install.sh does) and then
# opens the configuration menu instead of the daemon. This makes
# MnemoCore usable straight from a Downloader/Update_all custom
# database too: the Downloader is only allowed to place files, never
# to edit MiSTer.ini or anything under /linux, so this self-setup on
# first interactive launch is what actually wires everything up.

MEDIA_FAT="${MEDIA_FAT:-/media/fat}"
HELPER="$MEDIA_FAT/MnemoCore/mnemocore_helper.py"
LOG="$MEDIA_FAT/MnemoCore/mnemocore.log"
POLL_SECONDS=3

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

ensure_setup() {
    STARTUP="$MEDIA_FAT/linux/user-startup.sh"
    STARTUP_LINE="[ -e $MEDIA_FAT/Scripts/mnemocore.sh ] && setsid $MEDIA_FAT/Scripts/mnemocore.sh < /dev/null >> $MEDIA_FAT/MnemoCore/mnemocore.log 2>&1 &"

    if [ ! -e "$STARTUP" ]; then
        mkdir -p "$MEDIA_FAT/linux"
        printf '#!/bin/sh\n' > "$STARTUP"
    fi

    if ! grep -qF "mnemocore.sh" "$STARTUP"; then
        printf '%s\n' "$STARTUP_LINE" >> "$STARTUP"
        echo "Added autostart line to $STARTUP"
    fi

    INI="$MEDIA_FAT/MiSTer.ini"
    if [ -e "$INI" ]; then
        BACKUP="$INI.mnemocore-bak"
        [ -e "$BACKUP" ] || cp "$INI" "$BACKUP"

        upsert_ini_key() {
            # Inserts right after [MiSTer] rather than appending at
            # EOF when the key is missing -- see install.sh's
            # upsert_ini_key for why (custom trailing sections, e.g.
            # from Zaparoo, are common and only [MiSTer] is guaranteed
            # active in MiSTer's own ini parser).
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

        if ! grep -q "^bootcore=AutoBoot.mgl$" "$INI" \
            || ! grep -q "^bootcore_timeout=1$" "$INI" \
            || ! grep -q "^recents=1$" "$INI"; then
            upsert_ini_key bootcore AutoBoot.mgl
            upsert_ini_key bootcore_timeout 1
            upsert_ini_key recents 1
            echo "Configured $INI (bootcore=AutoBoot.mgl, bootcore_timeout=1, recents=1)"
        fi
    fi
}

if [ -t 0 ]; then
    ensure_setup
    python3 "$HELPER" --configure
    exit 0
fi

log "mnemocore started (pid $$), polling every ${POLL_SECONDS}s"

while true; do
    python3 "$HELPER" 2>>"$LOG"
    sleep "$POLL_SECONDS"
done

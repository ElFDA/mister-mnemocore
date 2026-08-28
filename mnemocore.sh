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
# not /dev/null), it opens the configuration menu instead of the
# daemon: from there you can enable/disable autoboot as a whole or
# exclude individual systems.

HELPER="/media/fat/MnemoCore/mnemocore_helper.py"
LOG="/media/fat/MnemoCore/mnemocore.log"
POLL_SECONDS=3

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

if [ -t 0 ]; then
    python3 "$HELPER" --configure
    exit 0
fi

log "mnemocore started (pid $$), polling every ${POLL_SECONDS}s"

while true; do
    python3 "$HELPER" 2>>"$LOG"
    sleep "$POLL_SECONDS"
done

#!/bin/sh
# antipanic.sh
#
# Emergency recovery: run this if MnemoCore autobooted into a broken
# core (black screen, no way to reach the MiSTer menu to fix
# bootcore= by hand). Installed alongside the rest of MnemoCore at
# /media/fat/MnemoCore/antipanic.sh -- run it over SSH/telnet when the
# OSD is unreachable:
#
#   ssh root@<mister-ip> sh /media/fat/MnemoCore/antipanic.sh
#
# It stops the running mnemocore.sh daemon (otherwise it can regenerate
# AutoBoot.mgl on its next poll, within 3s, undoing this), forces
# bootcore=AutoBoot.mgl in MiSTer.ini (overwriting whatever is
# currently set, including a broken arcade .mra path), and deletes
# AutoBoot.mgl. bootcore= then points at a file that doesn't exist, so
# MiSTer falls back to its normal menu on the next boot instead of
# reloading the broken core. No manual re-enable needed afterward: the
# daemon restarts on the next reboot (via user-startup.sh) and, once
# you launch a working game from the menu, regenerates AutoBoot.mgl on
# its own again.
#
# Safe to re-run.

set -e

MEDIA_FAT="${MEDIA_FAT:-/media/fat}"
INI="$MEDIA_FAT/MiSTer.ini"
MGL="$MEDIA_FAT/AutoBoot.mgl"

if [ ! -e "$INI" ]; then
    echo "ERROR: $INI not found -- this doesn't look like a MiSTer root." >&2
    echo "Set MEDIA_FAT to the correct path if you're testing off-device." >&2
    exit 1
fi

STOPPED=0
for pid in $(ps 2>/dev/null | grep '[m]nemocore\.sh' | awk '{print $1}'); do
    kill "$pid" 2>/dev/null || true
    STOPPED=1
done
[ "$STOPPED" = "1" ] && echo "stopped running mnemocore.sh daemon"

if grep -qE "^;?bootcore=" "$INI"; then
    sed -i "s|^;\{0,1\}bootcore=.*|bootcore=AutoBoot.mgl|" "$INI"
else
    # Insert right after [MiSTer] rather than appending at EOF, so it
    # lands somewhere MiSTer's ini parser always treats as active
    # even if a custom section (e.g. a trailing [menu] from another
    # tool) happens to be last in the file.
    awk '
        { print }
        !done && tolower($0) ~ /^\[mister\]/ { print "bootcore=AutoBoot.mgl"; done=1 }
        END { if (!done) print "bootcore=AutoBoot.mgl" }
    ' "$INI" > "$INI.tmp" && mv "$INI.tmp" "$INI"
fi
echo "set bootcore=AutoBoot.mgl in $INI"

if [ -e "$MGL" ]; then
    rm -f "$MGL"
    echo "removed $MGL"
else
    echo "$MGL already absent, nothing to remove"
fi

echo
echo "Done. Reboot -- MiSTer will fall back to the normal menu since"
echo "AutoBoot.mgl no longer exists. Autoboot resumes on its own once"
echo "you launch a working game."

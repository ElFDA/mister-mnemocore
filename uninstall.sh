#!/bin/sh
# uninstall.sh
#
# Completely removes MnemoCore from a MiSTer. Run it directly on the
# MiSTer, e.g. over SSH:
#
#   curl -kfsSL https://raw.githubusercontent.com/ElFDA/mister-mnemocore/master/uninstall.sh | sh
#
# Removes /media/fat/Scripts/mnemocore.sh, the whole
# /media/fat/MnemoCore/ folder (helper, log, conf, antipanic.sh),
# /media/fat/AutoBoot.mgl, the autostart line from user-startup.sh,
# and unconditionally comments out any active bootcore=/
# bootcore_timeout= line in MiSTer.ini -- even if you changed those
# values yourself after installing. MiSTer.ini.mnemocore-bak (if
# present, from the original install) is intentionally left in place.
#
# Safe to re-run.

MEDIA_FAT="${MEDIA_FAT:-/media/fat}"

echo "Uninstalling MnemoCore from $MEDIA_FAT ..."

STOPPED=0
for pid in $(ps 2>/dev/null | grep '[m]nemocore\.sh' | awk '{print $1}'); do
    kill "$pid" 2>/dev/null || true
    STOPPED=1
done
[ "$STOPPED" = "1" ] && echo "  stopped running mnemocore.sh process"

if [ -e "$MEDIA_FAT/Scripts/mnemocore.sh" ]; then
    rm -f "$MEDIA_FAT/Scripts/mnemocore.sh"
    echo "  removed $MEDIA_FAT/Scripts/mnemocore.sh"
fi

if [ -d "$MEDIA_FAT/MnemoCore" ]; then
    rm -rf "$MEDIA_FAT/MnemoCore"
    echo "  removed $MEDIA_FAT/MnemoCore/"
fi

if [ -e "$MEDIA_FAT/AutoBoot.mgl" ]; then
    rm -f "$MEDIA_FAT/AutoBoot.mgl"
    echo "  removed $MEDIA_FAT/AutoBoot.mgl"
fi

STARTUP="$MEDIA_FAT/linux/user-startup.sh"
if [ -e "$STARTUP" ] && grep -qF "mnemocore.sh" "$STARTUP"; then
    grep -vF "mnemocore.sh" "$STARTUP" > "$STARTUP.tmp"
    mv "$STARTUP.tmp" "$STARTUP"
    echo "  removed autostart line from $STARTUP"
fi

INI="$MEDIA_FAT/MiSTer.ini"
if [ -e "$INI" ]; then
    sed -i 's/^bootcore=/;bootcore=/' "$INI"
    sed -i 's/^bootcore_timeout=/;bootcore_timeout=/' "$INI"
    echo "  commented out bootcore=/bootcore_timeout= in $INI"
fi

if [ -e "$INI.mnemocore-bak" ]; then
    echo "  note: $INI.mnemocore-bak is left in place, remove it by hand if you don't need it"
fi

echo
echo "Done. Reboot to fully apply -- MiSTer will boot to its normal menu."

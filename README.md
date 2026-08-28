# MnemoCore

Reboot your MiSTer and it automatically resumes the last game you were playing, arcade or console, no change to how you browse.

## Why not an existing tool

Before landing here, these were tried and dropped, in order:

- `bootcore=lastcore`/`lastexactcore` (native MiSTer): only works for the core name, not for the specific file/game that was loaded.
- LastPlayed (mrext): the service no longer reliably generates the `Last Played.mgl` shortcut on recent MiSTer versions; cause not conclusively isolated, intermittent behavior.
- Zaparoo Core + `launch.last`: tracks the active game very well (`media.active` via API), but the `launch.last` command failed with `file not found: <setname>` for arcade cores with multiple variants/sets (`_alternatives`) or libraries with duplicate paths. Not 100% sure whether this is an actual bug in the Core's path resolution or a mistake on my end, I didn't dig further. Beyond that, I was also looking for something simpler than standing up Zaparoo's own media index/database just to resume the last game.

MnemoCore bypasses all three by reading MiSTer's native data sources directly: `/tmp/CORENAME` and the `*_recent_*.cfg` files MiSTer's OSD writes on its own. It only touches `bootcore=` in `MiSTer.ini` and `AutoBoot.mgl`, no shared file or database with Zaparoo, so the two can coexist without conflicts.

## Quick install

Over SSH on the MiSTer:

```bash
curl -kfsSL https://raw.githubusercontent.com/ElFDA/mnemocore/master/install.sh | sh
reboot
```

Copies the files, adds the autostart line, and sets `bootcore=AutoBoot.mgl`, `bootcore_timeout=1` and `recents=1` in `MiSTer.ini` (backing it up first, to `MiSTer.ini.mnemocore-bak`). Safe to re-run.

`-k` is required because stock MiSTer Linux ships with no CA certificates, so plain HTTPS verification fails. If you'd rather read [`install.sh`](install.sh) before running it, or don't have network access on the MiSTer, use manual installation instead.

## Manual installation

Copy the files to the MiSTer SD card with FileZilla or any other FTP/SFTP client:

- `mnemocore.sh` to `/media/fat/Scripts/`
- `mnemocore_helper.py`, `antipanic.sh` and `uninstall.sh` to `/media/fat/MnemoCore/` (create the folder)

Then, over SSH, make them executable:

```bash
chmod +x /media/fat/Scripts/mnemocore.sh
chmod +x /media/fat/MnemoCore/mnemocore_helper.py
chmod +x /media/fat/MnemoCore/antipanic.sh
chmod +x /media/fat/MnemoCore/uninstall.sh
```

Add this line to `/media/fat/linux/user-startup.sh` (create it if it doesn't exist, with `#!/bin/sh` as the first line):

```
[ -e /media/fat/Scripts/mnemocore.sh ] && setsid /media/fat/Scripts/mnemocore.sh < /dev/null >> /media/fat/MnemoCore/mnemocore.log 2>&1 &
```

In `MiSTer.ini`, section `[MiSTer]`:

```ini
bootcore=AutoBoot.mgl
bootcore_timeout=1
recents=1
```

`recents=1` is required: without it MiSTer doesn't write the `_recent_*.cfg` files MnemoCore reads, so nothing would ever autoboot.

Reboot, then verify with:

```bash
ps | grep mnemocore
tail -10 /media/fat/MnemoCore/mnemocore.log
```

## Turning autoboot on/off

Launch `mnemocore` from the MiSTer Scripts menu (the same file used for the daemon: launching it by hand opens the configuration menu instead of polling). A full-screen checklist opens (same style as Update_all.sh's settings screen) with a general switch plus one entry per system, arcade included. Up/Down to move, Space or Enter to toggle, `a`/`n` to enable/disable all systems, `s` to save and exit, `q` to exit without saving.

The configuration is saved to `/media/fat/MnemoCore/mnemocore.conf` and read by the daemon on every polling cycle, changes take effect within a few seconds. An excluded system doesn't touch `bootcore=`: it stays set to the last valid game launched on a non-excluded system.

## Antipanic (broken core, black screen)

If the last game/core autobooted is broken (black screen, no way to reach the MiSTer OSD to fix `bootcore=` by hand), every reboot just reloads the same broken core. Over SSH, when the OSD is unreachable:

```bash
ssh root@<mister-ip> sh /media/fat/MnemoCore/antipanic.sh
```

This forces `bootcore=AutoBoot.mgl` in `MiSTer.ini` (overwriting whatever is currently set, including a broken arcade `.mra` path) and deletes `AutoBoot.mgl`. `bootcore=` then points at a file that doesn't exist, so MiSTer falls back to its normal menu on the next boot instead of reloading the broken core, this is confirmed native MiSTer behavior. No manual re-enabling needed afterward: once you launch a working game from the menu, `mnemocore.sh` regenerates `AutoBoot.mgl` and autoboot resumes on its own.

This assumes SSH access to the MiSTer is already set up, that's a general MiSTer feature, not something MnemoCore configures.

## Uninstalling

Already on the SD card, works offline:

```bash
sh /media/fat/MnemoCore/uninstall.sh
```

Or, over SSH with network access:

```bash
curl -kfsSL https://raw.githubusercontent.com/ElFDA/mnemocore/master/uninstall.sh | sh
```

Stops the daemon, removes every installed file, removes the autostart line, and comments out `bootcore=`/`bootcore_timeout=` in `MiSTer.ini`.

## Acknowledgments

- [Sorgelig](https://github.com/sorgelig): creator and lead maintainer of the [MiSTer project](https://github.com/MiSTer-devel) itself, without which none of this would exist.
- [Wizzo](https://github.com/wizzomafizzo): author of [mrext](https://github.com/wizzomafizzo/mrext), whose LastPlayed feature (see [Why not an existing tool](#why-not-an-existing-tool) above) was one of the approaches this project compared itself against.

## License

MIT, see [LICENSE](LICENSE).

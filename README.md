# MnemoCore

Reboot your MiSTer and it automatically resumes the last game you were playing, arcade or console, no change to how you browse.

## Why not an existing tool

Before landing here, these were tried and dropped, in order:

- `bootcore=lastcore`/`lastexactcore` (native MiSTer): only works for the core name, not for the specific file/game that was loaded.
- LastPlayed (mrext): the service no longer reliably generates the `Last Played.mgl` shortcut on recent MiSTer versions; cause not conclusively isolated, intermittent behavior.
- Zaparoo Core + `launch.last`: tracks the active game very well (`media.active` via API), but the `launch.last` command failed with `file not found: <setname>` for arcade cores with multiple variants/sets (`_alternatives`) or libraries with duplicate paths. Not 100% sure whether this is an actual bug in the Core's path resolution or a mistake on my end, I didn't dig further. Beyond that, I was also looking for something simpler than standing up Zaparoo's own media index/database just to resume the last game.

MnemoCore bypasses all three by reading MiSTer's native data sources directly: `/tmp/CORENAME` and the `*_recent_*.cfg` files MiSTer's OSD writes on its own. It only touches `bootcore=` in `MiSTer.ini` and `AutoBoot.mgl`, no shared file or database with Zaparoo, so the two can install side by side without conflicts.

**Known limitation**: a game launched through the Zaparoo frontend is not currently picked up for autoboot. Zaparoo loads it the native way (`load_core` via `/dev/MiSTer_cmd`, so `/tmp/CORENAME` does update), but MiSTer's own recent-file tracking is tied to the OSD browser UI, which Zaparoo's launch path skips, so the `*_recent_*.cfg` files MnemoCore reads never get written for that launch. Being worked on.

## Installation

Three ways to install, pick one:

### 1. Downloader / Update_all (recommended)

Stays up to date automatically whenever you run Update_all or the Downloader, no need to re-run anything by hand for updates. Add this to the bottom of `/media/fat/downloader.ini`:

```ini
[mnemocore]
db_url = 'https://raw.githubusercontent.com/ElFDA/mister-mnemocore/master/db.json'
```

Run the Downloader (or Update_all), then launch `mnemocore` from the Scripts menu once: it self-configures on first interactive launch (autostart line, `bootcore=`/`bootcore_timeout=`/`recents=1`) since the Downloader itself is only allowed to place files, never touch `MiSTer.ini` or anything under `/linux`. Then reboot.

### 2. Automatic

Over SSH on the MiSTer:

```bash
curl -kfsSL https://raw.githubusercontent.com/ElFDA/mister-mnemocore/master/install.sh | sh
reboot
```

Automatically copies the files, adds the autostart line, and sets `bootcore=AutoBoot.mgl`, `bootcore_timeout=1` and `recents=1` in `MiSTer.ini` (backing it up first, to `MiSTer.ini.mnemocore-bak`). Safe to re-run.

If you'd rather read [`install.sh`](install.sh) before running it, or don't have network access on the MiSTer, use manual installation instead.

### 3. Manual

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

Launch `mnemocore` from the Scripts menu once: it self-configures (autostart line in `user-startup.sh`, `bootcore=`/`bootcore_timeout=`/`recents=1` in `MiSTer.ini`) the same way it does when installed via Downloader. Then reboot and verify:

```bash
reboot
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
curl -kfsSL https://raw.githubusercontent.com/ElFDA/mister-mnemocore/master/uninstall.sh | sh
```

Stops the daemon, removes every installed file, removes the autostart line, and comments out `bootcore=`/`bootcore_timeout=` in `MiSTer.ini`.

## Acknowledgments

- [Sorgelig](https://github.com/sorgelig): creator and lead maintainer of the [MiSTer project](https://github.com/MiSTer-devel) itself, without which none of this would exist.
- [Wizzo](https://github.com/wizzomafizzo): author of [mrext](https://github.com/wizzomafizzo/mrext), whose LastPlayed feature (see [Why not an existing tool](#why-not-an-existing-tool) above) was one of the approaches this project compared itself against.

## License

MIT, see [LICENSE](LICENSE).

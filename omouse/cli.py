"""omarchy-mouse-utils — find the pointer, or make it impossible to lose.

    omarchy-mouse-utils find         a spotlight that fades once you have seen it
    omarchy-mouse-utils crosshairs   lines through the pointer, for a screencast
    omarchy-mouse-utils ring         a highlight around it
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys

from . import __version__, launcher, menu, tracker
from .hypr import Hyprland, HyprlandError

CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                          "omarchy-mouse-utils")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
STATE_DIR = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "omarchy-mouse-utils")
PID_FILE = os.path.join(STATE_DIR, "overlay.pid")

DEFAULTS = {"colour": "", "thickness": 2, "radius": 110, "dim": 0.55,
            "fade_after": 1200, "hz": 60}
ICONS = {"find": "", "cross": "", "ring": "", "off": ""}


def config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return {**DEFAULTS, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def accent() -> str:
    chosen = config().get("colour") or ""
    if chosen:
        return chosen
    try:
        r = subprocess.run(["omarchy-theme-color", "accent"], capture_output=True,
                           timeout=10, check=False)
        value = r.stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.SubprocessError):
        value = ""
    return value if value.startswith("#") else "#ff5555"


# ---------------------------------------------------------------- one at a time

def running_pid() -> int | None:
    """The overlay we started, if it is still there."""
    try:
        with open(PID_FILE, encoding="utf-8") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return None
    return pid


def remember(pid: int) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(pid))


def stop_running() -> bool:
    pid = running_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    try:
        os.unlink(PID_FILE)
    except OSError:
        pass
    return True


# ---------------------------------------------------------------- commands

def show(mode: str, args) -> int:
    settings = config()
    fade = 0 if mode != "spotlight" else int(settings["fade_after"])
    if args.fade is not None:
        fade = args.fade
    options = {"mode": mode, "accent": accent(),
               "thickness": int(settings["thickness"]),
               "radius": int(settings["radius"]),
               "dim": float(settings["dim"]),
               "fade_after": fade}

    if stop_running() and args.toggle:
        print("Off.")
        return 0

    binary = launcher.quickshell()
    if binary is None:
        print("omarchy-mouse-utils: quickshell is not installed "
              "(sudo pacman -S quickshell)", file=sys.stderr)
        return 127
    path = launcher.qml_file("Pointer.qml")
    if not os.path.exists(path):
        print(f"omarchy-mouse-utils: {path} is missing", file=sys.stderr)
        return 1
    try:
        process = subprocess.Popen(launcher.build_command(path, binary),
                                   env=launcher.environment(options),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"omarchy-mouse-utils: {e}", file=sys.stderr)
        return 1
    remember(process.pid)
    if args.wait:
        return process.wait()
    return 0


def cmd_find(args) -> int:
    args.toggle = False
    return show("spotlight", args)


def cmd_crosshairs(args) -> int:
    return show("crosshairs", args)


def cmd_ring(args) -> int:
    return show("ring", args)


def cmd_off(args) -> int:
    if stop_running():
        print("Off.")
        return 0
    print("Nothing is showing.")
    return 1


def cmd_track(args) -> int:
    return tracker.run(hz=int(config()["hz"]), idle_after=args.idle or 0.0)


def cmd_where(args) -> int:
    """Where the pointer is, and on which monitor — the question behind all of this."""
    hyprland = Hyprland()
    try:
        x, y = hyprland.cursor()
        monitor = hyprland.monitor_at(x, y)
    except HyprlandError as e:
        print(f"omarchy-mouse-utils: {e}", file=sys.stderr)
        return 1
    where = f" on {monitor['name']}" if monitor else ""
    print(f"{x}, {y}{where}")
    return 0


def cmd_status(args) -> int:
    settings = config()
    pid = running_pid()
    print(f"quickshell     {launcher.quickshell() or 'NOT FOUND'}")
    print(f"showing        {'yes (pid ' + str(pid) + ')' if pid else 'no'}")
    print(f"colour         {accent()}")
    print(f"thickness      {settings['thickness']}px, radius {settings['radius']}px")
    try:
        x, y = Hyprland().cursor()
        print(f"pointer        {x}, {y}")
    except HyprlandError as e:
        print(f"pointer        unavailable ({e})")
    return 0


def cmd_menu(args) -> int:
    rows = [(ICONS["find"], "Find the pointer", "A spotlight that fades away"),
            (ICONS["cross"], "Crosshairs", "Lines through the pointer, for a screencast"),
            (ICONS["ring"], "Highlight ring", "A circle that follows it")]
    if running_pid():
        rows.append((ICONS["off"], "Turn it off", "Stop whatever is showing"))
    pick = menu.select("Mouse utilities", rows, width=620)
    if not pick:
        return 1
    label = pick.split("\t")[0]
    if label == "Find the pointer":
        return cmd_find(args)
    if label == "Crosshairs":
        return cmd_crosshairs(args)
    if label == "Highlight ring":
        return cmd_ring(args)
    return cmd_off(args)


def cmd_setup(args) -> int:
    print("Add these to ~/.config/hypr/bindings.lua:\n")
    print('  o.bind("SUPER + SHIFT + M", "Find the pointer", "omarchy-mouse-utils find")')
    print('  o.bind("SUPER + SHIFT + X", "Crosshairs", "omarchy-mouse-utils crosshairs")\n')
    print("Both are click-through: everything underneath keeps working while they show.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="omarchy-mouse-utils",
        description="Find the pointer, or make it impossible to lose.",
        epilog="With no command, the Omarchy menu opens.")
    p.add_argument("command", nargs="?",
                   help="find, crosshairs, ring, off, track, where, status, setup")
    p.add_argument("-t", "--toggle", action="store_true", default=True,
                   help="a second call turns it off (the default)")
    p.add_argument("-k", "--keep", dest="toggle", action="store_false",
                   help="do not turn it off, always start a new one")
    p.add_argument("-f", "--fade", type=int,
                   help="milliseconds before it disappears (0 stays up)")
    p.add_argument("-w", "--wait", action="store_true", help="stay until the overlay ends")
    p.add_argument("--idle", type=float, help="for track: stop after this many idle seconds")
    p.add_argument("-V", "--version", action="version",
                   version=f"omarchy-mouse-utils {__version__}")
    args = p.parse_args(argv)

    commands = {"find": cmd_find, "crosshairs": cmd_crosshairs, "ring": cmd_ring,
                "off": cmd_off, "track": cmd_track, "where": cmd_where,
                "status": cmd_status, "setup": cmd_setup, "menu": cmd_menu}
    if args.command is None:
        return cmd_menu(args)
    if args.command not in commands:
        print(f"omarchy-mouse-utils: unknown command {args.command!r}", file=sys.stderr)
        return 2
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

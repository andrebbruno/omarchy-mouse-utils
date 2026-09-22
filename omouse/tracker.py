"""The cursor feed: one line of "x y" per change, for the overlay to follow.

The overlay cannot ask for the pointer itself — a window that is transparent to input
never sees it, and one that is not would swallow every click. So the position comes in
from outside, on a pipe, from here.

Only changes are sent. A cursor that is not moving is the common case, and a stream
that repeats the same coordinates sixty times a second wakes the overlay up sixty
times to redraw exactly what is already on screen.
"""
from __future__ import annotations

import sys
import time

from .hypr import Hyprland, HyprlandError


def feed(hyprland: Hyprland, write, sleep=time.sleep, hz: int = 60,
         limit: int | None = None, idle_after: float = 0.0) -> int:
    """Write "x y" lines while the cursor moves. Returns how many lines were written.

    `limit` stops after that many polls, which is what the tests use instead of the
    clock. `idle_after` ends the feed when the cursor has been still that long, which
    is how the spotlight knows to fade out.
    """
    interval = 1.0 / max(1, hz)
    last: tuple[int, int] | None = None
    written = 0
    still_since = 0.0
    polls = 0

    while limit is None or polls < limit:
        polls += 1
        try:
            position = hyprland.cursor()
        except HyprlandError:
            return written                      # Hyprland went away; so do we
        if position != last:
            write(f"{position[0]} {position[1]}\n")
            written += 1
            last = position
            still_since = 0.0
        elif idle_after:
            still_since += interval
            if still_since >= idle_after:
                return written
        sleep(interval)
    return written


def run(hz: int = 60, idle_after: float = 0.0) -> int:
    """The `track` command: stdout, flushed per line, until the pipe closes."""
    def write(line: str) -> None:
        sys.stdout.write(line)
        sys.stdout.flush()

    try:
        feed(Hyprland(), write, hz=hz, idle_after=idle_after)
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    except HyprlandError as e:
        print(f"omarchy-mouse-utils: {e}", file=sys.stderr)
        return 1
    return 0

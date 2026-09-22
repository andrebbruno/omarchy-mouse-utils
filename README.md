# Mouse Utilities for Omarchy

Find the pointer, or make it impossible to lose. A port of
[PowerToys' mouse utilities](https://learn.microsoft.com/windows/powertoys/mouse-utilities)
— Find My Mouse, Mouse Highlighter and Mouse Crosshairs — to [Omarchy](https://omarchy.org).

*[Leia em português](README.pt-BR.md)*

```bash
omarchy-mouse-utils find         # a spotlight that fades once you have seen it
omarchy-mouse-utils crosshairs   # lines through the pointer, for a screencast
omarchy-mouse-utils ring         # a highlight around it
omarchy-mouse-utils off          # stop whatever is showing
```

All three are **click-through**: everything underneath keeps working while they are up.
Nothing is captured, nothing is blocked — you can carry on clicking, dragging and typing
with the crosshairs still following you.

## How it works, and why it had to

A Wayland overlay has a choice: take pointer input, or be invisible to it. Taking it
would swallow every click; not taking it means the overlay cannot see the pointer at
all. So the position comes from outside — `omarchy-mouse-utils track` reads Hyprland's
IPC socket and writes one line per move, and the overlay follows that.

The socket matters. `hyprctl cursorpos` costs about **25 ms** — a process spawn, a
connection, a parse — and a spotlight that follows the pointer asks sixty times a
second. The same question straight down the socket costs **0.16 ms**, which is what
makes the whole thing affordable.

Only changes are sent: a still pointer produces no traffic, so a crosshair left on
during a long meeting costs nothing.

## Install

### Arch / Omarchy

```bash
sudo pacman -U omarchy-mouse-utils-*-any.pkg.tar.zst   # from Releases
omarchy-mouse-utils setup
```

In `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + SHIFT + M", "Find the pointer", "omarchy-mouse-utils find")
o.bind("SUPER + SHIFT + X", "Crosshairs", "omarchy-mouse-utils crosshairs")
```

`crosshairs` and `ring` toggle: the same keybinding turns them off again. `find` always
shows, and fades by itself.

Settings in `~/.config/omarchy-mouse-utils/config.json`:

```json
{ "colour": "#ff8800", "thickness": 2, "radius": 110, "dim": 0.55, "fade_after": 1200, "hz": 60 }
```

Leaving `colour` empty follows your theme's accent.

### Elsewhere

`pipx install git+https://github.com/andrebbruno/omarchy-mouse-utils`, with `quickshell`.
The overlay needs a wlroots compositor and the tracker needs Hyprland's IPC socket.

## Commands

```
omarchy-mouse-utils              the menu
omarchy-mouse-utils find         the spotlight (fades after a moment)
omarchy-mouse-utils crosshairs   lines that follow the pointer
omarchy-mouse-utils ring         a circle around it
omarchy-mouse-utils off          stop it
omarchy-mouse-utils where        where the pointer is, and on which monitor
omarchy-mouse-utils track        the position feed, one "x y" per line
omarchy-mouse-utils status       what is showing, and the settings
```

`track` is useful on its own — it is a cursor position feed anything can read.

## Development

```bash
python -m pytest tests -q     # 36 tests, no compositor needed
```

The socket protocol, the monitor geometry (including scaled outputs) and the feed's
throttling are Python and tested against a fake pointer; the overlay is QML and was
driven on a real desktop — the spotlight, the crosshairs and, most importantly, a
click landing in the window underneath while the overlay was up.

## License

MIT © Andre Bruno

import json
import os

import pytest

from omouse import cli


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(cli, "STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(cli, "PID_FILE", str(tmp_path / "state" / "overlay.pid"))
    monkeypatch.setattr(cli, "accent", lambda: "#7aa2f7")
    monkeypatch.setattr(cli.menu, "notify", lambda *a, **k: None)
    monkeypatch.setattr(cli.launcher, "quickshell", lambda: "/usr/bin/qs")
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    return tmp_path


class Started:
    def __init__(self, pid=4242):
        self.pid = pid
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return self


def args(**kwargs):
    base = dict(toggle=True, fade=None, wait=False, idle=None)
    base.update(kwargs)
    return type("Args", (), base)()


def test_find_starts_the_overlay_in_spotlight_mode(home, monkeypatch):
    started = Started()
    monkeypatch.setattr(cli.subprocess, "Popen", started)
    assert cli.cmd_find(args()) == 0
    options = json.loads(started.calls[0][1]["env"]["OMARCHY_MOUSE_OPTIONS"])
    assert options["mode"] == "spotlight"
    assert options["accent"] == "#7aa2f7"
    assert options["fade_after"] > 0


def test_crosshairs_stay_up(home, monkeypatch):
    started = Started()
    monkeypatch.setattr(cli.subprocess, "Popen", started)
    cli.cmd_crosshairs(args())
    options = json.loads(started.calls[0][1]["env"]["OMARCHY_MOUSE_OPTIONS"])
    assert options["mode"] == "crosshairs"
    assert options["fade_after"] == 0


def test_the_fade_can_be_overridden(home, monkeypatch):
    started = Started()
    monkeypatch.setattr(cli.subprocess, "Popen", started)
    cli.cmd_crosshairs(args(fade=3000))
    options = json.loads(started.calls[0][1]["env"]["OMARCHY_MOUSE_OPTIONS"])
    assert options["fade_after"] == 3000


def test_the_pid_is_remembered(home, monkeypatch):
    monkeypatch.setattr(cli.subprocess, "Popen", Started(pid=1234))
    cli.cmd_crosshairs(args())
    assert (home / "state" / "overlay.pid").read_text(encoding="utf-8") == "1234"


def test_a_second_call_turns_it_off(home, monkeypatch):
    """The keybinding is the same one both times; it has to be a toggle."""
    monkeypatch.setattr(cli.subprocess, "Popen", Started(pid=1234))
    cli.cmd_crosshairs(args())
    killed = []
    monkeypatch.setattr(cli.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    assert cli.cmd_crosshairs(args()) == 0
    assert killed and killed[-1][0] == 1234


def test_keep_starts_another_one_instead(home, monkeypatch):
    started = Started(pid=1234)
    monkeypatch.setattr(cli.subprocess, "Popen", started)
    cli.cmd_crosshairs(args())
    monkeypatch.setattr(cli.os, "kill", lambda pid, sig: None)
    cli.cmd_crosshairs(args(toggle=False))
    assert len(started.calls) == 2


def test_a_stale_pid_is_not_taken_for_a_running_overlay(home, monkeypatch):
    os.makedirs(home / "state", exist_ok=True)
    (home / "state" / "overlay.pid").write_text("999999", encoding="utf-8")

    def gone(pid, sig):
        raise ProcessLookupError()
    monkeypatch.setattr(cli.os, "kill", gone)
    assert cli.running_pid() is None


def test_a_corrupt_pid_file_is_not_an_error(home):
    os.makedirs(home / "state", exist_ok=True)
    (home / "state" / "overlay.pid").write_text("not a pid", encoding="utf-8")
    assert cli.running_pid() is None


def test_off_with_nothing_showing(home, capsys):
    assert cli.cmd_off(args()) == 1
    assert "Nothing" in capsys.readouterr().out


def test_a_missing_quickshell_is_reported(home, monkeypatch, capsys):
    monkeypatch.setattr(cli.launcher, "quickshell", lambda: None)
    assert cli.cmd_find(args()) == 127
    assert "quickshell is not installed" in capsys.readouterr().err


def test_where_prints_the_position_and_the_monitor(home, monkeypatch, capsys):
    class FakeHyprland:
        def cursor(self):
            return (488, 274)

        def monitor_at(self, x, y):
            return {"name": "DP-1"}
    monkeypatch.setattr(cli, "Hyprland", lambda *a, **k: FakeHyprland())
    assert cli.cmd_where(args()) == 0
    assert capsys.readouterr().out.strip() == "488, 274 on DP-1"


def test_where_without_hyprland(home, monkeypatch, capsys):
    class Broken:
        def cursor(self):
            raise cli.HyprlandError("no Hyprland instance")
    monkeypatch.setattr(cli, "Hyprland", lambda *a, **k: Broken())
    assert cli.cmd_where(args()) == 1
    assert "no Hyprland" in capsys.readouterr().err


def test_settings_come_from_the_config(home, monkeypatch):
    (home / "config.json").write_text(json.dumps({"thickness": 5, "radius": 200}),
                                      encoding="utf-8")
    started = Started()
    monkeypatch.setattr(cli.subprocess, "Popen", started)
    cli.cmd_ring(args())
    options = json.loads(started.calls[0][1]["env"]["OMARCHY_MOUSE_OPTIONS"])
    assert options["thickness"] == 5 and options["radius"] == 200


def test_an_unknown_command(home, capsys):
    assert cli.main(["frobnicate"]) == 2

import json
import os

import pytest

from omouse.hypr import Hyprland, HyprlandError, parse_position, socket_path


def test_a_position_is_two_numbers():
    assert parse_position("488, 274") == (488, 274)
    assert parse_position(" 0,0 ") == (0, 0)
    assert parse_position("1920, 1080\n") == (1920, 1080)


def test_a_float_position_is_rounded_towards_zero():
    assert parse_position("488.7, 274.2") == (488, 274)


def test_anything_else_is_refused():
    for junk in ("", "488", "a, b", "1, 2, 3", "no cursor"):
        with pytest.raises(HyprlandError):
            parse_position(junk)


def test_the_socket_path_is_built_from_the_instance(tmp_path):
    instance = tmp_path / "hypr" / "abc123"
    instance.mkdir(parents=True)
    (instance / ".socket.sock").write_text("", encoding="utf-8")
    assert socket_path(str(tmp_path), "abc123") == str(instance / ".socket.sock")


def test_the_instance_is_worked_out_when_it_is_not_in_the_environment(tmp_path):
    instance = tmp_path / "hypr" / "onlyone"
    instance.mkdir(parents=True)
    (instance / ".socket.sock").write_text("", encoding="utf-8")
    assert socket_path(str(tmp_path), None).endswith(os.path.join("onlyone", ".socket.sock"))


def test_no_hyprland_at_all_is_reported(tmp_path):
    with pytest.raises(HyprlandError):
        socket_path(str(tmp_path), None)


def test_a_missing_socket_is_reported(tmp_path):
    (tmp_path / "hypr" / "abc").mkdir(parents=True)
    with pytest.raises(HyprlandError):
        socket_path(str(tmp_path), "abc")


# ---------------------------------------------------------------- monitors

class FakeHyprland(Hyprland):
    def __init__(self, answers):
        super().__init__(path="/nowhere")
        self.answers = answers
        self.asked = []

    def ask(self, command):
        self.asked.append(command)
        return self.answers[command]


MONITORS = [
    {"name": "DP-1", "x": 0, "y": 0, "width": 2560, "height": 1440, "scale": 1},
    {"name": "HDMI-A-1", "x": 2560, "y": 0, "width": 1920, "height": 1080, "scale": 1},
]


def monitors_answer(monitors=MONITORS):
    return {"j/monitors": json.dumps(monitors), "cursorpos": "10, 10"}


def test_the_monitor_under_the_pointer():
    hypr = FakeHyprland(monitors_answer())
    assert hypr.monitor_at(100, 100)["name"] == "DP-1"
    assert hypr.monitor_at(3000, 500)["name"] == "HDMI-A-1"


def test_a_point_off_every_monitor():
    assert FakeHyprland(monitors_answer()).monitor_at(9999, 9999) is None


def test_scaling_is_taken_into_account():
    """A 3840px monitor at scale 2 is 1920 wide in layout coordinates."""
    scaled = [{"name": "eDP-1", "x": 0, "y": 0, "width": 3840, "height": 2160, "scale": 2}]
    hypr = FakeHyprland(monitors_answer(scaled))
    assert hypr.monitor_at(1900, 1000)["name"] == "eDP-1"
    assert hypr.monitor_at(2000, 1000) is None


def test_the_edge_belongs_to_the_monitor_on_the_left():
    hypr = FakeHyprland(monitors_answer())
    assert hypr.monitor_at(2559, 0)["name"] == "DP-1"
    assert hypr.monitor_at(2560, 0)["name"] == "HDMI-A-1"


def test_unreadable_monitor_json_is_reported():
    hypr = FakeHyprland({"j/monitors": "{not json"})
    with pytest.raises(HyprlandError):
        hypr.monitors()


def test_the_cursor_question_is_the_short_one():
    hypr = FakeHyprland(monitors_answer())
    assert hypr.cursor() == (10, 10)
    assert hypr.asked == ["cursorpos"]

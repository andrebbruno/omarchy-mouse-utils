from omouse.hypr import HyprlandError
from omouse.tracker import feed


class Cursor:
    """A pointer that walks through a list of positions, one per poll."""

    def __init__(self, positions, fail_after=None):
        self.positions = list(positions)
        self.fail_after = fail_after
        self.polls = 0

    def cursor(self):
        self.polls += 1
        if self.fail_after is not None and self.polls > self.fail_after:
            raise HyprlandError("Hyprland went away")
        index = min(self.polls - 1, len(self.positions) - 1)
        return self.positions[index]


def collect():
    lines = []
    return lines, lines.append


def test_every_move_is_written():
    lines, write = collect()
    feed(Cursor([(1, 1), (2, 2), (3, 3)]), write, sleep=lambda s: None, limit=3)
    assert lines == ["1 1\n", "2 2\n", "3 3\n"]


def test_a_still_pointer_is_not_written_again():
    """Sixty identical lines a second would wake the overlay up to redraw nothing."""
    lines, write = collect()
    feed(Cursor([(5, 5)]), write, sleep=lambda s: None, limit=30)
    assert lines == ["5 5\n"]


def test_it_starts_by_saying_where_the_pointer_is():
    lines, write = collect()
    feed(Cursor([(7, 9)]), write, sleep=lambda s: None, limit=1)
    assert lines == ["7 9\n"]


def test_moving_back_to_a_previous_spot_is_a_move():
    lines, write = collect()
    feed(Cursor([(1, 1), (2, 2), (1, 1)]), write, sleep=lambda s: None, limit=3)
    assert lines == ["1 1\n", "2 2\n", "1 1\n"]


def test_hyprland_going_away_ends_the_feed_quietly():
    lines, write = collect()
    written = feed(Cursor([(1, 1)], fail_after=1), write, sleep=lambda s: None, limit=100)
    assert written == 1


def test_an_idle_pointer_ends_the_feed_when_asked():
    """This is how the spotlight knows to fade: nothing has moved for a while."""
    lines, write = collect()
    cursor = Cursor([(1, 1)])
    feed(cursor, write, sleep=lambda s: None, hz=100, idle_after=0.1, limit=1000)
    assert cursor.polls < 20               # ~10 polls of 10ms, not a thousand


def test_without_idle_it_keeps_going():
    cursor = Cursor([(1, 1)])
    lines, write = collect()
    feed(cursor, write, sleep=lambda s: None, hz=100, limit=200)
    assert cursor.polls == 200


def test_the_poll_rate_sets_the_sleep():
    slept = []
    feed(Cursor([(1, 1)]), lambda line: None, sleep=slept.append, hz=60, limit=2)
    assert all(abs(s - 1 / 60) < 1e-9 for s in slept)


def test_a_silly_rate_does_not_divide_by_zero():
    slept = []
    feed(Cursor([(1, 1)]), lambda line: None, sleep=slept.append, hz=0, limit=1)
    assert slept == [1.0]

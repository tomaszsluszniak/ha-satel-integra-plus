"""Arming mode settling: a partition armed in mode 1-3 must not flash as mode 0.

Run: PYTHONPATH=<satel-integra 1.6> python tests/test_arm_modes.py
"""

import importlib
import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import ha_stubs  # noqa: E402

ha_stubs.install()

spec = importlib.util.spec_from_file_location(
    "cc_satel",
    Path(__file__).parent.parent / "custom_components/satel_integra/__init__.py",
    submodule_search_locations=[
        str(Path(__file__).parent.parent / "custom_components/satel_integra")
    ],
)
cc = importlib.util.module_from_spec(spec)
sys.modules["cc_satel"] = cc
spec.loader.exec_module(cc)

coord = importlib.import_module("cc_satel.coordinator")
acp = importlib.import_module("cc_satel.alarm_control_panel")
AS = acp.AlarmState
State = ha_stubs.AlarmControlPanelState
T = coord.ARM_MODE_SETTLE_TIME


class Settler:
    """Feeds successive panel states like the coordinator does."""

    def __init__(self, expected=None):
        self.published = {}
        self.pending = {}
        self.expected = dict(expected or {})

    def __call__(self, data, now):
        self.published = coord.settle_arm_modes(
            data, self.published, self.pending, self.expected, now
        )
        return {
            n: acp.partition_alarm_state(self.published, n, True) for n in (1, 2, 3, 4)
        }


def test_mode3_without_exit_delay():
    s = Settler()
    s({AS.ARMED_MODE0: [], AS.ARMED_MODE3: []}, 0.0)  # disarmed
    # 0x0A arrives first: arming, not "full arming"
    st = s({AS.ARMED_MODE0: [3, 4], AS.ARMED_MODE3: []}, 10.0)
    assert st[3] == st[4] == State.ARMING, st
    # 0x0C ~3 s later
    st = s({AS.ARMED_MODE0: [3, 4], AS.ARMED_MODE3: [3, 4]}, 13.3)
    assert st[3] == st[4] == State.ARMED_NIGHT, st
    assert not s.pending


def test_mode3_after_exit_delay():
    s = Settler()
    s({AS.ARMED_MODE0: []}, 0.0)
    st = s({AS.EXIT_COUNTDOWN_OVER_10: [1, 2], AS.ARMED_MODE0: []}, 1.0)
    assert st[1] == State.ARMING
    st = s({AS.EXIT_COUNTDOWN_OVER_10: [], AS.ARMED_MODE0: [1, 2]}, 20.0)
    assert st[1] == st[2] == State.ARMING, st
    st = s({AS.ARMED_MODE0: [1, 2], AS.ARMED_MODE3: [1, 2]}, 22.9)
    assert st[1] == st[2] == State.ARMED_NIGHT, st


def test_real_mode0_after_settle_time():
    s = Settler()
    s({AS.ARMED_MODE0: []}, 0.0)
    st = s({AS.ARMED_MODE0: [1]}, 5.0)
    assert st[1] == State.ARMING and s.pending == {1: 5.0 + T}
    st = s({AS.ARMED_MODE0: [1]}, 5.0 + T)
    assert st[1] == State.ARMED_AWAY and not s.pending
    # stays mode 0 on later updates
    st = s({AS.ARMED_MODE0: [1], AS.ARMED_MODE3: [2]}, 100.0)
    assert st[1] == State.ARMED_AWAY and not s.pending


def test_mode0_armed_from_ha_is_shown_at_once():
    s = Settler(expected={1: 999.0})
    s({AS.ARMED_MODE0: []}, 0.0)
    st = s({AS.ARMED_MODE0: [1]}, 1.0)
    assert st[1] == State.ARMED_AWAY and not s.expected and not s.pending


def test_already_armed_at_start_and_disarm():
    s = Settler()
    st = s({AS.ARMED_MODE0: [1, 2]}, 0.0)  # first report: no holding
    assert st[1] == State.ARMED_AWAY
    st = s({AS.ARMED_MODE0: [2]}, 1.0)
    assert st[1] == State.DISARMED and st[2] == State.ARMED_AWAY
    # held partition disarmed before its mode arrived
    s({AS.ARMED_MODE0: [1, 2]}, 2.0)
    assert 1 in s.pending
    st = s({AS.ARMED_MODE0: [2]}, 3.0)
    assert st[1] == State.DISARMED and not s.pending


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)

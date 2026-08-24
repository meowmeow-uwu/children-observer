from __future__ import annotations

import numpy as np

from module_edge_firmware.demo_stream.fall import FallStateEngine, box_iou


def _pose(*, lying: bool, y: float = 0.5) -> np.ndarray:
    points = np.zeros((17, 3), dtype=np.float32)
    if lying:
        points[:, 0] = np.linspace(0.25, 0.75, 17)
        points[:, 1] = y
    else:
        points[:, 0] = 0.5
        points[:, 1] = np.linspace(y - 0.25, y + 0.25, 17)
    points[:, 2] = 0.95
    return points


def test_box_iou_matches_overlapping_pose_to_child_track():
    assert box_iou([0.1, 0.1, 0.5, 0.5], [0.2, 0.2, 0.6, 0.6]) > 0.3
    assert box_iou([0.1, 0.1, 0.2, 0.2], [0.8, 0.8, 0.9, 0.9]) == 0.0


def test_fall_state_confirms_once_then_recovers():
    engine = FallStateEngine(
        still_seconds=2.0,
        velocity_threshold=0.10,
        still_velocity_threshold=0.05,
        cooldown_seconds=30.0,
    )
    engine.update(7, _pose(lying=False, y=0.3), 0.0)
    suspected, emitted = engine.update(7, _pose(lying=True, y=0.7), 500.0)
    assert suspected.state == "suspected"
    assert not emitted

    waiting, emitted = engine.update(7, _pose(lying=True, y=0.7), 2_000.0)
    assert waiting.state == "suspected"
    assert not emitted

    confirmed, emitted = engine.update(7, _pose(lying=True, y=0.7), 2_600.0)
    assert confirmed.state == "confirmed"
    assert emitted

    still_confirmed, emitted = engine.update(7, _pose(lying=True, y=0.7), 3_100.0)
    assert still_confirmed.state == "confirmed"
    assert not emitted

    recovered, emitted = engine.update(7, _pose(lying=False, y=0.7), 3_600.0)
    assert recovered.state == "recovered"
    assert not emitted


def test_first_visible_lying_pose_enters_suspected_state():
    engine = FallStateEngine(
        still_seconds=2.0,
        velocity_threshold=0.1,
        still_velocity_threshold=0.05,
    )
    annotation, emitted = engine.update(9, _pose(lying=True), 0.0)
    assert annotation.state == "suspected"
    assert not emitted


def test_fall_state_is_isolated_per_track_and_pruned():
    engine = FallStateEngine(
        still_seconds=1.0,
        velocity_threshold=0.1,
        still_velocity_threshold=0.05,
        track_ttl_seconds=1.0,
    )
    engine.update(1, _pose(lying=False), 0.0)
    engine.update(2, _pose(lying=False), 0.0)
    engine.update(1, _pose(lying=True, y=0.8), 500.0)
    engine.prune(2_000.0)
    assert 1 not in engine._states
    assert 2 not in engine._states


def test_fall_state_reset_clears_tracks_and_cooldown():
    engine = FallStateEngine(
        still_seconds=1.0,
        velocity_threshold=0.1,
        still_velocity_threshold=0.05,
    )
    engine.update(4, _pose(lying=True), 0.0)
    engine._last_alert_ms[4] = 100.0

    engine.reset()

    assert engine._states == {}
    assert engine._last_alert_ms == {}

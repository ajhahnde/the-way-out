"""PressurePlate charge/trip behaviour and Lever single-shot toggle.
Both use lazy-built surfaces, so they need a video context — provided
by conftest's dummy SDL setup."""
import pygame

from interactables import Lever, PressurePlate
from settings import PLATE_TRIGGER_DELAY


def _plate():
    return PressurePlate((0, 0), [pygame.sprite.Group()], gate_group=("ord", 0))


def _lever():
    return Lever((0, 0), [pygame.sprite.Group()], gate_group=("ord", 0))


# --- PressurePlate -------------------------------------------------------

def test_plate_starts_idle():
    p = _plate()
    assert p.activated is False
    assert p.charge == 0.0


def test_plate_charge_accumulates_below_threshold():
    p = _plate()
    half = PLATE_TRIGGER_DELAY / 2
    tripped = p.step_on(half)
    assert tripped is False
    assert p.activated is False
    assert p.charge == half


def test_plate_trips_at_threshold_exactly_once():
    p = _plate()
    # Two equal halves exactly hit PLATE_TRIGGER_DELAY — that's the
    # tripping frame, and step_on returns True only on it.
    half = PLATE_TRIGGER_DELAY / 2
    assert p.step_on(half) is False
    assert p.step_on(half) is True
    assert p.activated is True
    # Subsequent ticks must not re-fire — the level opens the gate
    # exactly once.
    assert p.step_on(0.1) is False


def test_plate_stays_tripped_after_step_off():
    p = _plate()
    p.step_on(PLATE_TRIGGER_DELAY)        # trip it
    p.step_off()
    assert p.activated is True            # still down


def test_step_off_resets_charge_only_while_untripped():
    p = _plate()
    p.step_on(PLATE_TRIGGER_DELAY / 3)
    p.step_off()
    assert p.charge == 0.0
    # After tripping, charge is frozen (the plate stays down forever),
    # so step_off must be a no-op on the charge.
    p.step_on(PLATE_TRIGGER_DELAY)        # trip
    charge_after_trip = p.charge
    p.step_off()
    assert p.charge == charge_after_trip


# --- Lever ---------------------------------------------------------------

def test_lever_starts_inactive():
    lev = _lever()
    assert lev.activated is False


def test_lever_use_toggles_once_and_returns_true_only_first_time():
    lev = _lever()
    assert lev.use() is True
    assert lev.activated is True
    # Second pull is a no-op: returns False, stays activated.
    assert lev.use() is False
    assert lev.activated is True

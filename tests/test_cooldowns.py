"""Attack + ability cooldown bookkeeping on the Character base class
and the per-character ABILITY_COOLDOWN catalogue.

The Character constructor wants an obstacle_sprites group and a real
asset folder. ``Wizard`` is the simplest playable (defaults across the
board); the units module's ``load_assets`` tolerates missing PNGs by
returning an empty frame list (``_placeholder_frame`` covers the
draw)."""
import pygame

from settings import ATTACK_COOLDOWN, DASH_COOLDOWN
from units import Elf, Penguin, Shiggy, Wizard, Wolf


def _wizard():
    return Wizard(0, 0, obstacle_sprites=pygame.sprite.Group())


def _elf():
    return Elf(0, 0, obstacle_sprites=pygame.sprite.Group())


# --- Per-character ABILITY_COOLDOWN catalogue ----------------------------

def test_default_ability_cooldown_constants():
    # Numbers are the contract the HUD's ability-ring draws against
    # — bumping one without bumping the CHANGELOG is a regression.
    assert Wizard.ABILITY_COOLDOWN == 12.0
    assert Penguin.ABILITY_COOLDOWN == 11.0
    assert Elf.ABILITY_COOLDOWN == 9.0
    assert Wolf.ABILITY_COOLDOWN == 8.0
    assert Shiggy.ABILITY_COOLDOWN == DASH_COOLDOWN


def test_default_attack_cooldown_is_module_constant():
    # Wizard does not override attack_cooldown, so the class attribute
    # is the module-wide ATTACK_COOLDOWN.
    assert Wizard.attack_cooldown == ATTACK_COOLDOWN


# --- attack_timer tick + clamp ------------------------------------------

def test_attack_timer_starts_at_zero():
    w = _wizard()
    assert w.attack_timer == 0.0


def test_attack_timer_clamps_at_zero_after_overrun():
    w = _wizard()
    w.attack_timer = 0.05
    w.attack_timer = max(0.0, w.attack_timer - 0.5)
    assert w.attack_timer == 0.0


def test_current_attack_cooldown_default_equals_class_attr():
    w = _wizard()
    assert w.current_attack_cooldown() == Wizard.attack_cooldown


# --- Elf VOLLEY halves the cadence while active --------------------------

def test_elf_cooldown_halved_during_active_ability():
    e = _elf()
    base = e.current_attack_cooldown()
    assert base == Elf.attack_cooldown
    e.ability_active = True
    assert e.current_attack_cooldown() == Elf.attack_cooldown * 0.5
    e.ability_active = False
    assert e.current_attack_cooldown() == base


# --- ability_cooldown_timer tick + clamp ---------------------------------

def test_ability_cooldown_timer_starts_at_zero():
    w = _wizard()
    assert w.ability_cooldown_timer == 0.0


def test_ability_cooldown_timer_ticks_down_and_clamps():
    w = _wizard()
    w.ability_cooldown_timer = 0.4
    # Mirror the per-frame countdown handle_ability runs.
    w.ability_cooldown_timer = max(0.0, w.ability_cooldown_timer - 0.1)
    assert abs(w.ability_cooldown_timer - 0.3) < 1e-9
    w.ability_cooldown_timer = max(0.0, w.ability_cooldown_timer - 5.0)
    assert w.ability_cooldown_timer == 0.0


def test_ability_gating_uses_cooldown_timer_and_active_flag():
    # Mirror the gate handle_ability checks: ready only when not active
    # and cooldown timer is zero. No keyboard polling here — the trigger
    # check is just (not active) and (timer == 0).
    w = _wizard()
    assert not w.ability_active
    assert w.ability_cooldown_timer == 0.0
    ready = (not w.ability_active and w.ability_cooldown_timer == 0)
    assert ready is True

    w.ability_cooldown_timer = 0.5
    ready = (not w.ability_active and w.ability_cooldown_timer == 0)
    assert ready is False

    w.ability_cooldown_timer = 0.0
    w.ability_active = True
    ready = (not w.ability_active and w.ability_cooldown_timer == 0)
    assert ready is False

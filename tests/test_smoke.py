"""Headless smoke tests for core project data and imports."""

import importlib

from simulator.config import DISABILITIES, REFLECTIONS, SCENARIOS, GameState


def test_core_modules_import_without_starting_game() -> None:
    for module_name in (
        "simulator.audio",
        "simulator.config",
        "simulator.dialogue",
        "simulator.effects",
        "simulator.fx.audio_fx",
        "simulator.fx.cognitive",
        "simulator.fx.core",
        "simulator.fx.movement",
        "simulator.fx.postfx",
        "simulator.fx.registry",
        "simulator.fx.visual",
        "simulator.human",
        "simulator.lab",
        "simulator.npc",
        "simulator.player",
        "simulator.world",
    ):
        assert importlib.import_module(module_name) is not None


def test_catalogs_have_required_entries() -> None:
    assert {"none", "adhd", "schizophrenia", "wheelchair", "visual", "deaf", "dyslexia"} <= DISABILITIES.keys()
    assert {"school", "train", "zombies"} == SCENARIOS.keys()
    assert DISABILITIES.keys() == REFLECTIONS.keys()


def test_default_game_state_is_valid() -> None:
    state = GameState()
    assert state.disability is None
    assert state.scenario in SCENARIOS
    assert 0 <= state.blindness <= 1

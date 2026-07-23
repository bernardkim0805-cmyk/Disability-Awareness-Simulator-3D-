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
        "simulator.lab_demo",
        "simulator.lab_state",
        "simulator.npc",
        "simulator.player",
        "simulator.world",
        "simulator.windowing",
    ):
        assert importlib.import_module(module_name) is not None


def test_catalogs_have_required_entries() -> None:
    assert {"none", "adhd", "schizophrenia", "wheelchair", "visual", "deaf", "dyslexia"} <= DISABILITIES.keys()
    assert {"school", "train", "zombies", "kitchen"} <= set(SCENARIOS)
    assert DISABILITIES.keys() == REFLECTIONS.keys()


def test_default_game_state_is_valid() -> None:
    state = GameState()
    assert state.disability is None
    assert state.scenario in SCENARIOS
    assert 0 <= state.blindness <= 1


def test_supported_window_sizes_parse_without_platform_paths() -> None:
    from simulator.windowing import (
        requested_effects,
        requested_experience,
        requested_capture,
        requested_scenario,
        requested_window_size,
    )

    assert requested_window_size(["--window-size", "1280x720"]) == (1280, 720)
    assert requested_window_size(["--window-size", "1920x1080"]) == (1920, 1080)
    assert requested_window_size(["--window-size", "bad"]) is None
    assert requested_scenario(["--scenario", "train"], set(SCENARIOS)) == "train"
    assert requested_scenario(["--scenario", "unknown"], set(SCENARIOS)) is None
    assert requested_experience(["--experience", "deaf"], set(DISABILITIES)) == "deaf"
    assert requested_effects(
        ["--effect", "glaucoma:.3", "--effect", "tinnitus:2"],
        {"glaucoma", "tinnitus"},
    ) == {"glaucoma": .3, "tinnitus": 1.0}
    assert requested_capture(["--capture", "review.png"]) == "review.png"

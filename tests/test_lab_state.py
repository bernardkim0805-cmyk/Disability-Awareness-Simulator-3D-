"""Headless tests for Accessibility Lab selection and compatibility rules."""

from simulator.config import GameState
from simulator.fx.registry import EFFECTS, PRESETS
from simulator.lab_state import (
    ORIGINAL_EXPERIENCES,
    apply_preset,
    educational_fields_complete,
    incompatible_effects,
    reset_to_baseline,
    select_experience,
    toggle_effect,
    toggle_split,
)


class UnsupportedCamera:
    filter_quad = None

    @property
    def shader(self):
        return None

    @shader.setter
    def shader(self, value) -> None:
        raise RuntimeError("unsupported shader")


def test_all_original_experiences_are_available_with_metadata() -> None:
    assert set(ORIGINAL_EXPERIENCES) == {
        "none", "adhd", "schizophrenia", "wheelchair", "visual", "deaf", "dyslexia"
    }
    assert educational_fields_complete()


def test_selecting_original_experience_updates_state() -> None:
    state = GameState()
    assert select_experience(state, "wheelchair") == set()
    assert state.disability == "wheelchair"


def test_incompatible_combinations_are_removed_and_blocked() -> None:
    state = GameState()
    state.lab_effects = {"glaucoma": .6, "tinnitus": .4}
    removed = select_experience(state, "visual")
    assert removed == {"glaucoma"}
    assert state.lab_effects == {"tinnitus": .4}
    assert toggle_effect(state, "macular") is not None
    assert "Real conditions may coexist" in toggle_effect(state, "macular")

    select_experience(state, "deaf")
    assert "tinnitus" not in state.lab_effects
    assert incompatible_effects("deaf") == {
        key for key, spec in EFFECTS.items() if spec["cat"] == "audio"
    }

    state.lab_effects = {"adhd_fx": .6, "memory": .4}
    assert select_experience(state, "adhd") == {"adhd_fx"}
    assert state.lab_effects == {"memory": .4}


def test_effect_toggle_and_custom_intensity_state() -> None:
    state = GameState()
    assert toggle_effect(state, "glaucoma") is None
    assert state.lab_effects["glaucoma"] == PRESETS["moderate"]
    state.lab_effects["glaucoma"] = .47
    assert state.lab_effects["glaucoma"] == .47
    assert toggle_effect(state, "glaucoma") is None
    assert "glaucoma" not in state.lab_effects
    assert toggle_effect(state, "glaucoma") is None
    assert toggle_effect(state, "glaucoma") is None
    assert "glaucoma" not in state.lab_effects


def test_presets_apply_to_effects_and_original_visual_intensity() -> None:
    state = GameState()
    state.disability = "visual"
    state.lab_effects = {"tinnitus": .2, "memory": .8}
    apply_preset(state, PRESETS["severe"])
    assert state.blindness == PRESETS["severe"]
    assert set(state.lab_effects.values()) == {PRESETS["severe"]}


def test_reset_returns_to_true_baseline() -> None:
    state = GameState()
    state.disability = "schizophrenia"
    state.lab_effects = {"tinnitus": .8}
    state.lab_split = True
    state.blindness = .9
    reset_to_baseline(state)
    assert state.disability == "none"
    assert state.lab_effects == {}
    assert state.lab_split is False
    assert state.blindness == .55


def test_repeated_split_toggling_returns_to_a_clean_state() -> None:
    state = GameState()
    assert toggle_split(state) is True
    assert toggle_split(state) is False
    assert state.lab_split is False


def test_postfx_falls_back_when_shader_is_unsupported(monkeypatch) -> None:
    from simulator.fx import postfx

    monkeypatch.setattr(postfx, "camera", UnsupportedCamera())
    pipeline = postfx.PostFX()
    assert pipeline._attach() is False
    assert pipeline.available is False
    pipeline.apply(pipeline.default_params())


def test_original_visual_experience_contributes_scaled_blur(monkeypatch) -> None:
    from types import SimpleNamespace

    from simulator.fx import core

    applied = {}

    class FakePostFX:
        def default_params(self):
            return {"blur": 0.0, "bypass": 1.0, "split": 0.0}

        def apply(self, params):
            applied.update(params)

    monkeypatch.setattr(core, "get_postfx", lambda: FakePostFX(), raising=False)
    monkeypatch.setattr(core, "utime", SimpleNamespace(dt=.016))
    monkeypatch.setattr(core.STATE, "disability", "visual")
    monkeypatch.setattr(core.STATE, "blindness", .73)
    monkeypatch.setattr(core.STATE, "lab_split", False)

    stack = SimpleNamespace(effects=[], compare_held=False)
    # Redirect the function-local import used by EffectStack.update.
    import simulator.fx.postfx as postfx
    monkeypatch.setattr(postfx, "get_postfx", lambda: FakePostFX())
    core.EffectStack.update(stack)

    assert applied["blur"] == .73
    assert applied["bypass"] == 0.0

"""Testable state and compatibility rules for the Accessibility Lab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import DISABILITIES, REFLECTIONS
from .fx.registry import EFFECTS, PRESETS


@dataclass(frozen=True)
class ExperienceInfo:
    key: str
    name: str
    description: str
    simplified: str
    misconception: str
    assistive: str
    references: str
    preview: str


def _experience(
    key: str,
    simplified: str,
    misconception: str,
    assistive: str,
    references: str,
    preview: str,
) -> ExperienceInfo:
    definition = DISABILITIES[key]
    return ExperienceInfo(
        key=key,
        name=definition["name"],
        description=definition["desc"].replace("\n", " "),
        simplified=simplified,
        misconception=misconception,
        assistive=assistive,
        references=references,
        preview=preview,
    )


ORIGINAL_EXPERIENCES = {
    "none": _experience(
        "none",
        "Baseline removes simulated barriers; it is a comparison, not a typical person.",
        "A baseline is not a claim that everyone without a disability has the same experience.",
        "Accessible design benefits baseline users too.",
        "Project baseline; compare with each scenario reflection.",
        "Selecting baseline clears the full experience and all stackable effects.",
    ),
    "adhd": _experience(
        "adhd",
        "Models attention capture and recovery cost, not the full range of ADHD traits.",
        "ADHD is not laziness or a simple lack of willpower.",
        "Quiet spaces, extra time, coaching, medication, and reduced notifications.",
        "NIMH: Attention-Deficit/Hyperactivity Disorder.",
        "The focus mechanic is active in scenarios; press F to refocus.",
    ),
    "schizophrenia": _experience(
        "schizophrenia",
        "Uses selected perceptual distractions and cannot reproduce an individual lived experience.",
        "Schizophrenia does not mean a split personality and does not imply violence.",
        "Consistent care, medication, therapy, peer support, and low-stress environments.",
        "NIMH: Schizophrenia.",
        "Whispers and a shadow figure preview in the plaza and continue in scenarios.",
    ),
    "wheelchair": _experience(
        "wheelchair",
        "Models route and mobility barriers with one manual-chair control profile.",
        "Wheelchair use does not imply helplessness; environmental barriers create disability.",
        "Step-free routes, working elevators, ramps, lowered controls, and adequate turning space.",
        "WHO: Wheelchair provision guidelines; ADA accessibility guidance.",
        "Seated movement and route barriers activate when a scenario starts.",
    ),
    "visual": _experience(
        "visual",
        "Uses adjustable darkness and fog; most visual impairments are more varied and specific.",
        "Blindness is not always total darkness and visual ability can fluctuate.",
        "Screen readers, magnification, high contrast, tactile cues, and audio description.",
        "NEI: Low Vision and Blindness.",
        "Set intensity here; the readable panel stays undimmed. [ and ] adjust it in scenarios.",
    ),
    "deaf": _experience(
        "deaf",
        "Removes game audio; it does not model the diversity of Deaf identity or residual hearing.",
        "Deaf people are not ignoring speakers, and louder speech is not equivalent to access.",
        "Captions, interpreters, visual alerts, transcripts, and hearing technology when desired.",
        "NIDCD: Hearing, Ear Infections, and Deafness.",
        "Audio is muted immediately and remains muted in scenarios.",
    ),
    "dyslexia": _experience(
        "dyslexia",
        "Uses changing letter order as an analogy; dyslexia is not literally moving text for everyone.",
        "Dyslexia does not indicate low intelligence or poor effort.",
        "Structured literacy, text-to-speech, audiobooks, clear layouts, and additional time.",
        "International Dyslexia Association: Dyslexia Basics.",
        "Scenario signs, questions, and dialogue use the existing dyslexia mechanic.",
    ),
}


def incompatible_effects(experience: str) -> set[str]:
    """Return effects that would duplicate or contradict a full experience."""
    if experience == "visual":
        return {key for key, spec in EFFECTS.items() if spec["cat"] == "visual"}
    if experience == "deaf":
        return {key for key, spec in EFFECTS.items() if spec["cat"] == "audio"}
    if experience == "adhd":
        return {"adhd_fx"}
    return set()


def incompatibility_reason(experience: str, effect_id: str) -> str | None:
    if effect_id not in incompatible_effects(experience):
        return None
    if experience == "visual":
        return "Blocked: the full visual-impairment mode already controls the visual field."
    if experience == "deaf":
        return "Blocked: the full deaf mode removes audio, so another hearing effect would be hidden."
    return "Blocked: the full ADHD experience already supplies its attention mechanic."


def select_experience(state: Any, experience: str) -> set[str]:
    """Select one original experience and remove effects it makes misleading."""
    if experience not in ORIGINAL_EXPERIENCES:
        raise KeyError(experience)
    state.disability = experience
    if experience == "none":
        state.lab_effects.clear()
        state.lab_split = False
        return set()
    removed = set(state.lab_effects).intersection(incompatible_effects(experience))
    for effect_id in removed:
        del state.lab_effects[effect_id]
    return removed


def toggle_effect(state: Any, effect_id: str, default: float = PRESETS["moderate"]) -> str | None:
    """Toggle an effect, returning a user-facing block reason when incompatible."""
    if effect_id not in EFFECTS:
        raise KeyError(effect_id)
    reason = incompatibility_reason(state.disability or "none", effect_id)
    if reason:
        return reason
    if effect_id in state.lab_effects:
        del state.lab_effects[effect_id]
    else:
        state.lab_effects[effect_id] = default
    return None


def apply_preset(state: Any, value: float) -> None:
    for effect_id in state.lab_effects:
        state.lab_effects[effect_id] = value
    if state.disability == "visual":
        state.blindness = value


def reset_to_baseline(state: Any) -> None:
    state.disability = "none"
    state.lab_effects.clear()
    state.lab_split = False
    state.blindness = 0.55


def active_summary(state: Any) -> str:
    experience = ORIGINAL_EXPERIENCES[state.disability or "none"].name
    if state.lab_effects:
        effects = ", ".join(EFFECTS[key]["name"] for key in state.lab_effects)
        return f"Experience: {experience}  |  Effects: {effects}"
    return f"Experience: {experience}  |  Effects: none"


def educational_fields_complete() -> bool:
    required = ("description", "simplified", "misconception", "assistive", "references")
    return all(all(getattr(info, field) for field in required)
               for info in ORIGINAL_EXPERIENCES.values()) and set(REFLECTIONS) == set(ORIGINAL_EXPERIENCES)

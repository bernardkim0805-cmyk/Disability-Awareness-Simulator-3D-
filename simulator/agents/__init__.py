"""Autonomous NPC agent system (self-contained tab).

A data-driven, component-based, event-reactive crowd — each NPC is an
independent agent with its own procedural personality, perception, emotion,
memory and behaviour, driven by an event bus rather than scripted loops.

NOTE ON FIDELITY: this runs on Ursina's fixed-function pipeline with
primitive-built characters, so the realism here is *behavioural* (AAA-style
autonomy, reactions, emotion, ambient life) rather than *rendered* (no true
IK, cloth or facial-muscle simulation — those are approximated on the rig).
"""
from .demo import LivingCityScenario

__all__ = ['LivingCityScenario']

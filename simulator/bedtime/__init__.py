"""Getting Ready for Bed — a nightly-routine home simulation (self-contained tab).

A lived-in modern home (bedroom, hallway, bathroom, closet, laundry) where the
player completes a RANDOMIZED sequence of bedtime tasks. Every disability
reshapes the routine, and mistakes have gentle, educational consequences.

Fidelity note (consistent with the rest of the project): this runs on the
fixed-function pipeline, so realism here is INTERACTIVE and BEHAVIOURAL — real
rooms, objects, task logic, consequences and disability effects — not AAA
rendering (no PBR, IK, volumetric steam, mirror reflections or particle water,
which the shaderless stack cannot draw).
"""
if __package__ in (None, ''):
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from .bedtime import BedtimeScenario

__all__ = ['BedtimeScenario']

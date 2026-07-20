"""Driving simulation (self-contained package — safe for parallel work)."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from .scenario import DrivingScenario

__all__ = ['DrivingScenario']

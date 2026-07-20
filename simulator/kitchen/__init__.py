"""Home Kitchen cooking scenario (kept self-contained in this package so it
never collides with work happening in the rest of the codebase)."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from .kitchen import KitchenScenario

__all__ = ['KitchenScenario']

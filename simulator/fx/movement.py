"""Motor condition simulations. All camera perturbations are applied as
*remembered offsets* — each frame the previous offset is subtracted before
the new one is added — so several movement effects stack cleanly on top of
whatever the player controller did this frame."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math
import random

from ursina import camera, held_keys

from .core import MovementEffect


class CameraOffsetEffect(MovementEffect):
    """Base: additive camera-rotation offsets with automatic removal."""

    def __init__(self, context=None):
        super().__init__(context)
        self._off = [0.0, 0.0, 0.0]

    def _apply(self, x, y, z):
        camera.rotation_x += x - self._off[0]
        camera.rotation_y += y - self._off[1]
        camera.rotation_z += z - self._off[2]
        self._off = [x, y, z]

    def disable(self):
        self._apply(0, 0, 0)
        super().disable()

    def cleanup(self):
        self._apply(0, 0, 0)
        super().cleanup()


def _moving():
    return any(held_keys[k] for k in ('w', 'a', 's', 'd'))


class ParkinsonianTremor(CameraOffsetEffect):
    """Parkinsonian motor signs, translated to a first-person game:
    - 4-6 Hz resting tremor => view/crosshair jitter (worst when still)
    - bradykinesia => movement starts with a delay, then ramps up
    The tremor eases (never vanishes) during intentional movement, matching
    the resting-tremor pattern."""

    def __init__(self, context=None):
        super().__init__(context)
        self.t = random.uniform(0, 9)
        self.was_moving = False
        self.block_until = 0.0
        self.base_speed = None

    def update(self, dt):
        self.t += dt
        moving = _moving()
        # resting tremor: strongest when the hands are 'at rest'
        amp = self.intensity * (1.4 if not moving else .5)
        f = 5.0 * 6.2832                      # ~5 Hz
        self._apply(math.sin(self.t * f) * amp * .4,
                    math.sin(self.t * f * .93 + 1.3) * amp * .3,
                    math.sin(self.t * f * 1.07 + 2.1) * amp * .25)

        # bradykinesia: delayed movement initiation + slow ramp to speed
        player = self.player()
        if not player:
            return
        if self.base_speed is None:
            self.base_speed = player.speed
        if moving and not self.was_moving:
            self.block_until = self.t + .2 + self.intensity * .55
        self.was_moving = moving
        if moving:
            if self.t < self.block_until:
                player.speed = 0
            elif player.speed < self.base_speed:
                player.speed = min(self.base_speed,
                                   player.speed + self.base_speed * dt / .4)
        else:
            player.speed = self.base_speed

    def disable(self):
        player = self.player()
        if player and self.base_speed is not None:
            player.speed = self.base_speed
        super().disable()


class EssentialTremor(CameraOffsetEffect):
    """Essential tremor: a faster (~8 Hz) continuous oscillation that
    *worsens with intentional action* — the opposite pattern to the
    parkinsonian resting tremor above."""

    def __init__(self, context=None):
        super().__init__(context)
        self.t = random.uniform(0, 9)

    def update(self, dt):
        self.t += dt
        amp = self.intensity * (1.2 if _moving() else .45)
        f = 8.0 * 6.2832
        self._apply(math.sin(self.t * f) * amp * .3,
                    0,
                    math.sin(self.t * f * 1.13) * amp * .35)


class VestibularDisorder(CameraOffsetEffect):
    """Inner-ear balance failure: the horizon slowly tilts and drifts, the
    view sways with every step, and walking pulls sideways (imbalance).
    Motion amplifies everything — standing still is the only relief."""

    def __init__(self, context=None):
        super().__init__(context)
        self.t = random.uniform(0, 20)

    def update(self, dt):
        self.t += dt
        base = self.intensity
        motion_boost = 1.8 if _moving() else 1.0
        roll = math.sin(self.t * .45) * 5 * base * motion_boost      # horizon tilt
        drift = math.sin(self.t * .23 + 2) * 3 * base                # slow drift
        sway = math.sin(self.t * 1.7) * 1.6 * base * motion_boost    # step sway
        self._apply(sway, drift, roll)

        player = self.player()
        if player and _moving():
            # imbalance: a lateral push that slowly changes direction
            push = math.sin(self.t * .6) * .8 * base
            player.position += player.right * push * dt

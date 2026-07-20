"""NPCs: articulated humans that stand, wander waypoints or sprint, and talk."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math

from ursina import Entity, Color, Vec3, time, distance_xz, invoke, curve, destroy

from .human import Human


class NPC(Human):
    """A person. `lines` — what they say when the player presses E nearby."""

    def __init__(self, name='Someone', lines=None, waypoints=None, speed=2.2,
                 shirt=None, expression='neutral', **kwargs):
        super().__init__(shirt=shirt, **kwargs)
        self.set_expression(expression)
        self.npc_name = name
        self.lines = lines or ["Nice day, isn't it?"]
        self.waypoints = waypoints or []
        self.wp_index = 0
        self.move_speed = speed
        self.walking = bool(self.waypoints)
        # bobbing marker so players know NPCs are interactable
        self.marker = Entity(parent=self, model='diamond', color=Color(1, 1, .4, .9),
                             scale=.18, y=2.05)
        self.marker.setLightOff()

    def update(self):
        self.marker.y = 2.05 + math.sin(self.phase * .7) * .06

        if self.walking and self.waypoints:
            target = self.waypoints[self.wp_index]
            target = Vec3(target[0], self.y, target[2] if len(target) > 2 else target[1])
            direction = target - self.position
            direction.y = 0
            if direction.length() < .4:
                self.wp_index = (self.wp_index + 1) % len(self.waypoints)
            else:
                self.position += direction.normalized() * self.move_speed * time.dt
                self.look_at(Vec3(target.x, self.y, target.z))

        self.advance(moving=self.walking, speed=self.move_speed)

    def sprint_to(self, point, speed=7, then_vanish=False):
        """Run in a straight line (used to show NPCs doing things effortlessly)."""
        self.waypoints = []
        dist = distance_xz(self.position, Vec3(*point))
        dur = max(.1, dist / speed)
        self.look_at(Vec3(point[0], self.y, point[2]))
        self.move_speed = speed
        self.walking_anim_hack(dur)
        self.animate_position(Vec3(point[0], self.y, point[2]), duration=dur,
                              curve=curve.linear)
        if then_vanish:
            destroy(self, delay=dur + .5)

    def walking_anim_hack(self, duration):
        self.walking = True
        self.waypoints = []
        def stop():
            self.walking = False
        invoke(stop, delay=duration)

    def face(self, target_pos):
        self.look_at(Vec3(target_pos.x, self.y, target_pos.z))

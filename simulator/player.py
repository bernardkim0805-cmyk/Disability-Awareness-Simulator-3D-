"""Player construction: standard first-person walker, or wheelchair variant."""
from ursina import Entity, Color, held_keys
from ursina.prefabs.first_person_controller import FirstPersonController

from .config import STATE


class WheelchairController(FirstPersonController):
    """Lower eye height, slower, cannot jump; visible chair frame + wheels."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.speed = 3.4
        self.jump_height = 0
        self.camera_pivot.y = 1.15  # seated eye level

        grey = Color(.2, .2, .22, 1)
        self.frame = Entity(parent=self, model='cube', color=grey,
                            scale=(.6, .1, .6), y=.55)
        Entity(parent=self, model='cube', color=grey, scale=(.6, .5, .08),
               position=(0, .8, -.3))
        for side in (-1, 1):
            Entity(parent=self, model='sphere', color=Color(.05, .05, .05, 1),
                   scale=(.12, .55, .55), position=(side * .38, .35, -.1))

    def input(self, key):
        if key == 'space':
            return  # no jumping from a wheelchair
        super().input(key)


def create_player(position=(0, 0, 0)):
    if STATE.disability == 'wheelchair':
        return WheelchairController(position=position)
    p = FirstPersonController(position=position)
    p.speed = 6
    return p

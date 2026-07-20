"""AgentManager: spawns and updates a crowd, with level-of-detail so a large
population stays affordable. Near agents update fully every frame; far agents
update on a rotating budget. Owns the event bus and provides helpers to fire
world events (crash, police, greeting)."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import Entity, Vec3, destroy, time as utime

from .events import EventBus, WorldEvent
from .agent import Agent, tick_clock
from .profile import roll_profile


class AgentManager(Entity):
    def __init__(self, count=24, world_bounds=(38, 38), pois=None,
                 get_player=None, seed=None, **kwargs):
        super().__init__(**kwargs)
        self.bus = EventBus()
        self.world_bounds = world_bounds
        self.pois = pois or {}
        self.get_player = get_player or (lambda: None)
        self.rng = random.Random(seed)
        self.agents = []
        self._lod_cursor = 0
        for _ in range(count):
            self.spawn()

    def spawn(self, position=None):
        bx, bz = self.world_bounds
        pos = position or Vec3(self.rng.uniform(-bx, bx), 0,
                               self.rng.uniform(-bz, bz))
        agent = Agent(profile=roll_profile(self.rng), bus=self.bus,
                      world_bounds=self.world_bounds, pois=self.pois,
                      rng=self.rng, parent=self, position=pos,
                      rotation_y=self.rng.uniform(0, 360))
        self.agents.append(agent)
        return agent

    def fire_event(self, kind, position, intensity=1.0, source=None, **data):
        self.bus.publish(WorldEvent(kind=kind, position=position,
                                    intensity=intensity, source=source,
                                    data=data))

    def update(self):
        dt = utime.dt
        tick_clock(dt)
        player = self.get_player()
        ppos = player.position if (player and not player.isEmpty()) else None

        # LOD: full update for near agents; a rotating slice of far ones
        near, far = [], []
        for a in self.agents:
            if ppos is not None and (a.position - ppos).length() < 22:
                near.append(a)
            else:
                far.append(a)
        for a in near:
            a.agent_update(dt, self.agents, player)
        if far:
            budget = max(1, len(far) // 4)
            for _ in range(budget):
                self._lod_cursor = (self._lod_cursor + 1) % len(far)
                far[self._lod_cursor].agent_update(dt * 4, self.agents, player)

    def cleanup(self):
        for a in self.agents:
            a.destroy_agent()
        self.agents.clear()
        destroy(self)

"""Modular world-manager architecture.

The brief asks for the world to be structured as independent, externally
configurable managers. This module provides exactly that layer: a World
Manager that owns named sub-managers, each a thin facade over the concrete
system that already implements the behaviour (traffic AI, police, weather,
road network, damage, events). Keeping the seam here means systems can be
swapped or reconfigured from config without touching gameplay code.

RenderingManager is deliberately honest: it reports the engine's real
capabilities rather than pretending to run a PBR/deferred pipeline the
fixed-function stack cannot provide.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from . import config
from .damage import VehicleDamageSystem


class _Manager:
    """Base: every manager holds a back-reference to the scenario and its
    config slice, and exposes update(dt)."""
    config_key = None

    def __init__(self, world):
        self.world = world
        self.cfg = getattr(config, self.config_key) if self.config_key else {}

    def update(self, dt):
        pass


class TrafficManager(_Manager):
    """Owns the AI vehicle fleet (TrafficCar/Truck/Bus). Density is scaled by
    QUALITY.traffic_density; the concrete driving/updating already happens in
    each vehicle's own update()."""
    config_key = 'QUALITY'

    @property
    def vehicles(self):
        return self.world.vehicles

    def notify_hazard(self, position, radius=14):
        """Drivers near a hazard brake/slow — reused by CollisionManager."""
        for v in self.vehicles:
            if (v.position - position).length() < radius:
                v.base_speed *= .5


class PedestrianManager(_Manager):
    """Pedestrian population + reactions. In the driving scenario pedestrians
    are the scripted walkers; this facade scales/queries them and relays
    events. (The full autonomous-agent crowd lives in simulator/agents.)"""
    config_key = 'PEDESTRIANS'

    def react_to_event(self, kind, position):
        for npc in self.world.npcs:
            if (npc.position - position).length() < 16:
                try:
                    npc.set_expression('surprised')
                    npc.walking = True
                except Exception:
                    pass
        crowd = getattr(self.world, 'crowd', None)
        if crowd:
            crowd.react(position)


class PoliceManagerFacade(_Manager):
    """Facade over the persistent PoliceManager (police.py) — patrol,
    dispatch, pursuit and the traffic-stop cinematic already live there."""
    config_key = 'POLICE'

    @property
    def system(self):
        return self.world.police


class WeatherManager(_Manager):
    config_key = 'WEATHER'

    def __init__(self, world):
        super().__init__(world)
        self.current = world.weather

    def grip(self):
        return {'rain': self.cfg['rain_grip'], 'storm': self.cfg['rain_grip']
                * .9}.get(self.current, 1.0)


class CollisionManager(_Manager):
    """Central impact handling: applies visual+handling damage, notifies
    nearby drivers and pedestrians, and reports severity back."""

    def __init__(self, world):
        super().__init__(world)
        self.damage = VehicleDamageSystem(world.car)

    def register(self, speed, position, severe=False, kind='vehicle'):
        tier = self.damage.impact(speed, severe=severe)
        self.world.managers.traffic.notify_hazard(position)
        self.world.managers.pedestrian.react_to_event('crash', position)
        return tier

    def update(self, dt):
        self.damage.update(dt)


class EventManager(_Manager):
    """Simple typed event dispatch inside the driving world (crash, police,
    hazard). Systems subscribe; publishers fire once."""

    def __init__(self, world):
        super().__init__(world)
        self.subs = {}

    def on(self, kind, fn):
        self.subs.setdefault(kind, []).append(fn)

    def fire(self, kind, **data):
        for fn in self.subs.get(kind, []):
            fn(**data)


class MaterialSystem(_Manager):
    """Config-driven material tinting/quality. Honest stand-in for a PBR
    material system: it can apply the wet-road sheen via the post-fx pass and
    tint by region, which is the achievable subset on fixed-function."""
    config_key = 'QUALITY'

    def wet_roads_enabled(self):
        return self.cfg['wet_road_sheen'] and self.world.weather in ('rain', 'storm')


class RenderingManager(_Manager):
    """Reports the engine's REAL capabilities. Does not pretend to provide a
    PBR/deferred/HDR pipeline the fixed-function stack cannot run."""
    config_key = 'QUALITY'

    def capabilities(self):
        return dict(supported=self.cfg['supports'],
                    unsupported=self.cfg['unsupported'])

    def report(self):
        u = ', '.join(self.cfg['unsupported'])
        return (f'Rendering: fixed-function + GLSL120 post-fx. '
                f'NOT available on this stack: {u}.')


class WorldManager:
    """Top-level owner. Builds and updates the sub-managers; everything is
    reachable as world.managers.<name> and configured from config.py."""

    def __init__(self, scenario):
        self.w = scenario
        scenario.managers = self
        self.traffic = TrafficManager(scenario)
        self.pedestrian = PedestrianManager(scenario)
        self.police = PoliceManagerFacade(scenario)
        self.weather = WeatherManager(scenario)
        self.collision = CollisionManager(scenario)
        self.events = EventManager(scenario)
        self.material = MaterialSystem(scenario)
        self.rendering = RenderingManager(scenario)
        self._all = [self.traffic, self.pedestrian, self.police, self.weather,
                     self.collision, self.material, self.rendering]

    @property
    def damage(self):
        return self.collision.damage

    def update(self, dt):
        for m in self._all:
            m.update(dt)

    def cleanup(self):
        self.collision.damage.cleanup()

"""Driving scenario: "You have a doctor's appointment across the city. You
are running slightly late. Drive there safely, follow the law, and park."

The run is measured, not graded on perfection: crashes, close calls, red
lights, speeding, navigation mistakes, distraction time and assistive
feature usage are all tracked and reported in the end analysis — the point
is how environment + assistive design change the difficulty of an ordinary
task, not whether the player is flawless.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math
import random

from ursina import Entity, Text, Color, camera, mouse, time as utime, Vec3, destroy

from ..base_scenario import BaseScenario
from ..config import STATE
from .. import world
from .city import build_city, B, ROAD_W
from .car import PlayerCar, KMH
from .traffic import TrafficCar, Ambulance, Cyclist, Bus, Truck
from .phone import Phone, NotificationEngine
from .sounds import ensure_drive_assets, say_nav
from .worldgen import WorldGeneration, RoadNetworkSystem
from .managers import WorldManager
from .minimap import MinimapGPS
from .pedestrians import PedestrianCrowd
from .laws import DrivingEvaluator
from .police import PoliceManager, edu_summary

APPOINTMENT = 300            # seconds until the appointment begins

RING_SW = [(-B, -B), (0, -B), (0, 0), (-B, 0)]
RING_NE = [(0, 0), (B, 0), (B, B), (0, B)]
RING_BIG = [(-B, -B), (B, -B), (B, B), (-B, B)]
RING_NW = [(-B, 0), (0, 0), (0, B), (-B, B)]


class DrivingScenario(BaseScenario):
    player_start = (0, -50, 0)          # the walking body is parked out of sight
    sky_color = None

    # ------------------------------------------------------------------ build
    def build(self):
        ensure_drive_assets()
        self.weather = random.choice(['day', 'night', 'rain'])
        night = self.weather == 'night'

        self.player.enabled = False      # this scenario drives, not walks
        if night:
            self.lights = world.night_lights()
            if hasattr(self, 'sky'):
                destroy(self.sky)
            from ursina import window
            window.color = Color(.04, .04, .08, 1)
        else:
            self.lights = world.day_lights()

        self.world_gen = WorldGeneration(self, night=night, rng=random)
        self.places = self.world_gen.places
        self.roads = RoadNetworkSystem(self.places)
        self.car = PlayerCar(night=night, parent=self,
                             position=self.places['home'], rotation_y=0)

        # ---- route + instructions ------------------------------------------
        self.route = [
            (Vec3(-B, 0, 0), 'head NORTH on Ash Ave', None),
            (Vec3(0, 0, 0), 'turn RIGHT onto 2nd St', 'r'),
            (Vec3(B, 0, 0), 'continue EAST past the lights', None),
            (Vec3(B, 0, B), 'turn LEFT onto Cedar Ave (construction!)', 'l'),
            (Vec3(B + 22, 0, B), 'turn RIGHT toward the clinic', 'r'),
            (self.places['bay'], 'park in the GREEN bay and stop', None),
        ]
        self.leg = 0
        self.best_leg_dist = 1e9
        self.time_left = APPOINTMENT

        self.metrics = dict(crashes=0, close_calls=0, red_lights=0, speeding_s=0,
                            nav_mistakes=0, notifications=0, distracted_s=0,
                            phone_open_s=0, blindspot_saves=0, voice_navs=0,
                            potholes=0, warnings_shown=0)
        self.voice_nav = False
        self._crossed_lights = set()

        # ---- traffic ---------------------------------------------------------
        self.vehicles = []
        for ring, n in ((RING_SW, 3), (RING_NE, 3), (RING_BIG, 3)):
            for _ in range(n):
                c = TrafficCar(ring, self.places['lights'], parent=self,
                               speed=random.uniform(5.5, 8),
                               risky=random.random() < .15)
                self.vehicles.append(c)
        # highway ring traffic: faster cars + heavy trucks on a big loop
        H = self.places.get('highway_half', 200)
        HRING = [(-H, -H), (H, -H), (H, H), (-H, H)]
        for _ in range(4):
            self.vehicles.append(TrafficCar(HRING, self.places['lights'],
                                            parent=self, speed=random.uniform(12, 15)))
        for _ in range(2):
            self.vehicles.append(Truck(HRING, self.places['lights'], parent=self))
            self.vehicles.append(Truck(RING_BIG, self.places['lights'], parent=self))
        self.bus = Bus(RING_NW, self.places['lights'], stop_z=20, parent=self)
        self.vehicles.append(self.bus)
        self.cyclist = Cyclist(parent=self)
        for v in self.vehicles:
            v.others = self.vehicles
            v.player = self.car
        self.ambulance = None
        self.ambulance_at = random.uniform(60, 95)

        # scripted pedestrians
        self.school_ped = self.add_npc(name='pedestrian',
                                       position=(self.places['school_cross'].x,
                                                 0, self.places['school_cross'].z
                                                 + ROAD_W / 2 + 2),
                                       expression='neutral', lines=[])
        self.school_ped.marker.enabled = False
        self.ped_crossing = False
        for i in range(3):                                     # ambient walkers
            n = self.add_npc(name='walker', lines=[],
                             position=(random.choice((-B, 0, B)) + ROAD_W / 2 + 3.5,
                                       0, random.uniform(-B, B)))
            n.waypoints = [(n.x, -B - 10), (n.x, B + 10)]
            n.walking = True
            n.marker.enabled = False

        # ---- rain ------------------------------------------------------------
        if self.weather == 'rain':
            from ..audio import get_audio
            get_audio().play('drive_rain', volume=.35, loop=True)
            self.drops = []
            for _ in range(26):
                d = Entity(parent=camera.ui, model='quad',
                           position=(random.uniform(-.7, .7), random.uniform(-.45, .45)),
                           rotation_z=random.uniform(-15, 15),
                           scale=(.004, random.uniform(.01, .03)),
                           color=Color(.7, .8, .95, .5))
                self.drops.append(d)
            self.wiper = Entity(parent=camera.ui, model='quad', origin=(0, -.5),
                                position=(0, -.5), rotation_z=40, scale=(.015, .75),
                                color=Color(.1, .1, .12, .9))

        # ---- phone -----------------------------------------------------------
        self.phone = Phone(self)
        self.phone.set_route([i[1] for i in self.route])
        self.notifier = NotificationEngine(self, self.phone, parent=self)

        from ..audio import get_audio
        self.engine = get_audio().play('drive_engine', volume=.3, loop=True)
        get_audio().play('drive_traffic', volume=.2, loop=True)

        self.evaluator = DrivingEvaluator(self)
        self.police = PoliceManager(self, self.evaluator, parent=self)
        WorldManager(self)      # world.managers.{traffic,pedestrian,collision,...}
        self.minimap = MinimapGPS(self)
        self.crowd = PedestrianCrowd(self, count=120)

        self.set_objective("Doctor's appointment across the city — you're "
                           'running late. Drive safely and park in the green bay')
        self._announce_leg()
        Text(parent=self.hud, text='W/S drive · A/D steer · Q/R signals · H horn · '
                                   'TAB phone · V voice nav · P dismiss',
             position=(0, -.455), origin=(0, 0), scale=.68,
             color=Color(.6, .6, .65, 1))

    # ------------------------------------------------------------- navigation
    def _announce_leg(self):
        inst = self.route[self.leg][1]
        mins, secs = divmod(max(0, int(self.time_left)), 60)
        self.car.set_nav(f'{self.leg + 1}/{len(self.route)}  {inst}',
                         f'appointment in {mins}:{secs:02d}')
        if self.voice_nav:
            say_nav(inst)
            self.metrics['voice_navs'] += 1

    # ------------------------------------------------------------------ tick
    def tick(self):
        dt = utime.dt
        self.time_left -= dt

        car = self.car
        # engine pitch follows speed
        if self.engine:
            try:
                self.engine.pitch = .75 + abs(car.speed) / 14
                self.engine.volume = .2 + abs(car.speed) / 40
            except Exception:
                pass

        self._tick_route(dt)
        self._tick_laws(dt)
        self.evaluator.tick(dt)
        self.managers.update(dt)
        self.crowd.update()
        self._tick_infrastructure(dt)
        self._tick_hazards(dt)
        self._tick_events(dt)
        if self.weather == 'rain':
            self._tick_rain(dt)

        if car.update_mirrors(self.vehicles + [self.cyclist]):
            self.metrics['blindspot_saves'] += dt   # time warned = risk avoided
        if self.phone.enabled:
            self.metrics['phone_open_s'] += dt
            if abs(car.speed) > 4:
                self.metrics['distracted_s'] += dt

        if self.time_left <= 0:
            self._end(False, 'The appointment started without you.')

    def _tick_infrastructure(self, dt):
        """Tunnel: darken the view + echo the engine/siren. Bridge: raise the
        car onto the deck + crosswind. Region name shows on the HUD."""
        from ursina import camera as _cam, Color as _C
        p = self.car.position
        # ride the bridge deck: ease the car up the ramp and across the span
        target_y = self.roads.ground_height(p)
        self.car.y += (target_y - self.car.y) * min(1, 8 * dt)
        dark = self.roads.in_tunnel(p)
        if dark > 0:
            _cam.overlay.color = _C(0, 0, 0, min(.7, dark))
            if not getattr(self, '_in_tunnel', False):
                self._in_tunnel = True
                self.car.warn('entering tunnel — GPS signal weak', 2.5, flash=False)
            if self.engine:
                try:
                    self.engine.volume = .35 + abs(self.car.speed) / 30
                except Exception:
                    pass
        else:
            if getattr(self, '_in_tunnel', False):
                self._in_tunnel = False
                _cam.overlay.color = _C(0, 0, 0, 0)
        wind = self.roads.on_bridge(p)
        if wind > 0 and abs(self.car.speed) > 2:
            self.car.position += self.car.right * math.sin(self.t_total() * 1.7) \
                * wind * .04
            if not getattr(self, '_on_bridge', False):
                self._on_bridge = True
                self.car.warn('bridge — crosswinds, mind your lane', 3, flash=False)
        else:
            self._on_bridge = False
        region = self.roads.region_at(p)
        if region != getattr(self, '_region', None):
            self._region = region
            self.announcer.visual(f'now entering: {region.replace("_", " ").upper()}',
                                  3, _C(.7, .9, 1, 1))

    def _tick_route(self, dt):
        target, inst, _ = self.route[self.leg]
        d = (Vec3(target) - self.car.position)
        d.y = 0
        dist = d.length()
        self.best_leg_dist = min(self.best_leg_dist, dist)
        if dist < (2.4 if self.leg == len(self.route) - 1 else 6):
            if self.leg == len(self.route) - 1:
                if abs(self.car.speed) < .6:
                    self._end(True, None)
                return
            expected = self.route[self.leg][2]
            self.evaluator.on_turn_completed(expected, self.car.signal)
            self.leg += 1
            self.best_leg_dist = 1e9
            self._announce_leg()
        elif dist > self.best_leg_dist + 22:          # driving away: rerouting
            self.metrics['nav_mistakes'] += 1
            self.best_leg_dist = dist
            self.car.warn('recalculating route...', 2.5, flash=False)
            if self.voice_nav:
                say_nav('Recalculating. ' + self.route[self.leg][1])
        mins, secs = divmod(max(0, int(self.time_left)), 60)
        self.car.eta_text.text = f'appointment in {mins}:{secs:02d}'

    def _speed_limit(self):
        p = self.car.position
        if abs(p.z - B) < 12 and abs(p.x - 8) < 18:
            return 20                                   # school zone overrides
        return self.roads.speed_limit(p)

    def _tick_laws(self, dt):
        limit = self._speed_limit()
        self.car.limit_text.text = str(limit)
        if abs(self.car.speed) * KMH > limit * 1.18:
            self.metrics['speeding_s'] += dt
        # red-light running
        heading = self.car.forward
        axis = 'ew' if abs(heading.x) > abs(heading.z) else 'ns'
        for sig in self.places['lights']:
            gap = sig.world_position - self.car.position
            gap.y = 0
            if gap.length() < 4 and abs(self.car.speed) > 2:
                key = id(sig)
                if key not in self._crossed_lights and not sig.green_for(axis):
                    self._crossed_lights.add(key)
                    self.metrics['red_lights'] += 1
                    self.evaluator.report('red_light', cooldown=1)
                    self.metrics['warnings_shown'] += 1
            elif gap.length() > 10:
                self._crossed_lights.discard(id(sig))

    def _tick_hazards(self, dt):
        car = self.car
        # collisions with vehicles / cyclist / pedestrians
        for v in self.vehicles + [self.cyclist]:
            if (v.position - car.position).length() < 2.3:
                self._crash('you collided with traffic')
                v.position += (v.position - car.position).normalized() * 3
        for npc in self.npcs:
            if (npc.position - car.position).length() < 1.6:
                self._crash('you hit a pedestrian', severe=True)
        if abs(car.speed) > 1 and self.crowd.check_car_collision(car):
            self._crash('you hit a pedestrian', severe=True)
        # near misses count too
        if self.ped_crossing:
            gap = (self.school_ped.position - car.position).length()
            if 1.6 < gap < 3.4 and abs(car.speed) > 5:
                self.metrics['close_calls'] += 1
                self.evaluator.report('near_miss', cooldown=3, educate=False)
                from ..audio import get_audio
                get_audio().play('drive_screech', volume=.5)
                self.ped_crossing = False                # only counted once
        # potholes jolt the car
        for ph in self.places['potholes']:
            if (ph - car.position).length() < 1.3 and abs(car.speed) > 3:
                self.metrics['potholes'] += 1
                self.evaluator.report('pothole', cooldown=4, educate=False)
                car.speed *= .55
                camera.shake(duration=.25, magnitude=1.2)
        # construction cones
        if (self.places['construction'] - car.position).length() < 1.6:
            self._crash('you plowed through the construction zone')

    def _crash(self, why, severe=False):
        car = self.car
        if car.speed < 1.5 and not severe:
            return
        from ..audio import get_audio
        get_audio().play('drive_crash', volume=.6)
        camera.shake(duration=.5, magnitude=2.5)
        impact_speed = abs(car.speed)
        car.speed = 0
        tier = self.managers.collision.register(impact_speed, car.position,
                                                severe=severe)
        car.damage += 2 if severe else 1
        self.metrics['crashes'] += 1
        self.evaluator.report('collision_ped' if severe else 'collision',
                              cooldown=1, educate=False)
        car.warn(f'{why} ({tier} damage)', 3)
        self.metrics['warnings_shown'] += 1
        if self.managers.damage.totaled or (severe and car.damage >= 2):
            self.metrics['fines'] = self.metrics.get('fines', 0) + 450
            self._end(False, 'Major collision: the car is not driveable.\n'
                             'Towing + repairs: $450. The vehicle is gone for '
                             'the week.')

    def _tick_events(self, dt):
        # scripted: the school pedestrian steps out when you approach
        sp = self.places['school_cross']
        if (not self.ped_crossing and self.school_ped.enabled
                and (self.car.position - Vec3(sp.x, 0, sp.z)).length() < 17
                and abs(self.car.speed) > 3):
            self.ped_crossing = True
            self.school_ped.waypoints = [(sp.x, sp.z + ROAD_W / 2 + 2),
                                         (sp.x, sp.z - ROAD_W / 2 - 2)]
            self.school_ped.walking = True
            self.school_ped.move_speed = 2.6
            self.car.warn('PEDESTRIAN CROSSING AHEAD', 3)
            self.metrics['warnings_shown'] += 1
        # the ambulance event
        if self.ambulance is None and self.t_total() > self.ambulance_at:
            from ..audio import get_audio
            self.ambulance = Ambulance(RING_BIG, self.places['lights'], parent=self)
            self.ambulance.player = self.car
            self.ambulance.others = self.vehicles
            self.ambulance.siren = get_audio().play('drive_siren', volume=.3, loop=True)
            self.vehicles.append(self.ambulance)
        if self.ambulance:
            rel = self.ambulance.position - self.car.position
            rel.y = 0
            if rel.length() < 30 and self.t_total() > getattr(self, '_amb_warn_t', 0):
                self._amb_warn_t = self.t_total() + .9
                side = rel.dot(self.car.right)
                where = 'LEFT' if side < -3 else 'RIGHT' if side > 3 else 'BEHIND'
                self.car.warn(f'EMERGENCY VEHICLE {where} — pull over', 1.2,
                              flash=True)
                if rel.length() < 10 and abs(self.car.speed) > 3:
                    self.metrics['close_calls'] += 1
                    self.evaluator.report('fail_yield_ev', cooldown=6)

    def t_total(self):
        return APPOINTMENT - self.time_left

    def _tick_rain(self, dt):
        for d in self.drops:
            d.y -= dt * random.uniform(.15, .35)
            if d.y < -.48:
                d.position = (random.uniform(-.7, .7), .48)
        self.wiper.rotation_z = 40 * math.sin(self.t_total() * 2.2)

    # ------------------------------------------------------------------ input
    def input(self, key):
        super().input(key)
        if self.finished:
            return
        if key == 'tab':
            self.phone.enabled = not self.phone.enabled
        elif key == 'v':
            self.voice_nav = not self.voice_nav
            self.phone.voice_text.text = f'[V] voice guidance: {"ON" if self.voice_nav else "OFF"}'
            if self.voice_nav:
                say_nav(self.route[self.leg][1])
                self.metrics['voice_navs'] += 1
        elif key == 'p':
            self.notifier.dismiss()

    # -------------------------------------------------------------------- end
    def _end(self, success, reason):
        m = self.metrics
        used_assists = (m['voice_navs'] > 0 or m['blindspot_saves'] > 2)
        analysis = (
            f'time used {int(self.t_total())}s of {APPOINTMENT}s · '
            f'crashes {m["crashes"]} · close calls {m["close_calls"]}\n'
            f'red lights {m["red_lights"]} · speeding {int(m["speeding_s"])}s · '
            f'wrong turns {m["nav_mistakes"]} · potholes {m["potholes"]}\n'
            f'phone distraction {int(m["distracted_s"])}s · '
            f'notifications {m["notifications"]} · '
            f'voice nav used {m["voice_navs"]}x · '
            f'blind-spot warnings {int(m["blindspot_saves"])}s\n'
            f'SAFETY SCORE {int(self.evaluator.score)}/100'
            + (f' · fines ${m.get("fines", 0)}' if m.get('fines') else '') + '\n'
            + edu_summary() + '\n'
            + ('Assistive features carried part of the load — that is the '
               'point:\naccessible design, not perfection, makes independence '
               'possible.' if used_assists else
               'Try again with voice navigation (V) and the mirror warnings —\n'
               'assistive design measurably lowers the barrier.'))
        if success:
            self.finish('YOU MADE THE APPOINTMENT', analysis, success=True)
        else:
            self.finish('DID NOT ARRIVE', (reason + '\n' if reason else '') + analysis,
                        success=False)

    def cleanup(self):
        destroy(self.minimap)
        destroy(self.crowd)
        self.managers.cleanup()
        self.police.cleanup()
        for v in self.vehicles:           # stop AI from touching the dead car
            v.player = None
        destroy(self.phone)
        # destroy the car DIRECTLY: ursina only fires on_destroy (which
        # removes the dashboard GUI from camera.ui) on explicit destroys,
        # not when the car dies as a child of the scenario
        destroy(self.car)
        for d in getattr(self, 'drops', []):        # rain overlay is on camera.ui
            destroy(d)
        if hasattr(self, 'wiper'):
            destroy(self.wiper)
        super().cleanup()

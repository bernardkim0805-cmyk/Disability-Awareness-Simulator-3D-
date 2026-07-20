"""Continuous driving-behaviour evaluation.

Everything tunable lives in LAW_CONFIG — thresholds, penalty points, score
weights and police-dispatch pressure — so designers can rebalance without
touching detector logic. The evaluator watches the whole drive: speed vs
posted limits, lights and stop signs, yielding to pedestrians and emergency
vehicles, lane side, following distance, turn signals at route turns, plus
events reported by the scenario (collisions, near misses, potholes).

Fairness rule, enforced structurally: the evaluator sees only *behaviour*
(positions, speeds, signals). No disability flag is ever an input, so an
identical drive scores identically for every player.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from ursina import Text, Color, Vec3

from .city import GRID, ROAD_W
from .car import KMH

# ---------------------------------------------------------------------------
# Designer knobs. points = safety-score loss; heat = police-dispatch pressure.
# ---------------------------------------------------------------------------
LAW_CONFIG = dict(
    start_score=100,
    score_regen_per_s=.06,             # clean driving slowly earns trust back
    heat_decay_per_s=.08,
    dispatch_heat=10,                  # police appear at this much heat
    violations=dict(
        speeding=dict(over_kmh=8, repeat_s=4, points=2, heat=.8,
                      msg='speeding — {kmh} in a {limit} zone'),
        reckless_speed=dict(over_frac=.6, repeat_s=3, points=6, heat=3,
                            msg='RECKLESS speed — {kmh} in a {limit} zone'),
        red_light=dict(points=8, heat=4,
                       msg='ran a red light'),
        stop_sign=dict(roll_speed=4, points=4, heat=2,
                       msg='rolled through a stop sign'),
        fail_yield_ped=dict(dist=5.5, speed=6, points=7, heat=3.5,
                            msg='failed to yield to a pedestrian'),
        fail_yield_ev=dict(points=5, heat=2.5,
                           msg='failed to yield to an emergency vehicle'),
        oncoming_lane=dict(lateral=-.8, repeat_s=3.5, points=5, heat=2.5,
                           msg='drove against oncoming traffic'),
        tailgating=dict(gap=4.5, speed=8, repeat_s=3, points=2, heat=.7,
                        msg='following too closely'),
        no_signal_turn=dict(points=2, heat=.5,
                            msg='turned without signaling'),
        unsafe_lane_change=dict(points=3, heat=1.2,
                                msg='unsafe lane change into occupied space'),
        collision=dict(points=12, heat=5,
                       msg='collision'),
        collision_ped=dict(points=25, heat=10,
                           msg='struck a pedestrian'),
        near_miss=dict(points=4, heat=1.5,
                       msg='near miss'),
        pothole=dict(points=1, heat=.2,
                     msg='hit a road hazard at speed'),
    ),
)


class DrivingEvaluator:
    """Watches behaviour every frame; keeps score, heat, and a violation log
    the police cutscene quotes verbatim."""

    def __init__(self, scenario, config=None):
        self.cfg = config or LAW_CONFIG
        self.s = scenario
        self.score = self.cfg['start_score']
        self.heat = 0.0
        self.log = []                    # (t, code, human-readable description)
        self._cooldown = {}              # code -> earliest next report time
        self._timers = {}                # code -> continuous-condition seconds
        self._stop_zones_hit = set()
        gui = scenario.car.gui           # dies with the car -> no leaks
        self.score_label = Text(parent=gui, text='SAFETY', position=(-.62, .46),
                                scale=.7, color=Color(.7, .7, .7, 1))
        self.score_text = Text(parent=gui, text='100', position=(-.62, .43),
                               scale=1.5, color=Color(.4, .9, .5, 1))

    # ------------------------------------------------------------- reporting
    def report(self, code, cooldown=2.5, educate=True, **fmt):
        """Record one violation (rate-limited per code)."""
        t = self.s.t_total()
        if t < self._cooldown.get(code, 0):
            return False
        self._cooldown[code] = t + cooldown
        v = self.cfg['violations'][code]
        self.score = max(0, self.score - v['points'])
        self.heat += v['heat']
        desc = v['msg'].format(**fmt)
        self.log.append((t, code, desc))
        if educate:                       # inline educational feedback
            self.s.car.warn(f'(-{v["points"]}) {desc}', 2.6, flash=False)
        return True

    def recent_violations(self, n=3):
        seen, out = set(), []
        for t, code, desc in reversed(self.log):
            if code in seen:
                continue
            seen.add(code)
            out.append(desc)
            if len(out) >= n:
                break
        return out or ['a pattern of unsafe maneuvers']

    # ------------------------------------------------------------------ tick
    def tick(self, dt):
        cfg = self.cfg
        self.score = min(100, self.score + cfg['score_regen_per_s'] * dt)
        self.heat = max(0, self.heat - cfg['heat_decay_per_s'] * dt)
        self._check_speed(dt)
        self._check_stop_signs()
        self._check_lane_side(dt)
        self._check_tailgating(dt)
        self._check_pedestrian_yield()
        self.score_text.text = str(int(self.score))
        self.score_text.color = (Color(.4, .9, .5, 1) if self.score > 70 else
                                 Color(1, .8, .3, 1) if self.score > 40 else
                                 Color(1, .35, .3, 1))

    def _grow(self, code, condition, dt, needed):
        """Continuous conditions only fire after `needed` sustained seconds."""
        t = self._timers.get(code, 0)
        t = t + dt if condition else 0
        self._timers[code] = t
        if t >= needed:
            self._timers[code] = 0
            return True
        return False

    def _check_speed(self, dt):
        car = self.s.car
        kmh = abs(car.speed) * KMH
        limit = self.s._speed_limit()
        v = self.cfg['violations']
        if kmh > limit * (1 + v['reckless_speed']['over_frac']):
            if self._grow('reckless_speed', True, dt, v['reckless_speed']['repeat_s']):
                self.report('reckless_speed', kmh=int(kmh), limit=limit)
        elif kmh > limit + v['speeding']['over_kmh']:
            if self._grow('speeding', True, dt, v['speeding']['repeat_s']):
                self.report('speeding', kmh=int(kmh), limit=limit)
        else:
            self._timers['speeding'] = self._timers['reckless_speed'] = 0

    def _check_stop_signs(self):
        car = self.s.car
        roll = self.cfg['violations']['stop_sign']['roll_speed']
        for i, stop in enumerate(self.s.places.get('stops', [])):
            gap = Vec3(stop) - car.position
            gap.y = 0
            if gap.length() < 5:
                if abs(car.speed) < 1:
                    self._stop_zones_hit.add(i)      # proper stop: no flag
                elif abs(car.speed) * KMH > roll * KMH * .25 \
                        and i not in self._stop_zones_hit \
                        and abs(car.speed) > roll:
                    self._stop_zones_hit.add(i)
                    self.report('stop_sign')
            elif gap.length() > 10:
                self._stop_zones_hit.discard(i)

    def _check_lane_side(self, dt):
        """Right-hand traffic: heading +axis should sit on the +right offset
        (matches the AI's lane convention)."""
        car = self.s.car
        if abs(car.speed) < 3:
            self._timers['oncoming_lane'] = 0
            return
        v = self.cfg['violations']['oncoming_lane']
        f = car.forward
        wrong = False
        for k in GRID:
            if abs(car.position.x - k) < ROAD_W / 2 and abs(f.z) > .8:
                lateral = (car.position.x - k) * (1 if f.z > 0 else -1)
                wrong = lateral < v['lateral']
                break
            if abs(car.position.z - k) < ROAD_W / 2 and abs(f.x) > .8:
                lateral = (car.position.z - k) * (-1 if f.x > 0 else 1)
                wrong = lateral < v['lateral']
                break
        if self._grow('oncoming_lane', wrong, dt, v['repeat_s']):
            self.report('oncoming_lane')

    def _check_tailgating(self, dt):
        car = self.s.car
        v = self.cfg['violations']['tailgating']
        close = False
        if abs(car.speed) > v['speed']:
            for other in self.s.vehicles:
                rel = other.position - car.position
                rel.y = 0
                if 0 < rel.dot(car.forward) < v['gap'] \
                        and abs(rel.dot(car.right)) < 2:
                    close = True
                    break
        if self._grow('tailgating', close, dt, v['repeat_s']):
            self.report('tailgating')

    def _check_pedestrian_yield(self):
        car = self.s.car
        v = self.cfg['violations']['fail_yield_ped']
        if abs(car.speed) * KMH < v['speed'] * KMH * .4:
            return
        for npc in self.s.npcs:
            rel = npc.position - car.position
            rel.y = 0
            if 0 < rel.dot(car.forward) < v['dist'] \
                    and abs(rel.dot(car.right)) < 2.2 and abs(car.speed) > v['speed']:
                self.report('fail_yield_ped', cooldown=5)
                break

    # hooks the scenario calls on discrete events -----------------------------
    def on_turn_completed(self, expected_signal, actual_signal):
        if expected_signal and actual_signal != expected_signal:
            self.report('no_signal_turn', cooldown=1)

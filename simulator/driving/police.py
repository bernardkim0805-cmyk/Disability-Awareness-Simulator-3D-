"""Law enforcement: dispatch, pursuit, the pull-over cinematic, and the
progressive consequence ladder (warning -> citation -> suspension / tow).

Dispatch is driven purely by the evaluator's accumulated *behaviour* heat.
The officer's dialogue is generated from the recorded violation log and
always states the fairness principle out loud: the stop is about observed
driving that would stop ANY driver — never about a disability.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import Entity, Color, Vec3, time as utime, destroy, invoke

from ..config import STATE
from ..npc import NPC
from .traffic import _car_body

POLICE_CONFIG = dict(
    patrol_speed=12.5,
    pursuit_speed=15.5,
    pullover_hold_s=2.5,          # stand still this long to complete the stop
    evade_grace_s=14,             # keep driving this long -> pursuit
    pursuit_fail_s=28,            # keep evading -> license gone
    citation_fine=180,
    citation_score_floor=70,      # below this at the stop = citation
    suspension_score_floor=40,    # below this = suspension
)

# accommodation education, keyed by what the player is simulating -------------
TIPS = {
    'glaucoma': 'blind-spot monitoring + wide-angle mirrors compensate for '
                'peripheral loss',
    'macular': 'voice navigation and HUD speedometers move critical reading '
               'out of dead central vision',
    'cataracts': 'anti-glare windshields and well-designed road lighting cut '
                 'nighttime glare',
    'rp': 'daytime scheduling and high-contrast road markings extend safe '
          'driving years',
    'deaf': 'visual/haptic siren alerts (now in production cars) replace '
            'sound cues fully',
    'hearing_loss': 'visual/haptic siren alerts replace sound cues fully',
    'tinnitus': 'cabin noise management keeps alerts distinguishable',
    'parkinsonian': 'adaptive hand controls and steering dampers restore '
                    'precision',
    'essential_tremor': 'steering dampers and larger controls absorb tremor',
    'vestibular': 'lane-keep assist and horizon-stable displays reduce '
                  'disorientation',
    'adhd': "phone 'driving mode' + simplified single-instruction navigation "
            'remove the competition for attention',
    'adhd_fx': "phone 'driving mode' removes the competition for attention",
    'memory': 'repeating turn prompts and always-visible route lists remove '
              'the recall burden',
    'visual': 'voice-first navigation and audible signals carry the route',
}


def edu_summary():
    """What contributed, and what technology/design would have helped."""
    active = ([STATE.disability] if STATE.disability else []) + list(STATE.active_fx)
    tips = [TIPS[a] for a in active if a in TIPS]
    if not tips:
        return ('Environment shapes safety for every driver: clearer signals,\n'
                'protected crossings and assist systems lower everyone\'s risk.')
    return ('What would have helped here:\n- ' + '\n- '.join(tips[:3]))


class PoliceCar(Entity):
    """Pursues the player directly; lights always, siren via the manager so
    deaf mode gets the HUD/vibration channel instead."""

    def __init__(self, target, **kwargs):
        super().__init__(**kwargs)
        self.target = target
        self.speed = POLICE_CONFIG['patrol_speed']
        self.brakes = _car_body(self, Color(.12, .12, .14, 1), emergency=True)
        Entity(parent=self, model='cube', position=(0, .95, 0),
               scale=(1.92, .3, 2), color=Color(.95, .95, .95, 1))
        self.t = random.uniform(0, 2)
        self.hold = False

    def update(self):
        self.t += utime.dt
        on = int(self.t * 7) % 2 == 0
        for i, bcn in enumerate(getattr(self, 'beacons', [])):
            base = Color(1, .1, .1, 1) if i == 0 else Color(.15, .35, 1, 1)
            bcn.color = base if on == (i == 0) else Color(.25, .25, .28, 1)
        if self.hold or self.target is None or self.target.isEmpty():
            return
        rel = self.target.position - self.position
        rel.y = 0
        dist = rel.length()
        if dist > 7:                          # close in, then hold off the bumper
            d = rel.normalized()
            self.look_at(self.position + d)
            self.position += d * self.speed * utime.dt


class PoliceManager(Entity):
    """Owns dispatch, the stop, escalation, and consequences."""

    def __init__(self, scenario, evaluator, **kwargs):
        super().__init__(**kwargs)
        self.s = scenario
        self.ev = evaluator
        self.cfg = POLICE_CONFIG
        self.unit = None
        self.backup = None
        self.siren = None
        self.state = 'idle'      # idle | closing | ordering | cutscene | done-cooldown
        self.order_t = 0
        self.still_t = 0
        self.pursuit = False
        self.stops = 0

    # ------------------------------------------------------------------ tick
    def update(self):
        dt = utime.dt
        if self.state == 'idle':
            if self.ev.heat >= self.ev.cfg['dispatch_heat'] and not self.s.finished:
                self._dispatch()
            return
        if self.state in ('closing', 'ordering'):
            self._tick_pursuit(dt)

    def _dispatch(self):
        from ..audio import get_audio
        self.state = 'closing'
        car = self.s.car
        spawn = car.position - car.forward * 45
        spawn.y = 0
        self.unit = PoliceCar(car, parent=self.s, position=spawn)
        self.siren = get_audio().play('drive_siren', volume=.35, loop=True)
        self.s.car.warn('POLICE — LIGHTS BEHIND YOU', 4)
        self.s.metrics['warnings_shown'] += 1

    def _tick_pursuit(self, dt):
        car = self.s.car
        unit = self.unit
        if unit is None:
            return
        dist = (unit.position - car.position).length()
        if self.siren:
            try:
                self.siren.volume = max(.1, min(.7, 16 / max(6, dist)))
            except Exception:
                pass
        if dist > 16:
            return                          # still catching up
        if self.state == 'closing':
            self.state = 'ordering'
            self.order_t = 0
        self.order_t += dt
        if int(self.order_t * 1.2) % 2 == 0:
            self.s.car.warn('PULL OVER: stop the car and stay stopped', 1,
                            flash=True)
        # compliant?
        if abs(car.speed) < .6:
            self.still_t += dt
            if self.still_t >= self.cfg['pullover_hold_s']:
                self._begin_stop()
            return
        self.still_t = 0
        # evading?
        if not self.pursuit and self.order_t > self.cfg['evade_grace_s']:
            self.pursuit = True
            unit.speed = self.cfg['pursuit_speed']
            self.ev.report('reckless_speed', cooldown=0, educate=False,
                           kmh='evading', limit='police')
            spawn = car.position + car.right * 30
            self.backup = PoliceCar(car, parent=self.s, position=spawn)
            self.backup.speed = self.cfg['pursuit_speed']
            self.s.car.warn('PURSUIT — additional units dispatched', 3)
        if self.pursuit and self.order_t > self.cfg['pursuit_fail_s']:
            self._suspend(evaded=True)

    # ------------------------------------------------------------- the stop
    def _begin_stop(self):
        self.state = 'cutscene'
        car = self.s.car
        car.controls_locked = True
        for u in (self.unit, self.backup):
            if u:
                u.hold = True
        if self.siren:
            try:
                self.siren.stop()
            except Exception:
                pass
            self.siren = None
        # officer walks from the cruiser to the driver's window
        start = self.unit.position + Vec3(1.5, 0, 0)
        self.officer = NPC(parent=self.s, name='Officer Reyes',
                           position=start, expression='focused',
                           shirt=Color(.15, .2, .35, 1), lines=[])
        self.officer.marker.enabled = False
        window_pos = car.position - car.forward * 1 - car.right * 1.6
        self.officer.sprint_to((window_pos.x, 0, window_pos.z), speed=2.2)
        invoke(self._officer_speaks, delay=2.4)

    def _officer_speaks(self):
        self.officer.face(self.s.car.position)
        self.stops += 1
        severity = self._severity()
        quotes = self.ev.recent_violations(3)
        lines = ['Evening. Do you know why I stopped you?',
                 'I observed: ' + '; '.join(quotes) + '.']
        if severity == 'warning':
            lines += ["Nothing on your record, so this is a warning.",
                      'Any driver doing that gets this same stop — '
                      'watch the road, not the mistakes. Drive safe.']
        elif severity == 'citation':
            lines += [f'That pattern earns a citation — '
                      f'${self.cfg["citation_fine"]} fine.',
                      'To be clear: this is about the driving I watched, '
                      'and only that. Anyone driving that way gets this '
                      'ticket. Slow it down.']
        else:
            lines += ['That is a repeated, dangerous pattern. I\'m suspending '
                      'your driving privileges pending re-assessment.',
                      'This decision is based on observed driving that did '
                      'not meet safe standards — the same standard every '
                      'driver on this road is held to.']
        from ..dialogue import DialogueBox
        self.s.dialogue.say('Officer Reyes', lines,
                            on_done=lambda: self._resolve(severity),
                            speaker_entity=self.officer)

    def _severity(self):
        if self.pursuit or self.ev.score < self.cfg['suspension_score_floor'] \
                or self.stops >= 3:
            return 'suspension'
        if self.ev.score < self.cfg['citation_score_floor'] or self.stops >= 2:
            return 'citation'
        return 'warning'

    def _resolve(self, severity):
        s = self.s
        if severity == 'suspension':
            s.finish('LICENSE SUSPENDED',
                     'Driving privileges suspended pending assessment — the '
                     'observed driving\ndid not meet safe standards. '
                     f'(Safety score: {int(self.ev.score)}/100)\n' + edu_summary(),
                     success=False)
            return
        if severity == 'citation':
            s.metrics['fines'] = s.metrics.get('fines', 0) + self.cfg['citation_fine']
            self.ev.score = max(0, self.ev.score - 10)
            s.announcer.visual(f'citation issued: ${self.cfg["citation_fine"]} '
                               '— it goes on the record', 5, Color(1, .7, .4, 1))
        else:
            s.announcer.visual('let off with a warning — heed it', 4,
                               Color(.7, .9, .7, 1))
        # resume the mission
        s.car.controls_locked = False
        self.ev.heat = 2
        self.state = 'idle'
        self.pursuit = False
        self.order_t = self.still_t = 0
        officer = self.officer
        officer.sprint_to((self.unit.x + 1.5, 0, self.unit.z), speed=2.4,
                          then_vanish=True)
        for u in (self.unit, self.backup):
            if u:
                destroy(u, delay=3)
        self.unit = self.backup = None

    def _suspend(self, evaded=False):
        self.s.finish('LICENSE SUSPENDED',
                      ('You fled a traffic stop. ' if evaded else '')
                      + 'Driving privileges suspended pending assessment.\n'
                      + edu_summary(), success=False)

    def cleanup(self):
        if self.siren:
            try:
                self.siren.stop()
            except Exception:
                pass

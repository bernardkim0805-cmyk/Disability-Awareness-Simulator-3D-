"""Getting Ready for Bed scenario.

The player moves through a lived-in home completing a randomized checklist of
bedtime tasks. Interactions are proximity + E (or product keys in the shower).
Disabilities reshape every task; skipping consequences (running faucet,
unflushed toilet, wrong product) lowers the completion score and teaches why
accessible design matters. Ends with a reflection summary.
"""
if __package__ in (None, ''):
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math
import random

from ursina import (Entity, Text, Color, camera, mouse, distance_xz, Vec3,
                    time as utime, destroy, invoke)

from panda3d.core import Vec4 as _PVec4

from ..base_scenario import BaseScenario
from ..config import STATE
from .house import build_house
from .tasks import build_routine
from .reader import ReadingPanel
from .sounds import ensure_bed_assets

INTERACT_R = 2.4


class BedtimeScenario(BaseScenario):
    player_start = (-11, 0, -1)          # standing by the bed
    sky_color = Color(.03, .03, .06, 1)  # night; interior lit

    # ------------------------------------------------------------------ build
    def build(self):
        ensure_bed_assets()
        self.rng = random.Random()
        self.A = build_house(self, night=True)
        self.routine = build_routine(self.rng)
        self.task_i = 0
        self.done_tasks = set()
        self.mistakes = []               # (what, lesson)
        self.score = 100
        self.reader = None
        self.shower = None
        self.dropped = []
        self.faucet_warned = False
        self.t = 0
        self.notif = None
        self.notif_cd = self.rng.uniform(10, 18)
        self.memory_fade = 0

        # checklist HUD (top-left)
        self.checklist = Text(parent=self.hud, text='', position=(-.86, .34),
                              scale=.72, color=Color(.85, .9, .8, 1))
        self._refresh_checklist()
        self.set_objective(f'Bedtime routine — {len(self.routine)} tasks. '
                           'Follow the checklist (order matters!)')
        self.controls_text.text = ('WASD move · mouse look · E interact · '
                                   'J re-read checklist · Esc menu')

    # ------------------------------------------------------------- checklist
    def _cur(self):
        return self.routine[self.task_i] if self.task_i < len(self.routine) else None

    def _refresh_checklist(self):
        from ..dialogue import dyslexify
        lines = ['TONIGHT:']
        for i, (tid, label, *_ ) in enumerate(self.routine):
            mark = 'x' if tid in self.done_tasks else ('>' if i == self.task_i else ' ')
            text = label
            if STATE.disability == 'dyslexia' and mark != 'x':
                text = dyslexify(text)
            lines.append(f'[{mark}] {text}')
        self.checklist.text = '\n'.join(lines)
        # memory impairment: the list fades and must be re-read (J)
        if STATE.disability == 'memory' or 'memory' in STATE.active_fx:
            self.memory_fade = 0

    # ------------------------------------------------------------------ tick
    def tick(self):
        dt = utime.dt
        self.t += dt
        self._tick_consequences(dt)
        self._tick_adhd(dt)
        self._tick_memory(dt)
        if not self.dialogue.enabled and self.reader is None and self.shower is None:
            self.interact_hint.text = self._prompt() or ''

    def _prompt(self):
        cur = self._cur()
        if not cur:
            return ''
        anchor = self._anchor(cur[2])
        if anchor and distance_xz(self.player.position, anchor) < INTERACT_R:
            return f'[E] {cur[1]}'
        # allow flushing / drying / picking up dropped things opportunistically
        if not self.A['toilet_flushed'] and self.A['toilet_used'] \
                and distance_xz(self.player.position, self.A['toilet_pos']) < INTERACT_R:
            return '[E] flush the toilet'
        if self.A['faucet_on'] and distance_xz(self.player.position,
                                               self.A['sink_pos']) < INTERACT_R:
            return '[E] turn off the faucet'
        for d in self.dropped:
            if distance_xz(self.player.position, d.position) < INTERACT_R:
                return '[E] pick up the dropped bottle'
        return ''

    def _anchor(self, key):
        v = self.A.get(key)
        return v if isinstance(v, Vec3) else None

    # ---------------------------------------------------------------- consequences
    def _tick_consequences(self, dt):
        a = self.A
        if a['faucet_on']:
            a['faucet_stream'].enabled = True
            if not self.faucet_warned and self.t > 4:
                self.faucet_warned = True
                self.announcer.sound('the faucet is still running...', 3,
                                     cue='bed_faucet')
        else:
            a['faucet_stream'].enabled = False
        # shower steam builds while water runs; mirror fogs, then clears
        if a['shower_stream'].enabled:
            a['steam'] = min(1, a['steam'] + dt * .12)
        else:
            a['steam'] = max(0, a['steam'] - dt * .05)
        fog = a['steam']
        a['mirror_fog'].color = Color(.85, .9, .92, fog * .85)
        if fog > .2:
            camera.overlay.color = Color(.8, .82, .85, fog * .25)
        elif STATE.disability != 'visual':
            camera.overlay.color = Color(0, 0, 0, 0)

    def _tick_adhd(self, dt):
        if STATE.disability != 'adhd' and 'adhd_fx' not in STATE.active_fx:
            return
        if self.notif is None:
            self.notif_cd -= dt
            if self.notif_cd <= 0:
                from ..audio import get_audio
                get_audio().play('bed_chime', volume=.9)
                msg = self.rng.choice([
                    'phone buzz: "you up?"', 'app: your screen time report is ready',
                    'notification: 3 new likes', 'reminder you already forgot what for'])
                self.notif = Text(parent=self.hud, text='* ' + msg
                                  + '  [P to dismiss] *', origin=(0, 0), y=.16,
                                  scale=1, color=Color(1, .8, .3, 1))

    def _tick_memory(self, dt):
        if STATE.disability != 'memory' and 'memory' not in STATE.active_fx:
            return
        self.memory_fade += dt
        fade = max(0, min(.92, (self.memory_fade - 6) / 5))
        self.checklist.color = Color(.85, .9, .8, 1 - fade)

    # ------------------------------------------------------------------ input
    def input(self, key):
        if self.finished:
            return
        if key == 'escape':
            self.exit_to_menu()
            return
        if self.reader is not None or self.shower is not None:
            return
        if key == 'j':                    # re-read the checklist (memory aid)
            self.memory_fade = 0
            self.checklist.color = Color(.85, .9, .8, 1)
            return
        if key == 'p' and self.notif:
            destroy(self.notif); self.notif = None
            self.notif_cd = self.rng.uniform(14, 24)
            return
        if key != 'e':
            return
        # opportunistic fixes first
        if self._try_fixups():
            return
        cur = self._cur()
        if not cur:
            return
        anchor = self._anchor(cur[2])
        if not anchor or distance_xz(self.player.position, anchor) >= INTERACT_R:
            return
        self._do_task(cur)

    def _try_fixups(self):
        a = self.A
        p = self.player.position
        if not a['toilet_flushed'] and a['toilet_used'] \
                and distance_xz(p, a['toilet_pos']) < INTERACT_R:
            a['toilet_flushed'] = True
            from ..audio import get_audio
            get_audio().play('bed_flush', volume=.5)
            self.announcer.visual('flushed.', 1.5, Color(.7, .9, .7, 1))
            return True
        if a['faucet_on'] and distance_xz(p, a['sink_pos']) < INTERACT_R:
            a['faucet_on'] = False
            self.announcer.visual('faucet off — good catch.', 2, Color(.7, .9, .7, 1))
            return True
        for d in self.dropped[:]:
            if distance_xz(p, d.position) < INTERACT_R:
                self.dropped.remove(d); destroy(d)
                self.announcer.visual('picked it up.', 1.5)
                return True
        return False

    # ------------------------------------------------------------- task logic
    def _do_task(self, cur):
        tid, label, anchor_key, kind = cur
        a = self.A
        from ..audio import get_audio

        # tremor: a chance to fumble/drop when handling small items
        if kind in ('brush', 'floss', 'product', 'reading') and self._tremor() \
                and self.rng.random() < .5:
            self._drop_bottle()
            self.announcer.visual('your hand shakes — you drop it. Pick it up (E).',
                                  3, Color(1, .6, .5, 1))
            return

        if kind == 'toilet':
            a['toilet_lid'].y = 1.05
            a['toilet_used'] = True
            a['toilet_flushed'] = False
            self.announcer.visual('...done. Remember to FLUSH and wash hands.', 3)
            self._complete(tid, need_flush=True)
        elif kind == 'wash_hands':
            a['faucet_on'] = True
            get_audio().play('bed_faucet', volume=.4)
            invoke(self._auto_faucet_off, delay=2.5)
            self._complete(tid)
        elif kind == 'brush':
            get_audio().play('bed_brush', volume=.4)
            self._complete(tid)
        elif kind == 'floss':
            self._complete(tid)
        elif kind == 'product':
            self._use_product(tid, label)
        elif kind == 'action':
            get_audio().play('bed_click', volume=.4)
            if tid == 'alarm':
                self.announcer.visual('alarm set for 7:00.', 2)
            if tid == 'hair':
                self.announcer.visual('hair brushed.', 1.5)
            self._complete(tid)
        elif kind == 'water':
            a['faucet_on'] = True
            get_audio().play('bed_pour', volume=.4)
            invoke(self._auto_faucet_off, delay=2)
            self.announcer.visual('glass filled — set it by the bed.', 2)
            self._complete(tid)
        elif kind == 'pajamas':
            a['pajamas_on'] = True
            self.announcer.visual('changed into pajamas.', 2)
            self._complete(tid)
        elif kind == 'laundry':
            self.announcer.visual('dirty clothes in the hamper.', 2)
            self._complete(tid)
        elif kind == 'toggle':            # lock door
            a['door_locked'] = True
            get_audio().play('bed_click', volume=.4)
            self.announcer.visual('door locked.', 1.5)
            self._complete(tid)
        elif kind == 'curtains':
            a['curtains_open'] = False
            a['curtain_l'].scale_x = 1.6; a['curtain_r'].scale_x = 1.6
            self._complete(tid)
        elif kind == 'bath_light':
            a['bath_ceiling'].color = Color(.15, .15, .18, 1)
            a['bath_light_on'] = False
            self._complete(tid)
        elif kind == 'bed_light':
            a['bedroom_ceiling'].color = Color(.12, .12, .15, 1)
            a['bedroom_light_on'] = False
            self.lights.ambient_np.node().setColor(_PVec4(.14, .13, .17, 1))
            self._complete(tid)
        elif kind == 'reading':
            self._open_reader(tid)
        elif kind == 'shower':
            self._open_shower(tid)
        elif kind == 'sleep':
            self._finish_night()

    def _tremor(self):
        return {'essential_tremor', 'parkinsonian'} & STATE.active_fx

    def _drop_bottle(self):
        from ..audio import get_audio
        get_audio().play('bed_drop', volume=.5)
        p = self.player.position + self.player.forward * 1
        b = Entity(parent=self, model='cube', position=(p.x, .2, p.z),
                   rotation=(0, self.rng.uniform(0, 90), 70),
                   scale=(.28, .55, .28), color=Color(.7, .5, .5, 1))
        b.animate_position((p.x + self.rng.uniform(-1, 1), .15,
                            p.z + self.rng.uniform(-1, 1)), duration=.5)
        self.dropped.append(b)

    def _use_product(self, tid, label):
        """Visual impairment: bottles look alike, so you might grab the wrong
        one — an educational moment about accessible labeling."""
        wrong = (STATE.disability == 'visual' or {'macular', 'cataracts'}
                 & STATE.active_fx) and self.rng.random() < .45
        if wrong:
            self.score -= 8
            self.mistakes.append((f'used the wrong bottle for "{label}"',
                'high-contrast, large-print, or braille/bump-dot labels let '
                'people tell products apart by touch and sight.'))
            self.announcer.visual('wrong bottle! they all look the same. '
                                  '(that would sting on skin)', 4, Color(1, .6, .5, 1))
        self._complete(tid)

    def _auto_faucet_off(self):
        # the faucet auto-closes UNLESS a deaf player can't hear it AND leaves it;
        # here we model the risk: sometimes it stays on to be caught later
        if self.A['faucet_on'] and self.rng.random() < (.6 if STATE.disability
                                                        == 'deaf' else .15):
            return                        # left running — a consequence to catch
        self.A['faucet_on'] = False

    # ----------------------------------------------------------- reading task
    def _open_reader(self, tid):
        self.player.enabled = False
        mouse.locked = False
        kind = 'reading_book' if tid in ('read',) else 'med'
        def done(ok):
            self.reader = None
            self.player.enabled = True
            mouse.locked = True
            if tid == 'meds':
                self.A['meds_taken'] = True
                if not ok:
                    self.score -= 6
                    self.mistakes.append(('misread the medication label',
                        'clear, large, well-contrasted labels prevent dosing '
                        'errors — critical accessible-design.'))
            self._complete(tid)
        self.reader = ReadingPanel(kind, on_done=done)

    # ------------------------------------------------------------- shower task
    def _open_shower(self, tid):
        self.player.enabled = False
        mouse.locked = False
        def done():
            self.shower = None
            self.player.enabled = True
            mouse.locked = True
            self._complete(tid)
        self.shower = ShowerSequence(self, on_done=done)

    # ----------------------------------------------------------- completion
    def _complete(self, tid, need_flush=False):
        from ..audio import get_audio
        self.done_tasks.add(tid)
        get_audio().play('bed_chime', volume=.3)
        # advance to the next not-yet-done task
        while self.task_i < len(self.routine) and \
                self.routine[self.task_i][0] in self.done_tasks:
            self.task_i += 1
        self._refresh_checklist()
        if self.task_i < len(self.routine):
            self.set_objective(f'Next: {self.routine[self.task_i][1]}')

    def _finish_night(self):
        a = self.A
        # tally end-of-night consequences
        if not a['toilet_flushed'] and a['toilet_used']:
            self.score -= 10
            self.mistakes.append(('went to bed without flushing', 'routine slips '
                'happen — visual/checklist reminders help everyone stay on track.'))
        if a['faucet_on']:
            self.score -= 8
            self.mistakes.append(('left the faucet running all night',
                'a faucet you cannot HEAR needs a visual indicator — vital for '
                'deaf and hard-of-hearing people.'))
        if a['shower_stream'].enabled:
            self.score -= 8
            self.mistakes.append(('left the shower running', 'same lesson — '
                'accessible alerts should not rely on sound alone.'))
        if a['bath_light_on']:
            self.score -= 3
        skipped = [lbl for tid, lbl, *_ in self.routine
                   if tid not in self.done_tasks and tid != 'sleep']
        self.score -= 5 * len(skipped)

        summary = (f'You completed {len(self.done_tasks)} of '
                   f'{len(self.routine) - 1} tasks.  Score: {max(0, self.score)}/100\n')
        if self.mistakes:
            summary += '\nWhat tripped you up (and what would help):\n'
            for what, lesson in self.mistakes[:4]:
                summary += f'- {what}\n    -> {lesson}\n'
        else:
            summary += '\nA clean, complete routine. Notice how much easier this '
            summary += 'was without an added barrier — that ease is the point.'
        self.finish('GOODNIGHT', summary, success=self.score >= 55)

    def cleanup(self):
        camera.overlay.color = Color(0, 0, 0, 0)
        for x in (self.reader, self.shower):
            if x:
                destroy(x)
        for d in self.dropped:
            destroy(d)
        super().cleanup()


class ShowerSequence(Entity):
    """A full interactive shower: adjust temperature, then wash steps in order.
    Visual impairment hides the temperature readout (controls are just shapes);
    hearing loss removes the water sound so you rely on the visual stream."""

    STEPS = ['shampoo hair', 'rinse', 'apply conditioner', 'wash body',
             'rinse thoroughly', 'turn off water', 'dry with towel', 'hang towel']

    def __init__(self, scenario, on_done, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.s = scenario
        self.on_done = on_done
        self.temp = 20.0                  # target ~ 38
        self.step = -1                    # -1 = adjusting temperature
        self.low_vis = (STATE.disability == 'visual'
                        or bool({'macular', 'cataracts'} & STATE.active_fx))
        from ..audio import get_audio
        self.audio = get_audio()
        scenario.A['shower_stream'].enabled = True
        self.audio.play('bed_shower', volume=.4, loop=True)

        Entity(parent=self, model='quad', color=Color(0, 0, 0, .55),
               scale=(2, 2), z=1)
        Text(parent=self, text='SHOWER', origin=(0, 0), y=.4, scale=1.4,
             color=Color(.8, .9, 1, 1))
        self.info = Text(parent=self, text='', origin=(0, 0), y=.25, scale=1,
                         color=Color(.95, .95, .95, 1))
        self.hint = Text(parent=self, text='', origin=(0, 0), y=-.32, scale=.85,
                         color=Color(.8, .85, .9, 1))
        self.temp_bar = Entity(parent=self, model='quad', origin=(-.5, 0),
                               position=(-.2, .12), scale=(.4, .04),
                               color=Color(.4, .6, .9, 1))
        self._render()

    def _render(self):
        if self.step == -1:
            if self.low_vis:
                self.info.text = 'Adjust the water: [ hotter ] ] colder [\n' \
                                 '(you cannot read the dial clearly...)'
            else:
                self.info.text = f'Water: {int(self.temp)}C   ' \
                    f'({"too cold" if self.temp < 34 else "too hot" if self.temp > 42 else "just right"})\n' \
                    '] = hotter   [ = colder   ENTER when comfortable'
            self.temp_bar.scale_x = .4 * min(1, self.temp / 50)
            self.temp_bar.color = (Color(.9, .4, .3, 1) if self.temp > 42 else
                                   Color(.4, .6, .9, 1) if self.temp < 34 else
                                   Color(.3, .85, .5, 1))
            self.hint.text = 'get the temperature comfortable, then step in (ENTER)'
        else:
            self.info.text = f'Step {self.step + 1}/{len(self.STEPS)}:  ' \
                             f'{self.STEPS[self.step].upper()}'
            self.hint.text = 'press SPACE to do it'

    def input(self, key):
        if self.step == -1:
            if key == ']':
                self.temp = min(50, self.temp + 3); self._render()
            elif key == '[':
                self.temp = max(10, self.temp - 3); self._render()
            elif key == 'enter':
                if self.temp > 44:
                    self.s.score -= 5
                    self.s.mistakes.append(('shower ran too hot to feel safely',
                        'tactile/large temperature markings help when you cannot '
                        'read a small dial.'))
                self.step = 0
                self._render()
        else:
            if key == 'space':
                if self.STEPS[self.step] == 'turn off water':
                    self.s.A['shower_stream'].enabled = False
                    self.audio.stop_all()
                    self.s.audio_restart = True
                self.step += 1
                if self.step >= len(self.STEPS):
                    self._finish()
                else:
                    self._render()

    def _finish(self):
        self.s.A['shower_stream'].enabled = False
        cb = self.on_done
        destroy(self)
        cb()

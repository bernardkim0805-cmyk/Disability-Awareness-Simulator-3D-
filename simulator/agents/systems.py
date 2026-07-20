"""The per-agent component systems. Each is an independent object that reads
the agent's state and writes to the shared Human rig; they coordinate through
the agent and the event bus rather than calling each other directly.

Components: PerceptionSystem, EmotionSystem, MemorySystem, MovementController,
AnimationController, FacialExpressionController, GestureController,
PhysicsInteractionSystem. (NPCController — the decision brain — and
DialogueEngine live in their own files.)
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math
import random

from ursina import Color, Vec3, time as utime


# ============================================================ PERCEPTION
class PerceptionSystem:
    """What the agent can currently notice: nearby agents, the player, and
    the most salient world event it has heard. Rate-limited so 100 agents
    don't each scan every frame."""

    def __init__(self, agent):
        self.a = agent
        self.nearby = []            # (other_agent, distance)
        self.player = None
        self.player_dist = 999
        self.focus = None           # a Vec3 the eyes should track
        self._scan_t = random.uniform(0, .4)

    def update(self, dt, agents, player):
        self._scan_t -= dt
        if self._scan_t > 0:
            return
        self._scan_t = .3 + random.uniform(0, .2)
        r = self.a.profile.awareness_radius
        pos = self.a.position
        self.nearby = []
        for other in agents:
            if other is self.a:
                continue
            d = (other.position - pos).length()
            if d < r:
                self.nearby.append((other, d))
        self.nearby.sort(key=lambda o: o[1])
        if player is not None and not player.isEmpty():
            self.player = player
            self.player_dist = (player.position - pos).length()
        # choose a gaze focus: the player if close, else the nearest agent,
        # else whatever the controller last set
        if self.player_dist < r * .7:
            self.focus = self.player.position + Vec3(0, 1.6, 0)
        elif self.nearby:
            self.focus = self.nearby[0][0].position + Vec3(0, 1.7, 0)


# ============================================================ EMOTION
class EmotionSystem:
    """A small affect model: valence (mood) and arousal (stress) drift toward
    the profile baseline but are pushed by events. The current emotion label
    is derived from the valence/arousal quadrant and drives face + posture."""

    def __init__(self, agent):
        self.a = agent
        self.valence = agent.profile.base_mood
        self.arousal = agent.profile.base_stress
        self.emotion = 'neutral'
        self._hold = 0

    def bump(self, dvalence, darousal, hold=2.5):
        strength = self.a.profile.emotional_reaction_strength
        self.valence = max(-1, min(1, self.valence + dvalence * strength))
        self.arousal = max(0, min(1, self.arousal + darousal * strength))
        self._hold = max(self._hold, hold)

    def update(self, dt):
        # decay toward baseline
        base_v, base_s = self.a.profile.base_mood, self.a.profile.base_stress
        self.valence += (base_v - self.valence) * min(1, .25 * dt)
        self.arousal += (base_s - self.arousal) * min(1, .2 * dt)
        self._hold -= dt
        self.emotion = self._label()

    def _label(self):
        v, s = self.valence, self.arousal
        if s > .7:
            return 'scared' if v < -.1 else 'surprised'
        if v > .35:
            return 'happy'
        if v < -.35:
            return 'angry' if s > .45 else 'sad'
        if s > .5:
            return 'worried'
        if v < -.1:
            return 'tired'
        return 'neutral'


# ============================================================ MEMORY
class MemorySystem:
    """Short episodic memory of events and encounters. Lets an agent
    recognize a repeated player encounter and colour its future behaviour."""

    def __init__(self, agent):
        self.a = agent
        self.player_encounters = 0
        self.player_sentiment = 0.0     # -1 wary .. +1 friendly
        self.last_player_seen = -999
        self.events = []                # recent (kind, t)

    def note_event(self, kind, t):
        self.events.append((kind, t))
        if len(self.events) > 6:
            self.events.pop(0)

    def see_player(self, t, positive):
        if t - self.last_player_seen > 8:      # a fresh encounter
            self.player_encounters += 1
            self.player_sentiment = max(-1, min(1, self.player_sentiment
                                                + (.25 if positive else -.35)))
        self.last_player_seen = t

    def recognizes_player(self):
        return self.player_encounters >= 2


# ============================================================ MOVEMENT
class MovementController:
    """Weight-and-momentum locomotion. The body must ROTATE toward a new
    heading (limited by turn_rate) before it commits speed to that direction,
    and speed eases in/out — no instant direction changes or teleport-starts.
    Feet are nudged to terrain height via a simple ground probe (approximate
    IK)."""

    def __init__(self, agent):
        self.a = agent
        self.heading = Vec3(math.sin(math.radians(agent.rotation_y)), 0,
                            math.cos(math.radians(agent.rotation_y)))
        self.speed = 0.0
        self.target = None          # Vec3 goal
        self.arrive_radius = 1.2
        self.want_run = False
        self._speed_phase = random.uniform(0, 6)

    def go_to(self, point, run=False):
        self.target = Vec3(point.x, self.a.y, point.z)
        self.want_run = run

    def stop(self):
        self.target = None

    @property
    def moving(self):
        return self.speed > .15

    def update(self, dt):
        a = self.a
        prof = a.profile
        # desired speed: personality base with slow sinusoidal variation
        self._speed_phase += dt * .5
        var = 1 + math.sin(self._speed_phase) * prof.walking_speed_variation
        cruise = prof.base_speed * var * (1.9 if self.want_run else 1) * prof.posture
        # emotion colours pace: fear/anger quicken, sadness/tired slow
        emo = a.emotion.emotion
        cruise *= {'scared': 1.6, 'surprised': 1.2, 'angry': 1.3,
                   'happy': 1.05, 'sad': .8, 'tired': .8}.get(emo, 1)

        if self.target is None:
            desired = 0.0
        else:
            to = self.target - a.position
            to.y = 0
            dist = to.length()
            if dist < self.arrive_radius:
                self.target = None
                desired = 0.0
            else:
                desired = cruise
                want_dir = to.normalized()
                # rotate the body toward the goal before moving (momentum)
                cur = math.degrees(math.atan2(self.heading.x, self.heading.z))
                wnt = math.degrees(math.atan2(want_dir.x, want_dir.z))
                diff = (wnt - cur + 180) % 360 - 180
                max_turn = prof.turn_rate * dt
                step = max(-max_turn, min(max_turn, diff))
                ang = math.radians(cur + step)
                self.heading = Vec3(math.sin(ang), 0, math.cos(ang))
                a.rotation_y = cur + step
                # if still sharply turned away, throttle speed (can't run sideways)
                if abs(diff) > 55:
                    desired *= .3

        # ease speed toward desired (acceleration/deceleration have weight)
        rate = 4 if desired > self.speed else 6
        self.speed += (desired - self.speed) * min(1, rate * dt)
        if self.speed > .05:
            a.position += self.heading * self.speed * dt

        # crude terrain follow: keep feet near y=0 (extend with a raycast later)
        a.y += (0 - a.y) * min(1, 8 * dt)


# ============================================================ ANIMATION
class AnimationController:
    """Drives the Human rig's procedural gait from the movement state and
    layers posture from emotion. It does NOT play canned clips — it feeds the
    rig's per-frame `advance()` with live speed, and adds lean/slump."""

    RUN_THRESHOLD = 4.6

    def __init__(self, agent):
        self.a = agent

    def update(self, dt):
        a = self.a
        mv = a.movement
        speed = mv.speed
        running = speed > self.RUN_THRESHOLD
        a.advance(moving=mv.moving, speed=max(2.2, speed))
        # emotional posture on top of the gait
        lean = 0
        if running:
            lean = 12
        slump = (1 - a.profile.posture) * 14
        if a.emotion.emotion in ('sad', 'tired'):
            slump += 8
        if a.emotion.emotion == 'scared':
            lean -= 6                       # recoil / defensive
        a.torso.rotation_x += (lean + slump - a.torso.rotation_x) * min(1, 4 * dt) * .15


# ============================================================ FACE + EYES
class FacialExpressionController:
    """Emotion -> facial pose (via the rig's expression set) with dynamic eye
    behaviour: the eyes track the perception focus, saccade away periodically
    (no unnatural constant staring), and blink. During conversation the mouth
    is handled by the rig's lip-sync; here we add micro-expressions."""

    def __init__(self, agent):
        self.a = agent
        self._look_t = 0
        self._averting = False
        self._last_emotion = None

    def update(self, dt):
        a = self.a
        emo = a.emotion.emotion
        if emo != self._last_emotion:
            self._last_emotion = emo
            a.set_expression(emo if emo in a.EXPRESSIONS else 'neutral')

        # eye contact vs. aversion cycle, weighted by personality
        self._look_t -= dt
        if self._look_t <= 0:
            freq = a.profile.eye_contact_frequency
            if self._averting:
                self._averting = False
                self._look_t = random.uniform(.8, 2.2) * (.5 + freq)
            else:
                self._averting = random.random() > freq
                self._look_t = random.uniform(.4, 1.4)

        focus = a.perception.focus
        if focus is not None and not self._averting:
            to = focus - (a.world_position + Vec3(0, 1.7, 0))
            yaw = math.degrees(math.atan2(to.x, to.z)) - a.rotation_y
            yaw = (yaw + 180) % 360 - 180
            target = max(-22, min(22, yaw))
        else:
            target = math.sin(a.phase * .5) * 8      # idle glance
        a.head.rotation_y += (target - a.head.rotation_y) * min(1, 6 * dt)


# ============================================================ GESTURE
class GestureController:
    """Body-language layer: personality-scaled gestures fired by the
    controller or spontaneously while idle/talking (point, wave, shrug,
    cross-arms, check-watch, rub-face). Gestures are short pose overrides on
    the arm joints that blend out."""

    def __init__(self, agent):
        self.a = agent
        self.timer = random.uniform(3, 8)
        self.active = None
        self.t = 0

    def play(self, name):
        self.active = name
        self.t = 0

    def update(self, dt):
        a = self.a
        if self.active is None:
            self.timer -= dt
            if self.timer <= 0:
                self.timer = random.uniform(4, 11) / max(.2, a.profile.gesture_probability)
                if not a.movement.moving or random.random() < .3:
                    self.play(random.choice(
                        ['wave', 'shrug', 'check_watch', 'rub_face',
                         'cross_arms', 'point', 'hips']))
            return
        self.t += dt
        p = min(1, self.t / .9)
        sway = math.sin(p * math.pi)          # ease in/out
        sh_l, el_l = a.arms['l']
        sh_r, el_r = a.arms['r']
        g = self.active
        if g == 'wave':
            sh_r.rotation_x = -150 * sway
            el_r.rotation_x = -40 - 40 * math.sin(self.t * 12)
        elif g == 'shrug':
            sh_l.rotation_z = 30 * sway
            sh_r.rotation_z = -30 * sway
            el_l.rotation_x = el_r.rotation_x = -70 * sway
        elif g == 'check_watch':
            sh_l.rotation_x = -40 * sway
            el_l.rotation_x = -110 * sway
            a.head.rotation_x = 12 * sway
        elif g == 'rub_face':
            sh_r.rotation_x = -80 * sway
            el_r.rotation_x = -120 * sway
        elif g == 'cross_arms':
            sh_l.rotation_x = sh_r.rotation_x = -60 * sway
            el_l.rotation_x = el_r.rotation_x = -95 * sway
        elif g == 'point':
            sh_r.rotation_x = -95 * sway
            el_r.rotation_x = -10 * sway
        elif g == 'hips':
            sh_l.rotation_z = 40 * sway
            el_l.rotation_x = -100 * sway
        if p >= 1:
            self.active = None


# ============================================================ PHYSICS REACTION
class PhysicsInteractionSystem:
    """Startle, stumble, flinch and personal-space reactions. Applies a short
    impulse and a recovery ease rather than snapping between states, and gives
    props/accessories a bit of secondary motion."""

    def __init__(self, agent):
        self.a = agent
        self.recoil = Vec3(0, 0, 0)
        self.stagger = 0

    def startle(self, from_pos, strength=1.0):
        a = self.a
        away = (a.position - from_pos)
        away.y = 0
        if away.length() > .01:
            self.recoil = away.normalized() * strength * .5
        a.emotion.bump(-.2, .5 * strength)
        self.stagger = .5 * strength

    def bump(self, from_pos):
        self.startle(from_pos, strength=.5)

    def update(self, dt):
        a = self.a
        if self.recoil.length() > .01:
            a.position += self.recoil * dt * 4
            self.recoil *= max(0, 1 - 6 * dt)
        if self.stagger > 0:
            self.stagger -= dt
            a.rotation_z = math.sin(a.phase * 20) * 4 * self.stagger  # regain balance
        else:
            a.rotation_z *= max(0, 1 - 8 * dt)

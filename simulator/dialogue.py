"""Dialogue box, ambient sound-as-text announcements, and dyslexia text scrambling."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import Entity, Text, Color, camera, destroy, time

from .config import STATE


def dyslexify(text):
    """Scramble the inner letters of longer words + occasional b/d p/q flips."""
    out_words = []
    for word in text.split(' '):
        core = ''.join(c for c in word if c.isalpha())
        if len(core) > 3 and random.random() < .85:
            mid = list(word[1:-1])
            random.shuffle(mid)
            word = word[0] + ''.join(mid) + word[-1]
        if random.random() < .25:
            word = word.replace('b', 'd') if random.random() < .5 else word.replace('p', 'q')
        out_words.append(word)
    return ' '.join(out_words)


class DialogueBox(Entity):
    """Bottom-of-screen dialogue with a typewriter effect.

    With dyslexia selected, the visible line keeps re-scrambling.
    """

    def __init__(self, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.panel = Entity(parent=self, model='quad', color=Color(0, 0, 0, .8),
                            scale=(1.1, .24), y=-.36, z=1)
        self.speaker_text = Text(parent=self, text='', y=-.27, x=-.5,
                                 scale=1.1, color=Color(1, .85, .3, 1))
        self.line_text = Text(parent=self, text='', y=-.33, x=-.5, scale=1,
                              color=Color(.95, .95, .95, 1))
        self.hint = Text(parent=self, text='[E] continue', y=-.44, x=.38, scale=.8,
                         color=Color(.6, .6, .6, 1))
        self.lines = []
        self.on_done = None
        self.full_line = ''
        self.shown_chars = 0
        self.rescramble_timer = 0
        self.enabled = False

    def say(self, speaker, lines, on_done=None, speaker_entity=None):
        self.lines = list(lines)
        self.speaker_name = speaker
        self.on_done = on_done
        self.speaker_entity = speaker_entity
        self.enabled = True
        self._next_line()

    def _next_line(self):
        if not self.lines:
            self.enabled = False
            if getattr(self, 'speaker_entity', None):
                self.speaker_entity.talking = False
            if self.on_done:
                self.on_done()
            return
        self.full_line = self.lines.pop(0)
        self.shown_chars = 0
        self.speaker_text.text = self.speaker_name
        from .audio import get_audio
        get_audio().speak(f'{self.speaker_name} says: {self.full_line}')

    def update(self):
        still_typing = self.shown_chars < len(self.full_line)
        if getattr(self, 'speaker_entity', None):
            self.speaker_entity.talking = still_typing  # lip sync
        if still_typing:
            self.shown_chars = min(len(self.full_line), self.shown_chars + 60 * time.dt)
        visible = self.full_line[:int(self.shown_chars)]
        if STATE.disability == 'dyslexia':
            self.rescramble_timer -= time.dt
            if self.rescramble_timer <= 0:
                self.rescramble_timer = .4
                self._scrambled = dyslexify(visible)
            visible = getattr(self, '_scrambled', visible)
        self.line_text.text = visible

    def input(self, key):
        if not self.enabled:
            return
        if key in ('e', 'enter', 'left mouse down'):
            if self.shown_chars < len(self.full_line):
                self.shown_chars = len(self.full_line)  # skip typewriter
            else:
                self._next_line()


class Announcer(Entity):
    """Shows 'sounds' as italic text at the top of the screen.

    Deaf mode: sound-based announcements are silently dropped — the player
    genuinely never gets the information. Visual events always show.
    """

    def __init__(self, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        if STATE.disability == 'deaf':
            Text(parent=self, text='[ you hear: nothing ]', position=(-.86, .47),
                 scale=.9, color=Color(.5, .8, .7, .8))

    def sound(self, text, duration=4, color=None, cue='chime'):
        """A sound cue. Never reaches a deaf player — text or audio."""
        if STATE.disability == 'deaf':
            return
        from .audio import get_audio
        audio = get_audio()
        if cue:
            audio.play(cue, volume=.45)
        audio.speak(text)
        self._show(f'~ {text} ~', duration, color or Color(.85, .85, 1, 1))

    def visual(self, text, duration=4, color=None):
        """A visible event. Reaches everyone; narrated for blind players."""
        from .audio import get_audio
        get_audio().speak(text)
        self._show(text, duration, color or Color(1, 1, .8, 1))

    def _show(self, text, duration, color):
        if STATE.disability == 'dyslexia':
            text = dyslexify(text)
        t = Text(parent=self, text=text, y=.42 - random.uniform(0, .04),
                 x=0, origin=(0, 0), scale=1.05, color=color)
        t.animate('y', t.y + .03, duration=duration)
        destroy(t, delay=duration)

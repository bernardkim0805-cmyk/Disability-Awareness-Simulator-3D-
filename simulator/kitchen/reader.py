"""The recipe card reader.

Design goal (per spec): difficulty is NOT blur. It reproduces the actual
mechanics of impaired reading:

- losing your place: the line marker drifts/jumps and must be re-anchored
- slower word recognition: words resolve one at a time, on a timer
- dyslexic features: mirrored letters (b/d, p/q), inner-letter scrambles
- similar-looking word substitutions (form/from, casserole/carousel...)
- increased cognitive effort: a comprehension check before it closes

Severity scales with the dyslexia experience / lab reading conditions;
a mild version applies to everyone so all players feel the difference.
"""
import random

from ursina import Entity, Text, Button, Color, camera, destroy, time as utime

from ..config import STATE

CONFUSABLE = {'from': 'form', 'form': 'from', 'salt': 'slat', 'pan': 'nap',
              'stir': 'stri', 'pot': 'top', 'heat': 'hate', 'bowl': 'blow',
              'plate': 'pleat', 'sauce': 'cause', 'onion': 'union',
              'butter': 'batter', 'flour': 'floor', 'medium': 'medium',
              'boil': 'blot', 'dice': 'bice'}

MIRROR = str.maketrans('bdpq', 'dbqp')


def _dyslexify_word(word, severity):
    """Apply letter-level dyslexic features to a single word."""
    r = random.random()
    if r < .30 * severity and word.lower() in CONFUSABLE:
        return CONFUSABLE[word.lower()]
    if r < .45 * severity and len(word) > 3:
        mid = list(word[1:-1])
        random.shuffle(mid)
        word = word[0] + ''.join(mid) + word[-1]
    if random.random() < .35 * severity:
        word = word.translate(MIRROR)
    return word


def reading_severity():
    """0 = typical reader, 1 = severe. Pulls from both selection systems."""
    s = 0.15                                           # everyone feels a little
    if STATE.disability == 'dyslexia':
        s = 1.0
    for eid in ('memory', 'adhd_fx'):
        if eid in STATE.active_fx:
            s = max(s, .55)
    return s


class RecipeReader(Entity):
    """Modal card. Controls:
       SPACE  reveal the next word (word-by-word recognition)
       R      re-find your place after the marker jumps
       1/2    answer the comprehension check
    """

    def __init__(self, recipe, on_done, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.recipe = recipe
        self.on_done = on_done
        self.severity = reading_severity()
        self.lines = recipe['card_lines']
        self.line_i = 0
        self.word_i = 0
        self.lost_place = False
        self.jump_timer = self._next_jump()
        self.render_timer = 0
        self.done_reading = False

        Entity(parent=self, model='quad', color=Color(0, 0, 0, .82), scale=(2, 2), z=1)
        Entity(parent=self, model='quad', color=Color(.93, .9, .8, .98),
               scale=(.9, .62), z=.5)
        Text(parent=self, text='— RECIPE CARD —', origin=(0, 0), y=.26, scale=1.1,
             color=Color(.4, .3, .2, 1))
        self.title = Text(parent=self, text=recipe['name'], origin=(0, 0), y=.2,
                          scale=1.3, color=Color(.2, .15, .1, 1))
        self.body = Text(parent=self, text='', position=(-.4, .14), scale=.95,
                         color=Color(.15, .12, .1, 1))
        self.marker = Entity(parent=self, model='quad', scale=(.02, .02),
                             color=Color(.85, .3, .2, .9), position=(-.42, .14))
        self.hint = Text(parent=self, text='SPACE: next word', origin=(0, 0),
                         y=-.24, scale=.8, color=Color(.35, .3, .25, 1))
        self.effort = Text(parent=self, text='', origin=(0, 0), y=-.28, scale=.7,
                           color=Color(.6, .3, .25, 1))
        self.quiz_ui = []

    def _next_jump(self):
        return random.uniform(2.5, 6) * (1.5 - self.severity * .9)

    # ------------------------------------------------------------------ render
    def _render(self):
        out = []
        for li, line in enumerate(self.lines):
            words = line.split(' ')
            shown = []
            for wi, w in enumerate(words):
                if li < self.line_i or (li == self.line_i and wi < self.word_i):
                    shown.append(_dyslexify_word(w, self.severity * .6))
                elif li == self.line_i and wi == self.word_i and not self.lost_place:
                    shown.append('[' + _dyslexify_word(w, self.severity) + ']')
                else:
                    # unread text is a gray mush of shapes, not information
                    shown.append('~' * max(2, len(w) - 1))
            out.append(' '.join(shown))
        self.body.text = '\n'.join(out)
        self.marker.y = .14 - self.line_i * .035
        self.marker.color = (Color(.85, .3, .2, .9) if not self.lost_place
                             else Color(.85, .3, .2, .25))

    def update(self):
        self.render_timer -= utime.dt
        if self.render_timer <= 0:
            self.render_timer = .5
            self._render()
        if self.done_reading:
            return
        self.jump_timer -= utime.dt
        if self.jump_timer <= 0 and self.severity > .2:
            # you lose your place: marker detaches, R re-anchors it
            self.jump_timer = self._next_jump()
            self.lost_place = True
            self.line_i = max(0, self.line_i + random.choice((-1, -1, 1)))
            self.hint.text = 'you lost your place — R: find it again'

    # ------------------------------------------------------------------- input
    def input(self, key):
        if self.done_reading:
            if key in ('1', '2'):
                self._answer(int(key))
            return
        if key == 'space':
            if self.lost_place:
                self.effort.text = 'where was I...?'
                return
            # slower word recognition: each word costs a beat of effort
            self.word_i += 1
            if self.word_i >= len(self.lines[self.line_i].split(' ')):
                self.word_i = 0
                self.line_i += 1
            if self.line_i >= len(self.lines):
                self._comprehension_check()
            self._render()
        elif key == 'r' and self.lost_place:
            self.lost_place = False
            self.line_i = min(self.line_i, len(self.lines) - 1)
            self.hint.text = 'SPACE: next word'
            self.effort.text = ''
            self._render()

    # -------------------------------------------------------- comprehension
    def _comprehension_check(self):
        self.done_reading = True
        q = self.recipe['check']
        self.body.text = ''
        self.marker.enabled = False
        self.hint.text = ''
        self.quiz_ui.append(Text(parent=self, text='Quick check — ' + q['q'],
                                 origin=(0, 0), y=.05, scale=1,
                                 color=Color(.2, .15, .1, 1)))
        for i, opt in enumerate(q['options']):
            self.quiz_ui.append(Text(parent=self, text=f'{i + 1})  {opt}',
                                     origin=(0, 0), y=-.03 - i * .06, scale=1,
                                     color=Color(.25, .2, .15, 1)))

    def _answer(self, n):
        correct = n - 1 == self.recipe['check']['answer']
        cb = self.on_done
        destroy(self)
        cb(correct)

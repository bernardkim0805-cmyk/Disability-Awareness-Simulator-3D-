"""Accessibility Simulator panel.

Category tabs -> effect rows (toggle + intensity slider) -> info pane with
description / medical / gameplay / misconception / assistive tech /
references. Presets scale every enabled effect; effects preview LIVE on the
menu plaza behind the panel; split-screen and hold-N comparison included.
"""
from ursina import Entity, Text, Button, Color, Slider, camera, destroy

from .config import STATE
from .fx.core import EffectStack
from .fx.registry import EFFECTS, PRESETS, DISCLAIMER

CATS = [('visual', 'VISION'), ('audio', 'HEARING'),
        ('movement', 'MOVEMENT'), ('cognitive', 'COGNITIVE')]

DIM = Color(.13, .15, .2, .95)
ON = Color(.2, .5, .3, 1)
ACCENT = Color(.8, .75, .5, 1)


class LabPanel(Entity):
    def __init__(self, on_close=None, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.on_close = on_close
        self.cat = 'visual'
        self.selected = 'glaucoma'
        self.rows = []
        self.preview_stack = None

        Entity(parent=self, model='quad', color=Color(0, 0, 0, .78),
               scale=(2, 2), z=1)
        Text(parent=self, text='ACCESSIBILITY  SIMULATOR', origin=(0, 0), y=.45,
             scale=1.6, color=Color(1, 1, 1, 1))
        Text(parent=self, text=DISCLAIMER, origin=(0, 0), y=-.47, scale=.68,
             color=Color(.75, .75, .8, 1))
        Text(parent=self, text='effects preview live behind this panel · in scenarios: hold N = normal vision',
             origin=(0, 0), y=.405, scale=.7, color=Color(.6, .65, .7, 1))

        # category tabs
        self.tab_buttons = {}
        for i, (cat, label) in enumerate(CATS):
            b = Button(parent=self, text=label, scale=(.16, .045),
                       position=(-.62 + i * .17, .35), color=DIM)
            b.text_entity.scale *= .8
            b.on_click = lambda c=cat: self.set_cat(c)
            self.tab_buttons[cat] = b

        # info pane (right)
        self.info_title = Text(parent=self, text='', position=(.18, .3),
                               scale=1.1, color=ACCENT)
        self.info_body = Text(parent=self, text='', position=(.18, .25),
                              scale=.72, color=Color(.92, .92, .95, 1))

        # presets & modes (bottom)
        Text(parent=self, text='presets:', position=(-.72, -.33), scale=.8,
             color=Color(.7, .7, .7, 1))
        for i, (pname, val) in enumerate(PRESETS.items()):
            b = Button(parent=self, text=pname, scale=(.11, .045),
                       position=(-.56 + i * .12, -.325), color=DIM)
            b.text_entity.scale *= .8
            b.on_click = lambda v=val: self.apply_preset(v)
        self.split_btn = Button(parent=self, text='split-screen: off',
                                scale=(.2, .045), position=(-.13, -.325), color=DIM)
        self.split_btn.text_entity.scale *= .8
        self.split_btn.on_click = self.toggle_split
        clear = Button(parent=self, text='clear all', scale=(.12, .045),
                       position=(.06, -.325), color=Color(.35, .2, .2, 1))
        clear.text_entity.scale *= .8
        clear.on_click = self.clear_all
        back = Button(parent=self, text='<  BACK', scale=(.14, .05),
                      position=(-.72, .45), color=Color(.25, .25, .35, 1))
        back.on_click = self.close

        self.set_cat('visual')
        self._rebuild_preview()

    # ------------------------------------------------------------ rows
    def set_cat(self, cat):
        self.cat = cat
        for c, b in self.tab_buttons.items():
            b.color = ACCENT if c == cat else DIM
            b.text_color = Color(.1, .1, .1, 1) if c == cat else Color(.9, .9, .9, 1)
        for row in self.rows:
            destroy(row)
        self.rows = []
        ids = [eid for eid, spec in EFFECTS.items() if spec['cat'] == cat]
        for i, eid in enumerate(ids):
            y = .28 - i * .057
            row = Entity(parent=self)
            spec = EFFECTS[eid]
            enabled = eid in STATE.lab_effects
            t = Button(parent=row, text='ON' if enabled else 'off',
                       scale=(.05, .042), position=(-.72, y),
                       color=ON if enabled else DIM)
            t.text_entity.scale *= .75
            t.on_click = lambda e=eid: self.toggle(e)
            n = Button(parent=row, text=spec['name'], scale=(.34, .042),
                       position=(-.5, y),
                       color=Color(.2, .22, .3, 1) if eid == self.selected else DIM)
            n.text_entity.scale *= .72
            n.on_click = lambda e=eid: self.select(e)
            s = Slider(parent=row, min=5, max=100, step=1, dynamic=True,
                       default=int(STATE.lab_effects.get(eid, .6) * 100),
                       position=(-.31, y + .008), scale=.5)
            s.on_value_changed = lambda e=eid, sl=s: self.set_intensity(e, sl.value)
            self.rows.append(row)
        self.select(ids[0] if self.selected not in ids else self.selected)

    def toggle(self, eid):
        if eid in STATE.lab_effects:
            del STATE.lab_effects[eid]
        else:
            STATE.lab_effects[eid] = .6
        self.select(eid)
        self.set_cat(self.cat)
        self._rebuild_preview()

    def set_intensity(self, eid, value):
        if eid in STATE.lab_effects:
            STATE.lab_effects[eid] = value / 100
            for eff in (self.preview_stack.effects if self.preview_stack else []):
                if eff.effect_id == eid:
                    eff.setIntensity(value / 100)

    def apply_preset(self, val):
        for eid in STATE.lab_effects:
            STATE.lab_effects[eid] = val
        self.set_cat(self.cat)
        self._rebuild_preview()

    def clear_all(self):
        STATE.lab_effects.clear()
        self.set_cat(self.cat)
        self._rebuild_preview()

    def toggle_split(self):
        STATE.lab_split = not STATE.lab_split
        self.split_btn.text = f'split-screen: {"ON" if STATE.lab_split else "off"}'

    # ------------------------------------------------------------ info
    def select(self, eid):
        self.selected = eid
        spec = EFFECTS[eid]
        self.info_title.text = spec['name']
        self.info_body.text = (
            f"{spec['desc']}\n\n"
            f"MEDICAL\n{spec['medical']}\n\n"
            f"IN THIS GAME\n{spec['gameplay']}\n\n"
            f"COMMON MISCONCEPTION\n{spec['misconception']}\n\n"
            f"ASSISTIVE TECHNOLOGY\n{spec['assistive']}\n\n"
            f"REFERENCES\n{spec['refs']}")
        for row in self.rows:
            for child in row.children:
                if isinstance(child, Button) and child.text == spec['name']:
                    child.color = Color(.2, .22, .3, 1)

    # ------------------------------------------------------------ preview
    def _rebuild_preview(self):
        if self.preview_stack:
            self.preview_stack.cleanup()
            self.preview_stack = None
        if STATE.lab_effects:
            self.preview_stack = EffectStack(context=None)

    def close(self):
        if self.preview_stack:
            self.preview_stack.cleanup()
            self.preview_stack = None
        cb = self.on_close
        destroy(self)
        if cb:
            cb()

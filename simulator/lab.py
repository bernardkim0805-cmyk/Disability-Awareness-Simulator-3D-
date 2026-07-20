"""Accessible, responsive control panel for experiences and stackable effects."""


from __future__ import annotations

if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from collections.abc import Callable

from ursina import Button, Color, Entity, Slider, Text, camera, destroy

from .config import STATE
from .effects import EffectsManager
from .fx.core import EffectStack
from .fx.registry import DISCLAIMER, EFFECTS, PRESETS
from .lab_state import (
    ORIGINAL_EXPERIENCES,
    active_summary,
    apply_preset,
    incompatibility_reason,
    reset_to_baseline,
    select_experience,
    toggle_effect,
    toggle_split as toggle_split_state,
)

CATEGORIES = [
    ("original", "ORIGINAL EXPERIENCES"),
    ("visual", "VISUAL EFFECTS"),
    ("audio", "HEARING EFFECTS"),
    ("movement", "MOVEMENT EFFECTS"),
    ("cognitive", "COGNITIVE EFFECTS"),
]

PANEL = Color(.055, .065, .09, .97)
SURFACE = Color(.11, .13, .18, .98)
SURFACE_HOVER = Color(.17, .20, .28, 1)
SELECTED = Color(.18, .48, .38, 1)
ACCENT = Color(.95, .72, .25, 1)
DISABLED = Color(.13, .13, .15, .72)
TEXT = Color(.94, .95, .98, 1)
MUTED = Color(.65, .69, .76, 1)
WARNING = Color(1, .66, .35, 1)


def _button(parent: Entity, text: str, position: tuple[float, float],
            scale: tuple[float, float], on_click: Callable[[], None],
            color: Color = SURFACE, text_scale: float = .72) -> Button:
    button = Button(parent=parent, text=text, position=position, scale=scale,
                    color=color, highlight_color=SURFACE_HOVER,
                    pressed_color=SELECTED, on_click=on_click)
    button.text_entity.scale *= text_scale
    return button


class LabPanel(Entity):
    """Lab UI with keyboard navigation and live, non-destructive previews."""

    def __init__(self, on_close: Callable[[], None] | None = None,
                 on_demo: Callable[[], None] | None = None, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.on_close = on_close
        self.on_demo = on_demo
        self.category = "original"
        self.selected_id = STATE.disability or "none"
        self.rows: list[Entity] = []
        self.row_ids: list[str] = []
        self.focus_index = 0
        self.preview_stack: EffectStack | None = None
        self.original_preview: EffectsManager | None = None
        self.preset_index = 1

        Entity(parent=self, model="quad", color=PANEL, scale=(2, 2), z=1)
        Entity(parent=self, model="quad", color=SURFACE, position=(-.47, .01),
               scale=(.86, .72), z=.5)
        Entity(parent=self, model="quad", color=SURFACE, position=(.46, .01),
               scale=(.84, .72), z=.5)

        Text(parent=self, text="ACCESSIBILITY LAB", position=(-.76, .455),
             scale=1.45, color=TEXT)
        Text(parent=self, text="Configure one full experience and optional stackable effects",
             position=(-.76, .412), scale=.72, color=MUTED)

        self.summary = Text(parent=self, text="", position=(-.76, .365),
                            scale=.67, color=Color(.72, .88, .82, 1))
        self.status = Text(parent=self, text="", position=(-.76, -.405),
                           scale=.7, color=WARNING)

        self.tabs: dict[str, Button] = {}
        tab_widths = (.25, .17, .18, .19, .20)
        x = -.66
        for (category, label), width in zip(CATEGORIES, tab_widths):
            tab = _button(self, label, (x, .315), (width, .048),
                          lambda c=category: self.set_category(c), text_scale=.62)
            self.tabs[category] = tab
            x += width + .012

        self.info_title = Text(parent=self, text="", position=(.08, .285),
                               scale=1.05, color=ACCENT)
        self.info_kind = Text(parent=self, text="", position=(.08, .245),
                              scale=.62, color=Color(.6, .82, 1, 1))
        self.info_body = Text(parent=self, text="", position=(.08, .205),
                              scale=.64, color=TEXT)

        Text(parent=self, text="SEVERITY PRESETS", position=(-.76, -.31),
             scale=.66, color=MUTED)
        for index, (name, value) in enumerate(PRESETS.items()):
            _button(self, name.upper(), (-.59 + index * .13, -.345), (.12, .045),
                    lambda v=value: self.apply_preset(v), text_scale=.65)

        self.split_button = _button(self, "SPLIT: OFF", (-.22, -.345), (.16, .045),
                                    self.toggle_split, text_scale=.65)
        _button(self, "RESET BASELINE", (.00, -.345), (.19, .045),
                self.reset, color=Color(.42, .18, .18, 1), text_scale=.63)
        _button(self, "LIVE DEMO [D]", (.45, -.345), (.20, .05), self.open_demo,
                color=Color(.22, .34, .55, 1), text_scale=.67)
        _button(self, "APPLY & BACK", (.70, -.345), (.20, .05), self.close,
                color=SELECTED, text_scale=.72)

        Text(parent=self,
             text="Keyboard: 1-5 categories · Up/Down focus · Left/Right intensity · Space toggle · "
                  "P preset · S split · D demo · R disable all · Esc back",
             origin=(0, 0), y=-.445, scale=.61, color=MUTED)
        Text(parent=self, text=DISCLAIMER,
             origin=(0, 0), y=-.475, scale=.54, color=Color(.72, .73, .78, 1))

        self.set_category("original")
        self._rebuild_preview()

    def _ids_for_category(self, category: str) -> list[str]:
        if category == "original":
            return list(ORIGINAL_EXPERIENCES)
        return [key for key, spec in EFFECTS.items() if spec["cat"] == category]

    def set_category(self, category: str) -> None:
        self.category = category
        self.status.text = ""
        for key, tab in self.tabs.items():
            tab.color = ACCENT if key == category else SURFACE
            tab.text_color = Color(.08, .08, .1, 1) if key == category else TEXT
        for row in self.rows:
            destroy(row)
        self.rows.clear()
        self.row_ids = self._ids_for_category(category)
        if self.selected_id not in self.row_ids:
            self.selected_id = self.row_ids[0]
        self.focus_index = self.row_ids.index(self.selected_id)
        self._build_rows()
        self.select(self.selected_id)

    def _build_rows(self) -> None:
        for index, item_id in enumerate(self.row_ids):
            y = .25 - index * .05
            row = Entity(parent=self)
            if self.category == "original":
                info = ORIGINAL_EXPERIENCES[item_id]
                enabled = (STATE.disability or "none") == item_id
                toggle_text = "SELECTED" if enabled else "SELECT"
                name = info.name
                blocked = False
            else:
                spec = EFFECTS[item_id]
                enabled = item_id in STATE.lab_effects
                reason = incompatibility_reason(STATE.disability or "none", item_id)
                blocked = reason is not None
                toggle_text = "BLOCKED" if blocked else ("ON" if enabled else "OFF")
                name = spec["name"]

            toggle = _button(row, toggle_text, (-.72, y), (.105, .038),
                             lambda item=item_id: self.toggle(item),
                             color=DISABLED if blocked else (SELECTED if enabled else SURFACE),
                             text_scale=.58)
            toggle.disabled = blocked
            name_button = _button(row, name, (-.50, y), (.32, .038),
                                  lambda item=item_id: self.select(item),
                                  color=SURFACE, text_scale=.64)
            if item_id == self.selected_id:
                name_button.color = SURFACE_HOVER

            if self.category != "original":
                value = STATE.lab_effects.get(item_id, PRESETS["moderate"])
                slider = Slider(parent=row, min=5, max=100, step=1, dynamic=True,
                                default=int(value * 100), position=(-.28, y + .006), scale=.42)
                slider.enabled = enabled and not blocked
                slider.on_value_changed = (
                    lambda item=item_id, control=slider:
                    self.set_intensity(item, control.value)
                )
                Text(parent=row, text=f"{int(value * 100)}%", position=(-.08, y - .008),
                     scale=.56, color=MUTED)
            elif item_id == "visual":
                slider = Slider(parent=row, min=5, max=100, step=1, dynamic=True,
                                default=int(STATE.blindness * 100),
                                position=(-.28, y + .006), scale=.42)
                slider.enabled = enabled
                slider.on_value_changed = lambda control=slider: self.set_blindness(control.value)
                Text(parent=row, text=f"{int(STATE.blindness * 100)}%", position=(-.08, y - .008),
                     scale=.56, color=MUTED)
            self.rows.append(row)

    def toggle(self, item_id: str) -> None:
        self.status.text = ""
        if self.category == "original":
            removed = select_experience(STATE, item_id)
            if removed:
                self.status.text = "Removed incompatible effects: " + ", ".join(
                    EFFECTS[key]["name"] for key in sorted(removed))
        else:
            reason = toggle_effect(STATE, item_id)
            if reason:
                self.status.text = reason
        self.selected_id = item_id
        self.set_category(self.category)
        self._rebuild_preview()

    def select(self, item_id: str) -> None:
        self.selected_id = item_id
        self.focus_index = self.row_ids.index(item_id)
        if self.category == "original":
            info = ORIGINAL_EXPERIENCES[item_id]
            self.info_title.text = info.name
            self.info_kind.text = "ORIGINAL FULL EXPERIENCE - one may be selected"
            self.info_body.text = (
                f"{info.description}\n\n"
                f"WHAT THIS SIMPLIFIES\n{info.simplified}\n\n"
                f"COMMON MISCONCEPTION\n{info.misconception}\n\n"
                f"ACCOMMODATIONS / ASSISTIVE TECH\n{info.assistive}\n\n"
                f"PREVIEW\n{info.preview}\n\n"
                f"REFERENCES\n{info.references}"
            )
        else:
            spec = EFFECTS[item_id]
            self.info_title.text = spec["name"]
            self.info_kind.text = "STACKABLE INDIVIDUAL EFFECT"
            reason = incompatibility_reason(STATE.disability or "none", item_id)
            blocked = f"\n\nCOMPATIBILITY\n{reason}" if reason else ""
            self.info_body.text = (
                f"{spec['desc']}\n\nMEDICAL CONTEXT\n{spec['medical']}\n\n"
                f"IN THIS GAME\n{spec['gameplay']}\n\n"
                f"COMMON MISCONCEPTION\n{spec['misconception']}\n\n"
                f"ASSISTIVE TECHNOLOGY\n{spec['assistive']}\n\n"
                f"REFERENCES\n{spec['refs']}{blocked}"
            )
        self._refresh_summary()

    def set_intensity(self, effect_id: str, value: float) -> None:
        if effect_id not in STATE.lab_effects:
            return
        STATE.lab_effects[effect_id] = value / 100
        for effect in (self.preview_stack.effects if self.preview_stack else []):
            if effect.effect_id == effect_id:
                effect.setIntensity(value / 100)
        self._refresh_summary()

    def set_blindness(self, value: float) -> None:
        STATE.blindness = value / 100
        if self.original_preview:
            self.original_preview._apply_blindness()
        self._refresh_summary()

    def apply_preset(self, value: float) -> None:
        apply_preset(STATE, value)
        self.status.text = f"Applied {int(value * 100)}% severity to active simulations."
        self.set_category(self.category)
        self._rebuild_preview()

    def cycle_preset(self) -> None:
        values = list(PRESETS.values())
        self.preset_index = (self.preset_index + 1) % len(values)
        self.apply_preset(values[self.preset_index])

    def reset(self) -> None:
        reset_to_baseline(STATE)
        self.selected_id = "none"
        self.status.text = "Reset to baseline: all simulated barriers cleared."
        self.set_category("original")
        self._rebuild_preview()

    def toggle_split(self) -> None:
        toggle_split_state(STATE)
        self.split_button.text = f"SPLIT: {'ON' if STATE.lab_split else 'OFF'}"
        self.status.text = "Split-screen affects visual effects during preview and scenarios."

    def adjust_selected_intensity(self, delta: float) -> None:
        if self.category == "original" and self.selected_id == "visual":
            self.set_blindness(max(5, min(100, STATE.blindness * 100 + delta)))
            self.set_category(self.category)
            return
        if self.category != "original" and self.selected_id in STATE.lab_effects:
            value = STATE.lab_effects[self.selected_id] * 100
            self.set_intensity(self.selected_id, max(5, min(100, value + delta)))
            self.set_category(self.category)
        else:
            self.status.text = "Enable this effect before adjusting its intensity."

    def open_demo(self) -> None:
        callback = self.on_demo
        self.close(invoke_callback=False)
        if callback:
            callback()

    def _refresh_summary(self) -> None:
        self.summary.text = active_summary(STATE)
        self.split_button.text = f"SPLIT: {'ON' if STATE.lab_split else 'OFF'}"

    def _rebuild_preview(self) -> None:
        if self.preview_stack:
            self.preview_stack.cleanup()
            self.preview_stack = None
        if self.original_preview:
            destroy(self.original_preview)
            self.original_preview = None
        experience = STATE.disability or "none"
        # Only schizophrenia has a preview that stays behind the panel.
        # Legacy ADHD and visual overlays target camera.ui and would obscure
        # the configuration controls themselves, so they begin in scenarios.
        if experience == "schizophrenia":
            self.original_preview = EffectsManager(player=None)
        if STATE.lab_effects:
            self.preview_stack = EffectStack(context=None)
        self._refresh_summary()

    def input(self, key: str) -> None:
        if key == "escape":
            self.close()
        elif key in {"1", "2", "3", "4", "5"}:
            self.set_category(CATEGORIES[int(key) - 1][0])
        elif key in {"up arrow", "down arrow"}:
            delta = -1 if key == "up arrow" else 1
            self.focus_index = (self.focus_index + delta) % len(self.row_ids)
            self.select(self.row_ids[self.focus_index])
            self.set_category(self.category)
        elif key in {"space", "enter"}:
            self.toggle(self.selected_id)
        elif key in {"left arrow", "right arrow"}:
            self.adjust_selected_intensity(-5 if key == "left arrow" else 5)
        elif key == "p":
            self.cycle_preset()
        elif key == "s":
            self.toggle_split()
        elif key == "d":
            self.open_demo()
        elif key == "r":
            self.reset()

    def close(self, invoke_callback: bool = True) -> None:
        if self.preview_stack:
            self.preview_stack.cleanup()
            self.preview_stack = None
        if self.original_preview:
            destroy(self.original_preview)
            self.original_preview = None
        callback = self.on_close
        destroy(self)
        if callback and invoke_callback:
            callback()

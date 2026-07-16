# Walk In My World — 3D Disability Awareness Simulator

A first-person 3D simulator (Python + [Ursina](https://www.ursinaengine.org/)) that lets you
experience everyday situations through the lens of a disability, while the NPCs around you
breeze through the same tasks.

## Run it

```bash
pip install -r requirements.txt
python3 main.py
```

## The menu

A rotating 3D plaza sits behind the menu. Pick one **experience** and one **scenario**, then START.

**Experiences**

| Mode | What it does |
|---|---|
| No disability (baseline) | Play normally, for comparison |
| ADHD | Distractions hijack the screen; a focus meter drains; press **F** to refocus |
| Schizophrenia | Whispers fade in, shadow figures lurk (look at them and they vanish), reality pulses |
| Wheelchair user | Seated camera height, slower, no jumping, **stairs are impossible** |
| Visual impairment | Adjustable blindness — slider in the menu, `[` / `]` in game |
| Deaf / hard of hearing | All sound cues (PA announcements, warnings behind you) simply never appear |
| Dyslexia | Every sign, question and dialogue line continuously rescrambles |

**Scenarios**

- **School Test** — a timed 5-question exam. Classmates hand in perfect papers around you.
  The teacher gives one hint *out loud only*. Press **V** to toggle accommodations
  (large print / screen reader) and feel the difference they make.
- **Catch the Train** — reach platform 1 in 90 seconds. Stairs are fast, the elevator is
  out of order, and the accessible ramp is the long way round. The departure board is the
  only *visual* source of the announcement.
- **Zombie Escape** — reach the safehouse at night. Others sprint off instantly; groans
  behind you are a sound cue you may never receive.

## Controls

- **WASD** move · **mouse** look · **Space** jump (not in a wheelchair)
- **E** talk to NPCs / interact (desks, departure board, train doors)
- **1/2/3** answer test questions · **V** accommodations · **F** refocus (ADHD)
- **[ / ]** adjust blindness (visual impairment) · **Esc** back to menu / quit

Every scenario ends with a short reflection on what just happened and why it matters.

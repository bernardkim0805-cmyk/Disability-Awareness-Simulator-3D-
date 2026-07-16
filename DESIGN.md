# Design System — Walk In My World

Reusable building blocks for scenarios and future disability modules.
Everything targets Panda3D's fixed-function pipeline (this project disables
GLSL shaders in `main.py` for macOS compatibility): real lights + vertex
normals for shading, `entity.setLightOff()` for anything that should glow.

## Characters — `simulator/human.py`

`Human(skin=…, shirt=…, pants=…, hair=…, hunched=False)` builds a ~1.75-unit
articulated figure around joint pivots:

- **Rig**: hips → torso (lean pivot) → head; per-side shoulder→elbow and
  hip→knee chains. Feet, hands, ears, nose, hair (4 random styles), optional
  glasses (28%) and beard (18%), random eye color, natural height/width
  variation, soft blob shadow.
- **Gait** — `advance(moving, speed)` each frame:
  legs swing from the hip, knees flex only during the swing phase, ankle
  pivots roll the feet (toe-off push / pre-strike toe-up), arms counter-swing
  with elbow bend, pelvis rocks and shifts weight laterally, torso bobs twice
  per stride and leans into the walk, shoulders counter-rotate while the head
  counter-rotates back to keep the gaze forward. speed > 4.5 switches to a
  run: bigger stride, deep elbow bend, forward lean, higher bounce.
  Every instance rolls a **gait personality** (`self.gait`): cadence, stride,
  arm swing, sway, slouch and bounce multipliers — no two people move alike.
  Idle = breathing sway + head glances. `hunched=True` = zombie shamble.
- **Lip sync** — set `human.talking = True` and the mouth flaps organically;
  `DialogueBox.say(..., speaker_entity=npc)` does it automatically while each
  line types out, restoring the posed expression after.
- **Identity accessories** (auto-rolled, skipped when hunched): baseball cap
  (16%) / beanie (12%), open jacket (25%) or tie (15%), wristwatch (30%).
- **Faces** — `set_expression(name)` with poses driven by brow angle/raise,
  mouth-corner curve, eyelid openness and mouth opening:
  `neutral · happy · sad · worried · angry · surprised · focused · tired ·
  smug · scared`.
  Blinking is automatic. Add new emotions by extending `Human.EXPRESSIONS`
  (tuple: brow_angle, brow_raise, mouth_curve, lid, open).
- **Zombie horror kit** (see `zombies.Zombie`): permanently gaping jaw with
  yellowed teeth, lolling head + random twitches, rotting face patches, blood
  runs down the shirt, 50% gouged chest with exposed ribs, 40% missing
  forearm with a stump.
- **Face anatomy**: eye whites + colored iris + pupil + emissive catchlight,
  optional lashes (45%), two-tone lips (dark upper / light lower), a dark
  mouth aperture with teeth revealed as `open` rises, nostrils, cheekbones,
  blush (40%), freckles (15%), hollow-rim glasses (28%), chin beard (18%),
  4 hair styles. Skin-derived colors: lips = skin with reduced G/B; brows =
  hair darkened 20%.

`NPC(name, lines, waypoints, speed, expression, …)` (`simulator/npc.py`) adds
wandering, `sprint_to()` (for "NPCs make it look easy" beats), `face(pos)`,
dialogue lines and the interaction marker.

## Environments — `simulator/world.py`

Lighting: `day_lights() / indoor_lights() / night_lights()` → `SceneLights`
(store as `self.lights` in a scenario; `BaseScenario.cleanup` destroys it).

Builders: `building()` (textured, roof lip, door, lit/dark window grid),
`tree()`, `street_lamp(on=…)` (glow + light pool), `bench()`, `fountain()`,
`night_sky()` (moon + halo + star dome), `road()` (dashed lines),
`sidewalk()`, `abandoned_car()`.

Micro-detail: `ground_details(area, cracks, pebbles, leaves, tufts, scraps)`,
`manhole()`, `puddle()`. Use these on every walkable surface — they sell scale.

## Audio — `simulator/audio.py`

All effects are **synthesized to WAV on first run** (`assets/audio/`) — no
external assets. Cues: `chime` (PA), `bell` (school), `groan` (zombie),
`rumble` (train), `buzz` (ADHD phone), `whisper` (schizophrenia),
`success`/`fail` (endings). Add a cue by adding a generator lambda to
`audio.CUES` built from `_tone/_noise/_mix/_seq`.

Accessibility routing (`AudioManager`, singleton via `get_audio()`):
- **Deaf mode** → `play()` and `speak()` are silent. Hearing players lose the
  same information a deaf player never receives — this asymmetry IS the sim.
- **Visual-impairment mode** → `speak(text)` narrates via macOS `say`
  (cached WAVs in `assets/audio/tts/`, generated on a background thread) —
  a screen-reader experience. Announcements, dialogue, objectives and
  end-screens are already wired through it.
- `Announcer.sound(text, cue=…)` plays the cue + narration + on-screen text;
  `Announcer.visual(...)` shows text and narrates it for blind players.
- Scenarios call `get_audio().play(cue)` for events; `BaseScenario.cleanup`
  stops everything via `stop_all()`.

Rendering quality: `main.py` requests 8x MSAA
(`framebuffer-multisample 1`, `multisamples 8`, `AntialiasAttrib.MMultisample`).

## Adding a new disability module

1. `config.py`: add an entry to `DISABILITIES` (name, icon, color, desc) and
   `REFLECTIONS` (the empathy text at the end).
2. `effects.py`: add its sensory/attention mechanics in `EffectsManager`
   (`__init__` for HUD, `update`/`input` for behavior). Overlays via
   `camera.overlay.color`; fog via the exponential-fog pattern in
   `_apply_blindness`.
3. Scenarios automatically pick it up through `STATE.disability`; add
   scenario-specific twists inside each scenario's `tick()` (see the deaf
   PA-announcement or wheelchair stairs-block patterns).
4. Give NPCs contrasting ease: `sprint_to`, expressions, and an
   `announcer.visual(...)` beat showing them succeed effortlessly.
5. Optionally add social sting: an entry in `config.MOCKERY[scenario][disability]`
   (`name`+`lines` spawns a smug mocker via `BaseScenario.setup_mockery(pos)`;
   `taunt`+`taunt_time` fires once via `tick_mockery(t)`). Keep taunts
   realistic, PG, and let the reflection screen land the counterpoint.

## Conventions

- Text in the world: `Text(parent=self, scale≈6–10, billboard=True)` for
  signs; never above scale 12.
- Quads face −z by default — visible to a player approaching from lower z.
- Every glowing thing (windows, lamps, screens, markers) must call
  `setLightOff()`, otherwise scene lighting dims it.
- Emoji don't render in the bundled font — ASCII markers only.

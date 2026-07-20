"""GPU post-processing for all visual conditions (single fullscreen pass).

The scene is rendered into a texture (panda3d FilterManager, set up by
ursina's camera.shader) and this GLSL 1.20 shader — the newest GLSL this
Mac's legacy OpenGL accepts — re-renders it with every visual simulation
baked into one pass, so cost stays constant no matter how many effects
stack. The UI layer is not captured, keeping educational HUD text readable.

Merge conventions used by VisualEffect.contribute():
    'tunnel', 'scotoma', 'patches', 'snow', 'wave', 'aura', 'osc',
    'dark', 'haze', 'glare', 'desat', 'flicker', 'blur'  -> combine with max()
    'contrast' (1 = normal, lower = flatter)             -> combine with min()
    'cvd_mat' (mat3 as 9 floats, row-major)              -> last writer wins
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from ursina import Shader, camera, Vec2
from panda3d.core import Vec3 as PVec3

VERTEX = '''#version 120
// Passthrough fullscreen-quad vertex shader: transforms the filter quad and
// hands the interpolated texture coordinate to the fragment stage.
uniform mat4 p3d_ModelViewProjectionMatrix;
attribute vec4 p3d_Vertex;
attribute vec2 p3d_MultiTexCoord0;
varying vec2 uv;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv = p3d_MultiTexCoord0;
}
'''

FRAGMENT = '''#version 120
uniform sampler2D tex;        // the rendered scene
uniform float u_time;         // seconds, drives all animation
uniform float u_bypass;       // 1 = show the untouched scene (normal vision)
uniform float u_split;        // 1 = left half normal / right half simulated

// -- field loss ------------------------------------------------------------
uniform float u_tunnel;       // 0..1 peripheral loss (glaucoma / RP)
uniform float u_tunnel_soft;  // vignette edge softness
uniform float u_scotoma;      // 0..1 central blind-spot radius (AMD)
uniform float u_scotoma_seed; // randomizes the scotoma outline
// -- media opacity / light scatter (cataracts) ------------------------------
uniform float u_contrast;     // 1 = normal, lower flattens contrast
uniform float u_haze;         // white veil added over the image
uniform float u_glare;        // highlight bloom around bright pixels
uniform float u_desat;        // 0..1 desaturation
// -- retina ------------------------------------------------------------------
uniform float u_patches;      // dark blotch coverage (diabetic retinopathy)
uniform float u_patch_seed;
uniform float u_dark;         // scene darkening (night blindness)
uniform float u_blur;         // small radius blur (fluctuating acuity)
// -- color vision -------------------------------------------------------------
// Machado et al. (2009) dichromacy matrix, passed as three row vectors
// (panda3d 1.10 only uploads mat4, so rows are simpler and unambiguous)
uniform vec3 u_cvd0;
uniform vec3 u_cvd1;
uniform vec3 u_cvd2;
// -- cortical / perceptual -----------------------------------------------------
uniform float u_snow;         // visual snow static amount
uniform float u_flicker;      // whole-field luminance flicker
uniform float u_wave;         // uv distortion amplitude (migraine)
uniform float u_aura;         // scintillating scotoma progress 0..1
uniform vec2  u_aura_pos;     // aura center in uv space
uniform float u_osc;          // oscillopsia wobble amplitude
varying vec2 uv;

// Cheap value noise: hash the integer lattice, bilinearly interpolate.
// Good enough for organic edges; costs a handful of ALU ops per call.
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);          // smoothstep fade
    return mix(mix(hash(i),               hash(i + vec2(1, 0)), f.x),
               mix(hash(i + vec2(0, 1)),  hash(i + vec2(1, 1)), f.x), f.y);
}

// One simulated sample of the scene at a (possibly distorted) uv.
vec3 scene(vec2 p) { return texture2D(tex, clamp(p, 0.001, 0.999)).rgb; }

void main() {
    vec3 raw = scene(uv);                 // untouched pixel for compare modes
    vec2 p = uv;

    // ---- geometric distortions (applied to the lookup coordinate) --------
    // Migraine wave: slow rolling ripple across the whole field.
    p += u_wave * 0.012 * vec2(sin(p.y * 24.0 + u_time * 2.2),
                               cos(p.x * 21.0 + u_time * 1.9));
    // Oscillopsia: the world itself seems to jiggle (nystagmus). Two small
    // sinusoids at unrelated frequencies read as involuntary eye motion.
    p += u_osc * 0.006 * vec2(sin(u_time * 27.0), cos(u_time * 23.0));

    vec3 c = scene(p);
    // Oscillopsia motion blur: average with a second, offset sample.
    if (u_osc > 0.001)
        c = mix(c, scene(p + vec2(u_osc * 0.008, 0.0)), 0.5);
    // Fluctuating acuity: 4-tap box blur, radius scales with u_blur.
    if (u_blur > 0.001) {
        float r = u_blur * 0.004;
        c = (c + scene(p + vec2(r, r)) + scene(p + vec2(-r, r))
               + scene(p + vec2(r, -r)) + scene(p + vec2(-r, -r))) / 5.0;
    }

    // ---- color vision deficiency (Machado 2009 transformation) -----------
    c = clamp(vec3(dot(u_cvd0, c), dot(u_cvd1, c), dot(u_cvd2, c)), 0.0, 1.0);

    // ---- cataract optics ---------------------------------------------------
    float lum = dot(c, vec3(0.299, 0.587, 0.114));
    c = mix(vec3(lum), c, 1.0 - u_desat);                  // desaturate
    c = mix(vec3(0.5), c, u_contrast);                     // flatten contrast
    c += u_glare * pow(lum, 3.0) * vec3(1.0, 0.97, 0.9);   // scatter highlights
    c = mix(c, vec3(0.85, 0.85, 0.82), u_haze * 0.6);      // milky veil

    // ---- retinopathy blotches ---------------------------------------------
    // Threshold low-frequency noise into irregular dark islands.
    float blotch = vnoise(p * 6.0 + u_patch_seed);
    c *= 1.0 - u_patches * smoothstep(0.62, 0.75, blotch) * 0.92;

    // ---- central scotoma (AMD) --------------------------------------------
    // A gray-brown smudge, not black: the brain fills the hole poorly.
    float ang = atan(p.y - 0.5, p.x - 0.5);
    float wobble = vnoise(vec2(ang * 2.2 + u_scotoma_seed, u_scotoma_seed)) * 0.12;
    float d_c = distance(p, vec2(0.5)) + wobble;
    float hole = smoothstep(u_scotoma + 0.08, u_scotoma - 0.05, d_c);
    c = mix(c, vec3(0.32, 0.29, 0.27), hole * step(0.001, u_scotoma));

    // ---- peripheral loss (glaucoma / RP tunnel) ---------------------------
    float d_e = distance(p, vec2(0.5)) * 1.35;
    float keep = 1.0 - u_tunnel;                            // radius that survives
    c *= smoothstep(keep + u_tunnel_soft, keep - 0.05, d_e);

    // ---- night blindness ----------------------------------------------------
    c *= 1.0 - u_dark * 0.85;

    // ---- visual snow / flicker ---------------------------------------------
    // Per-pixel per-frame static, like analog TV noise laid over vision.
    float grain = hash(p * vec2(1911.0, 1737.0) + fract(u_time) * 61.0) - 0.5;
    c += grain * u_snow * 0.25;
    c *= 1.0 + u_flicker * 0.08 * sin(u_time * 19.0);

    // ---- migraine aura ------------------------------------------------------
    // An expanding C-shaped ring of shimmering zigzag light with a poorly
    // defined blind area just inside it (scintillating scotoma).
    if (u_aura > 0.001) {
        float radius = u_aura * 0.55;
        float d_a = distance(p, u_aura_pos);
        float ring = smoothstep(0.05, 0.0, abs(d_a - radius));
        float zig = 0.5 + 0.5 * sin(atan(p.y - u_aura_pos.y, p.x - u_aura_pos.x)
                                    * 34.0 + u_time * 26.0);
        vec3 shimmer = vec3(1.0, 0.95, 0.85) * ring * zig;
        float inner = smoothstep(radius, radius - 0.14, d_a);   // blind inside
        c = mix(c, vec3(0.75), inner * 0.55 * min(u_aura * 2.0, 1.0));
        c += shimmer * 0.9;
    }

    // ---- compare modes ------------------------------------------------------
    // Split screen: left half stays normal; a thin divider marks the seam.
    if (u_split > 0.5) {
        if (uv.x < 0.5) c = raw;
        if (abs(uv.x - 0.5) < 0.0012) c = vec3(1.0, 1.0, 0.4);
    }
    if (u_bypass > 0.5) c = raw;          // 'normal vision' button

    gl_FragColor = vec4(c, 1.0);
}
'''


class PostFX:
    """Owns the filter shader and pushes merged parameters to the GPU."""

    #: uniform defaults = the identity image (documented merge rule in ())
    DEFAULTS = dict(tunnel=0.0, tunnel_soft=.25, scotoma=0.0, scotoma_seed=3.7,
                    contrast=1.0, haze=0.0, glare=0.0, desat=0.0,
                    patches=0.0, patch_seed=1.3, dark=0.0, blur=0.0,
                    snow=0.0, flicker=0.0, wave=0.0, aura=0.0,
                    aura_pos=(.62, .55), osc=0.0,
                    cvd_mat=(1, 0, 0, 0, 1, 0, 0, 0, 1),
                    bypass=1.0, split=0.0)

    def __init__(self):
        self.shader = None
        self.attached = False
        self.available = True
        self.error = None
        self.time = 0.0

    def default_params(self):
        return dict(self.DEFAULTS)

    def _attach(self):
        if self.attached:
            return True
        if not self.available:
            return False
        try:
            self.shader = Shader(name='disability_postfx', language=Shader.GLSL,
                                 vertex=VERTEX, fragment=FRAGMENT)
            camera.shader = self.shader
            if not getattr(camera, 'filter_quad', None):
                raise RuntimeError('Ursina did not create a post-process filter quad')
            self.attached = True
            return True
        except Exception as error:
            # Unsupported/legacy GPUs keep the unfiltered scene rather than
            # crashing the simulator. The original non-GLSL experiences remain usable.
            self.error = str(error)
            self.available = False
            self.attached = False
            try:
                camera.shader = None
            except Exception:
                pass
            return False

    def apply(self, params):
        """Upload the merged parameter set. Called once per frame."""
        if not self._attach():
            return
        from ursina import time as utime
        self.time += utime.dt
        q = camera.filter_quad
        q.set_shader_input('u_time', self.time)
        for name in ('tunnel', 'tunnel_soft', 'scotoma', 'scotoma_seed',
                     'contrast', 'haze', 'glare', 'desat', 'patches',
                     'patch_seed', 'dark', 'blur', 'snow', 'flicker',
                     'wave', 'aura', 'osc', 'bypass', 'split'):
            q.set_shader_input('u_' + name, float(params[name]))
        q.set_shader_input('u_aura_pos', Vec2(*params['aura_pos']))
        m = params['cvd_mat']                      # row-major 3x3
        q.set_shader_input('u_cvd0', PVec3(m[0], m[1], m[2]))
        q.set_shader_input('u_cvd1', PVec3(m[3], m[4], m[5]))
        q.set_shader_input('u_cvd2', PVec3(m[6], m[7], m[8]))

    def reset(self):
        if self.attached:
            self.apply(self.default_params())


_postfx = None


def get_postfx():
    global _postfx
    if _postfx is None:
        _postfx = PostFX()
    return _postfx

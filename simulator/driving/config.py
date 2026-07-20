"""Central, adjustable configuration for the open-world driving simulation.

Every tunable the brief asked for lives here so designers can rebalance the
world without touching system logic: traffic/pedestrian density, weather
probability, accident frequency, police response, road complexity, and the
per-region identity that gives downtown / suburbs / industrial / highway /
countryside their distinct feel.

SCOPE NOTE: this runs on a fixed-function primitive renderer, so the world is
'AAA-structured' (interconnected districts, highway with ramps, a lit tunnel,
a bridge over water, region-aware AI) at a bounded scale — not a literal
square-mile GTA map, which the pipeline could not draw at frame rate.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

# ---------------------------------------------------------------- world layout
WORLD = dict(
    downtown_block=30,             # the core grid block size (B)
    road_width=10,
    # each district: center (x,z), half-extent, and identity knobs
    regions={
        'downtown':   dict(center=(0, 0),     radius=55,  speed=40,
                           traffic=1.0, peds=1.0, tint=(.55, .58, .62)),
        'suburbs':    dict(center=(-130, 40), radius=55,  speed=30,
                           traffic=.45, peds=.5, tint=(.6, .7, .55)),
        'industrial': dict(center=(120, -50), radius=55,  speed=45,
                           traffic=.6, peds=.15, tint=(.5, .48, .45),
                           trucks=.6),
        'countryside':dict(center=(-40, 150), radius=70,  speed=55,
                           traffic=.3, peds=.05, tint=(.55, .65, .45)),
        'highway':    dict(center=(0, 0),     radius=200, speed=90,
                           traffic=.8, peds=0.0, tint=(.5, .5, .52)),
    },
)

# ---------------------------------------------------------------- traffic AI
TRAFFIC = dict(
    density=1.0,                   # global multiplier over per-region traffic
    risky_fraction=.15,            # aggressive/distracted drivers
    truck_fraction=.18,            # of industrial/highway traffic
    highway_speed=15.5,            # world-units/s cruise on the highway
    city_speed=7.0,
    follow_gap=6.5,
    overtake_gap=9.0,
)

# ---------------------------------------------------------------- pedestrians
PEDESTRIANS = dict(density=1.0, jaywalk_chance=.15)

# ---------------------------------------------------------------- weather
WEATHER = dict(
    probabilities=dict(clear=.4, rain=.22, fog=.14, storm=.1, night=.14),
    rain_grip=.75, fog_visibility=45, storm_wind=1.4, snow_grip=.6,
)

# ---------------------------------------------------------------- emergencies
EMERGENCY = dict(accident_frequency=.0, ambulance_delay=(60, 95))

# ---------------------------------------------------------------- police
POLICE = dict(
    dispatch_heat=10, response_time=(2, 5),
    patrol_speed=12.5, pursuit_speed=15.5,
    citation_fine=180,
)

# ---------------------------------------------------------------- special roads
INFRA = dict(
    tunnel=dict(center=(0, -120), length=70, darkness=.62, echo=1.8),
    bridge=dict(center=(0, 95), length=90, wind=1.2, water_y=-8),
)

# ---------------------------------------------------------------- quality / LOD
# Honest note: this project runs on the fixed-function pipeline (no programmable
# shaders on this Mac), so PBR/deferred/HDR/SSAO/SSR/volumetrics/TAA are NOT
# available. These knobs control the achievable levers: draw density, LOD
# distance, and the single GLSL-120 post-process pass.
QUALITY = dict(
    pedestrian_density=1.0,        # multiplier on crowd size
    traffic_density=1.0,
    lod_near=22,                   # full-update / full-detail radius
    lod_far_budget=4,              # far agents updated per frame (1/N)
    wet_road_sheen=True,           # cheap post-fx wet look in rain
    # capabilities this engine genuinely supports vs. cannot:
    supports=dict(fixed_function_lighting=True, glsl120_postfx=True,
                  vertex_colors=True, textures=True, fog=True),
    unsupported=('PBR', 'deferred', 'HDR', 'SSAO', 'SSR', 'volumetrics',
                 'TAA', 'reflection_probes', 'realtime_GI', 'ragdoll_euphoria',
                 'rigidbody_destruction'),
)

# ---------------------------------------------------------------- vehicle damage
DAMAGE = dict(
    minor_impact=1.0,              # speed (world u/s) below = scratch only
    major_impact=6.0,              # above = heavy damage
    smoke_threshold=3,             # damage points before the hood smokes
    undriveable=5,                 # damage points before it's totaled/towed
    steering_pull_per_point=.06,   # alignment drift added per damage point
    speed_loss_per_point=.05,      # top-speed penalty per damage point
)

from animations.dynamic_ball import bounce_on_stairs
from objects.infinite_stairs import create_stairs_with_base
from objects.circle_bricks import create_radial_brick_ring
from objects.torii_corridor import build_torii_sequence
from utils.constants import VEL_NORMALIZER, TOTAL_FRAMES, SQUASH, STRETCH

STAIR_GROUPS = [
    "stairs_topleft_grp",
    "stairs_bottomleft_grp",
    "stairs_bottomright_grp",
    "stairs_topright_grp",
]

def run_bounce():
    bounce_on_stairs(
        ball_rig="ball_rig",
        stair_groups_in_order=STAIR_GROUPS,
        start_frame=1,
        total_frames=TOTAL_FRAMES,
        squash=SQUASH,
        stretch=STRETCH,
    )

def create_stairs():
    create_stairs_with_base()

def create_circle_brick():
    create_radial_brick_ring(
        count=12,
        inner_radius=3.5,
        outer_radius=4.5,
        height=0.4,
        gap_angle_deg=1.2
    )

def create_torii_corridor():
    build_torii_sequence()
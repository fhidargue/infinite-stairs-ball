from animations.dynamic_ball import bounce_on_stairs
from objects.infinite_stairs import create_stairs_with_base

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
        frames_per_bounce=23.5,
        squash=0.38,
        stretch=0.40,
    )

def create_stairs():
    create_stairs_with_base()
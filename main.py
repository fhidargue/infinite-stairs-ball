from animations.dynamic_ball import bounce_on_stairs

STAIR_GROUPS = [
    "stairs_topleft_grp",
    "stairs_bottomleft_grp",
    "stairs_bottomright_grp",
    "stairs_topright_grp",
]

def run():
    bounce_on_stairs(
    ball_rig="ball_rig",
    stair_groups_in_order=STAIR_GROUPS,
    start_frame=1,
    frames_per_bounce=30,
    steps_per_jump=2,
    squash=0.38,
    stretch=0.40,
)
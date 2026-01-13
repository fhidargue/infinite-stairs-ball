from animations.dynamic_ball import bounce_on_stairs
from objects.circle_bricks import create_radial_brick_ring
from objects.infinite_stairs import create_stairs_with_base
from objects.torii_corridor import build_torii_sequence
from utils.constants import SQUASH, STRETCH, TOTAL_FRAMES, STAIR_GROUPS, STEP_EXCLUSIONS, BALL2_SEQUENCE

def run_bounce():
    """
    Runs the bounce animation for the primary ball rig.
    """
    bounce_on_stairs(
        ball_rig="ball_rig",
        stair_groups_in_order=STAIR_GROUPS,
        excluded_stairs=STEP_EXCLUSIONS,
        start_frame=1,
        total_frames=TOTAL_FRAMES,
        squash=SQUASH,
        stretch=STRETCH,
    )

def run_bounce_second_ball():
    """
    Runs the bounce animation for the second ball rig.
    """
    bounce_on_stairs(
        ball_rig="ball_rig_1",
        stair_groups_in_order=[],
        excluded_stairs={},
        step_sequence=BALL2_SEQUENCE,
        start_frame=1,
        total_frames=TOTAL_FRAMES,
        squash=SQUASH,
        stretch=STRETCH,
        jump_power=1.6,
        impulse_ratio=0.33,
        squash_hold_mult=1.8
    )

def create_stairs():
    """
    Creates the infinite stairs with a base in the scene.
    """
    create_stairs_with_base()


def create_circle_brick():
    """
    Creates a radial ring of bricks in the scene.
    """
    create_radial_brick_ring()


def create_torii_corridor():
    """
    Creates a torii corridor with stairs in the scene.
    """
    build_torii_sequence()

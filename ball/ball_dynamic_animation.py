 
import pymel.core as pm
import re


# ------------------------------------------------------------
# GLOBAL CONFIG
# ------------------------------------------------------------

VEL_NORMALIZER = 60
PEAK_BIAS = 0.65        # > 0.5 = more hang time at apex (0.6–0.7 recommended)


# ------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------

_num_re = re.compile(r"(\d+)$")


def trailing_int(name, default=0):
    m = _num_re.search(name)
    return int(m.group(1)) if m else default


def get_ball_controls(ball_rig):
    MOVE_CTRL = pm.PyNode(f"{ball_rig}|move_anim")
    SQUASH_CTRL = pm.PyNode(f"{ball_rig}|move_anim|squash_stretch_axis_anim")
    ROTATE_CTRL = pm.PyNode(
        f"{ball_rig}|move_anim|squash_stretch_axis_anim|cancel_rotations_grp|rotate_anim"
    )
    ball_geo = pm.PyNode(f"{ball_rig}|ball_geo")

    bbox = ball_geo.getBoundingBox(space="world")
    radius = (bbox.max().y - bbox.min().y) * 0.5

    return MOVE_CTRL, SQUASH_CTRL, ROTATE_CTRL, radius


def collect_steps(stair_group):
    grp = pm.PyNode(stair_group)
    kids = pm.listRelatives(grp, children=True, type="transform") or []
    steps = [k for k in kids if k.nodeName().lower().startswith("step")]
    steps.sort(key=lambda n: trailing_int(n.nodeName()))
    return steps


def step_top_center(step, radius):
    bb = step.getBoundingBox(space="world")

    x = (bb.min().x + bb.max().x) * 0.5
    z = (bb.min().z + bb.max().z) * 0.5
    y = bb.max().y + radius

    return pm.datatypes.Vector(x, y, z)


def collect_targets(stair_groups, radius):
    targets = []
    for grp in stair_groups:
        for step in collect_steps(grp):
            targets.append(step_top_center(step, radius))
    return targets


# ------------------------------------------------------------
# MAIN FUNCTION
# ------------------------------------------------------------

def bounce_on_stairs(
    ball_rig,
    stair_groups_in_order,
    ball_type="tennis",
    start_frame=1,
    frames_per_bounce=26,   # 👈 MAIN SPEED CONTROL
    steps_per_jump=2
):
    """
    Stylized slow bouncing ball across impossible stairs.
    - Constant bounce height
    - Constant timing
    - 2 stairs per jump
    - Designed hang time
    """

    MOVE_CTRL, SQUASH_CTRL, ROTATE_CTRL, RADIUS = get_ball_controls(ball_rig)

    squash_by_type = {
        "tennis": 0.2,
        "beach": 0.5,
        "bowling": 0.15,
    }
    squash_factor = squash_by_type.get(ball_type.lower(), 0.2)

    targets = collect_targets(stair_groups_in_order, RADIUS)
    if len(targets) < 2:
        pm.warning("Not enough stair steps found.")
        return

    # ------------------------------------------------
    # MOTION CONSTANTS
    # ------------------------------------------------
    BOUNCE_HEIGHT = RADIUS * 6.0
    FRAMES = frames_per_bounce

    frame = start_frame
    prev_pos = targets[0]

    # ------------------------------------------------
    # INITIAL CONTACT
    # ------------------------------------------------
    MOVE_CTRL.translate.set(prev_pos)
    pm.setKeyframe(MOVE_CTRL.translate, t=frame)

    scale_y = 1.0 - squash_factor
    squash_offset = (1.0 - scale_y) * RADIUS
    MOVE_CTRL.translateY.set(prev_pos.y - squash_offset)
    pm.setKeyframe(MOVE_CTRL.translateY, t=frame)

    SQUASH_CTRL.scaleY.set(scale_y)
    pm.setKeyframe(SQUASH_CTRL.scaleY, t=frame)

    # ------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------
    for i in range(0, len(targets) - steps_per_jump, steps_per_jump):
        a = targets[i]
        b = targets[i + steps_per_jump]

        # -------- PEAK (with hang time) --------
        peak_frame = frame + int(FRAMES * PEAK_BIAS)
        peak_pos = (a + b) * 0.5
        peak_pos.y = max(a.y, b.y) + BOUNCE_HEIGHT

        MOVE_CTRL.translate.set(peak_pos)
        pm.setKeyframe(MOVE_CTRL.translate, t=peak_frame)

        stretch = 1.0 + squash_factor * 0.75
        pm.setKeyframe(SQUASH_CTRL.scaleY, v=stretch, t=peak_frame)

        # -------- NEXT CONTACT --------
        next_frame = frame + FRAMES
        MOVE_CTRL.translate.set(b)
        pm.setKeyframe(MOVE_CTRL.translate, t=next_frame)

        scale_y = 1.0 - squash_factor
        squash_offset = (1.0 - scale_y) * RADIUS
        MOVE_CTRL.translateY.set(b.y - squash_offset)
        pm.setKeyframe(MOVE_CTRL.translateY, t=next_frame)

        pm.setKeyframe(SQUASH_CTRL.scaleY, v=scale_y, t=next_frame)

        # -------- ROTATION --------
        travel = (b - prev_pos).length()
        rot_amount = travel * VEL_NORMALIZER
        current_rot = ROTATE_CTRL.rotateZ.get()
        pm.setKeyframe(
            ROTATE_CTRL.rotateZ,
            v=current_rot + rot_amount,
            t=next_frame,
        )

        prev_pos = b
        frame = next_frame

    # ------------------------------------------------
    # CLEANUP / POLISH
    # ------------------------------------------------
    pm.keyTangent(
        MOVE_CTRL.translateY,
        edit=True,
        itt="auto",
        ott="auto",
        inWeight=8,
        outWeight=8,
    )

    pm.setKeyframe(SQUASH_CTRL.scaleY, v=1.0, t=frame + 1)


# ------------------------------------------------------------
# USAGE
# ------------------------------------------------------------

STAIR_GROUPS = [
    "stairs_topleft_grp",
    "stairs_bottomleft_grp",
    "stairs_bottomright_grp",
    "stairs_topright_grp",
]

# Example run:
bounce_on_stairs(
    ball_rig="ball_rig",
    stair_groups_in_order=STAIR_GROUPS,
    ball_type="tennis",
    start_frame=1,
    frames_per_bounce=26,
    steps_per_jump=2
)

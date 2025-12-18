import pymel.core as pm

from utils.constants import (
    PEAK_BIAS,
    BOUNCE_HEIGHT_MULT,
    PRE_CONTACT_OFFSET,
    SQUASH_FRAME_OFFSET,
    RECOVER_FRAME_OFFSET,
    SQUASH_HOLD_FRAMES,
    STRETCH_AT_PEAK,
    STRETCH_PRECONTACT_MULT,
    STRETCH_RISE_MULT,
    APEX_TANGENT_WEIGHT,
    VEL_NORMALIZER
)

from utils.utils import trailing_int

def get_ball_controls(ball_rig):
    MOVE = pm.PyNode(f"{ball_rig}|move_anim")
    SQUASH = pm.PyNode(f"{ball_rig}|move_anim|squash_stretch_axis_anim")
    ROTATE = pm.PyNode(
        f"{ball_rig}|move_anim|squash_stretch_axis_anim|cancel_rotations_grp|rotate_anim"
    )

    ball_geo = pm.PyNode(f"{ball_rig}|ball_geo")
    bbox = ball_geo.getBoundingBox(space="world")
    radius = (bbox.max().y - bbox.min().y) * 0.5
    return MOVE, SQUASH, ROTATE, radius

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

def collect_targets(ball_rig, stair_groups_in_order, steps_per_jump=2):
    _, _, _, radius = get_ball_controls(ball_rig)
    targets = []
    for grp in stair_groups_in_order:
        steps = collect_steps(grp)
        for i in range(0, len(steps), max(1, steps_per_jump)):
            targets.append(step_top_center(steps[i], radius))
    return targets

def bounce_on_stairs(
    ball_rig,
    stair_groups_in_order,
    start_frame=1,
    frames_per_bounce=30,
    steps_per_jump=2,
    squash=0.38,
    stretch=0.40,
):
    """
    Animate a ball rig bouncing up a series of stairs.

    Args:
        ball_rig (str): Name of the ball rig root node.
        stair_groups_in_order (list of str): List of stair group names in the order to bounce.
        start_frame (int): Frame to start the animation.
        frames_per_bounce (int): Number of frames for each bounce cycle.
        steps_per_jump (int): Number of steps to skip per jump.
        squash (float): Amount of squash to apply on contact (0.0 to 1.0).
        stretch (float): Amount of stretch to apply during flight (0.0 to 1.0).
    """

    MOVE, SQUASH_CTRL, ROTATE, RADIUS = get_ball_controls(ball_rig)
    targets = collect_targets(ball_rig, stair_groups_in_order, steps_per_jump=steps_per_jump)

    if len(targets) < 2:
        pm.warning("Not enough targets found. Check stair group names and step naming.")
        return

    FRAMES = frames_per_bounce
    BOUNCE_HEIGHT = RADIUS * BOUNCE_HEIGHT_MULT

    apex_frames = []
    contact_frames = []

    def key_translate(t, v):
        pm.setKeyframe(MOVE.translateX, v=v.x, t=t)
        pm.setKeyframe(MOVE.translateY, v=v.y, t=t)
        pm.setKeyframe(MOVE.translateZ, v=v.z, t=t)

    def key_y(t, y):
        pm.setKeyframe(MOVE.translateY, v=y, t=t)

    def key_sy(t, sy):
        pm.setKeyframe(SQUASH_CTRL.scaleY, v=sy, t=t)

    current_rotation = ROTATE.rotateZ.get()

    # Initial contact
    frame = start_frame
    prev = targets[0]
    key_translate(frame, prev)
    key_sy(frame, 1.0)

    # Loop the bounces on the stairs
    for index in range(len(targets) - 1):
        a = targets[index]
        b = targets[index + 1]

        peak_frame = frame + int(FRAMES * PEAK_BIAS)
        contact_frame = frame + FRAMES

        apex_frames.append(peak_frame)
        contact_frames.append(contact_frame)

        peak = (a + b) * 0.5
        peak.y = max(a.y, b.y) + BOUNCE_HEIGHT
        key_translate(peak_frame, peak)
        key_sy(peak_frame, 1.0 + STRETCH_AT_PEAK)

        pre_contact = contact_frame - max(1, PRE_CONTACT_OFFSET)
        key_sy(pre_contact, 1.0 + stretch * STRETCH_PRECONTACT_MULT)

        stair_top_y = (b.y - RADIUS)
        key_y(pre_contact, stair_top_y + RADIUS * (1.0 + stretch * STRETCH_PRECONTACT_MULT))

        key_translate(contact_frame, b)
        key_sy(contact_frame, 1.0)

        squash_frame = contact_frame + SQUASH_FRAME_OFFSET
        recover_frame = contact_frame + RECOVER_FRAME_OFFSET
        launch_frame = recover_frame + SQUASH_HOLD_FRAMES

        squash_scale = 1.0 - squash
        squash_center_y = stair_top_y + (RADIUS * squash_scale)

        key_sy(squash_frame, squash_scale)
        key_y(squash_frame, squash_center_y)

        # Hold the squash for a few frames
        key_sy(recover_frame, squash_scale)
        key_y(recover_frame, squash_center_y)

        key_sy(launch_frame, 1.0)
        key_y(launch_frame, stair_top_y + RADIUS)

        rise_frame = min(contact_frame + int(FRAMES * 0.65), frame + FRAMES - 1)
        key_sy(rise_frame, 1.0 + stretch * STRETCH_RISE_MULT)

        # Rotation
        travel = (b - prev).length()
        current_rotation += travel * VEL_NORMALIZER
        pm.setKeyframe(ROTATE.rotateZ, v=current_rotation, t=contact_frame)

        prev = b
        frame = contact_frame

    pm.keyTangent(MOVE.translateY, edit=True, weightedTangents=True, itt="spline", ott="spline")

    for f in contact_frames:
        pm.keyTangent(
            MOVE.translateY,
            edit=True,
            time=(f, f),
            inTangentType="linear",
            outTangentType="linear",
            inWeight=0,
            outWeight=0,
        )

    for f in apex_frames:
        pm.keyTangent(
            MOVE.translateY,
            edit=True,
            time=(f, f),
            inTangentType="auto",
            outTangentType="auto",
            inWeight=APEX_TANGENT_WEIGHT,
            outWeight=APEX_TANGENT_WEIGHT,
        )

    pm.keyTangent(SQUASH_CTRL.scaleY, edit=True, itt="auto", ott="auto", weightedTangents=True)


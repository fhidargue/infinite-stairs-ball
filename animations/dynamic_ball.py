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

STEP_EXCLUSIONS = {
    "stairs_bottomright_grp": {"step_1"},
}

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
    exclude = STEP_EXCLUSIONS.get(grp.nodeName(), set())

    kids = pm.listRelatives(grp, children=True, type="transform") or []
    steps = [
        k for k in kids
        if k.nodeName().lower().startswith("step")
        and k.nodeName().lower() not in exclude
    ]

    steps.sort(key=lambda n: trailing_int(n.nodeName()))
    return steps

def step_top_center(step, radius):
    bb = step.getBoundingBox(space="world")
    x = (bb.min().x + bb.max().x) * 0.5
    z = (bb.min().z + bb.max().z) * 0.5
    y = bb.max().y + radius
    return pm.datatypes.Vector(x, y, z)

def collect_targets(ball_rig, stair_groups_in_order):
    _, _, _, radius = get_ball_controls(ball_rig)
    targets = []

    for grp_name in stair_groups_in_order:
        steps = collect_steps(grp_name)

        for step in steps:
            step_num = trailing_int(step.nodeName())

            if (step_num - 1) % 3 != 0:
                continue

            pos = step_top_center(step, radius)
            targets.append(pos)

    return targets

def bounce_on_stairs(
    ball_rig,
    stair_groups_in_order,
    start_frame=1,
    frames_per_bounce=30,
    squash=0.38,
    stretch=0.40,
):

    MOVE, SQUASH_CTRL, ROTATE, RADIUS = get_ball_controls(ball_rig)
    targets = collect_targets(ball_rig, stair_groups_in_order)

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

    frame = start_frame
    prev = targets[0]

    # Initial placement
    key_translate(frame, prev)
    key_sy(frame, 1.0)

    for index in range(len(targets) - 1):
        a = targets[index]
        b = targets[index + 1]

        peak_frame = frame + int(FRAMES * PEAK_BIAS)
        contact_frame = frame + FRAMES

        apex_frames.append(peak_frame)
        contact_frames.append(contact_frame)

        stair_top_y = b.y - RADIUS

        peak = (a + b) * 0.5
        peak.y = max(a.y, b.y) + BOUNCE_HEIGHT
        key_translate(peak_frame, peak)
        key_sy(peak_frame, 1.0 + STRETCH_AT_PEAK)

        pre_contact = contact_frame - max(1, PRE_CONTACT_OFFSET)
        pre_sy = 1.0 + stretch * STRETCH_PRECONTACT_MULT

        key_sy(pre_contact, pre_sy)
        key_y(pre_contact, stair_top_y + RADIUS * pre_sy)

        contact_center_y = stair_top_y + RADIUS
        key_translate(contact_frame, b)
        key_y(contact_frame, contact_center_y)
        key_sy(contact_frame, 1.0)

        squash_scale = 1.0 - squash
        squash_center_y = stair_top_y + RADIUS * squash_scale

        squash_frame = contact_frame + SQUASH_FRAME_OFFSET
        recover_frame = contact_frame + RECOVER_FRAME_OFFSET
        launch_frame = recover_frame + SQUASH_HOLD_FRAMES

        for t in (squash_frame, recover_frame):
            key_translate(t, b)
            key_sy(t, squash_scale)
            key_y(t, squash_center_y)

        launch_sy = 1.0 + stretch * STRETCH_RISE_MULT
        launch_center_y = stair_top_y + RADIUS

        key_translate(launch_frame, b)
        key_sy(launch_frame, launch_sy)
        key_y(launch_frame, launch_center_y)

        impulse_frame = launch_frame + 1
        impulse_height = launch_center_y + (BOUNCE_HEIGHT * 0.22)

        key_translate(impulse_frame, b)
        key_y(impulse_frame, impulse_height)
        key_sy(impulse_frame, launch_sy)

        travel = (b - prev).length()
        current_rotation += travel * VEL_NORMALIZER
        pm.setKeyframe(ROTATE.rotateZ, v=current_rotation, t=contact_frame)

        prev = b
        frame = contact_frame

    pm.keyTangent(
        MOVE.translateY,
        edit=True,
        weightedTangents=True,
        itt="spline",
        ott="spline",
    )

    # Fast bottom
    for f in contact_frames:
        for t in (f, f + SQUASH_FRAME_OFFSET, f + RECOVER_FRAME_OFFSET):
            pm.keyTangent(
                MOVE.translateY,
                edit=True,
                time=(t, t),
                inTangentType="linear",
                outTangentType="linear",
                inWeight=0,
                outWeight=0,
            )

    # Hang time at apex
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

    pm.keyTangent(
        SQUASH_CTRL.scaleY,
        edit=True,
        itt="auto",
        ott="auto",
        weightedTangents=True,
    )


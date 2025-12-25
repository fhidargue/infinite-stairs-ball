import pymel.core as pm

from utils.constants import (
    PEAK_BIAS,
    BOUNCE_HEIGHT_MULT,
    PRE_CONTACT_OFFSET,
    SQUASH_FRAME_OFFSET,
    RECOVER_FRAME_OFFSET,
    SQUASH_HOLD_FRAMES,
    STRETCH_PRECONTACT_MULT,
    STRETCH_RISE_MULT,
    APEX_TANGENT_WEIGHT,
    VEL_NORMALIZER,
    CONTACT_EPSILON
)

from utils.utils import trailing_int

# TODO: Implement diagonal rotation for ball
DIAG_ANGLE = 22.0 

STAIR_DIAGONAL = {
    "stairs_topleft_grp":  DIAG_ANGLE,
    "stairs_bottomleft_grp": -DIAG_ANGLE,
    "stairs_bottomright_grp": -DIAG_ANGLE,
    "stairs_topright_grp":  DIAG_ANGLE,
}

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
    return pm.datatypes.Vector(
        (bb.min().x + bb.max().x) * 0.5,
        bb.max().y + radius,
        (bb.min().z + bb.max().z) * 0.5,
    )


def collect_targets(ball_rig, stair_groups_in_order):
    _, _, _, radius = get_ball_controls(ball_rig)
    targets = []

    for grp_name in stair_groups_in_order:
        for step in collect_steps(grp_name):
            step_num = trailing_int(step.nodeName())
            if (step_num - 1) % 3 != 0:
                continue
            targets.append((grp_name, step_top_center(step, radius)))

    return targets
    

def bounce_on_stairs(
    ball_rig,
    stair_groups_in_order,
    start_frame=1,
    total_frames=250,
    squash=0.38,
    stretch=0.40,
    roll_normalizer=VEL_NORMALIZER,
):
    MOVE, SQUASH, ROTATE, RADIUS = get_ball_controls(ball_rig)
    targets = collect_targets(ball_rig, stair_groups_in_order)

    if len(targets) < 2:
        pm.warning("Not enough targets.")
        return

    hop_count = len(targets) - 1

    # Animation ends by ball descending
    needed = int(total_frames) + int(PRE_CONTACT_OFFSET)
    base = max(12, needed // hop_count)
    durations = [base] * hop_count
    for i in range(needed - base * hop_count):
        durations[i] += 1

    BOUNCE_HEIGHT = RADIUS * BOUNCE_HEIGHT_MULT

    apex_frames = []
    contact_frames = []

    current_roll = ROTATE.rotateZ.get()
    frame = int(start_frame)

    # TODO: add utils
    def key_xyz(t, v):
        v = pm.datatypes.Vector(v)
        pm.setKeyframe(MOVE.translateX, v=v.x, t=t)
        pm.setKeyframe(MOVE.translateY, v=v.y, t=t)
        pm.setKeyframe(MOVE.translateZ, v=v.z, t=t)

    def key_xz(t, v):
        pm.setKeyframe(MOVE.translateX, v=v.x, t=t)
        pm.setKeyframe(MOVE.translateZ, v=v.z, t=t)

    def key_y(t, y):
        pm.setKeyframe(MOVE.translateY, v=y, t=t)

    def key_sy(t, sy):
        pm.setKeyframe(SQUASH.scaleY, v=sy, t=t)

    def squash_upright(t):
        pm.setKeyframe(SQUASH.rotateX, v=0.0, t=t)
        pm.setKeyframe(SQUASH.rotateY, v=0.0, t=t)
        pm.setKeyframe(SQUASH.rotateZ, v=0.0, t=t)

    # Starting pose
    p0 = targets[0]
    key_xyz(frame, p0)
    key_sy(frame, 1.0)
    squash_upright(frame)

    # Bounces
    for i in range(hop_count):
        grp_a, a = targets[i]
        b = targets[i + 1]

        FRAMES = int(durations[i])
        is_last = (i == hop_count - 1)

        diag = STAIR_DIAGONAL.get(grp_a, 0.0)

        t0 = frame
        t_squash  = t0 + int(SQUASH_FRAME_OFFSET)
        t_recover = t0 + int(RECOVER_FRAME_OFFSET)
        t_launch  = t_recover + int(SQUASH_HOLD_FRAMES)
        t_impulse = t_launch + 1

        t_peak    = t0 + int(FRAMES * PEAK_BIAS)
        t_contact = t0 + FRAMES
        t_pre     = t_contact - int(PRE_CONTACT_OFFSET)

        # Diagonal timing
        t_up_diag   = t_peak - 2
        t_down_diag = t_peak + 2

        if is_last:
            t_contact = None

        apex_frames.append(t_peak)
        if t_contact is not None:
            contact_frames.append(t_contact)

        stair_a = a.y - RADIUS
        stair_b = b.y - RADIUS

        # Initial circle in A
        key_xyz(t0, pm.datatypes.Vector(
            a.x,
            stair_a + RADIUS + CONTACT_EPSILON,
            a.z
        ))
        key_sy(t0, 1.0)
        squash_upright(t0)

        # Squash in A
        squash_scale = 1.0 - squash
        squash_center = stair_a + (RADIUS * squash_scale) + CONTACT_EPSILON

        for t in (t_squash, t_recover):
            key_xz(t, a)
            key_y(t, squash_center)
            key_sy(t, squash_scale)
            squash_upright(t)

        # Jump
        center_a = stair_a + RADIUS + CONTACT_EPSILON
        launch_sy = 1.0 + stretch * STRETCH_RISE_MULT

        key_xz(t_launch, a)
        key_y(t_launch, center_a)
        key_sy(t_launch, launch_sy)
        squash_upright(t_launch)

        # Jump impulse
        impulse_y = center_a + (BOUNCE_HEIGHT * 0.18)
        key_xz(t_impulse, a)
        key_y(t_impulse, impulse_y)
        key_sy(t_impulse, launch_sy)
        squash_upright(t_impulse)

        # Up diagonal rotation
        if t_up_diag > t_impulse and t_up_diag < t_peak:
            pm.setKeyframe(SQUASH.rotateZ, v=diag, t=t_up_diag)

        # Apex
        peak = (a + b) * 0.5
        peak.y = max(a.y, b.y) + BOUNCE_HEIGHT
        key_xyz(t_peak, peak)
        key_sy(t_peak, 1.0)
        squash_upright(t_peak)

        # Down diagonal rotation
        if t_down_diag > t_peak and t_down_diag < t_pre:
            pm.setKeyframe(SQUASH.rotateZ, v=-diag, t=t_down_diag)

        # Descent
        pre_sy = 1.0 + stretch * STRETCH_PRECONTACT_MULT
        pre_center = stair_b + (RADIUS * pre_sy) + CONTACT_EPSILON

        key_xyz(t_pre, pm.datatypes.Vector(b.x, pre_center, b.z))
        key_sy(t_pre, pre_sy)
        squash_upright(t_pre)

        # Contact in B
        if t_contact is not None:
            center_b = stair_b + RADIUS + CONTACT_EPSILON
            key_xyz(t_contact, pm.datatypes.Vector(b.x, center_b, b.z))
            key_sy(t_contact, 1.0)
            squash_upright(t_contact)

            travel = (b - a).length()
            current_roll += travel * roll_normalizer
            pm.setKeyframe(ROTATE.rotateZ, v=current_roll, t=t_contact)

            frame = t_contact
        else:
            frame = t_pre

    # Tangents
    pm.keyTangent(
        MOVE.translateY,
        edit=True,
        weightedTangents=True,
        itt="spline",
        ott="spline",
    )

    for f in contact_frames:
        for t in (f, f - 1, f - 2):
            if t >= start_frame:
                pm.keyTangent(
                    MOVE.translateY,
                    edit=True,
                    time=(t, t),
                    inTangentType="linear",
                    outTangentType="linear",
                )

    for f in apex_frames:
        pm.keyTangent(
            MOVE.translateY,
            edit=True,
            time=(f, f),
            inWeight=APEX_TANGENT_WEIGHT,
            outWeight=APEX_TANGENT_WEIGHT,
        )

    pm.keyTangent(SQUASH.scaleY, edit=True, itt="auto", ott="auto")
    pm.keyTangent(SQUASH.rotate, edit=True, itt="auto", ott="auto")

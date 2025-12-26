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
    CONTACT_EPSILON,
    DIAG_ANGLE,
    JUMP_HEIGHT_SCALE,
    APEX_BACK_BLEND
)

from utils.utils import trailing_int, key_xyz, key_xz, key_y, key_sy, squash_upright, squash_contact_center

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
    BOUNCE_HEIGHT = RADIUS * BOUNCE_HEIGHT_MULT * JUMP_HEIGHT_SCALE
    SQUASH_Y_OFFSET = 0.15 * RADIUS
    POST_SQUASH_Y_OFFSET = 0.15 * RADIUS

    targets = collect_targets(ball_rig, stair_groups_in_order)
    hop_count = len(targets) - 1

    if len(targets) < 2:
        pm.warning("Not enough targets for the ball to bounce.")
        return

    needed = int(total_frames) + int(PRE_CONTACT_OFFSET)
    base = max(12, needed // hop_count)
    durations = [base] * hop_count

    for i in range(needed - base * hop_count):
        durations[i] += 1

    apex_frames = []
    contact_frames = []

    current_roll = ROTATE.rotateZ.get()
    frame = int(start_frame)

    # Precompute stairs into indexes for the jumps
    # For example: stair1 = 0, stair4 = 1 and stair7 = 2 (3 bounces per stair group)
    ordinals = []
    counts = {}

    for group_name, _pos in targets:
        counts.setdefault(group_name, 0)
        ordinals.append(counts[group_name])
        counts[group_name] += 1

    # Front hold state for the bottom left stairs
    # The ball will bounce in front of the stairs, simulating placement
    front_z_hold = None

    def visual_position(group, ordinal, pos):
        position = pm.datatypes.Vector(pos)
        if (front_z_hold is not None) and (group == "stairs_bottomleft_grp") and (ordinal in (0, 1)):
            position.z = front_z_hold
        return position

    # Starting pose (circle)
    _, initial_position = targets[0]
    initial_position = pm.datatypes.Vector(initial_position)
    key_xyz(MOVE, frame, initial_position)
    key_sy(SQUASH, frame, 1.0)
    squash_upright(SQUASH, frame)

    # Ball bounces
    for i in range(hop_count):
        group_a, a_raw = targets[i]
        group_b, b_raw = targets[i + 1]
        ordinal_a = ordinals[i]
        ordinal_b = ordinals[i + 1]

        a_raw = pm.datatypes.Vector(a_raw)
        b_raw = pm.datatypes.Vector(b_raw)

        FRAMES = int(durations[i])
        is_last = (i == hop_count - 1)

        # Remove diagonal bounce on stair sides
        is_group_transition = (group_a != group_b)
        is_straight_transition = (
            (group_a == "stairs_topleft_grp" and group_b == "stairs_bottomleft_grp") or
            (group_a == "stairs_bottomright_grp" and group_b == "stairs_topright_grp")
        )

        diag = STAIR_DIAGONAL.get(group_a, 0.0)
        if is_group_transition and is_straight_transition:
            diag = 0.0

        # Push ball forward for only the bottom left stairs
        if group_a == "stairs_topleft_grp" and ordinal_a == 2 and group_b == "stairs_bottomleft_grp" and ordinal_b == 0:
            dz = abs(b_raw.z - a_raw.z)
            front_z_hold = a_raw.z + (dz * 0.35) + (RADIUS * 0.25)

        a = visual_position(group_a, ordinal_a, a_raw)
        b = visual_position(group_b, ordinal_b, b_raw)

        # Keep the fake palcement hold through bottom left step4 (ordinal 1).
        clear_front_hold_after_hop = (group_a == "stairs_bottomleft_grp" and ordinal_a == 1)

        # Timing logic
        initial_time = int(frame)
        time_squash = initial_time + int(SQUASH_FRAME_OFFSET)
        time_recover = initial_time + int(RECOVER_FRAME_OFFSET)
        time_launch = time_recover + int(SQUASH_HOLD_FRAMES)
        time_impulse = time_launch + 1

        time_peak = initial_time + int(FRAMES * PEAK_BIAS)
        time_contact = initial_time + int(FRAMES)
        time_pre = time_contact - int(PRE_CONTACT_OFFSET)

        time_up_diag = time_peak - 2
        time_down_diag = time_peak + 2

        if is_last:
            time_contact = None

        apex_frames.append(time_peak)
        if time_contact is not None:
            contact_frames.append(time_contact)

        # Stair tops / top faces
        stair_a = a.y - RADIUS
        stair_b = b.y - RADIUS

        # Contact A
        key_xyz(
            MOVE,
            initial_time,
            pm.datatypes.Vector(
                a.x,
                stair_a + RADIUS + CONTACT_EPSILON,
                a.z,
            ),
        )
        key_sy(SQUASH, initial_time, 1.0)
        squash_upright(SQUASH, initial_time)

        # Squash A
        squash_scale = 1.0 - squash
        squash_center = (
            stair_a
            + (RADIUS * squash_scale)
            + CONTACT_EPSILON
            + SQUASH_Y_OFFSET
        )

        for t in (time_squash, time_recover):
            key_xz(MOVE, t, a)
            key_y(MOVE, t, squash_center)
            key_sy(SQUASH, t, squash_scale)
            squash_upright(SQUASH, t)

        # Launch from stair top
        center_a = stair_a + RADIUS + CONTACT_EPSILON + POST_SQUASH_Y_OFFSET
        launch_sy = 1.0 + stretch * STRETCH_RISE_MULT

        key_xz(MOVE, time_launch, a)
        key_y(MOVE, time_launch, center_a)
        key_sy(SQUASH, time_launch, launch_sy)
        squash_upright(SQUASH, time_launch)

        # Impulse upwards
        impulse_y = center_a + (BOUNCE_HEIGHT * 0.18)
        key_xz(MOVE, time_impulse, a)
        key_y(MOVE, time_impulse, impulse_y)
        key_sy(SQUASH, time_impulse, launch_sy)
        squash_upright(SQUASH, time_impulse)

        # Up diagonal rotation
        if diag != 0.0 and time_up_diag > time_impulse and time_up_diag < time_peak:
            pm.setKeyframe(SQUASH.rotateZ, v=diag, t=time_up_diag)

        # Top Apex, circle
        peak = (a + b) * 0.5
        peak.y = max(a.y, b.y) + BOUNCE_HEIGHT

        # Specific scenario
        # For the jump in bottom left stairs, from step1 to step4, move the ball to original place
        if not (group_a == "stairs_bottomleft_grp" and ordinal_a == 0 and ordinal_b == 1):
            if front_z_hold is not None:
                peak.z = (front_z_hold * (1.0 - APEX_BACK_BLEND)) + (b_raw.z * APEX_BACK_BLEND)

        key_xyz(MOVE, time_peak, peak)
        key_sy(SQUASH, time_peak, 1.0)
        squash_upright(SQUASH, time_peak)

        # Down diagonal rotation
        if diag != 0.0 and time_down_diag > time_peak and time_down_diag < time_pre:
            pm.setKeyframe(SQUASH.rotateZ, v=-diag, t=time_down_diag)

        # Descent into next stair
        pre_sy = 1.0 + stretch * STRETCH_PRECONTACT_MULT
        pre_center = squash_contact_center(stair_b, RADIUS, pre_sy)

        key_xyz(MOVE, time_pre, pm.datatypes.Vector(b.x, pre_center, b.z))
        key_sy(SQUASH, time_pre, pre_sy)
        squash_upright(SQUASH, time_pre)

        # Contact B
        if time_contact is not None:
            center_b = stair_b + RADIUS + CONTACT_EPSILON
            key_xyz(MOVE, time_contact, pm.datatypes.Vector(b.x, center_b, b.z))
            key_sy(SQUASH, time_contact, 1.0)
            squash_upright(SQUASH, time_contact)

            travel = (b - a).length()
            current_roll += travel * roll_normalizer
            pm.setKeyframe(ROTATE.rotateZ, v=current_roll, t=time_contact)

            frame = int(time_contact)
        else:
            frame = int(time_pre)

        # Release the fake placement after bottom left step4 (ordinal 1)
        if group_a == "stairs_bottomleft_grp" and ordinal_b == 1:
            front_z_hold = None

    # Tangent
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


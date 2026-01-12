import pymel.core as pm

from utils.constants import (
    APEX_BACK_BLEND,
    APEX_TANGENT_WEIGHT,
    BOUNCE_HEIGHT_MULT,
    CONTACT_EPSILON,
    DIAG_ANGLE,
    JUMP_HEIGHT_SCALE,
    PEAK_BIAS,
    PRE_CONTACT_OFFSET,
    RECOVER_FRAME_OFFSET,
    SQUASH_FRAME_OFFSET,
    SQUASH_HOLD_FRAMES,
    STRETCH_PRECONTACT_MULT,
    STRETCH_RISE_MULT,
    VEL_NORMALIZER,
    STAIR_DIAGONAL,
)
from utils.utils import (
    key_sy,
    key_xyz,
    key_xz,
    key_y,
    squash_contact_center,
    squash_upright,
    trailing_int,
)


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


def collect_steps(stair_group, excluded_stairs):
    group = pm.PyNode(stair_group)
    exclude = excluded_stairs.get(group.nodeName(), set())

    kids = pm.listRelatives(group, children=True, type="transform") or []
    steps = [
        k
        for k in kids
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


def collect_targets(ball_rig, stair_groups_in_order, excluded_stairs, start_overrides=None):
    _, _, _, radius = get_ball_controls(ball_rig)
    visit_counts = {}
    targets = []

    for group_name in stair_groups_in_order:
        visit_counts.setdefault(group_name, 0)
        steps = collect_steps(group_name, excluded_stairs)

        # Only override if it's the first visit
        if (
            start_overrides
            and visit_counts[group_name] == 0
            and group_name in start_overrides
        ):
            start_step_name = str(start_overrides[group_name]).lower()
            start_index = next(
                (i for i, step in enumerate(steps) if step.nodeName().lower() == start_step_name),
                None,
            )
            if start_index is not None:
                steps = steps[start_index:]
            else:
                pm.warning(
                    f"Start override step '{start_step_name}' not found in {group_name}."
                )

        visit_counts[group_name] += 1

        for step in steps:
            step_num = trailing_int(step.nodeName())
            if (step_num - 1) % 3 != 0:
                continue
            targets.append((group_name, step_top_center(step, radius)))

    return targets

def collect_targets_from_sequence(ball_rig, step_sequence):
    _, _, _, radius = get_ball_controls(ball_rig)
    targets = []

    for group_name, step_num in step_sequence:
        group = pm.PyNode(group_name)
        kids = pm.listRelatives(group, children=True, type="transform") or []
        step_name = f"step_{int(step_num)}"

        step = next(
            (k for k in kids if k.nodeName().lower() == step_name),
            None,
        )

        if not step:
            pm.warning(f"{step_name} not found under {group_name}, skipping.")
            continue

        pos = step_top_center(step, radius)

        # Fixes second ball entering the top right step 1
        if (
            ball_rig == "ball_rig_1"
            and group_name == "stairs_topright_grp"
            and int(step_num) == 1
        ):
            pos.z -= radius * 0.35

        targets.append((group_name, pos))

    return targets

def bounce_on_stairs(
    ball_rig,
    stair_groups_in_order,
    excluded_stairs,
    start_frame=1,
    total_frames=250,
    squash=0.38,
    stretch=0.40,
    roll_normalizer=VEL_NORMALIZER,
    start_overrides=None,
    step_sequence=None,
    jump_power=1.0,
    squash_hold_mult=1.0,
    impulse_ratio=0.35,
):
    MOVE, SQUASH, ROTATE, RADIUS = get_ball_controls(ball_rig)
    BOUNCE_HEIGHT = RADIUS * BOUNCE_HEIGHT_MULT * JUMP_HEIGHT_SCALE
    SQUASH_Y_OFFSET = 0.15 * RADIUS
    POST_SQUASH_Y_OFFSET = 0.15 * RADIUS

    if step_sequence is not None:
        targets = collect_targets_from_sequence(ball_rig, step_sequence)
    else:
        targets = collect_targets(
            ball_rig,
            stair_groups_in_order,
            excluded_stairs,
            start_overrides=start_overrides,
        )

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

    ordinals = []
    local_ordinals = []
    visit_index = []

    counts_global = {}
    counts_local_by_visit = {}
    visit_counts = {}
    last_group = None

    for group_name, _ in targets:
        counts_global.setdefault(group_name, 0)
        ordinals.append(counts_global[group_name])
        counts_global[group_name] += 1

        # Visit number increments when group changes
        if group_name != last_group:
            visit_counts[group_name] = visit_counts.get(group_name, -1) + 1
        v = visit_counts[group_name]
        visit_index.append(v)

        # Local ordinal resets per visit
        key = (group_name, v)
        counts_local_by_visit.setdefault(key, 0)
        local_ordinals.append(counts_local_by_visit[key])
        counts_local_by_visit[key] += 1

        last_group = group_name

    front_z_hold = None

    def visual_position(group, ordinal_for_visual, pos):
        position = pm.datatypes.Vector(pos)
        if (
            (front_z_hold is not None)
            and (group == "stairs_bottomleft_grp")
            and (ordinal_for_visual in (0, 1))
        ):
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

        local_a = local_ordinals[i]
        local_b = local_ordinals[i + 1]

        a_raw = pm.datatypes.Vector(a_raw)
        b_raw = pm.datatypes.Vector(b_raw)

        FRAMES = int(durations[i])
        is_last = i == hop_count - 1

        # Remove diagonal bounce on stair sides
        is_group_transition = group_a != group_b
        is_straight_transition = (
            group_a == "stairs_topleft_grp" and group_b == "stairs_bottomleft_grp"
        ) or (group_a == "stairs_bottomright_grp" and group_b == "stairs_topright_grp")

        diag = STAIR_DIAGONAL.get(group_a, 0.0)
        if is_group_transition and is_straight_transition:
            diag = 0.0

        # Push ball forward for only the bottom left stairs
        # Use local ordinals so it works on later visits too
        if (
            group_a == "stairs_topleft_grp"
            and local_a == 2
            and group_b == "stairs_bottomleft_grp"
            and local_b == 0
        ):
            dz = abs(b_raw.z - a_raw.z)
            front_z_hold = a_raw.z + (dz * 0.35) + (RADIUS * 0.25)

        # Make sure we compute placement on custom step sequence
        if (
            front_z_hold is None
            and group_b == "stairs_bottomleft_grp"
            and local_b == 0
        ):
            dz = abs(b_raw.z - a_raw.z)
            front_z_hold = a_raw.z + (dz * 0.35) + (RADIUS * 0.25)

        # For the bottom-left fake placement
        a_ord_for_visual = local_a if group_a == "stairs_bottomleft_grp" else ordinal_a
        b_ord_for_visual = local_b if group_b == "stairs_bottomleft_grp" else ordinal_b

        a = visual_position(group_a, a_ord_for_visual, a_raw)
        b = visual_position(group_b, b_ord_for_visual, b_raw)

        # Timing logic
        initial_time = int(frame)
        time_squash = initial_time + int(SQUASH_FRAME_OFFSET)
        time_recover = initial_time + int(RECOVER_FRAME_OFFSET)

        hold = int(round(SQUASH_HOLD_FRAMES * float(squash_hold_mult)))
        time_launch = time_recover + hold
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
        squash_depth_mult = 1.0 + (float(squash_hold_mult) - 1.0) * 0.5
        squash_scale = 1.0 - (squash * squash_depth_mult)

        # Safety logic to avoid negative or zero values
        squash_scale = max(0.05, squash_scale)

        squash_center = (
            stair_a + (RADIUS * squash_scale) + CONTACT_EPSILON + SQUASH_Y_OFFSET
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

        # Target apex height for this hop
        peak_y = max(a.y, b.y) + (BOUNCE_HEIGHT * float(jump_power))

        # Impulse upwards (based on the target apex height)
        impulse_y = center_a + ((peak_y - center_a) * float(impulse_ratio))
        key_xz(MOVE, time_impulse, a)
        key_y(MOVE, time_impulse, impulse_y)
        key_sy(SQUASH, time_impulse, launch_sy)
        squash_upright(SQUASH, time_impulse)

        # Up diagonal rotation
        if diag != 0.0 and time_up_diag > time_impulse and time_up_diag < time_peak:
            pm.setKeyframe(SQUASH.rotateZ, v=diag, t=time_up_diag)

        # Top Apex, circle
        peak = (a + b) * 0.5
        peak.y = peak_y

        if not (
            group_a == "stairs_bottomleft_grp" and local_a == 0 and local_b == 1
        ):
            if front_z_hold is not None:
                peak.z = (front_z_hold * (1.0 - APEX_BACK_BLEND)) + (
                    b_raw.z * APEX_BACK_BLEND
                )

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

        if group_a == "stairs_bottomleft_grp" and local_b == 1:
            front_z_hold = None

    # Tangent configuration
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
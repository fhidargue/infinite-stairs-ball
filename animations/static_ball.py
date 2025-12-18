import random
import pymel.core as pm


def bounce(ball_rig, ball_type="tennis", move_forward=False):
    POSITION_FLOOR = 1
    INITIAL_FRAME = 1
    VEL_NORMALIZER = 60

    ball_hierarchy = [
        "move_anim",
        "squash_stretch_axis_anim",
        "cancel_rotations_grp",
        "rotate_anim",
        "ball_geo",
    ]

    children = pm.listRelatives(ball_rig, allDescendents=True, type="transform")
    names = [c.nodeName() for c in children]
    ball_geo = pm.PyNode(f"{ball_rig}|ball_geo")
    bbox = ball_geo.getBoundingBox()

    for node in ball_hierarchy:
        if node not in names:
            pm.warning(f"Expected node '{node}' not found under {ball_rig}")
            return

    MOVE_CTRL = pm.PyNode(f"{ball_rig}|move_anim")
    SQUASH_CTRL = pm.PyNode(f"{ball_rig}|move_anim|squash_stretch_axis_anim")
    ROTATE_CTRL = pm.PyNode(f"{ball_rig}|move_anim|squash_stretch_axis_anim|cancel_rotations_grp|rotate_anim")
    RADIUS = (bbox.max().y - bbox.min().y) / 2.0

    ball_properties = {
        "tennis": {
            "position_y": 12,
            "ground_friction": 0.20,
            "air_friction": 0.08,
            "frames_to_fall": 10,
            "squash": 0.2,
        },
        "beach": {"position_y": 12, "ground_friction": 0.15, "air_friction": 0.05, "frames_to_fall": 10, "squash": 0.5},
        "bowling": {
            "position_y": 12,
            "ground_friction": 0.7,
            "air_friction": 0.3,
            "frames_to_fall": 10,
            "squash": 0.15,
        },
    }

    # Values from types
    props = ball_properties.get(ball_type.lower(), ball_properties["tennis"])
    initial_height = props["position_y"]
    position_y = initial_height
    ground_friction = props["ground_friction"]
    air_friction = props["air_friction"]
    frames_to_fall = props["frames_to_fall"]
    squash_factor = props["squash"]

    wait_y = 0.1
    positions = [position_y, POSITION_FLOOR]

    while position_y > wait_y:
        position_y *= 1 - ground_friction

        if position_y < POSITION_FLOOR + 0.05:  # Check distances
            break

        positions.append(position_y)
        positions.append(POSITION_FLOOR)

    # Timing calculations
    times = [INITIAL_FRAME]
    time_interval = frames_to_fall
    current_time = INITIAL_FRAME

    for i in range(1, len(positions)):
        current_time += time_interval
        times.append(round(current_time))

        if i % 2 == 0:
            time_interval *= 1 - air_friction

    # Initialize movement parameters
    x, z = MOVE_CTRL.translateX.get(), MOVE_CTRL.translateZ.get()

    for i, (t, p) in enumerate(zip(times, positions)):
        if move_forward:
            total_bounces = len(positions)
            step_x = (total_bounces - i) * 0.5  # Decrease the distance each bounce
            x += step_x
            z += random.uniform(-0.2, 0.2)  # Random Z movement

        MOVE_CTRL.translateY.set(p)
        MOVE_CTRL.translateX.set(x)
        MOVE_CTRL.translateZ.set(z)

        pm.setKeyframe(MOVE_CTRL.translateY, t=t)
        pm.setKeyframe(MOVE_CTRL.translateX, t=t)
        pm.setKeyframe(MOVE_CTRL.translateZ, t=t)

        if p == POSITION_FLOOR:
            bounce_factor = 1 - (i / len(positions)) * 0.5
            current_squash = squash_factor * bounce_factor

            scale_y = 1.0 - current_squash

            # Convert scale squash to world units
            squash_amount_world = (1.0 - scale_y) * RADIUS

            # Move ball DOWN so the bottom stays on floor
            corrected_y = POSITION_FLOOR - squash_amount_world

            SQUASH_CTRL.scaleY.set(scale_y)
            pm.setKeyframe(SQUASH_CTRL.scaleY, t=t)
            MOVE_CTRL.translateY.set(corrected_y)
            pm.setKeyframe(MOVE_CTRL.translateY, t=t)
        else:
            # Stretch the ball reducing power
            height_norm = max(0.0, min(1.0, (p - POSITION_FLOOR) / (initial_height - POSITION_FLOOR)))
            bounce_factor = 1 - (i / len(positions)) * 0.5
            current_squash = squash_factor * bounce_factor

            scale_y = 1.0 + height_norm * current_squash

            pm.setKeyframe(SQUASH_CTRL.scaleY, v=scale_y, t=t)

        # Adds rotation per bounce
        if i > 0:
            prev_height = positions[i - 1]
            velocity = abs(prev_height - p)
        else:
            velocity = 0

        # Normalize velocity
        rot_amount = velocity * VEL_NORMALIZER

        # Add current rotation
        current_rot = ROTATE_CTRL.rotateZ.get()
        pm.setKeyframe(ROTATE_CTRL.rotateZ, v=current_rot + rot_amount, t=t)

    # Clean tangents
    pm.keyTangent(MOVE_CTRL.translateY, edit=True, weightedTangents=True, itt="spline", ott="spline")

    # Floor should be linear
    floor_keys = [t for t, y in zip(times, positions) if y == POSITION_FLOOR]
    for fk in floor_keys:
        pm.keyTangent(
            MOVE_CTRL.translateY,
            edit=True,
            time=(fk, fk),
            inTangentType="linear",
            outTangentType="linear",
            inAngle=0,
            outAngle=0,
            inWeight=0,
            outWeight=0,
        )

    # Peaks smooth
    peak_keys = [t for t, y in zip(times, positions) if y != POSITION_FLOOR]
    for pk in peak_keys:
        pm.keyTangent(
            MOVE_CTRL.translateY,
            edit=True,
            time=(pk, pk),
            inTangentType="auto",
            outTangentType="auto",
            inWeight=5,
            outWeight=5,
        )

    # Reset the squash scale on final frame
    final_frame = times[-1] + 1
    SQUASH_CTRL.scaleY.set(1.0)
    pm.setKeyframe(SQUASH_CTRL.scaleY, t=final_frame)
    MOVE_CTRL.translateY.set(1.0)
    pm.setKeyframe(MOVE_CTRL.translateY, t=final_frame)

bounce(
    ball_rig="ball_rig",
    ball_type="tennis",
    move_forward=False
)
import math

import pymel.core as pm


def create_trapezoid(name, top_width, bottom_width, depth, thickness, center=(0, 0, 0), rotation=0):
    cx, cy, cz = center
    half_top = top_width * 0.5
    half_bottom = bottom_width * 0.5
    half_depth = depth * 0.5

    vertices = [
        (-half_top, half_depth, 0),
        (half_top, half_depth, 0),
        (half_bottom, -half_depth, 0),
        (-half_bottom, -half_depth, 0),
    ]

    vertices = [(cx + x, cy + y, cz + z) for (x, y, z) in vertices]

    # Create facet and convert to PyNode
    result = pm.polyCreateFacet(p=vertices, name=f"{name}_face")
    transform = pm.PyNode(result[0])
    shape = transform.getShape()
    pm.polyExtrudeFacet(shape.f[0], ltz=thickness)

    group = pm.group(transform, name=f"{name}_group")
    group.rotateY.set(rotation)

    return group


def create_step(name, sx, sy, sz, position):
    step = pm.polyCube(w=sx, h=sy, d=sz, name=name)[0]
    step.translate.set(position[0], position[1] + sy / 2.0, position[2])

    return step


def create_stair_sequence(
    name, start_position, direction, step_size=(1, 0.25, 0.8), step_count=3, gap=0.02, big_scale=1.5
):
    sx, sy, sz = step_size
    dx, dy, dz = direction

    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < 1e-6:
        raise ValueError("Direction vector is zero.")

    ndx, ndy, ndz = dx / length, dy / length, dz / length

    current_position = list(start_position)
    step_forward = sz + gap
    items = []

    # Small steps
    for i in range(step_count):
        step = create_step(f"{name}_step{i + 1}", sx, sy, sz, current_position)
        items.append(step)

        current_position[0] += ndx * step_forward
        current_position[1] += ndy * step_forward + sy * 0.4
        current_position[2] += ndz * step_forward

    # Connector step
    connector = create_step(f"{name}_connector", sx * big_scale, sy * big_scale, sz * big_scale, current_position)
    items.append(connector)

    end_position = (current_position[0], current_position[1] + (sy * big_scale) / 2.0, current_position[2])

    group = pm.group(items, name=f"{name}_group")
    return group, end_position


def make_hex_stairs():
    BASE_DEPTH = 2.0
    THICKNESS = 0.3

    pm.newFile(f=1)
    master = pm.group(em=True, name="hex_infinite_stairs")

    # Base bottom
    base_bottom = create_trapezoid(
        name="base_bottom_1", top_width=4, bottom_width=6, depth=BASE_DEPTH, thickness=THICKNESS, center=(0, 0, 0)
    )
    base_bottom.setParent(master)

    # Base top
    base_top = create_trapezoid(
        name="base_top_1", top_width=4, bottom_width=6, depth=BASE_DEPTH, thickness=THICKNESS, center=(0, 0.6, 6.5)
    )
    base_top.rotateY.set(0)
    base_top.setParent(master)

    # Right stairs
    right_start = (3.2, 0, 0.6)
    target_top = (0, 0.6, 6.5)
    direction1 = (target_top[0] - right_start[0], target_top[1] - right_start[1], target_top[2] - right_start[2])

    right_group, right_end = create_stair_sequence("right_stairs", right_start, direction1, step_size=(1, 0.25, 0.8))
    right_group.setParent(master)

    top_right_start = ((right_end[0] * 0.9), right_end[1], (right_end[2] * 0.9))
    direction2 = (
        target_top[0] - top_right_start[0],
        target_top[1] - top_right_start[1],
        target_top[2] - top_right_start[2],
    )

    top_right_group, top_right_end = create_stair_sequence(
        "top_right_stairs", top_right_start, direction2, step_size=(0.95, 0.23, 0.75)
    )
    top_right_group.setParent(master)

    # Left stairs
    left_start = (-3.2, 0.6, 6.2)
    left_target = (-3.4, 0.0, 1.5)

    direction3 = (left_target[0] - left_start[0], left_target[1] - left_start[1], left_target[2] - left_start[2])

    left_group, left_end = create_stair_sequence("left_stairs", left_start, direction3)
    left_group.setParent(master)

    second_base = create_trapezoid(
        "base_bottom_2", top_width=4, bottom_width=6, depth=BASE_DEPTH, thickness=THICKNESS, center=(0, 0, -8)
    )
    second_base.setParent(master)

    # Back base bottom
    connector_direction = (0 - left_end[0], 0 - left_end[1], -8 - left_end[2])

    back_start = (
        left_end[0] + connector_direction[0] * 0.15,
        left_end[1] + connector_direction[1] * 0.15,
        left_end[2] + connector_direction[2] * 0.15,
    )

    back_group, back_end = create_stair_sequence(
        "back_connector", back_start, connector_direction, step_size=(0.9, 0.22, 0.75), big_scale=1.6
    )
    back_group.setParent(master)

    print("\n✨ PyMEL hex-stair structure created.")
    return master

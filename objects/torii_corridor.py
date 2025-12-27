import pymel.core as pm
import pymel.core.datatypes as dt

from utils.torii_constants import (
    BASE_Y,
    CORRIDOR_COUNT,
    GATE_EVERY_NUM,
    GATE_SCALE_DECAY,
    GATE_SPACING,
    HEIGHT_PLACEMENT,
    INITIAL_GATE_NAME,
    MAX_NUM_STAIRS,
    MIN_STAIR_HEIGHT,
    STAIR_FORWARD_POSITION,
    STAIR_ROTATION_X,
    STAIR_SCALE,
    STAIR_SCALE_DECAY,
)


def build_torii_sequence(
    base_gate_name=INITIAL_GATE_NAME,
    corridor_gate_count=CORRIDOR_COUNT,
    gate_spacing=GATE_SPACING,
    scale_decay=GATE_SCALE_DECAY,
    base_y=BASE_Y,
    height_reference=HEIGHT_PLACEMENT,
    stair_forward=STAIR_FORWARD_POSITION,
    stair_scale=STAIR_SCALE,
    stair_rotation_x=STAIR_ROTATION_X,
    stair_scale_decay=STAIR_SCALE_DECAY,
    min_stair_height=MIN_STAIR_HEIGHT,
    max_stairs=MAX_NUM_STAIRS,
    torii_every_num=GATE_EVERY_NUM,
):
    if not pm.objExists(base_gate_name):
        pm.error(f"{base_gate_name} not found in scene")

    base_gate = pm.PyNode(base_gate_name)

    # Clean previous objects
    if pm.objExists("torii_corridor_grp"):
        pm.delete("torii_corridor_grp")

    group = pm.group(em=True, name="torii_corridor_grp")
    stairs_group = pm.group(em=True, name="stairs_grp", parent=group)
    stair_torii_group = pm.group(em=True, name="stair_torii_grp", parent=group)

    # Base data
    base_position = dt.Vector(base_gate.getTranslation(space="world"))
    base_rotation = base_gate.getRotation(space="world")
    base_scale = dt.Vector(base_gate.getScale())

    backward = dt.Vector(0, 0, -1)

    base_gate.setTranslation(
        dt.Vector(base_position.x, base_y, base_position.z),
        space="world",
    )

    current_pos = dt.Vector(base_position.x, base_y, base_position.z)
    current_scale = dt.Vector(base_scale)

    last_gate = None
    last_gate_scale = None

    # Torii corridor
    for i in range(1, corridor_gate_count + 1):
        current_pos += backward * gate_spacing
        current_scale *= scale_decay

        scale_factor = current_scale.y / base_scale.y
        lift = (1.0 - scale_factor) * height_reference
        target_y = base_y + lift

        gate = pm.duplicate(base_gate, name=f"torii_corridor_{i}")[0]
        gate.setParent(group)
        gate.setRotation(base_rotation, space="world")
        gate.setScale(current_scale)
        gate.setTranslation(
            dt.Vector(current_pos.x, target_y, current_pos.z),
            space="world",
        )

        last_gate = gate
        last_gate_scale = dt.Vector(current_scale)

    if not last_gate:
        return group

    # Initial stair, helps for future placement reference
    gate_pos = dt.Vector(last_gate.getTranslation(space="world"))
    scale_factor = last_gate_scale.y / base_scale.y

    stair_back_offset = gate_spacing * scale_factor * 3.0
    stair_down_offset = height_reference * (1.0 - scale_factor) * 0.25

    current_stair_pos = dt.Vector(
        gate_pos.x,
        gate_pos.y - stair_down_offset,
        gate_pos.z + stair_back_offset,
    )

    stair0_scale_vec = dt.Vector(stair_scale)
    current_stair_scale = dt.Vector(stair0_scale_vec)
    torii_scale_start = last_gate_scale * scale_decay

    for i in range(max_stairs):
        stair = pm.polyCube(name=f"stair_{i}")[0]
        stair.setParent(stairs_group)
        stair.setScale(current_stair_scale)
        stair.setRotation(dt.Vector(stair_rotation_x, 0, 0), space="world")
        stair.setTranslation(current_stair_pos, space="world")

        stair_bb = pm.exactWorldBoundingBox(stair)
        stair_top_y = stair_bb[4]

        # Torii gates on stairs
        if i % torii_every_num == 0:
            stair_center_x = (stair_bb[0] + stair_bb[3]) * 0.5
            stair_center_z = (stair_bb[2] + stair_bb[5]) * 0.5

            depth_factor = current_stair_scale.y / stair0_scale_vec.y
            torii_scale = torii_scale_start * depth_factor

            torii = pm.duplicate(base_gate, name=f"torii_stair_{i}")[0]
            torii.setParent(stair_torii_group)
            torii.setRotation(base_rotation, space="world")
            torii.setScale(torii_scale)

            # Provisional placement
            torii.setTranslation(
                dt.Vector(stair_center_x, stair_top_y, stair_center_z),
                space="world",
            )

            # Border box correction
            top_border = pm.exactWorldBoundingBox(torii)
            correction = dt.Vector(
                stair_center_x - (top_border[0] + top_border[3]) * 0.5,
                stair_top_y - top_border[1],
                stair_center_z - (top_border[2] + top_border[5]) * 0.5,
            )

            torii.setTranslation(
                torii.getTranslation(space="world") + correction,
                space="world",
            )

        # Next stair
        next_scale = current_stair_scale * stair_scale_decay
        if next_scale.y < min_stair_height:
            break

        depth_factor = current_stair_scale.y / stair0_scale_vec.y
        if depth_factor < 0.01:
            break

        next_pos = dt.Vector(current_stair_pos)
        next_pos += backward * stair_forward * depth_factor
        next_pos.y = stair_top_y + (next_scale.y * 0.5)

        current_stair_pos = next_pos
        current_stair_scale = next_scale

    return group

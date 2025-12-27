import pymel.core as pm
import pymel.core.datatypes as dt

from utils.torii_constants import (
    INITIAL_GATE_NAME,
    CORRIDOR_COUNT,
    GATE_SCALE_DECAY,
    GATE_SPACING,
    GATE_EVERY_NUM,
    BASE_Y,
    HEIGHT_PLACEMENT,
    STAIR_FORWARD_POSITION,
    STAIR_ROTATION_X,
    STAIR_SCALE,
    STAIR_SCALE_DECAY,
    MIN_STAIR_HEIGHT,
    MAX_NUM_STAIRS,
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

    # Cleanup existing objects
    if pm.objExists("torii_corridor_grp"):
        pm.delete("torii_corridor_grp")

    # Object groups
    grp = pm.group(em=True, name="torii_corridor_grp")
    stairs_grp = pm.group(em=True, name="stairs_grp", parent=grp)
    stair_torii_grp = pm.group(em=True, name="stair_torii_grp", parent=grp)

    # Initial data
    base_position = dt.Vector(base_gate.getTranslation(space="world"))
    base_rotation = base_gate.getRotation(space="world")
    base_scale = dt.Vector(base_gate.getScale())
    base_gate.setTranslation(dt.Vector(base_position.x, base_y, base_position.z), space="world")
    backward = dt.Vector(0, 0, -1)

    current_position = dt.Vector(base_position.x, base_y, base_position.z)
    current_scale = dt.Vector(base_scale)

    last_gate = None
    last_gate_scale = None

    # Torii corridor
    for i in range(1, corridor_gate_count + 1):
        current_position += backward * gate_spacing
        current_scale *= scale_decay

        scale_factor = current_scale.y / base_scale.y
        lift = (1.0 - scale_factor) * height_reference
        target_y = base_y + lift

        gate = pm.duplicate(base_gate, name=f"torii_corridor_{i}")[0]
        gate.setParent(grp)
        gate.setRotation(base_rotation, space="world")
        gate.setScale(current_scale)
        gate.setTranslation(dt.Vector(current_position.x, target_y, current_position.z), space="world")

        last_gate = gate
        last_gate_scale = dt.Vector(current_scale)

    if not last_gate:
        return grp

    # First stair creation
    gate_position = dt.Vector(last_gate.getTranslation(space="world"))
    scale_factor = last_gate_scale.y / base_scale.y

    stair_back_offset = gate_spacing * scale_factor * 3.0
    stair_down_offset = height_reference * (1.0 - scale_factor) * 0.25

    current_stair_pos = dt.Vector(
        gate_position.x,
        gate_position.y - stair_down_offset,
        gate_position.z + stair_back_offset,
    )

    stair0_scale_vec = dt.Vector(stair_scale)
    current_stair_scale = dt.Vector(stair0_scale_vec)

    # Torii gate scale continues the last one of the corridor
    torii_scale_start = last_gate_scale * scale_decay

    # Stairs loop
    for i in range(max_stairs):
        stair = pm.polyCube(name=f"stair_{i}")[0]
        stair.setParent(stairs_grp)
        stair.setScale(current_stair_scale)
        stair.setRotation(dt.Vector(stair_rotation_x, 0, 0), space="world")
        stair.setTranslation(current_stair_pos, space="world")

        # Top Y for stacking next stair
        stair_bb = pm.exactWorldBoundingBox(stair)
        stair_top_y = stair_bb[4]

        # Torii gates on stairs
        if (i % torii_every_num) == 0:
            stair_center_x = (stair_bb[0] + stair_bb[3]) * 0.5
            stair_center_z = (stair_bb[2] + stair_bb[5]) * 0.5

            # Scale torii based on stair depth
            stair_depth_ratio = (current_stair_scale.y / stair0_scale_vec.y)
            torii_scale = torii_scale_start * stair_depth_ratio

            torii = pm.duplicate(base_gate, name=f"torii_stair_{i}")[0]
            torii.setParent(stair_torii_grp)
            torii.setRotation(base_rotation, space="world")
            torii.setScale(torii_scale)

            # Rough placement
            torii.setTranslation(
                dt.Vector(stair_center_x, stair_top_y, stair_center_z),
                space="world",
            )

            # Precise pivot correction
            tb = pm.exactWorldBoundingBox(torii)
            torii_center_x = (tb[0] + tb[3]) * 0.5
            torii_center_z = (tb[2] + tb[5]) * 0.5
            torii_bottom_y = tb[1]

            correction = dt.Vector(
                stair_center_x - torii_center_x,
                stair_top_y - torii_bottom_y,
                stair_center_z - torii_center_z,
            )

            torii.setTranslation(
                torii.getTranslation(space="world") + correction,
                space="world",
            )

        # Prepare data for next stair
        next_scale = current_stair_scale * stair_scale_decay
        if next_scale.y < min_stair_height:
            break

        next_pos = dt.Vector(current_stair_pos)
        next_pos += backward * stair_forward * stair_scale_decay
        next_pos.y = stair_top_y + (next_scale.y * 0.5)

        current_stair_pos = next_pos
        current_stair_scale = next_scale

    return grp

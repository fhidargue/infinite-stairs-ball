import pymel.core as pm
import pymel.core.datatypes as dt


def build_torii_sequence(
    base_gate_name="torii_gate_0",
    corridor_gate_count=5,
    gate_spacing=18.0,
    scale_decay=0.88,
    base_y=8.0,
    y_step=1.0,            
):
    if not pm.objExists(base_gate_name):
        pm.error(f"{base_gate_name} not found in scene")

    base_gate = pm.PyNode(base_gate_name)

    grp = pm.group(em=True, name="torii_corridor_grp")

    base_pos = dt.Vector(base_gate.getTranslation(space="world"))
    base_rot = base_gate.getRotation(space="world")
    base_scale = dt.Vector(base_gate.getScale())

    backward = dt.Vector(0, 0, -1)

    # Start from torii_gate_0
    current_pos = dt.Vector(base_pos)
    current_scale = dt.Vector(base_scale)

    # Make sure torii_gate_0 is exactly base_y
    base_gate.setTranslation(dt.Vector(base_pos.x, base_y, base_pos.z), space="world")

    for gate_index in range(1, corridor_gate_count + 1):
        # Move backward consistently
        current_pos += backward * gate_spacing

        # Set exact Y for this gate index
        target_y = base_y + (y_step * gate_index)

        # Shrink scale
        current_scale *= scale_decay

        gate = pm.duplicate(base_gate, name=f"torii_corridor_{gate_index}")[0]
        gate.setParent(grp)

        gate.setTranslation(dt.Vector(current_pos.x, target_y, current_pos.z), space="world")
        gate.setRotation(base_rot, space="world")
        gate.setScale(current_scale)

    return grp

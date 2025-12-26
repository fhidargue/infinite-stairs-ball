import pymel.core as pm
import math

def create_stairs_with_base():
    step_count = 6
    run = 1.0
    rise = 1.0
    depth = 1.0
    base_height = 0.4

    group = pm.group(empty=True, name="stair_grp")

    steps = []

    # Create steps
    for i in range(step_count):
        step = pm.polyCube(w=run, h=rise, d=depth, name=f"step_{i+1}")[0]
        step.t.set((i * run, -i * rise, 0))
        step.setParent(group)
        steps.append(step)

    # Create base   
    diag = math.sqrt((run * step_count)**2 + (rise * step_count)**2)
    angle = -math.degrees(math.atan(rise / run))

    base = pm.polyCube(
        w=diag,
        h=base_height,
        d=depth * 1.1,
        name="base"
    )[0]

    base.rz.set(angle)
    vertical_offset = (rise / 2.0) + (base_height / 2.0)

    # Find diagonal center of stairs
    mid_x = (run * (step_count - 1)) / 2.0
    mid_y = -(rise * (step_count - 1)) / 2.0

    base.t.set((mid_x, mid_y - vertical_offset, 0))
    base.setParent(group)

    pm.makeIdentity(group, apply=True, t=1, r=1, s=1)

import math
import pymel.core as pm


def create_radial_brick_ring(
    count=12,
    inner_radius=3.5,
    outer_radius=4.5,
    height=0.4,
    gap_angle_deg=1.2,
    name_prefix="brick",
):
    angle_step = 360.0 / count
    half_gap = gap_angle_deg * 0.5
    bricks = []

    for index in range(count):
        face_nodes = []

        start_angle_rad = math.radians(index * angle_step + half_gap)
        end_angle_rad = math.radians((index + 1) * angle_step - half_gap)

        # Bottom points
        inner_start = pm.dt.Vector(
            math.cos(start_angle_rad) * inner_radius, 0.0,
            math.sin(start_angle_rad) * inner_radius
        )
        inner_end = pm.dt.Vector(
            math.cos(end_angle_rad) * inner_radius, 0.0,
            math.sin(end_angle_rad) * inner_radius
        )
        outer_end = pm.dt.Vector(
            math.cos(end_angle_rad) * outer_radius, 0.0,
            math.sin(end_angle_rad) * outer_radius
        )
        outer_start = pm.dt.Vector(
            math.cos(start_angle_rad) * outer_radius, 0.0,
            math.sin(start_angle_rad) * outer_radius
        )

        # Top points
        inner_start_top = inner_start + pm.dt.Vector(0, height, 0)
        inner_end_top   = inner_end   + pm.dt.Vector(0, height, 0)
        outer_end_top   = outer_end   + pm.dt.Vector(0, height, 0)
        outer_start_top = outer_start + pm.dt.Vector(0, height, 0)

        # Bottom face
        face_nodes.append(
            pm.polyCreateFacet(
                p=[inner_start, outer_start, outer_end, inner_end]
            )[0]
        )

        # Top face
        face_nodes.append(
            pm.polyCreateFacet(
                p=[inner_start_top, inner_end_top, outer_end_top, outer_start_top]
            )[0]
        )

        # Outer curved wall
        face_nodes.append(
            pm.polyCreateFacet(
                p=[outer_start, outer_start_top, outer_end_top, outer_end]
            )[0]
        )

        # Inner curved wall
        face_nodes.append(
            pm.polyCreateFacet(
                p=[inner_start, inner_end, inner_end_top, inner_start_top]
            )[0]
        )

        # Side wall A
        face_nodes.append(
            pm.polyCreateFacet(
                p=[inner_start, inner_start_top, outer_start_top, outer_start]
            )[0]
        )

        # Side wall B
        face_nodes.append(
            pm.polyCreateFacet(
                p=[inner_end, outer_end, outer_end_top, inner_end_top]
            )[0]
        )

        brick_mesh = pm.polyUnite(
            face_nodes, ch=False, name=f"{name_prefix}_{index}"
        )[0]

        pm.delete(brick_mesh, constructionHistory=True)
        bricks.append(brick_mesh)

    pm.group(bricks, name=f"{name_prefix}_ring_grp")
    return bricks

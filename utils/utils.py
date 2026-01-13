import pymel.core as pm

from utils.constants import CONTACT_EPSILON, DIGIT_REGEX


def trailing_int(name, default=0):
    """
    Extracts the trailing integer from a given name string.

    Args:
        name (str): The string to extract the integer from.
        default (int): The default value to return if no integer is found.
    """
    m = DIGIT_REGEX.search(name)
    return int(m.group(1)) if m else default


def key_xyz(control, time, vector):
    """
    Sets keyframes for the X, Y, and Z translation of a control at a given time.

    Args:
        control (pm.PyNode): The control node to set keyframes on.
        time (int): The time/frame to set the keyframes.
        vector (tuple or list): The (x, y, z) values to set for the translation.
    """
    vec3 = pm.datatypes.Vector(vector)
    pm.setKeyframe(control.translateX, v=vec3.x, t=time)
    pm.setKeyframe(control.translateY, v=vec3.y, t=time)
    pm.setKeyframe(control.translateZ, v=vec3.z, t=time)


def key_xz(control, time, vector):
    """
    Sets keyframes for the X and Z translation of a control at a given time.

    Args:
        control (pm.PyNode): The control node to set keyframes on.
        time (int): The time/frame to set the keyframes.
        vector (tuple or list): The (x, z) values to set for the translation
    """
    vec3 = pm.datatypes.Vector(vector)
    pm.setKeyframe(control.translateX, v=vec3.x, t=time)
    pm.setKeyframe(control.translateZ, v=vec3.z, t=time)


def key_y(control, time, y):
    """
    Sets a keyframe for the Y translation of a control at a given time.

    Args:
        control (pm.PyNode): The control node to set the keyframe on.
        time (int): The time/frame to set the keyframe.
        y (float): The Y value to set for the translation.
    """
    pm.setKeyframe(control.translateY, v=y, t=time)


def key_sy(control, time, scale_y):
    """
    Sets a keyframe for the Y scale of a control at a given time.

    Args:
        control (pm.PyNode): The control node to set the keyframe on.
        time (int): The time/frame to set the keyframe.
        scale_y (float): The Y scale value to set.
    """
    pm.setKeyframe(control.scaleY, v=scale_y, t=time)


def squash_upright(control, time):
    """
    Sets keyframes to make the control upright (no rotation) at a given time.

    Args:
        control (pm.PyNode): The control node to set the keyframes on.
        time (int): The time/frame to set the keyframes.
    """
    pm.setKeyframe(control.rotateX, v=0.0, t=time)
    pm.setKeyframe(control.rotateY, v=0.0, t=time)
    pm.setKeyframe(control.rotateZ, v=0.0, t=time)


def squash_contact_center(stair_y, radius, scale_y):
    """
    Sets the Y position for the ball's contact center based on stair position and ball scale.

    Args:
        stair_y (float): The Y position of the stair.
        radius (float): The radius of the ball.
        scale_y (float): The Y scale of the ball.
    """
    return stair_y + (radius * scale_y) + CONTACT_EPSILON

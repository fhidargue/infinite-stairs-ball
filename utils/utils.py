import pymel.core as pm
from utils.constants import DIGIT_REGEX, CONTACT_EPSILON

def trailing_int(name, default=0):
    m = DIGIT_REGEX.search(name)
    return int(m.group(1)) if m else default

def key_xyz(control, time, vector):
    vec3 = pm.datatypes.Vector(vector)
    pm.setKeyframe(control.translateX, v=vec3.x, t=time)
    pm.setKeyframe(control.translateY, v=vec3.y, t=time)
    pm.setKeyframe(control.translateZ, v=vec3.z, t=time)

def key_xz(control, time, vector):
    vec3 = pm.datatypes.Vector(vector)
    pm.setKeyframe(control.translateX, v=vec3.x, t=time)
    pm.setKeyframe(control.translateZ, v=vec3.z, t=time)

def key_y(control, time, y):
    pm.setKeyframe(control.translateY, v=y, t=time)

def key_sy(control, time, scale_y):
    pm.setKeyframe(control.scaleY, v=scale_y, t=time)

def squash_upright(control, time):
    pm.setKeyframe(control.rotateX, v=0.0, t=time)
    pm.setKeyframe(control.rotateY, v=0.0, t=time)
    pm.setKeyframe(control.rotateZ, v=0.0, t=time)

def squash_contact_center(stair_y, radius, scale_y):
    return stair_y + (radius * scale_y) + CONTACT_EPSILON

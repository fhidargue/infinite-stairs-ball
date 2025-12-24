import re

# Hang time and arc shape
PEAK_BIAS = 0.65         
BOUNCE_HEIGHT_MULT = 6

# Frames before contact to start stretch
PRE_CONTACT_OFFSET = 1

# Squash timing
SQUASH_FRAME_OFFSET  = 1
RECOVER_FRAME_OFFSET = 2
SQUASH_HOLD_FRAMES   = 2

# Stretch amounts
STRETCH_AT_PEAK = 0.0    
STRETCH_PRECONTACT_MULT = 1.0
STRETCH_RISE_MULT = 0.85

# Tangent weights
APEX_TANGENT_WEIGHT = 14

# Rotation
VEL_NORMALIZER = 0.08 

# Regex
DIGIT_REGEX = re.compile(r"(\d+)$")
from utils.constants import DIGIT_REGEX

def trailing_int(name, default=0):
    m = DIGIT_REGEX.search(name)
    return int(m.group(1)) if m else default
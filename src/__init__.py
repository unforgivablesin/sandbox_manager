import os

DIRECTORY = os.environ["HOME"] + "/.sandbox_manager"

APP_DIRECTORY = DIRECTORY + "/appdata"
CONFIG_DIRECTORY = DIRECTORY + "/config"
SECCOMP_DIRECTORY = DIRECTORY + "/seccomp"

try:
    os.mkdir(DIRECTORY)

except Exception:
    pass

try:
    os.mkdir(APP_DIRECTORY)
except Exception:
    pass

try:
    os.mkdir(CONFIG_DIRECTORY)
except Exception:
    pass

try:
    os.mkdir(SECCOMP_DIRECTORY)
except Exception:
    pass

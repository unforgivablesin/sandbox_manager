import os

HOME_DIR = os.path.expanduser("~")
DIRECTORY = os.path.join(HOME_DIR, ".sandbox_manager")

APP_DIRECTORY = os.path.join(DIRECTORY, "appdata")
CONFIG_DIRECTORY = os.path.join(DIRECTORY, "config")
SECCOMP_DIRECTORY = os.path.join(DIRECTORY, "seccomp")

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

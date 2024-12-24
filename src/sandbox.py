import os
from typing import Optional, Dict, Any
from argparse import Namespace

from . import DIRECTORY, APP_DIRECTORY, CONFIG_DIRECTORY, SECCOMP_DIRECTORY, HOME_DIR
from .desktop import (DesktopEntry, sandboxed_desktop_entry_factory,
                      hidden_desktop_entry_factory, desktop_entry_factory)
from .permissions import (Permissions, PermissionBuilder,
                          DBusPermissionBuilder)
from .config import ConfigBuilder, Config
from .launcher import launch_sandbox

class Sandbox:

    def __init__(
            self,
            app: str,
            entry: str,
            path: str,
            permissions: Permissions,
            seccomp_filter: Optional[str] = None,
            dbus_app: Optional[str] = None,
            dbus_permissions: Optional[DBusPermissionBuilder] = None,
            portable: bool = False) -> None:

        self.app = app
        self.path = path
        self.entry = entry
        self.filename = f"/usr/bin/{entry}" if not portable else os.path.join(path, entry)
        self.seccomp_filter = seccomp_filter

        realpath = os.path.realpath(self.filename)
        self.realpath = realpath if " " not in realpath else f"\"{realpath}\""

        self.permissions = permissions
        self.dbus_app = dbus_app
        self.dbus_permissions = dbus_permissions
        self.portable = portable

        self.script = DIRECTORY + f"/{self.app}.sh"
        self.app_data_dir = APP_DIRECTORY + "/" + app

    def create_app(self) -> None:
        try:
            os.mkdir(self.app_data_dir)
        except Exception:
            raise ValueError("Sandboxed application already exists")

        if self.portable:
            if not os.path.exists(self.filename):
                raise FileNotFoundError(f"Portable application executable not found at {self.filename}")

            desktop_entry_path = os.path.join(self.path, f"{self.entry}.desktop")
            
            # Create the entry for portable apps and capture it
            entry = sandboxed_desktop_entry_factory(
                app=self.app,
                name=self.entry,
                script=f"sandbox-launch --app {self.app}",
                portable=True,
                path=desktop_entry_path)

        else:
            # Create sandboxed desktop entry first
            entry = sandboxed_desktop_entry_factory(
                app=self.app,
                name=self.entry,
                script=f"sandbox-launch --app {self.app}")

            entry = hidden_desktop_entry_factory(name=self.entry)
            entry = desktop_entry_factory(name=self.entry)

        # Create configuration file for the application
        ConfigBuilder(app=self.app,
                      entry=entry,
                      path=self.path,
                      permissions=self.permissions,
                      seccomp_filter=self.seccomp_filter,
                      dbus_app=self.dbus_app,
                      dbus_permissions=self.dbus_permissions,
                      portable=self.portable).build()

def sandbox_delete_app(app: str) -> None:
    os.system(f"rm -rf {APP_DIRECTORY}/{app}")
    os.system(f"rm -rf {CONFIG_DIRECTORY}/{app}")
    os.system(f"rm -rf {SECCOMP_DIRECTORY}/{app}")

    applications = os.path.join(HOME_DIR, ".local", "share", "applications")
    os.system(f"rm -rf {applications}/{app}-sandboxed.desktop")

def sandbox_app_factory(args: Namespace) -> None:
    permissions = PermissionBuilder()
    permissions.from_args(args)

    dbus_permissions = DBusPermissionBuilder()
    dbus_permissions.from_args(args)

    permissions = permissions.build()
    dbus_permissions = dbus_permissions.build()

    sandbox = Sandbox(app=args.app,
                      path=args.path,
                      entry=args.entry,
                      permissions=permissions,
                      seccomp_filter=args.seccomp,
                      dbus_app=args.dbus_app,
                      dbus_permissions=dbus_permissions,
                      portable=args.portable)
    sandbox.create_app()

def sandbox_launcher(args: Dict[str, Any], argstr: str) -> None:
    home_dir = os.path.expanduser("~")
    file_path = os.path.join(home_dir, ".sandbox_manager", "config", args.app)

    # Check if config file exists before trying to load it
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No config file found at {file_path}")

    config = Config.from_config(file_path)
    launch_sandbox(binary_cmd=config.cmd,
                   args=argstr,
                   app=config.app,
                   path=config.path,
                   permissions=config.permissions,
                   seccomp_filter=config.seccomp_filter,
                   dbus_app=config.dbus_app,
                   dbus_permissions=config.dbus_permissions,
                   portable=config.portable)

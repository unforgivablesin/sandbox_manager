import os
from typing import Optional, Dict, Any
from argparse import Namespace

from . import DIRECTORY, APP_DIRECTORY, CONFIG_DIRECTORY, SECCOMP_DIRECTORY, HOME_DIR
from .desktop import (DesktopEntry, sandboxed_desktop_entry_factory,
                      hidden_desktop_entry_factory, desktop_entry_factory)

from .permissions import (Permissions, PermissionBuilder,
                          DBusPermissionBuilder)

from .config import ConfigBuilder, Config
from .launcher import SandboxLauncher


class Sandbox:

    def __init__(
            self,
            app: str,
            entry: str,
            path: str,
            permissions: Permissions,
            seccomp_filter: Optional[str] = None,
            dbus_app: Optional[str] = None,
            dbus_permissions: Optional[DBusPermissionBuilder] = None) -> None:

        self.app = app
        self.path = path
        self.entry = entry
        self.filename = f"/usr/bin/{entry}"
        self.seccomp_filter = seccomp_filter

        realpath = os.path.realpath(self.filename)
        self.realpath = realpath if not " " in realpath else f"\"{realpath}\""

        self.permissions = permissions

        self.dbus_app = dbus_app
        self.dbus_permissions = dbus_permissions

        self.script = DIRECTORY + f"/{self.app}.sh"
        self.app_data_dir = APP_DIRECTORY + "/" + app

    def create_app(self) -> None:

        # Create application home directory
        try:
            os.mkdir(self.app_data_dir)
        except Exception:
            raise ValueError("Sandboxed application already exists")

        sandboxed_desktop_entry_factory(
            app=self.app,
            name=self.entry,
            script=f"sandbox-launch --app {self.app}")

        entry = hidden_desktop_entry_factory(name=self.entry)
        entry = desktop_entry_factory(name=self.entry)

        ConfigBuilder(app=self.app,
                      entry=entry,
                      path=self.path,
                      permissions=self.permissions,
                      seccomp_filter=self.seccomp_filter,
                      dbus_app=self.dbus_app,
                      dbus_permissions=self.dbus_permissions).build()


def sandbox_delete_app(app: str) -> None:
    home_dir = os.path.expanduser("~")
    config_file_path = os.path.join(home_dir, ".sandbox_manager", "config",
                                    app)

    config = Config.from_config(config_file_path)

    os.system(f"rm -rf {APP_DIRECTORY}/{app}")
    os.system(f"rm -rf {CONFIG_DIRECTORY}/{app}")
    os.system(f"rm -rf {SECCOMP_DIRECTORY}/{app}")

    applications = os.path.join(HOME_DIR, ".local", "share", "applications")

    os.system(f"rm -rf {applications}/{app}-sandboxed.desktop")
    os.system(f"rm -rf {applications}/{config.entry}")


def sandbox_app_factory(args: Namespace) -> None:

    permissions = PermissionBuilder()
    permissions.from_args(args)

    dbus_permissions = DBusPermissionBuilder()
    dbus_permissions.from_args(args)

    permissions = permissions.build()
    dbus_permissions = dbus_permissions.build()

    Sandbox(app=args.app,
            path=args.path,
            entry=args.entry,
            permissions=permissions,
            seccomp_filter=args.seccomp,
            dbus_app=args.dbus_app,
            dbus_permissions=dbus_permissions).create_app()


def sandbox_launcher(args: Dict[str, Any], argstr: str) -> None:
    home_dir = os.path.expanduser("~")
    config_file_path = os.path.join(home_dir, ".sandbox_manager", "config",
                                    args.app)

    config = Config.from_config(config_file_path)

    SandboxLauncher(binary_cmd=config.cmd,
                    args=argstr,
                    app=config.app,
                    path=config.path,
                    permissions=config.permissions,
                    seccomp_filter=config.seccomp_filter,
                    dbus_app=config.dbus_app,
                    dbus_permissions=config.dbus_permissions).launch()

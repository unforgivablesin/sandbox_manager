import json
from typing import Self, Optional

from . import CONFIG_DIRECTORY
from .permissions import Permissions, DBusPermissions
from .desktop import DesktopEntry


class Config:

    def __init__(self,
                 app: str,
                 path: str,
                 icon: str,
                 cmd: str,
                 entry: str,
                 permissions: Permissions,
                 seccomp_filter: Optional[str] = None,
                 dbus_app: Optional[str] = None,
                 dbus_permissions: Optional[DBusPermissions] = None) -> None:
        self.app = app
        self.path = path
        self.icon = icon
        self.cmd = cmd
        self.permissions = permissions
        self.seccomp_filter = seccomp_filter
        self.entry = entry

        self.dbus_app = dbus_app
        self.dbus_permissions = dbus_permissions

    @classmethod
    def from_config(cls, config: str) -> Self:
        data = json.load(open(config))

        return cls(app=data['app'],
                   path=data['path'],
                   icon=data['icon'],
                   cmd=data['cmd'],
                   entry=data['entry'],
                   permissions=Permissions.from_dict(data['permissions']),
                   seccomp_filter=data['seccomp_filter'],
                   dbus_app=data['dbus_app'],
                   dbus_permissions=DBusPermissions.from_dict(
                       data['dbus_permissions']))


class ConfigBuilder:

    def __init__(self,
                 app: str,
                 path: str,
                 entry: DesktopEntry,
                 permissions: Permissions,
                 seccomp_filter: Optional[str] = None,
                 dbus_app: Optional[str] = None,
                 dbus_permissions: DBusPermissions = None) -> None:
        self.app = app
        self.path = path
        self.entry = entry
        self.permissions = permissions
        self.seccomp_filter = seccomp_filter

        self.dbus_app = dbus_app
        self.dbus_permissions = dbus_permissions

    def build(self) -> None:

        data = {
            "app": self.app,
            "path": self.path,
            "icon": self.entry._icon,
            "cmd": self.entry._exec,
            "entry": self.entry._entry,
            "permissions": self.permissions.permissions,
            "seccomp_filter": self.seccomp_filter,
            "dbus_app": self.dbus_app,
            "dbus_permissions": self.dbus_permissions.permissions
        }

        with open(CONFIG_DIRECTORY + "/" + self.app, "w") as fp:
            fp.write(json.dumps(data, indent=4))

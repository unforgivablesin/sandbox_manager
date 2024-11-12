from typing import Self, Dict
from argparse import Namespace


class PermissionList:

    Dri = 1
    Dbus = 2
    Ipc = 4
    DownloadsFolder = 8
    HomeFolder = 16
    Pulseaudio = 32
    Pipewire = 64


class DBusPermissionList:

    Notifications = 1
    Screencast = 2
    Screenshot = 4


class PermissionsBase:

    def __init__(self, permissions: int) -> None:
        self._permissions = permissions

    def __int__(self) -> int:
        return self._permissions

    @classmethod
    def from_dict(cls, data) -> Self:
        return cls(0)

    @property
    def permissions(self) -> Dict[str, bool]:
        ...

    def has_permission(self, permission: PermissionList) -> bool:
        return (self._permissions & permission) == permission

    def set_permission(self, permission: PermissionList) -> None:
        self._permissions |= permission


class Permissions(PermissionsBase):

    def __init__(self, permissions: int) -> None:
        PermissionsBase.__init__(self, permissions=permissions)

    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> Self:
        permissions = cls(0)
        if data['dri']: permissions.set_permission(PermissionList.Dri)
        if data['ipc']: permissions.set_permission(PermissionList.Ipc)
        if data['dbus']: permissions.set_permission(PermissionList.Dbus)
        if data['downloads']:
            permissions.set_permission(PermissionList.DownloadsFolder)
        if data['home']: permissions.set_permission(PermissionList.HomeFolder)
        if data['pulseaudio']:
            permissions.set_permission(PermissionList.Pulseaudio)
        if data['pipewire']:
            permissions.set_permission(PermissionList.Pipewire)
        return permissions

    @property
    def permissions(self) -> Dict[str, bool]:
        return {
            "dri": self.has_permission(PermissionList.Dri),
            "ipc": self.has_permission(PermissionList.Ipc),
            "dbus": self.has_permission(PermissionList.Dbus),
            "downloads": self.has_permission(PermissionList.DownloadsFolder),
            "home": self.has_permission(PermissionList.HomeFolder),
            "pulseaudio": self.has_permission(PermissionList.Pulseaudio),
            "pipewire": self.has_permission(PermissionList.Pipewire),
        }


class DBusPermissions(PermissionsBase):

    def __init__(self, permissions: int) -> None:
        PermissionsBase.__init__(self, permissions=permissions)

    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> Self:
        permissions = cls(0)
        if data['notifications']:
            permissions.set_permission(DBusPermissionList.Notifications)
        if data['screencast']:
            permissions.set_permission(DBusPermissionList.Screencast)
        if data['screenshot']:
            permissions.set_permission(DBusPermissionList.Screenshot)
        return permissions

    @property
    def permissions(self) -> Dict[str, bool]:
        return {
            "notifications":
            self.has_permission(DBusPermissionList.Notifications),
            "screencast": self.has_permission(DBusPermissionList.Screencast),
            "screenshot": self.has_permission(DBusPermissionList.Screenshot),
        }


class PermissionBuilder:

    def __init__(self) -> None:
        self._permissions = 0

    def build(self) -> Permissions:
        return Permissions(permissions=self._permissions)

    def from_args(self, args: Namespace) -> None:
        if args.dri:
            self.dri()
        if args.ipc:
            self.ipc()
        if args.dbus:
            self.dbus()
        if args.home:
            self.shared_home_folder()
        if args.downloads:
            self.shared_downloads_folder()
        if args.pulseaudio:
            self.pulseaudio()
        if args.pipewire:
            self.pipewire()

    def pipewire(self) -> Self:
        self._permissions |= PermissionList.Pipewire
        return self

    def pulseaudio(self) -> Self:
        self._permissions |= PermissionList.Pulseaudio
        return self

    def shared_home_folder(self) -> Self:
        self._permissions |= PermissionList.HomeFolder
        return self

    def shared_downloads_folder(self) -> Self:
        self._permissions |= PermissionList.DownloadsFolder
        return self

    def dbus(self) -> Self:
        self._permissions |= PermissionList.Dbus
        return self

    def dri(self) -> Self:
        self._permissions |= PermissionList.Dri
        return self

    def ipc(self) -> Self:
        self._permissions |= PermissionList.Ipc
        return self


class DBusPermissionBuilder:

    def __init__(self) -> None:
        self._permissions = 0

    def build(self) -> DBusPermissions:
        return DBusPermissions(permissions=self._permissions)

    def from_args(self, args: Namespace) -> None:
        if args.notifications:
            self.notifications()
        if args.screencast:
            self.screencast()
        if args.screenshot:
            self.screenshot()

    def screencast(self) -> Self:
        self._permissions |= DBusPermissionList.Screencast
        return self

    def screenshot(self) -> Self:
        self._permissions |= DBusPermissionList.Screenshot
        return self

    def notifications(self) -> Self:
        self._permissions |= DBusPermissionList.Notifications
        return self

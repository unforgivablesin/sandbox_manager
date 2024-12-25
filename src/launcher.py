import os, fcntl, subprocess
from typing import Optional

from . import APP_DIRECTORY
from .permissions import Permissions, DBusPermissionList, PermissionList


class XdgDbusProxy:

    def __init__(self, app: str, permissions: Permissions) -> None:
        self._app = app
        self._permissions = permissions

        self._command = ["/usr/bin/xdg-dbus-proxy"]
        self._xdg_runtime_dir = os.environ['XDG_RUNTIME_DIR']

    def _set_permissions(self) -> None:

        self._command.append(f"--own={self._app}")
        self._command.append(f"--own={self._app}.*")

        if self._permissions.has_permission(DBusPermissionList.Notifications):
            self._command.append("--talk=org.freedesktop.portal.Notification")
        if self._permissions.has_permission(DBusPermissionList.Screencast):
            self._command.append("--talk=org.freedesktop.portal.Screencast")
        if self._permissions.has_permission(DBusPermissionList.Screenshot):
            self._command.append("--talk=org.freedesktop.portal.Screenshot")

    def _set_dbus_proxy_socket(self) -> None:
        dbus_session_bus_address = os.environ['DBUS_SESSION_BUS_ADDRESS']

        self._command.append(
            f"{dbus_session_bus_address} {self._xdg_runtime_dir}/xdg-dbus-proxy/{self._app}.sock"
        )

    def launch(self) -> int:

        self._set_dbus_proxy_socket()
        self._set_permissions()

        args = " ".join(arg for arg in self._command)
        print(args)
        print("------------------")

        os.system(f"mkdir -p {self._xdg_runtime_dir}/xdg-dbus-proxy")

        pid = os.fork()

        if not pid:
            os.execl(self._command[0], *args.split(" "))

        return pid


class SandboxLauncher:

    def __init__(
            self,
            binary_cmd: str,
            args: str,
            app: str,
            path: str,
            permissions: Permissions,
            seccomp_filter: Optional[str] = None,
            dbus_app: Optional[str] = None,
            dbus_permissions: Optional[DBusPermissionList] = None) -> None:
        self.binary_cmd = binary_cmd
        self.args = args
        self.app = app
        self.path = path
        self.permissions = permissions
        self.seccomp_filter = seccomp_filter
        self.dbus_app = dbus_app
        self.dbus_permissions = dbus_permissions

        self.command = ["/bin/bwrap"]

        self.wayland_display = os.environ.get('WAYLAND_DISPLAY')
        self.xauthority = os.environ.get('XAUTHORITY')
        self.xdg_runtime_dir = os.environ['XDG_RUNTIME_DIR']
        self.xdg_data_dirs = os.environ['XDG_DATA_DIRS']
        self.display = os.environ.get('DISPLAY')
        self.home = os.environ['HOME']
        self.user = os.environ['USER']

        self.seccomp_fd = None
        self.xdg_proxy_pid = None

    def _bind(self, source: str, dest: Optional[str] = None) -> None:
        dest = dest if dest else source
        self.command.append(f"--bind-try {source} {dest}")

    def _ro_bind(self, source: str, dest: Optional[str] = None) -> None:
        dest = dest if dest else source
        self.command.append(f"--ro-bind-try {source} {dest}")

    def _dev_bind(self, source: str, dest: Optional[str] = None) -> None:
        dest = dest if dest else source
        self.command.append(f"--dev-bind-try {source} {dest}")

    def _set_env(self, env: str, value: str) -> None:
        self.command.append(f"--setenv {env} {value}")

    def _tmpfs_bind(self, path: str) -> None:
        self.command.append(f"--tmpfs {path}")

    def _set_ipc_permission(self) -> None:
        if not self.permissions.has_permission(PermissionList.Ipc):
            self.command.append("--unshare-ipc")

    def _set_security_isolation(self) -> None:
        self.command.append("--unshare-pid")
        self.command.append("--unshare-uts")
        self.command.append("--unshare-cgroup")
        self.command.append("--unshare-user")
        self.command.append("--new-session")

    def _bind_etc_paths(self) -> None:
        etc_bind_paths = [
            "/etc/ssl/certs/ca-bundle.crt",
            "/etc/ssl/certs/ca-certificates.crt", "/etc/resolv.conf",
            "/etc/hosts", "/etc/ld.so.preload", "/etc/ld.so.conf",
            "/etc/ld.so.cache", "/etc/ld.so.conf.d", "/etc/fonts"
        ]

        for path in etc_bind_paths:
            self._ro_bind(path)

    def _bind_filesystem_paths(self) -> None:
        fs_bind_paths = ["/usr", "/lib64", "/lib", "/usr", "/proc", "/dev"]

        for path in fs_bind_paths:
            self._ro_bind(path)

        self.command.append("--dev /dev")
        self.command.append("--proc /proc")

        self._tmpfs_bind("/var")
        self._tmpfs_bind("/tmp")

        self.command.append(f"--tmpfs /run --dir {self.xdg_runtime_dir}")

    def _set_display(self) -> None:
        if self.display:
            self._set_env("DISPLAY", self.display)

            if self.xauthority:
                self._ro_bind(self.xauthority)

        if self.wayland_display:
            self._set_env("WAYLAND_DISPLAY", self.wayland_display)
            self._set_env("XDG_SESSION_TYPE", "wayland")

            self._ro_bind(f"{self.xdg_runtime_dir}/{self.wayland_display}")

    def _set_dri(self) -> None:
        if self.permissions.has_permission(PermissionList.Dri):
            self._dev_bind("/dev/dri")
            self._ro_bind("/sys/devices/pci0000:00")
            self._ro_bind("/sys/dev/char")

    def _set_audio(self) -> None:
        if self.permissions.has_permission(PermissionList.Pulseaudio):
            self._ro_bind(f"{self.xdg_runtime_dir}/pulse")

        if self.permissions.has_permission(PermissionList.Pipewire):
            self._ro_bind(f"{self.xdg_runtime_dir}/pipewire-0")

    def _set_shared_downloads(self) -> None:
        if self.permissions.has_permission(PermissionList.DownloadsFolder):
            self._bind(f"{self.home}/Downloads")

    def _set_shared_home(self) -> None:
        if self.permissions.has_permission(PermissionList.HomeFolder):
            self._bind(self.home)
        else:
            self._bind(source=f"{APP_DIRECTORY}/{self.app}", dest=self.home)

    def _launch_xdg_dbus_proxy(self) -> Optional[int]:
        if self.permissions.has_permission(PermissionList.Dbus):
            xdg_socket_path = f"{self.xdg_runtime_dir}/xdg-dbus-proxy/{self.dbus_app}.sock"
            self._ro_bind(source=xdg_socket_path, dest="/run/user/1000/bus")

            self._ro_bind("/var/lib/dbus/machine-id")
            self._ro_bind("/etc/machine-id")
            self._set_env("DBUS_SESSION_BUS_ADDRESS",
                          "unix:path=/run/user/1000/bus")

            return XdgDbusProxy(app=self.dbus_app,
                                permissions=self.dbus_permissions).launch()

    def _set_misc(self) -> None:
        self._set_env("GTK_THEME", "Adwaita:dark")
        self._set_env("XDG_DATA_DIRS", self.xdg_data_dirs)
        self._bind(f"/home/{self.user}/.config/mimeapps.list")

    def launch(self) -> None:
        self._set_security_isolation()
        self._set_ipc_permission()

        self._bind_etc_paths()
        self._bind_filesystem_paths()

        self._set_display()

        self._set_shared_downloads()
        self._set_shared_home()

        self._set_misc()

        xdg_dbus_proxy_pid = self._launch_xdg_dbus_proxy()
        self._ro_bind(self.path)

        if self.seccomp_filter:
            fd = open(self.seccomp_filter, "r")
            self.seccomp_fd = os.dup(fd.fileno())
            fcntl.fcntl(
                self.seccomp_fd, fcntl.F_SETFD,
                fcntl.fcntl(self.seccomp_fd, fcntl.F_GETFD)
                & ~fcntl.FD_CLOEXEC)

            self.command.append(f"--seccomp {self.seccomp_fd}")

        self.command.append(self.binary_cmd)
        self.command.append(self.args)

        command_args = " ".join(arg for arg in self.command[1:])
        print(self.command[0], command_args)
        print("------------------")

        if self.seccomp_fd:
            subprocess.check_output(f"{self.command[0]} {command_args}",
                                    shell=True,
                                    pass_fds=[self.seccomp_fd])
        else:
            subprocess.check_output(f"{self.command[0]} {command_args}",
                                    shell=True)

        if xdg_dbus_proxy_pid:
            os.kill(xdg_dbus_proxy_pid, 9)

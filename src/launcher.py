import os, fcntl, subprocess
from typing import Optional

from . import APP_DIRECTORY
from .permissions import Permissions, DBusPermissionList, PermissionList


def launch_xdg_dbus_proxy(app: str, permissions: Permissions) -> int:

    command = ["/usr/bin/xdg-dbus-proxy"]

    dbus_session_bus_address = os.environ['DBUS_SESSION_BUS_ADDRESS']
    xdg_runtime_dir = os.environ['XDG_RUNTIME_DIR']

    command.append(
        f"{dbus_session_bus_address} {xdg_runtime_dir}/xdg-dbus-proxy/{app}.sock"
    )

    command.append(f"--own={app}")
    command.append(f"--own={app}.*")

    if permissions.has_permission(DBusPermissionList.Notifications):
        command.append("--talk=org.freedesktop.portal.Notification")
    if permissions.has_permission(DBusPermissionList.Screencast):
        command.append("--talk=org.freedesktop.portal.Screencast")
    if permissions.has_permission(DBusPermissionList.Screenshot):
        command.append("--talk=org.freedesktop.portal.Screenshot")

    args = " ".join(arg for arg in command)
    print(args)
    print("------------------")

    os.system(f"mkdir -p {xdg_runtime_dir}/xdg-dbus-proxy")

    pid = os.fork()

    if not pid:
        os.execl(command[0], *args.split(" "))

    return pid


def launch_sandbox(
        binary_cmd: str,
        args: str,
        app: str,
        path: str,
        permissions: Permissions,
        seccomp_filter: Optional[str] = None,
        dbus_app: Optional[str] = None,
        dbus_permissions: Optional[DBusPermissionList] = None) -> None:
    command = ["/bin/bwrap"]

    wayland_display = os.environ.get('WAYLAND_DISPLAY')
    xauthority = os.environ.get('XAUTHORITY')
    xdg_runtime_dir = os.environ['XDG_RUNTIME_DIR']
    display = os.environ.get('DISPLAY')
    home = os.environ['HOME']

    seccomp_fd = None
    xdg_proxy_pid = None

    # IPC
    if not permissions.has_permission(PermissionList.Ipc):
        command.append("--unshare-ipc")

    command.append("--unshare-pid")
    command.append("--unshare-uts")
    command.append("--unshare-cgroup")
    command.append("--unshare-user")
    command.append("--new-session")
    #command.append("--unshare-net")

    # /etc
    command.append(
        "--ro-bind-try /etc/ssl/certs/ca-bundle.crt /etc/ssl/certs/ca-bundle.crt"
    )
    command.append(
        "--ro-bind-try /etc/ssl/certs/ca-bundle.crt /etc/ssl/certs/ca-certificates.crt"
    )
    command.append("--ro-bind-try /etc/resolv.conf /etc/resolv.conf")
    command.append("--ro-bind-try /etc/hosts /etc/hosts")
    command.append("--ro-bind-try /etc/ld.so.preload /etc/ld.so.preload")
    command.append("--ro-bind-try /etc/ld.so.conf /etc/ld.so.conf")
    command.append("--ro-bind-try /etc/ld.so.conf /etc/ld.so.conf")
    command.append("--ro-bind-try /etc/ld.so.cache /etc/ld.so.cache")
    command.append("--ro-bind-try /etc/ld.so.conf.d /etc/ld.so.conf.d")
    command.append("--ro-bind-try /etc/fonts /etc/fonts")

    # Necessary to run
    command.append("--ro-bind /usr /usr")
    command.append("--ro-bind /lib64 /lib64")
    command.append("--ro-bind /lib /lib")
    command.append("--ro-bind /usr /usr")
    command.append("--ro-bind /proc /proc")
    command.append("--ro-bind /dev /dev")
    command.append("--tmpfs /var")
    command.append("--tmpfs /tmp")
    command.append(f"--tmpfs /run --dir {xdg_runtime_dir}")
    command.append("--dev /dev")
    command.append("--proc /proc")

    # Mount directory of application
    command.append(f"--ro-bind {path} {path}")

    # Give access to /etc/resolv.conf and hosts
    command.append("--ro-bind-try /etc/resolv.conf /etc/resolv.conf")
    #command.append("--ro-bind-try /etc/hosts /etc/hosts")

    # Use X11 when available
    if display:
        command.append(f"--setenv DISPLAY {display}")

        if xauthority:
            command.append(f"--ro-bind {xauthority} {xauthority}")

    # Use wayland when available
    if wayland_display:
        command.append(f"--setenv WAYLAND_DISPLAY {wayland_display}")
        command.append("--setenv XDG_SESSION_TYPE wayland")

    command.append(
        f"--ro-bind {xdg_runtime_dir}/{wayland_display} {xdg_runtime_dir}/{wayland_display}"
    )

    # Seperate home folder
    if permissions.has_permission(PermissionList.HomeFolder):
        command.append(f"--bind-try {home} {home}")
    else:
        command.append(f"--bind-try {APP_DIRECTORY}/{app} {home}")

    if permissions.has_permission(PermissionList.DownloadsFolder):
        command.append(f"--bind-try {home}/Downloads {home}/Downloads")

    # Rest of the permissions
    if permissions.has_permission(PermissionList.Dri):
        command.append("--dev-bind /dev/dri /dev/dri")
        command.append(
            "--ro-bind /sys/devices/pci0000:00 /sys/devices/pci0000:00")
        command.append("--ro-bind /sys/dev/char /sys/dev/char")

    if permissions.has_permission(PermissionList.Pulseaudio):
        command.append(
            f"--ro-bind-try {xdg_runtime_dir}/pulse {xdg_runtime_dir}/pulse")

    if permissions.has_permission(PermissionList.Pipewire):
        command.append(
            f"--ro-bind-try {xdg_runtime_dir}/pipewire-0 {xdg_runtime_dir}/pipewire-0"
        )

    # DBus proxy
    if permissions.has_permission(PermissionList.Dbus):
        command.append(
            f"--ro-bind {xdg_runtime_dir}/xdg-dbus-proxy/{dbus_app}.sock /run/user/1000/bus"
        )
        command.append(
            "--ro-bind /var/lib/dbus/machine-id /var/lib/dbus/machine-id")
        command.append(
            "--setenv DBUS_SESSION_BUS_ADDRESS unix:path=/run/user/1000/bus")

        xdg_proxy_pid = launch_xdg_dbus_proxy(app=dbus_app,
                                              permissions=dbus_permissions)

    # Set the theme to dark
    command.append("--setenv GTK_THEME Adwaita:dark")

    # Seccomp
    if seccomp_filter:
        # We want to open the file and unset CLOEXEC so it doesnt close on exec
        fd = open(seccomp_filter, "r")
        seccomp_fd = os.dup(fd.fileno())
        fcntl.fcntl(seccomp_fd, fcntl.F_SETFD,
                    fcntl.fcntl(seccomp_fd, fcntl.F_GETFD) & ~fcntl.FD_CLOEXEC)

        command.append(f"--seccomp {seccomp_fd}")

    # Test
    aaa = os.environ['XDG_DATA_DIRS']
    command.append(f"--setenv XDG_DATA_DIRS {aaa}")
    command.append(
        "--bind /home/user/.config/mimeapps.list /home/user/.config/mimeapps.list"
    )

    command.append(binary_cmd)
    command.append(args)

    # When Wayland is available we will always choose it over X11
    #if wayland_display:
    #    command.append("--ozone-platform=wayland")

    args = " ".join(arg for arg in command[1:])
    print(command[0], args)
    print("------------------")

    subprocess.check_output(f"{command[0]} {args}",
                            shell=True,
                            pass_fds=[seccomp_fd])

    # Kill xdg dbus proxy
    if xdg_proxy_pid:
        os.kill(xdg_proxy_pid, 9)

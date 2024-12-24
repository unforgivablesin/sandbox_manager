import os, fcntl, subprocess
from typing import Optional, Tuple

from . import APP_DIRECTORY
from .permissions import Permissions, DBusPermissionList, PermissionList

def launch_xdg_dbus_proxy(app: str, permissions: Permissions) -> int:
    command = ["/usr/bin/xdg-dbus-proxy"]
    dbus_session_bus_address = os.environ['DBUS_SESSION_BUS_ADDRESS']
    xdg_runtime_dir = os.environ['XDG_RUNTIME_DIR']
    
    command.append(f"{dbus_session_bus_address} {xdg_runtime_dir}/xdg-dbus-proxy/{app}.sock")
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
    
    os.makedirs(f"{xdg_runtime_dir}/xdg-dbus-proxy", exist_ok=True)
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
    dbus_permissions: Optional[DBusPermissionList] = None,
    portable: bool = False
) -> None:
    command = ["/bin/bwrap"]
    
    wayland_display = os.environ.get('WAYLAND_DISPLAY')
    xauthority = os.environ.get('XAUTHORITY')
    xdg_runtime_dir = os.environ['XDG_RUNTIME_DIR']
    xdg_data_dirs = os.environ['XDG_DATA_DIRS']
    display = os.environ.get('DISPLAY')
    home = os.environ['HOME']
    user = os.environ['USER']
    
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
    
    # Basic system bindings
    command.extend([
        "--bind /run/dbus /run/dbus",
        "--bind /var/run/dbus /var/run/dbus",
        "--bind /run/dbus/system_bus_socket /run/dbus/system_bus_socket",
        "--bind-try /run/user/1000/bus /run/user/1000/bus",
        "--ro-bind /bin/bash /bin/bash",
        "--ro-bind /bin/sh /bin/sh",
        "--ro-bind /usr/bin/env /usr/bin/env",
        "--ro-bind /usr/bin/dirname /usr/bin/dirname",
        "--ro-bind /usr/bin/basename /usr/bin/basename",
        "--ro-bind /usr/bin/grep /usr/bin/grep",
        "--ro-bind /usr/bin/sed /usr/bin/sed",
        "--ro-bind /etc/shells /etc/shells",
        "--ro-bind-try /etc/ssl/certs/ca-bundle.crt /etc/ssl/certs/ca-bundle.crt",
        "--ro-bind-try /etc/resolv.conf /etc/resolv.conf",
        "--ro-bind-try /etc/hosts /etc/hosts",
        "--ro-bind-try /etc/ld.so.cache /etc/ld.so.cache",
        "--ro-bind-try /etc/fonts /etc/fonts",
        "--ro-bind /usr /usr",
        "--ro-bind /lib64 /lib64",
        "--ro-bind /lib /lib",
        "--ro-bind /proc /proc",
        "--ro-bind /dev /dev",
        "--tmpfs /var",
        "--tmpfs /tmp",
        f"--tmpfs /run --dir {xdg_runtime_dir}",
        "--dev /dev",
        "--proc /proc"
    ])

    # Special handling for Tor Browser
    if app == "TorBrowser":
        browser_dir = os.path.join(path, "Browser")
        if os.path.exists(browser_dir):
            # Bind parent and subdirectory in correct order
            command.extend([
                f"--bind {path} {path}",
                f"--bind {browser_dir} {browser_dir}",
                "--setenv HOME /home/admin",
                "--setenv TOR_BROWSER_DIR /usr/share/tor-browser",
                "--setenv GSETTINGS_BACKEND memory",
                "--setenv __GL_SHADER_DISK_CACHE 0"
            ])
            binary_cmd = f"sh -c 'cd {browser_dir} && exec ./start-tor-browser'"
        else:
            raise FileNotFoundError(f"Tor Browser directory not found at {browser_dir}")
    
    if display:
        command.append(f"--setenv DISPLAY {display}")
        if xauthority:
            command.append(f"--ro-bind {xauthority} {xauthority}")
    
    if wayland_display:
        command.extend([
            f"--setenv WAYLAND_DISPLAY {wayland_display}",
            "--setenv XDG_SESSION_TYPE wayland",
            f"--ro-bind {xdg_runtime_dir}/{wayland_display} {xdg_runtime_dir}/{wayland_display}"
        ])

    if permissions.has_permission(PermissionList.HomeFolder):
        command.append(f"--bind-try {home} {home}")
    else:
        command.append(f"--bind-try {APP_DIRECTORY}/{app} {home}")
    
    if permissions.has_permission(PermissionList.DownloadsFolder):
        command.append(f"--bind-try {home}/Downloads {home}/Downloads")

    # DRI - Asahi Linux specific paths
    if permissions.has_permission(PermissionList.Dri):
        command.extend([
            "--dev-bind /dev/dri /dev/dri",
            "--ro-bind-try /sys/dev/char /sys/dev/char",
            "--ro-bind-try /sys/class/drm /sys/class/drm",
            "--ro-bind-try /sys/devices/platform/soc/206400000.gpu /sys/devices/platform/soc/206400000.gpu",
            "--ro-bind-try /sys/devices/platform/soc/soc:display-subsystem /sys/devices/platform/soc/soc:display-subsystem",
            "--ro-bind /usr/lib64/dri /usr/lib64/dri",
            "--ro-bind-try /proc/cpuinfo /proc/cpuinfo",
            "--ro-bind-try /sys/devices/system/cpu /sys/devices/system/cpu",
            "--ro-bind-try /sys/class/drm/card1/device/drm /sys/class/drm/card1/device/drm",
            "--ro-bind-try /sys/class/drm/card2/device/drm /sys/class/drm/card2/device/drm",
            "--ro-bind-try /sys/class/drm/card2-eDP-1/device /sys/class/drm/card2-eDP-1/device",
            "--setenv LIBGL_VSYNC 0",
            "--setenv __GL_SYNC_TO_VBLANK 0",
            "--setenv GALLIUM_DRIVER asahi"
        ])

    if permissions.has_permission(PermissionList.Pulseaudio):
        command.append(f"--ro-bind-try {xdg_runtime_dir}/pulse {xdg_runtime_dir}/pulse")
    if permissions.has_permission(PermissionList.Pipewire):
        command.append(f"--ro-bind-try {xdg_runtime_dir}/pipewire-0 {xdg_runtime_dir}/pipewire-0")

    if permissions.has_permission(PermissionList.Dbus):
        command.extend([
            f"--ro-bind {xdg_runtime_dir}/xdg-dbus-proxy/{dbus_app}.sock /run/user/1000/bus",
            "--ro-bind /var/lib/dbus/machine-id /var/lib/dbus/machine-id",
            "--setenv DBUS_SESSION_BUS_ADDRESS unix:path=/run/user/1000/bus"
        ])
        xdg_proxy_pid = launch_xdg_dbus_proxy(app=dbus_app, permissions=dbus_permissions)

    command.extend([
        "--setenv GTK_THEME Adwaita:dark",
        f"--setenv XDG_DATA_DIRS {xdg_data_dirs}",
        f"--bind /home/{user}/.config/mimeapps.list /home/{user}/.config/mimeapps.list"
    ])

    if seccomp_filter:
        fd = open(seccomp_filter, "r")
        seccomp_fd = os.dup(fd.fileno())
        fcntl.fcntl(seccomp_fd, fcntl.F_SETFD, fcntl.fcntl(seccomp_fd, fcntl.F_GETFD) & ~fcntl.FD_CLOEXEC)
        command.append(f"--seccomp {seccomp_fd}")

    command.append(binary_cmd)
    command.append(args)
    args = " ".join(arg for arg in command[1:])
    print(command[0], args)
    print("------------------")

    try:
        if seccomp_fd:
            subprocess.check_output(f"{command[0]} {args}", shell=True, pass_fds=[seccomp_fd])
        else:
            subprocess.check_output(f"{command[0]} {args}", shell=True)
    finally:
        if xdg_proxy_pid:
            os.kill(xdg_proxy_pid, 9)

# Sandbox Tool

A simple sandbox tool that works with bubblewrap, seccomp, and xdg-dbus-proxy to securely start your applications from a desktop entry.

### Use case
---

If you do not want to use flatpak for your applications but you are looking for a secure program to sandbox your applications without sacrificing convenience. This is it.

### Examples
---

Set up Element with Wayland for graphics, DRI for video acceleration and NET for sharing a network namespace

```bash
sandbox-create --app Element --entry element-desktop --path /opt/Element --dri
```

Set up Element with Wayland for graphics, Audio, DRI for video acceleration and a shared Downloads folder with the user in $HOME/Downloads. DBus permissions for notifications, screencasting and screenshotting.

```bash
sandbox-create --app Element \
    --path /opt/Element \
    --entry element-desktop \
    --dri \
    --downloads \
    --pulseaudio \
    --pipewire \
    --dbus \
    --dbus-app im.riot.Riot \
    --notifications \
    --screencast \
```

### Seccomp
---

To utilize seccomp-bpf for increased security, go to tools/minijail, and follow these instructions.
**Whitelisting** is always better than blacklisting. So we shall first try to create a whitelist seccomp-bpf.

First we want to generate the LLVM IR for our platform specific instruction set.

```bash
make minijail0 constants.json
```

Then we want to strace the application we want to confine so we can pull all of the syscalls it uses, and turn it into a policy file.

```bash
strace -f -e raw=all -o strace.txt -- <program>
./tools/generate_seccomp_policy.py strace.txt > <program>.policy
```

Now we want to compile it into an actual BPF filter.

```bash
./tools/compile_seccomp_policy.py <program>.policy <program>.bpf
```

Now we want to output this in `/home/$USER/.sandbox_manager/seccomp`

```bash
mv <program>.policy /home/$USER/.sandbox_manager/seccomp
mv <program>.bpf /home/$USER/.sandbox_manager/seccomp
```

Now if we want to add the seccomp filter to our program:

```bash
sandbox-create \
    --app Element \
    --entry element-desktop \
    --dri \
    --seccomp /home/$USER/.sandbox_manager/seccomp/element.bpf
```

if the program is not launching correctly, check `/var/log/audit/audit.log` for seccomp denials to fix them. By reading the syscall you can create a very strict policy.

```md
type=SECCOMP msg=audit(1728657531.241:911): auid=1000 uid=1000 gid=1000 ses=4 subj=unconfined_u:unconfined_r:unconfined_t:s0 pid=40463 comm="element-desktop" exe="/opt/Element/element-desktop" sig=31 arch=c000003e **syscall=296** compat=0 ip=0x7f2461d1f050 code=0x0AUID="user" UID="user" GID="user" ARCH=x86_64 **SYSCALL=pwritev**
```

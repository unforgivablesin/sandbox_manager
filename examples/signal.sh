#!/bin/bash

sandbox-create --app Signal \
    --path /usr/lib64/Signal \
    --entry signal-desktop \
    --dri \
    --downloads \
    --pulseaudio \
    --pipewire \
    --dbus \
    --dbus-app org.signal.Signal \
    --screencast \
    --screenshot \
    --seccomp /home/$USER/.sandbox_manager/seccomp/signal-desktop.bpf    


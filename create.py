#!/bin/python3

import argparse, os
from src.sandbox import sandbox_app_factory

parser = argparse.ArgumentParser(description='Sandbox tool creation')

parser.add_argument('--app', required=True)
parser.add_argument('--path', required=True)
parser.add_argument('--entry', required=True)
parser.add_argument('--seccomp')

parser.add_argument('--dri',
                    action='store_true',
                    help="Enable video acceleration with DRI")
parser.add_argument('--ipc',
                    action='store_true',
                    help="Allow Interprocess communication")
parser.add_argument('--home',
                    action='store_true',
                    help="Share entire home directory")
parser.add_argument('--downloads',
                    action='store_true',
                    help="Share Downloads folder")
parser.add_argument('--pulseaudio',
                    action='store_true',
                    help="Allow application to send audio with Pulseaudio")
parser.add_argument('--pipewire',
                    action='store_true',
                    help="Allow application to send audio with Pipewire")
"""
Dbus permissions
"""

parser.add_argument('--dbus',
                    action='store_true',
                    help="Allow dbus communication with xdg-dbus-proxy")
parser.add_argument('--dbus-app')

parser.add_argument('--screencast',
                    action='store_true',
                    help="Allows the application to screenshare")
parser.add_argument('--screenshot',
                    action='store_true',
                    help="Allows the application to take screenshots")
parser.add_argument('--notifications',
                    action='store_true',
                    help="Allows the application to show notifications")
parser.add_argument(
    '--vfs',
    action='store_true',
    help="Allow the application to interact with virtual filesystems")

args = parser.parse_args()

if args.seccomp and not os.path.exists(args.seccomp):
    parser.error("--seccomp requires a valid path to a BPF filter")

if args.dbus:
    if not args.dbus_app:
        parser.error(
            "--dbus-app is required if dbus is enabled. Example: --dbus-app org.signal.Signal"
        )

if not args.dbus:
    if args.screencast or args.screenshot or args.vfs:
        parser.error(
            "Cannot enable screencasting/screenshotting/vfs without DBus access."
        )

sandbox_app_factory(args)

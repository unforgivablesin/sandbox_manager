#!/bin/python3

import argparse
from src.sandbox import sandbox_delete_app

parser = argparse.ArgumentParser(description='Sandbox tool launching')

parser.add_argument('--app', required=True)
options = parser.parse_args()

print(f"Deleting application '\x1b[91m{options.app}\x1b[0m'")
sandbox_delete_app(app=options.app)

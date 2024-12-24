#!/bin/python3

import argparse
from src.sandbox import sandbox_launcher

parser = argparse.ArgumentParser(description='Sandbox tool launching')

parser.add_argument('--app', required=True)
parser.add_argument('--portable',
                    action='store_true',
                    help="Specify if the application is portable")
parser.add_argument('args',
                    nargs=argparse.REMAINDER,
                    help='Rest of the arguments')

args = parser.parse_args()
argstr = ' '.join(args.args)

sandbox_launcher(args, argstr)

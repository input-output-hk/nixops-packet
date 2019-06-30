#! /usr/bin/env python2
# -*- coding: utf-8 -*-

#from nixops import deployment
#from nixops.nix_expr import py2nix
#from nixops.parallel import MultipleExceptions, run_tasks
#import pluggy

#import nixops.statefile
#import prettytable
#import argparse
#import os
#import pwd
#import re
#import sys
#import subprocess
#import nixops.parallel
#import nixops.util
#import nixops.known_hosts
#import time
#import logging
#import logging.handlers
#import syslog
#import json
#import pipes

#from datetime import datetime
#from pprint import pprint
#import importlib

import nixops.script_defs


def op_sos_console(args):
    depl = nixops.script_defs.open_deployment(args)
    m = depl.machines.get(args.machine)
    if not m: raise Exception("unknown machine ‘{0}’".format(args.machine))
    m.sos_console()

#def op_foo(args):
#    print('FOO')

#def op_bar(args):
#    print('BAR')

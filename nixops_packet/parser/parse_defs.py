#! /usr/bin/env python2
# -*- coding: utf-8 -*-

import nixops.script_defs


def op_sos_console(args):
    depl = nixops.script_defs.open_deployment(args)
    m = depl.machines.get(args.machine)
    if not m:
        raise Exception("unknown machine ‘{0}’".format(args.machine))
    m.op_sos_console()


def op_update_provision(args):
    depl = nixops.script_defs.open_deployment(args)
    m = depl.machines.get(args.machine)
    if not m:
        raise Exception("unknown machine ‘{0}’".format(args.machine))
    m.op_update_provSystem()


def op_reinstall(args):
    depl = nixops.script_defs.open_deployment(args)
    m = depl.machines.get(args.machine)
    if not m:
        raise Exception("unknown machine ‘{0}’".format(args.machine))
    m.op_reinstall()


# def op_foo(args):
#    print('FOO')

# def op_bar(args):
#    print('BAR')

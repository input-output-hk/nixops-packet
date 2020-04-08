#! /usr/bin/env python2
# -*- coding: utf-8 -*-

import nixops.script_defs
from nixops_packet.backends.device import PacketState
from typing import cast


def op_sos_console(args):
    with nixops.script_defs.deployment(args) as depl:
        m = depl.machines.get(args.machine)
        if not m:
            raise Exception("unknown machine ‘{0}’".format(args.machine))
        if not isinstance(m, PacketState):
            raise Exception(
                "machine is not a Packet device: ‘{0}’".format(args.machine)
            )
            cast(PacketState, m).op_sos_console()


def op_update_provision(args):
    with nixops.script_defs.deployment(args) as depl:
        m = depl.machines.get(args.machine)
        if not m:
            raise Exception("unknown machine ‘{0}’".format(args.machine))
        if not isinstance(m, PacketState):
            raise Exception(
                "machine is not a Packet device: ‘{0}’".format(args.machine)
            )
        cast(PacketState, m).op_update_provSystem()


def op_reinstall(args):
    with nixops.script_defs.deployment(args) as depl:
        m = depl.machines.get(args.machine)
        if not m:
            raise Exception("unknown machine ‘{0}’".format(args.machine))
        if not isinstance(m, PacketState):
            raise Exception(
                "machine is not a Packet device: ‘{0}’".format(args.machine)
            )
        cast(PacketState, m).op_reinstall()

import os.path
import nixops.plugins
import nixops.script_defs
import nixops_packet.parser
from argparse import ArgumentParser, _SubParsersAction
from typing import List


@nixops.plugins.hookimpl
def nixexprs() -> List[str]:
    return [os.path.dirname(os.path.abspath(__file__)) + "/nix"]


@nixops.plugins.hookimpl
def load() -> List[str]:
    return [
        "nixops_packet.resources",
        "nixops_packet.backends.device",
        "nixops_packet.resources.keypair",
        "nixops_packet.parser",
    ]


@nixops.plugins.hookimpl
def parser(parser: ArgumentParser, subparsers: _SubParsersAction) -> None:
    plugin_parser = subparsers.add_parser(
        "packet", help="run packet specific plugin commands"
    )
    plugin_cmd_subparsers = plugin_parser.add_subparsers(dest="type")
    plugin_command = nixops.script_defs.add_subparser(
        plugin_cmd_subparsers,
        "sos-console",
        help="connect to the machine's sos console",
    )
    plugin_command.set_defaults(op=nixops_packet.parser.parse_defs.op_sos_console)
    plugin_command.add_argument(
        "machine", metavar="MACHINE", help="identifier of the machine"
    )
    nixops.script_defs.add_common_deployment_options(plugin_command)

    plugin_command = nixops.script_defs.add_subparser(
        plugin_cmd_subparsers,
        "update-provision",
        help="pull an updated system.nix from a provisioned system",
    )
    plugin_command.set_defaults(op=nixops_packet.parser.parse_defs.op_update_provision)
    plugin_command.add_argument(
        "machine", metavar="MACHINE", help="identifier of the machine"
    )
    nixops.script_defs.add_common_deployment_options(plugin_command)

    plugin_command = nixops.script_defs.add_subparser(
        plugin_cmd_subparsers,
        "reinstall",
        help="deprovision, erase, and reinstall an already provisioned system",
    )
    plugin_command.set_defaults(op=nixops_packet.parser.parse_defs.op_reinstall)
    plugin_command.add_argument(
        "machine", metavar="MACHINE", help="identifier of the machine"
    )
    nixops.script_defs.add_common_deployment_options(plugin_command)

    return

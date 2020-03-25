import os.path
import nixops.plugins
import nixops.script_defs
import nixopspacket.parser


@nixops.plugins.hookimpl
def nixexprs():
    return [os.path.dirname(os.path.abspath(__file__)) + "/nix"]


@nixops.plugins.hookimpl
def load():
    return [
        "nixopspacket.resources",
        "nixopspacket.backends.device",
        "nixopspacket.resources.keypair",
        "nixopspacket.parser",
    ]


@nixops.plugins.hookimpl
def parser(parser, subparsers):
    plugin_parser = subparsers.add_parser(
        "packet", help="run packet specific plugin commands"
    )
    plugin_cmd_subparsers = plugin_parser.add_subparsers(dest="type")
    plugin_command = nixops.script_defs.add_subparser(
        plugin_cmd_subparsers,
        "sos-console",
        help="connect to the machine's sos console",
    )
    plugin_command.set_defaults(op=nixopspacket.parser.parse_defs.op_sos_console)
    plugin_command.add_argument(
        "machine", metavar="MACHINE", help="identifier of the machine"
    )
    nixops.script_defs.add_common_deployment_options(plugin_command)

    plugin_command = nixops.script_defs.add_subparser(
        plugin_cmd_subparsers,
        "update-provision",
        help="pull an updated system.nix from a provisioned system",
    )
    plugin_command.set_defaults(op=nixopspacket.parser.parse_defs.op_update_provision)
    plugin_command.add_argument(
        "machine", metavar="MACHINE", help="identifier of the machine"
    )
    nixops.script_defs.add_common_deployment_options(plugin_command)

    plugin_command = nixops.script_defs.add_subparser(
        plugin_cmd_subparsers,
        "reinstall",
        help="deprovision, erase, and reinstall an already provisioned system",
    )
    plugin_command.set_defaults(op=nixopspacket.parser.parse_defs.op_reinstall)
    plugin_command.add_argument(
        "machine", metavar="MACHINE", help="identifier of the machine"
    )
    nixops.script_defs.add_common_deployment_options(plugin_command)

    #    plugin_command = plugin_cmd_subparsers.add_parser('foo', help='execute command "foo"')
    #    plugin_command.set_defaults(op=nixopspacket.parser.parse_defs.op_foo)
    #    plugin_command.add_argument('--verbose', '-v', action='store_true', help='Provide extra foo information')
    #    plugin_command.add_argument('--debug', action='store_true', help='enable debug output')

    #    plugin_command = plugin_cmd_subparsers.add_parser('bar', help='execute command "bar"')
    #    plugin_command.set_defaults(op=nixopspacket.parser.parse_defs.op_bar)
    #    plugin_command.add_argument('--verbose', '-v', action='store_true', help='Provide extra bar information')
    #    plugin_command.add_argument('--debug', action='store_true', help='enable debug output')
    return

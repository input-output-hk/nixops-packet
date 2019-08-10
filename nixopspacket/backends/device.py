# -*- coding: utf-8 -*-
"""
A backend for packet.net.

"""
from __future__ import absolute_import
import os
import os.path
import time
import sys
import nixops.resources
from nixops.backends import MachineDefinition, MachineState
from nixops.nix_expr import Function, RawValue
import nixops.util
import nixops.known_hosts
import nixopspacket.utils as packet_utils
import nixopspacket.resources
import socket
import packet
from json import dumps
import getpass

class PacketDefinition(MachineDefinition):
    @classmethod
    def get_type(cls):
        return "packet"

    def __init__(self, xml, config):
        MachineDefinition.__init__(self, xml, config)
        self.access_key_id = config["packet"]["accessKeyId"]
        self.key_pair = config["packet"]["keyPair"]
        self.tags = config["packet"]["tags"]
        self.facility = config["packet"]["facility"]
        self.plan = config["packet"]["plan"]
        self.project = config["packet"]["project"]
        self.nixosVersion = config["packet"]["nixosVersion"]
        self.spotInstance = config["packet"]["spotInstance"]
        self.spotPriceMax = config["packet"]["spotPriceMax"]

    def show_type(self):
        return "packet [something]"


class PacketState(MachineState):
    @classmethod
    def get_type(cls):
        return "packet"

    state = nixops.util.attr_property("state", MachineState.MISSING, int)  # override
    accessKeyId = nixops.util.attr_property("packet.accessKeyId", None)
    key_pair = nixops.util.attr_property("packet.keyPair", None)
    plan = nixops.util.attr_property("packet.plan", None)
    public_ipv4 = nixops.util.attr_property("publicIpv4", None)
    public_ipv6 = nixops.util.attr_property("publicIpv6", None)
    private_ipv4 = nixops.util.attr_property("privateIpv4", None)
    default_gateway = nixops.util.attr_property("defaultGateway", None)
    private_gateway = nixops.util.attr_property("privateGateway", None)
    default_gatewayv6 = nixops.util.attr_property("defaultGatewayv6", None)
    public_cidr = nixops.util.attr_property("publicCidr", None, int)
    public_cidrv6 = nixops.util.attr_property("publicCidrv6", None, int)
    private_cidr = nixops.util.attr_property("privateCidr", None, int)

    def __init__(self, depl, name, id):
        MachineState.__init__(self, depl, name, id)
        self.name = name
        self._conn = None

    def get_ssh_name(self):
        retVal = None
        if not self.public_ipv4:
            raise Exception("Packet machine ‘{0}’ does not have a public IPv4 address (yet)".format(self.name))
        return self.public_ipv4

    @property
    def resource_id(self):
        return self.vm_id

    def connect(self):
        if self._conn: return self._conn
        if not self.accessKeyId:
            raise Exception("No API token is set, ensure packet.accessKeyId is set!")
        self._conn = packet_utils.connect(self.accessKeyId)
        return self._conn

    def get_ssh_private_key_file(self):
        if self._ssh_private_key_file: return self._ssh_private_key_file
        kp = self.findKeypairResource(self.key_pair)
        if kp:
            return self.write_ssh_private_key(kp.private_key)
        else:
            return None

    def get_ssh_flags(self, *args, **kwargs):
        file = self.get_ssh_private_key_file()
        super_flags = super(PacketState, self).get_ssh_flags(*args, **kwargs)
        return super_flags + (["-i", file] if file else []) + [ "-o", "StrictHostKeyChecking=accept-new" ]

    def get_sos_ssh_name(self):
        self.connect()
        instance = self._conn.get_device(self.vm_id)
        return "sos.{}.packet.net".format(instance.facility['code'])

    def sos_console(self):
        ssh = nixops.ssh_util.SSH(self.logger)
        ssh.register_flag_fun(self.get_ssh_flags)
        ssh.register_host_fun(self.get_sos_ssh_name)
        flags, command = ssh.split_openssh_args([])
        user = self.vm_id
        sys.exit(ssh.run_command(command, flags, check=False, logged=False,
                               allow_ssh_args=True, user=user))

    def get_physical_spec_from_plan(self, public_key):
        if self.plan == "c1.small.x86":
            return Function("{ ... }", {
                 ('config', 'boot', 'initrd', 'availableKernelModules'): [ "ata_piix", "uhci_hcd", "virtio_pci", "sr_mod", "virtio_blk" ],
                 ('config', 'boot', 'loader', 'grub', 'devices'): [ '/dev/sda', '/dev/sdb' ],
                 ('config', 'fileSystems', '/'): { 'label': 'nixos', 'fsType': 'ext4'},
                 ('config', 'users', 'users', 'root', 'openssh', 'authorizedKeys', 'keys'): [public_key],
                 ('config', 'networking', 'bonds', 'bond0', 'interfaces'): [ "enp1s0f0", "enp1s0f1"],
                 ('config', 'boot', 'kernelParams'): [ "console=ttyS1,115200n8" ],
                 ('config', 'boot', 'loader', 'grub', 'extraConfig'): """
                     serial --unit=0 --speed=115200 --word=8 --parity=no --stop=1
                     terminal_output serial console
                     terminal_input serial console
                 """,
                 ('config', 'networking', 'bonds', 'bond0', 'driverOptions'): {
                     "mode": "802.3ad",
                     "xmit_hash_policy": "layer3+4",
                     "lacp_rate": "fast",
                     "downdelay": "200",
                     "miimon": "100",
                     "updelay": "200",
                   },
                 ('config', 'networking', 'nameservers'): [ "8.8.8.8", "8.8.4.4" ], # TODO
                 ('config', 'networking', 'defaultGateway'): {
                     "address": self.default_gateway,
                     "interface": "bond0",
                 },
                 ('config', 'networking', 'defaultGateway6'): {
                     "address": self.default_gatewayv6,
                     "interface": "bond0",
                 },
                 ('config', 'networking', 'dhcpcd', 'enable'): False,
                 ('config', 'networking', 'interfaces', 'bond0'): {
                     "useDHCP": False,
                     "ipv4": {
                         "addresses": [
                             { "address": self.public_ipv4, "prefixLength": self.public_cidr },
                             { "address": self.private_ipv4, "prefixLength": self.private_cidr },
                         ],
                         "routes": [
                             {
                                 "address": "10.0.0.0",
                                 "prefixLength": 8,
                                 "via": self.private_gateway,
                             },
                         ],

                     },
                     "ipv6": {
                         "addresses": [
                             { "address": self.public_ipv6, "prefixLength": self.public_cidrv6 },
                         ],
                     },
                   },

            })
        elif self.plan == "c2.medium.x86":
            return Function("{ ... }", {
                 ('config', 'boot', 'initrd', 'availableKernelModules'): [ "xhci_pci", "ahci", "mpt3sas", "sd_mod" ],
                 ('config', 'boot', 'kernelModules'): [ "kvm-amd", "dm_multipath", "dm_round_robin", "ipmi_watchdog" ],
                 ('config', 'boot', 'kernelParams'): [ "console=ttyS1,115200n8" ],
                 ('config', 'boot', 'loader', 'efi', 'efiSysMountPoint'): "/boot/efi",
                 ('config', 'boot', 'loader', 'efi', 'canTouchEfiVariables'): False,
                 ('config', 'boot', 'loader', 'grub', 'enable'): True,
                 ('config', 'boot', 'loader', 'grub', 'version'): 2,
                 ('config', 'boot', 'loader', 'grub', 'efiSupport'): True,
                 ('config', 'boot', 'loader', 'grub', 'device'): "nodev",
                 ('config', 'boot', 'loader', 'grub', 'efiInstallAsRemovable'): True,
                 ('config', 'boot', 'loader', 'grub', 'extraConfig'): """
                     serial --unit=0 --speed=115200 --word=8 --parity=no --stop=1
                     terminal_output serial console
                     terminal_input serial console
                 """,
                 ('config', 'boot', 'loader', 'systemd-boot', 'enable'): False,
                 ('config', 'fileSystems', '/'): { "label": "nixos", "fsType": "ext4" },
                 ('config', 'fileSystems', '/boot/efi'): { "device": "/dev/sda1", "fsType": "vfat" },
                 ('config', 'hardware', 'enableAllFirmware'): True,
                 ('config', 'networking', 'bonds', 'bond0', 'interfaces'): [ "enp1s0f0", "enp1s0f1"],
                 ('config', 'networking', 'bonds', 'bond0', 'driverOptions'): {
                     "mode": "802.3ad",
                     "xmit_hash_policy": "layer3+4",
                     "lacp_rate": "fast",
                     "downdelay": "200",
                     "miimon": "100",
                     "updelay": "200",
                 },
                 ('config', 'networking', 'defaultGateway'): {
                     "address": self.default_gateway,
                     "interface": "bond0",
                 },
                 ('config', 'networking', 'defaultGateway6'): {
                     "address": self.default_gatewayv6,
                     "interface": "bond0",
                 },
                 ('config', 'networking', 'dhcpcd', 'enable'): False,
                 ('config', 'networking', 'interfaces', 'bond0'): {
                     "useDHCP": False,
                     "ipv4": {
                         "addresses": [
                             { "address": self.public_ipv4, "prefixLength": self.public_cidr },
                             { "address": self.private_ipv4, "prefixLength": self.private_cidr },
                         ],
                         "routes": [
                             {
                                 "address": "10.0.0.0",
                                 "prefixLength": 8,
                                 "via": self.private_gateway,
                             },
                         ],

                     },
                     "ipv6": {
                         "addresses": [
                             { "address": self.public_ipv6, "prefixLength": self.public_cidrv6 },
                         ],
                     },
                 },
                 ('config', 'networking', 'nameservers'): [ "8.8.8.8", "8.8.4.4" ], # TODO
                 ('config', 'nixpkgs', 'config', 'allowUnfree'): True,
                 ('config', 'swapDevices'): [ { "label": "swap" } ],
                 ('config', 'users', 'users', 'root', 'openssh', 'authorizedKeys', 'keys'): [public_key],
            })
        elif self.plan == "g2.large.x86":
            return Function("{ ... }", {
                 ('config', 'boot', 'initrd', 'availableKernelModules'): [ "ata_piix", "uhci_hcd", "virtio_pci", "sr_mod", "virtio_blk" ],
                 ('config', 'boot', 'loader', 'grub', 'devices'): [ '/dev/sda' ],
                 ('config', 'fileSystems', '/'): { 'label': 'nixos', 'fsType': 'ext4'},
                 ('config', 'users', 'users', 'root', 'openssh', 'authorizedKeys', 'keys'): [public_key],
                 ('config', 'networking', 'bonds', 'bond0', 'interfaces'): [ "enp96s0f0", "enp96s0f1"],
                 ('config', 'boot', 'kernelParams'): [ "console=ttyS1,115200n8" ],
                 ('config', 'boot', 'kernelModules'): [ 'kvm-intel' ],
                 ('config', 'boot', 'loader', 'grub', 'extraConfig'): """
                     serial --unit=0 --speed=115200 --word=8 --parity=no --stop=1
                     terminal_output serial console
                     terminal_input serial console
                 """,
                 ('config', 'networking', 'bonds', 'bond0', 'driverOptions'): {
                     "mode": "802.3ad",
                     "xmit_hash_policy": "layer3+4",
                     "lacp_rate": "fast",
                     "downdelay": "200",
                     "miimon": "100",
                     "updelay": "200",
                   },
                 ('config', 'networking', 'nameservers'): [ "8.8.8.8", "8.8.4.4" ], # TODO
                 ('config', 'networking', 'defaultGateway'): {
                     "address": self.default_gateway,
                     "interface": "bond0",
                 },
                 ('config', 'networking', 'defaultGateway6'): {
                     "address": self.default_gatewayv6,
                     "interface": "bond0",
                 },
                 ('config', 'networking', 'dhcpcd', 'enable'): False,
                 ('config', 'networking', 'interfaces', 'bond0'): {
                     "useDHCP": False,
                     "ipv4": {
                         "addresses": [
                             { "address": self.public_ipv4, "prefixLength": self.public_cidr },
                             { "address": self.private_ipv4, "prefixLength": self.private_cidr },
                         ],
                         "routes": [
                             {
                                 "address": "10.0.0.0",
                                 "prefixLength": 8,
                                 "via": self.private_gateway,
                             },
                         ],

                     },
                     "ipv6": {
                         "addresses": [
                             { "address": self.public_ipv6, "prefixLength": self.public_cidrv6 },
                         ],
                     },
                   },

            })
        else:
            raise Exception("Plan {} not supported by nixops".format(self.plan))

    def get_physical_spec(self):
        if self.key_pair == None and not self.dry_run:
            raise Exception("Key Pair is not set")
        kp = self.findKeypairResource(self.key_pair)
        if kp:
            public_key = kp.public_key
        else:
            public_key = "not set"
        return self.get_physical_spec_from_plan(public_key)


    def create_after(self, resources, defn):
        # make sure the ssh key exists before we do anything else
        return {
            r for r in resources if
            isinstance(r, nixopspacket.resources.keypair.PacketKeyPairState)
        }

    def get_api_key(self):
        apikey = os.environ.get('PACKET_API_KEY', self.apikey)
        if apikey == None:
            raise Exception("PACKET_API_KEY must be set in the environment to deploy instances")
        return apikey

    def get_common_tags(self):
        tags = {
                 "uuid": self.depl.uuid,
                 "name": self.name,
                 "ssh_url": "{0}@{1}:{2}".format(getpass.getuser(), socket.gethostname(), self.depl._db.db_file),
               }
        if self.depl.name:
            tags.update({ "deployment_name": self.depl.name})
        return tags


    def destroy(self, wipe=False):
        self.connect()
        if not self.depl.logger.confirm("are you sure you want to destroy Packet.Net machine ‘{0}’?".format(self.name)): return False
        self.log("destroying instance {}".format(self.vm_id))
        try:
            instance = self._conn.get_device(self.vm_id)
            instance.delete()
        except packet.baseapi.Error as e:
            if e.args[0] == "Error 422: Cannot delete a device while it is provisioning":
                self.state = self.packetstate2state(instance.state)
                raise e
            else:
                print e
                self.log("An error occurred destroying instance. Assuming it's been destroyed already.")
        self.public_ipv4 = None
        self.private_ipv4 = None
        self.vm_id = None
        self.state = MachineState.MISSING
        self.key_pair = None
        return True

    def create(self, defn, check, allow_reboot, allow_recreate):
        assert isinstance(defn, PacketDefinition)
        self.accessKeyId = defn.access_key_id
        self.connect()

        if self.state != self.UP:
            check = True

        self.set_common_state(defn)

        if self.vm_id and check:
            try:
                instance = self._conn.get_device(self.vm_id)
            except packet.baseapi.Error as e:
                if e.args[0] == "Error 404: Not found":
                    instance = None
                    self.vm_id = None
                    self.state = MachineState.MISSING
                else:
                    raise e

            if instance is None:
                if not allow_recreate:
                    raise Exception("Packet.net instance ‘{0}’ went away; use ‘--allow-recreate’ to create a new one".format(self.name))

            if instance:
                self.update_state(instance)

        if not self.vm_id:
            self.create_device(defn, check, allow_reboot, allow_recreate)

    def update_state(self, instance):
        self.state = self.packetstate2state(instance.state)
        addresses = instance.ip_addresses
        for address in addresses:
           if address["public"] and address["address_family"] == 4:
               self.public_ipv4 = address["address"]
               self.default_gateway = address["gateway"]
               self.public_cidr = address["cidr"]
           if address["public"] and address["address_family"] == 6:
               self.public_ipv6 = address["address"]
               self.default_gatewayv6 = address["gateway"]
               self.public_cidrv6 = address["cidr"]
           if  not address["public"] and address["address_family"] == 4:
               self.private_ipv4 = address["address"]
               self.private_gateway = address["gateway"]
               self.private_cidr = address["cidr"]

    def packetstate2state(self, packetstate):
        states = {
                "queued": MachineState.STARTING,
                "provisioning": MachineState.STARTING,
                "active": MachineState.UP,
                "powering_off": MachineState.STOPPING,
                "powering_on": MachineState.STARTING,
                "inactive": MachineState.STOPPED,
        }
        return states.get(packetstate)

    def findKeypairResource(self, key_pair_name):
        for r in self.depl.active_resources.itervalues():
            if isinstance(r, nixopspacket.resources.keypair.PacketKeyPairState) and \
                    r.state == nixopspacket.resources.keypair.PacketKeyPairState.UP and \
                    r.keypair_name == key_pair_name:
                return r
        return None

    def create_device(self, defn, check, allow_reboot, allow_recreate):

        self.connect()
        kp = self.findKeypairResource(defn.key_pair)
        common_tags = self.get_common_tags()
        tags = { }
        tags.update(defn.tags)
        tags.update(common_tags)
        self.log_start("creating packet device ...")
        self.log("project: '{0}'".format(defn.project))
        self.log("facility: {0}".format(defn.facility))
        self.log("keyid: {0}".format(kp.keypair_id))
        instance = self._conn.create_device(
            project_id=defn.project,
            hostname = "{0}.{1}".format(self.name, self.depl.description),
            plan=defn.plan,
            facility=[ defn.facility ],
            operating_system=defn.nixosVersion,
            user_ssh_keys=[],
            project_ssh_keys = [ kp.keypair_id ],
            spot_instance = defn.spotInstance,
            spot_price_max = defn.spotPriceMax,
            tags = packet_utils.dict2tags(tags)
        )

        self.vm_id = instance.id
        self.key_pair = defn.key_pair
        self.plan = defn.plan
        self.accessKeyId = defn.access_key_id
        self.log("instance id: " + self.vm_id)
        self.update_state(instance)

        self.log("instance is in {} state".format(instance.state))

        while True:
            instance = self._conn.get_device(self.vm_id)
            self.update_state(instance)
            if instance.state == "active": break
            if instance.state == "provisioning" and hasattr(instance, "provisioning_percentage") and instance.provisioning_percentage:
                self.log("instance is in {}, {}% done".format(instance.state, int(instance.provisioning_percentage)))
            else:
                self.log("instance is in {} state".format(instance.state))
            time.sleep(10)

        self.update_state(instance)
        nixops.known_hosts.remove(self.public_ipv4, None)

        self.log_end("{}".format(self.public_ipv4))
        self.wait_for_ssh()

    def switch_to_configuration(self, method, sync, command=None):
        res = super(PacketState, self).switch_to_configuration(method, sync, command)
        if res == 0:
            self._ssh_public_key_deployed = True
        return res


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
from nixops.nix_expr import Function, RawValue, nix2py
import nixops.util
import nixops.known_hosts
import nixopspacket.utils as packet_utils
import nixopspacket.resources
import socket
import packet
import json
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
        self.ipxe_script_url = config["packet"]["ipxeScriptUrl"]
        self.customData = config["packet"]["customData"]
        self.storage = config["packet"]["storage"]
        self.always_pxe = config["packet"]["alwaysPxe"]
        self.spotInstance = config["packet"]["spotInstance"]
        self.spotPriceMax = config["packet"]["spotPriceMax"]

        if config["packet"]["reservationId"] is None:
            self.reservationId = ""
        else:
            self.reservationId = config["packet"]["reservationId"]

        if self.ipxe_script_url != "":
            self.operating_system = "custom_ipxe"
        else:
            self.operating_system = self.nixosVersion

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
    provSystem = nixops.util.attr_property("packet.provSystem", None)
    metadata = nixops.util.attr_property("packet.metadata", None)
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
        # print(self.provSystem)

    def get_ssh_name(self):
        retVal = None
        if not self.public_ipv4:
            raise Exception(
                "Packet machine ‘{0}’ does not have a public IPv4 address (yet)".format(
                    self.name
                )
            )
        return self.public_ipv4

    @property
    def resource_id(self):
        return self.vm_id

    def connect(self):
        if self._conn:
            return self._conn
        if not self.accessKeyId:
            raise Exception("No API token is set, ensure packet.accessKeyId is set!")
        self._conn = packet_utils.connect(self.accessKeyId)
        return self._conn

    def get_ssh_private_key_file(self):
        if self._ssh_private_key_file:
            return self._ssh_private_key_file
        kp = self.findKeypairResource(self.key_pair)
        if kp:
            return self.write_ssh_private_key(kp.private_key)
        else:
            return None

    def get_ssh_flags(self, *args, **kwargs):
        file = self.get_ssh_private_key_file()
        super_flags = super(PacketState, self).get_ssh_flags(*args, **kwargs)
        return (
            super_flags
            + (["-i", file] if file else [])
            + ["-o", "StrictHostKeyChecking=accept-new"]
        )

    def get_sos_ssh_name(self):
        self.connect()
        instance = self._conn.get_device(self.vm_id)
        return "sos.{}.packet.net".format(instance.facility["code"])

    def op_sos_console(self):
        ssh = nixops.ssh_util.SSH(self.logger)
        ssh.register_flag_fun(self.get_ssh_flags)
        ssh.register_host_fun(self.get_sos_ssh_name)
        flags, command = ssh.split_openssh_args([])
        user = self.vm_id
        sys.exit(
            ssh.run_command(
                command,
                flags,
                check=False,
                logged=False,
                allow_ssh_args=True,
                user=user,
            )
        )

    def get_physical_spec_from_plan(self, public_key):
        return {
            "config": {
                ("users", "extraUsers", "root", "openssh", "authorizedKeys", "keys"): [
                    public_key
                ]
            },
            "imports": [nix2py(self.provSystem if self.provSystem else "{}")],
        }

    def get_physical_spec(self):
        if self.key_pair == None and self.plan != None:
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
            r
            for r in resources
            if isinstance(r, nixopspacket.resources.keypair.PacketKeyPairState)
        }

    def get_api_key(self):
        apikey = os.environ.get("PACKET_API_KEY", self.apikey)
        if apikey == None:
            raise Exception(
                "PACKET_API_KEY must be set in the environment to deploy instances"
            )
        return apikey

    def get_common_tags(self):
        tags = {
            "uuid": self.depl.uuid,
            "name": self.name,
            "ssh_url": "{0}@{1}:{2}".format(
                getpass.getuser(), socket.gethostname(), self.depl._db.db_file
            ),
        }
        if self.depl.name:
            tags.update({"deployment_name": self.depl.name})
        return tags

    def destroy(self, wipe=False):
        if self.plan != None:
            self.connect()
        if not self.depl.logger.confirm(
            "are you sure you want to destroy Packet.Net machine ‘{0}’?".format(
                self.name
            )
        ):
            return False
        self.log("destroying instance {}".format(self.vm_id))
        try:
            if self.vm_id != None:
                instance = self._conn.get_device(self.vm_id)
                instance.delete()
        except packet.baseapi.Error as e:
            if (
                e.args[0]
                == "Error 422: Cannot delete a device while it is provisioning"
            ):
                self.state = self.packetstate2state(instance.state)
                raise e
            else:
                print e
                self.log(
                    "An error occurred destroying instance. Assuming it's been destroyed already."
                )
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
                    raise Exception(
                        "Packet.net instance ‘{0}’ went away; use ‘--allow-recreate’ to create a new one".format(
                            self.name
                        )
                    )

            if instance:
                self.update_state(instance)

            ssh = nixops.ssh_util.SSH(self.logger)
            ssh.register_flag_fun(self.get_ssh_flags)
            ssh.register_host_fun(lambda: self.public_ipv4)
            if self.provSystem is None:
                self.update_provSystem(ssh, check)
            if self.metadata is None:
                self.update_metadata(ssh, check)

        if not self.vm_id:
            self.create_device(defn, check, allow_reboot, allow_recreate)

    def op_update_provSystem(self):
        ssh = nixops.ssh_util.SSH(self.logger)
        ssh.register_flag_fun(self.get_ssh_flags)
        ssh.register_host_fun(lambda: self.public_ipv4)
        self.update_provSystem(ssh, check=True)

    def update_provSystem(self, ssh, check):
        user = "root"
        command_provSystem = "cat /etc/nixos/packet/system.nix"
        flags, command = ssh.split_openssh_args([command_provSystem])
        provSystem = ssh.run_command(
            command,
            flags,
            check=check,
            logged=True,
            allow_ssh_args=True,
            user=user,
            capture_stdout=True,
        )
        self.provSystem = "\n".join(
            [
                line
                for line in provSystem.splitlines()
                if not line.lstrip().startswith("#")
            ]
        )
        self.log("System provisioning file captured: {}".format(self.provSystem))

    def update_metadata(self, ssh, check):
        user = "root"
        command_metadata = "curl -Ls https://metadata.packet.net/metadata"
        flags, command = ssh.split_openssh_args([command_metadata])
        metadata = ssh.run_command(
            command,
            flags,
            check=check,
            logged=True,
            allow_ssh_args=True,
            user=user,
            capture_stdout=True,
        )
        self.metadata = json.dumps(metadata)

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
            if not address["public"] and address["address_family"] == 4:
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
            if (
                isinstance(r, nixopspacket.resources.keypair.PacketKeyPairState)
                and r.state == nixopspacket.resources.keypair.PacketKeyPairState.UP
                and r.keypair_name == key_pair_name
            ):
                return r
        return None

    def create_device(self, defn, check, allow_reboot, allow_recreate):
        self.connect()
        kp = self.findKeypairResource(defn.key_pair)
        common_tags = self.get_common_tags()
        tags = {}
        tags.update(defn.tags)
        tags.update(common_tags)
        self.log_start("creating packet device ...")
        self.log("project: '{0}'".format(defn.project))
        self.log("facility: {0}".format(defn.facility))
        self.log("keyid: {0}".format(kp.keypair_id))
        instance = self._conn.create_device(
            project_id=defn.project,
            hostname="{0}".format(self.name),
            plan=defn.plan,
            facility=[defn.facility],
            operating_system=defn.operating_system,
            user_ssh_keys=[],
            project_ssh_keys=[kp.keypair_id],
            hardware_reservation_id=defn.reservationId,
            spot_instance=defn.spotInstance,
            storage=defn.storage,
            customdata=defn.customData,
            spot_price_max=defn.spotPriceMax,
            tags=packet_utils.dict2tags(tags),
            ipxe_script_url=defn.ipxe_script_url,
            always_pxe=defn.always_pxe,
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
            if instance.state == "active":
                break
            if (
                instance.state == "provisioning"
                and hasattr(instance, "provisioning_percentage")
                and instance.provisioning_percentage
            ):
                self.log(
                    "instance is in {}, {}% done".format(
                        instance.state, int(instance.provisioning_percentage)
                    )
                )
            else:
                self.log("instance is in {} state".format(instance.state))
            time.sleep(10)

        self.update_state(instance)
        nixops.known_hosts.remove(self.public_ipv4, None)

        self.log("{}".format(self.public_ipv4))
        self.wait_for_ssh()

        ssh = nixops.ssh_util.SSH(self.logger)
        ssh.register_flag_fun(self.get_ssh_flags)
        ssh.register_host_fun(lambda: self.public_ipv4)
        self.update_provSystem(ssh, check)
        self.update_metadata(ssh, check)
        self.update_state(instance)

    def switch_to_configuration(self, method, sync, command=None):
        res = super(PacketState, self).switch_to_configuration(method, sync, command)
        if res == 0:
            self._ssh_public_key_deployed = True
        return res

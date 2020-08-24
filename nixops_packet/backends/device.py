# -*- coding: utf-8 -*-
"""
A backend for packet.net.

"""

import os
import os.path
import time
import sys
import nixops.resources
from nixops.resources import ResourceOptions
from nixops.backends import MachineDefinition, MachineState, MachineOptions
from nixops.nix_expr import Function, RawValue, nix2py
import nixops.util
import nixops.known_hosts
import nixops_packet.utils as packet_utils
import nixops_packet.resources
import socket
import packet
import json
import getpass
from typing import cast, Dict, List, Optional, Any


class PacketMachineOptions(ResourceOptions):
    accessKeyId: Optional[str]
    keyPair: str
    # tags: List[str]
    facility: str
    plan: str
    project: str
    nixosVersion: str
    ipxeScriptUrl: Optional[str]
    customData: Any
    storage: Any
    alwaysPxe: Optional[bool]
    spotInstance: bool
    spotPriceMax: str
    reservationId: Optional[str]


class MyMachineOptions(MachineOptions):
    packet: PacketMachineOptions


class PacketDefinition(MachineDefinition):
    @classmethod
    def get_type(cls):
        return "packet"

    config: MyMachineOptions

    def __init__(self, name: str, config):
        super().__init__(name, config)
        if self.config.packet.accessKeyId is None:
            self.access_key_id = os.environ["PACKET_ACCESS_KEY"]
        else:
            self.access_key_id = self.config.packet.accessKeyId

        self.key_pair = self.config.packet.keyPair
        self.tags = self.config.packet.tags
        self.facility = self.config.packet.facility
        self.plan = self.config.packet.plan
        self.project = self.config.packet.project
        self.nixosVersion = self.config.packet.nixosVersion
        self.ipxe_script_url = self.config.packet.ipxeScriptUrl
        self.customData = self.config.packet.customData
        self.storage = self.config.packet.storage
        self.always_pxe = self.config.packet.alwaysPxe
        self.spotInstance = self.config.packet.spotInstance
        self.spotPriceMax = self.config.packet.spotPriceMax
        self.reservationId = self.config.packet.reservationId

        if self.ipxe_script_url != "":
            self.operating_system = "custom_ipxe"
        else:
            self.operating_system = self.nixosVersion

    def show_type(self):
        return "packet [something]"


class PacketState(MachineState[PacketDefinition]):
    @classmethod
    def get_type(cls):
        return "packet"

    state = nixops.util.attr_property("state", MachineState.MISSING, int)  # override
    accessKeyId: Optional[str] = nixops.util.attr_property("packet.accessKeyId", None)
    key_pair: Optional[str] = nixops.util.attr_property("packet.keyPair", None)
    nixos_version: Optional[str] = nixops.util.attr_property(
        "packet.nixosVersion", None
    )
    ipxe_script_url: Optional[str] = nixops.util.attr_property(
        "packet.ipxeScriptUrl", None
    )
    plan: Optional[str] = nixops.util.attr_property("packet.plan", None)
    provSystem: Optional[str] = nixops.util.attr_property("packet.provSystem", None)
    metadata: Optional[str] = nixops.util.attr_property("packet.metadata", None)
    public_ipv4: str = nixops.util.attr_property("publicIpv4", None)
    public_ipv6: Optional[str] = nixops.util.attr_property("publicIpv6", None)
    private_ipv4: Optional[str] = nixops.util.attr_property("privateIpv4", None)
    default_gateway: Optional[str] = nixops.util.attr_property("defaultGateway", None)
    private_gateway: Optional[str] = nixops.util.attr_property("privateGateway", None)
    default_gatewayv6: Optional[str] = nixops.util.attr_property(
        "defaultGatewayv6", None
    )
    public_cidr: Optional[str] = nixops.util.attr_property("publicCidr", None, int)
    public_cidrv6: Optional[str] = nixops.util.attr_property("publicCidrv6", None, int)
    private_cidr: Optional[str] = nixops.util.attr_property("privateCidr", None, int)

    def __init__(self, depl: nixops.deployment.Deployment, name: str, id):
        MachineState.__init__(self, depl, name, id)
        self.name = name
        self._conn = None
        # print(self.provSystem)

    def get_ssh_name(self) -> str:
        if not self.public_ipv4:
            raise Exception(
                "Packet machine ‘{0}’ does not have a public IPv4 address (yet)".format(
                    self.name
                )
            )
        return self.public_ipv4

    @property
    def resource_id(self) -> Optional[str]:
        return self.vm_id

    def connect(self):
        if self._conn:
            return self._conn
        if not self.accessKeyId:
            raise Exception("No API token is set, ensure packet.accessKeyId is set!")
        self._conn = packet_utils.connect(self.accessKeyId)
        return self._conn

    def get_ssh_private_key_file(self) -> Optional[str]:
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

    def get_sos_ssh_name(self) -> str:
        instance = self.connect().get_device(self.vm_id)
        return "sos.{}.packet.net".format(instance.facility["code"])

    def op_sos_console(self) -> None:
        ssh = nixops.ssh_util.SSH(self.logger)
        ssh.register_flag_fun(self.get_ssh_flags)
        ssh.register_host_fun(self.get_sos_ssh_name)
        flags, command = ssh.split_openssh_args([])
        assert self.vm_id is not None
        sys.exit(
            ssh.run_command(
                command, user=self.vm_id, check=False, logged=False, allow_ssh_args=True
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
            if isinstance(r, nixops_packet.resources.keypair.PacketKeyPairState)
        }

    def get_common_tags(self):
        tags: Dict[str, str] = {
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
                instance = self.connect().get_device(self.vm_id)
                instance.delete()
        except packet.baseapi.Error as e:
            if (
                e.args[0]
                == "Error 422: Cannot delete a device while it is provisioning"
            ):
                self.state = self.packetstate2state(instance.state)
                raise e
            else:
                print(e)
                self.log(
                    "An error occurred destroying instance. Assuming it's been destroyed already."
                )
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
                instance = self.connect().get_device(self.vm_id)
            except packet.baseapi.Error as e:
                if e.args[0] == "Error 404: Not found":
                    instance = None
                    self.vm_id = None
                    self.state = MachineState.MISSING
                    self.provSystem = None
                    self.metadata = None
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

        if not self.vm_id:
            self.create_device(defn, check, allow_reboot, allow_recreate)

        self.wait_for_ssh()

        if self.provSystem is None:
            self.update_provSystem()
        if self.metadata is None:
            self.update_metadata()

    def op_update_provSystem(self) -> None:
        self.update_provSystem()

    def update_provSystem(self) -> None:
        self.wait_for_ssh()

        provSystem = self.run_command(
            "cat /etc/nixos/packet/system.nix",
            check=True,
            logged=True,
            allow_ssh_args=True,
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

    def op_reinstall(self):
        """Instruct Packet to deprovision and reinstall NixOS."""
        self.connect()

        if self.vm_id is not None:
            instance = self.connect().get_device(self.vm_id)
            instance.reinstall()

        self.log_start("waiting for the machine to go down ...")
        self.wait_for_ssh()
        self.log_end("[down]")
        self._ssh_pinged_this_time = False
        self.ssh_pinged = False
        self.ssh.reset()
        # !!! nixops.known_hosts.remove(self.public_ipv4, None)

        self.wait_for_state("provisioning")
        self.wait_for_state("active")

        self.wait_for_ssh()
        self.log_end("[up]")

        self.update_state(instance)

        self.log("{}".format(self.public_ipv4))
        self.wait_for_ssh()

        self.update_provSystem()
        self.update_metadata()
        self.update_state(instance)

    def update_metadata(self) -> None:
        metadata: str = self.run_command(
            "curl -Ls https://metadata.packet.net/metadata",
            check=True,
            logged=True,
            allow_ssh_args=True,
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

    def findKeypairResource(
        self, key_pair_name
    ) -> Optional[nixops_packet.resources.keypair.PacketKeyPairState]:
        for r in self.depl.active_resources.values():
            if isinstance(r, nixops_packet.resources.keypair.PacketKeyPairState):
                key = cast(nixops_packet.resources.keypair.PacketKeyPairState, r)
                if (
                    key.keypair_name == key_pair_name
                    and key.state
                    == nixops_packet.resources.keypair.PacketKeyPairState.UP
                ):
                    return key

        return None

    def create_device(self, defn, check, allow_reboot, allow_recreate):
        self.connect()
        kp = self.findKeypairResource(defn.key_pair)
        assert kp is not None
        common_tags = self.get_common_tags()
        tags: Dict[str, str] = {}
        tags.update(defn.tags)
        tags.update(common_tags)
        self.log_start("creating packet device ...")
        self.log("project: '{0}'".format(defn.project))
        self.log("facility: {0}".format(defn.facility))
        self.log("keyid: {0}".format(kp.keypair_id))
        instance = self.connect().create_device(
            project_id=defn.project,
            hostname="{0}".format(self.name),
            plan=defn.plan,
            facility=[defn.facility],
            operating_system=defn.operating_system,
            user_ssh_keys=[],
            project_ssh_keys=[kp.keypair_id],
            hardware_reservation_id=defn.reservationId,
            spot_instance=defn.spotInstance,
            storage=None if defn.storage is None else json.dumps(defn.storage, sort_keys=True, cls=nixops.util.NixopsEncoder),
            customdata=None if defn.customData is None else json.dumps(defn.customData, sort_keys=True, cls=nixops.util.NixopsEncoder),
            spot_price_max=defn.spotPriceMax,
            tags=packet_utils.dict2tags(tags),
            ipxe_script_url=defn.ipxe_script_url,
            always_pxe=defn.always_pxe,
        )

        self.vm_id = instance.id
        assert self.vm_id is not None
        self.key_pair = defn.key_pair
        self.plan = defn.plan
        self.accessKeyId = defn.access_key_id
        self.log("instance id: " + self.vm_id)
        self.update_state(instance)

        self.log("instance is in {} state".format(instance.state))

        self.wait_for_state("active")

        self.update_state(instance)
        # !!! nixops.known_hosts.remove(self.public_ipv4, None)

        self.log("{}".format(self.public_ipv4))

        self._ssh_pinged_this_time = False
        self.ssh_pinged = False
        self.wait_for_ssh()
        self.update_provSystem()
        self.update_metadata()
        self.update_state(instance)

    def wait_for_state(self, target_state: str) -> None:
        self.log_start(
            "waiting for the machine to enter the state '{}'  ...".format(target_state)
        )
        while True:
            instance = self.connect().get_device(self.vm_id)
            self.update_state(instance)
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

            if instance.state == target_state:
                break
            else:
                time.sleep(10)

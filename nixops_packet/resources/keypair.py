# -*- coding: utf-8 -*-

# Automatic provisioning of packet key pairs.

import nixops.util
import nixops.resources
import nixops_packet.utils as packet_utils
import nixops_packet.backends.device
import packet
import os
from typing import cast, Optional


class PacketKeyPairOptions(nixops.resources.ResourceOptions):
    name: str
    accessKeyId: Optional[str]
    project: str


class PacketKeyPairDefinition(nixops.resources.ResourceDefinition):
    """Definition of a Packet.net key pair."""

    config: PacketKeyPairOptions

    @classmethod
    def get_type(cls) -> str:
        return "packet-keypair"

    @classmethod
    def get_resource_type(cls) -> str:
        return "packetKeyPairs"

    def __init__(self, name: str, config: nixops.resources.ResourceEval):
        super().__init__(name, config)
        self.keypair_name = self.config.name
        self.access_key_id = self.config.accessKeyId or None
        self.project = self.config.project


class PacketKeyPairState(nixops.resources.ResourceState[PacketKeyPairDefinition]):
    """State of a Packet.net key pair."""

    keypair_name: str = nixops.util.attr_property("packet.keyPairName", None)
    public_key: str = nixops.util.attr_property("publicKey", None)
    private_key: str = nixops.util.attr_property("privateKey", None)
    access_key_id: Optional[str] = nixops.util.attr_property("packet.accessKeyId", None)
    keypair_id: str = nixops.util.attr_property("packet.keyPairId", None)
    project: str = nixops.util.attr_property("packet.project", None)

    @classmethod
    def get_type(cls) -> str:
        return "packet-keypair"

    def __init__(self, depl: nixops.deployment.Deployment, name: str, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._conn = None

    @property
    def resource_id(self) -> str:
        return self.keypair_name

    def get_definition_prefix(self) -> str:
        return "resources.packetKeyPairs."

    def connect(self):
        if self._conn is None:
            self._conn = packet_utils.connect(self.access_key_id)

    def _connection(self):
        self.connect()
        return self._conn

    def create(
        self,
        defn: PacketKeyPairDefinition,
        check: bool,
        allow_reboot: bool,
        allow_recreate: bool,
    ) -> None:

        # TODO: Fix Me
        if defn.access_key_id == "":
            self.access_key_id = os.environ["PACKET_ACCESS_KEY"]
        else:
            self.access_key_id = defn.access_key_id
        self.project = defn.project
        if not self.access_key_id:
            raise Exception("please set ‘accessKeyId’, $PACKET_ACCESS_KEY")

        # Generate the key pair locally.
        if not self.public_key:
            (private, public) = nixops.util.create_key_pair(type="rsa")
            with self.depl._db:
                self.public_key = public
                self.private_key = private

        # Upload the public key to Packet.net.
        if check or self.state != self.UP:

            try:
                kp = self._connection().get_ssh_key(self.keypair_id)
            except packet.baseapi.Error as e:
                if e.args[0] == "Error 404: Not found":
                    kp = None
                else:
                    raise e

            # Don't re-upload the key if it exists and we're just checking.
            if not kp or self.state != self.UP:
                if kp:
                    kp.delete()
                self.log("uploading Packet key pair ‘{0}’...".format(defn.keypair_name))
                kp = self._connection().create_project_ssh_key(
                    self.project, defn.keypair_name, self.public_key
                )
                self.keypair_id = kp.id

            with self.depl._db:
                self.state = self.UP
                self.keypair_name = defn.keypair_name

    def destroy(self, wipe: bool = False) -> bool:
        def keypair_used() -> Optional[nixops_packet.backends.device.PacketState]:
            for m in self.depl.active_resources.values():
                if isinstance(m, nixops_packet.backends.device.PacketState):
                    device = cast(nixops_packet.backends.device.PacketState, m)
                    if device.key_pair == self.keypair_name:
                        return device
            return None

        m = keypair_used()
        if m:
            raise Exception(
                "keypair ‘{0}’ is still in use by ‘{1}’ ({2})".format(
                    self.keypair_name, m.name, m.vm_id
                )
            )

        if not self.depl.logger.confirm(
            "are you sure you want to destroy keypair ‘{0}’?".format(self.keypair_name)
        ):
            return False

        if self.state == self.UP:
            self.log("deleting Packet.net key pair ‘{0}’...".format(self.keypair_name))
            kp = self._connection().get_ssh_key(self.keypair_id)
            kp.delete()

        return True

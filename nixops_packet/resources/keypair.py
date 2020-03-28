# -*- coding: utf-8 -*-

# Automatic provisioning of packet key pairs.

import nixops.util
import nixops.resources
import nixops_packet.utils as packet_utils
import nixops_packet.backends.device
import packet
import os


class PacketKeyPairDefinition(nixops.resources.ResourceDefinition):
    """Definition of a Packet.net key pair."""

    @classmethod
    def get_type(cls):
        return "packet-keypair"

    @classmethod
    def get_resource_type(cls):
        return "packetKeyPairs"

    def __init__(self, xml):
        nixops.resources.ResourceDefinition.__init__(self, xml)
        self.keypair_name = xml.find("attrs/attr[@name='name']/string").get("value")
        self.access_key_id = xml.find("attrs/attr[@name='accessKeyId']/string").get(
            "value"
        )
        self.project = xml.find("attrs/attr[@name='project']/string").get("value")

    def show_type(self):
        return "{0} [something]".format(self.get_type())


class PacketKeyPairState(nixops.resources.ResourceState):
    """State of a Packet.net key pair."""

    state = nixops.util.attr_property(
        "state", nixops.resources.ResourceState.MISSING, int
    )
    keypair_name = nixops.util.attr_property("packet.keyPairName", None)
    public_key = nixops.util.attr_property("publicKey", None)
    private_key = nixops.util.attr_property("privateKey", None)
    access_key_id = nixops.util.attr_property("packet.accessKeyId", None)
    keypair_id = nixops.util.attr_property("packet.keyPairId", None)
    project = nixops.util.attr_property("packet.project", None)

    @classmethod
    def get_type(cls):
        return "packet-keypair"

    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._conn = None

    @property
    def resource_id(self):
        return self.keypair_name

    def get_definition_prefix(self):
        return "resources.packetKeyPairs."

    def connect(self):
        if self._conn:
            return
        self._conn = packet_utils.connect(self.access_key_id)

    def _connection(self):
        self.connect()
        return self._conn

    def create(self, defn, check, allow_reboot, allow_recreate):

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

    def destroy(self, wipe=False):
        def keypair_used():
            for m in self.depl.active_resources.values():
                if (
                    isinstance(m, nixops_packet.backends.device.PacketState)
                    and m.key_pair == self.keypair_name
                ):
                    return m
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

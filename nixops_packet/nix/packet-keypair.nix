{ config, lib, uuid, name, ... }:

with lib;

{

  options = {

    name = mkOption {
      default = "charon-${uuid}-${name}";
      type = types.str;
      description = "Name of the Packet key pair.";
    };


    accessKeyId = mkOption {
      default = "";
      type = types.str;
      description = "The Packet Access Key ID.";
    };

    project = mkOption {
      type = types.str;
      description = "UUID of a project (must match all devices using it)";
    };
  };

  config._type = "packet-keypair";

}

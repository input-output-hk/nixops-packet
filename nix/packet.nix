{ config, pkgs, lib, utils, ... }:

with utils;
with lib;
with import ./lib.nix lib;

let
  cfg = config.deployment.packet;
in
{
  ###### interface
  options = {
    deployment.packet = {
      accessKeyId = mkOption {
        example = "YOURAPIKEY";
        type = types.str;
        description = ''
          packet.net access key ID
        '';
      };
      facility = mkOption {
        example = "any";
        type = types.str;
        description = ''
          packet.net facility
        '';
      };
      keyPair = mkOption {
        example = "my-keypair";
        type = types.either types.str (resource "packet-keypair");
        apply = x: if builtins.isString x then x else x.name;
        description = ''
          Needs to be TODO of existing keypair or a resource created
          by nixops using `resources.packetKeyPairs.name`.
        '';
      };
      plan = mkOption {
        example = "c1.small.x86";
        type = types.str;
        description = ''
          the instance type to launch
        '';
      };
      project = mkOption {
        example = "something";
        type = types.str;
        description = ''
          the project the instance will be launched under
        '';
      };
      nixosVersion = mkOption {
        example = "nixos_19_09";
        default = "nixos_19_09";
        type = types.str;
        description = ''
          NixOS version to install
        '';
      };
      reservationId = mkOption {
        example = "next-available";
        default = null;
        type = types.nullOr types.str;
        description = "Reservation ID for using a reserved instance.";
      };
      spotInstance = mkOption {
        default = false;
        type = types.bool;
        description = ''
          Request a spot instance (WARNING: can be destroyed at any time based on demand)
        '';
      };
      spotPriceMax = mkOption {
        default = "-1.0";
        type = types.str;
        description = ''
          Price (in dollars per hour) to use for spot instances request for the machine.
        '';
      };
      ipxeScriptUrl = mkOption {
        example = "https://myhostingserver:8080/netboot.ipxe";
        default = "";
        type = types.str;
        description = "If using custom iPXE booting, the URL for the iPXE server and iPXE script";
      };
      alwaysPxe = mkOption {
        default = false;
        type = types.bool;
        description = "If using custom iPXE booting, whether to always use iPXE boot (true) or just iPXE boot on the first boot (false).";
      };
      tags = mkOption {
        default = { };
        example = { foo = "bar"; xyzzy = "bla"; };
        type = types.attrsOf types.str;
        # FIXME: size and count are probably wrong
        description = ''
          Tags assigned to the instance.  Each tag name can be at most
          128 characters, and each tag value can be at most 256
          characters.  There can be at most 10 tags.
        '';
      };
      customData = mkOption {
        default = null;
        type = types.nullOr types.attrs;
        description = ''
          customData passed to packet API (e.g. CPR partitioning instructions)
        '';
      };
      storage = mkOption {
        default = null;
        type = types.nullOr types.attrs;
        description = ''
          storage configuration for CPR provisioning (can only be used with hardware reservations)
        '';
      };
    };
  };

  config = mkIf (config.deployment.targetEnv == "packet") {
    nixpkgs.system = mkOverride 900 "x86_64-linux";
    services.openssh.enable = true;
  };
}

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
        # FIXME: describe this correctly
        description = ''
        '';
      };
      facility = mkOption {
        example = "something";
        type = types.str;
        # FIXME: describe this correctly
        description = ''
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
        example = "something";
        type = types.str;
        description = ''
        '';
      };
      project = mkOption {
        example = "something";
        type = types.str;
        description = ''
        '';
      };
      nixosVersion = mkOption {
        example = "nixos_18_03";
        default = "nixos_18_03";
        type = types.str;
        description = ''
          NixOS version to install
        '';
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
        type = types.string;
        description = ''
          Price (in dollars per hour) to use for spot instances request for the machine.
        '';
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
    };
  };

  config = mkIf (config.deployment.targetEnv == "packet") {
    nixpkgs.system = mkOverride 900 "x86_64-linux";
    services.openssh.enable = true;
  };
}

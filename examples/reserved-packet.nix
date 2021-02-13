let
  pkgs = import <nixpkgs> { };
  inherit (pkgs) lib;
  accessKeyId = (import ./packet-secret.nix).accessKeyId;
  projectId = (import ./packet-secret.nix).projectId;
in {
  network.description = "packetReservedDemo";
  resources.packetKeyPairs.keyReservedDemo = {
    inherit accessKeyId;
    project = projectId;
  };
  machineReservedDemo = { resources, config, pkgs, ... }: {
    deployment.packet = {
      inherit accessKeyId;
      keyPair = resources.packetKeyPairs.keyReservedDemo;
      facility = "any";
      plan = "c1.small.x86";
      reservationId = "next-available";
      project = projectId;
    };
    deployment.targetEnv = "packet";
  };
}

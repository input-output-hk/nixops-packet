let
  pkgs = import <nixpkgs> {};
  inherit (pkgs) lib;
  accessKeyId = (import ./packet-secret.nix).accessKeyId;
  projectId = (import ./packet-secret.nix).projectId;
in {
  network.description = "c1-res-test";
  resources.packetKeyPairs.c1-res-test = {
    inherit accessKeyId;
    project = projectId;
  };
  c1res = { resources, config, pkgs, ... }: {
    deployment.packet = {
      inherit accessKeyId;
      keyPair = resources.packetKeyPairs.c1-res-test;
      facility = "any";
      plan = "c1.small.x86";
      reservationId = "next-available";
      project = projectId;
    };
    deployment.targetEnv = "packet";
  };
}

{
  config_exporters = { optionalAttrs, ... }: [
    (config: { packet = optionalAttrs (config.deployment.targetEnv == "packet") config.deployment.packet; })
  ];
  options = [
    ./packet.nix
  ];
  resources = { evalResources, zipAttrs, resourcesByType, ... }: {
    packetKeyPairs = evalResources ./packet-keypair.nix (zipAttrs resourcesByType.packetKeyPairs or []);
  };
}

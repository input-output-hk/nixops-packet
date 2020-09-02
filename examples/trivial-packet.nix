let
  accessKeyId = "YOURAPIKEY";
  your-projid = "your-project-id-uuid";
in {
  network.description = "packetDemo";
  resources.packetKeyPairs.keyDemo = {
    inherit accessKeyId;
    project = your-projid;
  };
  machineDemo = { resources, ... }: {
    deployment.packet = {
      inherit accessKeyId;
      keyPair = resources.packetKeyPairs.keyDemo;
      facility = "ams1";
      plan = "c1.small.x86";
      project = your-projid;
    };
    deployment.targetEnv = "packet";
  };
}

let
  accessKeyId = "YOURAPIKEY";
  your-projid = "your-project-id-uuid";

in {
  network.description = "test-packet";
  resources.packetKeyPairs.dummy = {
    inherit accessKeyId;
    project = your-projid;
  };
  machine-sam = { resources, ... }: {
    deployment.packet = {
      inherit accessKeyId;
      keyPair = resources.packetKeyPairs.dummy;
      facility = "ams1";
      plan = "c1.small.x86";
      project = your-projid;
    };
    deployment.targetEnv = "packet";
  };
}

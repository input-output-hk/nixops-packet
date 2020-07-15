{ pkgs }:

self: super: {
  zipp = super.zipp.overridePythonAttrs (
    { propagatedBuildInputs ? [], ... }: {
      propagatedBuildInputs = propagatedBuildInputs ++ [
        self.toml
      ];
    }
  );

  packet-python = super.packet-python.overridePythonAttrs (
    { propagatedBuildInputs ? [], ... }: {
      buildInputs = propagatedBuildInputs ++ [
        self.pytest-runner
      ];
    }
  );

  nixops = super.nixops.overridePythonAttrs (
    { nativeBuildInputs ? [], ... }: {
      nativeBuildInputs = nativeBuildInputs ++ [ self.poetry ];
      format = "pyproject";
    }
  );
}

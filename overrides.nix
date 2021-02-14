{ pkgs }:

self: super: {
  nixops = super.nixops.overridePythonAttrs ({ nativeBuildInputs ? [ ], ... }: {
    nativeBuildInputs = nativeBuildInputs ++ [ self.poetry ];
    format = "pyproject";
  });

  packet-python = super.packet-python.overridePythonAttrs (old: {
    buildInputs = (old.propagatedBuildInputs or [ ]) ++ [ self.pytest-runner ];
    postPatch = ''
      substituteInPlace setup.py --replace 'setup_requires=["pytest-runner"],' ""
    '';
  });

  zip = super.zipp.overridePythonAttrs ({ propagatedBuildInputs ? [ ], ... }: {
    propagatedBuildInputs = propagatedBuildInputs ++ [ self.toml ];
  });
}

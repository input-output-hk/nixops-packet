{ nixopsSrc ? { outPath = ./.; revCount = 0; shortRev = "abcdef"; rev = "HEAD"; }
, officialRelease ? false
, nixpkgs ? <nixpkgs>
}:

let
  pkgs = import nixpkgs { };
  version = "1.6.1" + (if officialRelease then "" else "pre${toString nixopsSrc.revCount}_${nixopsSrc.shortRev}");
  packet = pkgs.python2Packages.packet-python.overrideAttrs (old: {
    src = pkgs.fetchFromGitHub {
      owner = "packethost";
      repo = "packet-python";
      rev = "v1.42.0";
      sha256 = "16nsq7bg9588cqiw3d7xqdps0lgv1s6dsjivawf3kjxnkz5ldliy";
    };
    patches = [];
    buildInputs = old.buildInputs ++ [ pkgs.python2Packages.pytestrunner ];
  });

in

rec {
  build = pkgs.lib.genAttrs [ "x86_64-linux" "i686-linux" "x86_64-darwin" ] (system:
    with import nixpkgs { inherit system; };

    python2Packages.buildPythonPackage rec {
      name = "nixops-packet-${version}";
      namePrefix = "";

      src = ./.;

      prePatch = ''
        for i in setup.py; do
          substituteInPlace $i --subst-var-by version ${version}
        done
      '';

      buildInputs = [ python2Packages.nose python2Packages.coverage ];

      propagatedBuildInputs = [
          packet
        ];

      postInstall =
        ''
          mkdir -p $out/share/nix/nixops-packet
          cp -av nix/* $out/share/nix/nixops-packet
        '';


      # For "nix-build --run-env".
      shellHook = ''
        export PYTHONPATH=$(pwd):$PYTHONPATH
        export PATH=$(pwd)/scripts:${openssh}/bin:$PATH
      '';

      doCheck = true;

    });

  }

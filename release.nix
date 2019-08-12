{ nixopsSrc ? { outPath = ./.; revCount = 0; shortRev = "abcdef"; rev = "HEAD"; }
, officialRelease ? false
, nixpkgs ? <nixpkgs>
}:

let
  pkgs = import nixpkgs { };
  version = "1.6.1" + (if officialRelease then "" else "pre${toString nixopsSrc.revCount}_${nixopsSrc.shortRev}");
  packet = pkgs.python2Packages.packet-python.overrideAttrs (old: {
    src = pkgs.fetchFromGitHub {
      owner = "input-output-hk";
      repo = "packet-python";
      rev = "6d3f64cf60166a3b863957b5b305fb671ec06390";
      sha256 = "1w9qyj13mcgldba197yb70ds88d7nfx0f46k503yl3j5by2pvqc4";
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

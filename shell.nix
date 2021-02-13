{ pkgs ? import ./nix { } }:
let
  overrides = import ./overrides.nix { inherit pkgs; };
  poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
    projectDir = ./.;
    overrides = pkgs.poetry2nix.overrides.withDefaults overrides;
  };
in pkgs.mkShell {
  buildInputs = with pkgs; [
    poetryEnv
    black
    mypy
    nixfmt
    poetry
    python3
    python3Packages.flake8
  ];
}

{ pkgs ? import ./nix { }, sources ? import ./nix/sources.nix }: {
  nixops-packet =
    pkgs.lib.genAttrs [ "x86_64-linux" "i686-linux" "x86_64-darwin" ] (system:
      let
        pkgs = import sources.nixpkgs { inherit system; };
        nixops-packet = import ./default.nix { };
      in nixops-packet);
}

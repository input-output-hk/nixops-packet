{ sources ? import ./sources.nix }:
with { overlay = self: super: { inherit (import sources.niv { }) niv; }; };
import sources.nixpkgs {
  overlays = [ overlay ];
  config = { };
}

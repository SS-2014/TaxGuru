{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.gcc
    pkgs.stdenv.cc.cc.lib
  ];
}

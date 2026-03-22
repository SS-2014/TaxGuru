{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.streamlit
    pkgs.gcc
    pkgs.stdenv.cc.cc.lib
  ];
}

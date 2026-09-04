#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: sudo ./uninstall.sh [OPTION]
  --all             remove every KeyFlip component (default)
  --gui-only        remove only the GTK GUI
  --extension-only  remove only the GNOME extension
  --core-only       remove only the shared core (front ends will stop working)
  -h, --help        show this help
EOF
}

remove_core=false
remove_gui=false
remove_extension=false
case ${1:---all} in
    --all) remove_core=true; remove_gui=true; remove_extension=true ;;
    --gui-only) remove_gui=true ;;
    --extension-only) remove_extension=true ;;
    --core-only) remove_core=true ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { usage >&2; exit 2; }

if [[ $EUID -ne 0 ]]; then
    echo "Run this uninstaller with sudo: sudo ./uninstall.sh [OPTION]" >&2
    exit 1
fi

if $remove_gui; then
    rm -f /usr/local/bin/keyflip
    rm -f /usr/local/share/applications/io.github.miflow13.KeyFlip.desktop
    rm -f /usr/local/share/icons/hicolor/512x512/apps/io.github.miflow13.KeyFlip.png
    rm -f /usr/local/share/metainfo/io.github.miflow13.KeyFlip.metainfo.xml
    rm -f /usr/libexec/keyflip/app.py /usr/libexec/keyflip/keyflip_app.py
fi
if $remove_extension; then
    rm -rf /usr/share/gnome-shell/extensions/keyflip@miflow13.github.io
fi
if $remove_core; then
    rm -f /usr/share/polkit-1/actions/io.github.miflow13.KeyFlip.policy
    rm -f /usr/libexec/keyflip/keyflip-helper
    rm -rf /usr/share/keyflip
fi
rmdir /usr/libexec/keyflip 2>/dev/null || true
echo "Requested KeyFlip components removed."

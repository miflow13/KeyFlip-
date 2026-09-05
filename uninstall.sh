#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: sudo ./uninstall.sh [OPTION]
Remove the full KeyFlip app, GNOME panel integration, and shared resources.
  --all       remove everything (default)
  -h, --help  show this help
EOF
}

case ${1:---all} in
    --all) ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { usage >&2; exit 2; }

if [[ $EUID -ne 0 ]]; then
    echo "Run this uninstaller with sudo: sudo ./uninstall.sh [OPTION]" >&2
    exit 1
fi

rm -f /usr/local/bin/keyflip
rm -f /usr/local/share/applications/io.github.miflow13.KeyFlip.desktop
rm -f /usr/local/share/icons/hicolor/512x512/apps/io.github.miflow13.KeyFlip.png
rm -f /usr/local/share/metainfo/io.github.miflow13.KeyFlip.metainfo.xml
rm -f /usr/libexec/keyflip/app.py /usr/libexec/keyflip/keyflip_app.py
rm -rf /usr/share/gnome-shell/extensions/keyflip@miflow13.github.io
rm -f /usr/share/glib-2.0/schemas/io.github.miflow13.KeyFlip.gschema.xml
glib-compile-schemas /usr/share/glib-2.0/schemas
rm -f /usr/share/polkit-1/actions/io.github.miflow13.KeyFlip.policy
rm -f /usr/libexec/keyflip/keyflip-helper
rm -rf /usr/share/keyflip
rmdir /usr/libexec/keyflip 2>/dev/null || true
echo "KeyFlip removed. Log out and back in to unload the panel integration."

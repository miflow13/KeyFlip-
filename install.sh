#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run this installer with sudo: sudo ./install.sh" >&2
    exit 1
fi

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install -d /usr/local/lib/keyflip /usr/local/bin
install -d /usr/local/share/applications /usr/local/share/icons/hicolor/512x512/apps
install -d /usr/local/share/metainfo
install -m 644 "$source_dir/app.py" /usr/local/lib/keyflip/app.py
install -m 644 "$source_dir/keyflip_app.py" /usr/local/lib/keyflip/keyflip_app.py
install -m 755 "$source_dir/keyflip-helper" /usr/local/lib/keyflip/keyflip-helper
install -m 755 "$source_dir/keyflip" /usr/local/bin/keyflip
install -m 644 "$source_dir/assets/keyflip.png" \
    /usr/local/share/icons/hicolor/512x512/apps/io.github.miflow13.KeyFlip.png
install -m 644 "$source_dir/packaging/io.github.miflow13.KeyFlip.desktop" \
    /usr/local/share/applications/io.github.miflow13.KeyFlip.desktop
install -m 644 "$source_dir/packaging/io.github.miflow13.KeyFlip.metainfo.xml" \
    /usr/local/share/metainfo/io.github.miflow13.KeyFlip.metainfo.xml

command -v update-desktop-database >/dev/null && \
    update-desktop-database /usr/local/share/applications || true
command -v gtk-update-icon-cache >/dev/null && \
    gtk-update-icon-cache -f -t /usr/local/share/icons/hicolor || true

echo "KeyFlip 0.1.0-beta installed. Open KeyFlip from the application menu."

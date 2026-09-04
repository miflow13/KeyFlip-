#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run this uninstaller with sudo: sudo ./uninstall.sh" >&2
    exit 1
fi

rm -f /usr/local/bin/keyflip
rm -f /usr/local/share/applications/io.github.miflow13.KeyFlip.desktop
rm -f /usr/local/share/icons/hicolor/512x512/apps/io.github.miflow13.KeyFlip.png
rm -f /usr/local/share/metainfo/io.github.miflow13.KeyFlip.metainfo.xml
rm -rf /usr/local/lib/keyflip
echo "KeyFlip removed."

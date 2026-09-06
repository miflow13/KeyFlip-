#!/usr/bin/env bash
set -euo pipefail

version=0.2.0-beta
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
bundle="$stage/keyflip-$version"
mkdir -p "$bundle/assets/sounds" "$bundle/packaging/systemd" "$bundle/gnome-extension" \
    "$bundle/helper" "$bundle/src/keyflip"

install -m 644 "$project_dir/app.py" "$bundle/app.py"
install -m 644 "$project_dir/src/keyflip/"*.py "$bundle/src/keyflip/"
install -m 644 "$project_dir/packaging/systemd/keyflip-recovery.service" "$bundle/packaging/systemd/"
install -m 644 "$project_dir/assets/sounds/cleaning-key.wav" "$bundle/assets/sounds/"
install -m 755 "$project_dir/keyflip" "$bundle/keyflip"
install -m 755 "$project_dir/helper/keyflip-helper" "$bundle/helper/keyflip-helper"
install -m 755 "$project_dir/install.sh" "$bundle/install.sh"
install -m 755 "$project_dir/uninstall.sh" "$bundle/uninstall.sh"
install -m 644 "$project_dir/README.md" "$bundle/README.md"
install -m 644 "$project_dir/CHANGELOG.md" "$bundle/CHANGELOG.md"
install -m 644 "$project_dir/LICENSE" "$bundle/LICENSE"
install -m 644 "$project_dir/assets/keyflip.png" "$bundle/assets/keyflip.png"
install -m 644 "$project_dir/assets/sounds/"*.ogg "$bundle/assets/sounds/"
install -m 644 "$project_dir/packaging/io.github.miflow13.KeyFlip.desktop" "$bundle/packaging/"
install -m 644 "$project_dir/packaging/io.github.miflow13.KeyFlip.metainfo.xml" "$bundle/packaging/"
install -m 644 "$project_dir/packaging/io.github.miflow13.KeyFlip.policy" "$bundle/packaging/"
install -m 644 "$project_dir/packaging/io.github.miflow13.KeyFlip.gschema.xml" "$bundle/packaging/"
install -m 644 "$project_dir/gnome-extension/extension.js" "$bundle/gnome-extension/"
install -m 644 "$project_dir/gnome-extension/metadata.json" "$bundle/gnome-extension/"
install -m 644 "$project_dir/gnome-extension/stylesheet.css" "$bundle/gnome-extension/"
install -m 644 "$project_dir/gnome-extension/"*.svg "$bundle/gnome-extension/"

mkdir -p "$project_dir/dist"
tar -C "$stage" -czf "$project_dir/dist/keyflip-$version.tar.gz" "keyflip-$version"
sha256sum "$project_dir/dist/keyflip-$version.tar.gz" > \
    "$project_dir/dist/keyflip-$version.tar.gz.sha256"
echo "Built dist/keyflip-$version.tar.gz"

#!/usr/bin/env bash
set -euo pipefail

version=0.1.0-beta
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
bundle="$stage/keyflip-$version"
mkdir -p "$bundle/assets" "$bundle/packaging"

install -m 644 "$project_dir/app.py" "$bundle/app.py"
install -m 644 "$project_dir/keyflip_app.py" "$bundle/keyflip_app.py"
install -m 755 "$project_dir/keyflip" "$bundle/keyflip"
install -m 755 "$project_dir/keyflip-helper" "$bundle/keyflip-helper"
install -m 755 "$project_dir/install.sh" "$bundle/install.sh"
install -m 755 "$project_dir/uninstall.sh" "$bundle/uninstall.sh"
install -m 644 "$project_dir/README.md" "$bundle/README.md"
install -m 644 "$project_dir/assets/keyflip.png" "$bundle/assets/keyflip.png"
install -m 644 "$project_dir/packaging/io.github.miflow13.KeyFlip.desktop" "$bundle/packaging/"
install -m 644 "$project_dir/packaging/io.github.miflow13.KeyFlip.metainfo.xml" "$bundle/packaging/"

mkdir -p "$project_dir/dist"
tar -C "$stage" -czf "$project_dir/dist/keyflip-$version.tar.gz" "keyflip-$version"
sha256sum "$project_dir/dist/keyflip-$version.tar.gz" > \
    "$project_dir/dist/keyflip-$version.tar.gz.sha256"
echo "Built dist/keyflip-$version.tar.gz"

#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: sudo ./install.sh [OPTION]

Install KeyFlip components. The shared core is always installed.
  --all             install the GTK GUI and GNOME extension (default)
  --gui-only        install the GTK GUI and shared core
  --extension-only  install the GNOME extension and shared core
  --core-only       install only the helper, policy, and sounds
  -h, --help        show this help
EOF
}

install_gui=false
install_extension=false
case ${1:---all} in
    --all) install_gui=true; install_extension=true ;;
    --gui-only) install_gui=true ;;
    --extension-only) install_extension=true ;;
    --core-only) ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { usage >&2; exit 2; }

if [[ $EUID -ne 0 ]]; then
    echo "Run this installer with sudo: sudo ./install.sh [OPTION]" >&2
    exit 1
fi

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

# Shared core
install -d /usr/libexec/keyflip /usr/share/keyflip/sounds
install -d /usr/share/polkit-1/actions
install -m 755 "$source_dir/keyflip-helper" /usr/libexec/keyflip/keyflip-helper
install -m 644 "$source_dir/assets/sounds/"*.ogg /usr/share/keyflip/sounds/
install -m 644 "$source_dir/packaging/io.github.miflow13.KeyFlip.policy" \
    /usr/share/polkit-1/actions/io.github.miflow13.KeyFlip.policy

if $install_gui; then
    install -d /usr/local/bin /usr/local/share/applications
    install -d /usr/local/share/icons/hicolor/512x512/apps /usr/local/share/metainfo
    install -m 644 "$source_dir/app.py" /usr/libexec/keyflip/app.py
    install -m 644 "$source_dir/keyflip_app.py" /usr/libexec/keyflip/keyflip_app.py
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
fi

if $install_extension; then
    extension_dir=/usr/share/gnome-shell/extensions/keyflip@miflow13.github.io
    install -d "$extension_dir"
    install -m 644 "$source_dir/gnome-extension/extension.js" "$extension_dir/extension.js"
    install -m 644 "$source_dir/gnome-extension/metadata.json" "$extension_dir/metadata.json"
    install -m 644 "$source_dir/gnome-extension/stylesheet.css" "$extension_dir/stylesheet.css"
    install -m 644 "$source_dir/gnome-extension/"*.svg "$extension_dir/"
fi

echo "KeyFlip 0.1.0-beta installed."
if $install_extension; then
    echo "Log out and back in once, then run: gnome-extensions enable keyflip@miflow13.github.io"
fi

Name:           keyflip
Version:        0.1.0
Release:        0.beta%{?dist}
Summary:        GTK interface for controlling a laptop internal keyboard
License:        LicenseRef-Proprietary
URL:            https://github.com/miflow13/KeyFlip-
Source0:        %{url}/archive/refs/tags/v0.1.0-beta.tar.gz#/keyflip-%{version}.tar.gz
BuildArch:      noarch

Requires:       keyflip-core = %{version}-%{release}
Requires:       python3
Requires:       python3-gobject
Requires:       gtk4

%description
KeyFlip provides a GTK 4 interface for enabling and disabling a supported
i8042/AT laptop keyboard while leaving external keyboards available.

%package core
Summary:        Shared helper and resources for KeyFlip
Requires:       polkit
Requires:       util-linux
Requires:       systemd
Requires:       libcanberra-gtk3

%description core
Privileged keyboard control helper, authorization policy, and shared sounds
used by the KeyFlip GTK application and GNOME Shell extension.

%package -n gnome-shell-extension-keyflip
Summary:        KeyFlip indicator for GNOME Shell
Requires:       keyflip-core = %{version}-%{release}
Requires:       gnome-shell

%description -n gnome-shell-extension-keyflip
GNOME Shell top-bar indicator for controlling a supported laptop internal
keyboard through the shared KeyFlip helper.

%prep
%autosetup -n KeyFlip--%{version}-beta
sed -i 's|Exec=/usr/local/bin/keyflip|Exec=keyflip|' \
    packaging/io.github.miflow13.KeyFlip.desktop

%build

%install
# Shared core
install -Dm755 keyflip-helper %{buildroot}%{_libexecdir}/keyflip/keyflip-helper
install -Dm644 packaging/io.github.miflow13.KeyFlip.policy \
    %{buildroot}%{_datadir}/polkit-1/actions/io.github.miflow13.KeyFlip.policy
install -Dm644 assets/sounds/toggle-on.ogg \
    %{buildroot}%{_datadir}/keyflip/sounds/toggle-on.ogg
install -Dm644 assets/sounds/toggle-off.ogg \
    %{buildroot}%{_datadir}/keyflip/sounds/toggle-off.ogg

# GTK GUI
install -Dm644 app.py %{buildroot}%{_libexecdir}/keyflip/app.py
install -Dm644 keyflip_app.py %{buildroot}%{_libexecdir}/keyflip/keyflip_app.py
install -Dm755 keyflip %{buildroot}%{_bindir}/keyflip
install -Dm644 assets/keyflip.png \
    %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/io.github.miflow13.KeyFlip.png
install -Dm644 packaging/io.github.miflow13.KeyFlip.desktop \
    %{buildroot}%{_datadir}/applications/io.github.miflow13.KeyFlip.desktop
install -Dm644 packaging/io.github.miflow13.KeyFlip.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/io.github.miflow13.KeyFlip.metainfo.xml

# GNOME Shell extension
extension_dir=%{buildroot}%{_datadir}/gnome-shell/extensions/keyflip@miflow13.github.io
install -d "$extension_dir"
install -m644 gnome-extension/extension.js gnome-extension/metadata.json \
    gnome-extension/stylesheet.css gnome-extension/*.svg "$extension_dir/"

%files
%doc README.md
%{_bindir}/keyflip
%{_libexecdir}/keyflip/app.py
%{_libexecdir}/keyflip/keyflip_app.py
%{_datadir}/applications/io.github.miflow13.KeyFlip.desktop
%{_datadir}/icons/hicolor/512x512/apps/io.github.miflow13.KeyFlip.png
%{_datadir}/metainfo/io.github.miflow13.KeyFlip.metainfo.xml

%files core
%{_libexecdir}/keyflip/keyflip-helper
%{_datadir}/keyflip/
%{_datadir}/polkit-1/actions/io.github.miflow13.KeyFlip.policy

%files -n gnome-shell-extension-keyflip
%{_datadir}/gnome-shell/extensions/keyflip@miflow13.github.io/

%changelog
* Fri Sep 04 2026 Miflow13 <pizzafan513@gmail.com> - 0.1.0-0.beta
- Split the shared core, GTK GUI, and GNOME Shell extension packages

Name:           keyflip
Version:        0.2.0
Release:        0.beta%{?dist}
Summary:        Laptop keyboard modes with a GTK app and GNOME panel controls
License:        MIT
URL:            https://github.com/miflow13/KeyFlip-
Source0:        keyflip-%{version}-beta.tar.gz
BuildArch:      noarch
BuildRequires:  systemd-rpm-macros

Requires:       python3
Requires:       python3-gobject
Requires:       python3-evdev
Requires:       gtk4
Requires:       polkit
Requires:       util-linux
Requires:       systemd
Requires:       libcanberra-gtk3
Requires:       glib2
Requires:       gnome-shell
Obsoletes:      keyflip-core <= %{version}-%{release}
Obsoletes:      gnome-shell-extension-keyflip <= %{version}-%{release}

%description
KeyFlip combines a GTK 4 application, GNOME Shell panel controls, a global
shortcut, and automatic mode switching in one package for supported i8042/AT
laptop keyboards.

%prep
%autosetup -n keyflip-%{version}-beta
sed -i 's|Exec=/usr/local/bin/keyflip|Exec=keyflip|' \
    packaging/io.github.miflow13.KeyFlip.desktop

%build

%install
# Shared core
install -Dm755 helper/keyflip-helper %{buildroot}%{_libexecdir}/keyflip/keyflip-helper
install -Dm644 packaging/io.github.miflow13.KeyFlip.policy \
    %{buildroot}%{_datadir}/polkit-1/actions/io.github.miflow13.KeyFlip.policy
install -Dm644 packaging/io.github.miflow13.KeyFlip.gschema.xml \
    %{buildroot}%{_datadir}/glib-2.0/schemas/io.github.miflow13.KeyFlip.gschema.xml
install -Dm644 assets/sounds/toggle-on.ogg \
    %{buildroot}%{_datadir}/keyflip/sounds/toggle-on.ogg
install -Dm644 assets/sounds/toggle-off.ogg \
    %{buildroot}%{_datadir}/keyflip/sounds/toggle-off.ogg

# GTK GUI
install -Dm644 app.py %{buildroot}%{_libexecdir}/keyflip/app.py
for module in __init__ application window state cleaning recovery sound; do
    install -Dm644 "src/keyflip/$module.py" "%{buildroot}%{_libexecdir}/keyflip/keyflip/$module.py"
done
install -Dm644 packaging/systemd/keyflip-recovery.service %{buildroot}%{_unitdir}/keyflip-recovery.service
install -Dm644 assets/sounds/cleaning-key.wav %{buildroot}%{_datadir}/keyflip/sounds/cleaning-key.wav
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

%post
%systemd_post keyflip-recovery.service

%preun
%systemd_preun keyflip-recovery.service

%postun
%systemd_postun keyflip-recovery.service

%files
%license LICENSE
%doc README.md CHANGELOG.md
%{_bindir}/keyflip
%{_libexecdir}/keyflip/app.py
%{_libexecdir}/keyflip/keyflip/
%{_unitdir}/keyflip-recovery.service
%{_datadir}/applications/io.github.miflow13.KeyFlip.desktop
%{_datadir}/icons/hicolor/512x512/apps/io.github.miflow13.KeyFlip.png
%{_datadir}/metainfo/io.github.miflow13.KeyFlip.metainfo.xml

%{_libexecdir}/keyflip/keyflip-helper
%{_datadir}/keyflip/
%{_datadir}/polkit-1/actions/io.github.miflow13.KeyFlip.policy
%{_datadir}/glib-2.0/schemas/io.github.miflow13.KeyFlip.gschema.xml

%{_datadir}/gnome-shell/extensions/keyflip@miflow13.github.io/

%changelog
* Sat Sep 05 2026 Miflow13 <pizzafan513@gmail.com> - 0.2.0-0.beta
- Bundle the GTK app, GNOME panel integration, and shared resources as KeyFlip

* Fri Sep 04 2026 Miflow13 <pizzafan513@gmail.com> - 0.1.0-0.beta
- Split the shared core, GTK GUI, and GNOME Shell extension packages

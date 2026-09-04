Name:           keyflip
Version:        0.1.0
Release:        0.beta%{?dist}
Summary:        Toggle a supported laptop internal keyboard
License:        LicenseRef-Proprietary
URL:            https://github.com/miflow13/KeyFlip-
Source0:        %{url}/archive/refs/tags/v0.1.0-beta.tar.gz#/keyflip-%{version}.tar.gz
BuildArch:      noarch

Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       polkit
Requires:       util-linux
Requires:       systemd
Requires:       libcanberra-gtk3

%description
KeyFlip provides a GTK 4 interface for enabling and disabling a supported
i8042/AT laptop keyboard while leaving external keyboards available.

%prep
%autosetup -n KeyFlip--%{version}-beta
sed -i 's|/usr/local/lib/keyflip/app.py|%{_libexecdir}/keyflip/app.py|' keyflip
sed -i 's|Exec=/usr/local/bin/keyflip|Exec=keyflip|' \
    packaging/io.github.miflow13.KeyFlip.desktop

%build

%install
install -Dm644 app.py %{buildroot}%{_libexecdir}/keyflip/app.py
install -Dm644 keyflip_app.py %{buildroot}%{_libexecdir}/keyflip/keyflip_app.py
install -Dm755 keyflip-helper %{buildroot}%{_libexecdir}/keyflip/keyflip-helper
install -Dm755 keyflip %{buildroot}%{_bindir}/keyflip
install -Dm644 assets/keyflip.png \
    %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/io.github.miflow13.KeyFlip.png
install -Dm644 packaging/io.github.miflow13.KeyFlip.desktop \
    %{buildroot}%{_datadir}/applications/io.github.miflow13.KeyFlip.desktop
install -Dm644 packaging/io.github.miflow13.KeyFlip.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/io.github.miflow13.KeyFlip.metainfo.xml

%files
%doc README.md
%{_bindir}/keyflip
%{_libexecdir}/keyflip/
%{_datadir}/applications/io.github.miflow13.KeyFlip.desktop
%{_datadir}/icons/hicolor/512x512/apps/io.github.miflow13.KeyFlip.png
%{_datadir}/metainfo/io.github.miflow13.KeyFlip.metainfo.xml

%changelog
* Fri Sep 04 2026 Miflow13 <pizzafan513@gmail.com> - 0.1.0-0.beta
- Initial beta package

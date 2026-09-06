# Changelog

All notable changes to KeyFlip are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Cleaning Mode for temporarily suppressing keyboard input while retaining
  mouse and trackpad input, including automatic timeout and early termination.
- Root-owned recovery that restores Laptop Mode when KeyFlip front ends exit or
  the computer suspends.
- Event-driven keyboard-state monitoring with a periodic safety fallback.
- Tests for Cleaning Mode, recovery, state classification, GNOME panel
  automation, packaging layout, and command-line behavior.
- A real-hardware validation checklist.

### Changed

- Organized Python code as the `src/keyflip` package, separating GTK lifecycle,
  window presentation, state monitoring, cleaning, recovery, and sound duties.
- Moved the helper source to `helper/keyflip-helper` while preserving its
  Polkit-authorized installed path at `/usr/libexec/keyflip/keyflip-helper`.
- Moved the recovery unit to `packaging/systemd` and aligned the manual, Arch,
  RPM, and release installation layouts.
- Extended `make check` to validate every Python module and run GNOME panel
  tests.
- Updated project documentation and branding.

### Security

- Desk Mode now arms independent recovery before disabling the internal
  keyboard.
- Keyboard mutations and Cleaning Mode share a lock to prevent unsafe races.
- Recovery validates the i8042 port and `atkbd` driver before writing to sysfs.

## [0.2.0-beta] - 2026-09-04

### Added

- Laptop Mode and Desk Mode presets.
- GTK 4 application and GNOME Shell panel controls in one package.
- Global mode-toggle shortcut.
- Automatic switching when USB or Bluetooth keyboards connect or disconnect.
- External-keyboard warnings before manual internal-keyboard disablement.
- Arch and RPM packaging.

### Changed

- Redesigned the GTK interface around input-mode cards.
- Kept GTK and panel state synchronized with actual keyboard state.
- Hardened automatic switching and tray command forwarding.

## [0.1.0-beta] - 2026-09-04

### Added

- Initial beta release for safely enabling and disabling one supported
  i8042/AT internal keyboard.
- Polkit-authorized helper, GTK interface, manual installer, and uninstaller.

[Unreleased]: https://github.com/miflow13/KeyFlip/compare/v0.2.0-beta...HEAD
[0.2.0-beta]: https://github.com/miflow13/KeyFlip/compare/v0.1.0-beta...v0.2.0-beta
[0.1.0-beta]: https://github.com/miflow13/KeyFlip/releases/tag/v0.1.0-beta

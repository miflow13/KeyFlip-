<img width="800" height="450" alt="KeyFlip demo" src="https://github.com/user-attachments/assets/4f224ba1-1f8a-47b8-b3d8-36cad5cf97ed" />


**KeyFlip** is a GNOME app with built-in panel controls for enabling or disabling a supported laptop's internal keyboard.

Useful when you're using an external keyboard and want to avoid accidental input from the built-in one.


## Features

- Toggle the internal laptop keyboard on or off
- Press **Super + Shift + K** to switch between Laptop Mode and Desk Mode
  globally while the GNOME extension is enabled, even with the app closed
- Optionally disable it when a USB or Bluetooth keyboard connects, then
  re-enable it when the last external keyboard disconnects
- Warn before manual disabling when no external keyboard is detected
- Works on **Wayland** and **X11**
- Does not affect external USB keyboards
- Does not affect Bluetooth keyboards
- One install includes the full app, panel menu, and global shortcut
- Open the full app directly from the panel menu

  ## Screenshots
<img width="1920" height="1080" alt="Screenshot From 2026-09-04 19-30-01" src="https://github.com/user-attachments/assets/f43d125f-4547-4a41-83c9-76d11ffc778d" />
<img width="1920" height="1080" alt="Screenshot From 2026-09-04 19-29-57" src="https://github.com/user-attachments/assets/f9233967-490a-4506-992e-ba2315ce6e88" />



## Requirements

Currently built and tested for:

- Fedora Linux
- GNOME
- Python 3
- GTK 4 / `python3-gobject`
- `polkit`
- `util-linux`
- `systemd`
- Standard **i8042/AT internal keyboards**

### Supported

- ✅ i8042/AT internal keyboards
- ✅ Wayland
- ✅ X11
- ✅ USB keyboards remain enabled
- ✅ Bluetooth keyboards remain enabled

### Not currently supported

- ❌ Internal USB keyboards
- ❌ Internal I2C keyboards

## Install

Download and extract:

`keyflip-0.2.0-beta.tar.gz`

Open a terminal inside the extracted folder and run:

```bash
sudo ./install.sh
```

This installs the complete KeyFlip experience: the full GTK app, GNOME panel
menu, global shortcut, and keyboard-control helper. There are no separate
GUI-only, extension-only, or core-only editions.

Log out and back in after installing or updating. On first install, enable
KeyFlip's panel integration:

```bash
gnome-extensions enable keyflip@miflow13.github.io
```

Launch **KeyFlip** from your applications, or click its keyboard icon in the
panel and choose **Open KeyFlip**. The panel menu shows the active mode and
lets you select **Laptop Mode** or **Desk Mode**. Use the full app to configure
automatic mode switching. Panel controls, automatic switching, and the global
shortcut continue working when the app window is closed, while the GNOME
extension is enabled.

The included extension targets **GNOME Shell 50**. On unsupported keyboard
hardware, the menu shows **Keyboard unavailable**, but **Open KeyFlip** remains
available for viewing the details.

To remove a manual installation:

```bash
sudo ./uninstall.sh
```

Distribution packaging also produces one `keyflip` package containing all
components, replacing the former `keyflip-core` and
`gnome-shell-extension-keyflip` packages. Use your package manager to remove a
package-managed installation.

## Global keyboard shortcut

With the GNOME extension enabled, **Super + Shift + K** toggles modes from
any application or the Activities overview. Holding the keys does not repeatedly
toggle. The usual authorization and no-external-keyboard confirmation still apply.
In Desk Mode, use an external keyboard for the shortcut, since the internal
keyboard is disabled. You can also restore Laptop Mode from the panel menu.

The binding is stored in GSettings for a future shortcut preferences UI. To
change it now, for example:

```bash
gsettings set io.github.miflow13.KeyFlip toggle-mode-shortcut "['<Super><Shift>j']"
```

Changes apply immediately. Set it to `"[]"` to disable the shortcut, or restore
the default with:

```bash
gsettings reset io.github.miflow13.KeyFlip toggle-mode-shortcut
```

After updating, reinstall KeyFlip (`sudo ./install.sh`) and log out and back in.

## Building packages

Run `make package` to validate the sources and create
`dist/keyflip-0.2.0-beta.tar.gz`. The Arch and RPM recipes use this local archive,
so they package the combined app from the current source instead of an older
upstream tag. For Arch, copy the archive beside `packaging/arch/PKGBUILD` and
refresh its checksum with `updpkgsums` before running `makepkg`. For RPM, place
it in your RPM `SOURCES` directory and build `packaging/obs/keyflip.spec`.

## AI-assisted development

KeyFlip was developed with help from AI tools for coding, debugging, documentation, and learning.

I review, test, modify, and take responsibility for everything released in this project.

## Status

**Version:** `0.2.0-beta`

KeyFlip is still in active development. Bug reports and feedback are welcome.

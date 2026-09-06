<p align="center">
  <img src="./assets/keyflip-logo.png" alt="KeyFlip logo" width="600" />
</p>

# KeyFlip

[![Copr build status](https://copr.fedorainfracloud.org/coprs/mikachu/keyflip/package/keyflip/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/mikachu/keyflip/package/keyflip/)

**KeyFlip is a GNOME utility for safely enabling and disabling your laptop's built-in keyboard.**

Useful when you're using an external keyboard, covering your laptop keyboard, or cleaning your keyboard without accidental input.

KeyFlip includes a GTK 4 app, GNOME panel controls, automatic external-keyboard detection, Cleaning Mode, and a global keyboard shortcut.

## Quick install

### Fedora

```bash
sudo dnf copr enable mikachu/keyflip
sudo dnf install keyflip
````

Then launch **KeyFlip** from your applications menu or run:

```bash
keyflip
```

Log out and back in after the first installation if the GNOME panel integration does not appear.

Enable the extension manually if needed:

```bash
gnome-extensions enable keyflip@miflow13.github.io
```

## Features

* 💻 **Laptop Mode** — keeps the internal keyboard enabled
* ⌨️ **Desk Mode** — disables the internal keyboard while leaving external keyboards available
* 🧹 **Cleaning Mode** — blocks keyboard input for 60 seconds while keeping your mouse or trackpad usable
* ⚡ **Super + Shift + K** — quickly switch between Laptop Mode and Desk Mode
* 🔌 **Automatic switching** — optionally enter Desk Mode when a USB or Bluetooth keyboard connects
* 🛡️ **Safety checks** — warns before disabling the internal keyboard when no external keyboard is detected
* 🖥️ Built-in GNOME panel controls
* 🪟 Works on Wayland and X11
* 🎛️ Open the full KeyFlip app directly from the panel

Panel controls, automatic switching, and the global shortcut continue working while the KeyFlip app window is closed.

## Screenshots

<img
width="1920"
alt="KeyFlip main window"
src="https://github.com/user-attachments/assets/f43d125f-4547-4a41-83c9-76d11ffc778d"
/>

<img
width="1920"
alt="KeyFlip settings"
src="https://github.com/user-attachments/assets/f9233967-490a-4506-992e-ba2315ce6e88"
/>

## Compatibility

KeyFlip is currently developed and tested primarily on **Fedora + GNOME**.

| Feature                       | Support             |
| ----------------------------- | ------------------- |
| Fedora                        | ✅                   |
| GNOME                         | ✅                   |
| Wayland                       | ✅                   |
| X11                           | ✅                   |
| i8042 / AT internal keyboards | ✅                   |
| External USB keyboards        | ✅ Remain enabled    |
| Bluetooth keyboards           | ✅ Remain enabled    |
| Internal USB keyboards        | ❌ Not yet supported |
| Internal I2C keyboards        | ❌ Not yet supported |

The included GNOME extension currently targets **GNOME Shell 50**.

KeyFlip requires:

* Python 3
* GTK 4 / `python3-gobject`
* `polkit`
* `util-linux`
* `systemd`
* `python3-evdev` on Fedora or `python-evdev` on Arch for Cleaning Mode

## How the modes work

### Laptop Mode

Your built-in laptop keyboard works normally.

Use this when using the laptop by itself.

### Desk Mode

KeyFlip disables the supported internal laptop keyboard while leaving USB and Bluetooth keyboards available.

This is useful when your laptop is being used more like a desktop or when an external keyboard is placed over or near the built-in keyboard.

### Cleaning Mode

Cleaning Mode temporarily blocks keyboard input for **60 seconds** so you can clean your keyboard without triggering shortcuts or typing accidentally.

Your mouse and trackpad remain usable, and you can select **End Cleaning** at any time.

Keyboard input automatically returns after the timer ends.

<details>
<summary>Cleaning Mode technical details</summary>

Release any held keys before starting Cleaning Mode.

Cleaning temporarily pauses panel controls and automatic mode switching while preserving your previous Laptop/Desk Mode.

If the internal keyboard was disabled before cleaning, it remains disabled afterward.

For devices that combine keyboard and pointer input on one event endpoint, KeyFlip attempts to filter keyboard events while forwarding pointer input.

If this cannot be configured safely, Cleaning Mode stops instead of leaving only part of the keyboard set blocked.

New input devices are checked approximately every 100 ms during cleaning.

</details>

## Automatic external-keyboard detection

KeyFlip can automatically switch to Desk Mode when a USB or Bluetooth keyboard connects.

When the last external keyboard disconnects, KeyFlip can return to Laptop Mode.

Automatic switching can be configured from the full KeyFlip application.

## Global shortcut

With the GNOME extension enabled:

```text
Super + Shift + K
```

switches between Laptop Mode and Desk Mode from anywhere in GNOME.

In Desk Mode, use an external keyboard for the shortcut because the internal keyboard is disabled.

You can also restore Laptop Mode from the GNOME panel.

### Change the shortcut

For example:

```bash
gsettings set io.github.miflow13.KeyFlip toggle-mode-shortcut "['<Super><Shift>j']"
```

Disable the shortcut:

```bash
gsettings set io.github.miflow13.KeyFlip toggle-mode-shortcut "[]"
```

Restore the default:

```bash
gsettings reset io.github.miflow13.KeyFlip toggle-mode-shortcut
```

Changes apply immediately.

## Manual installation

Download and extract:

```text
keyflip-0.2.0-beta.tar.gz
```

Open a terminal inside the extracted directory and run:

```bash
sudo ./install.sh
```

This installs the full KeyFlip package:

* GTK application
* GNOME Shell extension
* panel controls
* global shortcut
* keyboard-control helper

For Cleaning Mode on Fedora:

```bash
sudo dnf install python3-evdev
```

Combined keyboard/pointer devices also require `/dev/uinput`.

Log out and back in after installing or updating KeyFlip.

### Uninstall a manual installation

From the source directory:

```bash
sudo ./uninstall.sh
```

## Remove the Fedora package

```bash
sudo dnf remove keyflip
```

Optionally remove the COPR repository:

```bash
sudo dnf copr remove mikachu/keyflip
```

## Building packages

Run:

```bash
make package
```

This validates the source and creates:

```text
dist/keyflip-0.2.0-beta.tar.gz
```

The Arch and RPM packaging recipes use this local source archive.

### Arch

Copy the archive beside:

```text
packaging/arch/PKGBUILD
```

Then refresh the checksum:

```bash
updpkgsums
```

and build with:

```bash
makepkg
```

### RPM

Place the source archive in your RPM `SOURCES` directory and build:

```text
packaging/obs/keyflip.spec
```

## AI-assisted development

KeyFlip was developed with help from AI tools for coding, debugging, documentation, and learning.

I review, test, modify, and take responsibility for everything released in this project.

## Status

**Current version:** `0.2.0-beta`

KeyFlip is still in active development.

Bug reports, hardware compatibility reports, feature suggestions, and other feedback are welcome.

```
```

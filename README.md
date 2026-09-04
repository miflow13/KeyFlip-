# KeyFlip

![KeyFlip icon](assets/keyflip.png)

**KeyFlip 0.1.0-beta** is a polished Fedora GNOME utility for safely enabling or disabling a supported laptop's internal keyboard. It works on Wayland and X11 and leaves external USB and Bluetooth keyboards untouched.

### AI Assistance

This project was developed with the assistance of AI tools during parts of the coding, debugging, planning, and learning process.

AI did not independently create or maintain this project. I chose the project’s direction, tested the software, made implementation decisions, reviewed and modified the code, and remain responsible for the final result.

I’m still actively learning software development, and I use AI as one of several tools to help me understand concepts, troubleshoot problems, and build things I find useful.

If you find a bug or have suggestions for improving KeyFlip, contributions and feedback are welcome.

## Requirements

- Fedora Linux with GNOME
- Python 3 and GTK 4 Python bindings (`python3-gobject`)
- `polkit`, `util-linux`, and `systemd`
- A standard i8042/AT internal keyboard

KeyFlip currently does not support internal USB or I2C keyboards.

## Install the beta

Download and extract `keyflip-0.1.0-beta.tar.gz`, then run:

```bash
cd keyflip-0.1.0-beta
sudo ./install.sh
```

Open **KeyFlip** from the GNOME application menu. The app requests the normal Fedora administrator authorization whenever the keyboard state changes.

Keep an external keyboard connected before disabling the internal keyboard.

## Run from source

```bash
./keyflip
```

## Command-line helper

From the source directory:

```bash
sudo ./keyflip-helper disable
sudo ./keyflip-helper enable
sudo ./keyflip-helper toggle
./keyflip-helper status
```

For a safe 15-second test:

```bash
sudo ./keyflip-helper test
```

## Build a release archive

```bash
make package
```

The distributable archive and SHA-256 checksum are written to `dist/`.

## Uninstall

From the extracted release or source directory:

```bash
sudo ./uninstall.sh
```

## Recovery

If authorization is cancelled while the internal keyboard is disabled, use an external keyboard and run:

```bash
sudo /usr/local/lib/keyflip/keyflip-helper enable
```

Restarting the computer also restores normal keyboard operation.

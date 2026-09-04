# Internal Laptop Keyboard Toggle

A simple script to enable or disable a supported laptop’s internal keyboard on Fedora GNOME. Works with Wayland and X11.

Designed for Linux laptops with an i8042/AT internal keyboard. Developed for Fedora; other distributions have not been tested.
## Install

Download `internal-keyboard`, open a terminal in the folder containing it, and run:

```bash
sudo install -m 755 internal-keyboard /usr/local/bin/internal-keyboard
```

## Test first

Disable the internal keyboard for about 15 seconds, then automatically enable it:

```bash
sudo internal-keyboard test
```

## Usage

```bash
# Switch between enabled and disabled
sudo internal-keyboard toggle

# Disable the internal keyboard
sudo internal-keyboard disable

# Enable the internal keyboard
sudo internal-keyboard enable

# Check current status
internal-keyboard status
```

## Recovery

Have an external keyboard available before disabling the internal keyboard indefinitely. Run `sudo internal-keyboard enable` to restore it.

Restarting the computer also restores the keyboard. The script makes no persistent configuration changes.

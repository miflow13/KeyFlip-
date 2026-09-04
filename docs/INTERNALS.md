# KeyFlip Internals and Learning Guide

This document explains what KeyFlip does, how its pieces cooperate, why the
architecture looks the way it does, and where its current limitations are. It
is written for maintainers who want to understand the system rather than treat
the project as generated code that happens to work.

## 1. The product idea

KeyFlip began as a solution to one concrete problem: prevent accidental input
from a laptop keyboard while an external keyboard is placed over it.

The low-level operation is “unbind the `atkbd` driver from the laptop's i8042
keyboard port.” That is not a useful mental model for most users. The product
therefore evolved through three levels of abstraction:

1. A privileged command that enables or disables the keyboard.
2. A graphical switch and GNOME panel button that expose that command safely.
3. User-facing presets: **Laptop Mode** and **Desk Mode**.

The current preset meanings are intentionally simple:

| Preset | Internal keyboard |
| --- | --- |
| Laptop Mode | Enabled |
| Desk Mode | Disabled |

These are presets, not an independent source of truth. KeyFlip derives the
selected mode from the real keyboard state every time it refreshes. It does not
store a separate `desk_mode = true` flag that can disagree with the hardware.

Touchpad control may eventually add another action to each preset, but it is
not part of the current implementation.

## 2. Architecture at a glance

```text
GTK application                 GNOME Shell extension
keyflip_app.py                  gnome-extension/extension.js
        |                                   |
        | unprivileged status queries       | unprivileged status queries
        | privileged state changes          | privileged state changes
        +-----------------+-----------------+
                          |
                     pkexec + Polkit
                          |
                    keyflip-helper
                          |
              Linux sysfs keyboard driver controls
                          |
             /sys/bus/serio/drivers/atkbd
```

There are two front ends but only one component that knows how to manipulate
the kernel. This separation is deliberate:

- The GUI owns presentation, mode selection, warnings, and progress feedback.
- The extension owns panel integration, automatic detection, animation, and
  shell notifications.
- The helper owns device discovery, validation, locking, and kernel writes.
- Polkit decides whether a user may run the helper with administrator rights.

Keeping kernel logic out of both front ends prevents two separate
implementations from drifting apart.

## 3. Repository map

| Path | Responsibility |
| --- | --- |
| `keyflip-helper` | Low-level keyboard detection and state changes. |
| `keyflip_app.py` | GTK 4 GUI and Laptop/Desk Mode workflow. |
| `app.py` | Small application entry point. |
| `keyflip` | Launcher that finds the source or installed application. |
| `gnome-extension/extension.js` | GNOME Shell panel interface and automation. |
| `gnome-extension/metadata.json` | Extension identity and supported Shell version. |
| `gnome-extension/stylesheet.css` | Panel icon sizing and spacing. |
| `packaging/*.policy` | Polkit authorization rule. |
| `packaging/*.desktop` | Desktop application launcher metadata. |
| `packaging/*.metainfo.xml` | AppStream/store metadata and release history. |
| `install.sh` / `uninstall.sh` | System installation and removal. |
| `Makefile` | Static validation and release entry points. |

## 4. The Linux input model KeyFlip relies on

### 4.1 i8042 and `atkbd`

Many traditional laptop keyboards are exposed through an i8042 controller.
Linux represents its keyboard port under:

```text
/sys/bus/serio/devices/serioN
```

The keyboard driver is normally:

```text
/sys/bus/serio/drivers/atkbd
```

When the port has a `driver` symlink pointing to `atkbd`, the keyboard is
enabled. When that driver is unbound, key events stop reaching userspace.

KeyFlip does not unload the entire `atkbd` module. It targets one validated
i8042 keyboard port so unrelated input devices remain usable.

### 4.2 Why hardware support is limited

Not every laptop keyboard uses i8042. Newer machines may expose an internal
keyboard through USB or I2C. The current helper intentionally refuses those
systems instead of guessing. A wrong guess in input-device code can disable the
only usable keyboard.

The helper requires exactly one port whose description is:

```text
i8042 KBD port
```

If it finds zero or multiple matching ports, it stops with an error.

### 4.3 Enabling and disabling

To disable the keyboard, the helper:

1. Changes the port's `bind_mode` to `manual`.
2. Writes the port identifier, such as `serio0`, to the driver's `unbind` file.

To enable it, the helper:

1. Restores `bind_mode` to `auto`.
2. Explicitly binds the port if the kernel did not bind it automatically.

`bind_mode` matters. Without manual mode, the kernel may immediately reconnect
the driver after it is unbound.

The change is not permanent firmware configuration. Rebooting restores the
normal kernel/device initialization path.

## 5. The helper as a security boundary

`keyflip-helper` is the most security-sensitive file in the project because it
runs as root.

It follows several defensive rules:

- `set -euo pipefail` stops on failed commands, unset variables, and failed
  pipeline stages.
- `PATH` is replaced with a known system path instead of trusting the caller.
- Actions are accepted from a fixed allowlist.
- The discovered port identifier must match `serio[0-9]+`.
- The driver symlink must point to the expected `atkbd` path.
- Required sysfs control files must be writable before changes begin.
- `flock` serializes operations so the GUI and extension cannot change state
  at the same time.

This is an example of **defense in depth**: no single check is treated as
sufficient protection.

### Read-only versus privileged actions

The following actions do not require root:

```text
status
external-status
external-list
```

The following actions modify kernel state and require root:

```text
enable
disable
toggle
test
```

This split is important. The front ends poll status frequently. Requiring an
authentication prompt for every poll would be both annoying and unsafe.

### The test action

`test` schedules a systemd recovery job before disabling the keyboard. The job
re-enables it after roughly 15 seconds. Scheduling recovery first avoids a
failure mode where the keyboard is disabled and the recovery step never starts.

## 6. Polkit and `pkexec`

Normal desktop applications cannot write to sysfs driver controls. KeyFlip uses
`pkexec` to ask Polkit to run only the installed helper as root.

The policy action is:

```text
io.github.miflow13.KeyFlip.toggle
```

The policy's executable annotation points to:

```text
/usr/libexec/keyflip/keyflip-helper
```

This exact installed path matters. Running an arbitrary edited script through
the same policy is not intended to inherit authorization.

The current policy uses `allow_active=yes`, while inactive and remote-style
sessions are denied. In Polkit policy language, `yes` normally means an active
local user is authorized without entering a password. The policy's descriptive
“Authentication is required” message does not enforce authentication by
itself. If administrator authentication is intended, this default should be
reviewed and changed to an appropriate value such as `auth_admin` or
`auth_admin_keep` after testing the desired security and usability tradeoff.

The front ends invoke a change like this conceptually:

```text
pkexec /usr/libexec/keyflip/keyflip-helper disable
```

If the selected Polkit rule requires credentials, Polkit owns the password
prompt; KeyFlip never reads or stores a password.

## 7. External-keyboard detection

The helper scans `/sys/class/input/event*` and asks udev for properties of each
input endpoint. A device counts as an external keyboard when it has:

```text
ID_INPUT_KEYBOARD=1
```

and its bus is USB or Bluetooth.

Mouse and touchpad names are excluded because many programmable mice expose a
small keyboard endpoint for media buttons.

`external-list` prints udev `DEVPATH` values instead of friendly names. The
extension needs stable identities so it can distinguish “a keyboard remains
connected” from “a new keyboard was added.”

### Detection is a heuristic

udev reports what hardware claims to be. Some receivers and embedded devices
claim to be full keyboards even when the user does not consider them one. This
is why external-device detection must not be treated as perfect truth.

Current behavior:

- The GUI warns before Desk Mode when no external keyboard is detected.
- Automatic switching is an opt-in GSettings preference and defaults off.
- When enabled, the extension disables when an external endpoint appears.
- The extension restores the keyboard when the last endpoint disappears, but
  only if KeyFlip itself performed the automatic disable.

A future device allowlist would be safer than hardcoding vendor IDs into the
helper, because the same hardware ID may be legitimate for another user.

## 8. GTK application flow

`keyflip_app.py` uses GTK 4 through PyGObject.

### Startup

`app.py` imports the shared `Gtk.Application` object. On activation:

1. Application CSS is registered.
2. `KeyboardWindow` is created.
3. The window builds the mode selector, status card, and safety note.
4. `refresh_status()` asks the helper for the real keyboard state.
5. A one-second timer keeps the UI synchronized.

### Presets and source of truth

The two mode buttons are grouped `Gtk.ToggleButton` widgets. They are a
presentation of the current keyboard state:

```python
keyboard enabled  -> Laptop Mode selected
keyboard disabled -> Desk Mode selected
```

`sync_mode_controls()` updates the buttons while `updating_mode` suppresses
their callbacks. This guard prevents programmatic UI synchronization from being
mistaken for a user request.

This is a common event-driven programming pattern:

```text
read model -> temporarily suppress handlers -> update view -> restore handlers
```

### Activating Laptop Mode

1. The user selects Laptop Mode.
2. `on_mode_selected()` verifies that the request differs from real state.
3. The UI returns to confirmed state while the operation is pending.
4. `start_toggle("enable", True)` plays feedback and marks the UI busy.
5. A background thread runs the privileged helper.
6. The GTK main thread receives the result through `GLib.idle_add()`.
7. Status is read again before the selected mode changes.

### Activating Desk Mode

Desk Mode follows the same path with one additional safety gate:

```text
external keyboard detected?
    yes -> request disable
    no  -> show warning -> cancel or Activate Anyway
```

The warning window is presented with `GLib.idle_add()`. Presenting a modal
window directly inside a toggle signal proved unreliable in GTK 4; deferring it
lets the original event finish first.

### Why work runs in a thread

`subprocess.run()` blocks until the command finishes. A Polkit interaction can
take several seconds while the user enters a password. Running that call on the
GTK main thread would freeze painting and input for the entire window.

The background thread performs blocking work. It never edits GTK widgets
directly because GTK is not thread-safe. Instead it schedules
`show_toggle_result()` back on the main loop with `GLib.idle_add()`.

### Verification after mutation

A zero exit code is not treated as enough. After a successful helper command,
the GUI runs `status` and checks that hardware reached the expected state. This
is the difference between “the command said it worked” and “the system is now
in the requested configuration.”

## 9. GNOME Shell extension flow

The extension is JavaScript executed by GJS inside GNOME Shell. It does not use
GTK widgets. Shell UI uses `St` actors, Clutter animation, and GNOME Shell's own
modules.

### Lifecycle

`enable()` creates a `KeyFlipIndicator` and inserts it in the panel.
`disable()` destroys it. The indicator's destroy handler removes both polling
timers. Cleaning timers is essential because an extension can be reloaded many
times in one Shell session.

### Polling

The extension currently uses two timers:

- Every 1 second: refresh internal keyboard status and icon.
- Every 500 milliseconds: refresh the set of external keyboards.

Polling is simple and robust, but it performs repeated subprocess and udev
work. The subprocess calls are asynchronous so they do not block GNOME Shell's
main thread. A future version could listen to udev events through a dedicated
service instead.

### Automatic switching state

The persistent `automatic-disable-owned` GSettings key records ownership of an
automatic disable cycle.

Why ownership matters:

- If KeyFlip automatically disables the keyboard, it should restore it when
  the external keyboard disappears.
- If the user manually disabled the keyboard, disconnecting an unrelated
  device should not override that choice.

`_disconnectChecks` requires two consecutive missing-device polls before
restoring. This small debounce protects against a transient udev read that
briefly makes a connected keyboard disappear.

### Shell animation

The original animation reference used `Adw.SpringAnimation`, which belongs to
libadwaita/GTK and cannot animate a GNOME Shell `St.Icon`. The extension instead
uses a sequence of Clutter scale keyframes:

```text
1.00 -> 0.82 -> 1.20 -> 0.94 -> 1.05 -> 1.00
```

The icon's pivot is its center. Each frame uses an easing curve and starts the
next frame in `onComplete`, producing anticipation, overshoot, and settlement.

### OSD feedback

After a successful operation, the extension shows a GNOME on-screen display.
KeyFlip temporarily centers its OSD and restores the Shell's previous alignment
after the message fades. Access to `_osdWindows` is private Shell API, so this
area deserves testing on every supported GNOME release.

## 10. Installation and the “stale installed copy” lesson

Source files and installed files are separate copies.

The GUI is installed under:

```text
/usr/libexec/keyflip/
```

The extension is installed under:

```text
/usr/share/gnome-shell/extensions/keyflip@miflow13.github.io/
```

Editing a repository file does not update either installed copy. This caused a
real debugging trap during development: source contained a fixed dialog while
the desktop launcher still ran the old installed `Gtk.MessageDialog` code.

After GUI changes:

```bash
sudo ./install.sh --gui-only
keyflip
```

After extension changes:

```bash
sudo ./install.sh --extension-only
gnome-extensions disable keyflip@miflow13.github.io
gnome-extensions enable keyflip@miflow13.github.io
```

On Wayland, logging out and back in is the most reliable Shell reload.

To prove whether source and installed GUI match:

```bash
sha256sum keyflip_app.py /usr/libexec/keyflip/keyflip_app.py
```

Matching hashes mean the installed Python file is current.

## 11. Validation and debugging

Run the project checks before committing:

```bash
make check
```

This currently verifies:

- Python syntax compilation.
- Shell-script syntax.
- Desktop entry validity.
- AppStream metadata validity.

Useful direct diagnostics:

```bash
./keyflip-helper status
./keyflip-helper external-status
./keyflip-helper external-list
```

Inspect all input endpoints udev considers keyboards:

```bash
for event in /sys/class/input/event*; do
    udevadm info --query=property --path="$event" 2>/dev/null |
        grep -q '^ID_INPUT_KEYBOARD=1$' || continue
    echo "$event: $(<"$event/device/name")"
done
```

Watch GNOME Shell extension logs:

```bash
journalctl --user -f -o cat | grep -i keyflip
```

When diagnosing a state bug, check each layer in order:

1. What does `keyflip-helper status` report?
2. Does the source helper report the expected external devices?
3. Does the installed helper match the source?
4. Did Polkit display an authorization prompt?
5. What exit code and output did the helper return?
6. Did the front end verify state after the command?

This layered approach is much faster than repeatedly changing UI code.

## 12. Important current limitations

1. Only a single standard i8042 keyboard port is supported.
2. USB/I2C internal keyboards are deliberately unsupported.
3. External-keyboard detection depends on udev classifications and can have
   false positives.
4. The GUI's presets currently control only the internal keyboard.
5. Both front ends poll by spawning helper processes, although that work is
   performed asynchronously.
6. Some extension OSD behavior relies on private GNOME Shell internals.
7. There is no automated integration test for real sysfs mutation.

These are not merely missing features; they define the safe boundary of what
the current code can promise.

## 13. Sensible next stages

### Stage 1: finish and test the preset UI

- Test Laptop/Desk transitions with authorization accepted and cancelled.
- Test Desk Mode with no external keyboard.
- Test status synchronization when the extension changes state.
- Update screenshots and user documentation.

### Stage 2: touchpad support

First research how GNOME represents the user's touchpad preference. Touchpad
control should probably use the desktop setting rather than unbind a kernel
driver. Add separate low-level actions before adding them to presets.

### Stage 3: persistent preset configuration

Store user preferences in a GSettings schema, for example whether Desk Mode
disables the touchpad. Keep policy decisions in settings and device operations
in dedicated functions.

### Stage 4: event-driven automation

Replace high-frequency polling with udev monitoring, likely in a small user
service. Define recovery behavior carefully before moving automatic control out
of the Shell extension.

### Stage 5: broader hardware support

Add USB or I2C internal-keyboard support only after reliable identification is
designed. “Internal” cannot safely be inferred from bus type alone.

## 14. Concepts this project demonstrates

KeyFlip is a compact example of several general software-engineering ideas:

- **Abstraction:** users choose Laptop Mode, not kernel driver operations.
- **Separation of concerns:** UI, authorization, and hardware mutation live in
  different components.
- **Least privilege:** status is unprivileged; only mutations use Polkit.
- **Source of truth:** mode selection is derived from actual device state.
- **State ownership:** automatic restoration occurs only for automatic changes.
- **Event-loop programming:** GTK and GNOME Shell react to signals and timers.
- **Concurrency:** blocking authorization runs outside the GTK main thread.
- **Idempotence:** enabling an enabled keyboard or disabling a disabled one is
  safe and produces the intended final state.
- **Verification:** state is read after a mutation instead of trusting success
  output alone.
- **Defensive programming:** hardware assumptions are validated before root
  writes happen.
- **Progressive enhancement:** presets come before touchpad profiles and
  background automation.

The central lesson is that the visible button is the smallest part of the
system. A trustworthy input utility is primarily about explicit state,
privilege boundaries, hardware validation, recovery, and honest limitations.

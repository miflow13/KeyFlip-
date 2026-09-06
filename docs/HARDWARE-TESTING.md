# KeyFlip hardware test checklist

Keep a known-good external keyboard connected. If possible, keep an SSH session
open from another device. Stop immediately if recovery does not behave exactly
as expected.

## Setup

- [ ] Confirm the external keyboard and SSH fallback both work.
- [ ] Install the current build and log out/in to reload the Shell extension.
- [ ] Confirm `keyflip` opens and the panel indicator appears.
- [ ] Run `keyflip-helper status`, `external-status`, and `external-list` without
      elevation; confirm they do not prompt for authorization.

## Internal keyboard modes

- [ ] In Laptop Mode, confirm the internal and external keyboards both type.
- [ ] Run 15-second Test Mode first; confirm the internal keyboard disables and
      restores automatically.
- [ ] Enter Desk Mode with the external keyboard connected; confirm only the
      internal keyboard stops typing.
- [ ] Return to Laptop Mode; confirm the internal keyboard works immediately.
- [ ] Cancel a Polkit prompt; confirm the hardware state does not change.

## Recovery and automation

- [ ] Enable automatic switching and connect an external keyboard; confirm Desk
      Mode activates only after the keyboard is detected.
- [ ] Disconnect the last external keyboard; confirm Laptop Mode returns.
- [ ] Manually select Desk Mode, then disconnect an external keyboard; confirm
      the automatic ownership rule does not override the manual choice.
- [ ] Quit KeyFlip in Desk Mode; confirm Laptop Mode is restored before exit.
- [ ] Enter Desk Mode, then suspend and resume; confirm Laptop Mode is restored.

## Cleaning Mode

- [ ] Start Cleaning Mode with all keys released; confirm keyboard input is
      blocked while mouse/trackpad input remains usable.
- [ ] Use End Cleaning; confirm all keyboards recover immediately.
- [ ] Start it again and let the 60-second timeout expire; confirm recovery.
- [ ] Hot-plug an external keyboard during Cleaning Mode; confirm it is blocked
      and then restored with every other keyboard.

## Failure checks

- [ ] With no external keyboard detected, confirm Desk Mode shows a warning.
- [ ] Confirm unsupported hardware reports an error and performs no mutation.
- [ ] Review `journalctl -u keyflip-recovery.service` for recovery failures.
- [ ] Record GNOME version, kernel version, keyboard buses, and any failed step
      before changing code.

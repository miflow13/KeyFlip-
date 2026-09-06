"""Temporary keyboard suppression. Device handles own the lifetime of each grab."""
import errno
import fcntl
import json
import os
from pathlib import Path
import select
import signal
import sys
import time


DURATION = 60


def pointer_capabilities(capabilities, codes):
    """Keep pointer buttons/axes, including combined keyboard/trackpad devices."""
    result = {}
    for kind in (codes.EV_KEY, codes.EV_REL, codes.EV_ABS, codes.EV_MSC):
        values = capabilities.get(kind, [])
        if kind == codes.EV_KEY:
            values = [code for code in values if code in codes.BTN]
        elif kind == codes.EV_MSC:
            values = [code for code in values if code != codes.MSC_SCAN]
        if values:
            result[kind] = values
    if not any(kind in result for kind in (codes.EV_KEY, codes.EV_REL, codes.EV_ABS)):
        return {}
    return result


class CleaningSession:
    def __init__(self, backend, keypress=lambda: None):
        self.backend = backend
        self.devices = {}
        self.keypress = keypress

    def close(self):
        for device, pointer in self.devices.values():
            device.close()  # Kernel releases EVIOCGRAB even on process death.
            if pointer is not None:
                pointer.close()
        self.devices.clear()

    def scan(self):
        # Glob rather than list_devices(): inaccessible devices must cause an
        # explicit failure, not silently disappear from the coverage claim.
        paths = set(Path('/dev/input').glob('event*'))
        for path in list(self.devices):
            if path not in paths:
                device, pointer = self.devices.pop(path)
                device.close()
                if pointer is not None:
                    pointer.close()
        for path in sorted(paths - self.devices.keys()):
            device = None
            pointer = None
            try:
                device = self.backend.InputDevice(str(path))
                capabilities = device.capabilities()
                codes = self.backend.ecodes
                if not any(code in codes.KEY for code in capabilities.get(codes.EV_KEY, [])):
                    device.close()
                    continue
                if device.active_keys():
                    raise RuntimeError('Release all keys and pointer buttons before starting Cleaning Mode.')
                pointer_events = pointer_capabilities(capabilities, codes)
                if pointer_events:
                    pointer = self.backend.UInput(
                        pointer_events, name=f'KeyFlip pointer: {device.name}',
                        vendor=device.info.vendor, product=device.info.product,
                        version=device.info.version, bustype=device.info.bustype,
                        input_props=device.input_props(),
                    )
                device.grab()
                self.devices[path] = (device, pointer)
            except BaseException:
                if device is not None:
                    device.close()
                if pointer is not None:
                    pointer.close()
                raise

    def drain(self, device, pointer):
        codes = self.backend.ecodes
        try:
            for event in device.read():
                if event.type == codes.EV_SYN and event.code == codes.SYN_DROPPED:
                    raise RuntimeError('Input events were lost; Cleaning Mode ended to restore normal input.')
                if event.type == codes.EV_KEY and event.code in codes.KEY and event.value == 1:
                    self.keypress()
                if pointer is None:
                    continue
                if event.type == codes.EV_KEY and event.code in codes.BTN:
                    pointer.write_event(event)
                elif event.type in (codes.EV_REL, codes.EV_ABS, codes.EV_SYN):
                    pointer.write_event(event)
                elif event.type == codes.EV_MSC and event.code != codes.MSC_SCAN:
                    pointer.write_event(event)
        except BlockingIOError:
            pass
        except OSError as error:
            if error.errno != errno.ENODEV:
                raise
            # Event numbers may be reused before the next scan observes the
            # unplug. Drop the dead handle so its replacement is grabbed.
            for path, (current, _) in list(self.devices.items()):
                if current is device:
                    del self.devices[path]
                    device.close()
                    if pointer is not None:
                        pointer.close()
                    break

    def run(self, control, ready, duration=DURATION):
        try:
            self.scan()
            if not self.devices:
                raise RuntimeError('No keyboard input devices found. Nothing changed.')
            started = time.clock_gettime(time.CLOCK_BOOTTIME)
            # BOOTTIME includes suspend; MONOTONIC does not. End even a short
            # suspended session on resume, independently of GTK or GNOME Shell.
            suspend_offset = started - time.monotonic()
            deadline = started + duration
            ready()
            while time.clock_gettime(time.CLOCK_BOOTTIME) < deadline:
                if time.clock_gettime(time.CLOCK_BOOTTIME) - time.monotonic() - suspend_offset > 0.1:
                    break
                readers = [control, *(device for device, _ in self.devices.values())]
                readable, _, _ = select.select(readers, [], [], min(0.1, max(0, deadline - time.clock_gettime(time.CLOCK_BOOTTIME))))
                if control in readable:
                    # Any command or EOF ends the session; no second Polkit prompt.
                    break
                for device, pointer in list(self.devices.values()):
                    if device in readable:
                        self.drain(device, pointer)
                self.scan()
        finally:
            self.close()


def main():
    if os.geteuid() != 0:
        print('Cleaning Mode requires authorization.', file=sys.stderr)
        return 1
    try:
        import evdev
        if select.select([sys.stdin], [], [], 0)[0]:
            return 0  # Cancelled (or GUI closed) during authorization.
        # Shared with the internal-keyboard helper: modes cannot race cleaning.
        with open('/run/internal-keyboard-toggle.lock', 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            def interrupted(_signum, _frame):
                raise SystemExit(0)
            for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                signal.signal(signum, interrupted)
            runtime = Path('/run/keyflip')
            runtime.mkdir(mode=0o755, exist_ok=True)
            marker = runtime / 'cleaning.json'
            def ready():
                start = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
                marker.write_text(json.dumps(dict(pid=os.getpid(), start=start,
                    until=time.clock_gettime(time.CLOCK_BOOTTIME) + DURATION)))
                print('READY', flush=True)
                os.set_blocking(sys.stdout.fileno(), False)
            def keypress():
                try:
                    os.write(sys.stdout.fileno(), b'KEY\n')
                except BlockingIOError:
                    pass  # Feedback must never block keyboard filtering.
            try:
                CleaningSession(evdev, keypress).run(sys.stdin, ready)
            finally:
                marker.unlink(missing_ok=True)
    except ImportError:
        print('Install python3-evdev (Fedora) or python-evdev (Arch) to use Cleaning Mode.', file=sys.stderr)
        return 1
    except BlockingIOError:
        print('Another keyboard change is in progress. Try again when it finishes.', file=sys.stderr)
        return 1
    except (OSError, RuntimeError) as error:
        print(f'Cleaning Mode ended: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

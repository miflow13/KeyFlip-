"""Read-only input state and coalesced desktop notifications; no helper subprocesses."""
import json
import os
from pathlib import Path
import struct
import sys
import time

SYS_INPUT = Path('/sys/class/input')
SERIO = Path('/sys/bus/serio')
UDEV_DATA = Path('/run/udev/data')
RUNTIME = Path('/run/keyflip')


def process_start(pid):
    return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]


def heartbeat(role, pid):
    path = Path(f'/run/user/{os.getuid()}/keyflip-{role}.lease')
    try:
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(pid=pid, start=process_start(pid))))
        temporary.replace(path)
    except OSError:
        pass


def typing_keys(bitmap):
    words = bitmap.split()
    bits = sum(int(word, 16) << (index * struct.calcsize('L') * 8)
               for index, word in enumerate(reversed(words)))
    return all(bits & (1 << key) for key in (28, 30, 44, 57))  # Enter, A, Z, Space


def external_keyboards(sys_input=SYS_INPUT, udev_data=UDEV_DATA):
    keyboards = set()
    for event in sys_input.glob('event*'):
        try:
            if not typing_keys((event / 'device/capabilities/key').read_text()):
                continue
            major_minor = (event / 'dev').read_text().strip()
            properties = {}
            for line in (udev_data / f'c{major_minor}').read_text().splitlines():
                if line.startswith('E:') and '=' in line:
                    key, value = line[2:].split('=', 1)
                    properties[key] = value
            if properties.get('ID_INPUT_KEYBOARD') == '1' and properties.get('ID_BUS') in ('usb', 'bluetooth'):
                # The input endpoint is stable while connected; sets handle
                # receivers exposing multiple keyboard endpoints without counts.
                keyboards.add(str(event.resolve()))
        except FileNotFoundError:
            if event.exists():
                raise RuntimeError('Keyboard device information is not ready; automatic switching is paused.')
        except (OSError, ValueError) as error:
            raise RuntimeError(f'Could not inspect keyboard devices: {error}') from error
    return sorted(keyboards)


def internal_state(serio=SERIO):
    ports = []
    for port in (serio / 'devices').glob('serio*'):
        try:
            if (port / 'description').read_text().strip() == 'i8042 KBD port':
                ports.append(port)
        except FileNotFoundError:
            continue
    if len(ports) != 1:
        return None, 'No single supported i8042 internal keyboard found. Laptop/Desk Mode supports i8042/AT keyboards; Cleaning Mode also supports USB and I2C keyboards.'
    driver = ports[0] / 'driver'
    if not driver.is_symlink():
        return False, ''
    if driver.resolve() != (serio / 'drivers/atkbd').resolve():
        return None, 'The internal keyboard uses an unexpected driver. Nothing changed.'
    return True, ''


def cleaning_active(runtime=RUNTIME):
    try:
        state = json.loads((runtime / 'cleaning.json').read_text())
        # Include process start time to reject a stale marker with a reused PID.
        start = Path(f'/proc/{int(state["pid"])}/stat').read_text().rsplit(')', 1)[1].split()[19]
        return start == state['start'] and time.clock_gettime(time.CLOCK_BOOTTIME) < state['until']
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return False


def snapshot():
    try:
        enabled, error = internal_state()
    except OSError as exception:
        enabled, error = None, f'Could not read internal keyboard state: {exception}'
    try:
        external, external_error = external_keyboards(), ''
    except RuntimeError as exception:
        external, external_error = None, str(exception)
    return dict(enabled=enabled, error=error, external=external,
                external_error=external_error, cleaning=cleaning_active())


class StateMonitor:
    """File events trigger reads; a slow fallback covers sysfs and lost events."""
    def __init__(self, callback, role='app', owner=None):
        from gi.repository import Gio, GLib
        self.GLib = GLib
        self.callback = callback
        self.previous = None
        self.monitors = []
        self.pending = None
        self.closed = False
        self.role = role
        self.owner = owner or os.getpid()
        self.runtime_monitored = False
        for path in (SYS_INPUT, Path('/dev/input'), UDEV_DATA, SERIO / 'drivers/atkbd', Path('/run'), RUNTIME):
            if not path.exists():
                continue
            try:
                monitor = Gio.File.new_for_path(str(path)).monitor_directory(Gio.FileMonitorFlags.NONE, None)
                monitor.connect('changed', self.changed)
                self.monitors.append(monitor)
                if path == RUNTIME:
                    self.runtime_monitored = True
            except GLib.Error:
                pass  # Periodic verification still works without inotify support.
        self.timer = GLib.timeout_add_seconds(5, self.refresh)
        self.queue()

    def changed(self, _monitor, file, _other, _event):
        if file.get_parent().get_path() == '/run' and file.get_basename() != 'keyflip':
            return
        if not self.runtime_monitored and RUNTIME.exists():
            from gi.repository import Gio
            monitor = Gio.File.new_for_path(str(RUNTIME)).monitor_directory(Gio.FileMonitorFlags.NONE, None)
            monitor.connect('changed', self.changed)
            self.monitors.append(monitor)
            self.runtime_monitored = True
        self.queue()

    def queue(self):
        if not self.closed and self.pending is None:
            self.pending = self.GLib.timeout_add(100, self.flush)

    def flush(self):
        self.pending = None
        self.refresh()
        return self.GLib.SOURCE_REMOVE

    def refresh(self, force=False):
        if self.closed:
            return self.GLib.SOURCE_REMOVE
        if self.role is not None:
            heartbeat(self.role, self.owner)
        state = snapshot()
        if force or state != self.previous:
            self.previous = state
            self.callback(state)
        return self.GLib.SOURCE_CONTINUE

    def close(self):
        self.closed = True
        for monitor in self.monitors:
            monitor.cancel()
        self.monitors.clear()
        for source in (self.timer, self.pending):
            if source is not None:
                self.GLib.source_remove(source)
        self.timer = self.pending = None
        if self.role is not None:
            Path(f'/run/user/{os.getuid()}/keyflip-{self.role}.lease').unlink(missing_ok=True)


def main():
    if sys.argv[1:] == ['--watch']:
        from gi.repository import GLib
        owner = os.getppid()
        monitor = StateMonitor(lambda state: print(json.dumps(state), flush=True), role='panel', owner=owner)
        loop = GLib.MainLoop()
        def parent_alive():
            if os.getppid() != owner:
                loop.quit()
                return GLib.SOURCE_REMOVE
            return GLib.SOURCE_CONTINUE
        parent_timer = GLib.timeout_add_seconds(5, parent_alive)
        try:
            loop.run()
        finally:
            monitor.close()
            if os.getppid() == owner:
                GLib.source_remove(parent_timer)
    elif sys.argv[1:] == ['--external']:
        try:
            print('\n'.join(external_keyboards()))
        except RuntimeError as error:
            print(error, file=sys.stderr)
            return 1
    else:
        print(json.dumps(snapshot()))
    return 0


if __name__ == '__main__':
    sys.exit(main())

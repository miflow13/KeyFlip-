"""Root-owned recovery for Desk Mode, independent of the GTK app and Shell."""
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

RUNTIME = Path('/run/keyflip')
STATE = RUNTIME / 'desk.json'
LOCK = Path('/run/internal-keyboard-toggle.lock')
SERIO = Path('/sys/bus/serio')


def process_matches(pid, start):
    try:
        return Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')', 1)[1].split()[19] == start
    except (OSError, ValueError, IndexError):
        return False


def frontend_alive(uid, runtime_root=Path('/run/user'), now=None):
    now = time.time() if now is None else now
    for role in ('app', 'panel'):
        path = runtime_root / str(uid) / f'keyflip-{role}.lease'
        try:
            stat = path.stat()
            lease = json.loads(path.read_text())
            if stat.st_uid == uid and 0 <= now - stat.st_mtime < 15 and process_matches(lease['pid'], lease['start']):
                return True
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return False


def restore(state, serio=SERIO):
    port_id = state.get('port', '')
    if not re.fullmatch(r'serio[0-9]+', port_id):
        raise RuntimeError('Invalid recovery keyboard port')
    port = serio / 'devices' / port_id
    driver = serio / 'drivers/atkbd'
    if (port / 'description').read_text().strip() != 'i8042 KBD port':
        raise RuntimeError('Recovery port is not an i8042 keyboard')
    if (port / 'driver').is_symlink() and (port / 'driver').resolve() != driver.resolve():
        raise RuntimeError('Recovery port is using an unexpected driver')
    (port / 'bind_mode').write_text('auto')
    if not (port / 'driver').is_symlink():
        (driver / 'bind').write_text(port_id)
    if not (port / 'driver').is_symlink() or (port / 'driver').resolve() != driver.resolve():
        raise RuntimeError('Recovery could not confirm that the internal keyboard is enabled')


def recover(force=False, wait=False):
    if not STATE.exists():
        return
    try:
        with LOCK.open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
            if not STATE.exists():
                return
            state = json.loads(STATE.read_text())
            if force or not frontend_alive(int(state['uid'])):
                restore(state)
                STATE.unlink()
    except BlockingIOError:
        pass  # Retry on the next tick if a mode change is completing.


def arm(uid, port):
    uid = int(uid)
    if uid < 0 or not re.fullmatch(r'serio[0-9]+', port):
        raise RuntimeError('Invalid keyboard recovery request')
    if not frontend_alive(uid):
        raise RuntimeError('Open KeyFlip or enable its panel before Desk Mode. Recovery could not confirm a live front end.')
    RUNTIME.mkdir(mode=0o755, exist_ok=True)
    # The installed system service must be running before the caller unbinds.
    result = subprocess.run(['/usr/bin/systemctl', 'start', 'keyflip-recovery.service'], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Keyboard recovery could not start. Reinstall KeyFlip. ' + result.stderr.strip())
    temporary = STATE.with_suffix('.tmp')
    with temporary.open('w') as stream:
        os.chmod(temporary, 0o600)
        json.dump(dict(uid=uid, port=port), stream)
    temporary.replace(STATE)


def serve():
    from gi.repository import Gio, GLib
    loop = GLib.MainLoop()
    force_pending = False

    def check():
        nonlocal force_pending
        try:
            recover(force_pending)
            if not STATE.exists():
                force_pending = False
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            print(f'KeyFlip recovery will retry: {error}', file=sys.stderr, flush=True)
        return GLib.SOURCE_CONTINUE

    def sleep_signal(_connection, _sender, _path, _interface, _signal, _parameters):
        nonlocal force_pending
        force_pending = True
        check()  # Both entering and leaving suspend restore Laptop Mode.

    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    subscription = bus.signal_subscribe('org.freedesktop.login1', 'org.freedesktop.login1.Manager',
        'PrepareForSleep', '/org/freedesktop/login1', None, Gio.DBusSignalFlags.NONE, sleep_signal)
    timer = GLib.timeout_add_seconds(5, check)
    try:
        loop.run()
    finally:
        GLib.source_remove(timer)
        bus.signal_unsubscribe(subscription)
        recover(force=True)


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Keyboard recovery requires root')
    if sys.argv[1:] == ['serve']:
        serve()
    elif len(sys.argv) == 4 and sys.argv[1] == 'arm':
        arm(sys.argv[2], sys.argv[3])
    elif sys.argv[1:] == ['disarm']:
        STATE.unlink(missing_ok=True)
    elif sys.argv[1:] == ['restore']:
        # Teardown has no next tick: wait for a mode change/Cleaning Mode to
        # release the shared lock instead of reporting success without recovery.
        recover(force=True, wait=True)
    else:
        raise RuntimeError('Invalid recovery action')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

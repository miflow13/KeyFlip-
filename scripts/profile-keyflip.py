#!/usr/bin/python3
"""Read-only GUI baseline; uses a unique app ID and memory-backed settings.

Run with GSETTINGS_BACKEND=memory and GSETTINGS_SCHEMA_DIR pointing to a
compiled copy of packaging/. Optional argument selects a source checkout.
"""
import json
import os
from pathlib import Path
import resource
import sys
import time

if os.environ.get('GSETTINGS_BACKEND') != 'memory':
    raise SystemExit('Use GSETTINGS_BACKEND=memory to avoid changing desktop settings.')
started = time.monotonic()
root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from keyflip import window as k
if hasattr(k, "StateMonitor"):
    monitor_class = k.StateMonitor
    k.StateMonitor = lambda callback: monitor_class(callback, role=None)
k.app = k.Gtk.Application(application_id='io.github.miflow13.KeyFlip.Profile', flags=k.Gio.ApplicationFlags.NON_UNIQUE)
k.app.register(None)
k.load_css()
window = k.KeyboardWindow(k.app)
loop = k.GLib.MainLoop()
measure = {}

def cpu():
    usage = [resource.getrusage(who) for who in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    return sum(item.ru_utime + item.ru_stime for item in usage)

def memory():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('VmRSS:'):
            return int(line.split()[1])

def begin_idle():
    measure['startup_status_ms'] = round((time.monotonic() - started) * 1000, 2)
    measure['rss_kib'] = memory()
    measure['idle_started'] = time.monotonic()
    measure['cpu_started'] = cpu()
    k.GLib.timeout_add_seconds(10, finish)
    return False

def wait_status():
    if window.state_label.get_text() == 'Checking status...':
        return True
    begin_idle()
    return False

def finish():
    duration = time.monotonic() - measure.pop('idle_started')
    measure['idle_cpu_percent_one_core_including_children'] = round((cpu() - measure.pop('cpu_started')) / duration * 100, 3)
    measure['idle_seconds'] = round(duration, 2)
    measure['rss_after_idle_kib'] = memory()
    window.close()
    loop.quit()
    print(json.dumps(measure), flush=True)
    return False

window.present()
k.GLib.timeout_add(10, wait_status)
loop.run()

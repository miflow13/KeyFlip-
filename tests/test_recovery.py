"""Recovery failure paths without modifying real input devices."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from keyflip import recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.state = self.root / 'desk.json'
        self.state.write_text(json.dumps(dict(uid=os.getuid(), port='serio0')))
        for name, value in [('STATE', self.state), ('LOCK', self.root / 'lock')]:
            change = patch.object(recovery, name, value)
            change.start()
            self.addCleanup(change.stop)

    def test_all_frontends_gone_restores_and_disarms(self):
        with patch.object(recovery, 'frontend_alive', return_value=False), patch.object(recovery, 'restore') as restore:
            recovery.recover()
        restore.assert_called_once_with(dict(uid=os.getuid(), port='serio0'))
        self.assertFalse(self.state.exists())

    def test_teardown_waits_for_busy_keyboard_change(self):
        import fcntl
        import threading
        import time
        with recovery.LOCK.open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            def unlock():
                time.sleep(0.05)
                fcntl.flock(lock, fcntl.LOCK_UN)
            worker = threading.Thread(target=unlock)
            worker.start()
            try:
                with patch.object(recovery, 'restore') as restore, \
                     patch.object(recovery.os, 'geteuid', return_value=0), \
                     patch.object(recovery.sys, 'argv', ['recovery.py', 'restore']):
                    recovery.main()
                restore.assert_called_once()
                self.assertFalse(self.state.exists())
            finally:
                worker.join()

    def test_live_frontend_keeps_desk_mode(self):
        with patch.object(recovery, 'frontend_alive', return_value=True), patch.object(recovery, 'restore') as restore:
            recovery.recover()
        restore.assert_not_called()
        self.assertTrue(self.state.exists())

    def test_suspend_forces_restore_even_with_live_frontend(self):
        with patch.object(recovery, 'frontend_alive', return_value=True), patch.object(recovery, 'restore') as restore:
            recovery.recover(force=True)
        restore.assert_called_once()
        self.assertFalse(self.state.exists())

    def test_failed_restore_retains_record_for_retry(self):
        with patch.object(recovery, 'restore', side_effect=OSError('bind failed')):
            with self.assertRaises(OSError):
                recovery.recover(force=True)
        self.assertTrue(self.state.exists())
        with patch.object(recovery, 'restore') as restore:
            recovery.recover(force=True)
        restore.assert_called_once()
        self.assertFalse(self.state.exists())

    def test_dead_app_lease_does_not_hide_live_panel(self):
        runtime = self.root / str(os.getuid())
        runtime.mkdir()
        for role, pid in [('app', 123), ('panel', 456)]:
            (runtime / f'keyflip-{role}.lease').write_text(json.dumps(dict(pid=pid, start='1')))
        with patch.object(recovery, 'process_matches', side_effect=lambda pid, start: pid == 456):
            self.assertTrue(recovery.frontend_alive(os.getuid(), self.root))

    def test_stale_lease_is_not_live_even_if_pid_exists(self):
        runtime = self.root / str(os.getuid())
        runtime.mkdir()
        lease = runtime / 'keyflip-app.lease'
        lease.write_text(json.dumps(dict(pid=os.getpid(), start='1')))
        os.utime(lease, (100, 100))
        with patch.object(recovery, 'process_matches', return_value=True):
            self.assertFalse(recovery.frontend_alive(os.getuid(), self.root, now=116))

    def test_restore_requires_confirmed_driver_before_disarming(self):
        port = self.root / 'devices/serio0'
        driver = self.root / 'drivers/atkbd'
        port.mkdir(parents=True)
        driver.mkdir(parents=True)
        (port / 'description').write_text('i8042 KBD port')
        with self.assertRaisesRegex(RuntimeError, 'could not confirm'):
            recovery.restore(dict(port='serio0'), self.root)
        self.assertEqual((port / 'bind_mode').read_text(), 'auto')
        self.assertEqual((driver / 'bind').read_text(), 'serio0')


if __name__ == '__main__':
    unittest.main()

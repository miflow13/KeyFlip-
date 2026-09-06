"""Keep every installation route aligned with the runtime file layout."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingLayoutTests(unittest.TestCase):
    def test_runtime_sources_exist(self):
        expected = {
            "__init__.py", "application.py", "window.py", "state.py",
            "cleaning.py", "recovery.py", "sound.py",
        }
        self.assertEqual({path.name for path in (ROOT / "src/keyflip").glob("*.py")}, expected)
        self.assertTrue((ROOT / "helper/keyflip-helper").is_file())
        self.assertTrue((ROOT / "packaging/systemd/keyflip-recovery.service").is_file())

    def test_install_routes_include_package_and_helper(self):
        install = (ROOT / "install.sh").read_text()
        release = (ROOT / "scripts/build-release.sh").read_text()
        arch = (ROOT / "packaging/arch/PKGBUILD").read_text()
        rpm = (ROOT / "packaging/obs/keyflip.spec").read_text()
        for text in (install, release, arch, rpm):
            self.assertIn("src/keyflip", text)
            self.assertIn("helper/keyflip-helper", text)
        for text in (install, release, arch, rpm):
            self.assertIn("packaging/systemd/keyflip-recovery.service", text)

    def test_privileged_installed_path_is_stable(self):
        policy = (ROOT / "packaging/io.github.miflow13.KeyFlip.policy").read_text()
        extension = (ROOT / "gnome-extension/extension.js").read_text()
        self.assertIn("/usr/libexec/keyflip/keyflip-helper", policy)
        self.assertIn("/usr/libexec/keyflip/keyflip-helper", extension)


if __name__ == "__main__":
    unittest.main()

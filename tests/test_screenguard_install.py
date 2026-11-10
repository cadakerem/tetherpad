import os
import sys
import subprocess
import unittest
from unittest.mock import patch, MagicMock

# Add repository root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestScreenGuardInstall(unittest.TestCase):
    """Unit tests for ScreenGuard APK installation logic across Android versions."""

    def _setup_mock_dispatcher(self, install_stdout="Success\n", install_ret=0):
        """Helper to create a standard mock subprocess runner for ADB."""
        executed_cmds = []

        def side_effect(cmd, *args, **kwargs):
            executed_cmds.append(list(cmd))
            cmd_str = " ".join(cmd)
            if "pm list packages" in cmd_str:
                return MagicMock(stdout="", returncode=0)
            elif "install" in cmd_str:
                return MagicMock(stdout=install_stdout, returncode=install_ret)
            elif "am start" in cmd_str:
                return MagicMock(stdout="Starting...", returncode=0)
            return MagicMock(stdout="", returncode=0)

        return side_effect, executed_cmds

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_legacy_android_omits_g_flag(self, mock_run, mock_exists):
        """On Android < 6, -g flag must be omitted from adb install."""
        import tetherpad
        tetherpad._device_info = {
            "android_ver": 4,
            "manufacturer": "GRUNDIG",
            "ver_str": "4.4.4"
        }

        side_effect, cmds = self._setup_mock_dispatcher("Success\n", 0)
        mock_run.side_effect = side_effect
        tetherpad.setup_screenguard()

        install_cmds = [c for c in cmds if "install" in c]
        self.assertEqual(len(install_cmds), 1)
        self.assertNotIn("-g", install_cmds[0])
        self.assertIn("-r", install_cmds[0])
        self.assertIn("-d", install_cmds[0])

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_modern_android_uses_g_flag(self, mock_run, mock_exists):
        """On Android >= 6, -g flag must be included initially."""
        import tetherpad
        tetherpad._device_info = {
            "android_ver": 14,
            "manufacturer": "GOOGLE",
            "ver_str": "14"
        }

        side_effect, cmds = self._setup_mock_dispatcher("Success\n", 0)
        mock_run.side_effect = side_effect
        tetherpad.setup_screenguard()

        install_cmds = [c for c in cmds if "install" in c]
        self.assertEqual(len(install_cmds), 1)
        self.assertIn("-g", install_cmds[0])

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_fallback_triggers_when_g_fails_silently(self, mock_run, mock_exists):
        """If -g causes exit 0 but lacks Success in stdout, retry without -g."""
        import tetherpad
        tetherpad._device_info = {
            "android_ver": 8,
            "manufacturer": "GENERIC",
            "ver_str": "8.0"
        }

        cmds = []

        def side_effect(cmd, *args, **kwargs):
            cmds.append(list(cmd))
            if "pm" in cmd:
                return MagicMock(stdout="", returncode=0)
            elif "install" in cmd:
                if "-g" in cmd:
                    # Silent failure on older adb/pm
                    return MagicMock(
                        stdout="Error: Unknown option: -g\n",
                        returncode=0
                    )
                return MagicMock(stdout="Success\n", returncode=0)
            elif "am" in cmd and "start" in cmd:
                return MagicMock(returncode=0)
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect
        tetherpad.setup_screenguard()

        install_cmds = [c for c in cmds if "install" in c]
        self.assertEqual(len(install_cmds), 2)
        self.assertIn("-g", install_cmds[0])
        self.assertNotIn("-g", install_cmds[1])

    @patch("subprocess.run")
    def test_immersive_mode_modern_android(self, mock_run):
        """On Android >= 5, set_immersive_mode uses settings put global policy_control."""
        import tetherpad
        tetherpad._device_info = {"android_ver": 11}

        tetherpad.set_immersive_mode(True)
        mock_run.assert_called_with(
            [tetherpad.adb_cmd, "shell", "settings", "put", "global", "policy_control", "immersive.navigation=*"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2
        )

        tetherpad.set_immersive_mode(False)
        mock_run.assert_called_with(
            [tetherpad.adb_cmd, "shell", "settings", "put", "global", "policy_control", "null*"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2
        )

    @patch("subprocess.run")
    def test_immersive_mode_query_and_toggle(self, mock_run):
        """is_immersive_mode_enabled queries settings, and toggle flips state."""
        import tetherpad
        tetherpad._device_info = {"android_ver": 10}

        mock_run.return_value = MagicMock(stdout="immersive.navigation=*", returncode=0)
        self.assertTrue(tetherpad.is_immersive_mode_enabled())

        mock_run.return_value = MagicMock(stdout="null*", returncode=0)
        self.assertFalse(tetherpad.is_immersive_mode_enabled())

        # Toggle when disabled should enable it
        tetherpad.toggle_immersive_mode()
        mock_run.assert_called_with(
            [tetherpad.adb_cmd, "shell", "settings", "put", "global", "policy_control", "immersive.navigation=*"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2
        )


if __name__ == "__main__":
    unittest.main()

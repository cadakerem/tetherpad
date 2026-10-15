import unittest
import py_compile
import subprocess
import sys
import os
import threading
from unittest.mock import patch, MagicMock

# Add repository root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class TestMultiNodeDualSense(unittest.TestCase):
    def test_py_compile(self):
        """Ensure tetherpad.py compiles with 0 syntax errors."""
        res = py_compile.compile("tetherpad.py", doraise=True)
        self.assertTrue(res)

    @patch("subprocess.run")
    def test_find_device_node_modern_android(self, mock_run):
        """Simulate Google Pixel (Android 17) with DualSense multi-node split."""
        pixel_output = """
add device 1: /dev/input/event0
  name:     "qpnp_pon"
add device 2: /dev/input/event7
  name:     "DualSense Wireless Controller Touchpad"
  vendor:   054c
  product:  0ce6
add device 3: /dev/input/event8
  name:     "DualSense Wireless Controller Motion Sensors"
  vendor:   054c
  product:  0ce6
add device 4: /dev/input/event9
  name:     "DualSense Wireless Controller"
  vendor:   054c
  product:  0ce6
"""
        mock_run.return_value = MagicMock(stdout=pixel_output)
        import tetherpad
        main_node, p_type, name, tp_node = tetherpad.find_device_node()

        self.assertEqual(main_node, "/dev/input/event9")
        self.assertEqual(p_type, "sony")
        self.assertEqual(name, "DualSense Wireless Controller")
        self.assertEqual(tp_node, "/dev/input/event7")

    @patch("subprocess.run")
    def test_find_device_node_legacy_android(self, mock_run):
        """Simulate legacy Android 4.4 / 7 (MTK BT HID single node)."""
        legacy_output = """
add device 1: /dev/input/event0
  name:     "gpio-keys"
add device 2: /dev/input/event3
  name:     "MTK BT HID"
  vendor:   0000
  product:  0000
"""
        mock_run.return_value = MagicMock(stdout=legacy_output)
        import tetherpad
        main_node, p_type, name, tp_node = tetherpad.find_device_node()

        self.assertEqual(main_node, "/dev/input/event3")
        self.assertEqual(p_type, "sony")
        self.assertEqual(name, "MTK BT HID")
        self.assertIsNone(tp_node)

    @patch("subprocess.run")
    def test_find_device_node_xbox(self, mock_run):
        """Simulate Xbox Wireless Controller."""
        xbox_output = """
add device 1: /dev/input/event4
  name:     "Xbox Wireless Controller"
  vendor:   045e
  product:  02fd
"""
        mock_run.return_value = MagicMock(stdout=xbox_output)
        import tetherpad
        main_node, p_type, name, tp_node = tetherpad.find_device_node()

        self.assertEqual(main_node, "/dev/input/event4")
        self.assertEqual(p_type, "xbox")
        self.assertIn("Xbox", name)
        self.assertIsNone(tp_node)

    @patch("subprocess.run")
    def test_find_device_node_empty(self, mock_run):
        """Simulate no controller connected."""
        mock_run.return_value = MagicMock(stdout="add device 1: /dev/input/event0\n  name: 'power_key'")
        import tetherpad
        main_node, p_type, name, tp_node = tetherpad.find_device_node()

        self.assertIsNone(main_node)
        self.assertIsNone(p_type)
        self.assertIsNone(name)
        self.assertIsNone(tp_node)

    def test_gamepad_bridge_thread_safety(self):
        """Verify GamepadBridge handles concurrent button and touchpad updates without races."""
        import tetherpad
        with patch.object(tetherpad.vg, "VDS4Gamepad") as mock_vds4:
            mock_pad = MagicMock()
            mock_vds4.return_value = mock_pad
            bridge = tetherpad.GamepadBridge("sony")
            self.assertTrue(hasattr(bridge, "lock"))

            errors = []
            def worker_buttons():
                try:
                    for _ in range(50):
                        bridge.press_button(0x0001)
                        bridge.set_left_stick(100, 200)
                        bridge.release_button(0x0001)
                except Exception as e:
                    errors.append(e)

            def worker_touchpad():
                try:
                    for i in range(50):
                        bridge.set_touchpad(True, i * 10, i * 5)
                        bridge.set_touchpad(False, 0, 0)
                except Exception as e:
                    errors.append(e)

            threads = [
                threading.Thread(target=worker_buttons),
                threading.Thread(target=worker_touchpad),
                threading.Thread(target=worker_buttons),
                threading.Thread(target=worker_touchpad)
            ]
            for t in threads: t.start()
            for t in threads: t.join()

            self.assertEqual(len(errors), 0)

if __name__ == "__main__":
    unittest.main()

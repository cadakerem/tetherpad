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
        self.assertEqual(p_type, "sony_modern")
        self.assertEqual(name, "DualSense Wireless Controller")
        self.assertEqual(tp_node, "/dev/input/event7")

    @patch("subprocess.run")
    def test_find_device_node_synaptics_touchpad_before_controller(self, mock_run):
        """Regression test: non-Sony touchpad before controller must not raise UnboundLocalError."""
        output = """
add device 1: /dev/input/event0
  name:     "synaptics_touchpad"
  vendor:   06cb
  product:  0000
add device 2: /dev/input/event7
  name:     "DualSense Wireless Controller Touchpad"
  vendor:   054c
  product:  0ce6
add device 3: /dev/input/event9
  name:     "DualSense Wireless Controller"
  vendor:   054c
  product:  0ce6
"""
        mock_run.return_value = MagicMock(stdout=output)
        import tetherpad
        main_node, p_type, name, tp_node = tetherpad.find_device_node()

        self.assertEqual(main_node, "/dev/input/event9")
        self.assertEqual(p_type, "sony_modern")
        self.assertEqual(tp_node, "/dev/input/event7")

    @patch("subprocess.run")
    def test_find_device_node_generic_touchpad_name_with_sony_vendor(self, mock_run):
        """Regression test: device named simply 'Touchpad' with vendor 054c matches companion."""
        output = """
add device 1: /dev/input/event2
  name:     "Touchpad"
  vendor:   054c
  product:  0ce6
add device 2: /dev/input/event9
  name:     "DualSense Wireless Controller"
  vendor:   054c
  product:  0ce6
"""
        mock_run.return_value = MagicMock(stdout=output)
        import tetherpad
        main_node, p_type, name, tp_node = tetherpad.find_device_node()

        self.assertEqual(main_node, "/dev/input/event9")
        self.assertEqual(p_type, "sony_modern")
        self.assertEqual(tp_node, "/dev/input/event2")

    @patch("subprocess.run")
    def test_find_device_node_ds4_with_touchpad_retains_sony_legacy(self, mock_run):
        """DualShock 4 (product 05c4 / Wireless Controller) retains legacy sony profile even if touchpad node is split."""
        ds4_output = """
add device 1: /dev/input/event7
  name:     "Wireless Controller Touchpad"
  vendor:   054c
  product:  05c4
add device 2: /dev/input/event9
  name:     "Wireless Controller"
  vendor:   054c
  product:  05c4
"""
        mock_run.return_value = MagicMock(stdout=ds4_output)
        import tetherpad
        main_node, p_type, name, tp_node = tetherpad.find_device_node()

        self.assertEqual(main_node, "/dev/input/event9")
        self.assertEqual(p_type, "sony")
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
        with patch.object(tetherpad, "vg") as mock_vg:
            mock_pad = MagicMock()
            mock_vg.VDS4Gamepad.return_value = mock_pad
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

    def test_mapping_sony_modern_evdev_axes(self):
        """Verify modern hid-playstation profile maps right stick and triggers according to Linux evdev."""
        import tetherpad
        tetherpad.load_mapping("sony_modern")
        self.assertEqual(tetherpad.AXIS_RX, "0003")
        self.assertEqual(tetherpad.AXIS_RY, "0004")
        self.assertEqual(tetherpad.AXIS_L2, "0002")
        self.assertEqual(tetherpad.AXIS_R2, "0005")

    def test_mapping_sony_legacy_axes(self):
        """Verify legacy Sony profile retains MTK BT HID quirks for Android 4.4/7.0."""
        import tetherpad
        tetherpad.load_mapping("sony")
        self.assertEqual(tetherpad.AXIS_RX, "0002")
        self.assertEqual(tetherpad.AXIS_RY, "0005")
        self.assertEqual(tetherpad.AXIS_L2, "0003")
        self.assertEqual(tetherpad.AXIS_R2, "0004")

    def test_resolve_profile_matrix(self):
        """Test resolve_profile across DualSense, DualShock 4, legacy, and Xbox."""
        import tetherpad
        # DualSense by name
        self.assertEqual(tetherpad.resolve_profile("sony", "DualSense Wireless Controller", "/dev/input/event7"), "sony_modern")
        # DualSense by product ID (0ce6)
        self.assertEqual(tetherpad.resolve_profile("sony", "Wireless Controller", "/dev/input/event7", "0ce6"), "sony_modern")
        # DualSense Edge by product ID (0df2)
        self.assertEqual(tetherpad.resolve_profile("sony", "Wireless Controller", "/dev/input/event7", "0df2"), "sony_modern")
        # DualShock 4 with companion touchpad -> retains sony legacy layout
        self.assertEqual(tetherpad.resolve_profile("sony", "Wireless Controller", "/dev/input/event7", "05c4"), "sony")
        # DualSense without touchpad node (single-node legacy Android 4.4/7) -> retains sony legacy layout
        self.assertEqual(tetherpad.resolve_profile("sony", "DualSense Wireless Controller", None), "sony")
        # Xbox controller -> stays xbox
        self.assertEqual(tetherpad.resolve_profile("xbox", "Xbox Wireless Controller", None), "xbox")

if __name__ == "__main__":
    unittest.main()

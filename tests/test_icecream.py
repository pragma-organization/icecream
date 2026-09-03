#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
from io import StringIO
from unittest.mock import patch

from icecream import ic


def captureIcOutput(func):
    """Run func and capture everything ic() writes to stderr."""
    buf = StringIO()
    with patch.object(ic, 'outputFunction', lambda s: buf.write(s + '\n')):
        func()
    return buf.getvalue()


class TestIcDisabledContextManager(unittest.TestCase):

    def setUp(self):
        # Always start each test with ic enabled.
        ic.enable()

    def tearDown(self):
        # Restore enabled state after each test.
        ic.enable()

    # ------------------------------------------------------------------
    # Case 1: ic is enabled; output is suppressed inside the block and
    #         restored afterwards.
    # ------------------------------------------------------------------
    def test_disabled_suppresses_output_and_restores(self):
        output = []
        with patch.object(ic, 'outputFunction', lambda s: output.append(s)):
            ic(1)                        # should print
            with ic.disabled():
                ic(2)                    # should be silent
            ic(3)                        # should print again

        # Extract the integer values that appeared in output lines.
        values = [line for line in output]
        self.assertEqual(len(values), 2,
                         "Expected exactly 2 output lines (before and after block)")
        self.assertIn('1', values[0])
        self.assertIn('3', values[1])

    def test_disabled_enabled_state_restored_after_block(self):
        """ic.enabled should be True after exiting a disabled() block."""
        ic.enable()
        with ic.disabled():
            self.assertFalse(ic.enabled)
        self.assertTrue(ic.enabled)

    # ------------------------------------------------------------------
    # Case 2: ic was already disabled before entering the block;
    #         it must stay disabled after the block exits.
    # ------------------------------------------------------------------
    def test_disabled_preserves_already_disabled_state(self):
        ic.disable()
        with ic.disabled():
            self.assertFalse(ic.enabled)
        # Must still be disabled after block exit.
        self.assertFalse(ic.enabled)

    # ------------------------------------------------------------------
    # Case 3: exception inside the block; previous state is restored.
    # ------------------------------------------------------------------
    def test_disabled_restores_state_on_exception(self):
        ic.enable()
        try:
            with ic.disabled():
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        # State must be restored to enabled.
        self.assertTrue(ic.enabled)

    def test_disabled_restores_disabled_state_on_exception(self):
        """If ic was disabled before the block, it stays disabled after an exception."""
        ic.disable()
        try:
            with ic.disabled():
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        self.assertFalse(ic.enabled)

    # ------------------------------------------------------------------
    # Case 4: nested disabled() blocks.
    # ------------------------------------------------------------------
    def test_nested_disabled_blocks(self):
        """Exiting the inner block must not re-enable ic while the outer block is active."""
        ic.enable()
        with ic.disabled():
            self.assertFalse(ic.enabled)   # outer block disables
            with ic.disabled():
                self.assertFalse(ic.enabled)  # still disabled inside inner
            # inner block has exited — must still be disabled
            self.assertFalse(ic.enabled)
        # outer block has exited — must be enabled again
        self.assertTrue(ic.enabled)

    def test_nested_disabled_blocks_no_spurious_output(self):
        """No ic() call inside any nested disabled() block should produce output."""
        output = []
        with patch.object(ic, 'outputFunction', lambda s: output.append(s)):
            with ic.disabled():
                ic('outer suppressed')
                with ic.disabled():
                    ic('inner suppressed')
                ic('still suppressed')
        self.assertEqual(output, [], "No output expected inside nested disabled() blocks")


if __name__ == '__main__':
    unittest.main()

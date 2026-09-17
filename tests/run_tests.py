"""Test-suite entry point — run inside FreeCAD's console interpreter.

Usage:
    freecadcmd.exe tests/run_tests.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))


def main() -> None:
    loader = unittest.TestLoader()
    suite = loader.discover(HERE, pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


main()

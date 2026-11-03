"""Load the replaceable LGPL FriBidi DLL before Pillow initialises RAQM."""
import os
from pathlib import Path

def setup():
    if os.name != 'nt': return False
    try:
        import ctypes
        ctypes.WinDLL(str(Path(__file__).with_name('fonts')/'libfribidi-0.dll'))
        return True
    except OSError:
        return False

setup()

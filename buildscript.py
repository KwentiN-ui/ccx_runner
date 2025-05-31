"""
Dieses Skript erzeugt bei Ausführung eine Binärdatei der GUI Anwendung zur Ausführung ohne installierten Python Interpreter.
"""

import PyInstaller.__main__
import os
from pathlib import Path


PyInstaller.__main__.run([
    'ccx_runner/main.py',
    '--onefile',
    '--name=CCX_Runner',
    # '--windowed',
    '--clean',
])

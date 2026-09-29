#!/usr/bin/env python3
"""
SSStudio - App Store Screenshot Composer
Simple, fast, high-quality GUI application for creating App Store promotional screenshots.
"""

import sys
import os

# Ensure local SSStudio package is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow


def main():
    try:
        app = MainWindow()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()

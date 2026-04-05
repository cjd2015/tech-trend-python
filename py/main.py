#!/usr/bin/env python3
"""Crucix - Python Intelligence Engine"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crucix.server import run

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════╗
║           CRUCIX INTELLIGENCE ENGINE         ║
║              Python Edition v2.0             ║
╠══════════════════════════════════════════════╣
║  Dashboard:  http://localhost:3117           ║
║  Sources:   29 OSINT feeds                  ║
║  Refresh:   Every 15 min                    ║
╚══════════════════════════════════════════════╝
    """)
    run()

#!/usr/bin/env python3
"""TechTrend - Python Intelligence Engine"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from techtrend.server import run

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════╗
║           TECHTREND INTELLIGENCE ENGINE       ║
║              Python Edition v2.0             ║
╠══════════════════════════════════════════════╣
║  Dashboard:  http://localhost:3117           ║
║  Sources:   29 OSINT feeds                  ║
║  Refresh:   Every 15 min                    ║
╚══════════════════════════════════════════════╝
    """)
    run()
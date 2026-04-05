#!/usr/bin/env python3
"""
Crucix Lite - Python Intelligence Engine
A lightweight OSINT aggregator from public data sources.
"""

from .sources import *
from .engine import CrucixEngine
from .delta import DeltaEngine

__version__ = "1.0.0"

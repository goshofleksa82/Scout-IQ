"""Compatibility import; implementation is in app/repositories/players.py."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("app.repositories.players")
